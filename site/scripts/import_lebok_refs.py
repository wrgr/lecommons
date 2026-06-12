#!/usr/bin/env python3
"""Import a plain-text LEBOK-style citation list into reading-list MDX stubs.

Usage (dry-run by default):
    python3 site/scripts/import_lebok_refs.py --input /path/to/citations.txt

Write new files:
    python3 site/scripts/import_lebok_refs.py --input /path/to/citations.txt --write

Input format:
- One citation per line (or wrapped paragraph blocks separated by blank lines).
- Leading bullets ('*', '-', '1.') are allowed.
- Optional bracket notes are preserved in the body, e.g. "[add IITSEC paper details]".
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
READING_LIST_DIR = ROOT / "site" / "src" / "content" / "reading-list"
DEFAULT_REPORT_DIR = ROOT / "site" / "data" / "import_reports"


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:90] or "untitled"


def normalize_key(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def title_variants(text: str) -> List[str]:
    base = normalize_key(text)
    if not base:
        return []
    out = [base]
    for prefix in ("the ", "a ", "an "):
        if base.startswith(prefix):
            out.append(base[len(prefix) :].strip())
    return [v for v in out if v]


def normalize_url(url: str) -> str:
    return (url or "").strip().rstrip(".,);]").lower()


def yaml_escape(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_paragraph_entries(path: Path) -> List[str]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    entries: List[str] = []
    current: List[str] = []

    bullet_re = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+")
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current).strip())
                current = []
            continue

        if bullet_re.match(line):
            if current:
                entries.append(" ".join(current).strip())
                current = []
            stripped = bullet_re.sub("", line).strip()
            current.append(stripped)
            continue

        current.append(stripped)

    if current:
        entries.append(" ".join(current).strip())
    return [e for e in entries if e and not e.startswith("#")]


def parse_frontmatter(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_text = parts[1]
    out: Dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        out[key] = value
    return out


def load_existing_index() -> Dict[str, Dict[str, str]]:
    by_title: Dict[str, str] = {}
    by_url: Dict[str, str] = {}
    by_slug: Dict[str, str] = {}
    for path in sorted(READING_LIST_DIR.glob("*.mdx")):
        fm = parse_frontmatter(path)
        slug = path.stem
        by_slug[slug] = path.name
        for title in title_variants(fm.get("title", "")):
            by_title[title] = path.name
        url = normalize_url(fm.get("url", ""))
        if url:
            by_url[url] = path.name
    return {"title": by_title, "url": by_url, "slug": by_slug}


def clean_line(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^\s*(?:in\s+)", "", s, flags=re.IGNORECASE)
    return s


def extract_url(text: str) -> tuple[str, str]:
    m = re.search(r"https?://\S+", text)
    if not m:
        return text, ""
    url = normalize_url(m.group(0))
    without = (text[: m.start()] + " " + text[m.end() :]).strip()
    return without, url


def extract_notes(text: str) -> tuple[str, List[str]]:
    notes = re.findall(r"\[([^\]]+)\]", text)
    cleaned = re.sub(r"\[[^\]]+\]", "", text).strip()
    return cleaned, [n.strip() for n in notes if n.strip()]


def infer_format(source: str, title: str, venue: str, default_format: str) -> str:
    blob = " ".join([source, title, venue]).lower()
    if "conference" in blob or "proceedings" in blob or "lncs" in blob or "doi.org/10.1007/" in blob:
        return "paper"
    if "routledge" in blob or "corwin" in blob or "publishing" in blob or "book" in blob:
        return "book"
    if "edsurge" in blob or "moonshot catalog" in blob or "medium.com" in blob:
        return "article"
    return default_format


def parse_citation(raw: str, default_format: str) -> Dict:
    line = clean_line(raw)
    line, notes = extract_notes(line)
    line, url = extract_url(line)

    year = None
    authors = ""
    title = ""
    venue = ""

    ym = re.search(r"\((19|20)\d{2}\)", line)
    if ym:
        year = int(ym.group(0)[1:-1])
        before = line[: ym.start()].strip(" .,:;")
        after = line[ym.end() :].strip(" .,:;")
        authors = re.sub(r"^\s*In\s+", "", before, flags=re.IGNORECASE).strip()
        segments = [s.strip(" \"'") for s in re.split(r"\.\s+", after) if s.strip()]
        if segments:
            title = segments[0]
            venue = segments[1] if len(segments) > 1 else ""
    else:
        year_candidates = re.findall(r"\b(19|20)\d{2}\b", line)
        if year_candidates:
            m = list(re.finditer(r"\b(19|20)\d{2}\b", line))[-1]
            year = int(m.group(0))
            left = line[: m.start()].strip(" .,:;")
            right = line[m.end() :].strip(" .,:;")
        else:
            left = line
            right = ""

        left_parts = [p.strip(" \"'") for p in re.split(r"\.\s+", left) if p.strip()]
        if len(left_parts) >= 2:
            authors = left_parts[0]
            title = left_parts[1]
            venue = left_parts[2] if len(left_parts) > 2 else ""
        elif left_parts:
            title = left_parts[0]
        if right and not venue:
            venue = right

    title = re.sub(r"\s+", " ", title).strip(" .\"'")
    venue = re.sub(r"\s+", " ", venue).strip(" .\"'")
    authors = re.sub(r"\s+", " ", authors).strip(" .\"'")

    if not title:
        # Final fallback: first sentence-like chunk.
        chunks = [c.strip(" .\"'") for c in re.split(r"\.\s+", line) if c.strip()]
        if chunks:
            title = chunks[0]

    fmt = infer_format(line, title, venue, default_format)
    return {
        "raw": raw,
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "url": url,
        "format": fmt,
        "notes": notes,
    }


def build_mdx_text(item: Dict, dataset: str, section_header: str, tag: str) -> str:
    lines: List[str] = ["---"]
    lines.append(f"title: {yaml_escape(item['title'])}")
    lines.append(f"format: {yaml_escape(item['format'])}")
    if item.get("venue"):
        lines.append(f"venue: {yaml_escape(item['venue'])}")
    if item.get("authors"):
        lines.append(f"authors: {yaml_escape(item['authors'])}")
    if item.get("year"):
        lines.append(f"year: {int(item['year'])}")
    if item.get("url"):
        lines.append(f"url: {yaml_escape(item['url'])}")
    lines.append("tags:")
    lines.append(f"  - {yaml_escape(tag)}")
    lines.append("provenance:")
    lines.append(f"  dataset: {yaml_escape(dataset)}")
    lines.append(f"  ref: {yaml_escape(item['raw'])}")
    lines.append("  sheet: \"manual curation\"")
    lines.append(f"  sectionHeader: {yaml_escape(section_header)}")
    lines.append("---")
    lines.append("")
    lines.append("Imported from citation intake list. Verify topics, summary, and venue details.")
    if item.get("notes"):
        lines.append("")
        lines.append("Source notes:")
        for note in item["notes"]:
            lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def unique_path_for_slug(slug: str, used: Dict[str, str]) -> Path:
    candidate = slug
    n = 2
    while candidate in used:
        candidate = f"{slug}-{n}"
        n += 1
    used[candidate] = candidate
    return READING_LIST_DIR / f"{candidate}.mdx"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import citation text into reading-list MDX stubs.")
    p.add_argument("--input", required=True, help="Path to plain-text citations file.")
    p.add_argument("--write", action="store_true", help="Write new files (default is dry-run).")
    p.add_argument("--dataset", default="lebok.wiki", help="provenance.dataset value.")
    p.add_argument(
        "--section-header",
        default="Citation intake",
        help="provenance.sectionHeader value.",
    )
    p.add_argument("--default-format", default="article", choices=["paper", "book", "article", "report", "post", "essay"])
    p.add_argument("--tag", default="lebok-wiki", help="Tag added to generated files.")
    p.add_argument("--report", default="", help="Optional report JSON output path.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    existing = load_existing_index()
    entries = read_paragraph_entries(input_path)

    seen_in_batch_titles: Dict[str, str] = {}
    seen_in_batch_urls: Dict[str, str] = {}
    used_slugs = dict(existing["slug"])

    created: List[Dict] = []
    skipped: List[Dict] = []
    failed: List[Dict] = []

    for raw in entries:
        parsed = parse_citation(raw, args.default_format)
        title_keys = title_variants(parsed.get("title", ""))
        url_key = normalize_url(parsed.get("url", ""))

        if not title_keys:
            failed.append({"raw": raw, "reason": "could_not_parse_title"})
            continue

        existing_match = next((existing["title"][k] for k in title_keys if k in existing["title"]), "")
        if existing_match:
            skipped.append({"raw": raw, "reason": "duplicate_title_existing", "match": existing_match})
            continue
        if url_key and url_key in existing["url"]:
            skipped.append({"raw": raw, "reason": "duplicate_url_existing", "match": existing["url"][url_key]})
            continue
        batch_match = next((seen_in_batch_titles[k] for k in title_keys if k in seen_in_batch_titles), "")
        if batch_match:
            skipped.append({"raw": raw, "reason": "duplicate_title_in_input", "match": batch_match})
            continue
        if url_key and url_key in seen_in_batch_urls:
            skipped.append({"raw": raw, "reason": "duplicate_url_in_input", "match": seen_in_batch_urls[url_key]})
            continue

        for key in title_keys:
            seen_in_batch_titles[key] = parsed["title"]
        if url_key:
            seen_in_batch_urls[url_key] = parsed["url"]

        slug = slugify(parsed["title"])
        out_path = unique_path_for_slug(slug, used_slugs)
        rendered = build_mdx_text(parsed, dataset=args.dataset, section_header=args.section_header, tag=args.tag)
        record = {
            "raw": raw,
            "title": parsed["title"],
            "authors": parsed.get("authors", ""),
            "year": parsed.get("year"),
            "venue": parsed.get("venue", ""),
            "url": parsed.get("url", ""),
            "format": parsed["format"],
            "path": str(out_path.relative_to(ROOT)),
        }

        if args.write:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered, encoding="utf-8")
        created.append(record)

    report = {
        "input_path": str(input_path),
        "mode": "write" if args.write else "dry-run",
        "created_count": len(created),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_path = Path(args.report).expanduser().resolve() if args.report else None
    if report_path is None and args.write:
        DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = DEFAULT_REPORT_DIR / f"lebok_import_{ts}.json"
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report["report_path"] = str(report_path)

    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
