"""Scrapes GitHub API, web search (Brave or Google CSE), and public job boards for people using 'Learning Engineer' as a job title.

Excludes any variant containing 'machine learning'. Appends new records to
data/people.jsonl; company leads from job boards go to data/company_leads.jsonl.
Run: python3 scripts/scrape_learning_engineers.py [--github] [--web] [--jobs] [--stats]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_PATH = DATA_DIR / "people.jsonl"
COMPANY_LEADS_PATH = DATA_DIR / "company_leads.jsonl"

GITHUB_API_BASE = "https://api.github.com"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

# GitHub Search API returns at most 1000 results per query window.
# Date-range slicing bypasses this cap by recursively bisecting the window.
GITHUB_SEARCH_WINDOW_CAP = 1000
GITHUB_SEARCH_START = "2008-01-01"  # GitHub public launch
# Unauthenticated: 10 req/min → 6.5s gap. Authenticated: 5000/hr → 1s is safe.
GITHUB_SLEEP_UNAUTH_SEC = 6.5
GITHUB_SLEEP_AUTH_SEC = 1.0
WEB_SLEEP_SEC = 4.0
PROGRESS_INTERVAL = 10  # print running totals every N profiles inspected

# Reject "machine learning" anywhere in text.
# Reject "[modifier] learning engineer" title phrases where the modifier indicates an ML/AI
# sub-discipline (deep, reinforcement, robot) — these are AI roles, not ed-tech roles.
# Note: "deep learning" / "reinforcement learning" alone are NOT rejected — a genuine
# ed-tech LE might mention those techniques in passing.
_ML_EXCLUDE = re.compile(
    r"\bmachine\s+learning\b"
    r"|\b(?:deep|reinforcement|robot)\s+learning\s+engineer\b",
    re.IGNORECASE,
)
_LE_INCLUDE = re.compile(r"\blearning\s+engineer", re.IGNORECASE)

_SENIORITY = r"(?:Senior |Lead |Principal |Staff |Associate )?"
# Greedy org match stopping at sentence punctuation; max 4 words to avoid runaway matches.
# Includes "en" so Spanish bios ("Learning Engineer en Platzi") also match.
_ORG = r"(?:\s+(?:at|with|@|,|en)\s+([A-Za-z][A-Za-z\s&.]{1,44}?(?=[,.|)\n]|$)))?"
# Name: exactly 2–4 capitalised words so we don't absorb surrounding context.
_NAME = r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){1,3})"

# Patterns that match text INTRODUCING a named individual with their LE title.
# Ordered from most to least specific; first match wins.
_SNIPPET_NAME_TITLE = [
    # Article/bio intro: "April Murphy, a learning engineer at Carnegie Learning"
    re.compile(
        rf"{_NAME},\s+a\s+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Conference abstract: "Name (Learning Engineer, Org)"  or  "Name (Sr. Learning Engineer)"
    re.compile(
        rf"{_NAME}\s*\(\s*{_SENIORITY}learning engineer{_ORG}\s*\)",
        re.IGNORECASE,
    ),
    # Speaker/author bio: "Name is a learning engineer at Org"
    re.compile(
        rf"{_NAME}\s+is\s+a\s+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Resume/LinkedIn title: "Name - Learning Engineer at Org | ..."
    re.compile(
        rf"^{_NAME}\s*[-–|]\s*{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Comma-separated: "Name, Learning Engineer at Org"
    re.compile(
        rf"^{_NAME},\s+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Byline: "By Name, Learning Engineer at Org" or "By Name — Learning Engineer at Org"
    re.compile(
        rf"[Bb]y\s+{_NAME}[,\s–-]+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Spanish: "Soy Name, un Learning Engineer en Org"
    re.compile(
        rf"[Ss]oy\s+{_NAME}[,\s]+un[ao]?\s+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
    # Spanish article without "Soy": "Name, un Learning Engineer en Org"
    re.compile(
        rf"{_NAME},\s+un[ao]?\s+{_SENIORITY}learning engineer{_ORG}",
        re.IGNORECASE,
    ),
]

DDG_QUERIES = [
    # Conference abstract format: "Name (Learning Engineer, Org)"
    '"(learning engineer," OR "(senior learning engineer"',
    # Speaker/author bio pages from known ed-tech publications
    '"learning engineer" author OR speaker site:edsurge.com OR site:gettingsmart.com OR site:the-learning-agency.com',
    # ATD DevLearn conference — speaker bios with explicit titles
    '"learning engineer" speaker site:td.org OR site:devlearn.org OR site:elearningguild.com',
    # ICICLE / IEEE learning engineering community members
    '"learning engineer" site:sagroups.ieee.org OR site:ieeexplore.ieee.org',
    # Ed-tech company staff/team pages with structured bios
    '"learning engineer" site:amplify.com OR site:carnegielearning.com OR site:khanacademy.org',
    # EDUCAUSE — higher-ed tech conference, many LE titles in higher ed
    '"learning engineer" site:educause.edu speaker OR presenter OR bio',
    # "is a learning engineer" intro phrase — only in editorial/bio text
    '"is a learning engineer at" -"machine" -"deep" -"robot"',
    # ISTE conference participants (major K-12 ed-tech conference)
    '"learning engineer" site:iste.org speaker OR presenter',
    # Named individuals with explicit title in articles about their work
    '"learning engineer at carnegie" OR "learning engineer at amplify" OR "learning engineer at ETS" OR "learning engineer at duolingo"',
]


# ---------------------------------------------------------------------------
# Title filtering
# ---------------------------------------------------------------------------

# Words that appear in org names but not human names; used to reject false positives.
_ORG_WORDS = re.compile(
    r"\b(learning|university|college|institute|agency|center|centre|school|foundation"
    r"|academy|association|corporation|consulting|technologies|solutions|labs|inc|llc"
    r"|ltd|group|network|council|consortium|system|platform)\b",
    re.IGNORECASE,
)


def is_le_title(text: str) -> bool:
    """Return True if text contains 'learning engineer' but not 'machine learning'."""
    return bool(_LE_INCLUDE.search(text)) and not bool(_ML_EXCLUDE.search(text))


def looks_like_person_name(text: str) -> bool:
    """Return True if text looks like a 2–4 word human name, not an organisation."""
    words = text.strip().split()
    if not (2 <= len(words) <= 4):
        return False
    if _ORG_WORDS.search(text):
        return False
    # Every word should start with a capital and contain only letters/hyphens
    return all(re.match(r"^[A-Z][a-zA-Z\-']+$", w) for w in words)


def extract_title_phrase(text: str) -> str:
    """Pull a short title phrase around the 'learning engineer' match."""
    match = _LE_INCLUDE.search(text)
    if not match:
        return "Learning Engineer"
    start = max(0, match.start() - 15)
    end = min(len(text), match.end() + 25)
    phrase = text[start:end].strip().split("\n")[0]
    return re.sub(r"\s+", " ", phrase).strip()


# ---------------------------------------------------------------------------
# Record I/O and ID generation
# ---------------------------------------------------------------------------

def load_existing_keys(path: Path) -> set[str]:
    """Return (name|org) dedup keys from an existing people.jsonl."""
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            keys.add(_dedup_key(rec.get("name", ""), rec.get("organization", "")))
        except json.JSONDecodeError:
            continue
    return keys


def _dedup_key(name: str, org: str) -> str:
    """Produce a lowercase dedup key."""
    return f"{name.strip().lower()}|{org.strip().lower()}"


def next_person_id(path: Path) -> str:
    """Return the next LP-NNN ID based on line count in existing file."""
    if not path.is_file():
        return "LP-001"
    count = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
    return f"LP-{count + 1:03d}"


def append_record(record: dict, path: Path) -> None:
    """Append one JSON record to the JSONL output file."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_url(
    url: str,
    headers: Optional[dict[str, str]] = None,
    retries: int = 3,
) -> str:
    """Fetch URL and return response body; retries on transient errors."""
    req = urllib.request.Request(url, headers=headers or {})
    last_exc: Exception = RuntimeError("no attempts")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 403):
                time.sleep(12 * (2 ** attempt))
            else:
                time.sleep(2 ** attempt)
        except Exception as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed {url} after {retries} attempts: {last_exc}") from last_exc


def github_headers() -> dict[str, str]:
    """Return GitHub API headers, adding Bearer token if GITHUB_TOKEN is set."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LE-People-Scraper/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_sleep_sec() -> float:
    """Return the appropriate inter-request delay based on whether a token is set."""
    return GITHUB_SLEEP_AUTH_SEC if os.environ.get("GITHUB_TOKEN") else GITHUB_SLEEP_UNAUTH_SEC


# ---------------------------------------------------------------------------
# GitHub source
# ---------------------------------------------------------------------------

_GITHUB_BIO_QUERY = (
    '"learning engineer" in:bio NOT "machine learning" NOT "deep learning"'
)


def fetch_github_users() -> list[dict]:
    """Return all GitHub users whose bio matches the LE query via date-range slicing.

    Recursively bisects the account-creation date window whenever a window hits
    the 1000-result API cap, giving near-exhaustive coverage of all matching profiles.
    Deduplicates by login so overlapping boundary calls never produce duplicates.
    """
    results: list[dict] = []
    seen: set[str] = set()
    hdrs = github_headers()

    def _fetch_range(start: str, end: str) -> None:
        """Fetch one date window; split in half if it hits the API cap."""
        query = f"{_GITHUB_BIO_QUERY} created:{start}..{end}"
        params = urllib.parse.urlencode({"q": query, "per_page": 30, "page": 1})
        try:
            body = fetch_url(f"{GITHUB_API_BASE}/search/users?{params}", headers=hdrs)
        except RuntimeError as exc:
            print(f"  [github] window {start}..{end} failed: {exc}")
            return
        data = json.loads(body)
        total = data.get("total_count", 0)
        if total == 0:
            return
        if total > GITHUB_SEARCH_WINDOW_CAP:
            # Bisect the window so each half stays under the cap.
            start_dt, end_dt = date.fromisoformat(start), date.fromisoformat(end)
            if start_dt >= end_dt:
                # Single day exceeds cap — accept what the API returns.
                print(f"  [github] Warning: {start} alone has {total} results, capped at 1000")
            else:
                mid = start_dt + (end_dt - start_dt) // 2
                time.sleep(github_sleep_sec())
                _fetch_range(start, mid.isoformat())
                _fetch_range((mid + timedelta(days=1)).isoformat(), end)
                return
        # Collect first page, then remaining pages.
        for page_data in [data]:
            for item in page_data.get("items", []):
                login = item.get("login", "")
                if login and login not in seen:
                    seen.add(login)
                    results.append(item)
        page = 2
        while True:
            params = urllib.parse.urlencode({"q": query, "per_page": 30, "page": page})
            try:
                body = fetch_url(
                    f"{GITHUB_API_BASE}/search/users?{params}", headers=hdrs
                )
            except RuntimeError as exc:
                print(f"  [github] page {page} failed ({start}..{end}): {exc}")
                break
            items = json.loads(body).get("items", [])
            if not items:
                break
            for item in items:
                login = item.get("login", "")
                if login and login not in seen:
                    seen.add(login)
                    results.append(item)
            if len(items) < 30:
                break
            page += 1
            time.sleep(github_sleep_sec())
        print(
            f"  [github] {start}..{end}: {total} in window, "
            f"{len(results)} unique candidates so far"
        )

    today_str = date.today().isoformat()
    print(f"[github] Date-range scan {GITHUB_SEARCH_START}..{today_str}")
    _fetch_range(GITHUB_SEARCH_START, today_str)
    return results


def fetch_github_user_detail(login: str) -> dict:
    """Fetch a single GitHub user's full profile JSON."""
    url = f"{GITHUB_API_BASE}/users/{login}"
    body = fetch_url(url, headers=github_headers())
    return json.loads(body)


def parse_github_user(raw: dict, today: str) -> Optional[dict]:
    """Convert a GitHub profile dict to a person record, or None if title doesn't qualify."""
    bio = (raw.get("bio") or "").strip()
    company = re.sub(r"^@", "", (raw.get("company") or "").strip())
    name = (raw.get("name") or raw.get("login") or "").strip()
    if not name or not is_le_title(bio):
        return None
    blog = (raw.get("blog") or "").strip()
    profile_urls = [u for u in [raw.get("html_url", ""), blog] if u]
    return {
        "record_type": "learning_engineer_person",
        "name": name,
        "title_as_found": extract_title_phrase(bio),
        "organization": company,
        "source_url": raw.get("html_url", ""),
        "source_type": "github_api",
        "profile_urls": profile_urls,
        "location": (raw.get("location") or "").strip(),
        "bio_snippet": bio[:300],
        "date_collected": today,
        "verified": False,
        "notes": "",
    }


def run_github_source(
    existing_keys: set[str], today: str, limit: Optional[int], out_path: Path
) -> int:
    """Fetch all matching GitHub users via date-range scan, inspect profiles, write records."""
    auth = bool(os.environ.get("GITHUB_TOKEN"))
    print(f"[github] Starting full date-range scan ({'authenticated' if auth else 'unauthenticated'})…")
    search_results = fetch_github_users()
    candidates = search_results if limit is None else search_results[:limit]
    print(f"[github] {len(search_results)} unique candidates found, inspecting {len(candidates)}")
    found = 0
    for i, item in enumerate(candidates, 1):
        login = item.get("login", "")
        try:
            detail = fetch_github_user_detail(login)
            time.sleep(github_sleep_sec())
        except RuntimeError as exc:
            print(f"  [github] skipping {login}: {exc}")
            continue
        record = parse_github_user(detail, today)
        if record is None:
            continue
        key = _dedup_key(record["name"], record["organization"])
        if key in existing_keys:
            continue
        existing_keys.add(key)
        record["person_id"] = next_person_id(out_path)
        append_record(record, out_path)
        found += 1
        print(f"  [github] + {record['name']} ({record['organization']})")
        if i % PROGRESS_INTERVAL == 0:
            print(f"  [github] progress: {i}/{len(candidates)} inspected, {found} new found")
    return found


# ---------------------------------------------------------------------------
# Brave Search API source
# ---------------------------------------------------------------------------

def _fetch_brave(query: str) -> list[dict]:
    """Search via Brave Search API; returns normalised result list."""
    params = urllib.parse.urlencode({"q": query, "count": 20, "search_lang": "en"})
    url = f"{BRAVE_SEARCH_URL}?{params}"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": os.environ.get("BRAVE_API_KEY", ""),
    }
    body = fetch_url(url, headers=headers)
    data = json.loads(body)
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in data.get("web", {}).get("results", [])
    ]


def _fetch_serper(query: str) -> list[dict]:
    """Search via Serper.dev (Google results); returns normalised result list.

    Requires SERPER_API_KEY env var.
    Free tier: 2,500 queries on signup. serper.dev
    """
    payload = json.dumps({"q": query, "num": 20}).encode()
    headers = {
        "X-API-KEY": os.environ.get("SERPER_API_KEY", ""),
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(SERPER_SEARCH_URL, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", ""),
        }
        for r in data.get("organic", [])
    ]


def fetch_web_results(query: str) -> list[dict]:
    """Run a web search using whichever API key is configured.

    Priority: Brave (BRAVE_API_KEY) → Serper.dev (SERPER_API_KEY).
    Returns a normalised list of {title, url, snippet} dicts.
    """
    if os.environ.get("BRAVE_API_KEY"):
        try:
            return _fetch_brave(query)
        except RuntimeError as exc:
            print(f"  [web] Brave failed, trying Serper: {exc}")

    if os.environ.get("SERPER_API_KEY"):
        try:
            return _fetch_serper(query)
        except Exception as exc:
            print(f"  [web] Serper search failed: {exc}")
            return []

    print(
        "  [web] No search API key found. Set BRAVE_API_KEY or SERPER_API_KEY (see README)."
    )
    return []


# Keep alias so existing tests that reference _DDGParser still import cleanly.
class _DDGParser:
    """Deprecated stub — replaced by Brave Search API. Kept for test compatibility."""

    def __init__(self) -> None:
        self.results: list[dict] = []

    def feed(self, _html: str) -> None:
        """No-op: DDG HTML parsing is no longer used."""


_HTML_TAGS = re.compile(r"<[^>]+>")


def parse_snippet_for_person(result: dict, today: str) -> Optional[dict]:
    """Attempt to extract a named person record from a web search result snippet."""
    # Search both snippet and title; title alone often has the clearest structure.
    # Strip HTML tags (Brave highlights matches with <strong>…</strong>).
    title = _HTML_TAGS.sub("", result.get("title", ""))
    snippet = _HTML_TAGS.sub("", result.get("snippet", ""))
    combined = f"{title} {snippet}".strip()
    if not is_le_title(combined):
        return None
    name, org = "", ""
    # Try title first (most structured), then full combined text
    for text in (title, combined):
        for pattern in _SNIPPET_NAME_TITLE:
            m = pattern.search(text)
            if m:
                candidate = m.group(1).strip()
                if not looks_like_person_name(candidate):
                    continue
                name = candidate
                org = (m.group(2) or "").strip().rstrip(".,;)(")
                break
        if name:
            break
    if not name:
        return None
    return {
        "record_type": "learning_engineer_person",
        "name": name,
        "title_as_found": extract_title_phrase(combined),
        "organization": org,
        "source_url": result.get("url", ""),
        "source_type": "web_search_snippet",
        "profile_urls": [result.get("url", "")] if result.get("url") else [],
        "location": "",
        "bio_snippet": combined[:300],
        "date_collected": today,
        "verified": False,
        "notes": "Needs manual verification — extracted from search snippet.",
    }


def run_web_source(existing_keys: set[str], today: str, out_path: Path) -> int:
    """Run web search queries, write qualifying person records immediately, return count."""
    found = 0
    for query in DDG_QUERIES:
        print(f"[web] Query: {query}")
        results = fetch_web_results(query)
        print(f"  {len(results)} results")
        for result in results:
            record = parse_snippet_for_person(result, today)
            if record is None:
                continue
            key = _dedup_key(record["name"], record["organization"])
            if key in existing_keys:
                continue
            existing_keys.add(key)
            record["person_id"] = next_person_id(out_path)
            append_record(record, out_path)
            found += 1
            print(f"  [web] + {record['name']} ({record['organization']})")
        time.sleep(WEB_SLEEP_SEC)
    return found


# ---------------------------------------------------------------------------
# Seed company leads — known ed-tech employers that regularly hire Learning Engineers
# ---------------------------------------------------------------------------

# Curated list of organisations known to carry "Learning Engineer" as a job title.
# Sourced from published job postings, ICICLE community, and academic literature.
KNOWN_ED_TECH_EMPLOYERS: list[dict] = [
    {"company": "Carnegie Learning", "notes": "Inventor of the LE title; ITS / MATHia platform"},
    {"company": "Amplify", "notes": "K-12 curriculum and assessment platform"},
    {"company": "Curriculum Associates", "notes": "iReady adaptive learning platform"},
    {"company": "Age of Learning", "notes": "ABCmouse / Adventure Academy"},
    {"company": "Imagine Learning", "notes": "Adaptive K-12 literacy and math"},
    {"company": "Renaissance Learning", "notes": "Star assessments, Accelerated Reader"},
    {"company": "ETS", "notes": "Educational Testing Service; research + assessment"},
    {"company": "Duolingo", "notes": "Language learning; ICICLE community member"},
    {"company": "Khan Academy", "notes": "Free K-12 + higher-ed platform; Khanmigo"},
    {"company": "Newsela", "notes": "News-based literacy platform"},
    {"company": "Pearson", "notes": "Global ed publisher; large LE function"},
    {"company": "McGraw-Hill Education", "notes": "ALEKS adaptive platform"},
    {"company": "Discovery Education", "notes": "K-12 streaming + curriculum"},
    {"company": "Achieve3000", "notes": "Differentiated literacy platform"},
    {"company": "Scholastic", "notes": "K-12 books and classroom content"},
    {"company": "PowerSchool", "notes": "Student information + learning platform"},
    {"company": "IXL Learning", "notes": "Adaptive practice platform"},
    {"company": "Nearpod", "notes": "Interactive lesson delivery"},
    {"company": "Seesaw", "notes": "K-8 learning and portfolio platform"},
    {"company": "Illustrative Mathematics", "notes": "OER math curriculum"},
    {"company": "LearnPlatform", "notes": "EdTech evidence and analytics"},
    {"company": "Turnitin", "notes": "Integrity and writing feedback"},
    {"company": "Instructure", "notes": "Canvas LMS"},
    {"company": "D2L", "notes": "Brightspace LMS"},
    {"company": "Blackboard", "notes": "Now Anthology; enterprise LMS"},
    {"company": "Platzi", "notes": "Latin American online tech education"},
    {"company": "Coursera", "notes": "MOOC platform; content engineering team"},
    {"company": "edX", "notes": "MOOC platform (now 2U)"},
    {"company": "Chegg", "notes": "Tutoring and study support"},
    {"company": "Paper", "notes": "24/7 tutoring platform for K-12"},
]


def run_seed_source(today: str) -> int:
    """Append KNOWN_ED_TECH_EMPLOYERS to company_leads.jsonl; return count of new entries."""
    existing = _load_existing_leads(COMPANY_LEADS_PATH)
    added = 0
    for entry in KNOWN_ED_TECH_EMPLOYERS:
        company = entry["company"]
        # Use empty string as url so the key is just company-name based
        key = f"{company.lower()}|"
        # Also check against any existing url-based key for this company
        company_key = company.lower()
        already = any(k.startswith(company_key + "|") for k in existing)
        if already:
            continue
        existing.add(key)
        lead = {
            "company": company,
            "job_title_found": "Learning Engineer (seeded)",
            "job_url": "",
            "source_type": "manual_seed",
            "date_collected": today,
            "notes": entry.get("notes", ""),
        }
        append_record(lead, COMPANY_LEADS_PATH)
        added += 1
        print(f"  [seed] + {company}")
    return added


# ---------------------------------------------------------------------------
# Job board source (Greenhouse, Lever, Ashby — all public ATS platforms)
# ---------------------------------------------------------------------------

JOB_BOARD_QUERIES = [
    # Greenhouse — largest public ATS; exclude ML noise with ed-tech context words
    '"learning engineer" instructional OR curriculum OR "learning experience" site:boards.greenhouse.io',
    # Lever ATS
    '"learning engineer" instructional OR curriculum site:jobs.lever.co',
    # Ashby ATS
    '"learning engineer" instructional OR curriculum site:jobs.ashbyhq.com',
    # SmartRecruiters ATS
    '"learning engineer" instructional OR curriculum site:jobs.smartrecruiters.com',
    # Workday ATS (major enterprise ed-tech companies use Workday)
    '"learning engineer" instructional OR curriculum site:myworkdayjobs.com',
    # Known ed-tech employers by name — surfaces their job listings on any platform
    '"learning engineer" "carnegie learning" OR "amplify education" OR "curriculum associates" job OR career OR hiring',
    '"learning engineer" "age of learning" OR "imagine learning" OR "renaissance learning" job OR career',
    '"learning engineer" "educational testing" OR "ETS" OR "pearson" OR "mcgraw-hill" job OR career',
    '"learning engineer" "discovery education" OR "scholastic" OR "achieve3000" OR "newsela" job OR career',
    # Ed-tech context (catches postings not on major ATS platforms)
    '"learning engineer" "instructional design" OR "curriculum development" job OR career OR hiring',
]

# Per-company query templates for reverse lookup from company leads.
# {company} is substituted at runtime.
# The LinkedIn variant surfaces public profile snippets via SERP — direct scraping is ToS-violating
# but search engine result snippets for linkedin.com/in URLs are freely accessible.
REVERSE_QUERY_TEMPLATES = [
    '"{company}" "learning engineer" -"machine learning"',
    '"{company}" "learning engineer" profile OR bio OR team -"machine learning"',
    'site:linkedin.com/in "learning engineer" "{company}" -"machine learning"',
]

# Patterns to extract company name from ATS job posting page titles/snippets.
# Ordered from most to least specific; first match wins.
_JOB_TITLE_PATTERNS = [
    # "Learning Engineer [role words] at Company"  /  "Learning Engineer @ Company"
    re.compile(r"Learning Engineer[^|@\n]{0,40}(?:at|@)\s+([A-Z][A-Za-z0-9\s&.']{1,40}?)(?:\s*[|\-,]|$)", re.IGNORECASE),
    # "Role @ Company"  (Ashby/Lever format: "Lead Learning Engineer @ Faculty")
    re.compile(r"Learning Engineer\s+@\s+([A-Z][A-Za-z0-9\s&.']{1,40}?)(?:\s*[|\-,]|$)", re.IGNORECASE),
    # "Company | ... Learning Engineer"  (reversed title)
    re.compile(r"^([A-Z][A-Za-z0-9\s&.']{1,35}?)\s*[|–\-]\s*[^|]*Learning Engineer", re.IGNORECASE),
    # "... - Careers at Company" or "Jobs at Company"
    re.compile(r"(?:careers?|jobs?)\s+at\s+([A-Z][A-Za-z0-9\s&.']{2,40}?)(?:\s*[|\-,]|$)", re.IGNORECASE),
]


def _parse_job_result(result: dict, today: str) -> Optional[dict]:
    """Extract a company lead from a job board search result, or None if not qualifying."""
    combined = f"{result.get('title', '')} {result.get('snippet', '')}".strip()
    if not is_le_title(combined):
        return None
    company = ""
    job_title = extract_title_phrase(combined)
    for pat in _JOB_TITLE_PATTERNS:
        m = pat.search(result.get("title", ""))
        if m:
            company = m.group(1).strip().rstrip(".,;-")
            break
    if not company:
        return None
    return {
        "company": company,
        "job_title_found": job_title,
        "job_url": result.get("url", ""),
        "source_type": "job_board_search",
        "date_collected": today,
        "notes": "",
    }


def _load_existing_leads(path: Path) -> set[str]:
    """Return (company|job_url) dedup keys from an existing company_leads.jsonl."""
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            keys.add(f"{rec.get('company','').lower()}|{rec.get('job_url','').lower()}")
        except json.JSONDecodeError:
            continue
    return keys


def run_job_board_source(today: str) -> list[dict]:
    """Search public ATS job boards for LE postings; return new company leads."""
    existing = _load_existing_leads(COMPANY_LEADS_PATH)
    leads: list[dict] = []
    for query in JOB_BOARD_QUERIES:
        print(f"[jobs] Query: {query}")
        results = fetch_web_results(query)
        print(f"  {len(results)} results")
        for result in results:
            lead = _parse_job_result(result, today)
            if lead is None:
                continue
            key = f"{lead['company'].lower()}|{lead['job_url'].lower()}"
            if key in existing:
                continue
            existing.add(key)
            leads.append(lead)
            print(f"  [jobs] + {lead['company']} — {lead['job_title_found']}")
        time.sleep(WEB_SLEEP_SEC)
    return leads


# ---------------------------------------------------------------------------
# Reverse company search (company leads → named individuals)
# ---------------------------------------------------------------------------

def run_reverse_company_search(
    existing_keys: set[str], today: str, out_path: Path
) -> int:
    """Search for named Learning Engineers at each company in company_leads.jsonl.

    For each company, runs REVERSE_QUERY_TEMPLATES through the web search API —
    including a LinkedIn SERP query that surfaces public profile snippets without
    direct scraping (which would violate LinkedIn ToS).
    """
    if not COMPANY_LEADS_PATH.is_file():
        print("[reverse] No company_leads.jsonl found; run --jobs first.")
        return 0
    companies: list[str] = []
    for line in COMPANY_LEADS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            c = rec.get("company", "").strip()
            if c and c not in companies:
                companies.append(c)
        except json.JSONDecodeError:
            continue
    if not companies:
        print("[reverse] No companies in company_leads.jsonl.")
        return 0
    print(f"[reverse] {len(companies)} company lead(s): {', '.join(companies)}")
    found = 0
    for company in companies:
        for template in REVERSE_QUERY_TEMPLATES:
            query = template.format(company=company)
            print(f"[reverse] Query: {query}")
            results = fetch_web_results(query)
            print(f"  {len(results)} results")
            for result in results:
                record = parse_snippet_for_person(result, today)
                if record is None:
                    continue
                key = _dedup_key(record["name"], record["organization"])
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                record["person_id"] = next_person_id(out_path)
                append_record(record, out_path)
                found += 1
                print(f"  [reverse] + {record['name']} ({record['organization']})")
            time.sleep(WEB_SLEEP_SEC)
    return found


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(people_path: Path, leads_path: Path) -> None:
    """Print a summary of the current people and company leads databases."""
    if not people_path.is_file():
        print("No people.jsonl found yet.")
        return
    people = [
        json.loads(ln)
        for ln in people_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    print(f"\n=== People database: {len(people)} records ===")
    by_source: dict[str, int] = {}
    by_org: dict[str, int] = {}
    needs_verify = 0
    for p in people:
        src = p.get("source_type", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
        org = p.get("organization", "").strip() or "(none)"
        by_org[org] = by_org.get(org, 0) + 1
        if not p.get("verified"):
            needs_verify += 1
    print(f"  Needs verification: {needs_verify}")
    print("  By source:")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")
    print("  Top organizations:")
    for org, count in sorted(by_org.items(), key=lambda x: -x[1])[:15]:
        print(f"    {org}: {count}")
    if leads_path.is_file():
        leads = [ln for ln in leads_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        print(f"\n=== Company leads: {len(leads)} records ===")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse args, run enabled sources, and append new records to people.jsonl."""
    parser = argparse.ArgumentParser(
        description="Scrape for people with 'Learning Engineer' in their title."
    )
    parser.add_argument("--github", action="store_true", help="Run GitHub API source")
    parser.add_argument("--web", action="store_true", help="Run DuckDuckGo web search source")
    parser.add_argument(
        "--jobs",
        action="store_true",
        help="Search public job boards (Greenhouse, Lever, Ashby) for LE postings",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse-search company_leads.jsonl to find named individuals (includes LinkedIn SERP)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Populate company_leads.jsonl with curated list of known ed-tech employers",
    )
    parser.add_argument("--stats", action="store_true", help="Print database stats and exit")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max GitHub profiles to inspect (default: all found by date-range scan)",
    )
    args = parser.parse_args()

    if args.stats:
        print_stats(OUTPUT_PATH, COMPANY_LEADS_PATH)
        return

    # Default: run all sources when no source flag is given (--seed is always explicit)
    no_source_flags = not args.github and not args.web and not args.jobs and not args.reverse and not args.seed
    run_github = args.github or no_source_flags
    run_web = args.web or no_source_flags
    run_jobs = args.jobs or no_source_flags
    run_reverse = args.reverse or no_source_flags
    run_seed = args.seed

    today = date.today().isoformat()
    existing_keys = load_existing_keys(OUTPUT_PATH)
    print(f"Existing records: {len(existing_keys)}  |  Output: {OUTPUT_PATH}")

    total_people = 0

    if run_seed:
        added = run_seed_source(today)
        print(f"  [seed] {added} new company lead(s) written to {COMPANY_LEADS_PATH}")

    if run_github:
        total_people += run_github_source(existing_keys, today, limit=args.limit, out_path=OUTPUT_PATH)

    if run_web:
        total_people += run_web_source(existing_keys, today, out_path=OUTPUT_PATH)

    if run_jobs:
        job_leads = run_job_board_source(today)
        for lead in job_leads:
            append_record(lead, COMPANY_LEADS_PATH)
        print(f"  {len(job_leads)} new company lead(s) written to {COMPANY_LEADS_PATH}")

    if run_reverse:
        total_people += run_reverse_company_search(existing_keys, today, out_path=OUTPUT_PATH)

    print(f"\nDone. {total_people} new person record(s) written to {OUTPUT_PATH}")
    print_stats(OUTPUT_PATH, COMPANY_LEADS_PATH)


if __name__ == "__main__":
    main()
