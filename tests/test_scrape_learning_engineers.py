"""Tests for the Learning Engineer people scraper (scrape_learning_engineers.py)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.scrape_learning_engineers import (
    _DDGParser,
    _dedup_key,
    append_record,
    extract_title_phrase,
    is_le_title,
    load_existing_keys,
    looks_like_person_name,
    next_person_id,
    parse_github_user,
    parse_snippet_for_person,
)


class PersonNameTests(unittest.TestCase):
    def test_valid_two_word_name(self) -> None:
        self.assertTrue(looks_like_person_name("Jane Doe"))

    def test_valid_three_word_name(self) -> None:
        self.assertTrue(looks_like_person_name("Mary Ann Smith"))

    def test_rejects_org_word(self) -> None:
        self.assertFalse(looks_like_person_name("Carnegie Learning"))

    def test_rejects_single_word(self) -> None:
        self.assertFalse(looks_like_person_name("Duolingo"))

    def test_rejects_lowercase(self) -> None:
        self.assertFalse(looks_like_person_name("jane doe"))

    def test_org_false_positive_rejected(self) -> None:
        """Regression: 'Carnegie Learning' must not be treated as a person name."""
        result = {"title": "Something about Carnegie Learning", "url": "https://example.com",
                  "snippet": "Carnegie Learning, a learning engineer at Acme Corp"}
        self.assertIsNone(parse_snippet_for_person(result, "2026-04-13"))


class TitleFilterTests(unittest.TestCase):
    def test_accepts_learning_engineer(self) -> None:
        self.assertTrue(is_le_title("Senior Learning Engineer at Acme"))

    def test_rejects_machine_learning_engineer(self) -> None:
        self.assertFalse(is_le_title("Machine Learning Engineer at Big Co"))

    def test_rejects_machine_learning_in_context(self) -> None:
        self.assertFalse(is_le_title("I'm a learning engineer focused on machine learning"))

    def test_case_insensitive(self) -> None:
        self.assertTrue(is_le_title("LEARNING ENGINEER"))

    def test_empty_string(self) -> None:
        self.assertFalse(is_le_title(""))

    def test_extract_title_phrase(self) -> None:
        phrase = extract_title_phrase("I work as a Learning Engineer at Acme Corp")
        self.assertIn("Learning Engineer", phrase)


class RecordIOTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.path = Path(self._tmp.name)
        self._tmp.close()
        self.path.unlink()  # start empty

    def test_next_id_when_empty(self) -> None:
        self.assertEqual(next_person_id(self.path), "LP-001")

    def test_next_id_increments(self) -> None:
        self.path.write_text('{"name":"A"}\n{"name":"B"}\n', encoding="utf-8")
        self.assertEqual(next_person_id(self.path), "LP-003")

    def test_append_and_reload(self) -> None:
        rec = {"name": "Jane Doe", "organization": "Acme"}
        append_record(rec, self.path)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["name"], "Jane Doe")

    def test_load_existing_keys(self) -> None:
        self.path.write_text(
            json.dumps({"name": "Jane Doe", "organization": "Acme"}) + "\n",
            encoding="utf-8",
        )
        keys = load_existing_keys(self.path)
        self.assertIn("jane doe|acme", keys)

    def test_load_empty_file(self) -> None:
        self.assertEqual(load_existing_keys(self.path), set())

    def test_dedup_key_normalised(self) -> None:
        self.assertEqual(_dedup_key("Jane Doe ", " Acme "), "jane doe|acme")


class GithubParserTests(unittest.TestCase):
    _TODAY = "2026-04-13"

    def _make_raw(self, **kwargs: str) -> dict:
        base = {
            "login": "jdoe",
            "name": "Jane Doe",
            "bio": "Learning Engineer at Acme",
            "company": "@Acme",
            "html_url": "https://github.com/jdoe",
            "blog": "",
            "location": "NYC",
        }
        base.update(kwargs)
        return base

    def test_valid_profile_parsed(self) -> None:
        rec = parse_github_user(self._make_raw(), self._TODAY)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "Jane Doe")
        self.assertEqual(rec["organization"], "Acme")
        self.assertEqual(rec["source_type"], "github_api")

    def test_machine_learning_excluded(self) -> None:
        raw = self._make_raw(bio="Machine Learning Engineer at Big Co")
        self.assertIsNone(parse_github_user(raw, self._TODAY))

    def test_missing_name_excluded(self) -> None:
        raw = self._make_raw(name="", login="")
        self.assertIsNone(parse_github_user(raw, self._TODAY))

    def test_company_at_sign_stripped(self) -> None:
        rec = parse_github_user(self._make_raw(company="@WidgetCo"), self._TODAY)
        self.assertEqual(rec["organization"], "WidgetCo")


class SnippetParserTests(unittest.TestCase):
    _TODAY = "2026-04-13"

    def _result(self, title: str = "", snippet: str = "") -> dict:
        return {"title": title, "url": "https://example.com", "snippet": snippet}

    def test_name_title_org_extracted(self) -> None:
        rec = parse_snippet_for_person(
            self._result(title="Jane Doe - Learning Engineer at WidgetCo"), self._TODAY
        )
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "Jane Doe")
        self.assertIn("WidgetCo", rec["organization"])

    def test_machine_learning_rejected(self) -> None:
        rec = parse_snippet_for_person(
            self._result(title="John Smith - Machine Learning Engineer"), self._TODAY
        )
        self.assertIsNone(rec)

    def test_no_name_returns_none(self) -> None:
        rec = parse_snippet_for_person(
            self._result(snippet="A learning engineer worked here"), self._TODAY
        )
        self.assertIsNone(rec)


class DDGParserTests(unittest.TestCase):
    def test_stub_returns_empty(self) -> None:
        """_DDGParser is a deprecated stub; feed() is a no-op."""
        p = _DDGParser()
        p.feed("<html>anything</html>")
        self.assertEqual(p.results, [])


if __name__ == "__main__":
    unittest.main()
