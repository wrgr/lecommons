"""Add provenance source field to all landscape/resources YAML files that lack one.

Provenance values:
  curated           — manually authored/reviewed entry
  openalex_expansion — from OpenAlex cross-seed expansion (has openalex_id)
  book_endnotes     — from Goodell & Kolodner Learning Engineering Toolkit endnotes
  registry_migration — migrated from site/src/data/programs_people_registry.json
"""

from __future__ import annotations

import re
from pathlib import Path

RESOURCES_DIR = Path("/home/user/lecommons/landscape/resources")

# Subdirectories and their default provenance for entries without openalex_id
SUBDIR_DEFAULTS: dict[str, str] = {
    "papers": "curated",          # per-file logic below overrides this
    "people": "curated",
    "grey_literature": "curated",
    "organizations": "curated",
    "programs": "registry_migration",
    "conferences": "curated",
    "tools": "curated",
    "journals": "curated",
    "standards": "curated",
    "history_timeline": "curated",
}


def detect_provenance(text: str, subdir: str) -> str:
    """Determine provenance from file contents."""
    if "openalex_id:" in text:
        # Check if openalex_id is non-empty
        m = re.search(r'^openalex_id:\s*"?([^"\s]+)"?', text, re.MULTILINE)
        if m and m.group(1) not in ("", '""', "''"):
            return "openalex_expansion"
    if "book_endnotes" in text.lower() or "Goodell & Kolodner" in text:
        return "book_endnotes"
    return SUBDIR_DEFAULTS.get(subdir, "curated")


def add_provenance_to_file(path: Path, subdir: str) -> bool:
    """Add source: field after content_type: if not already present. Returns True if changed."""
    text = path.read_text(encoding="utf-8")

    if "\nsource:" in text or text.startswith("source:"):
        return False  # already has provenance

    provenance = detect_provenance(text, subdir)

    # Insert after content_type: line
    new_text = re.sub(
        r"(^content_type:.*$)",
        rf"\1\nsource: {provenance}",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    if new_text == text:
        # No content_type line found; insert after resource_id
        new_text = re.sub(
            r"(^resource_id:.*$)",
            rf"\1\nsource: {provenance}",
            text,
            count=1,
            flags=re.MULTILINE,
        )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    """Add provenance to all YAML files in landscape/resources/."""
    by_source: dict[str, int] = {}
    total_changed = 0

    for subdir in sorted(SUBDIR_DEFAULTS):
        subdir_path = RESOURCES_DIR / subdir
        if not subdir_path.is_dir():
            continue
        for yf in sorted(subdir_path.glob("*.yaml")):
            changed = add_provenance_to_file(yf, subdir)
            if changed:
                # Detect what we wrote
                text = yf.read_text()
                m = re.search(r"^source:\s*(\S+)", text, re.MULTILINE)
                src = m.group(1) if m else "unknown"
                by_source[src] = by_source.get(src, 0) + 1
                total_changed += 1

    print(f"Added provenance to {total_changed} files:")
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count}")


if __name__ == "__main__":
    main()
