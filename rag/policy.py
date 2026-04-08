from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

from .corpus import tokenize


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    reason: Optional[str] = None
    message: Optional[str] = None
    matched_terms: Optional[List[str]] = None


class QueryPolicy:
    def __init__(self, domain_keywords: Iterable[str], min_domain_overlap: int = 2):
        self.domain_keywords: Set[str] = {k.lower() for k in domain_keywords if k}
        self.min_domain_overlap = min_domain_overlap

        self.controversial_patterns = [
            re.compile(p, re.I)
            for p in (
                r"\b(election|vote|democrat|republican|campaign)\b",
                r"\b(gaza|ukraine|war|genocide|terrorism)\b",
                r"\b(abortion|gun control|2nd amendment)\b",
                r"\b(religion|jesus|allah|torah|bible|quran)\b",
            )
        ]
        self.high_risk_patterns = [
            re.compile(p, re.I)
            for p in (
                r"\b(legal advice|lawsuit|sue|tax evasion)\b",
                r"\b(diagnose|prescription|medical advice|treatment plan)\b",
                r"\b(insider trading|stock tip|guaranteed return)\b",
                r"\b(build a bomb|weaponize|malware|phishing)\b",
            )
        ]
        self.general_off_topic_patterns = [
            re.compile(p, re.I)
            for p in (
                r"\b(weather|forecast|temperature)\b",
                r"\b(sports score|nba|nfl|mlb|nhl)\b",
                r"\b(movie|celebrity|recipe|travel itinerary)\b",
                r"\b(crypto price|bitcoin price|stock price)\b",
            )
        ]

    def evaluate(self, query: str) -> PolicyDecision:
        raw = (query or "").strip()
        if not raw:
            return PolicyDecision(
                allow=False,
                reason="out_of_scope",
                message="I can only answer specific questions about the learning-engineering knowledge base.",
            )

        for pattern in self.high_risk_patterns:
            if pattern.search(raw):
                return PolicyDecision(
                    allow=False,
                    reason="controversial_or_high_risk",
                    message="I cannot help with high-risk or sensitive advisory requests.",
                )
        for pattern in self.controversial_patterns:
            if pattern.search(raw):
                return PolicyDecision(
                    allow=False,
                    reason="controversial_or_high_risk",
                    message="I cannot answer controversial or polarizing topics in this assistant.",
                )

        terms = set(tokenize(raw))
        matched = sorted(terms & self.domain_keywords)
        if len(matched) >= self.min_domain_overlap:
            return PolicyDecision(allow=True, matched_terms=matched)

        for pattern in self.general_off_topic_patterns:
            if pattern.search(raw):
                return PolicyDecision(
                    allow=False,
                    reason="out_of_scope",
                    message="That question is outside this assistant's learning-engineering scope.",
                )

        # Fall back to scope refusal when question has little lexical support in the domain.
        return PolicyDecision(
            allow=False,
            reason="out_of_scope",
            message="I can answer questions grounded in the learning-engineering knowledge graph and topic corpus.",
            matched_terms=matched,
        )
