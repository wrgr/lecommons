from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .corpus import build_documents_from_dataset, write_documents_jsonl

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EXTRA_DOCS_PATH = DATA_DIR / "extra_docs.json"
RAG_CORPUS_PATH = DATA_DIR / "rag_corpus.jsonl"
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

_TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_DDG_LINK_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S,
)


@dataclass(frozen=True)
class ExternalDoc:
    doc_id: str
    title: str
    text: str
    source_type: str
    summary: str
    captured_at: str
    updated_at: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    query: Optional[str] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "text": self.text,
            "summary": self.summary,
            "source_type": self.source_type,
            "url": self.url,
            "file_path": self.file_path,
            "query": self.query,
            "tags": self.tags or [],
            "captured_at": self.captured_at,
            "updated_at": self.updated_at,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _strip_html(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw_html or "")
    cleaned = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return _normalize_space(html.unescape(cleaned))


def _extract_html_title(raw_html: str) -> Optional[str]:
    match = _TITLE_RE.search(raw_html or "")
    if not match:
        return None
    return _normalize_space(html.unescape(match.group(1)))


def _hash_locator(locator: str) -> str:
    return hashlib.sha1(locator.encode("utf-8")).hexdigest()[:18]


def _summary(text: str, limit: int = 280) -> str:
    compact = _normalize_space(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_external_docs(path: Path = EXTRA_DOCS_PATH) -> Dict[str, object]:
    payload = _read_json(path, default={})
    docs = payload.get("documents")
    if not isinstance(docs, list):
        docs = []
    return {
        "updated_at": payload.get("updated_at"),
        "count": len(docs),
        "documents": docs,
    }


def save_external_docs(documents: Sequence[Dict[str, object]], path: Path = EXTRA_DOCS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": now_iso(),
        "count": len(documents),
        "documents": list(documents),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _pdf_to_text_bytes(payload: bytes) -> str:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext is required to scan PDF documents.")
    with tempfile.TemporaryDirectory(prefix="webscan_pdf_") as tmpdir:
        tmp = Path(tmpdir)
        pdf_path = tmp / "input.pdf"
        txt_path = tmp / "out.txt"
        pdf_path.write_bytes(payload)
        subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return _normalize_space(txt_path.read_text(encoding="utf-8", errors="replace"))


def scan_url(url: str, query: Optional[str] = None, tags: Optional[Sequence[str]] = None) -> ExternalDoc:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = response.read()
        content_type = (response.headers.get("Content-Type") or "").lower()

    if "application/pdf" in content_type or url.lower().endswith(".pdf"):
        title = Path(urllib.parse.urlsplit(url).path).name or "PDF Document"
        text = _pdf_to_text_bytes(payload)
    else:
        raw_html = payload.decode("utf-8", errors="replace")
        title = _extract_html_title(raw_html) or url
        text = _strip_html(raw_html)

    locator = f"url:{url}"
    timestamp = now_iso()
    return ExternalDoc(
        doc_id=f"ext-{_hash_locator(locator)}",
        title=title[:240] or url,
        text=text[:45000],
        source_type="webscan",
        summary=_summary(text),
        url=url,
        file_path=None,
        query=query,
        tags=[str(t) for t in (tags or []) if str(t).strip()],
        captured_at=timestamp,
        updated_at=timestamp,
    )


def search_web(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw_html = resp.read().decode("utf-8", errors="replace")

    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for href, title_html in _DDG_LINK_RE.findall(raw_html):
        parsed = urllib.parse.urlsplit(href)
        if parsed.path == "/l/":
            params = urllib.parse.parse_qs(parsed.query)
            href = params.get("uddg", [href])[0]
        href = html.unescape(href)
        if not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append(
            {
                "url": href,
                "title": _normalize_space(_strip_html(title_html)) or href,
            }
        )
        if len(out) >= max(1, max_results):
            break
    return out


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    return _strip_html(xml)


def read_local_document(path: Path) -> Tuple[str, str]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".py"}:
        return (path.stem, _normalize_space(path.read_text(encoding="utf-8", errors="replace")))
    if ext in {".html", ".htm"}:
        raw = path.read_text(encoding="utf-8", errors="replace")
        title = _extract_html_title(raw) or path.stem
        return (title, _strip_html(raw))
    if ext == ".docx":
        return (path.stem, _extract_docx_text(path))
    if ext == ".pdf":
        if shutil.which("pdftotext") is None:
            raise RuntimeError("pdftotext is required to upload PDF documents.")
        with tempfile.TemporaryDirectory(prefix="upload_pdf_") as tmpdir:
            txt_path = Path(tmpdir) / "out.txt"
            subprocess.run(
                ["pdftotext", "-layout", str(path), str(txt_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return (path.stem, _normalize_space(txt_path.read_text(encoding="utf-8", errors="replace")))
    return (path.stem, _normalize_space(path.read_text(encoding="utf-8", errors="replace")))


def upload_paths(paths: Sequence[str], tags: Optional[Sequence[str]] = None) -> List[ExternalDoc]:
    out: List[ExternalDoc] = []
    timestamp = now_iso()
    for raw_path in paths:
        p = Path(raw_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(str(p))
        title, text = read_local_document(p)
        locator = f"file:{p}"
        out.append(
            ExternalDoc(
                doc_id=f"ext-{_hash_locator(locator)}",
                title=title[:240] or p.name,
                text=text[:45000],
                source_type="upload",
                summary=_summary(text),
                url=None,
                file_path=str(p),
                query=None,
                tags=[str(t) for t in (tags or []) if str(t).strip()],
                captured_at=timestamp,
                updated_at=timestamp,
            )
        )
    return out


def _doc_locator(doc: Dict[str, object]) -> str:
    if doc.get("url"):
        return f"url:{doc['url']}"
    if doc.get("file_path"):
        return f"file:{doc['file_path']}"
    return f"id:{doc.get('doc_id')}"


def upsert_external_docs(new_docs: Sequence[ExternalDoc], path: Path = EXTRA_DOCS_PATH) -> Dict[str, int]:
    current = load_external_docs(path)
    existing_rows = current.get("documents", [])
    index: Dict[str, Dict[str, object]] = {
        _doc_locator(row): dict(row)
        for row in existing_rows
        if isinstance(row, dict)
    }

    added = 0
    updated = 0
    for doc in new_docs:
        row = doc.to_dict()
        key = _doc_locator(row)
        prior = index.get(key)
        if prior:
            row["captured_at"] = prior.get("captured_at") or row["captured_at"]
            updated += 1
        else:
            added += 1
        index[key] = row

    merged = sorted(index.values(), key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    save_external_docs(merged, path=path)
    return {"added": added, "updated": updated, "total": len(merged)}


def rebuild_rag_corpus(data_dir: Path = DATA_DIR, corpus_path: Path = RAG_CORPUS_PATH) -> Dict[str, int]:
    docs = build_documents_from_dataset(data_dir)
    write_documents_jsonl(docs, corpus_path)
    return {"documents_written": len(docs)}


def rebuild_dataset(skip_openalex: bool = True) -> Dict[str, object]:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_dataset.py")]
    if skip_openalex:
        cmd.append("--skip-openalex")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2400:],
        "stderr": proc.stderr[-2400:],
    }


def sync_knowledge(
    *,
    query: Optional[str] = None,
    urls: Optional[Sequence[str]] = None,
    paths: Optional[Sequence[str]] = None,
    max_search_results: int = 6,
    scan_search_results: int = 4,
    tags: Optional[Sequence[str]] = None,
    rebuild_dataset_first: bool = False,
    skip_openalex: bool = True,
) -> Dict[str, object]:
    urls = list(urls or [])
    paths = list(paths or [])
    gathered: List[ExternalDoc] = []
    errors: List[str] = []
    search_results: List[Dict[str, str]] = []

    if query:
        try:
            search_results = search_web(query=query, max_results=max_search_results)
        except Exception as exc:
            errors.append(f"search failed: {exc}")
        for row in search_results[: max(0, scan_search_results)]:
            try:
                gathered.append(scan_url(row["url"], query=query, tags=tags))
            except Exception as exc:
                errors.append(f"scan failed for {row['url']}: {exc}")

    for url in urls:
        try:
            gathered.append(scan_url(url, query=query, tags=tags))
        except Exception as exc:
            errors.append(f"scan failed for {url}: {exc}")

    if paths:
        try:
            gathered.extend(upload_paths(paths, tags=tags))
        except Exception as exc:
            errors.append(f"upload failed: {exc}")

    upsert_stats = upsert_external_docs(gathered) if gathered else {
        "added": 0,
        "updated": 0,
        "total": load_external_docs()["count"],
    }

    dataset_stats = None
    if rebuild_dataset_first:
        dataset_stats = rebuild_dataset(skip_openalex=skip_openalex)
        if not dataset_stats["ok"]:
            errors.append("dataset rebuild failed")

    rag_stats = rebuild_rag_corpus()
    return {
        "query": query,
        "search_results": search_results,
        "scanned_or_uploaded_docs": len(gathered),
        "upsert": upsert_stats,
        "dataset_rebuild": dataset_stats,
        "rag_corpus": rag_stats,
        "errors": errors,
    }
