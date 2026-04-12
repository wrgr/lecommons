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
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

from utils import (
    normalize_doi, to_work_id, load_json, write_json, doi_to_url,
    citation_plain, citation_bibtex, listify,
    OPENALEX_CACHE_PATH, OPENALEX_SELECT_FIELDS,
    URL_FETCH_TIMEOUT_SEC, URL_FETCH_SLEEP_SEC, URL_FETCH_MAX_RETRIES,
    URL_ABSTRACT_CACHE_PATH, URL_PDF_ABSTRACT_CACHE_PATH,
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
    req = urllib.request.Request(url, headers={"User-Agent": "learning-engineering-resources/1.0"})
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
                return ""
            time.sleep(min(2**attempt, 20))
    return ""


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
    req = urllib.request.Request(url, headers={"User-Agent": "learning-engineering-resources/1.0"})
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
                return b""
            time.sleep(min(2**attempt, 20))
    return b""


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
    if not pdf_bytes:
        return ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as infile:
            infile.write(pdf_bytes)
            infile.flush()
            out = subprocess.check_output(
                [
                    "pdftotext",
                    "-f",
                    "1",
                    "-l",
                    "3",
                    "-enc",
                    "UTF-8",
                    infile.name,
                    "-",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        return ""
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

    return lookup
