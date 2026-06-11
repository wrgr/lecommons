# Learning Engineering Commons (lecommons)

Shared research corpus and tooling for the IEEE ICICLE / learning engineering community: a
structured, YAML-first registry of the field's people, organizations, programs, papers, and grey
literature, plus the scripts that maintain and expand it.

> **The Capability Matters website has moved.** The Astro site previously under `site/` now lives
> in [`wrgr/capabilitymatters`](https://github.com/wrgr/capabilitymatters) and deploys
> [capabilitymatters.org](https://capabilitymatters.org) from there. It consumes this repo's
> landscape corpus through committed snapshots (run `npm run sync:registry` in that repo with this
> one checked out alongside). LEBOK (Learning Engineering Body of Knowledge) will eventually be
> linked from that project as a wiki.

## What's here

- `landscape/` — the field-review corpus. One YAML record per resource under
  `landscape/resources/<type>/` (people, organizations, programs, conferences, papers,
  grey literature, journals, standards, tools, history timeline), typed JSON exports under
  `landscape/data/`, plus research (`landscape/research/`) and synthesis docs. Schema and id
  conventions: `landscape/README.md`.
- `scripts/` — corpus maintenance tooling (below).
- `titlesearch/` — the "learning engineers" title-search study: reports, data, and analysis
  (`titlesearch/PROVENANCE.md`).
- `corpus/expansion/` — OpenAlex expansion artifacts retained from earlier pipeline runs.
- `archive/` — the previous generation of the website and corpus pipeline, frozen for reference;
  its own docs live in `archive/REBUILD_STATUS.md` and `archive/corpus/README.md`.

## Corpus workflow

YAML records under `landscape/resources/` are the source of truth.

1. Edit or add records (ids are namespaced `LE-…`; see `landscape/README.md`).
2. Rebuild the typed JSON exports consumed downstream:

```bash
pip install -r scripts/requirements.txt   # PyYAML
python3 scripts/build_typed_json.py
```

3. To refresh the website's data snapshots, run `npm run sync:registry` in a
   `wrgr/capabilitymatters` checkout sitting next to this repo (its sync script reads
   `landscape/resources/` directly, or honors `LECOMMONS_DIR`).

## Scripts

- `build_typed_json.py` — regenerate `landscape/data/*.json` from the YAML records (consumed by
  lebokai's `scripts/enrich.ts` and other downstream tools).
- `add_people_from_json.py` — create person YAMLs from a JSON list of contributor specs
  (dry run by default; `--write` to apply).
- `add_provenance.py` — backfill a provenance `source` field on YAML records that lack one.
- `enrich_key_works.py` — top up `key_works` on person records via OpenAlex.
- `expand_corpus_from_chairs.py` — add top LE-relevant papers authored by conference-chair people
  to the paper corpus via OpenAlex.
- `convert_archive_to_yaml.py`, `convert_endnotes_to_yaml.py` — one-shot converters that seeded
  the YAML paper corpus from the archived pipeline's outputs.

The OpenAlex-backed scripts read `OPENALEX_MAILTO` (and optionally `OPENALEX_API_KEY`) from the
environment or a gitignored repo-root `.env` (see `.env.example`).
