# Landscape: Comprehensive Learning Engineering Field Review

A structured research layer providing a comprehensive view of the learning engineering field: its history, critical people, landmark papers, grey literature, standards, and journals/conferences. This module is intentionally **separate from the main site** and will be folded into the existing corpus pipeline when ready.

## Why This Exists

The main site (`site/`, `archive/`) focuses on curated resources linked to the existing 18-topic knowledge graph. This module goes deeper on field history and intellectual lineage — capturing the foundational literature, key actors, and synthesis documents that explain *why* the field exists and *how* it developed, rather than simply cataloging current resources.

## Contents

```
landscape/
  data/
    history_timeline.json    # Chronological milestones (pre-field → contemporary)
    people.json              # Critical researchers and practitioners (PP type)
    papers.json              # Landmark academic papers (AP type)
    grey_literature.json     # Reports, policy docs, white papers (GL type)
    organizations.json       # Journals, conferences, standards bodies, orgs
  synthesis/
    field_overview.md        # Narrative synthesis of the field
```

## Schema Conventions

All records follow existing `archive/corpus/tables/content_type_taxonomy.json` codes:
- `AP` — Academic Paper
- `GL` — Grey Literature / Report
- `PP` — Person / Practitioner
- `CE` — Conference / Event
- `CO` — Community / Organization
- `SG` — Standard / Guideline
- `TP` — Tool / Platform

Topic codes (`primary_topic`, `secondary_topics`) match `archive/corpus/tables/topic_map.json` (T00–T17).

Resource IDs use `LE-LS-*` namespace to avoid collisions with existing corpus IDs (`LE-T1-*`, `LE-PP-*`, `LE-IC-*`). Strip `LS-` prefix when merging into the main corpus.

## Future Merge Path

When ready to fold into the main site:

1. `landscape/data/people.json` → `archive/corpus/tables/programs_people_registry.json` (append, dedup on name)
2. `landscape/data/papers.json` → `archive/corpus/academic_papers.jsonl` (append) + seed queries
3. `landscape/data/grey_literature.json` → `archive/corpus/non_paper_resources.jsonl` (append)
4. `landscape/data/organizations.json` → `archive/corpus/non_paper_resources.jsonl` + `icicle_resources_registry.json`
5. `landscape/synthesis/field_overview.md` → `site/src/content/` collection (TBD category)

## Status (April 2026)

Data files populated and committed. Pipeline inputs (expansion seeds, venue queries, registry entries) are all wired into `archive/`. The corpus expansion pipeline has **not yet been run** — that is the next step.

See `archive/REBUILD_STATUS.md` → **PICK UP HERE** section for the exact commands.

## Primary Source

Content drawn from: "Comprehensive Landscape of Learning Engineering: An Analysis of Foundational Papers, Contemporary Research, and Grey Literature" (internal document, April 2026), supplemented by web research.
