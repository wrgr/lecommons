"""Derive institution records and compute person-paper associations from existing MDX.

Reads the current `community/` (people, programs, orgs) and `reading-list/` MDX files,
extracts unique parent institutions from their `venue` frontmatter, and emits one
institution MDX per unique institution with a body that lists the programs and
ICICLE-affiliated people hosted there, plus papers/grey literature authored by
members (matched by authors-string).

Idempotent: will only overwrite institution MDX whose body was previously auto-
generated (marker line `<!-- auto:institution -->`). Hand edits are preserved.
Person MDX is enriched with a trailing `<!-- auto:person-papers -->` block that
is rewritten on each run.

Run from the repo root:

    source venv/bin/activate
    python3 site/scripts/derive_institutions_and_associations.py
"""

from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "site" / "src" / "content"
COMMUNITY = CONTENT / "community"
READING = CONTENT / "reading-list"

AUTO_INST_MARKER = "{/* auto:institution */}"
AUTO_PERSON_MARKER = "{/* auto:person-papers */}"

# Canonical institution names and their aliases (left: canonical, right: patterns).
CANONICAL_INSTITUTIONS: list[tuple[str, list[str]]] = [
    ("Carnegie Mellon University", ["carnegie mellon", r"\bcmu\b"]),
    ("Massachusetts Institute of Technology", [r"\bmit\b", "massachusetts institute"]),
    ("Johns Hopkins University", ["johns hopkins", r"\bjhu\b"]),
    ("Arizona State University", ["arizona state", r"\basu\b"]),
    ("Stanford University", ["stanford"]),
    ("University of Pennsylvania", ["university of pennsylvania", r"\bupenn\b", r"\bpenn\b"]),
    ("Vanderbilt University", ["vanderbilt"]),
    ("University of Washington", ["university of washington", r"\buw\b"]),
    ("Purdue University", ["purdue"]),
    ("Dartmouth College", ["dartmouth"]),
    ("Indiana University", ["indiana university"]),
    ("University of Calgary", ["university of calgary", "calgary"]),
    ("Georgia Institute of Technology", ["georgia institute", "georgia tech"]),
    ("IEEE ICICLE", ["ieee icicle"]),
    ("U.S. Air Force", ["u.s. air force", "air force", r"\busaf\b", "air university"]),
    ("Canadian Armed Forces", ["canadian armed forces"]),
]

# A short editorial stub for institutions we know something about; institutions
# outside this list get a generic auto-sentence.
INST_BLURB: dict[str, str] = {
    "Carnegie Mellon University":
        "The most concentrated academic home of learning engineering in the US — CMU's "
        "Simon Initiative, Open Learning Initiative (OLI), HCII, and METALS master's "
        "program all intersect here.",
    "Massachusetts Institute of Technology":
        "Home to the LEAP (Learning Engineering and Practice) group and multiple ICICLE "
        "working-group contributors; a significant site for cross-disciplinary LE work.",
    "Johns Hopkins University":
        "Hosts the LENS (Learning Engineering for Next-Generation Systems) concentration "
        "— a joint School of Education / APL program targeting high-consequence domains.",
    "Arizona State University":
        "Houses the Learning Engineering Institute and a graduate certificate, both "
        "launched in 2023; ICICLE-affiliated people work here across Human Systems "
        "Engineering and Fulton Schools of Engineering.",
    "University of Pennsylvania":
        "The Graduate School of Education hosts the Penn Center for Learning Analytics "
        "(Ryan Baker's group) — a key node in the learning-analytics strand of the field.",
    "Stanford University":
        "Stanford GSE offers the M.S. Learning Design and Technology, one of the older "
        "adjacent programs feeding into learning engineering practice.",
    "Vanderbilt University":
        "Peabody College's LIVE (Learning Innovation Incubator) is a research home for "
        "learning-sciences-to-practice translation.",
    "University of Washington":
        "Learning sciences and design work spans the College of Education, HCDE, and the "
        "iSchool; multiple adjacent programs.",
    "Purdue University":
        "The School of Engineering Education (ENE) is a long-running engineering-education "
        "research home with substantial overlap with learning engineering.",
    "Dartmouth College":
        "Faculty affiliates contribute to ICICLE working groups, particularly the pK-12 MIG.",
    "Indiana University":
        "The Luddy School's Information and Learning Science programs are close neighbors "
        "to learning engineering practice.",
    "University of Calgary":
        "Home to ICICLE-affiliated faculty working in higher-education LE.",
    "Georgia Institute of Technology":
        "Leads the National AI Institute for Adult Learning and Online Education (AI-ALOE) "
        "consortium — a major applied-AI learning research hub.",
    "IEEE ICICLE":
        "The professional home of learning engineering — hosts the annual meeting, "
        "publishes the Body of Knowledge, and convenes SIGs and MIGs that do the "
        "ongoing working-group labor of the field.",
    "U.S. Air Force":
        "Air University and the Enterprise Learning Engineering Center of Excellence (ELE CoE) "
        "represent the largest publicly-visible US government investment in LE practice.",
    "Canadian Armed Forces":
        "A contributor to ICICLE's Government/Military MIG and related workforce work.",
}


def read_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (frontmatter-dict, body) from an MDX file. Minimal YAML parser."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    data: dict = {}
    current_key: str | None = None
    for raw in yaml_block.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("  - "):
            # list item under current_key
            val = raw.strip()[2:].strip().strip('"')
            if current_key:
                data.setdefault(current_key, [])
                if isinstance(data[current_key], list):
                    data[current_key].append(val)
            continue
        if raw.startswith("  "):
            # nested mapping (e.g. provenance.ref)
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        val = val.strip()
        if val == "":
            current_key = key
            data[key] = []
            continue
        current_key = key
        if val.startswith('"') and val.endswith('"'):
            data[key] = val[1:-1]
        elif val == "true":
            data[key] = True
        elif val == "false":
            data[key] = False
        else:
            try:
                data[key] = int(val)
            except ValueError:
                data[key] = val
    return data, body


def slugify(text: str) -> str:
    """Convert a title to a filesystem-safe slug, clipped to 70 chars."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:70] or "untitled"


def yaml_escape(s: str) -> str:
    """Quote a string value for YAML frontmatter output."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def match_institution(venue: str) -> str | None:
    """Return the canonical institution name for a venue string, or None."""
    if not venue:
        return None
    v = venue.lower()
    for canonical, patterns in CANONICAL_INSTITUTIONS:
        for pat in patterns:
            if re.search(pat, v):
                return canonical
    return None


def normalize_name(s: str) -> str:
    """Collapse a string to alphabetic-only lowercase for name matching."""
    return re.sub(r"[^a-z]", "", (s or "").lower())


def collect_records(dir_: Path) -> list[tuple[Path, dict, str]]:
    """Load every MDX in a directory as (path, frontmatter, body) triples."""
    return [(p, *read_frontmatter(p)) for p in sorted(dir_.glob("*.mdx"))]


def main() -> None:
    """Derive institution MDX and enrich person MDX with associated papers."""
    community_items = collect_records(COMMUNITY)
    reading_items = collect_records(READING)

    # Group persons and programs by institution.
    members_by_inst: dict[str, list[str]] = defaultdict(list)
    programs_by_inst: dict[str, list[str]] = defaultdict(list)
    for path, fm, _body in community_items:
        inst = match_institution(fm.get("venue", ""))
        if not inst:
            continue
        if fm.get("format") == "person":
            members_by_inst[inst].append(fm.get("title", path.stem))
        elif fm.get("format") == "program":
            programs_by_inst[inst].append(fm.get("title", path.stem))

    # Papers (authored by ICICLE people).
    person_papers: dict[str, list[tuple[str, str]]] = defaultdict(list)
    # Map normalized-name -> display name of each ICICLE person
    icicle_people: dict[str, str] = {}
    for _, fm, _ in community_items:
        if fm.get("format") == "person":
            icicle_people[normalize_name(fm.get("title", ""))] = fm.get("title", "")
    # Scan reading-list authors strings for any ICICLE person name substring.
    for _, fm, _ in reading_items:
        authors = fm.get("authors", "") or ""
        title = fm.get("title", "")
        fmt = fm.get("format", "")
        url = fm.get("url")
        if not authors:
            continue
        for name_key, display in icicle_people.items():
            # Match on surname at minimum — split display name into tokens.
            tokens = [t for t in display.split() if len(t) >= 4]
            if any(t.lower() in authors.lower() for t in tokens):
                person_papers[display].append((title, fmt, url))

    # Institutions associated with papers via their members.
    papers_by_inst: dict[str, set[str]] = defaultdict(set)
    for _, fm, _ in community_items:
        if fm.get("format") != "person":
            continue
        inst = match_institution(fm.get("venue", ""))
        if not inst:
            continue
        for title, _fmt, _url in person_papers.get(fm.get("title", ""), []):
            papers_by_inst[inst].add(title)

    institutions = (
        set(members_by_inst) | set(programs_by_inst) | set(papers_by_inst)
    )

    created = 0
    updated = 0
    for inst in sorted(institutions):
        slug = "institution-" + slugify(inst)
        path = COMMUNITY / f"{slug}.mdx"

        programs = sorted(set(programs_by_inst.get(inst, [])))
        members = sorted(set(members_by_inst.get(inst, [])))
        papers = sorted(papers_by_inst.get(inst, []))

        # Compose body.
        blurb = INST_BLURB.get(inst, "")
        body_lines: list[str] = []
        if blurb:
            body_lines.append(blurb)
        if programs:
            body_lines.append(
                f"**Programs here** ({len(programs)}): " + ", ".join(programs) + "."
            )
        if members:
            body_lines.append(
                f"**ICICLE-affiliated people** ({len(members)}): "
                + ", ".join(members) + "."
            )
        if papers:
            peek = papers[:3]
            suffix = f" (and {len(papers) - 3} more)" if len(papers) > 3 else ""
            body_lines.append(
                f"**Papers / grey literature from members** ({len(papers)}): "
                + "; ".join(peek) + suffix + "."
            )
        body_lines.append(AUTO_INST_MARKER)
        body = "\n\n".join(body_lines)

        frontmatter_lines = [
            "---",
            f"title: {yaml_escape(inst)}",
            'format: "institution"',
            'cluster: "Institutions"',
            "topics:",
            '  - "T16"',
            "provenance:",
            '  dataset: "Derived from ICICLE registry"',
            f'  ref: {yaml_escape("members=" + str(len(members)) + "; programs=" + str(len(programs)) + "; papers=" + str(len(papers)))}',
            "---",
            "",
            body,
            "",
        ]

        # Only rewrite if file absent or body was auto-generated before
        should_write = True
        if path.exists():
            _, existing_body = read_frontmatter(path)
            if AUTO_INST_MARKER not in existing_body:
                should_write = False

        if should_write:
            path.write_text("\n".join(frontmatter_lines), encoding="utf-8")
            if path.exists():
                updated += 1
            else:
                created += 1

    # Enrich each person MDX: append (or replace) an auto-block listing their papers.
    person_enriched = 0
    for path, fm, body in community_items:
        if fm.get("format") != "person":
            continue
        display = fm.get("title", "")
        papers = person_papers.get(display, [])
        if not papers:
            continue
        # Remove any previous auto-block
        split = body.split(AUTO_PERSON_MARKER)
        base_body = split[0].rstrip()
        new_lines = [
            base_body,
            "",
            AUTO_PERSON_MARKER,
            "",
            "**Associated reading:**",
        ]
        for title, _fmt, url in papers[:6]:
            if url:
                new_lines.append(f"- [{title}]({url})")
            else:
                new_lines.append(f"- {title}")

        # Reassemble the MDX with the original frontmatter block intact.
        text = path.read_text(encoding="utf-8")
        end = text.find("\n---", 3)
        header = text[: end + 4]
        path.write_text(header + "\n\n" + "\n".join(new_lines) + "\n", encoding="utf-8")
        person_enriched += 1

    print(f"Institutions: {len(institutions)} total")
    print(f"  person-paper matches: {sum(len(v) for v in person_papers.values())}")
    print(f"  persons enriched with associated reading: {person_enriched}")


if __name__ == "__main__":
    main()
