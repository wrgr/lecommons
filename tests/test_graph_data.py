"""Validate the Explore graph data files: taxonomy codes resolve and required fields exist.

Guards competencies.json, the pedagogy fields on pathways.json, and the vendored
lebokai_nodes.json against the canonical topic/concept taxonomy so a bad code or a
missing field fails the build rather than silently breaking the graph.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA = REPO_ROOT / "site" / "src" / "data"


def _load(name: str):
    """Load a JSON data file from site/src/data by filename."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _valid_topics() -> set[str]:
    """Return the set of canonical topic codes (T00–T17)."""
    return {t["topic_code"] for t in _load("topic_map.json")}


def _valid_concepts() -> set[str]:
    """Return the set of canonical concept codes (C01–C35)."""
    return {c["concept_id"] for c in _load("concept_ontology.json")}


def test_competency_codes_resolve() -> None:
    """Every competency's topic and concept codes exist in the taxonomy."""
    topics, concepts = _valid_topics(), _valid_concepts()
    for comp in _load("competencies.json"):
        assert comp["topics"], f"{comp['id']} has no topics"
        for code in comp["topics"]:
            assert code in topics, f"{comp['id']}: unknown topic {code}"
        for code in comp["concepts"]:
            assert code in concepts, f"{comp['id']}: unknown concept {code}"


def test_pathways_have_pedagogy() -> None:
    """Every pathway carries a non-empty pedagogy rationale for the graph detail panel."""
    for pw in _load("pathways.json"):
        assert pw.get("pedagogy"), f"pathway {pw['id']} missing pedagogy"


def test_learner_journey_codes_resolve() -> None:
    """Every learner journey's topic and concept codes exist in the taxonomy."""
    topics, concepts = _valid_topics(), _valid_concepts()
    for j in _load("learner_journeys.json"):
        assert j["topics"], f"journey {j['id']} has no topics"
        for code in j["topics"]:
            assert code in topics, f"{j['id']}: unknown topic {code}"
        for code in j["concepts"]:
            assert code in concepts, f"{j['id']}: unknown concept {code}"


def test_lebokai_nodes_topics_valid() -> None:
    """Vendored lebokai node topics are all real taxonomy codes (if the manifest is present)."""
    path = DATA / "lebokai_nodes.json"
    if not path.exists():
        return  # manifest is synced separately; absence is not a failure here
    topics = _valid_topics()
    nodes = json.loads(path.read_text(encoding="utf-8"))
    assert nodes, "lebokai_nodes.json is empty"
    for node in nodes:
        for code in node.get("topics", []):
            assert code in topics, f"{node['slug']}: unknown topic {code}"


if __name__ == "__main__":
    test_competency_codes_resolve()
    test_pathways_have_pedagogy()
    test_learner_journey_codes_resolve()
    test_lebokai_nodes_topics_valid()
    print("graph data OK")
