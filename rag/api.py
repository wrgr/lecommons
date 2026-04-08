from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import RAGEngine
from .knowledge_ops import load_external_docs, rebuild_rag_corpus, sync_knowledge

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", str(ROOT / "data")))
CORPUS_PATH = Path(os.getenv("RAG_CORPUS_PATH", str(DATA_DIR / "rag_corpus.jsonl")))
USE_VERTEX = os.getenv("RAG_USE_VERTEX", "1") not in {"0", "false", "False"}

_engine_lock = threading.Lock()


def _build_engine() -> RAGEngine:
    return RAGEngine.from_paths(
        data_dir=DATA_DIR,
        corpus_jsonl_path=CORPUS_PATH if CORPUS_PATH.exists() else None,
        use_vertex=USE_VERTEX,
    )


engine = _build_engine()

app = FastAPI(title="Learning Engineering Vertex RAG", version="0.1.0")


class AskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2400)
    top_k: int = Field(default=6, ge=2, le=12)


class SyncRequest(BaseModel):
    query: Optional[str] = Field(default=None, min_length=2, max_length=300)
    urls: List[str] = Field(default_factory=list, max_length=40)
    paths: List[str] = Field(default_factory=list, max_length=40)
    tags: List[str] = Field(default_factory=list, max_length=20)
    max_search_results: int = Field(default=6, ge=1, le=20)
    scan_search_results: int = Field(default=4, ge=0, le=20)
    rebuild_dataset_first: bool = False
    skip_openalex: bool = True


@app.get("/healthz")
def healthz() -> dict:
    extra_docs = load_external_docs(DATA_DIR / "extra_docs.json")
    return {
        "ok": True,
        "corpus_loaded": len(engine.retriever.documents),
        "extra_docs": extra_docs.get("count", 0),
        "corpus_path": str(CORPUS_PATH),
        "vertex_enabled": USE_VERTEX,
    }


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    return engine.ask(query=req.query, top_k=req.top_k).to_dict()


@app.post("/admin/rebuild-corpus")
def admin_rebuild_corpus() -> dict:
    stats = rebuild_rag_corpus(data_dir=DATA_DIR, corpus_path=CORPUS_PATH)
    reload_stats = admin_reload()
    return {"rag_corpus": stats, "reload": reload_stats}


@app.post("/admin/reload")
def admin_reload() -> dict:
    global engine
    with _engine_lock:
        engine = _build_engine()
    return {
        "ok": True,
        "corpus_loaded": len(engine.retriever.documents),
        "vertex_enabled": USE_VERTEX,
    }


@app.post("/admin/sync")
def admin_sync(req: SyncRequest) -> dict:
    try:
        report = sync_knowledge(
            query=req.query,
            urls=req.urls,
            paths=req.paths,
            max_search_results=req.max_search_results,
            scan_search_results=req.scan_search_results,
            tags=req.tags,
            rebuild_dataset_first=req.rebuild_dataset_first,
            skip_openalex=req.skip_openalex,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    reload_stats = admin_reload()
    return {
        "sync": report,
        "reload": reload_stats,
    }
