"""Search the web for people with a 'Learning Engineer' title at companies in companies.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = ROOT / "people" / "companies.json"
OUT_DIR = ROOT / "people" / "raw"

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
SLEEP_SEC = 2.0

# Reject machine-learning job titles; keep genuine ed-tech LE hits.
_ML_RE = re.compile(
    r"\bmachine\s+learning\b|\b(?:deep|reinforcement|robot)\s+learning\s+engineer\b",
    re.IGNORECASE,
)
_LE_RE = re.compile(r"\blearning\s+engineer", re.IGNORECASE)

# Name: 2-4 capitalised words, no org-noise tokens.
_ORG_NOISE = re.compile(
    r"\b(learning|university|college|institute|agency|center|school|foundation"
    r"|academy|corporation|consulting|technologies|solutions|labs|inc|llc|ltd"
    r"|group|network|council|system|platform)\b",
    re.IGNORECASE,
)
_NAME_RE = re.compile(r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){1,3})")

# Patterns that extract a name + optional org from a snippet or title.
_SENIORITY = r"(?:Senior |Lead |Principal |Staff |Associate )?"
_ORG_SUFFIX = r"(?:\s+(?:at|with|@|,|en)\s+([A-Za-z][A-Za-z\s&.]{1,44}?(?=[,.|)\n]|$)))?"
_INTRO_PATTERNS = [
    re.compile(rf"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){{1,3}}),\s+a\s+{_SENIORITY}learning engineer{_ORG_SUFFIX}", re.IGNORECASE),
    re.compile(rf"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){{1,3}})\s+is\s+a\s+{_SENIORITY}learning engineer{_ORG_SUFFIX}", re.IGNORECASE),
    re.compile(rf"^([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){{1,3}})\s*[-–|]\s*{_SENIORITY}learning engineer{_ORG_SUFFIX}", re.IGNORECASE),
    re.compile(rf"^([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){{1,3}}),\s+{_SENIORITY}learning engineer{_ORG_SUFFIX}", re.IGNORECASE),
    re.compile(rf"[Bb]y\s+([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){{1,3}})[,\s–-]+{_SENIORITY}learning engineer{_ORG_SUFFIX}", re.IGNORECASE),
]
_HTML_TAGS = re.compile(r"<[^>]+>")


def load_companies(path: Path) -> list[dict]:
    """Load the companies list from companies.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["companies"]


def brave_search(query: str, api_key: str, count: int = 20) -> list[dict]:
    """Run a Brave Search API query; return normalised {title, url, snippet} list."""
    params = urllib.parse.urlencode({"q": query, "count": count, "search_lang": "en"})
    req = urllib.request.Request(
        f"{BRAVE_URL}?{params}",
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
                for r in data.get("web", {}).get("results", [])
            ]
        except Exception as exc:
            print(f"  Brave error (attempt {attempt+1}): {exc}")
            time.sleep(4 * (2 ** attempt))
    return []


def is_le_hit(text: str) -> bool:
    """Return True if text mentions learning engineer but not ML variants."""
    return bool(_LE_RE.search(text)) and not bool(_ML_RE.search(text))


def looks_like_name(text: str) -> bool:
    """Return True if text looks like a human name (2-4 words, no org-noise tokens)."""
    words = text.strip().split()
    if not 2 <= len(words) <= 4:
        return False
    if _ORG_NOISE.search(text):
        return False
    return all(re.match(r"^[A-Z][a-zA-Z\-']+$", w) for w in words)


def extract_person(result: dict, company: str, today: str) -> dict | None:
    """Try to extract a named person from a search result; return None if not found."""
    title = _HTML_TAGS.sub("", result.get("title", ""))
    snippet = _HTML_TAGS.sub("", result.get("snippet", ""))
    combined = f"{title} {snippet}".strip()
    if not is_le_hit(combined):
        return None
    name, org = "", ""
    for text in (title, combined):
        for pat in _INTRO_PATTERNS:
            m = pat.search(text)
            if m:
                candidate = m.group(1).strip()
                if looks_like_name(candidate):
                    name = candidate
                    org = (m.group(2) or company).strip().rstrip(".,;)(")
                    break
        if name:
            break
    if not name:
        return None
    # Pull a short title phrase from around the match.
    lm = _LE_RE.search(combined)
    start = max(0, lm.start() - 15)
    title_phrase = re.sub(r"\s+", " ", combined[start:lm.end() + 25]).strip()
    return {
        "source": "WS",
        "name": name,
        "title_as_found": title_phrase,
        "organization": org,
        "company_searched": company,
        "result_url": result.get("url", ""),
        "snippet": combined[:300],
        "date_collected": today,
        "needs_verification": True,
    }


def build_queries(company: str) -> list[str]:
    """Return search queries for a given company name."""
    return [
        f'"{company}" "learning engineer" -"machine learning" -"reinforcement learning" -"deep learning"',
        f'site:linkedin.com/in "learning engineer" "{company}" -"machine learning"',
    ]


def main() -> None:
    """Search Brave for learning engineers at each company in companies.json."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.environ.get("BRAVE_API_KEY", ""), help="Brave Search API key (default: $BRAVE_API_KEY)")
    parser.add_argument("--tiers", nargs="+", default=None, help="Restrict to specific tier codes, e.g. --tiers 1 2 (default: all)")
    parser.add_argument("--out", default=str(OUT_DIR / f"WS_company_search_{date.today().isoformat()}.jsonl"), help="Output JSONL path")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Set BRAVE_API_KEY or pass --api-key")

    companies = load_companies(COMPANIES_PATH)
    if args.tiers:
        companies = [c for c in companies if c["tier"] in args.tiers]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    print(f"Searching {len(companies)} companies | output: {out_path}")
    total = 0
    for entry in companies:
        company = entry["company"]
        for query in build_queries(company):
            print(f"  {query}")
            results = brave_search(query, args.api_key)
            for result in results:
                record = extract_person(result, company, today)
                if record is None:
                    continue
                with out_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                total += 1
                print(f"    + {record['name']} ({record['organization']})")
            time.sleep(SLEEP_SEC)

    print(f"\nDone. {total} candidate records written to {out_path}")


if __name__ == "__main__":
    main()
