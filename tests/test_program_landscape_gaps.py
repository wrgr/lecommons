"""Validates programs panel removal gap log schema for CI."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GAP_FILE = REPO / "data" / "programs_landscape_removal_gaps.json"


class ProgramsLandscapeGapsTests(unittest.TestCase):
    def test_gaps_file_exists_and_schema(self) -> None:
        self.assertTrue(GAP_FILE.is_file(), f"missing {GAP_FILE}")
        data = json.loads(GAP_FILE.read_text(encoding="utf-8"))
        self.assertTrue(data.get("title"))
        self.assertIsInstance(data.get("removed_ui"), dict)
        self.assertIsInstance(data.get("where_content_lives_now"), dict)
        self.assertIsInstance(data.get("not_fully_covered_below"), list)
        self.assertIsInstance(data.get("paper_coverage_priorities"), list)
        self.assertTrue(data["paper_coverage_priorities"])
        for item in data["not_fully_covered_below"]:
            self.assertIn("area", item)
            self.assertIn("detail", item)


if __name__ == "__main__":
    unittest.main()
