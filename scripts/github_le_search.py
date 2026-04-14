"""Search GitHub user bios for 'learning engineer', excluding ML role variants."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "people" / "raw"

# Excludes "machine learning", "deep learning", "reinforcement learning"
# as full phrases so bios that merely mention those techniques are retained.
QUERY = (
    '"learning engineer" in:bio '
    'NOT "machine learning" '
    'NOT "reinforcement learning" '
    'NOT "deep learning"'
)

API_BASE = "https://api.github.com"
SEARCH_START = "2008-01-01"  # GitHub public launch
SLEEP_SEC = 1.0              # Safe for authenticated (5000 req/hr)
PAGE_SIZE = 100
CAP = 1000                   # GitHub search API hard cap per window


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def make_headers(token: str) -> dict[str, str]:
    """Build GitHub API request headers with Bearer token."""
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "LE-Study-GH-Search/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get(url: str, headers: dict[str, str]) -> dict:
    """Fetch a GitHub API URL and return parsed JSON; raises on non-2xx."""
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 422:
                raise  # unprocessable — don't retry
            wait = 12 * (2 ** attempt) if exc.code in (429, 403) else 2 ** attempt
            print(f"  HTTP {exc.code} on {url} — retrying in {wait}s")
            time.sleep(wait)
        except Exception as exc:
            time.sleep(2 ** attempt)
            if attempt == 3:
                raise RuntimeError(f"Failed {url}: {exc}") from exc
    raise RuntimeError(f"Exhausted retries for {url}")


# ---------------------------------------------------------------------------
# Search with date-range bisection
# ---------------------------------------------------------------------------

def search_window(
    start: str, end: str, headers: dict[str, str], seen: set[str]
) -> list[dict]:
    """Collect all users created in [start, end]; bisect window if count hits CAP."""
    query = f"{QUERY} created:{start}..{end}"
    params = urllib.parse.urlencode({"q": query, "per_page": PAGE_SIZE, "page": 1})
    data = get(f"{API_BASE}/search/users?{params}", headers)
    total = data.get("total_count", 0)

    if total == 0:
        return []

    start_dt, end_dt = date.fromisoformat(start), date.fromisoformat(end)
    if total > CAP and start_dt < end_dt:
        mid = start_dt + (end_dt - start_dt) // 2
        time.sleep(SLEEP_SEC)
        left = search_window(start, mid.isoformat(), headers, seen)
        right = search_window((mid + timedelta(days=1)).isoformat(), end, headers, seen)
        return left + right

    results: list[dict] = []
    page = 1
    while True:
        items = data.get("items", []) if page == 1 else get(
            f"{API_BASE}/search/users?{urllib.parse.urlencode({'q': query, 'per_page': PAGE_SIZE, 'page': page})}",
            headers,
        ).get("items", [])
        for item in items:
            login = item.get("login", "")
            if login and login not in seen:
                seen.add(login)
                results.append(item)
        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(SLEEP_SEC)

    print(f"  window {start}..{end}: {total} total, {len(results)} new")
    return results


# ---------------------------------------------------------------------------
# Profile detail
# ---------------------------------------------------------------------------

def fetch_profile(login: str, headers: dict[str, str]) -> dict:
    """Fetch full GitHub profile for a given login."""
    return get(f"{API_BASE}/users/{login}", headers)


def to_record(profile: dict, today: str) -> dict:
    """Convert a GitHub profile dict to a study record."""
    return {
        "source": "GH",
        "login": profile.get("login", ""),
        "name": (profile.get("name") or profile.get("login") or "").strip(),
        "bio": (profile.get("bio") or "").strip(),
        "company": (profile.get("company") or "").strip().lstrip("@"),
        "location": (profile.get("location") or "").strip(),
        "blog": (profile.get("blog") or "").strip(),
        "profile_url": profile.get("html_url", ""),
        "followers": profile.get("followers", 0),
        "date_collected": today,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run GitHub bio search for learning engineers and write results to JSONL."""
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub PAT (default: $GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--out",
        default=str(OUT_DIR / f"GH_bio_search_{date.today().isoformat()}.jsonl"),
        help="Output JSONL path",
    )
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("Set GITHUB_TOKEN or pass --token")

    headers = make_headers(args.token)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    seen: set[str] = set()

    print(f"Query: {QUERY}")
    print(f"Date range: {SEARCH_START} → {today}")
    print(f"Output: {out_path}")

    candidates = search_window(SEARCH_START, today, headers, seen)
    print(f"\n{len(candidates)} unique candidates found — fetching full profiles…")

    written = 0
    for i, item in enumerate(candidates, 1):
        login = item.get("login", "")
        try:
            profile = fetch_profile(login, headers)
            time.sleep(SLEEP_SEC)
        except RuntimeError as exc:
            print(f"  [{i}/{len(candidates)}] skipping {login}: {exc}")
            continue
        record = to_record(profile, today)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        written += 1
        if i % 25 == 0 or i == len(candidates):
            print(f"  [{i}/{len(candidates)}] written {written} records")

    print(f"\nDone. {written} records written to {out_path}")


if __name__ == "__main__":
    main()
