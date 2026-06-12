"""Generate Astro MDX stubs for opt-in YAML records not yet surfaced.

For every YAML record in landscape/resources/*/ that carries `featured: true`,
check whether an MDX file under site/src/content/ already references it via
`provenance.ref`. If not, emit a stub MDX file to the appropriate collection
with frontmatter derived from the YAML, and a body that echoes the description.

Editorial can then flesh the stub out; nothing is lost because the YAML remains
the source of truth and stubs carry the canonical resource_id.

Collection routing (content_type → Astro collection):
    CO, PC, PP     → community
    TP             → tools
    GL, AP (paper) → reading-list  (unless type indicates event media)
    GL event media → events
    SG             → tools   (standards surface as reference material)

Usage:
    python3 scripts/generate_mdx_stubs.py           # dry run
    python3 scripts/generate_mdx_stubs.py --write   # apply

Requires PyYAML (see scripts/requirements.txt).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
RES_DIR = REPO_ROOT / "landscape" / "resources"
MDX_DIR = REPO_ROOT / "site" / "src" / "content"

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
REF_RE = re.compile(r'^\s*ref:\s*"?(LE-[A-Z]+-\d+)"?', re.MULTILINE)

# MDX type formats (from site/src/content.config.ts); we map content_type onto them.
FORMAT_BY_CTYPE: dict[str, str] = {
    "CO": "org",
    "PC": "program",
    "PP": "person",
    "TP": "tool",
    "SG": "tool",
    "GL": "report",
    "AP": "paper",
    "HT": "post",
    "JO": "org",
    "CE": "conference",
}

COLLECTION_BY_CTYPE: dict[str, str] = {
    "CO": "community",
    "PC": "community",
    "PP": "community",
    "TP": "tools",
    "SG": "tools",
    "GL": "reading-list",
    "AP": "reading-list",
    "HT": "reading-list",
    "JO": "community",
    "CE": "events",
}

# GL records whose `type:` indicates recorded talk / podcast / webinar are
# routed to the events collection instead of reading-list.
EVENT_TYPES = {"podcast", "webinar", "keynote", "conference-talk", "video", "series"}


def slugify(text: str, max_len: int = 70) -> str:
    """Make a filesystem-safe slug from a title."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].strip("-") or "untitled"


def load_existing_refs() -> set[str]:
    """Return the set of LE-*-NNN refs already present in any MDX file."""
    refs: set[str] = set()
    for mdx in MDX_DIR.rglob("*.mdx"):
        text = mdx.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            continue
        rm = REF_RE.search(m.group(1))
        if rm:
            refs.add(rm.group(1))
    return refs


def iter_featured_yaml() -> list[tuple[Path, dict]]:
    """Yield (path, record) for every YAML record marked `featured: true`."""
    out: list[tuple[Path, dict]] = []
    for yf in sorted(RES_DIR.rglob("*.yaml")):
        rec = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        if rec.get("featured") is True:
            out.append((yf, rec))
    return out


def pick_collection(rec: dict) -> str:
    """Return Astro collection directory for a YAML record."""
    ctype = rec.get("content_type", "")
    if ctype == "GL" and (rec.get("type") or "").lower() in EVENT_TYPES:
        return "events"
    return COLLECTION_BY_CTYPE.get(ctype, "reading-list")


def pick_format(rec: dict) -> str:
    """Return the MDX `format:` value matching the YAML record."""
    ctype = rec.get("content_type", "")
    t = (rec.get("type") or "").lower()
    if ctype == "GL" and t in EVENT_TYPES:
        return t
    return FORMAT_BY_CTYPE.get(ctype, "report")


def render_frontmatter(rec: dict) -> str:
    """Render a minimal Astro-compatible MDX frontmatter block."""
    title = rec.get("title") or rec.get("name") or rec.get("event") or rec["resource_id"]
    url = rec.get("url") or ""
    venue = rec.get("affiliation_or_venue") or rec.get("publisher") or rec.get("venue") or ""
    authors = rec.get("authors") or rec.get("role") or ""
    if isinstance(authors, list):
        authors = ", ".join(a for a in authors if a)
    year = rec.get("year")
    topics = [rec.get("primary_topic") or "T00", *(rec.get("secondary_topics") or [])]
    summary = (rec.get("description") or rec.get("significance") or "").strip()

    def esc(v: str) -> str:
        return v.replace("\\", "\\\\").replace('"', '\\"')

    lines = ["---", f'title: "{esc(title)}"', f'format: "{pick_format(rec)}"']
    if venue:
        lines.append(f'venue: "{esc(venue)}"')
    if authors:
        lines.append(f'authors: "{esc(authors)}"')
    if year:
        lines.append(f"year: {int(year)}")
    if url:
        lines.append(f'url: "{esc(url)}"')
    lines.append("topics:")
    for t in topics:
        if t:
            lines.append(f'  - "{t}"')
    if summary:
        # Summaries can be long; truncate to 400 chars in the stub frontmatter.
        short = summary if len(summary) < 400 else summary[:397] + "…"
        lines.append(f'summary: "{esc(short)}"')
    lines.append("provenance:")
    lines.append('  dataset: "landscape YAML corpus"')
    lines.append(f'  ref: "{rec["resource_id"]}"')
    lines.append("---")
    return "\n".join(lines) + "\n"


def render_body(rec: dict) -> str:
    """Render the stub MDX body: description plus a 'stub' note for editors."""
    body = (rec.get("description") or rec.get("significance") or "").strip()
    if not body:
        body = "Stub — expand with editorial framing."
    return f"\n{body}\n\n<!-- stub: generated from landscape YAML; expand before publishing -->\n"


def main() -> int:
    """Emit MDX stubs for featured YAML records not yet surfaced."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="Write MDX files.")
    args = parser.parse_args()

    existing = load_existing_refs()
    featured = iter_featured_yaml()

    created: list[tuple[str, Path]] = []
    skipped_existing: list[str] = []
    skipped_unroutable: list[str] = []

    for yaml_path, rec in featured:
        rid = rec.get("resource_id")
        if not rid:
            continue
        if rid in existing:
            skipped_existing.append(rid)
            continue
        ctype = rec.get("content_type", "")
        collection = pick_collection(rec)
        if collection not in {"community", "tools", "reading-list", "events", "practice"}:
            skipped_unroutable.append(f"{rid}  ({ctype})")
            continue
        title = rec.get("title") or rec.get("name") or rec.get("event") or rid
        slug = f"{rid.lower()}-{slugify(title)}"
        out_path = MDX_DIR / collection / f"{slug}.mdx"
        mdx = render_frontmatter(rec) + render_body(rec)
        created.append((rid, out_path))
        if args.write:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(mdx, encoding="utf-8")

    print(f"YAML records marked featured: {len(featured)}")
    print(f"Already surfaced (skipped):   {len(skipped_existing)}")
    print(f"Stubs to create:              {len(created)}")
    for rid, p in created:
        print(f"  {rid}  →  {p.relative_to(REPO_ROOT)}")
    if skipped_unroutable:
        print(f"\nUnroutable content_type ({len(skipped_unroutable)}):")
        for line in skipped_unroutable:
            print(f"  {line}")
    if not args.write:
        print("\n(dry run — use --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
