# Learning Engineers People Study

**Study date:** 2026-04-14  
**Purpose:** Auditable census of individuals who self-apply the title "learning engineer" across LinkedIn, GitHub, Google Scholar, ResearchGate, Brave Search, and Twitter/X.

## File layout

```
people/
├── README.md              — this file
├── PROVENANCE.md          — full query log (one entry per discrete search)
├── people.csv             — deduplicated master list of individuals
└── raw/
    ├── Q001_LI_keyword_US.jsonl   — raw results, query Q001
    └── ...                        — one file per query
```

## people.csv columns

| Column | Description |
|--------|-------------|
| `id` | Stable row ID (P001, P002, …) assigned on first insertion |
| `name` | Full name as it appears in the source |
| `current_title` | Job title or self-description from the source |
| `organization` | Employer / institution |
| `location` | City/country as reported |
| `source_ids` | Pipe-separated source codes (LI, GH, GS, RG, WS, TW) |
| `query_ids` | Pipe-separated query IDs from PROVENANCE.md that surfaced this person |
| `profile_url` | Primary profile link (LinkedIn URL, GitHub handle, etc.) |
| `date_collected` | ISO date first seen (YYYY-MM-DD) |
| `triage` | `yes` = explicit self-ID; `probable` = strong signal but unconfirmed; `no` = surfaced by query but not a self-ID |
| `triage_reason` | One-line rationale for the triage value |
| `notes` | Free text: variant title, context, dedup notes |

## raw/ file format

Each `QXXX_SOURCE_desc.jsonl` file contains one JSON object per result row as pasted/scraped.
Fields vary by source; preserve the original structure.
Every record should include at minimum: `{"query_id": "QXXX", "source": "LI", "raw": {...}}`.

## Dedup policy

A person is considered the **same individual** if two or more of the following match across sources:
- Full name (case-insensitive, ignoring middle initials)
- Employer + approximate role
- Profile URL or handle

When merging, keep all `source_ids` and `query_ids`, use the most complete name/title/org, and note the merge in `notes`.
