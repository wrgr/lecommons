from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from html import unescape
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, TextIO, Tuple

from utils import (
    normalize_doi, to_work_id, load_json, write_json, doi_to_url,
    citation_plain, citation_bibtex, listify,
    OPENALEX_CACHE_PATH, OPENALEX_SELECT_FIELDS,
    URL_FETCH_TIMEOUT_SEC, URL_FETCH_SLEEP_SEC, URL_FETCH_MAX_RETRIES,
    URL_ABSTRACT_CACHE_PATH, URL_PDF_ABSTRACT_CACHE_PATH,
    FULL_TEXT_CACHE_PATH, FULL_TEXT_PROGRESS_LOG_PATH, FULL_TEXT_CACHE_MAX_CHARS, FULL_TEXT_CACHE_MAX_PDF_PAGES, FULL_TEXT_CACHE_MIN_CHARS,
    CORPUS_DIR,
)
from openalex_client import (
    api_get_json,
    load_openalex_cache,
    save_openalex_cache,
    work_to_metadata,
    resolve_openalex_work_id_by_title,
    enrich_missing_abstracts_from_crossref,
    enrich_missing_abstracts_from_arxiv,
    strip_tags,
)

USER_AGENT = "learning-engineering-resources/1.0"


def _curl_available() -> bool:
    return shutil.which("curl") is not None


def _curl_fetch_headers(url: str) -> str:
    if not url or not _curl_available():
        return ""
    timeout_sec = max(int(URL_FETCH_TIMEOUT_SEC), 1)
    try:
        return subprocess.check_output(
            ["curl", "-sS", "-L", "-I", "--max-time", str(timeout_sec), "-A", USER_AGENT, url],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""


def _curl_content_type(url: str) -> str:
    headers = _curl_fetch_headers(url)
    if not headers:
        return ""
    matches = re.findall(r"(?im)^content-type:\s*([^\r\n;]+)", headers)
    if not matches:
        return ""
    return matches[-1].strip().lower()


def _curl_fetch_bytes(url: str) -> bytes:
    if not url or not _curl_available():
        return b""
    timeout_sec = max(int(URL_FETCH_TIMEOUT_SEC), 1)
    try:
        return subprocess.check_output(
            ["curl", "-sS", "-L", "--max-time", str(timeout_sec), "-A", USER_AGENT, url],
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return b""


def load_url_abstract_cache(path: Path) -> Dict[str, str]:
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


def save_url_abstract_cache(path: Path, rows: Dict[str, str]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "abstracts": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def load_url_pdf_abstract_cache(path: Path) -> Dict[str, str]:
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


def save_url_pdf_abstract_cache(path: Path, rows: Dict[str, str]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "abstracts": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def load_full_text_cache(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("papers"), dict):
        out: Dict[str, Dict] = {}
        for key, value in payload["papers"].items():
            if isinstance(value, dict):
                out[str(key)] = value
        return out
    if isinstance(payload, dict):
        out: Dict[str, Dict] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                out[str(key)] = {"text": value}
            elif isinstance(value, dict):
                out[str(key)] = value
        return out
    return {}


def save_full_text_cache(path: Path, rows: Dict[str, Dict]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "papers": rows,
        "count": len(rows),
    }
    write_json(path, payload)


def looks_abstract_like(text: str) -> bool:
    if not text:
        return False
    t = " ".join(text.split())
    if len(t) < 80 or len(t) > 7000:
        return False
    low = t.lower()
    bad_snippets = [
        "cookie",
        "all rights reserved",
        "log in",
        "sign in",
        "javascript is disabled",
        "no abstract available",
    ]
    if any(s in low for s in bad_snippets):
        return False
    return True


def looks_pdf_abstract_like(text: str) -> bool:
    if not looks_abstract_like(text):
        return False
    t = " ".join(text.split())
    if len(t) < 120 or len(t) > 2800:
        return False
    alpha = sum(1 for ch in t if ch.isalpha())
    if alpha < 90:
        return False
    digit_ratio = sum(1 for ch in t if ch.isdigit()) / max(len(t), 1)
    if digit_ratio > 0.16:
        return False
    return True


def fetch_url_html(url: str) -> str:
    if not url:
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(URL_FETCH_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=URL_FETCH_TIMEOUT_SEC) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                if "html" not in content_type and "xml" not in content_type:
                    return ""
                body = resp.read().decode("utf-8", errors="ignore")
            if URL_FETCH_SLEEP_SEC > 0:
                time.sleep(URL_FETCH_SLEEP_SEC)
            return body
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 404, 410}:
                return ""
            if attempt >= URL_FETCH_MAX_RETRIES:
                return ""
            time.sleep(min(2**attempt, 20))
        except urllib.error.URLError:
            if attempt >= URL_FETCH_MAX_RETRIES:
                break
            time.sleep(min(2**attempt, 20))
    content_type = _curl_content_type(url)
    if "html" not in content_type and "xml" not in content_type:
        return ""
    body = _curl_fetch_bytes(url)
    if not body:
        return ""
    return body.decode("utf-8", errors="ignore")


def discover_pdf_urls_from_html(html: str, base_url: str) -> List[str]:
    urls: List[str] = []
    if not html:
        return urls

    meta_match = re.search(
        r"""<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["'](.*?)["']""",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if meta_match:
        value = (meta_match.group(1) or "").strip()
        if value:
            urls.append(urllib.parse.urljoin(base_url, value))

    hrefs = re.findall(r'href=["\'](.*?)["\']', html, flags=re.IGNORECASE | re.DOTALL)
    for href in hrefs:
        value = (href or "").strip()
        if not value:
            continue
        low = value.lower()
        if ".pdf" in low or "/pdf/" in low:
            urls.append(urllib.parse.urljoin(base_url, value))

    out: List[str] = []
    seen: Set[str] = set()
    for url in urls:
        normalized = url.split("#", 1)[0]
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def fetch_pdf_bytes(url: str) -> bytes:
    if not url:
        return b""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(URL_FETCH_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=URL_FETCH_TIMEOUT_SEC) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                body = resp.read()
            if URL_FETCH_SLEEP_SEC > 0:
                time.sleep(URL_FETCH_SLEEP_SEC)
            if not body:
                return b""
            looks_pdf = body.startswith(b"%PDF") or "pdf" in content_type or url.lower().endswith(".pdf")
            return body if looks_pdf else b""
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 404, 410}:
                return b""
            if attempt >= URL_FETCH_MAX_RETRIES:
                return b""
            time.sleep(min(2**attempt, 20))
        except urllib.error.URLError:
            if attempt >= URL_FETCH_MAX_RETRIES:
                break
            time.sleep(min(2**attempt, 20))
    content_type = _curl_content_type(url)
    body = _curl_fetch_bytes(url)
    if not body:
        return b""
    looks_pdf = body.startswith(b"%PDF") or "pdf" in content_type or url.lower().endswith(".pdf")
    return body if looks_pdf else b""


def _pdftotext_from_bytes(pdf_bytes: bytes, first_page: int = 1, last_page: int = 0) -> str:
    if not pdf_bytes:
        return ""
    args = ["pdftotext", "-enc", "UTF-8"]
    if first_page > 0:
        args.extend(["-f", str(first_page)])
    if last_page > 0:
        args.extend(["-l", str(last_page)])
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as infile:
            infile.write(pdf_bytes)
            infile.flush()
            out = subprocess.check_output(
                [*args, infile.name, "-"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        return ""
    return out or ""


def _normalize_text(text: str, max_chars: int) -> Tuple[str, bool]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return "", False
    if max_chars > 0 and len(normalized) > max_chars:
        return normalized[:max_chars].rstrip(), True
    return normalized, False


def _looks_full_text_like(text: str) -> bool:
    if not text:
        return False
    t = " ".join(text.split())
    if len(t) < FULL_TEXT_CACHE_MIN_CHARS:
        return False
    low = t.lower()
    bad_snippets = [
        "javascript is disabled",
        "enable cookies",
        "access denied",
        "cloudflare",
        "captcha",
    ]
    if any(s in low for s in bad_snippets):
        return False
    alpha = sum(1 for ch in t if ch.isalpha())
    if alpha < 700:
        return False
    return True


def extract_full_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, bool]:
    if FULL_TEXT_CACHE_MAX_PDF_PAGES > 0:
        raw = _pdftotext_from_bytes(pdf_bytes, first_page=1, last_page=FULL_TEXT_CACHE_MAX_PDF_PAGES)
    else:
        raw = _pdftotext_from_bytes(pdf_bytes, first_page=1, last_page=0)
    text, truncated = _normalize_text(raw, FULL_TEXT_CACHE_MAX_CHARS)
    if not _looks_full_text_like(text):
        return "", False
    return text, truncated


def extract_full_text_from_html(html: str) -> Tuple[str, bool]:
    if not html:
        return "", False
    cleaned = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    text, truncated = _normalize_text(cleaned, FULL_TEXT_CACHE_MAX_CHARS)
    if not _looks_full_text_like(text):
        return "", False
    return text, truncated


def extract_candidate_abstract_from_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""

    pattern = re.compile(
        r"\babstract\b\s*[:.-]?\s*(.+?)(?:\bkeywords?\b\s*[:-]|(?:\b1\b\s*[.)-]?\s*introduction\b)|\bintroduction\b)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(cleaned)
    if match:
        candidate = " ".join(match.group(1).split())
        if looks_pdf_abstract_like(candidate):
            return candidate

    if cleaned.lower().startswith("abstract"):
        candidate = cleaned[8:].strip(" .:-")
        if looks_pdf_abstract_like(candidate):
            return candidate

    return ""


def extract_abstract_from_pdf_bytes(pdf_bytes: bytes) -> str:
    out = _pdftotext_from_bytes(pdf_bytes, first_page=1, last_page=3)
    return extract_candidate_abstract_from_text(out)


def parse_jsonld_abstract(html: str) -> str:
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for script in scripts:
        text = script.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        queue = payload if isinstance(payload, list) else [payload]
        while queue:
            item = queue.pop(0)
            if isinstance(item, dict):
                if isinstance(item.get("abstract"), str):
                    candidate = strip_tags(item.get("abstract", ""))
                    if looks_abstract_like(candidate):
                        return candidate
                if isinstance(item.get("description"), str):
                    candidate = strip_tags(item.get("description", ""))
                    if looks_abstract_like(candidate):
                        return candidate
                for value in item.values():
                    if isinstance(value, (dict, list)):
                        queue.append(value)
            elif isinstance(item, list):
                queue.extend(item)
    return ""


def extract_abstract_from_html(html: str, url: str) -> str:
    if not html:
        return ""

    meta_patterns = [
        r'<meta[^>]+name=["\']citation_abstract["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']dc\.description["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    ]
    for pattern in meta_patterns:
        m = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        candidate = strip_tags(m.group(1))
        if looks_abstract_like(candidate):
            return candidate

    jsonld = parse_jsonld_abstract(html)
    if jsonld:
        return jsonld

    if "arxiv.org" in (url or ""):
        m = re.search(r'<blockquote[^>]*class=["\'][^"\']abstract[^"\']["\'][^>]*>(.*?)</blockquote>', html, flags=re.IGNORECASE | re.DOTALL)
        if m:
            text = strip_tags(m.group(1)).replace("Abstract:", "").strip()
            if looks_abstract_like(text):
                return text

    return ""


def candidate_urls_for_paper(paper: Dict) -> List[str]:
    urls = []
    source_url = (paper.get("source_url") or "").strip()
    doi = normalize_doi(paper.get("doi", ""))
    openalex_id = (paper.get("openalex_id") or "").strip()
    if source_url:
        urls.append(source_url)
    if doi:
        doi_url = doi_to_url(doi)
        if doi_url and doi_url not in urls:
            urls.append(doi_url)
    if openalex_id and openalex_id not in urls:
        urls.append(openalex_id)
    return urls


def empty_full_text_cache_stats() -> Dict[str, int]:
    return {
        "full_text_cache_candidates": 0,
        "full_text_cache_hits": 0,
        "full_text_urls_checked": 0,
        "full_text_pdf_fetches": 0,
        "full_text_html_fetches": 0,
        "full_text_cached_new": 0,
        "full_text_cache_refreshed": 0,
        "full_text_cache_failures": 0,
        "full_text_text_truncated": 0,
        "full_text_cache_total_entries": 0,
        "papers_with_cached_full_text": 0,
        "papers_without_cached_full_text": 0,
    }


def _emit_full_text_progress(line: str, log_file: Optional[TextIO]) -> None:
    print(line, flush=True)
    if log_file is not None:
        log_file.write(line + "\n")
        log_file.flush()


def _paper_full_text_cache_key(paper: Dict, fallback_index: int) -> str:
    pid = (paper.get("id") or "").strip()
    if pid:
        return f"id:{pid}"
    doi = normalize_doi(paper.get("doi", ""))
    if doi:
        return f"doi:{doi.lower()}"
    src = (paper.get("source_url") or paper.get("openalex_id") or "").strip()
    if src:
        return f"url:{src}"
    return f"row:{fallback_index}"


def _paper_id_for_entry(paper: Dict, fallback_index: int) -> str:
    pid = (paper.get("id") or "").strip()
    if pid:
        return pid
    doi = normalize_doi(paper.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    return f"row:{fallback_index}"


def prime_full_text_cache(
    seed_papers: List[Dict],
    hop_papers: List[Dict],
    *,
    max_papers: int = 0,
    refresh: bool = False,
) -> Dict[str, int]:
    papers = seed_papers + hop_papers
    if max_papers > 0:
        papers = papers[:max_papers]

    total = len(papers)
    stats = empty_full_text_cache_stats()
    stats["full_text_cache_candidates"] = total
    cache = load_full_text_cache(FULL_TEXT_CACHE_PATH)
    cache_mutated = False
    progress_log: Optional[TextIO] = None
    try:
        FULL_TEXT_PROGRESS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        progress_log = FULL_TEXT_PROGRESS_LOG_PATH.open("w", encoding="utf-8")
        progress_log.write(
            f"# full-text progress started {datetime.now(timezone.utc).isoformat()} candidates={total}\n"
        )
        progress_log.flush()
    except Exception:
        progress_log = None

    for idx, paper in enumerate(papers, start=1):
        paper_id = _paper_id_for_entry(paper, idx)
        paper_title = (paper.get("title") or "").strip() or "Untitled"
        cache_key = _paper_full_text_cache_key(paper, idx)
        existing = cache.get(cache_key) if isinstance(cache.get(cache_key), dict) else None
        if existing and not refresh and ((existing.get("text") or "").strip() or existing.get("status") == "unavailable"):
            stats["full_text_cache_hits"] += 1
            _emit_full_text_progress(
                f"[full-text] {idx}/{total} cache_hit {paper_id} | {paper_title}",
                progress_log,
            )
            continue

        urls = [u for u in candidate_urls_for_paper(paper) if u.startswith(("http://", "https://"))]
        urls = list(dict.fromkeys(urls))
        stats["full_text_urls_checked"] += len(urls)

        best_text = ""
        best_source_url = ""
        best_source_type = ""
        was_truncated = False

        for url in urls:
            if best_text:
                break

            url_low = url.lower()
            html = ""
            tried_direct_pdf = False

            # Some DOI or publisher links resolve directly to a PDF even when the URL
            # does not end with ".pdf". Try direct PDF extraction first for likely cases.
            if url_low.endswith(".pdf") or "doi.org/" in url_low or "/pdf/" in url_low or "arxiv.org/pdf/" in url_low:
                stats["full_text_pdf_fetches"] += 1
                tried_direct_pdf = True
                pdf_bytes = fetch_pdf_bytes(url)
                if pdf_bytes:
                    text, truncated = extract_full_text_from_pdf_bytes(pdf_bytes)
                    if text:
                        best_text = text
                        best_source_url = url
                        best_source_type = "pdf"
                        was_truncated = truncated
                        break

            if best_text:
                break

            html = fetch_url_html(url)
            if html:
                stats["full_text_html_fetches"] += 1
            elif not tried_direct_pdf:
                # Fallback: when HTML fetch yields nothing, the URL may still be
                # serving binary PDF content behind a non-obvious path.
                stats["full_text_pdf_fetches"] += 1
                pdf_bytes = fetch_pdf_bytes(url)
                if pdf_bytes:
                    text, truncated = extract_full_text_from_pdf_bytes(pdf_bytes)
                    if text:
                        best_text = text
                        best_source_url = url
                        best_source_type = "pdf"
                        was_truncated = truncated
                        break

            if not html:
                continue

            pdf_urls = discover_pdf_urls_from_html(html, url)
            for pdf_url in pdf_urls:
                stats["full_text_pdf_fetches"] += 1
                pdf_bytes = fetch_pdf_bytes(pdf_url)
                if not pdf_bytes:
                    continue
                text, truncated = extract_full_text_from_pdf_bytes(pdf_bytes)
                if text:
                    best_text = text
                    best_source_url = pdf_url
                    best_source_type = "pdf"
                    was_truncated = truncated
                    break
            if best_text:
                break

            html_text, truncated = extract_full_text_from_html(html)
            if html_text:
                best_text = html_text
                best_source_url = url
                best_source_type = "html"
                was_truncated = truncated
                break

        now = datetime.now(timezone.utc).isoformat()
        if best_text:
            if was_truncated:
                stats["full_text_text_truncated"] += 1
            cache[cache_key] = {
                "paper_id": paper_id,
                "title": paper_title,
                "scope": (paper.get("scope") or "").strip(),
                "doi": normalize_doi(paper.get("doi", "")),
                "source_url": best_source_url,
                "source_type": best_source_type,
                "char_count": len(best_text),
                "truncated": was_truncated,
                "status": "ok",
                "updated_at_utc": now,
                "text": best_text,
            }
            if existing and refresh:
                stats["full_text_cache_refreshed"] += 1
                event = "refreshed"
            else:
                stats["full_text_cached_new"] += 1
                event = "cached"
            cache_mutated = True
            save_full_text_cache(FULL_TEXT_CACHE_PATH, cache)
            _emit_full_text_progress(
                f"[full-text] {idx}/{total} {event} {paper_id} | chars={len(best_text)} | source={best_source_type} | {paper_title}",
                progress_log,
            )
        else:
            cache[cache_key] = {
                "paper_id": paper_id,
                "title": paper_title,
                "scope": (paper.get("scope") or "").strip(),
                "doi": normalize_doi(paper.get("doi", "")),
                "status": "unavailable",
                "updated_at_utc": now,
                "attempted_urls": urls,
                "text": "",
            }
            stats["full_text_cache_failures"] += 1
            cache_mutated = True
            save_full_text_cache(FULL_TEXT_CACHE_PATH, cache)
            _emit_full_text_progress(
                f"[full-text] {idx}/{total} unavailable {paper_id} | urls={len(urls)} | {paper_title}",
                progress_log,
            )

    if cache_mutated:
        save_full_text_cache(FULL_TEXT_CACHE_PATH, cache)
    if progress_log is not None:
        progress_log.write(
            f"# full-text progress completed {datetime.now(timezone.utc).isoformat()} total_entries={len(cache)}\n"
        )
        progress_log.flush()
        progress_log.close()
    stats["full_text_cache_total_entries"] = len(cache)
    return stats


def _excerpt_for_display(text: str, max_chars: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return ""
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "\u2026"


def annotate_papers_with_full_text_cache(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict[str, int]:
    cache = load_full_text_cache(FULL_TEXT_CACHE_PATH)
    by_paper_id: Dict[str, Dict] = {}
    by_doi: Dict[str, Dict] = {}
    for entry in cache.values():
        if not isinstance(entry, dict):
            continue
        status = (entry.get("status") or "").strip()
        text = (entry.get("text") or "").strip()
        if status != "ok" or not text:
            continue
        pid = (entry.get("paper_id") or "").strip()
        doi = normalize_doi(entry.get("doi", ""))
        if pid:
            by_paper_id[pid] = entry
        if doi:
            by_doi[doi] = entry

    papers = seed_papers + hop_papers
    cached_count = 0
    for paper in papers:
        pid = (paper.get("id") or "").strip()
        doi = normalize_doi(paper.get("doi", ""))
        entry = by_paper_id.get(pid) or by_doi.get(doi)
        if entry:
            text = (entry.get("text") or "").strip()
            paper["full_text_cached"] = True
            paper["full_text_char_count"] = int(entry.get("char_count") or len(text))
            paper["full_text_source_url"] = (entry.get("source_url") or "").strip()
            paper["full_text_source_type"] = (entry.get("source_type") or "").strip()
            paper["full_text_excerpt"] = _excerpt_for_display(text)
            cached_count += 1
        else:
            paper["full_text_cached"] = False
            paper["full_text_char_count"] = 0
            paper["full_text_source_url"] = ""
            paper["full_text_source_type"] = ""
            paper["full_text_excerpt"] = ""

    return {
        "papers_with_cached_full_text": cached_count,
        "papers_without_cached_full_text": max(len(papers) - cached_count, 0),
        "full_text_cache_total_entries": len(cache),
    }


def enrich_missing_abstracts_from_urls(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    papers = seed_papers + hop_papers
    missing = [p for p in papers if not (p.get("abstract") or "").strip()]

    cache = load_url_abstract_cache(URL_ABSTRACT_CACHE_PATH)
    pdf_cache = load_url_pdf_abstract_cache(URL_PDF_ABSTRACT_CACHE_PATH)
    fetched = 0
    filled = 0
    urls_checked = 0
    pdf_urls_checked = 0
    pdf_urls_fetched = 0
    pdf_abstracts_filled = 0

    for paper in missing:
        for url in candidate_urls_for_paper(paper):
            if (paper.get("abstract") or "").strip():
                break
            urls_checked += 1
            if url not in cache:
                html = fetch_url_html(url)
                cache[url] = extract_abstract_from_html(html, url) if html else ""
                fetched += 1
            else:
                html = fetch_url_html(url) if (cache.get(url, "") == "" and url.startswith(("http://", "https://"))) else ""
            candidate = (cache.get(url) or "").strip()
            if candidate and not (paper.get("abstract") or "").strip():
                paper["abstract"] = candidate
                paper["abstract_source"] = "url_meta"
                paper["abstract_is_proxy"] = False
                filled += 1
                break

            if (paper.get("abstract") or "").strip():
                break

            pdf_urls: List[str] = []
            if url.lower().endswith(".pdf"):
                pdf_urls.append(url)
            else:
                pdf_urls.append(url)
            if html:
                pdf_urls.extend(discover_pdf_urls_from_html(html, url))

            seen_pdf: Set[str] = set()
            for pdf_url in pdf_urls:
                if (paper.get("abstract") or "").strip():
                    break
                normalized_pdf = pdf_url.split("#", 1)[0]
                if normalized_pdf in seen_pdf:
                    continue
                seen_pdf.add(normalized_pdf)
                pdf_urls_checked += 1
                if normalized_pdf not in pdf_cache:
                    pdf_bytes = fetch_pdf_bytes(normalized_pdf)
                    pdf_cache[normalized_pdf] = extract_abstract_from_pdf_bytes(pdf_bytes) if pdf_bytes else ""
                    pdf_urls_fetched += 1
                pdf_candidate = (pdf_cache.get(normalized_pdf) or "").strip()
                if pdf_candidate and not (paper.get("abstract") or "").strip():
                    paper["abstract"] = pdf_candidate
                    paper["abstract_source"] = "url_pdf"
                    paper["abstract_is_proxy"] = False
                    filled += 1
                    pdf_abstracts_filled += 1
                    break

    if fetched:
        save_url_abstract_cache(URL_ABSTRACT_CACHE_PATH, cache)
    if pdf_urls_fetched:
        save_url_pdf_abstract_cache(URL_PDF_ABSTRACT_CACHE_PATH, pdf_cache)

    remaining_missing = sum(1 for p in papers if not (p.get("abstract") or "").strip())
    return {
        "url_abstract_urls_checked": urls_checked,
        "url_abstract_urls_fetched": fetched,
        "url_abstracts_filled": filled,
        "url_pdf_urls_checked": pdf_urls_checked,
        "url_pdf_urls_fetched": pdf_urls_fetched,
        "url_pdf_abstracts_filled": pdf_abstracts_filled,
        "papers_missing_abstract_after_url_fallback": remaining_missing,
    }


def build_proxy_description(paper: Dict) -> str:
    title = (paper.get("title") or "Untitled work").strip()
    work_type = (paper.get("type") or "scholarly work").replace("-", " ").strip()
    year = paper.get("year")
    venue = (paper.get("venue") or "").strip()
    topics = paper.get("topic_codes") or []
    topic_text = ", ".join(topics[:4]) if topics else "unmapped topics"
    scope = "seed corpus" if paper.get("scope") == "seed" else "one-hop expansion set"

    pieces = [f'Description proxy (no source abstract available): "{title}"']
    pieces.append(f"is included as a {work_type} in the {scope}.")
    if year:
        pieces.append(f"Publication year: {year}.")
    if venue:
        pieces.append(f"Venue/source: {venue}.")
    pieces.append(f"Topic mapping: {topic_text}.")

    source = doi_to_url(normalize_doi(paper.get("doi", ""))) or (paper.get("source_url") or "").strip() or (
        paper.get("openalex_id") or ""
    )
    if source:
        pieces.append(f"Reference URL: {source}.")
    return " ".join(piece for piece in pieces if piece).strip()


def fill_proxy_descriptions(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    papers = seed_papers + hop_papers
    filled = 0
    for paper in papers:
        if (paper.get("abstract") or "").strip():
            continue
        paper["abstract"] = build_proxy_description(paper)
        paper["abstract_source"] = "proxy_description"
        paper["abstract_is_proxy"] = True
        filled += 1

    remaining_missing = sum(1 for p in papers if not (p.get("abstract") or "").strip())
    return {
        "proxy_descriptions_filled": filled,
        "papers_missing_abstract_after_proxy": remaining_missing,
    }


def fetch_openalex_metadata(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict[str, Dict]:
    papers = seed_papers + hop_papers
    cache = load_openalex_cache(OPENALEX_CACHE_PATH)

    work_ids_needed: Set[str] = set()
    dois_needed: Set[str] = set()

    for paper in papers:
        work_id = to_work_id(paper.get("openalex_id", "")) or (
            paper.get("id", "") if str(paper.get("id", "")).startswith("W") else ""
        )
        doi = normalize_doi(paper.get("doi", ""))
        if work_id and work_id not in cache:
            work_ids_needed.add(work_id)
        if doi:
            dois_needed.add(doi)

    fetched = 0

    for work_id in sorted(work_ids_needed):
        try:
            work = api_get_json(
                f"/works/{work_id}",
                {"select": OPENALEX_SELECT_FIELDS},
            )
        except Exception as exc:
            print(f"[warn] OpenAlex work fetch failed for {work_id}: {exc}")
            continue
        meta = work_to_metadata(work)
        if meta["work_id"]:
            cache[meta["work_id"]] = meta
            fetched += 1

    doi_to_work_id = {meta.get("doi"): wid for wid, meta in cache.items() if meta.get("doi")}
    for doi in sorted(dois_needed):
        if doi in doi_to_work_id:
            continue
        try:
            data = api_get_json(
                "/works",
                {"filter": f"doi:{doi}", "per-page": "1", "select": OPENALEX_SELECT_FIELDS},
            )
        except Exception as exc:
            print(f"[warn] OpenAlex DOI fetch failed for {doi}: {exc}")
            continue
        results = data.get("results", [])
        if not results:
            continue
        meta = work_to_metadata(results[0])
        if meta["work_id"]:
            cache[meta["work_id"]] = meta
            doi_to_work_id[doi] = meta["work_id"]
            fetched += 1

    if fetched:
        save_openalex_cache(OPENALEX_CACHE_PATH, cache)

    return cache


def enrich_papers_with_openalex(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    papers = seed_papers + hop_papers
    metadata_by_work_id = fetch_openalex_metadata(seed_papers, hop_papers)
    metadata_by_doi = {
        meta["doi"]: meta for meta in metadata_by_work_id.values() if isinstance(meta, dict) and meta.get("doi")
    }

    def refresh_metadata_by_doi() -> None:
        metadata_by_doi.clear()
        metadata_by_doi.update(
            {meta["doi"]: meta for meta in metadata_by_work_id.values() if isinstance(meta, dict) and meta.get("doi")}
        )

    def apply_meta(paper: Dict, meta: Dict) -> bool:
        abstract_filled = False
        if not paper.get("openalex_id") and meta.get("openalex_id"):
            paper["openalex_id"] = meta["openalex_id"]
        if (not paper.get("title") or paper.get("title", "").strip().lower() == "untitled") and meta.get("title"):
            paper["title"] = meta["title"]
        if not paper.get("abstract") and meta.get("abstract"):
            paper["abstract"] = meta["abstract"]
            paper["abstract_source"] = "openalex"
            paper["abstract_is_proxy"] = False
            abstract_filled = True
        if not paper.get("authors") and meta.get("authors"):
            paper["authors"] = meta["authors"]
        if not paper.get("year") and meta.get("year"):
            paper["year"] = meta["year"]
        if not paper.get("doi") and meta.get("doi"):
            paper["doi"] = meta["doi"]
        if not paper.get("type") and meta.get("type"):
            paper["type"] = meta["type"]
        if (not paper.get("cited_by_count")) and meta.get("cited_by_count"):
            paper["cited_by_count"] = meta["cited_by_count"]
        if not paper.get("referenced_works") and meta.get("referenced_works"):
            paper["referenced_works"] = meta["referenced_works"]
        if not paper.get("venue") and meta.get("venue"):
            paper["venue"] = meta["venue"]

        authors_text = ", ".join(paper.get("authors", []))
        venue_text = (paper.get("venue") or "").strip()
        doi_text = normalize_doi(paper.get("doi", ""))
        paper["citation_plain"] = citation_plain(
            paper.get("title", ""),
            authors_text,
            paper.get("year"),
            venue_text,
            doi_text,
        )
        paper["citation_bibtex"] = citation_bibtex(
            paper.get("id", "resource"),
            paper.get("title", ""),
            authors_text,
            paper.get("year"),
            venue_text,
            doi_text,
        )
        paper["source_url"] = doi_to_url(doi_text) or paper.get("openalex_id", "")
        return abstract_filled

    total = len(papers)
    enriched = 0
    abstracts_filled = 0
    unresolved: List[Dict] = []

    for paper in papers:
        paper_doi = normalize_doi(paper.get("doi", ""))
        work_id = to_work_id(paper.get("openalex_id", "")) or (
            paper.get("id", "") if str(paper.get("id", "")).startswith("W") else ""
        )
        meta = metadata_by_work_id.get(work_id) or metadata_by_doi.get(paper_doi)
        if not meta:
            unresolved.append(paper)
            continue
        enriched += 1
        if apply_meta(paper, meta):
            abstracts_filled += 1

    resolved_by_title = 0
    title_fetches = 0
    cache_mutated = False

    for paper in unresolved:
        work_id = resolve_openalex_work_id_by_title(paper)
        if not work_id:
            continue
        title_fetches += 1

        meta = metadata_by_work_id.get(work_id)
        if not meta:
            try:
                work = api_get_json(f"/works/{work_id}", {"select": OPENALEX_SELECT_FIELDS})
                meta = work_to_metadata(work)
            except Exception:
                continue
            if meta.get("work_id"):
                metadata_by_work_id[meta["work_id"]] = meta
                cache_mutated = True
                refresh_metadata_by_doi()

        if not meta:
            continue

        was_openalex_empty = not (paper.get("openalex_id") or "").strip()
        if apply_meta(paper, meta):
            abstracts_filled += 1
        if was_openalex_empty and (paper.get("openalex_id") or "").strip():
            resolved_by_title += 1
            enriched += 1

    if cache_mutated:
        save_openalex_cache(OPENALEX_CACHE_PATH, metadata_by_work_id)

    crossref_stats = enrich_missing_abstracts_from_crossref(seed_papers, hop_papers)
    arxiv_stats = enrich_missing_abstracts_from_arxiv(seed_papers, hop_papers)
    url_stats = enrich_missing_abstracts_from_urls(seed_papers, hop_papers)
    proxy_stats = fill_proxy_descriptions(seed_papers, hop_papers)
    missing_abstracts = sum(1 for paper in papers if not (paper.get("abstract") or "").strip())
    proxy_count = sum(1 for paper in papers if bool(paper.get("abstract_is_proxy")))
    without_source_abstract = sum(
        1 for paper in papers if bool(paper.get("abstract_is_proxy")) or not (paper.get("abstract_source") or "").strip()
    )
    return {
        "papers_total": total,
        "papers_with_openalex_match": enriched,
        "abstracts_filled": abstracts_filled,
        "openalex_title_lookups": title_fetches,
        "openalex_resolved_by_title": resolved_by_title,
        "papers_missing_abstract": missing_abstracts,
        "papers_with_proxy_description": proxy_count,
        "papers_without_source_abstract": without_source_abstract,
        **crossref_stats,
        **arxiv_stats,
        **url_stats,
        **proxy_stats,
    }


@dataclass
class Topic:
    code: str
    layer: str
    name: str
    why: str


def load_topics() -> Tuple[List[Topic], Dict[str, Topic]]:
    rows = load_json(CORPUS_DIR / "tables" / "topic_map.json")
    topics: List[Topic] = []
    for row in rows:
        code = row.get("topic_code", "").strip()
        if not code:
            continue
        topics.append(
            Topic(
                code=code,
                layer=(row.get("layer") or "").strip(),
                name=(row.get("topic_name") or "").strip(),
                why=(row.get("why_it_matters") or "").strip(),
            )
        )
    topic_by_code = {topic.code: topic for topic in topics}
    return topics, topic_by_code


def build_seed_topic_lookup(topic_by_code: Dict[str, Topic]) -> Dict[str, Set[str]]:
    lookup: Dict[str, Set[str]] = defaultdict(set)

    corpus_rows = load_json(CORPUS_DIR / "tables" / "corpus_registry.json")
    for row in corpus_rows:
        corpus_id = (row.get("corpus_id") or "").strip()
        if not corpus_id:
            continue
        topics = [row.get("primary_topic", "")] + listify(row.get("secondary_topics", []))
        topics = [t for t in topics if t in topic_by_code]
        if not topics:
            continue
        lookup[f"WORKBOOK-{corpus_id}"].update(topics)

    expansion_rows = load_json(CORPUS_DIR / "tables" / "expansion_sources.json")
    for row in expansion_rows:
        source_id = (row.get("source_id") or "").strip()
        if not source_id:
            continue
        topics = [row.get("primary_topic", "")] + listify(row.get("topics_covered", []))
        topics = [t for t in topics if t in topic_by_code]
        if topics:
            lookup[f"WORKBOOK-{source_id}"].update(topics)

    # Landscape-anchor seeds (LS-SEED-*) carry their own primary/secondary topics
    # in expansion_seed_queries.jsonl. Without this, hop candidates whose
    # origin_seed_ids point at LS-SEED rows resolve to no topics and are dropped
    # silently by build_hop_papers().
    seed_query_path = CORPUS_DIR / "expansion_seed_queries.jsonl"
    if seed_query_path.is_file():
        with seed_query_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                seed_id = (row.get("seed_id") or "").strip()
                if not seed_id:
                    continue
                topics = [row.get("primary_topic", "")] + listify(row.get("secondary_topics", []))
                topics = [t for t in topics if t in topic_by_code]
                if topics:
                    lookup[seed_id].update(topics)

    return lookup
