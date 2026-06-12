"""One-shot seeder: read landscape registries and emit MDX stubs into site content collections.

Maps landscape records into the five practice sections (process, methods, tools, evidence,
community) based on content_type and primary_topic. Idempotent — skips files that already
exist so human edits survive re-runs.

Data flow:
  landscape/resources/**/*.yaml  →  scripts/build_registry.py
                                 →  site/src/data/programs_people_registry.json  (PROGRAMS_REG)

Run from the repo root:
    python3 scripts/build_registry.py && python3 site/scripts/import_from_archive.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "archive"
SITE = ROOT / "site"
CONTENT = SITE / "src" / "content"

ICICLE_REG = ARCHIVE / "corpus" / "tables" / "icicle_resources_registry.json"
# Canonical source: built from landscape/resources/**/*.yaml via scripts/build_registry.py
PROGRAMS_REG = SITE / "src" / "data" / "programs_people_registry.json"
PAPERS = ARCHIVE / "corpus" / "academic_papers.jsonl"
PEOPLE = ROOT / "titlesearch" / "data" / "people.json"

# Map ICICLE content_type to our `kind` enum.
ICICLE_KIND = {
    "GL": "framework",  # default for grey-lit; process items become 'diagram', media become 'media'
    "TP": "method",     # default for tools; some become 'tool' based on topic
    "CO": "org",
}

# Fine-grained kind overrides by (content_type, primary_topic) signal and name keywords.
MEDIA_KEYWORDS = ("podcast", "youtube", "webinar", "keynote", "video")
DIAGRAM_KEYWORDS = ("diagram", "process description", "checklist", "toolkit")


def slugify(text: str) -> str:
    """Convert a title to a filesystem-safe slug."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:70]


def route_icicle(rec: dict) -> tuple[str, str] | None:
    """Decide which section + kind an ICICLE registry record belongs in. Return (section, kind) or None."""
    ct = rec["content_type"]
    topic = rec["primary_topic"]
    name_lc = rec["name"].lower()

    # Orgs always go to community
    if ct == "CO":
        return "community", "org"

    # TP (templates/tools) — split by topic
    if ct == "TP":
        if topic in {"T03", "T09", "T15"}:
            return "methods", "method"
        return "tools", "tool"

    # GL (grey literature) — route by topic
    if ct == "GL":
        if topic == "T03":
            kind = "diagram" if any(k in name_lc for k in DIAGRAM_KEYWORDS) else "framework"
            return "process", kind
        if topic == "T15":
            return "evidence", "framework"
        if topic in {"T04", "T16", "T17"}:
            # measurement / standards / methods — keep with evidence as reference material
            return "evidence", "framework"
        # T00, T06, T08, T13 → general field material; treat as evidence references
        kind = "media" if any(k in name_lc for k in MEDIA_KEYWORDS) else "framework"
        return "evidence", kind

    return None


def route_program(rec: dict) -> tuple[str, str] | None:
    """Decide which section an entry in programs_people_registry belongs in. Everything lands in community."""
    ct = rec["content_type"]
    kind_map = {"PP": "person", "PC": "program", "CO": "org", "CE": "event", "TP": "tool", "GL": "framework"}
    kind = kind_map.get(ct)
    if not kind:
        return None
    # Tools from program registry go to the tools section, not community
    if ct == "TP":
        return "tools", "tool"
    if ct == "GL":
        return "evidence", "framework"
    return "community", kind


def route_paper(rec: dict) -> tuple[str, str] | None:
    """Academic papers land in evidence."""
    if rec.get("selection_tier") != "T1":
        return None
    return "evidence", "paper"


def yaml_escape(s: str) -> str:
    """Quote a value for YAML frontmatter — double quotes with escaped double-quotes."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def split_topics(primary: str, secondary: str | list | None) -> list[str]:
    """Normalize primary + secondary topic codes into a single deduped list."""
    out = [primary] if primary else []
    if isinstance(secondary, list):
        out.extend(secondary)
    elif isinstance(secondary, str) and secondary.strip():
        out.extend(s.strip() for s in secondary.split(",") if s.strip())
    seen = set()
    deduped = []
    for t in out:
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def emit(section: str, kind: str, title: str, frontmatter: dict, body: str, slug: str) -> bool:
    """Write one MDX file if it doesn't already exist. Return True if written."""
    out_dir = CONTENT / section
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.mdx"
    if path.exists():
        return False

    lines = ["---"]
    lines.append(f"title: {yaml_escape(title)}")
    lines.append(f"kind: {kind}")
    for k in ("url", "source", "sourceId", "affiliation", "authors"):
        v = frontmatter.get(k)
        if v:
            lines.append(f"{k}: {yaml_escape(str(v))}")
    if frontmatter.get("year"):
        lines.append(f"year: {frontmatter['year']}")
    topics = frontmatter.get("topics") or []
    if topics:
        lines.append("topics:")
        for t in topics:
            lines.append(f"  - {t}")
    if frontmatter.get("order") is not None:
        lines.append(f"order: {frontmatter['order']}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def process_icicle(stats: dict) -> None:
    """Ingest ICICLE resource registry."""
    records = json.loads(ICICLE_REG.read_text(encoding="utf-8"))
    for rec in records:
        if rec.get("status") != "APPROVED":
            continue
        routed = route_icicle(rec)
        if not routed:
            continue
        section, kind = routed
        slug = slugify(rec["name"])
        frontmatter = {
            "url": rec.get("url", ""),
            "source": "ICICLE resources registry",
            "sourceId": rec["resource_id"],
            "affiliation": rec.get("affiliation_or_venue", ""),
            "topics": split_topics(rec.get("primary_topic", ""), rec.get("secondary_topics", "")),
        }
        body = rec.get("description", "").strip() or "_Blurb pending._"
        if emit(section, kind, rec["name"], frontmatter, body, slug):
            stats[section] = stats.get(section, 0) + 1


def process_programs(stats: dict) -> None:
    """Ingest programs/people registry."""
    records = json.loads(PROGRAMS_REG.read_text(encoding="utf-8"))
    for rec in records:
        if rec.get("status") not in {"APPROVED", "SEED"}:
            continue
        routed = route_program(rec)
        if not routed:
            continue
        section, kind = routed
        slug = slugify(rec["name"])
        frontmatter = {
            "url": rec.get("url", "") if rec.get("url", "") != "[internal]" else "",
            "source": "Programs & people registry",
            "sourceId": rec["resource_id"],
            "affiliation": rec.get("affiliation_or_venue", ""),
            "topics": split_topics(rec.get("primary_topic", ""), rec.get("secondary_topics", "")),
        }
        body = rec.get("description", "").strip() or "_Blurb pending._"
        if emit(section, kind, rec["name"], frontmatter, body, slug):
            stats[section] = stats.get(section, 0) + 1


def process_papers(stats: dict) -> None:
    """Ingest academic papers (seed tier only)."""
    for line in PAPERS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("status") != "APPROVED":
            continue
        routed = route_paper(rec)
        if not routed:
            continue
        section, kind = routed
        slug = slugify(rec["title"])
        frontmatter = {
            "url": rec.get("doi", "") and f"https://doi.org/{rec['doi']}" or "",
            "source": "Academic papers (seed tier)",
            "sourceId": rec["resource_id"],
            "authors": rec.get("authors", ""),
            "year": rec.get("year"),
            "topics": split_topics(rec.get("primary_topic", ""), rec.get("secondary_topics")),
        }
        justification = rec.get("topic_justification", "").strip()
        body = justification or "_Blurb pending._"
        if emit(section, kind, rec["title"], frontmatter, body, slug):
            stats[section] = stats.get(section, 0) + 1


def process_people(stats: dict, limit: int = 12) -> None:
    """Ingest a small sample of titlesearch APPROVED practitioners into community."""
    if not PEOPLE.exists():
        return
    records = json.loads(PEOPLE.read_text(encoding="utf-8"))
    approved = [p for p in records if p.get("triage") == "APPROVED"]
    # Prefer records with both organization and a real job_title
    curated = [p for p in approved if p.get("organization") and p.get("job_title")]
    curated.sort(key=lambda p: (p.get("organization", ""), p.get("display_name", "")))

    for p in curated[:limit]:
        name = p["display_name"]
        slug = "practitioner-" + slugify(name)
        title = f"{name} — {p.get('job_title', 'Learning Engineer')}"
        frontmatter = {
            "source": "Titlesearch practitioner registry",
            "sourceId": p.get("person_id", ""),
            "affiliation": p.get("organization", ""),
            "topics": [],
        }
        org = p.get("organization", "")
        body = f"{p.get('job_title', 'Learning Engineer')} at {org}." if org else p.get("job_title", "")
        if emit("community", "person", title, frontmatter, body, slug):
            stats["community"] = stats.get("community", 0) + 1


def main() -> None:
    """Run all seeders and report counts per section."""
    stats: dict[str, int] = {}
    process_icicle(stats)
    process_programs(stats)
    process_papers(stats)
    process_people(stats)

    print("Wrote new MDX files:")
    for section in ("process", "methods", "tools", "evidence", "community"):
        print(f"  {section:10s} +{stats.get(section, 0)}")
    print(f"  total      {sum(stats.values())}")


if __name__ == "__main__":
    main()
