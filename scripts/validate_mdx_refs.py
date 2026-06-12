"""Validate provenance.ref fields on every MDX entry against the YAML corpus.

For each MDX under site/src/content/, reads `provenance.ref` from the frontmatter
and checks it points to a real resource_id in landscape/data/*.json. Reports:

  - coverage: how many MDX files carry a ref at all
  - orphans: refs that do not match any YAML resource_id (drift)
  - valid: refs that resolve

Exit codes:
  0  no orphans (regardless of coverage)
  1  orphans present when --strict is set
  2  usage or I/O error

Run from the repo root:

    python3 scripts/validate_mdx_refs.py           # report only
    python3 scripts/validate_mdx_refs.py --strict  # fail on orphans

Requires PyYAML (see scripts/requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MDX_DIR = REPO_ROOT / "site" / "src" / "content"
YAML_JSON_DIR = REPO_ROOT / "landscape" / "data"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
ANY_REF_RE = re.compile(r'^\s*ref:\s*"?([^"\n]+)"?\s*$', re.MULTILINE)
LE_REF_RE = re.compile(r"^LE-[A-Z]+-\d+$")


def load_yaml_ids() -> set[str]:
    """Collect every resource_id emitted into landscape/data/*.json."""
    ids: set[str] = set()
    for jf in YAML_JSON_DIR.glob("*.json"):
        data = json.loads(jf.read_text(encoding="utf-8"))
        for rec in data:
            rid = rec.get("resource_id")
            if rid:
                ids.add(rid)
    return ids


def scan_mdx() -> tuple[int, list[tuple[Path, str]], int]:
    """Return (total_mdx_count, LE-ref pairs, non-LE-ref count).

    Non-LE refs (e.g. Excel workbook rows, citation strings) are provenance
    traces, not resource-id pointers, and are reported separately.
    """
    pairs: list[tuple[Path, str]] = []
    non_le = 0
    total = 0
    for mdx in sorted(MDX_DIR.rglob("*.mdx")):
        total += 1
        text = mdx.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        rm = ANY_REF_RE.search(m.group(1))
        if not rm:
            continue
        ref = rm.group(1).strip().strip('"')
        if LE_REF_RE.match(ref):
            pairs.append((mdx, ref))
        else:
            non_le += 1
    return total, pairs, non_le


def main() -> int:
    """Validate MDX provenance.ref fields and print a coverage report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any orphaned ref is found.",
    )
    args = parser.parse_args()

    if not MDX_DIR.is_dir() or not YAML_JSON_DIR.is_dir():
        print(f"Missing directory: {MDX_DIR} or {YAML_JSON_DIR}", file=sys.stderr)
        return 2

    yaml_ids = load_yaml_ids()
    total_mdx, pairs, non_le = scan_mdx()

    orphans: list[tuple[Path, str]] = [
        (p, r) for p, r in pairs if r not in yaml_ids
    ]
    valid = len(pairs) - len(orphans)
    no_ref = total_mdx - len(pairs) - non_le

    print(f"MDX files scanned:       {total_mdx}")
    print(f"  with LE-*-NNN ref:     {len(pairs)}")
    print(f"  with non-LE ref:       {non_le}  (provenance trace, e.g. Excel row)")
    print(f"  without any ref:       {no_ref}")
    print(f"YAML resource_ids:       {len(yaml_ids)}")
    print(f"LE refs resolving:       {valid}")
    print(f"Orphaned LE refs:        {len(orphans)}")

    if orphans:
        print("\nOrphans (ref → file):")
        for path, ref in sorted(orphans, key=lambda t: (t[1], t[0])):
            rel = path.relative_to(REPO_ROOT)
            print(f"  {ref}  {rel}")

    if orphans and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
