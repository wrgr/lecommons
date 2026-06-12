"""Build site/src/data/programs_people_registry.json from landscape/resources/ YAML files.

Reads all YAML files in landscape/resources/<type>/ subdirectories and writes a flat
JSON array suitable for graph.astro consumption.  This script is the canonical way to
regenerate the registry; do not hand-edit the output JSON.

Requires PyYAML (see scripts/requirements.txt).
"""

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
RESOURCES_DIR = REPO_ROOT / "landscape" / "resources"
OUTPUT_FILE = REPO_ROOT / "site" / "src" / "data" / "programs_people_registry.json"

# Subdirectories in landscape/resources/ to include in the registry
# (papers are excluded — too large; queried separately via papers_seed.json)
INCLUDE_TYPES = {"people", "organizations", "grey_literature", "programs",
                 "conferences", "tools", "journals", "standards", "history_timeline"}


def load_yaml_record(path: Path) -> dict:
    """Load a YAML record file to a dict."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalise_secondary_topics(raw) -> list[str]:
    """Normalise secondary_topics to a list of strings."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if t]
    if isinstance(raw, str):
        return [t.strip() for t in raw.replace(",", " ").split() if t.strip()]
    return []


def record_to_registry_entry(record: dict, subdir: str) -> dict | None:
    """Convert a landscape YAML record to a flat registry entry."""
    rid = record.get("resource_id") or record.get("id")
    if not rid:
        return None

    content_type = record.get("content_type", subdir.upper()[:2])
    name = (
        record.get("name")
        or record.get("title")
        or record.get("event")
        or rid
    )
    url = record.get("url") or record.get("doi") or ""
    if url and record.get("doi") and not url.startswith("http"):
        url = f"https://doi.org/{url}"

    description = record.get("description") or record.get("significance") or ""
    primary_topic = record.get("primary_topic") or "T00"
    secondary_topics = normalise_secondary_topics(record.get("secondary_topics"))

    entry: dict = {
        "resource_id": rid,
        "content_type": content_type,
        "status": record.get("status") or "APPROVED",
        "name": name,
        "url": url,
        "primary_topic": primary_topic,
        "secondary_topics": secondary_topics,
        "description": description,
    }

    # Include extra fields for people
    if content_type == "PP":
        for field in ("affiliation", "era", "role", "years"):
            if record.get(field):
                entry[field] = record[field]

    return entry


def main() -> None:
    """Consolidate all landscape YAML files into a flat registry JSON."""
    entries: list[dict] = []
    seen_ids: set[str] = set()
    errors: list[str] = []

    for subdir in sorted(INCLUDE_TYPES):
        subdir_path = RESOURCES_DIR / subdir
        if not subdir_path.is_dir():
            continue
        yaml_files = sorted(subdir_path.glob("*.yaml"))
        for yf in yaml_files:
            try:
                record = load_yaml_record(yf)
                entry = record_to_registry_entry(record, subdir)
                if entry is None:
                    errors.append(f"No resource_id in {yf.name}")
                    continue
                rid = entry["resource_id"]
                if rid in seen_ids:
                    errors.append(f"Duplicate resource_id {rid} in {yf.name}")
                    continue
                seen_ids.add(rid)
                entries.append(entry)
            except Exception as exc:
                errors.append(f"Error reading {yf}: {exc}")

    OUTPUT_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Registry built: {len(entries)} entries → {OUTPUT_FILE}")
    if errors:
        print(f"\nWarnings ({len(errors)}):")
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")


if __name__ == "__main__":
    main()
