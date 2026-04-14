# Learning Engineers Study — Query Provenance Log

**Study goal:** Identify individuals who self-apply the title "learning engineer" (or close variants) across professional and academic networks.  
**Study date:** 2026-04-14  
**Lead:** [redacted]  
**Branch:** `claude/learning-engineers-research-7Ij1K`

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
- **Notes:** Page 1 (start=0) not captured; run separately as Q003. Three ASU people (McCaleb, Oster, Jongewaard) co-author a Jan 2026 chapter and all use "As learning engineer…"; snippets truncated so title confirmation pending. Blakesley formerly at CMU Eberly Center per a separate PDF in the same SERP.

---

<!-- Add new query blocks here. Copy the template below. -->

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
