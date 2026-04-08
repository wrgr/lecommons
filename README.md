# Learning Engineering Resource Graph (MVP)

This repository contains a lightweight, structured synthesis of learning engineering resources and citations.

The MVP is intentionally small and migration-friendly: it aligns to the broader EBKGC architecture but focuses on a usable first artifact.

## Canonical Inputs

- IEEE ICICLE resources page (source of truth): https://sagroups.ieee.org/icicle/resources/
- *Learning Engineering Toolkit* PDFs (two parts provided locally)
- ICICLE adjacent programs document (exported text)
- User-provided architecture/context files, including:
  - `Figure1_DKG_Architecture.svg`
  - `EBKGC_Paper_Draft.docx`
  - `LENS_Prospective_Students_040726_draft.docx`
- Manual seed explicitly added:
  - Goodell, J., Kessler, A., Kurzweil, D., Kolodner, J. (2020). *Competencies of Learning Engineering Teams and Team Members*. IEEE ICICLE proceedings.

## What This MVP Produces

- Topic graph from:
  - Toolkit chapter structure (parts + chapters)
  - ICICLE resources section structure
- Explicit topic-to-citation linkage (section -> chapter -> seed citation edges)
- Parsed endnote corpus with explicit `artifact_type` tags
- DOI-first enriched seed-paper metadata (title, abstract if available, plain citation, BibTeX)
- One-hop citation expansion from matched seed papers
- Structured summary of key programs (academic/nonprofit/commercial), including LENS at JHU
- Gap synthesis for next iterations
- A static interactive page (`index.html`) with:
  - topic + citation graph
  - clickable node inspector with per-node provenance
  - one-hop toggle
  - resource organization view
  - artifact/paper cards with citations and BibTeX
  - program summaries and surfaced gaps

## Current Build Snapshot

From `data/build_summary.json`:

- Parsed endnotes: **296**
- Processed endnotes: **296**
- Matched enriched endnotes: **60** (DOI-first pass)
- Seed papers in graph: **59**
- One-hop papers in graph: **178**
- ICICLE resource items extracted: **171**

Artifact type distribution (from parsed endnotes):

- `article_report_or_web`: 196
- `paper_or_article`: 46
- `conference_artifact`: 16
- `book_or_chapter`: 16
- `video`: 11
- `standard_or_spec`: 9
- `webinar`: 1
- `software_or_repository`: 1

Notes:

- Not all endnotes are papers; books/videos/web resources are intentionally retained and tagged.
- DOI-first enrichment favors precision and runtime stability for MVP. Non-DOI enrichment is deferred to a later pass.

## Methodology (MVP)

The pipeline follows a reduced version of your architecture:

1. Seed ingestion
- Fetch ICICLE canonical resources page.
- Extract Toolkit text from both PDF parts.
- Load adjacent-program context and user-specified manual seeds.

2. Extraction and normalization
- Parse ICICLE sections and links into structured JSON.
- Parse chapter headings into topic nodes.
- Parse endnotes into citation/artifact entries with typed classification.

3. Evidence enrichment
- Resolve DOI-backed entries to OpenAlex metadata.
- Build plain-text citations and BibTeX per resolved work.
- Add one-hop expansion from referenced works.

4. Graph assembly
- Topic-part -> chapter edges.
- ICICLE section -> chapter topic edges.
- Chapter -> seed-paper edges from endnotes.
- Seed-paper -> one-hop-paper edges from OpenAlex references.

5. Synthesis outputs
- Program summary by category.
- Gap report for missing/weak structures.

## Education-Technical Grounded Synthesis Process (Detailed)

This project treats synthesis as both an educational design problem and a technical evidence-integration problem.
The goal is not only to aggregate links, but to produce a structure that educators, researchers, and learning engineers can inspect, trace, and reuse.

1. Educational grounding
- Organize content around instructional and practice-relevant structures (topic parts, chapter topics, program categories, and gaps).
- Preserve mixed artifact types (papers, books, standards, webinars, videos, repositories) because learning engineering practice depends on more than journal literature alone.
- Keep evidence legible for human interpretation through plain citations, BibTeX, source links, and chapter linkage.
- Anchor structure to validated educational methods, especially competency-oriented curriculum mapping and constructive alignment between topics, evidence, and intended practice use.

2. Technical grounding
- Use deterministic parsing and normalization for source extraction, chapter detection, endnote segmentation, and artifact typing.
- Use DOI-first metadata resolution to maximize precision and reduce false positive paper matching.
- Build explicit graph edges (`icicle_section -> topic_part/topic -> seed paper -> one-hop paper`) so each relationship is inspectable.
- Keep generated outputs in versionable JSON artifacts to support reproducibility and incremental migration.

3. Synthesis and quality controls
- Separate parsed evidence from inferred synthesis so downstream users can distinguish source facts from generated summaries.
- Surface unresolved areas through an explicit gap layer instead of hiding uncertainty.
- Prioritize stable MVP behavior (precision over recall) and defer weaker enrichment modes to later iterations.

4. Role of LLM technologies in this workflow
- LLMs are used as synthesis accelerators: drafting summaries, clustering themes, and helping convert heterogeneous evidence into readable, decision-support language.
- LLMs are not treated as a sole source of truth: canonical sources, parsed citations, DOI-resolved metadata, and graph linkages remain the grounding substrate.
- Outputs are most reliable when LLM-assisted interpretation is paired with deterministic extraction, explicit provenance, and human review.

5. Anchoring to validated methods (cross-domain)
- Educational methods: competency mapping and practice-focused organization patterns from learning engineering and instructional design.
- Bibliometric methods: DOI normalization, citation-link construction, one-hop network expansion, and precision-first matching before recall expansion.
- Technical methods: deterministic parsing, typed artifacts, explicit graph schemas, and reproducible build outputs.
- Governance principle: generated synthesis is always traceable back to source artifacts and is expected to be reviewable by domain experts.

## Files

- Build script: `scripts/build_dataset.py`
- Knowledge ops script: `scripts/knowledge_ops.py`
- Main page: `index.html`
- UI entrypoint: `app.js`
- UI modules: `app/components/*.js` and `app/*.js`
- Styling: `styles.css`
- Generated datasets: `data/*.json`

Key generated files:

- `data/icicle_resources.json`
- `data/topics_chapters.json`
- `data/endnotes_raw.json`
- `data/endnotes_enriched.json`
- `data/papers_seed.json`
- `data/papers_one_hop.json`
- `data/graph.json`
- `data/programs_summary.json`
- `data/gaps.json`
- `data/extra_docs.json`
- `data/rag_corpus.jsonl`

## Run / Rebuild

### Rebuild data (fast, no external enrichment)

```bash
python3 scripts/build_dataset.py --skip-openalex --seed-limit 296
```

### Rebuild data (DOI-first enrichment + one-hop)

```bash
python3 scripts/build_dataset.py --seed-limit 296 --doi-only --hop-per-seed 5 --hop-total-limit 180
```

### Serve the page locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

### SWE guardrail lint

Run repository-level checks for:
- separation of concerns and mixed-responsibility files
- file-size and long-function warnings
- memory-bank docs presence (`docs/tech-stack.md`, `docs/architecture.md`, `docs/progress.md`)
- stale dependency hygiene (pinning/range checks)
- broken local imports and suspicious markdown path references

```bash
python3 scripts/swe_lint.py
```

Optional live dependency staleness check (requires network/tooling):

```bash
python3 scripts/swe_lint.py --check-outdated
```

### Search/webscan/upload and refresh corpus + RAG

Search and ingest top results, then rebuild `data/rag_corpus.jsonl`:

```bash
python3 scripts/knowledge_ops.py search \
  --query "learning engineering competency framework" \
  --max-results 8 \
  --scan-results 5 \
  --tag competency
```

Scan specific URLs:

```bash
python3 scripts/knowledge_ops.py webscan \
  --url "https://sagroups.ieee.org/icicle/resources/" \
  --url "https://oli.cmu.edu/" \
  --tag web-source
```

Upload local documents:

```bash
python3 scripts/knowledge_ops.py upload \
  --path "/path/to/notes.md" \
  --path "/path/to/brief.pdf" \
  --tag local-upload
```

Run all in one command:

```bash
python3 scripts/knowledge_ops.py sync \
  --query "evidence-centered design learning engineering" \
  --url "https://learningatscale.asu.edu/" \
  --path "/path/to/research_memo.docx" \
  --scan-results 4
```

Rebuild only the RAG corpus from current dataset + external docs:

```bash
python3 scripts/knowledge_ops.py rebuild-corpus
```

### RAG API admin endpoints

If you run the FastAPI app (`rag/api.py`), these endpoints are available:

- `POST /admin/sync` - accepts query/urls/paths and runs the same ingestion flow.
- `POST /admin/rebuild-corpus` - rebuilds `data/rag_corpus.jsonl` and reloads engine.
- `POST /admin/reload` - hot-reloads the in-memory RAG engine.

## Surfaced Gaps (MVP)

After scanning adjacent ICICLE pages (`data/icicle_page_scan.json`), gaps are reassessed in `data/gaps.json`:

- `resolved`: Role-based pathways
  - Evidence found across SIG/MIG, meetings, and conference pages for Higher Ed, pK-12, Government/Military, Workforce, and Students/Grads.
- `partial`: Reusable technical assets
  - Templates/checklists/case-study artifacts are present, but robust reusable datasets/APIs/code assets remain uneven.
- `flagged`: Citation metadata coverage
  - Many endnotes are non-DOI artifacts and still require stronger metadata linking beyond DOI-first enrichment.

Uncertainty/staleness lifecycle is still conceptual in MVP and not yet fully operationalized in UI.

## Next Migration Steps

- Add full multi-source convergence scoring (not just parsed linkage).
- Expand enrichment beyond DOI-only with stronger title/URL matching.
- Add assertion-level provenance UI and review queue mechanics.
- Add uncertainty/staleness flags and human-in-the-loop validation flows.
- Transition from static JSON to versioned corpus + incremental update jobs.
