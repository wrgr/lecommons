"""Guards the field analysis PDF source and built artifact used for stakeholder communication."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MD_PATH = REPO / "docs" / "field_analysis_learning_engineering_lens.md"
PDF_PATH = REPO / "docs" / "field_analysis_learning_engineering_lens.pdf"


class FieldAnalysisDocTests(unittest.TestCase):
    def test_markdown_has_core_sections(self) -> None:
        text = MD_PATH.read_text(encoding="utf-8")
        for phrase in (
            "Executive summary",
            "Gap opportunities",
            "LENS @ JHU",
            "Literature landscape",
        ):
            self.assertIn(phrase, text)

    def test_pdf_built_and_non_empty(self) -> None:
        self.assertTrue(PDF_PATH.is_file(), "expected pandoc output at docs/")
        self.assertGreater(PDF_PATH.stat().st_size, 8_000, "PDF looks unexpectedly small")


if __name__ == "__main__":
    unittest.main()
