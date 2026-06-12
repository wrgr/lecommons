"""Add provenance-based tags to all MDX content files.

Ensures every file with a provenance.dataset field carries a corresponding tag:
- ICICLE-sourced datasets → 'icicle'
- LE Resources Excel v1 → 'le-excel-v1'
Skips files that already have the correct tag. Inserts a tags field if none exists.
"""

import re
from pathlib import Path

CONTENT = Path(__file__).resolve().parent.parent / "src" / "content"

DATASET_TO_TAG = {
    "IEEE ICICLE resources page (web harvest)": "icicle",
    "IEEE ICICLE resources page (web harvest) + curated extensions": "icicle",
    "IEEE ICICLE programs & people registry": "icicle",
    "IEEE ICICLE Invitation to LE Webinar Series page": "icicle",
    "IEEE ICICLE Invitation to LE Webinar Series page (sagroups.ieee.org/icicle/invitation-to-learning-engineering-webinar-series/)": "icicle",
    "Derived from ICICLE registry": "icicle",
    "LE Resources Excel v1": "le-excel-v1",
}


def extract_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (before_fm, frontmatter, after_fm) split on --- delimiters."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, "", ""
    return parts[0], parts[1], parts[2]


def get_dataset(fm: str) -> str | None:
    """Extract provenance.dataset value from frontmatter text."""
    match = re.search(r'dataset:\s*"([^"]+)"', fm)
    return match.group(1) if match else None


def has_tag(fm: str, tag: str) -> bool:
    """Check if a tag already exists in the frontmatter."""
    return bool(re.search(rf'^\s*-\s*"{re.escape(tag)}"', fm, re.MULTILINE))


def add_tag(fm: str, tag: str) -> str:
    """Add a tag to frontmatter. Creates tags field if it doesn't exist."""
    if re.search(r"^tags:", fm, re.MULTILINE):
        # Insert new tag at end of existing tags list
        lines = fm.split("\n")
        result = []
        in_tags = False
        inserted = False
        for i, line in enumerate(lines):
            if line.startswith("tags:"):
                in_tags = True
                result.append(line)
                continue
            if in_tags:
                if line.strip().startswith("- "):
                    result.append(line)
                    # Check if next line is still a tag entry
                    if i + 1 < len(lines) and not lines[i + 1].strip().startswith("- "):
                        result.append(f'  - "{tag}"')
                        inserted = True
                        in_tags = False
                else:
                    if not inserted:
                        result.append(f'  - "{tag}"')
                        inserted = True
                    result.append(line)
                    in_tags = False
            else:
                result.append(line)
        if in_tags and not inserted:
            result.append(f'  - "{tag}"')
        return "\n".join(result)
    else:
        # Insert tags field before provenance field
        lines = fm.split("\n")
        result = []
        inserted = False
        for line in lines:
            if line.startswith("provenance:") and not inserted:
                result.append("tags:")
                result.append(f'  - "{tag}"')
                inserted = True
            result.append(line)
        if not inserted:
            result.append("tags:")
            result.append(f'  - "{tag}"')
        return "\n".join(result)


def main() -> None:
    """Process all MDX files and add provenance tags."""
    updated = 0
    skipped = 0
    no_match = 0

    for mdx in sorted(CONTENT.rglob("*.mdx")):
        text = mdx.read_text()
        before, fm, after = extract_frontmatter(text)
        if not fm:
            no_match += 1
            continue

        dataset = get_dataset(fm)
        if not dataset:
            no_match += 1
            continue

        tag = DATASET_TO_TAG.get(dataset)
        if not tag:
            print(f"  UNKNOWN dataset: {dataset} in {mdx.relative_to(CONTENT)}")
            no_match += 1
            continue

        if has_tag(fm, tag):
            skipped += 1
            continue

        new_fm = add_tag(fm, tag)
        mdx.write_text(f"{before}---{new_fm}---{after}")
        print(f"  + {tag:12s} → {mdx.relative_to(CONTENT)}")
        updated += 1

    print(f"\nDone: {updated} updated, {skipped} already had tag, {no_match} no matching dataset")


if __name__ == "__main__":
    main()
