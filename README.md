# Learning Engineering Commons

This repo now serves the Learning Engineering Commons, a topic-linked evidence website, built from the latest corpus pipeline.

## What It Does

- Builds a curated corpus from the workbook + methodology sources.
- Extracts and de-duplicates Learning Engineering Toolkit endnotes.
- Expands citations with OpenAlex one-hop retrieval.
- Applies corpus filters (`cross_seed_score >= 2`, then `2-core + in-degree >= 2`).
- Publishes a static website where each topic is explicitly linked to:
  - seed papers,
  - expansion papers,
  - non-paper resources (programs, people, conferences, tools, orgs).
- The graph UI includes a **Browse nodes** tab that lists every visible graph node (topics, concepts, papers, resources) with the same search and type filters as the canvas, similar in spirit to Resource Navigator. 

## Main Commands

1. Build corpus package:

```bash
python3 scripts/build_corpus.py
```

1. Run OpenAlex expansion:

```bash
python3 scripts/run_openalex_expansion.py \
  --seed-file corpus/expansion_seed_queries.jsonl \
  --output-dir corpus/expansion \
  --max-forward-per-seed 100
```

1. Apply graph filters and produce final expansion subset:

- Current final filtered file:
  - `corpus/expansion/candidates_cross_seed_ge2_kcore2_indegree2.jsonl`

1. Build website data from corpus outputs:

```bash
python3 scripts/build_dataset.py
```

The script loads `**OPENALEX_MAILTO**` / `**OPENALEX_API_KEY**` from a repo-root `**.env**` file when present (same pattern as `build_merged_site_dataset.py`); existing shell environment wins.

For a **fast rebuild** after editing registries (for example `[corpus/tables/programs_people_registry.json](corpus/tables/programs_people_registry.json)`) without re-running OpenAlex/CrossRef abstract enrichment, use:

```bash
python3 scripts/build_dataset.py --skip-paper-enrichment
```

Same behavior: set `**SKIP_PAPER_ENRICHMENT=1**` in the environment.

To populate a **full-text paper cache** (PDF-first, HTML fallback) for downstream retrieval workflows:

```bash
python3 scripts/build_dataset.py --prime-full-text-cache
```

Useful options:

- `--full-text-cache-max-papers 50` to cap a run while testing.
- `--refresh-full-text-cache` to re-fetch entries already present in cache.

Cache file: `[archive/corpus/cache/paper_full_text_cache.json](archive/corpus/cache/paper_full_text_cache.json)`.
Progress log (updated per paper): `[archive/corpus/cache/full_text_progress.log](archive/corpus/cache/full_text_progress.log)`.
For live progress in a terminal, run:

```bash
tail -f archive/corpus/cache/full_text_progress.log
```

Tune limits via env vars: `FULL_TEXT_CACHE_MAX_CHARS`, `FULL_TEXT_CACHE_MAX_PDF_PAGES`, `FULL_TEXT_CACHE_MIN_CHARS`.
Network fetch behavior is configurable with `URL_FETCH_TIMEOUT_SEC` (default `30`), `URL_FETCH_SLEEP_SEC` (default `0.08`), and `URL_FETCH_MAX_RETRIES` (default `4`).

1. Serve website locally:

```bash
python3 -m http.server 8000
# open http://127.0.0.1:8000/            — curated edition: index.html (default graph + data/)
# open http://127.0.0.1:8000/merged.html — broadened corpus (merged graph + Core/Expanded)
```

The hero and footer on each page link to the other HTML entry point so you can switch editions without typing URLs.

1. Regenerate the **broadened** merged bundle (OpenAlex + distilled broad-lane papers under `data/merged/`):

```bash
python3 scripts/build_merged_site_dataset.py
```

1. Import new citation lists (LEBOK-style) into `site/src/content/reading-list/`:

```bash
# dry-run (shows what would be created/skipped)
python3 site/scripts/import_lebok_refs.py --input /path/to/citations.txt

# write mode (creates new MDX stubs, dedupes against existing reading-list)
python3 site/scripts/import_lebok_refs.py --input /path/to/citations.txt --write

# then validate/build site
npm --prefix site run build
```

Notes:

- Input can be bullet lists or paragraph-style citations.
- Duplicate detection uses normalized title and URL checks.
- In `--write` mode, a JSON import report is saved under `site/data/import_reports/`.

If OpenAlex returns budget or rate-limit errors, set `**OPENALEX_MAILTO**` (contact email for the API) and optionally `**OPENALEX_API_KEY**` (premium quota) in the environment before running the command. The scripts read them but never print them. You can put the same variables in a `**.env**` file at the repository root (see `[.env.example](.env.example)`); `merged_lane_proposal.py` and `build_merged_site_dataset.py` load it automatically when present. Existing shell environment variables take precedence over `.env`.

`build_merged_site_dataset.py` skips any lane row whose `work_id` already appears as `**openalex_id**` on a seed or one-hop paper (dedupe), and drops duplicate `work_id` entries in `lane_work_specs.json`. Skips are recorded under `merged_lane_specs_skipped` in `data/merged/build_summary.json`. Each surviving lane work is fetched from OpenAlex with **outer retries** (on top of the client’s own handling of rate limits); per-work timing is in `**merged_lane_openalex_fetch_log`**.

Edit `corpus/merged_lane/lane_work_specs.json` before re-running. Each row is an OpenAlex `work_id` plus `topic_codes`, `corpus_tier`, and optional `**source_expansion**` (`thematic`  `program`  `person`) with `**registry_program_id**` / `**registry_person_id**` matching IDs in `[corpus/tables/programs_people_registry.json](corpus/tables/programs_people_registry.json)`.

**Completeness vs. the rest of the corpus:** `lane_work_specs` only lists *representative* broad-lane papers fetched for `data/merged/` (it is not meant to duplicate every seed/one-hop work). Optional thematic harvests are documented in `[corpus/merged_lane/openalex_thematic_queries.json](corpus/merged_lane/openalex_thematic_queries.json)`; add chosen works to `lane_work_specs` after you run those searches. **Tracked coverage:** `[corpus/merged_lane/coverage_manifest.json](corpus/merged_lane/coverage_manifest.json)` declares which registry IDs and minimum thematic rows must appear in `lane_work_specs`; tests enforce it—update both files when you expand coverage.

**Provenance / rerun:** After `build_merged_site_dataset.py`, `data/merged/build_summary.json` includes `**merged_lane_input_provenance`** (SHA-256 of `lane_work_specs.json`, thematic queries, coverage manifest, and programs/people registry, plus optional `git_head`). Together with `**merged_lane_specs_skipped**`, `**merged_lane_openalex_fetch_log**`, and `**built_merged_at_utc**`, you can tell exactly which inputs produced the bundle and rerun with confidence.

**Growing the lane from the registry (people-first):** `[corpus/tables/programs_people_registry.json](corpus/tables/programs_people_registry.json)` already lists programs and people. `scripts/merged_lane_proposal.py` uses each **approved or seed person** (`content_type` **PP**) to (1) resolve an OpenAlex **author** via name search, (2) pull that author’s works sorted by `**cited_by_count`**, and (3) write proposed lane rows to `**corpus/merged_lane/proposed_lane_additions.json**`, skipping anything already in seed, one-hop, `lane_work_specs`, or `data/merged/papers_merged_lane.json`. Set `**OPENALEX_MAILTO**` before running.

**Permissive inclusion defaults** live in `[corpus/merged_lane/proposal_inclusion.json](corpus/merged_lane/proposal_inclusion.json)` (low `**min_citations`**, higher `**per_person**`, more `**max_pages**` for API list scans). Override via CLI flags or `**--strict**` for the older, tighter thresholds. Expect noise at low citation floors—**always** run `**prune_merged_lane_offtopic.py`** after a build when casting a wide net.

```bash
OPENALEX_MAILTO=you@example.edu python3 scripts/merged_lane_proposal.py
# Smoke-test one registry id:
OPENALEX_MAILTO=you@example.edu python3 scripts/merged_lane_proposal.py --only-resource-id LE-PP-010 --per-person 5
```

**One-shot automation (harvest → merge proposed → build):** `scripts/run_merged_lane_automation.py` loads `**.env`** (for `**OPENALEX_MAILTO**` / optional key), runs `**harvest_ieee_icicle_conference_works.py**` (writes `**ieee_conference_seed_work_ids.json**`), `**merge_proposed_into_lane_work_specs.py**` (appends `**proposed_lane_additions.json**` into `**lane_work_specs.json**`, deduped), and `**build_merged_site_dataset.py**`. Flags: `**--skip-harvest**`, `**--skip-merge**`, `**--skip-build**`, `**--with-citing-expansion**` (optional forward citation pass).

**Conference breadth:** `[corpus/merged_lane/icicle_adjacent_conference_queries.json](corpus/merged_lane/icicle_adjacent_conference_queries.json)` lists many venue-style OpenAlex searches (IEEE ICICLE, L@S, EDM, AIED, LAK, ITS, ICLS, …) with per-query caps. The harvester trusts those searches (see `**trust_query`**) so proceedings are not dropped by the narrow ICICLE title heuristic. Default **global** cap is **10000** unique `**work_ids`** (`--max-total`); use `**harvest_ieee_icicle_conference_works.py --merge-existing**` to union new ids with prior `**work_ids**`. Prepaid OpenAlex API access is recommended for large harvests—see [OpenAlex pricing](https://openalex.org/pricing).

```bash
python3 scripts/run_merged_lane_automation.py
```

**Parallel proposal runs (multiple workers / agents):** `scripts/merged_lane_proposal_workers.py` runs one `merged_lane_proposal.py` subprocess per **PP** registry row (each with `--only-resource-id`), using the same `**proposal_inclusion.json`**, writes shards under `**corpus/merged_lane/proposal_shards/**`, then merges `**lane_rows**` into `**corpus/merged_lane/proposed_lane_additions.json**` (deduped by `**work_id**`). Use a low `**--jobs**` (default **2**) to reduce OpenAlex rate-limit risk. `**--merge-only`** skips subprocesses and only merges existing shard files after a partial run.

```bash
OPENALEX_MAILTO=you@example.edu python3 scripts/merged_lane_proposal_workers.py --jobs 2
```

**One-hop citation expansion (papers citing merged-lane works):** after `data/merged/papers_merged_lane.json` exists, collect works that **cite** those seeds (forward hop in OpenAlex’s citation graph) for manual curation into `lane_work_specs` or a future automated merge. By default, seeds are the **union** of merged-lane paper ids and any `**work_ids`** listed in `[corpus/merged_lane/ieee_conference_seed_work_ids.json](corpus/merged_lane/ieee_conference_seed_work_ids.json)` (IEEE / ICICLE **proceedings** papers with OpenAlex ids are often missing from the classic seed JSON—add them here so each gets a 1-hop citing pass). Use `**--no-merged`** or point `**--seed-list-json**` at a non-existent path to skip one side. `**--work-id W…**` adds more ids to that union.

```bash
python3 scripts/collect_citing_works_openalex.py
# Or: python3 scripts/collect_citing_works_openalex.py --work-id W1234567890 --max-per-seed 50
# Work-id only (no merged bundle, no ieee seed file): use --no-merged and e.g. --seed-list-json /dev/null
```

**Two-hop (exploratory):** `collect_citing_works_openalex.py` supports `**--rounds 2`**: after hop 1 from the base seeds, it uses the top `**cited_by_count**` hop-1 candidates (up to `**--max-round2-seeds**`, default **80**) as seeds for a second OpenAlex hop. Output rows include `**hop_round`** (1 or 2). You can still chain manual reruns using `**--work-id**` lists from a previous `citing_one_hop_candidates.json` if you prefer.

**ICICLE and grey literature (site resources):** registry-driven and Excel ingest paths (`scripts/ingest_excel_resources.py`, `[corpus/tables/icicle_resources_registry.json](corpus/tables/icicle_resources_registry.json)`) feed `**build_dataset.py`** → `data/icicle_resources.json`. Dedicated site scraping of IEEE ICICLE pages is **not** automated here yet—treat SIG/resource URLs in the registry as the source of truth until a scraper is added.

**Classic corpus one-hop (seed → citing papers):** unchanged pipeline—`scripts/run_openalex_expansion.py` from `[corpus/expansion_seed_queries.jsonl](corpus/expansion_seed_queries.jsonl)` → filtered candidates → `build_dataset.py` → `papers_one_hop.json`.

If OpenAlex matches the wrong author (common names), add an override map in `**corpus/merged_lane/openalex_author_overrides.json`** — keys are `**resource_id**` (e.g. `LE-PP-010`), values are OpenAlex author IDs or full `https://openalex.org/A…` URLs. **Review** each proposed row (title and citations appear under `**_proposal_audit`**), drop `**_proposal_audit**` when merging, append the rest into `**lane_work_specs.json**`, update `**coverage_manifest.json**` if you change minimums, then rerun `**build_merged_site_dataset.py**`.

**Programs and venues (PC, CE, …):** the proposal script does not yet map whole programs to OpenAlex automatically (no institution IDs in the registry). Use **manual exemplar works** per program in `lane_work_specs`, or run searches from `[corpus/merged_lane/openalex_thematic_queries.json](corpus/merged_lane/openalex_thematic_queries.json)` and add chosen `work_id`s by hand.

**Pruning bad author matches:** after bulk proposals, run `python3 scripts/prune_merged_lane_offtopic.py --write` to drop lane rows whose **titles** match obvious non-education patterns (materials science, clinical trials, unrelated physics, etc.), using titles from `data/merged/papers_merged_lane.json`. Review `[corpus/merged_lane/offtopic_prune_audit.json](corpus/merged_lane/offtopic_prune_audit.json)`, adjust `corpus/merged_lane/coverage_manifest.json` if thematic minimums change, then rerun `build_merged_site_dataset.py`.

## Website Data Outputs

Generated by `scripts/build_dataset.py` in `data/`:

- `icicle_resources.json` — **all** rows from `corpus/non_paper_resources.jsonl` plus `[corpus/tables/icicle_resources_registry.json](corpus/tables/icicle_resources_registry.json)` and `[corpus/tables/programs_people_registry.json](corpus/tables/programs_people_registry.json)`. Rows with an unknown `primary_topic` are assigned `**T00`** (field overview) instead of being dropped; rows missing `resource_id` get a stable synthetic `**R-REG-…**` id so they appear in the graph and Resource Navigator. Rebuild after editing those tables.
- `programs_summary.json` — one entry per resource row for the programs merge (including unknown `content_type` as category `**other**`).
- `build_summary.json`
- `graph.json`
- `topic_map.json`
- `papers_seed.json`
- `papers_one_hop.json`
- `programs_landscape_removal_gaps.json` (what the old programs panel covered vs Resource Navigator / papers; prioritizes paper linkage)
- `gaps.json`
- `endnotes_raw.json`
- `endnotes_enriched.json`
- `extra_docs.json`

**Broadened edition** adds under `data/merged/` (after step 6 above):

- `build_summary.json` — includes `merged_lane_papers`, `merged_lane_core`, `merged_lane_expanded`
- `graph.json` — classic graph plus merged-lane paper nodes (`hop: 2`) and topic links
- `papers_merged_lane.json` — distilled broad-corpus lane with `corpus_tier` and `source_lane`

## Current Snapshot

From `data/build_summary.json`:

- Seed papers: `21`
- Expansion papers: `274`
- Non-paper resources: `26`
- Topics: `18`
- Graph nodes: `339`
- Graph edges: `1261`

## Notes

- Website code was restored from `feature/vertex-rag` and updated to use the fresh corpus data model.
- Topic-to-paper and topic-to-resource links are explicit in `data/graph.json` and `data/icicle_resources.json`.
- RAG modules remain present under `rag/` for downstream retrieval workflows.

## Explore page — learner journeys → LEBOK knowledge graph

The Astro site's **Explore** page (`site/src/pages/explore.astro`, menu item "Explore")
renders an interactive, client-side force-directed graph that reconfigures around a
chosen **learner journey**, **theme**, **competency**, or **role**, focusing on the
specific **leaf** topic pages of the [LEBOK](https://github.com/wrgr/lebokai) wiki. Each
page node exposes its evidence & examples (lecommons resources tagged to its topics) and,
on click, its full prose + references fetched from the LEBOK site.

Data sources:

- `site/src/data/learner_journeys.json` — 6 staged learner journeys, generated from the
  archive by `python3 scripts/build_learner_journeys.py`; also supplies the role filter.
- `site/src/data/pathways.json` — 5 thematic threads (each carries a `pedagogy` note).
- `site/src/data/competencies.json` — competency selectors (topic/concept/standards codes).
- `site/src/data/lebokai_nodes.json` — **vendored** copy of lebokai's `public/graph-nodes.json`.
- Shared graph logic lives in `site/src/scripts/focusGraph.ts`.

To refresh the LEBOK node data after lebokai regenerates its manifest
(`npm run build:graph` in the lebokai repo):

```bash
python3 scripts/sync_lebokai_nodes.py           # copies ../lebokai/public/graph-nodes.json
# or point at a different checkout:
LEBOKAI_DIR=/path/to/lebokai python3 scripts/sync_lebokai_nodes.py
```

Validate the graph data files with `python3 tests/test_graph_data.py`.

The build-time **Topic Map** page (`site/src/pages/graph.astro`) bakes a static SVG via
d3-force; its client interactivity (hover, detail panel, "open topic page" link) lives in
`site/src/scripts/topicMap.ts`.

## Site lens — Researcher vs. Practitioner

The header "Site lens" toggle switches every page between two experiences, persisted in
`localStorage` under `lec-audience-mode` (values `academic` = Researcher, `practitioner`).
The choice is a single attribute — `html[data-audience="…"]` — set **before first paint** by
an inline script in `site/src/layouts/Base.astro`, so the theme never flashes. A one-time
`LensChooser` dialog (`site/src/components/LensChooser.astro`) prompts first-time visitors.

- **Researcher** (default): the dense, cool, serif "reference index" — papers, citations,
  concept ontology, and Bloom levels are exposed.
- **Practitioner**: a plainer, roomier, warmer sans-serif treatment (theme tokens are
  re-pointed in `Base.astro`); academic scaffolding is hidden and problem-first, how-to
  affordances lead.

The lens drives content visibility through two global utility classes defined in
`Base.astro`: `.lens-only--researcher` and `.lens-only--practitioner` (usable at section or
item level). Micro-copy still uses the older paired `.lens-academic` / `.lens-practitioner`
spans. Guarded with `python3 tests/test_lens_assets.py`.

This site is under rapid dev
