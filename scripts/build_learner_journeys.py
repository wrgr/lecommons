"""Build site/src/data/learner_journeys.json from the archived staged journey table.

Transforms archive/corpus/tables/learning_journeys.json (one row per journey
stage) into a per-journey structure the Explore page can consume: each journey
carries its ordered stages plus the union of topic/concept codes used for graph
focusing, and a short role label derived from its learner_type.
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / "archive" / "corpus" / "tables" / "learning_journeys.json"
OUT = REPO_ROOT / "site" / "src" / "data" / "learner_journeys.json"

# Short role label per journey id (the learner_type is the long form).
ROLE_BY_JOURNEY = {
    "J-01": "New to LE",
    "J-02": "Systems engineer",
    "J-03": "Researcher",
    "J-04": "LENS student",
    "J-05": "AI / EdTech",
    "J-06": "Time-pressed",
}


def split_codes(raw: str) -> list[str]:
    """Split a comma/space separated code string into a clean list."""
    if not raw:
        return []
    return [c.strip() for c in re.split(r"[,\s]+", raw) if c.strip()]


def anchor_ids(text: str) -> list[str]:
    """Extract LE-* resource ids embedded in a free-text anchor_resources field."""
    return re.findall(r"LE-[A-Z0-9-]+", text or "")


def build() -> list[dict]:
    """Group staged rows into per-journey records with unioned topics/concepts."""
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    journeys: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows:
        jid = r["journey_id"]
        j = journeys.setdefault(jid, {
            "id": jid.lower(), "title": r["journey_name"],
            "learner_type": r.get("learner_type", ""),
            "role": ROLE_BY_JOURNEY.get(jid, r.get("learner_type", "")[:24]),
            "stages": [], "topics": [], "concepts": [],
        })
        topics, concepts = split_codes(r.get("topics", "")), split_codes(r.get("concept_ids", ""))
        j["stages"].append({
            "stage": r.get("stage", ""), "name": r.get("stage_name", ""),
            "topics": topics, "concepts": concepts,
            "anchors": r.get("anchor_resources", ""), "anchor_ids": anchor_ids(r.get("anchor_resources", "")),
        })
        for t in topics:
            if t not in j["topics"]:
                j["topics"].append(t)
        for c in concepts:
            if c not in j["concepts"]:
                j["concepts"].append(c)
    return list(journeys.values())


def main() -> None:
    """Write the per-journey JSON consumed by the Explore page."""
    data = build()
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"→ {OUT.relative_to(REPO_ROOT)}: {len(data)} journeys "
          f"({sum(len(j['stages']) for j in data)} stages)")


if __name__ == "__main__":
    main()
