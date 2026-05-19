"""Shared constants and pure utility functions for the LE corpus build pipeline."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from html import unescape
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
DATA_DIR = ROOT / "data"
OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_TIMEOUT_SEC = 30.0
OPENALEX_SLEEP_SEC = 0.15
OPENALEX_BATCH_SIZE = 20
OPENALEX_MAX_RETRIES = 6
OPENALEX_SELECT_FIELDS = (
    "id,doi,display_name,abstract_inverted_index,authorships,"
    "publication_year,type,cited_by_count,primary_location,referenced_works"
)
OPENALEX_CACHE_PATH = CORPUS_DIR / "cache" / "openalex_works_cache.json"
CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_TIMEOUT_SEC = 30.0
CROSSREF_SLEEP_SEC = 0.12
CROSSREF_MAX_RETRIES = 4
CROSSREF_CACHE_PATH = CORPUS_DIR / "cache" / "crossref_abstract_cache.json"
ARXIV_BASE = "https://export.arxiv.org/api/query"
ARXIV_TIMEOUT_SEC = 25.0
ARXIV_SLEEP_SEC = 0.12
ARXIV_MAX_RETRIES = 4
ARXIV_CACHE_PATH = CORPUS_DIR / "cache" / "arxiv_abstract_cache.json"
URL_FETCH_TIMEOUT_SEC = _float_env("URL_FETCH_TIMEOUT_SEC", 30.0)
URL_FETCH_SLEEP_SEC = _float_env("URL_FETCH_SLEEP_SEC", 0.08)
URL_FETCH_MAX_RETRIES = _int_env("URL_FETCH_MAX_RETRIES", 4)
URL_ABSTRACT_CACHE_PATH = CORPUS_DIR / "cache" / "url_abstract_cache.json"
URL_PDF_ABSTRACT_CACHE_PATH = CORPUS_DIR / "cache" / "url_pdf_abstract_cache.json"
FULL_TEXT_CACHE_PATH = CORPUS_DIR / "cache" / "paper_full_text_cache.json"
FULL_TEXT_PROGRESS_LOG_PATH = CORPUS_DIR / "cache" / "full_text_progress.log"
FULL_TEXT_CACHE_MAX_CHARS = _int_env("FULL_TEXT_CACHE_MAX_CHARS", 180000)
FULL_TEXT_CACHE_MAX_PDF_PAGES = _int_env("FULL_TEXT_CACHE_MAX_PDF_PAGES", 0)
FULL_TEXT_CACHE_MIN_CHARS = _int_env("FULL_TEXT_CACHE_MIN_CHARS", 1200)


def load_dotenv_optional(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a repo `.env` file into `os.environ` only for keys not already set."""
    p = path or (ROOT / ".env")
    if not p.is_file():
        return
    raw = p.read_text(encoding="utf-8")
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        key, _, rest = s.partition("=")
        key = key.strip()
        if not key or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        val = rest.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if key not in os.environ:
            os.environ[key] = val


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_doi(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    text = text.replace("doi.org/", "").replace("DOI:", "").strip()
    return text


def to_work_id(openalex_id: str) -> str:
    text = (openalex_id or "").strip()
    if not text:
        return ""
    if text.startswith("W") and "/" not in text:
        return text
    return text.rstrip("/").split("/")[-1]


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def listify(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_authors(value: str) -> List[str]:
    text = (value or "").strip()
    if not text:
        return []
    if " and " in text and "," not in text:
        return [part.strip() for part in text.split(" and ") if part.strip()]
    return [text]


def normalize_url(value: str) -> str:
    text = (value or "").strip()
    if not text or text.lower() in {"[internal]", "internal", "n/a"}:
        return ""
    if text.startswith("www."):
        return f"https://{text}"
    return text


def doi_to_url(doi: str) -> str:
    doi = normalize_doi(doi)
    if not doi:
        return ""
    if doi.startswith("http://") or doi.startswith("https://"):
        return doi
    return f"https://doi.org/{doi}"


def citation_plain(title: str, authors: str, year, venue: str, doi: str) -> str:
    parts = []
    if authors:
        parts.append(authors)
    if year:
        parts.append(f"({year})")
    if title:
        parts.append(f"{title}.")
    if venue:
        parts.append(venue)
    if doi:
        parts.append(f"DOI: {doi}")
    return " ".join(parts).strip()


def citation_bibtex(key: str, title: str, authors: str, year, venue: str, doi: str) -> str:
    safe_key = (key or "resource").replace(" ", "_")
    lines = [f"@misc{{{safe_key},", f"  title = {{{title}}},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if venue:
        lines.append(f"  howpublished = {{{venue}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    lines.append("}")
    return "\n".join(lines)
