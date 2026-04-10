from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from html import unescape
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

from utils import (
    normalize_doi, to_work_id, chunked, load_json, write_json, doi_to_url,
    citation_plain, citation_bibtex,
    OPENALEX_BASE, OPENALEX_TIMEOUT_SEC, OPENALEX_SLEEP_SEC,
    OPENALEX_MAX_RETRIES, OPENALEX_SELECT_FIELDS, OPENALEX_CACHE_PATH,
    CROSSREF_BASE, CROSSREF_TIMEOUT_SEC, CROSSREF_SLEEP_SEC, CROSSREF_MAX_RETRIES,
    CROSSREF_CACHE_PATH,
    ARXIV_BASE, ARXIV_TIMEOUT_SEC, ARXIV_SLEEP_SEC, ARXIV_MAX_RETRIES, ARXIV_CACHE_PATH,
)


def api_get_json(path: str, params: Dict[str, str]) -> Dict:
    q = dict(params)
    mailto = (os.getenv("OPENALEX_MAILTO") or "").strip()
    if mailto and "mailto" not in q:
        q["mailto"] = mailto
    api_key = (os.getenv("OPENALEX_API_KEY") or os.getenv("OPENALEX_KEY") or "").strip()
    if api_key and "api_key" not in q:
        q["api_key"] = api_key

    url = f"{OPENALEX_BASE}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": "learning-engineering-resources/1.0"})

    last_error = None
    for attempt in range(OPENALEX_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=OPENALEX_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if OPENALEX_SLEEP_SEC > 0:
                time.sleep(OPENALEX_SLEEP_SEC)
            return data
        except urllib.error.HTTPError as exc:
            last_error = exc
            retriable = exc.code in {429, 500, 502, 503, 504}
            if not retriable or attempt >= OPENALEX_MAX_RETRIES:
                raise
            retry_after = 0.0
            if exc.headers:
                raw = exc.headers.get("Retry-After", "").strip()
                if raw:
                    try:
                        retry_after = float(raw)
                    except ValueError:
                        retry_after = 0.0
            wait_sec = retry_after if retry_after > 0 else min(2**attempt, 60)
            time.sleep(wait_sec)
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt >= OPENALEX_MAX_RETRIES:
                raise
            time.sleep(min(2**attempt, 30))

    raise RuntimeError(f"OpenAlex request failed after retries: {last_error}")


def normalize_title(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def score_openalex_candidate(paper: Dict, candidate: Dict) -> float:
    paper_title = normalize_title(paper.get("title", ""))
    cand_title = normalize_title(candidate.get("display_name", ""))
    if not paper_title or not cand_title:
        return 0.0

    score = SequenceMatcher(None, paper_title, cand_title).ratio()

    paper_year = paper.get("year")
    try:
        paper_year = int(paper_year) if paper_year is not None else None
    except Exception:
        paper_year = None
    cand_year = candidate.get("publication_year")
    if paper_year is not None and cand_year == paper_year:
        score += 0.10

    paper_doi = normalize_doi(paper.get("doi", ""))
    cand_doi = normalize_doi(candidate.get("doi", ""))
    if paper_doi and cand_doi and paper_doi == cand_doi:
        score += 0.25

    return score


def resolve_openalex_work_id_by_title(paper: Dict) -> str:
    title = (paper.get("title") or "").strip()
    if not title:
        return ""
    try:
        data = api_get_json(
            "/works",
            {"search": title, "per-page": "8", "select": "id,display_name,publication_year,doi"},
        )
    except Exception:
        return ""
    candidates = data.get("results", []) or []
    if not candidates:
        return ""

    best = None
    best_score = 0.0
    for candidate in candidates:
        score = score_openalex_candidate(paper, candidate)
        if score > best_score:
            best = candidate
            best_score = score

    if best is None or best_score < 0.72:
        return ""
    return to_work_id(best.get("id", ""))


def decode_abstract(index: Dict) -> str:
    if not isinstance(index, dict) or not index:
        return ""

    max_pos = -1
    for positions in index.values():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int) and pos > max_pos:
                max_pos = pos

    if max_pos < 0 or max_pos > 50000:
        return ""

    tokens = [""] * (max_pos + 1)
    for token, positions in index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int) and 0 <= pos <= max_pos and not tokens[pos]:
                tokens[pos] = str(token)

    text = " ".join(token for token in tokens if token).strip()
    if not text:
        return ""
    for punct in [",", ".", ";", ":", "?", "!", ")", "]", "}"]:
        text = text.replace(f" {punct}", punct)
    for punct in ["(", "[", "{"]:
        text = text.replace(f"{punct} ", punct)
    return text.strip()


def work_to_metadata(work: Dict) -> Dict:
    work_id = to_work_id(work.get("id", ""))
    doi = normalize_doi(work.get("doi", ""))

    authors: List[str] = []
    seen = set()
    for row in work.get("authorships", []) or []:
        name = ((row.get("author") or {}).get("display_name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            authors.append(name)

    venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name", "")
    if not venue:
        venue = ((work.get("host_venue") or {}).get("display_name") or "").strip()

    return {
        "work_id": work_id,
        "openalex_id": (work.get("id") or "").strip(),
        "doi": doi,
        "title": (work.get("display_name") or "").strip(),
        "abstract": decode_abstract(work.get("abstract_inverted_index")),
        "authors": authors,
        "year": work.get("publication_year"),
        "type": (work.get("type") or "").strip(),
        "cited_by_count": int(work.get("cited_by_count") or 0),
        "venue": (venue or "").strip(),
        "referenced_works": [to_work_id(ref) for ref in (work.get("referenced_works") or []) if to_work_id(ref)],
    }


def load_openalex_cache(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("works"), dict):
        return payload["works"]
    if isinstance(payload, dict):
        return payload
    return {}


def save_openalex_cache(path: Path, rows: Dict[str, Dict]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "works": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def strip_tags(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_crossref_cache(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("abstracts"), dict):
        return payload["abstracts"]
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if isinstance(v, str)}
    return {}


def save_crossref_cache(path: Path, rows: Dict[str, str]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "abstracts": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def crossref_get_abstract(doi: str) -> str:
    norm_doi = normalize_doi(doi)
    if not norm_doi:
        return ""
    quoted_doi = urllib.parse.quote(norm_doi, safe="")
    url = f"{CROSSREF_BASE}/works/{quoted_doi}"
    mailto = (os.getenv("OPENALEX_MAILTO") or "").strip()
    if mailto:
        url = f"{url}?mailto={urllib.parse.quote(mailto, safe='')}"

    req = urllib.request.Request(url, headers={"User-Agent": "learning-engineering-resources/1.0"})
    last_error = None
    for attempt in range(CROSSREF_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=CROSSREF_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            message = data.get("message") or {}
            abstract = strip_tags(message.get("abstract", ""))
            if CROSSREF_SLEEP_SEC > 0:
                time.sleep(CROSSREF_SLEEP_SEC)
            return abstract
        except urllib.error.HTTPError as exc:
            last_error = exc
            retriable = exc.code in {429, 500, 502, 503, 504}
            if exc.code in {404, 400}:
                return ""
            if not retriable or attempt >= CROSSREF_MAX_RETRIES:
                return ""
            retry_after = 0.0
            if exc.headers:
                raw = exc.headers.get("Retry-After", "").strip()
                if raw:
                    try:
                        retry_after = float(raw)
                    except ValueError:
                        retry_after = 0.0
            wait_sec = retry_after if retry_after > 0 else min(2**attempt, 30)
            time.sleep(wait_sec)
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt >= CROSSREF_MAX_RETRIES:
                return ""
            time.sleep(min(2**attempt, 20))

    if last_error:
        return ""
    return ""


def enrich_missing_abstracts_from_crossref(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    papers = seed_papers + hop_papers
    missing = [p for p in papers if not (p.get("abstract") or "").strip()]
    doi_set = sorted({normalize_doi(p.get("doi", "")) for p in missing if normalize_doi(p.get("doi", ""))})

    cache = load_crossref_cache(CROSSREF_CACHE_PATH)
    fetched = 0
    for doi in doi_set:
        if doi in cache:
            continue
        abstract = crossref_get_abstract(doi)
        cache[doi] = abstract
        fetched += 1
    if fetched:
        save_crossref_cache(CROSSREF_CACHE_PATH, cache)

    filled = 0
    for paper in missing:
        doi = normalize_doi(paper.get("doi", ""))
        if not doi:
            continue
        abstract = (cache.get(doi) or "").strip()
        if abstract and not (paper.get("abstract") or "").strip():
            paper["abstract"] = abstract
            paper["abstract_source"] = "crossref"
            paper["abstract_is_proxy"] = False
            filled += 1

    remaining_missing = sum(1 for p in papers if not (p.get("abstract") or "").strip())
    return {
        "crossref_doi_candidates": len(doi_set),
        "crossref_doi_fetched": fetched,
        "crossref_abstracts_filled": filled,
        "papers_missing_abstract_after_crossref": remaining_missing,
    }


def load_arxiv_cache(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("abstracts"), dict):
        return payload["abstracts"]
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if isinstance(v, str)}
    return {}


def save_arxiv_cache(path: Path, rows: Dict[str, str]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "abstracts": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def extract_arxiv_id(paper: Dict) -> str:
    candidates = [
        normalize_doi(paper.get("doi", "")),
        (paper.get("id") or "").strip(),
        (paper.get("openalex_id") or "").strip(),
    ]
    for value in candidates:
        text = (value or "").strip()
        if not text:
            continue
        text = text.replace("arxiv:", "").replace("ArXiv:", "").strip()
        match = re.search(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b", text)
        if match:
            return match.group(1)
    return ""


def arxiv_get_abstract(arxiv_id: str) -> str:
    if not arxiv_id:
        return ""
    params = {"search_query": f"id:{arxiv_id}", "start": "0", "max_results": "1"}
    url = f"{ARXIV_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "learning-engineering-resources/1.0"})
    for attempt in range(ARXIV_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=ARXIV_TIMEOUT_SEC) as resp:
                xml_text = resp.read().decode("utf-8", errors="ignore")
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find("atom:entry", ns)
            if entry is None:
                return ""
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            summary = re.sub(r"\s+", " ", summary)
            if ARXIV_SLEEP_SEC > 0:
                time.sleep(ARXIV_SLEEP_SEC)
            return summary
        except Exception:
            if attempt >= ARXIV_MAX_RETRIES:
                return ""
            time.sleep(min(2**attempt, 20))
    return ""


def enrich_missing_abstracts_from_arxiv(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    papers = seed_papers + hop_papers
    missing = [p for p in papers if not (p.get("abstract") or "").strip()]
    arxiv_ids = sorted({extract_arxiv_id(p) for p in missing if extract_arxiv_id(p)})

    cache = load_arxiv_cache(ARXIV_CACHE_PATH)
    fetched = 0
    for arxiv_id in arxiv_ids:
        if arxiv_id in cache:
            continue
        cache[arxiv_id] = arxiv_get_abstract(arxiv_id)
        fetched += 1
    if fetched:
        save_arxiv_cache(ARXIV_CACHE_PATH, cache)

    filled = 0
    for paper in missing:
        arxiv_id = extract_arxiv_id(paper)
        if not arxiv_id:
            continue
        abstract = (cache.get(arxiv_id) or "").strip()
        if abstract and not (paper.get("abstract") or "").strip():
            paper["abstract"] = abstract
            paper["abstract_source"] = "arxiv"
            paper["abstract_is_proxy"] = False
            filled += 1

    remaining_missing = sum(1 for p in papers if not (p.get("abstract") or "").strip())
    return {
        "arxiv_candidates": len(arxiv_ids),
        "arxiv_fetched": fetched,
        "arxiv_abstracts_filled": filled,
        "papers_missing_abstract_after_arxiv": remaining_missing,
    }
