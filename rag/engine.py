from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .corpus import (
    LexicalRetriever,
    RetrievalDocument,
    RetrievedChunk,
    build_domain_keywords,
    build_documents_from_dataset,
    load_documents_jsonl,
)
from .policy import PolicyDecision, QueryPolicy
from .vertex import LocalGroundedGenerator, VertexConfig, VertexGenerator

CITATION_RE = re.compile(r"\[([a-z0-9:_\-]+)\]", re.I)


@dataclass(frozen=True)
class RAGResponse:
    status: str
    answer: Optional[str]
    refusal_reason: Optional[str]
    refusal_message: Optional[str]
    citations: List[Dict[str, object]]
    retrieved_count: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class RAGEngine:
    def __init__(
        self,
        retriever: LexicalRetriever,
        policy: QueryPolicy,
        generator,
        min_retrieval_score: float = 0.04,
    ):
        self.retriever = retriever
        self.policy = policy
        self.generator = generator
        self.min_retrieval_score = min_retrieval_score

    @classmethod
    def from_paths(
        cls,
        data_dir: Path,
        corpus_jsonl_path: Optional[Path] = None,
        use_vertex: bool = True,
    ) -> "RAGEngine":
        if corpus_jsonl_path and corpus_jsonl_path.exists():
            docs = load_documents_jsonl(corpus_jsonl_path)
        else:
            docs = build_documents_from_dataset(data_dir)

        retriever = LexicalRetriever(docs)
        policy = QueryPolicy(build_domain_keywords(docs), min_domain_overlap=2)
        generator = _build_generator(use_vertex=use_vertex)
        return cls(retriever=retriever, policy=policy, generator=generator)

    def ask(self, query: str, top_k: int = 6) -> RAGResponse:
        decision = self.policy.evaluate(query)
        if not decision.allow:
            return self._refuse(decision, retrieved_count=0)

        retrieved = self.retriever.retrieve(query, top_k=max(2, top_k))
        if not retrieved:
            return self._refuse(
                PolicyDecision(
                    allow=False,
                    reason="out_of_scope",
                    message="I could not find grounded evidence for that question in this corpus.",
                ),
                retrieved_count=0,
            )
        if retrieved[0].score < self.min_retrieval_score:
            return self._refuse(
                PolicyDecision(
                    allow=False,
                    reason="out_of_scope",
                    message="That appears outside the covered learning-engineering material.",
                ),
                retrieved_count=len(retrieved),
            )

        prompt = self._build_prompt(query=query, retrieved=retrieved)
        answer = self.generator.generate(prompt).strip()

        if "INSUFFICIENT_GROUNDED_CONTEXT" in answer:
            return self._refuse(
                PolicyDecision(
                    allow=False,
                    reason="out_of_scope",
                    message="I cannot answer that with grounded evidence from the available corpus.",
                ),
                retrieved_count=len(retrieved),
            )

        allowed_ids = {item.document.doc_id for item in retrieved}
        cited_ids = {cid.lower() for cid in CITATION_RE.findall(answer)}
        if not cited_ids:
            return self._refuse(
                PolicyDecision(
                    allow=False,
                    reason="grounding_failure",
                    message="I could not produce a citation-grounded answer for that question.",
                ),
                retrieved_count=len(retrieved),
            )

        invalid = [cid for cid in cited_ids if cid not in {x.lower() for x in allowed_ids}]
        if invalid:
            return self._refuse(
                PolicyDecision(
                    allow=False,
                    reason="grounding_failure",
                    message="I could not guarantee that all claims are grounded in retrieved evidence.",
                ),
                retrieved_count=len(retrieved),
            )

        citations = [_citation_payload(chunk) for chunk in retrieved[:top_k]]
        return RAGResponse(
            status="answer",
            answer=answer,
            refusal_reason=None,
            refusal_message=None,
            citations=citations,
            retrieved_count=len(retrieved),
        )

    def _refuse(self, decision: PolicyDecision, retrieved_count: int) -> RAGResponse:
        return RAGResponse(
            status="refused",
            answer=None,
            refusal_reason=decision.reason,
            refusal_message=decision.message,
            citations=[],
            retrieved_count=retrieved_count,
        )

    def _build_prompt(self, query: str, retrieved: List[RetrievedChunk]) -> str:
        snippets = []
        for item in retrieved:
            doc = item.document
            snippet = doc.text.strip().replace("\n", " ")
            snippets.append(f"[{doc.doc_id}] {doc.title} :: {snippet[:900]}")

        context_block = "\n".join(snippets)
        return f"""
You are a retrieval-grounded assistant for Learning Engineering.

Hard constraints:
1) Use only the provided context snippets.
2) If the evidence is insufficient, return exactly: INSUFFICIENT_GROUNDED_CONTEXT
3) Include inline citations in square brackets, e.g., [paper:W123].
4) Do not answer controversial/polarizing topics or out-of-domain requests.

Question:
{query}

CONTEXT_SNIPPETS_START
{context_block}
CONTEXT_SNIPPETS_END

Provide a concise answer with citations after each key claim.
""".strip()


def _citation_payload(item: RetrievedChunk) -> Dict[str, object]:
    doc = item.document
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "score": round(item.score, 6),
        "source_url": doc.metadata.get("source_url"),
        "type": doc.metadata.get("type"),
    }


def _build_generator(use_vertex: bool):
    if not use_vertex:
        return LocalGroundedGenerator()

    project_id = os.getenv("VERTEX_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("VERTEX_LOCATION", "us-central1")
    model_name = os.getenv("VERTEX_MODEL_NAME", "gemini-2.5-flash")
    if not project_id:
        return LocalGroundedGenerator()
    return VertexGenerator(VertexConfig(project_id=project_id, location=location, model_name=model_name))
