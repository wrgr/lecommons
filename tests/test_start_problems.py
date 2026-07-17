"""Validate start_problems.json: every problem link resolves to a real topic or section.

Guards the practitioner Start page's curated links so a bad topic code or an
unknown section slug fails the build rather than shipping a broken link.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA = REPO_ROOT / "site" / "src" / "data"
PAGES = REPO_ROOT / "site" / "src" / "pages"

# Section links point at top-level pages; each must exist as pages/<slug>.astro.
ALLOWED_SECTIONS = {"practice", "tools", "explore", "graph", "reading-list", "community"}


def _valid_topics() -> set[str]:
    """Return the set of canonical topic codes (T00–T17)."""
    topic_map = json.loads((DATA / "topic_map.json").read_text(encoding="utf-8"))
    return {t["topic_code"] for t in topic_map}


def test_start_problem_links_resolve() -> None:
    """Every Start-page link is either a known topic code or a real section page."""
    topics = _valid_topics()
    problems = json.loads((DATA / "start_problems.json").read_text(encoding="utf-8"))
    assert problems, "start_problems.json is empty"
    for prob in problems:
        assert prob["title"] and prob["blurb"], f"{prob['id']} missing title/blurb"
        assert prob["links"], f"{prob['id']} has no links"
        for link in prob["links"]:
            if "topic" in link:
                assert link["topic"] in topics, f"{prob['id']}: unknown topic {link['topic']}"
            else:
                section = link["section"]
                assert section in ALLOWED_SECTIONS, f"{prob['id']}: unknown section {section}"
                assert (PAGES / f"{section}.astro").exists(), f"{prob['id']}: no page for {section}"
