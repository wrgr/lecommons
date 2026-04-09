from __future__ import annotations

import unittest

from rag.corpus import LexicalRetriever, RetrievalDocument
from rag.engine import RAGEngine
from rag.policy import QueryPolicy
from rag.vertex import LocalGroundedGenerator


class RAGEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        docs = [
            RetrievalDocument(
                doc_id="topic:ch05",
                title="Chapter 5: Learning Engineering Uses Data",
                text="Chapter 5 focuses on instrumentation and collecting learner interaction data.",
                metadata={"type": "topic"},
            ),
            RetrievalDocument(
                doc_id="paper:W123",
                title="Data-driven Learner Modeling",
                text="The paper links instrumentation events to analytics and iterative improvement.",
                metadata={"type": "paper", "source_url": "https://openalex.org/W123"},
            ),
        ]
        retriever = LexicalRetriever(docs)
        policy = QueryPolicy(
            domain_keywords={"learning", "engineering", "instrumentation", "analytics"},
            min_domain_overlap=2,
        )
        self.engine = RAGEngine(
            retriever=retriever,
            policy=policy,
            generator=LocalGroundedGenerator(),
            min_retrieval_score=0.0,
        )

    def test_in_scope_returns_answer(self):
        response = self.engine.ask(
            "How do instrumentation and analytics support learning engineering?"
        )
        self.assertEqual(response.status, "answer")
        self.assertTrue(response.citations)

    def test_out_of_scope_refused(self):
        response = self.engine.ask("What is the weather in Miami this weekend?")
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.refusal_reason, "out_of_scope")


if __name__ == "__main__":
    unittest.main()
