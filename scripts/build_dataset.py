#!/usr/bin/env python3
"""Build a lightweight learning-engineering knowledge graph dataset.

This script aligns to a staged architecture:
1) seed corpus + provenance
2) extraction (resources, chapter topics, endnotes)
3) citation/topic graph + one-hop expansion
4) gaps/program summaries for synthesis
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
DATA_DIR = ROOT / "data"

ICICLE_URL = "https://sagroups.ieee.org/icicle/resources/"
ICICLE_HTML = CACHE_DIR / "icicle_resources.html"
PROGRAMS_TXT = CACHE_DIR / "icicle_adjacent_programs.txt"
ICICLE_PAGE_CACHE_DIR = CACHE_DIR / "icicle_pages"
ICICLE_ADJACENT_URLS = [
    "https://sagroups.ieee.org/icicle/learning-engineering-process/",
    "https://sagroups.ieee.org/icicle/learning-engineering-toolkit/",
    "https://sagroups.ieee.org/icicle/sigs/",
    "https://sagroups.ieee.org/icicle/newsletters/",
    "https://sagroups.ieee.org/icicle/proceedings/",
    "https://sagroups.ieee.org/icicle/meetings/",
    "https://sagroups.ieee.org/icicle/invitation-to-learning-engineering-webinar-series/",
    "https://sagroups.ieee.org/icicle/2024-icicle-conference-on-learning-engineering/",
    "https://sagroups.ieee.org/icicle/2023-icicle-conference-on-learning-engineering/",
    "https://sagroups.ieee.org/icicle/2022-icicle-conference-on-learning-engineering/",
]
LENS_DRAFT_DOC = Path("/Users/wgray13/Downloads/LENS_Prospective_Students_040726_draft.docx")

PDF_A_DEFAULT = "/Users/wgray13/Desktop/Learning Engineering Toolkit_26_04_07_15_45_22A.pdf"
PDF_B_DEFAULT = "/Users/wgray13/Downloads/Learning Engineering Toolkit_26_04_07_15_45_22.pdf"
TXT_A = CACHE_DIR / "toolkit_part_a.txt"
TXT_B = CACHE_DIR / "toolkit_part_b.txt"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
MAILTO = "wgray13+learning-engineering@example.com"
MANUAL_SEEDS = [
    {
        "id": "manual:goodell2020-competencies",
        "title": "Competencies of Learning Engineering Teams and Team Members",
        "plain_citation": "Goodell, J., Kessler, A., Kurzweil, D., Kolodner, J. (2020). Competencies of Learning Engineering Teams and Team Members. In IEEE ICICLE Proceedings of the 2019 Conference on Learning Engineering, Arlington, VA, May 2019.",
        "source_type": "user_added_seed",
    }
]

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s)\]>\"']+", re.I)
QUOTE_RE = re.compile(r"[\"“]([^\"”]{6,})[\"”]")


@dataclass
class Chapter:
    number: int
    title: str
    section: str
    start_page: int


@dataclass
class Endnote:
    id: str
    chapter: int
    note_number: int
    raw_text: str
    title_guess: str
    doi: Optional[str]
    urls: List[str]
    artifact_type: str


def ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ICICLE_PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_binary(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def download_inputs(refresh: bool, include_programs_doc: bool) -> None:
    if refresh or not ICICLE_HTML.exists():
        ICICLE_HTML.write_text(fetch_text(ICICLE_URL), encoding="utf-8")

    if include_programs_doc and (refresh or not PROGRAMS_TXT.exists()):
        doc_url = (
            "https://docs.google.com/document/d/"
            "1Rg36o2ZnqMhd_uYTEYij_A_x-tilUaGwhUFcysazQc4/export?format=txt"
        )
        PROGRAMS_TXT.write_text(fetch_text(doc_url), encoding="utf-8")


def cache_name_for_url(url: str) -> str:
    return (url.rstrip("/").split("/")[-1] or "root") + ".html"


def download_adjacent_pages(refresh: bool) -> List[Path]:
    pages = []
    for url in ICICLE_ADJACENT_URLS:
        out = ICICLE_PAGE_CACHE_DIR / cache_name_for_url(url)
        if refresh or not out.exists():
            try:
                out.write_text(fetch_text(url), encoding="utf-8")
            except Exception:
                # Keep going: partial page cache is acceptable for MVP reassessment.
                pass
        if out.exists():
            pages.append(out)
    return pages


def extract_pdf_text(pdf_path: str, out_path: Path, refresh: bool) -> None:
    if out_path.exists() and not refresh:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftotext", "-layout", pdf_path, str(out_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return normalize_space(html.unescape(s))


def parse_icicle_resources(html_text: str) -> Dict[str, object]:
    # Keep only main post body for cleaner extraction.
    start = html_text.find('<div class="post">')
    end = html_text.find('</div><!-- .post -->')
    body = html_text[start:end] if start != -1 and end != -1 else html_text

    token_re = re.compile(r"<(h2|h3|p|li)[^>]*>(.*?)</\1>", re.I | re.S)
    href_re = re.compile(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)

    current_section = "Uncategorized"
    sections: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for tag, inner in token_re.findall(body):
        tag = tag.lower()
        text = strip_tags(inner)

        if tag in {"h2", "h3"}:
            if text:
                current_section = text
            continue

        links = href_re.findall(inner)
        if not links:
            continue

        for href, anchor in links:
            title = strip_tags(anchor)
            if not title:
                continue
            sections[current_section].append(
                {
                    "title": title,
                    "url": html.unescape(href),
                    "context": text,
                }
            )

    section_list = []
    total_items = 0
    for section, items in sections.items():
        # Deduplicate exact URL+title collisions.
        seen = set()
        deduped = []
        for it in items:
            key = (it["title"], it["url"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        section_list.append({"section": section, "items": deduped})
        total_items += len(deduped)

    return {
        "source_url": ICICLE_URL,
        "section_count": len(section_list),
        "item_count": total_items,
        "sections": section_list,
    }


def visible_text_from_html(html_text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_space(text).lower()


def build_page_scan(page_paths: List[Path]) -> List[dict]:
    rows = []
    for p in page_paths:
        html_text = p.read_text(encoding="utf-8", errors="replace")
        t = visible_text_from_html(html_text)
        rows.append(
            {
                "file": str(p),
                "url": "https://sagroups.ieee.org/icicle/" + p.stem + "/",
                "text": t,
            }
        )
    return rows


def assess_gap_status(page_scan: List[dict], resources_item_count: int, unmatched_processed_notes: int, processed_notes: int) -> List[dict]:
    all_text = " ".join(r["text"] for r in page_scan)
    url_map = {r["file"]: r["url"] for r in page_scan}

    def page_hits(keywords: List[str]) -> List[str]:
        hits = []
        for row in page_scan:
            if any(k in row["text"] for k in keywords):
                hits.append(row["url"])
        return sorted(set(hits))

    role_terms = [
        "higher education",
        "pk-12",
        "government / military",
        "workforce",
        "students and grads",
        "market interest groups",
    ]
    role_hit_count = sum(1 for term in role_terms if term in all_text)
    role_status = "resolved" if role_hit_count >= 4 else "flagged"

    asset_terms = [
        "template",
        "checklist",
        "tracker",
        "xapi",
        "caliper",
        "datashop",
        "github",
        "case study",
    ]
    asset_hit_count = sum(1 for term in asset_terms if term in all_text)
    asset_status = "partial" if asset_hit_count >= 3 else "flagged"

    gaps = [
        {
            "id": "missing_metadata_coverage",
            "label": "Citation metadata coverage",
            "status": "flagged",
            "detail": "Structured metadata still does not resolve all parsed endnotes/artifacts automatically.",
            "evidence": {
                "unmatched_processed_notes": unmatched_processed_notes,
                "processed_notes": processed_notes,
            },
            "evidence_links": [],
        },
        {
            "id": "role_based_navigation",
            "label": "Role-based pathways",
            "status": role_status,
            "detail": (
                "Adjacent ICICLE pages include explicit role/market pathways (SIGs/MIGs + meetings)."
                if role_status == "resolved"
                else "Role pathways remain weakly surfaced."
            ),
            "evidence": {"matched_role_terms": role_hit_count, "target_terms": len(role_terms)},
            "evidence_links": page_hits(["sig", "mig", "higher education", "pk-12", "workforce", "government / military"])[:8],
        },
        {
            "id": "reproducible_assets",
            "label": "Reusable technical assets",
            "status": asset_status,
            "detail": (
                "Adjacent pages include templates/checklists/case-study assets, but reusable data/API/code assets are still uneven."
                if asset_status == "partial"
                else "Reusable data/API/code assets remain sparse."
            ),
            "evidence": {"matched_asset_terms": asset_hit_count, "resource_items": resources_item_count},
            "evidence_links": page_hits(["template", "checklist", "tracker", "xapi", "caliper", "case study"])[:8],
        },
    ]
    return gaps


def parse_chapters_from_contents(text: str) -> List[Chapter]:
    lines = text.splitlines()
    in_contents = False
    current_part = "Other"
    chapters: List[Chapter] = []

    for line in lines:
        t = line.strip()
        if t == "CONTENTS":
            in_contents = True
            continue
        if not in_contents:
            continue
        if t in {"FOUNDATIONS", "TOOLS", "VISION AND COMMENTARY", "AUTHORS"}:
            current_part = t.title()
            continue
        # End when contributors/front matter starts after contents.
        if t.startswith("Contributors, Reviewers"):
            break

        m = re.match(r"^(\d{2})\s+(.+?)\.{4,}\s*(\d+)\s*$", t)
        if m:
            num = int(m.group(1))
            title = normalize_space(m.group(2))
            page = int(m.group(3))
            chapters.append(Chapter(number=num, title=title, section=current_part, start_page=page))

    return chapters


def infer_title(raw: str) -> str:
    raw = normalize_space(raw)
    q = QUOTE_RE.search(raw)
    if q:
        return normalize_space(q.group(1))

    # Fallback: choose longest sentence-like span with content words.
    parts = [normalize_space(p) for p in re.split(r"\.\s+", raw) if normalize_space(p)]
    if not parts:
        return raw[:120]

    candidates = [p for p in parts if len(p.split()) >= 4]
    if candidates:
        # prefer a candidate with keywords that look title-like
        def score(p: str) -> Tuple[int, int]:
            caps = sum(1 for w in p.split() if w[:1].isupper())
            return (caps, len(p))

            
        return sorted(candidates, key=score, reverse=True)[0][:220]

    return parts[0][:220]


def extract_doi(raw: str) -> Optional[str]:
    m = DOI_RE.search(raw)
    if not m:
        return None
    doi = m.group(0).rstrip(".,;)\"]")
    return doi


def extract_urls(raw: str) -> List[str]:
    urls = []
    for m in URL_RE.finditer(raw):
        u = m.group(0).rstrip(".,;)\"]")
        if u.startswith("www."):
            u = "https://" + u
        urls.append(u)
    # Preserve order while deduping.
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def classify_artifact(raw: str, urls: List[str], doi: Optional[str]) -> str:
    t = raw.lower()
    url_blob = " ".join(urls).lower()
    if "youtube.com" in url_blob or "youtu.be" in url_blob or "video" in t:
        return "video"
    if "podcast" in t:
        return "podcast"
    if "webinar" in t:
        return "webinar"
    if "proceedings" in t or "conference" in t:
        return "conference_artifact"
    if "book" in t or "chapter" in t:
        return "book_or_chapter"
    if doi:
        return "paper_or_article"
    if "github.com" in url_blob:
        return "software_or_repository"
    if "standard" in t:
        return "standard_or_spec"
    return "article_report_or_web"


def parse_endnotes(text: str) -> List[Endnote]:
    lines = text.splitlines()
    current_chapter = None
    in_endnotes = False
    current_note_num = None
    current_buf: List[str] = []
    out: List[Endnote] = []
    section_last_note = 0

    def flush() -> None:
        nonlocal current_note_num, current_buf
        if current_chapter is None or current_note_num is None or not current_buf:
            current_note_num = None
            current_buf = []
            return

        raw = normalize_space(" ".join(current_buf))
        doi = extract_doi(raw)
        urls = extract_urls(raw)
        note_id = f"ch{current_chapter:02d}-n{current_note_num:03d}"
        out.append(
            Endnote(
                id=note_id,
                chapter=current_chapter,
                note_number=current_note_num,
                raw_text=raw,
                title_guess=infer_title(raw),
                doi=doi,
                urls=urls,
                artifact_type=classify_artifact(raw, urls, doi),
            )
        )
        current_note_num = None
        current_buf = []

    chapter_re = re.compile(r"^CHAPTER\s+(\d+)\s*$")
    note_re = re.compile(r"^\s*(\d{1,3})\s{1,3}(\S.*)$")

    for line in lines:
        t = line.rstrip()
        ts = t.strip()

        cm = chapter_re.match(ts)
        if cm:
            flush()
            current_chapter = int(cm.group(1))
            in_endnotes = False
            continue

        if ts == "Endnotes":
            flush()
            in_endnotes = True
            section_last_note = 0
            continue

        if not in_endnotes:
            continue

        # Endnotes section usually ends at next chapter.
        nm = note_re.match(t)
        if nm:
            candidate = int(nm.group(1))
            # Guardrails: endnote numbering is usually sequential within a chapter.
            # This avoids pulling unrelated numeric lines (e.g., image dimensions, page labels).
            if section_last_note == 0 and candidate > 12:
                continue
            if section_last_note > 0 and candidate > section_last_note + 3:
                continue
            if section_last_note > 0 and candidate < section_last_note:
                if candidate != 1:
                    continue
            flush()
            current_note_num = candidate
            section_last_note = candidate
            current_buf = [nm.group(2)]
            continue

        # Stop collecting when obvious non-note content appears.
        if ts.startswith("CHAPTER "):
            flush()
            in_endnotes = False
            continue

        if current_note_num is not None:
            # Keep wrapped lines and blank separators.
            if ts:
                current_buf.append(ts)

    flush()
    return out


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def openalex_get(url: str, pause_sec: float = 0.03) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        time.sleep(pause_sec)
        return payload
    except Exception:
        return None


def decode_openalex_abstract(inv_idx: Optional[dict]) -> Optional[str]:
    if not inv_idx or not isinstance(inv_idx, dict):
        return None
    try:
        size = 0
        for positions in inv_idx.values():
            if positions:
                size = max(size, max(positions) + 1)
        words = [""] * size
        for word, positions in inv_idx.items():
            for p in positions:
                if 0 <= p < size:
                    words[p] = word
        text = " ".join(w for w in words if w)
        return normalize_space(text) if text else None
    except Exception:
        return None


def sanitize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = html.unescape(str(value))
    text = (
        text.replace("\u00A0", " ")
        .replace("\u0091", "'")
        .replace("\u0092", "'")
        .replace("\u0093", '"')
        .replace("\u0094", '"')
        .replace("\u0096", "-")
        .replace("\u0097", "-")
    )
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", " ", text)
    text = normalize_space(text)
    return text or None


def abstract_looks_malformed(text: str, work_type: Optional[str]) -> bool:
    lower = text.lower()
    url_count = len(re.findall(r"https?://", text))
    work_type = (work_type or "").lower()
    is_book_like = work_type in {"book", "book-series", "edited-book", "monograph"}

    if len(text) > 5000:
        return True
    if "search for more papers by this author" in lower:
        return True
    if lower.startswith("no access") and "doi.org" in lower:
        return True
    if url_count >= 4 and len(text) > 900:
        return True
    if is_book_like and len(text) > 1700:
        return True
    return False


def work_plain_citation(work: dict) -> str:
    authors = []
    for a in work.get("authorships", [])[:6]:
        name = a.get("author", {}).get("display_name")
        if name:
            authors.append(name)
    author_str = ", ".join(authors) if authors else "Unknown author"
    year = work.get("publication_year") or "n.d."
    title = sanitize_text(work.get("display_name")) or "Untitled"
    host_venue = work.get("host_venue") or {}
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = sanitize_text(host_venue.get("display_name") or source.get("display_name")) or ""
    doi = work.get("doi")
    tail = f" {doi}" if doi else ""
    if venue:
        return f"{author_str} ({year}). {title}. {venue}.{tail}".strip()
    return f"{author_str} ({year}). {title}.{tail}".strip()


def work_bibtex(work: dict) -> str:
    title = (sanitize_text(work.get("display_name")) or "Untitled").replace("{", "").replace("}", "")
    year = work.get("publication_year") or ""
    doi = work.get("doi") or ""
    url = work.get("id") or ""
    authors = []
    for a in work.get("authorships", []):
        name = a.get("author", {}).get("display_name")
        if name:
            authors.append(name)
    author_field = " and ".join(authors)
    key_base = re.sub(r"[^a-zA-Z0-9]+", "", (authors[0] if authors else "work")[:20])
    key = f"{key_base}{year}" if year else key_base

    lines = [f"@misc{{{key},"]
    if author_field:
        lines.append(f"  author = {{{author_field}}},")
    lines.append(f"  title = {{{title}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if doi:
        lines.append(f"  doi = {{{doi.replace('https://doi.org/', '')}}},")
    if url:
        lines.append(f"  url = {{{url}}},")
    lines.append("}")
    return "\n".join(lines)


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "")
    return doi


def resolve_work_for_note(
    note: Endnote,
    cache: dict,
    allow_network: bool = True,
    doi_only: bool = False,
) -> Optional[dict]:
    cache_key = None
    if note.doi:
        cache_key = f"doi:{normalize_doi(note.doi).lower()}"
    elif note.urls:
        cache_key = f"url:{note.urls[0]}"
    elif note.title_guess:
        cache_key = f"title:{note.title_guess.lower()}"

    if cache_key and cache_key in cache:
        return cache[cache_key]
    if not allow_network:
        return None

    work = None

    if note.doi:
        doi = normalize_doi(note.doi)
        doi_url = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
        work = openalex_get(f"https://api.openalex.org/works/{doi_url}?mailto={urllib.parse.quote(MAILTO)}")

    # Fallback title search.
    if not work and note.title_guess and not doi_only:
        q = urllib.parse.quote(note.title_guess[:180])
        payload = openalex_get(
            f"https://api.openalex.org/works?search={q}&per-page=5&mailto={urllib.parse.quote(MAILTO)}"
        )
        if payload and payload.get("results"):
            best = None
            best_score = 0.0
            for cand in payload["results"]:
                cand_title = (cand.get("display_name") or "").lower()
                score = difflib.SequenceMatcher(None, note.title_guess.lower(), cand_title).ratio()
                if score > best_score:
                    best = cand
                    best_score = score
            if best and best_score >= 0.55:
                work = best

    if cache_key:
        cache[cache_key] = work
    return work


def resolve_work_for_title(title: str, cache: dict, allow_network: bool = True) -> Optional[dict]:
    key = f"title:{title.lower()}"
    if key in cache:
        return cache[key]
    if not allow_network:
        return None
    q = urllib.parse.quote(title[:180])
    payload = openalex_get(
        f"https://api.openalex.org/works?search={q}&per-page=5&mailto={urllib.parse.quote(MAILTO)}"
    )
    work = None
    if payload and payload.get("results"):
        best = None
        best_score = 0.0
        for cand in payload["results"]:
            cand_title = (cand.get("display_name") or "").lower()
            score = difflib.SequenceMatcher(None, title.lower(), cand_title).ratio()
            if score > best_score:
                best = cand
                best_score = score
        if best and best_score >= 0.55:
            work = best
    cache[key] = work
    return work


def compact_work(work: dict, hop: int) -> dict:
    work_type = sanitize_text(work.get("type")) or "unknown"
    abstract = sanitize_text(decode_openalex_abstract(work.get("abstract_inverted_index")))
    if abstract and abstract_looks_malformed(abstract, work_type):
        abstract = None

    return {
        "id": work.get("id"),
        "openalex_id": work.get("id"),
        "title": sanitize_text(work.get("display_name")),
        "abstract": abstract,
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "type": work_type,
        "cited_by_count": work.get("cited_by_count"),
        "authors": [
            sanitize_text(a.get("author", {}).get("display_name"))
            for a in work.get("authorships", [])
            if sanitize_text(a.get("author", {}).get("display_name"))
        ],
        "referenced_works": work.get("referenced_works", []),
        "citation_plain": work_plain_citation(work),
        "citation_bibtex": work_bibtex(work),
        "hop": hop,
        "source_url": sanitize_text(work.get("primary_location", {}).get("landing_page_url"))
        or sanitize_text(work.get("id")),
    }


def extract_programs(programs_txt: Optional[str]) -> dict:
    # Curated MVP summary with explicit categories and sources.
    programs = [
        {
            "name": "Carnegie Mellon University (METALS, OLI, OpenSimon)",
            "category": "academic",
            "summary": "Program and ecosystem focused on learning sciences, analytics, and learning engineering practice through METALS, OLI, and OpenSimon tools.",
            "links": [
                "https://www.cmu.edu/simon/open-simon/index.html",
                "https://www.cmu.edu/masters-educational-technology-applied-learning-science/",
                "https://oli.cmu.edu/"
            ],
        },
        {
            "name": "Arizona State University (Learning Engineering Institute + Grad Pathways)",
            "category": "academic",
            "summary": "ASU’s Learning Engineering Institute and associated graduate pathways support research-to-practice learning system design at scale.",
            "links": [
                "https://learningatscale.asu.edu/",
                "https://news.asu.edu/colleges-and-units/learning-engineering-institute",
                "https://education.asu.edu/degree/graduate-certificate-learning-engineering"
            ],
        },
        {
            "name": "Johns Hopkins University (LENS: Learning Engineering for Next-Generation Systems)",
            "category": "academic",
            "summary": "LENS is positioned as a systems-framing, decision-grade learning engineering pathway for high-consequence domains (defense, healthcare, and large-scale education).",
            "links": [
                "https://education.jhu.edu/masters-programs/master-of-education-in-learning-design-and-technology/"
            ],
            "evidence_note": "Program description aligned to user-provided draft: /Users/wgray13/Downloads/LENS_Prospective_Students_040726_draft.docx",
        },
        {
            "name": "Boston College (Learning Design and Technology)",
            "category": "academic",
            "summary": "Graduate preparation path with strong ties to learning engineering methods and practice-oriented design workflows.",
            "links": [
                "https://www.bc.edu/content/bc-web/schools/lynch-school/academics/departments-and-programs/curriculum-and-instruction/ma-learning-design-technology.html"
            ],
        },
        {
            "name": "ICICLE (IEEE SA Industry Consortium)",
            "category": "nonprofit",
            "summary": "Consortium hub for shared resources, SIG/MIG practice communities, webinars, and conference-based field coordination.",
            "links": [
                "https://sagroups.ieee.org/icicle/",
                "https://sagroups.ieee.org/icicle/resources/"
            ],
        },
        {
            "name": "The Learning Agency Community",
            "category": "nonprofit",
            "summary": "Community programming, resources, and networking support for practitioners and researchers applying learning engineering.",
            "links": [
                "https://www.the-learning-agency.com/",
                "https://groups.google.com/g/learning-engineering"
            ],
        },
        {
            "name": "Yet Analytics",
            "category": "commercial",
            "summary": "Commercial tooling and services for data instrumentation and analysis workflows used in learning engineering settings.",
            "links": [
                "https://www.yetanalytics.com/learningengineering"
            ],
        },
    ]

    inferred = []
    if programs_txt:
        # Pull program lines from the exported ICICLE students+grads programs tab text.
        in_block = False
        for line in programs_txt.splitlines():
            t = line.strip()
            if "🏫 LE-adjacent programs" in t:
                in_block = True
                continue
            if in_block and t.startswith("See more programs listed here"):
                break
            if in_block and t.startswith("*"):
                item = normalize_space(t.lstrip("* "))
                if item and "ICICLE Students & Grads" not in item and "See other tabs" not in item:
                    inferred.append(item)

    return {
        "notes": "Program list intentionally lightweight for MVP; migrate to broader EBKGC ingestion later.",
        "programs": programs,
        "adjacent_program_mentions": inferred[:30],
    }


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "untitled"


def build_graph(
    chapters: List[Chapter],
    matched_notes: List[dict],
    seed_works: Dict[str, dict],
    hop_works: Dict[str, dict],
    icicle_sections: List[dict],
) -> dict:
    nodes = []
    edges = []
    matched_by_work = defaultdict(lambda: {"note_ids": [], "chapters": set(), "artifact_types": set()})

    for note in matched_notes:
        work_id = note.get("work_id")
        if not work_id:
            continue
        m = matched_by_work[work_id]
        m["note_ids"].append(note.get("id"))
        if note.get("chapter") is not None:
            m["chapters"].add(int(note["chapter"]))
        if note.get("artifact_type"):
            m["artifact_types"].add(note["artifact_type"])

    hop_parent_map = defaultdict(set)
    for w in seed_works.values():
        seed_id = w.get("id")
        if not seed_id:
            continue
        for ref in w.get("referenced_works", []):
            hop_parent_map[ref].add(seed_id)

    # Part + chapter topic nodes.
    part_ids = {}
    chapter_ids = []
    for ch in chapters:
        part_id = f"part:{ch.section}"
        if part_id not in part_ids:
            part_ids[part_id] = ch.section
            nodes.append(
                {
                    "id": part_id,
                    "label": ch.section,
                    "type": "topic_part",
                    "hop": 0,
                    "provenance": {
                        "kind": "derived_topic_part",
                        "source": "Learning Engineering Toolkit contents",
                        "method": "contents_heading_parse",
                    },
                }
            )

        ch_id = f"topic:ch{ch.number:02d}"
        nodes.append(
            {
                "id": ch_id,
                "label": f"Chapter {ch.number}: {ch.title}",
                "type": "topic",
                "chapter": ch.number,
                "hop": 0,
                "provenance": {
                    "kind": "derived_topic_chapter",
                    "source": "Learning Engineering Toolkit contents",
                    "method": "contents_heading_parse",
                    "chapter_number": ch.number,
                    "section": ch.section,
                    "start_page": ch.start_page,
                },
            }
        )
        chapter_ids.append(ch_id)
        edges.append({"source": part_id, "target": ch_id, "type": "contains"})

    # ICICLE section topic-surface nodes.
    section_to_chapter_map = {
        "what is learning engineering?": [1, 2, 3],
        "books": [1, 2, 4],
        "examples of practices and tools": [1, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "background resources": [1, 2, 3, 4, 7],
        "conference proceedings": [19],
        "learning engineering adjacent academic programs": [10, 16],
        "learning about learning engineering: articles, papers, interviews, podcasts, videos and more (chronological order)": [1, 2, 3, 4, 19],
        "communities": [10],
    }
    for sec in icicle_sections:
        section_name = sec.get("section", "").strip()
        if not section_name:
            continue
        sid = f"icicle_section:{slugify(section_name)}"
        nodes.append(
            {
                "id": sid,
                "label": section_name,
                "type": "topic_surface",
                "hop": 0,
                "provenance": {
                    "kind": "icicle_section",
                    "source": "ICICLE resources page",
                    "method": "section_heading_parse",
                    "source_url": ICICLE_URL,
                    "resource_item_count": len(sec.get("items", [])),
                },
            }
        )
        mapped = section_to_chapter_map.get(section_name.lower(), [])
        for ch_num in mapped:
            edges.append(
                {
                    "source": sid,
                    "target": f"topic:ch{int(ch_num):02d}",
                    "type": "section_to_topic",
                }
            )

    # Paper nodes.
    for w in seed_works.values():
        work_id = w["id"]
        m = matched_by_work.get(work_id)
        seed_origin = w.get("seed_origin", "endnote_match")
        if seed_origin == "user_added_seed":
            provenance = {
                "kind": "manual_seed",
                "source": "user_added_seed",
                "method": "manual_inclusion",
                "seed_label": w.get("seed_label"),
                "source_url": w.get("source_url"),
            }
        else:
            provenance = {
                "kind": "seed_artifact",
                "source": "Toolkit endnotes",
                "method": "endnote_parse + metadata_resolution",
                "source_url": w.get("source_url"),
                "note_ids": sorted(m["note_ids"]) if m else [],
                "chapters": sorted(m["chapters"]) if m else [],
                "artifact_types": sorted(m["artifact_types"]) if m else [],
                "matched_note_count": len(m["note_ids"]) if m else 0,
            }
        nodes.append({"id": work_id, "label": w["title"], "type": "paper", "hop": 0, "provenance": provenance})

    for w in hop_works.values():
        parents = sorted(hop_parent_map.get(w["id"], set()))
        nodes.append(
            {
                "id": w["id"],
                "label": w["title"],
                "type": "paper",
                "hop": 1,
                "provenance": {
                    "kind": "one_hop_expansion",
                    "source": "OpenAlex referenced_works",
                    "method": "seed_to_reference_expansion",
                    "source_url": w.get("source_url"),
                    "parent_seed_ids": parents,
                    "parent_seed_count": len(parents),
                },
            }
        )

    # Chapter -> seed paper edges from endnotes.
    for note in matched_notes:
        work_id = note.get("work_id")
        chapter = note.get("chapter")
        if not work_id or not chapter:
            continue
        edges.append(
            {
                "source": f"topic:ch{int(chapter):02d}",
                "target": work_id,
                "type": "cites_in_endnotes",
                "note_id": note.get("id"),
            }
        )

    # Seed -> one-hop edges.
    hop_ids = set(hop_works)
    for w in seed_works.values():
        for ref in w.get("referenced_works", []):
            if ref in hop_ids:
                edges.append(
                    {
                        "source": w["id"],
                        "target": ref,
                        "type": "one_hop_reference",
                    }
                )

    # Deduplicate nodes/edges.
    uniq_nodes = {}
    for n in nodes:
        if "provenance" not in n:
            n["provenance"] = {
                "kind": "unknown",
                "source": "unspecified",
                "method": "unspecified",
            }
        uniq_nodes[n["id"]] = n

    uniq_edges = set()
    out_edges = []
    for e in edges:
        k = (e["source"], e["target"], e["type"], e.get("note_id"))
        if k in uniq_edges:
            continue
        uniq_edges.add(k)
        out_edges.append(e)

    return {
        "nodes": list(uniq_nodes.values()),
        "edges": out_edges,
        "stats": {
            "node_count": len(uniq_nodes),
            "edge_count": len(out_edges),
            "seed_papers": len(seed_works),
            "hop_papers": len(hop_works),
            "chapters": len(chapters),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-fetch/download and regenerate caches.")
    parser.add_argument("--skip-openalex", action="store_true", help="Skip enrichment against OpenAlex.")
    parser.add_argument("--seed-limit", type=int, default=260, help="Maximum number of endnotes to attempt enriching.")
    parser.add_argument("--hop-per-seed", type=int, default=5, help="Max referenced works to consider per seed paper.")
    parser.add_argument("--hop-total-limit", type=int, default=320, help="Global cap for one-hop papers.")
    parser.add_argument("--doi-only", action="store_true", help="Only resolve works via DOI (skip title lookup).")
    parser.add_argument("--pdf-a", default=PDF_A_DEFAULT)
    parser.add_argument("--pdf-b", default=PDF_B_DEFAULT)
    args = parser.parse_args()

    ensure_dirs()
    download_inputs(refresh=args.refresh, include_programs_doc=True)
    page_paths = download_adjacent_pages(refresh=args.refresh)
    extract_pdf_text(args.pdf_a, TXT_A, refresh=args.refresh)
    extract_pdf_text(args.pdf_b, TXT_B, refresh=args.refresh)

    icicle_html = ICICLE_HTML.read_text(encoding="utf-8", errors="replace")
    resources = parse_icicle_resources(icicle_html)
    save_json(DATA_DIR / "icicle_resources.json", resources)

    text_a = TXT_A.read_text(encoding="utf-8", errors="replace")
    text_b = TXT_B.read_text(encoding="utf-8", errors="replace")

    chapters = parse_chapters_from_contents(text_a)
    save_json(
        DATA_DIR / "topics_chapters.json",
        {
            "count": len(chapters),
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "section": c.section,
                    "start_page": c.start_page,
                }
                for c in chapters
            ],
        },
    )

    notes = parse_endnotes(text_a) + parse_endnotes(text_b)
    # Deduplicate repeated entries if overlap exists.
    uniq = {}
    for n in notes:
        uniq[n.id] = n
    notes = [uniq[k] for k in sorted(uniq)]

    save_json(
        DATA_DIR / "endnotes_raw.json",
        {
            "count": len(notes),
            "notes": [
                {
                    "id": n.id,
                    "chapter": n.chapter,
                    "note_number": n.note_number,
                    "title_guess": n.title_guess,
                    "doi": n.doi,
                    "urls": n.urls,
                    "artifact_type": n.artifact_type,
                    "raw_text": n.raw_text,
                }
                for n in notes
            ],
        },
    )

    cache_path = CACHE_DIR / "openalex_cache.json"
    openalex_cache = load_json(cache_path, default={})
    works_cache = load_json(CACHE_DIR / "openalex_work_objects.json", default={})

    matched_notes = []
    seed_works: Dict[str, dict] = {}

    to_process = notes[: args.seed_limit]
    for n in to_process:
        work = resolve_work_for_note(
            n,
            openalex_cache,
            allow_network=not args.skip_openalex,
            doi_only=args.doi_only,
        )
        if not work or not work.get("id"):
            matched_notes.append(
                {
                    "id": n.id,
                    "chapter": n.chapter,
                    "note_number": n.note_number,
                    "matched": False,
                    "title_guess": n.title_guess,
                    "doi": n.doi,
                    "urls": n.urls,
                    "artifact_type": n.artifact_type,
                }
            )
            continue

        work_id = work["id"]
        works_cache[work_id] = work
        if work_id not in seed_works:
            seed_works[work_id] = compact_work(work, hop=0)

        matched_notes.append(
            {
                "id": n.id,
                "chapter": n.chapter,
                "note_number": n.note_number,
                "matched": True,
                "title_guess": n.title_guess,
                "doi": n.doi,
                "urls": n.urls,
                "artifact_type": n.artifact_type,
                "work_id": work_id,
                "work_title": work.get("display_name"),
            }
        )

    # Add explicit manual seeds that should always be included.
    for seed in MANUAL_SEEDS:
        work = resolve_work_for_title(seed["title"], openalex_cache, allow_network=not args.skip_openalex)
        if work and work.get("id"):
            wid = work["id"]
            works_cache[wid] = work
            if wid not in seed_works:
                seed_obj = compact_work(work, hop=0)
                seed_obj["seed_origin"] = seed["source_type"]
                seed_obj["seed_label"] = seed["plain_citation"]
                seed_works[wid] = seed_obj
        else:
            fallback_id = seed["id"]
            if fallback_id not in seed_works:
                seed_works[fallback_id] = {
                    "id": fallback_id,
                    "openalex_id": None,
                    "title": seed["title"],
                    "abstract": None,
                    "year": 2020,
                    "doi": None,
                    "type": "proceedings-article",
                    "cited_by_count": None,
                    "authors": ["Jim Goodell", "Aaron Kessler", "Dina Kurzweil", "Janet Kolodner"],
                    "referenced_works": [],
                    "citation_plain": seed["plain_citation"],
                    "citation_bibtex": "@inproceedings{goodell2020competencies,\n  title = {Competencies of Learning Engineering Teams and Team Members},\n  author = {Goodell, Jim and Kessler, Aaron and Kurzweil, Dina and Kolodner, Janet},\n  year = {2020},\n  booktitle = {IEEE ICICLE Proceedings of the 2019 Conference on Learning Engineering},\n  address = {Arlington, VA}\n}",
                    "hop": 0,
                    "source_url": "https://sagroups.ieee.org/icicle/proceedings/",
                    "seed_origin": seed["source_type"],
                    "seed_label": seed["plain_citation"],
                }

    # One-hop expansion from referenced works of matched seed papers.
    hop_ids = []
    for w in seed_works.values():
        refs = w.get("referenced_works", [])[: args.hop_per_seed]
        hop_ids.extend(refs)

    hop_counter = Counter(hop_ids)
    ordered_hops = [wid for wid, _ in hop_counter.most_common(args.hop_total_limit)]

    hop_works: Dict[str, dict] = {}
    for wid in ordered_hops:
        work = works_cache.get(wid)
        if not work and not args.skip_openalex:
            enc = urllib.parse.quote(wid, safe=":/")
            work = openalex_get(f"https://api.openalex.org/works/{enc}?mailto={urllib.parse.quote(MAILTO)}")
            if work and work.get("id"):
                works_cache[wid] = work
        if work and work.get("id"):
            hop_works[work["id"]] = compact_work(work, hop=1)

    # Persist caches after network calls.
    save_json(cache_path, openalex_cache)
    save_json(CACHE_DIR / "openalex_work_objects.json", works_cache)

    seed_list = list(seed_works.values())
    hop_list = list(hop_works.values())

    save_json(
        DATA_DIR / "papers_seed.json",
        {
            "count": len(seed_list),
            "papers": seed_list,
        },
    )
    save_json(
        DATA_DIR / "papers_one_hop.json",
        {
            "count": len(hop_list),
            "papers": hop_list,
        },
    )

    matched_count = sum(1 for x in matched_notes if x.get("matched"))
    save_json(
        DATA_DIR / "endnotes_enriched.json",
        {
            "source_note_count": len(notes),
            "processed_note_count": len(to_process),
            "matched_note_count": matched_count,
            "match_rate_processed": round(matched_count / len(to_process), 4) if to_process else 0,
            "rows": matched_notes,
        },
    )

    programs_txt = PROGRAMS_TXT.read_text(encoding="utf-8", errors="replace") if PROGRAMS_TXT.exists() else None
    programs = extract_programs(programs_txt)
    save_json(DATA_DIR / "programs_summary.json", programs)

    graph = build_graph(chapters, matched_notes, seed_works, hop_works, resources.get("sections", []))
    save_json(DATA_DIR / "graph.json", graph)

    # Gap synthesis: reassess flagged gaps using adjacent ICICLE pages.
    unresolved = [m for m in matched_notes if not m["matched"]]
    page_scan = build_page_scan(page_paths)
    save_json(
        DATA_DIR / "icicle_page_scan.json",
        {
            "page_count": len(page_scan),
            "pages": [{"file": p["file"], "url": p["url"]} for p in page_scan],
        },
    )

    gap_items = assess_gap_status(
        page_scan,
        resources_item_count=resources.get("item_count", 0),
        unmatched_processed_notes=len(unresolved),
        processed_notes=len(to_process),
    )
    save_json(DATA_DIR / "gaps.json", {"gaps": gap_items})

    summary = {
        "chapters": len(chapters),
        "icicle_sections": resources.get("section_count", 0),
        "icicle_resource_items": resources.get("item_count", 0),
        "parsed_endnotes": len(notes),
        "processed_endnotes": len(to_process),
        "matched_endnotes": matched_count,
        "seed_papers": len(seed_list),
        "one_hop_papers": len(hop_list),
        "graph_nodes": graph["stats"]["node_count"],
        "graph_edges": graph["stats"]["edge_count"],
        "artifact_type_counts": dict(Counter(n.artifact_type for n in notes)),
    }
    save_json(DATA_DIR / "build_summary.json", summary)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
