from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-]{1,}", re.I)


@dataclass(frozen=True)
class RetrievalDocument:
    doc_id: str
    title: str
    text: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class RetrievedChunk:
    document: RetrievalDocument
    score: float
    matched_terms: List[str]


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _paper_doc_id(raw_id: str, fallback_index: int) -> str:
    m = re.search(r"/(W\d+)$", raw_id or "")
    if m:
        return f"paper:{m.group(1)}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw_id or "").strip("-").lower()
    if not slug:
        slug = f"paper-{fallback_index}"
    return f"paper:{slug[:64]}"


def build_documents_from_dataset(data_dir: Path) -> List[RetrievalDocument]:
    topics = _load_json(data_dir / "topics_chapters.json")
    seed = _load_json(data_dir / "papers_seed.json")
    hop = _load_json(data_dir / "papers_one_hop.json")
    enriched = _load_json(data_dir / "endnotes_enriched.json")

    chapter_by_number: Dict[int, Dict[str, object]] = {
        int(ch["number"]): ch for ch in topics.get("chapters", [])
    }
    paper_chapters: Dict[str, set[int]] = defaultdict(set)
    paper_artifacts: Dict[str, set[str]] = defaultdict(set)

    for row in enriched.get("rows", []):
        if not row.get("matched") or not row.get("work_id"):
            continue
        wid = str(row["work_id"])
        chapter = row.get("chapter")
        if isinstance(chapter, int):
            paper_chapters[wid].add(chapter)
        artifact = row.get("artifact_type")
        if artifact:
            paper_artifacts[wid].add(str(artifact))

    out: List[RetrievalDocument] = []

    for ch in topics.get("chapters", []):
        number = int(ch["number"])
        section = str(ch.get("section", "Unknown"))
        title = str(ch.get("title", "Untitled"))
        doc_id = f"topic:ch{number:02d}"
        text = (
            f"Topic chapter {number} in section {section}. "
            f"Title: {title}. "
            "This chapter is part of the Learning Engineering body of knowledge."
        )
        out.append(
            RetrievalDocument(
                doc_id=doc_id,
                title=f"Chapter {number}: {title}",
                text=text,
                metadata={
                    "type": "topic",
                    "chapter": number,
                    "section": section,
                    "start_page": ch.get("start_page"),
                },
            )
        )

    all_papers: List[Dict[str, object]] = []
    for row in seed.get("papers", []):
        p = dict(row)
        p["scope"] = "seed"
        all_papers.append(p)
    for row in hop.get("papers", []):
        p = dict(row)
        p["scope"] = "hop"
        all_papers.append(p)

    for idx, paper in enumerate(all_papers, start=1):
        paper_id = str(paper.get("id", ""))
        doc_id = _paper_doc_id(paper_id, idx)
        chapters = sorted(paper_chapters.get(paper_id, set()))
        chapter_titles = [
            f"Chapter {c}: {chapter_by_number[c]['title']}"
            for c in chapters
            if c in chapter_by_number
        ]

        authors = paper.get("authors") or []
        if isinstance(authors, list):
            authors_text = ", ".join(str(a) for a in authors if a) or "Unknown authors"
        else:
            authors_text = "Unknown authors"

        artifacts = sorted(paper_artifacts.get(paper_id, set()))
        citation_plain = str(paper.get("citation_plain") or "")
        abstract = str(paper.get("abstract") or "Abstract unavailable.")
        title = str(paper.get("title") or "Untitled")
        scope = str(paper.get("scope") or "seed")

        sections = [
            f"Paper title: {title}",
            f"Scope: {scope}",
            f"Authors: {authors_text}",
            f"Year: {paper.get('year') or 'n.d.'}",
            f"Citation: {citation_plain}" if citation_plain else "",
            f"Abstract: {abstract}",
            f"Linked chapters: {', '.join(chapter_titles)}" if chapter_titles else "",
            f"Artifact types in toolkit: {', '.join(artifacts)}" if artifacts else "",
        ]
        text = "\n".join(s for s in sections if s)

        out.append(
            RetrievalDocument(
                doc_id=doc_id,
                title=title,
                text=text,
                metadata={
                    "type": "paper",
                    "paper_id": paper_id,
                    "scope": scope,
                    "year": paper.get("year"),
                    "source_url": paper.get("source_url"),
                    "chapters": chapters,
                    "artifact_types": artifacts,
                },
            )
        )

    out.extend(_build_external_documents(data_dir))
    return out


def _build_external_documents(data_dir: Path) -> List[RetrievalDocument]:
    external_path = data_dir / "extra_docs.json"
    if not external_path.exists():
        return []

    payload = _load_json(external_path)
    rows = payload.get("documents", [])
    if not isinstance(rows, list):
        return []

    out: List[RetrievalDocument] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        title = str(row.get("title") or "Untitled external document")
        base_id = _external_doc_id(str(row.get("doc_id") or f"external-{idx}"), idx)
        source_type = str(row.get("source_type") or "external")
        source_url = row.get("url")
        file_path = row.get("file_path")

        chunks = _chunk_text(text)
        for chunk_idx, chunk in enumerate(chunks, start=1):
            out.append(
                RetrievalDocument(
                    doc_id=f"{base_id}:c{chunk_idx:02d}",
                    title=title,
                    text=chunk,
                    metadata={
                        "type": "external_doc",
                        "source_type": source_type,
                        "source_url": source_url,
                        "file_path": file_path,
                        "query": row.get("query"),
                        "tags": row.get("tags") or [],
                        "chunk": chunk_idx,
                    },
                )
            )
    return out


def _external_doc_id(raw_id: str, fallback_index: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9:_\-]+", "-", raw_id or "").strip("-").lower()
    if not slug:
        slug = f"external-{fallback_index}"
    return f"external:{slug[:64]}"


def _chunk_text(text: str, chunk_chars: int = 1400, overlap_chars: int = 220) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    step = max(300, chunk_chars - overlap_chars)
    size = len(cleaned)
    while start < size:
        end = min(size, start + chunk_chars)
        # Prefer to end on punctuation for readability.
        if end < size:
            punct = max(cleaned.rfind(". ", start, end), cleaned.rfind("; ", start, end))
            if punct > start + 240:
                end = punct + 1
        segment = cleaned[start:end].strip()
        if segment:
            chunks.append(segment)
        if end >= size:
            break
        start += step
    return chunks


def write_documents_jsonl(documents: Sequence[RetrievalDocument], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for doc in documents:
            fh.write(
                json.dumps(
                    {
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "text": doc.text,
                        "metadata": doc.metadata,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def load_documents_jsonl(path: Path) -> List[RetrievalDocument]:
    docs: List[RetrievalDocument] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        docs.append(
            RetrievalDocument(
                doc_id=str(row["doc_id"]),
                title=str(row.get("title") or ""),
                text=str(row.get("text") or ""),
                metadata=dict(row.get("metadata") or {}),
            )
        )
    return docs


def build_domain_keywords(documents: Iterable[RetrievalDocument], max_terms: int = 250) -> List[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "using",
        "part",
        "chapter",
        "paper",
        "title",
        "scope",
        "year",
        "toolkit",
        "learning",
    }
    counts: Counter[str] = Counter()
    for doc in documents:
        counts.update(tokenize(f"{doc.title} {doc.text}"))

    for s in stop:
        counts.pop(s, None)

    return [term for term, _ in counts.most_common(max_terms)]


class LexicalRetriever:
    def __init__(self, documents: Sequence[RetrievalDocument]):
        if not documents:
            raise ValueError("documents must not be empty")
        self.documents = list(documents)
        self._doc_tokens = [Counter(tokenize(f"{d.title}\n{d.text}")) for d in self.documents]
        self._idf = self._compute_idf(self._doc_tokens)

    @staticmethod
    def _compute_idf(doc_tokens: Sequence[Counter[str]]) -> Dict[str, float]:
        df: Counter[str] = Counter()
        total = len(doc_tokens)
        for tokens in doc_tokens:
            df.update(tokens.keys())
        return {
            term: math.log((1.0 + total) / (1.0 + freq)) + 1.0
            for term, freq in df.items()
        }

    def retrieve(self, query: str, top_k: int = 8) -> List[RetrievedChunk]:
        q_terms = tokenize(query)
        if not q_terms:
            return []
        q_counts = Counter(q_terms)
        results: List[RetrievedChunk] = []
        for doc, tf in zip(self.documents, self._doc_tokens):
            score = 0.0
            overlap: List[str] = []
            for term, qtf in q_counts.items():
                dtf = tf.get(term, 0)
                if not dtf:
                    continue
                overlap.append(term)
                idf = self._idf.get(term, 1.0)
                score += (1.0 + math.log(dtf)) * idf * qtf
            if score <= 0:
                continue
            norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
            results.append(
                RetrievedChunk(
                    document=doc,
                    score=score / norm,
                    matched_terms=sorted(set(overlap)),
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: max(1, top_k)]
