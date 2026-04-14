# Learning Engineers Study — Query Provenance Log

**Study goal:** Identify individuals who self-apply the title "learning engineer" (or close variants) across professional and academic networks.  
**Study date:** 2026-04-14  
**Lead:** [redacted]  
**Branch:** `claude/learning-engineers-research-7Ij1K`

---

## Methodology artifacts

| File | Purpose |
|------|---------|
| `people/companies.json` | Curated company seed list (~120 orgs, 11 tiers); read by scraper scripts |
| `scripts/github_le_search.py` | GitHub bio search via date-range bisection; writes to `people/raw/GH_bio_search_DATE.jsonl` |
| `scripts/web_le_search.py` | Brave Search per-company queries; writes to `people/raw/WS_company_search_DATE.jsonl` |

Run commands:
```bash
# GitHub (requires GITHUB_TOKEN env var)
python3 scripts/github_le_search.py

# Web search per company (requires BRAVE_API_KEY env var)
python3 scripts/web_le_search.py --tiers 1 2   # specific tiers
python3 scripts/web_le_search.py                # all tiers
```

---

## Source inventory

| Source ID | Platform | Access method | Known limitations |
|-----------|----------|---------------|-------------------|
| LI | LinkedIn | PhantomBuster + Business trial | US-biased; trial may be rate-limited; incomplete global coverage |
| GH | GitHub | GitHub search API / manual | Self-reported bios only; skews technical |
| GS | Google Scholar | Manual / API | Only surfaces published authors; sparse for practitioners |
| RG | ResearchGate | Manual | Academic bias; subset of GS population |
| WS | Brave Search | Brave API | Broad but unstructured; coverage varies |
| TW | Twitter/X | Manual / API | Self-reported bios; API access constrained |

---

## Query log

Each entry records one discrete search action. `raw_file` links to the file in `people/raw/` containing unprocessed results.

---

### Q001
- **Date:** 2026-04-14
- **Source:** LI (LinkedIn)
- **Query type:** Keyword search
- **Scope:** United States
- **Query string:** `"learning engineer"`
- **Filters:** Title field only (PhantomBuster title scrape)
- **Result count:** _[to be filled]_
- **Raw file:** `people/raw/Q001_LI_keyword_US.jsonl`
- **Notes:** First pass; US-scoped to test completeness before global run.

---

### Q002
- **Date:** 2026-04-14
- **Source:** RG (ResearchGate via Google site: search)
- **Query type:** Google site-scoped keyword search
- **Scope:** Global
- **Query string:** `site:researchgate.net/profile "learning engineer" -"machine learning" -"deep learning" -"reinforcement learning"`
- **URL:** `https://www.google.com/search?q=site:researchgate.net/profile+%22learning+engineer%22+-%22machine+learning%22+-%22deep+learning%22+-%22reinforcement+learning%22&start=10`
- **Result count:** ~20 shown (Google suppressed additional similar results; `start=10` = page 2 of results — **page 1 not yet captured**)
- **Raw file:** `people/raw/Q002_RG_google_site_search_p2.jsonl`
- **Included in CSV:** 13 records (10 explicit self-ID; 3 probable self-ID with truncated snippets)
- **Skipped:** 3 records (Rod Roscoe — descriptive panel context; Volodymyr Kukharenko — article about concept; Priyavrat Thareja — metaphorical usage); 2 publication-only results (no person profile)
- **Notes:** URL in paste shows start=10 (page 2) but user confirmed both pages were captured in the same paste; all ~20 results are logged. Three ASU people (McCaleb, Oster, Jongewaard) co-author a Jan 2026 chapter and all use "As learning engineer…"; snippets truncated so title confirmation pending. Blakesley formerly at CMU Eberly Center per a separate PDF in the same SERP.

---

### Q003
- **Date:** 2026-04-14
- **Source:** GS (Google Scholar via Google search)
- **Query type:** Google Scholar keyword search (query string not captured — reconstruct from context)
- **Scope:** Global
- **Query string:** Not provided; inferred as `"learning engineer"` on Google Scholar (similar exclusion filters to Q002 likely applied)
- **URL:** Not captured
- **Result count:** ~15 results page 1 (per Google's "omitted entries similar to the 15 already displayed" note) + 10 results page 2; both pages captured across two sequential pastes
- **Raw file:** `people/raw/Q003_GS_google_scholar_both_pages.jsonl`
- **New people added to CSV:** 4 (Lauren Totino, Tyree Cowell, Kyoung Whan Choe, Yongsung Kim); Gautam Yadav already in CSV as P001
- **Notes:** GS surfacing mechanism is distinct from RG — query hits co-author panels on other people's profiles, so many results are profile *subjects* who are not learning engineers themselves but have an LE person in their network. Yongsung Kim's title "Machin Learning Engineer" is an apparent typo for "Machine Learning Engineer" — different field, triage=no. Kyoung Whan Choe ("Robot Learning Engineer") is a title variant worth tracking. Page 1 appeared to have ~15 results but only the last 5 were captured in the paste; full page 1 content may be incomplete.

---

<!-- Add new query blocks here. Copy the template below. -->

### Q004
- **Date:** 2026-04-14
- **Source:** LI (LinkedIn)
- **Query type:** Keyword search — broad term exclusions
- **Scope:** Global
- **Query string:** `"learning engineer" NOT ("machine" OR "deep" OR "robot" OR "reinforcement")`
- **URL:** `https://www.linkedin.com/search/results/people/?keywords=%22learning%20engineer%22%20NOT%20%28%22machine%22%20OR%20%22deep%22%20OR%20%22robot%22%20OR%20%22reinforcement%22%29&origin=FACETED_SEARCH`
- **Run count:** 1
- **Result count:** _[to be filled when results pasted]_
- **Raw file:** `people/raw/Q004_LI_keyword_global_broad_exclusions.jsonl`
- **Notes:** Broadest exclusion set — single words rather than phrases, so e.g. any profile mentioning "machine" at all is excluded; may over-exclude. Results to follow.

---

### Q005
- **Date:** 2026-04-14
- **Source:** LI (LinkedIn)
- **Query type:** Keyword search — phrase exclusions
- **Scope:** Global
- **Query string:** `"learning engineer" NOT ("machine learning" OR "reinforcement learning" OR "robot learning" OR "deep learning")`
- **URL:** `https://www.linkedin.com/search/results/people/?keywords=%22learning%20engineer%22%20NOT%20%28%22machine%20learning%22%20OR%20%22reinforcement%20learning%22%20OR%20%22robot%20learning%22%20OR%20%22deep%20learning%22%29&origin=TYPEAHEAD_ESCAPE_HATCH`
- **Result count:** _[to be filled when results pasted]_
- **Raw file:** `people/raw/Q005_LI_keyword_global_phrase_exclusions.jsonl`
- **Notes:** Narrower exclusion logic than Q004 (full phrases, not single words); should retain more true LE results. Origin=TYPEAHEAD_ESCAPE_HATCH suggests it was entered via the main search bar.

---

### Q006
- **Date:** 2026-04-14
- **Source:** LI (LinkedIn)
- **Query type:** Title field search — phrase exclusions
- **Scope:** Global
- **Query string:** `title:"learning engineer" NOT ("machine learning" OR "reinforcement learning" OR "robot learning" OR "deep learning")`
- **URL:** `https://www.linkedin.com/search/results/people/?keywords=title%3A%22learning%20engineer%22%20NOT%20%28%22machine%20learning%22%20OR%20%22reinforcement%20learning%22%20OR%20%22robot%20learning%22%20OR%20%22deep%20learning%22%29&origin=GLOBAL_SEARCH_HEADER`
- **Result count:** _[to be filled when results pasted]_
- **Raw file:** `people/raw/Q006_LI_title_global_phrase_exclusions.jsonl`
- **Notes:** Title-scoped search; most precise of the three LI queries — requires "learning engineer" to appear in the job title field specifically. Should yield highest-confidence self-IDs.

<!--
### QXXX
- **Date:** 2026-04-14
- **Source:** 
- **Query type:** 
- **Scope:** 
- **Query string:** 
- **Filters:** 
- **Result count:** 
- **Raw file:** `people/raw/QXXX_SOURCE_desc.jsonl`
- **Notes:** 
-->
