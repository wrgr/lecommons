"""Unit tests for fast-path paper enrichment stub in `scripts/build_dataset.py`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_dataset import _paper_enrichment_stub, build_path_first_graph


class PaperEnrichmentStubTests(unittest.TestCase):
    def test_stub_counts_papers(self) -> None:
        seed = [{"id": "a", "abstract": "x", "abstract_source": "openalex", "abstract_is_proxy": False}]
        hop = [{"id": "W1", "abstract": "", "abstract_source": "", "abstract_is_proxy": False}]
        out = _paper_enrichment_stub(seed, hop)
        self.assertEqual(out["papers_total"], 2)
        self.assertGreaterEqual(out["papers_missing_abstract"], 1)
        self.assertIn("full_text_cache_total_entries", out)
        self.assertEqual(out["full_text_cache_total_entries"], 0)

    def test_path_first_graph_filters_to_spine_edge_types(self) -> None:
        graph = {
            "nodes": [
                {"id": "T00", "type": "topic"},
                {"id": "C01", "type": "concept"},
                {"id": "P1", "type": "paper"},
                {"id": "R1", "type": "resource"},
            ],
            "edges": [
                {"source": "T00", "target": "C01", "type": "has_concept"},
                {"source": "C01", "target": "P1", "type": "core_evidence"},
                {"source": "T00", "target": "R1", "type": "resource"},
            ],
        }
        out = build_path_first_graph(graph)
        self.assertEqual(len(out["edges"]), 2)
        self.assertEqual({e["type"] for e in out["edges"]}, {"has_concept", "core_evidence"})
        self.assertEqual({n["id"] for n in out["nodes"]}, {"T00", "C01", "P1"})


if __name__ == "__main__":
    unittest.main()
