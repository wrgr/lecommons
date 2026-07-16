"""Vendor lebokai's exported knowledge-graph node manifest into the lecommons site.

Copies ../lebokai/public/graph-nodes.json to site/src/data/lebokai_nodes.json so
the Explore graph can build against a committed file (lecommons' GitHub Pages CI
only checks out this repo, so the manifest must live here). Run whenever lebokai's
node data changes; the source path is overridable via the LEBOKAI_DIR env var.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_LEBOKAI = REPO_ROOT.parent / "lebokai"
OUTPUT_FILE = REPO_ROOT / "site" / "src" / "data" / "lebokai_nodes.json"

# Fields every node must carry for the Explore graph to render it.
REQUIRED_KEYS = {"slug", "href", "title", "topics"}


def source_path() -> Path:
    """Resolve the lebokai manifest path, honouring the LEBOKAI_DIR override."""
    base = Path(os.environ.get("LEBOKAI_DIR", DEFAULT_LEBOKAI))
    return base / "public" / "graph-nodes.json"


def load_and_validate(path: Path) -> tuple[str, list[dict]]:
    """Return the raw manifest text and its parsed nodes, or exit with a clear error."""
    if not path.exists():
        raise SystemExit(
            f"Source manifest not found: {path}\n"
            "Run `npm run build:graph` in the lebokai repo first, or set LEBOKAI_DIR."
        )
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"Manifest is empty or not a JSON array: {path}")
    missing = REQUIRED_KEYS - set(data[0].keys())
    if missing:
        raise SystemExit(f"Manifest nodes are missing required keys: {sorted(missing)}")
    return text, data


def main() -> None:
    """Copy the validated lebokai manifest verbatim into site/src/data/lebokai_nodes.json."""
    src = source_path()
    # Copy the source bytes verbatim (after validation) so the vendored file stays
    # byte-identical to lebokai's output rather than being re-serialised.
    text, nodes = load_and_validate(src)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(text, encoding="utf-8")
    tagged = sum(1 for n in nodes if n.get("topics"))
    print(f"→ {OUTPUT_FILE.relative_to(REPO_ROOT)}: {len(nodes)} nodes ({tagged} with topics)")


if __name__ == "__main__":
    sys.exit(main())
