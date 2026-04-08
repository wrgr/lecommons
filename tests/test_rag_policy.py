from __future__ import annotations

import unittest

from rag.policy import QueryPolicy


class QueryPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        domain_keywords = {
            "learning",
            "engineering",
            "instrumentation",
            "analytics",
            "endnotes",
            "chapter",
            "toolkit",
        }
        self.policy = QueryPolicy(domain_keywords=domain_keywords, min_domain_overlap=2)

    def test_allows_in_scope_query(self):
        decision = self.policy.evaluate(
            "How does instrumentation in learning engineering support analytics?"
        )
        self.assertTrue(decision.allow)

    def test_refuses_out_of_scope_query(self):
        decision = self.policy.evaluate("What is tomorrow's weather in Boston?")
        self.assertFalse(decision.allow)
        self.assertEqual(decision.reason, "out_of_scope")

    def test_refuses_controversial_query(self):
        decision = self.policy.evaluate("Who should I vote for in the election?")
        self.assertFalse(decision.allow)
        self.assertEqual(decision.reason, "controversial_or_high_risk")


if __name__ == "__main__":
    unittest.main()
