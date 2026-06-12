# Learning Engineering Commons (lecommons)

Shared research corpus, tooling, and website for the IEEE ICICLE / learning engineering
community: a structured, YAML-first registry of the field's people, organizations, programs,
papers, and grey literature — published as the **Learning Engineering Commons** at
[lecommons.org](https://lecommons.org).

Sibling projects:

- [`wrgr/capabilitymatters`](https://github.com/wrgr/capabilitymatters) →
  [capabilitymatters.org](https://capabilitymatters.org) — the LENS @ JHU editorial lens site.
  The Commons references LENS; LENS links back here for resources.
- [`wrgr/lebok`](https://github.com/wrgr/lebok) — the Learning Engineering Body of Knowledge,
  growing into a community-editable wiki with editorial review, linked prominently from the
  Commons.

## What's here

- `site/` — the Commons website (Astro), deployed to lecommons.org by
  `.github/workflows/deploy-gh-pages.yml`. See `site/README.md`.
- `landscape/` — the field-review corpus. One YAML record per resource under
  `landscape/resources/<type>/` (people, organizations, programs, conferences, papers,
  grey literature, journals, standards, tools, history timeline), typed JSON exports under
  `landscape/data/`, plus research (`landscape/research/`) and synthesis docs. Schema and id
  conventions: `landscape/README.md`.
- `scripts/` — corpus maintenance and site-data tooling (below).
- `titlesearch/` — the "learning engineers" title-search study: reports, data, and analysis
  (`titlesearch/PROVENANCE.md`).
- `corpus/expansion/` — OpenAlex expansion artifacts retained from earlier pipeline runs.
- `archive/` — the previous generation of the website and corpus pipeline, frozen for
  reference; its own docs live in `archive/REBUILD_STATUS.md` and `archive/corpus/README.md`.

## Corpus workflow

YAML records under `landscape/resources/` are the source of truth.

1. Edit or add records (ids are namespaced `LE-…`; see `landscape/README.md`).
2. Rebuild the typed JSON exports (consumed downstream and by the site's ref validator):

```bash
pip install -r scripts/requirements.txt   # PyYAML
python3 scripts/build_typed_json.py
```

3. The website picks up corpus changes automatically: the site prebuild runs
   `scripts/build_registry.py` against `landscape/resources/`, and the deploy workflow
   triggers on `landscape/**` changes pushed to `main`.

## Scripts

- `build_registry.py` — flatten the landscape YAML into
  `site/src/data/programs_people_registry.json` (run automatically by the site prebuild).
- `validate_mdx_refs.py` — check site MDX `provenance.ref` fields against
  `landscape/data/*.json` (run automatically by the site prebuild; `--strict` in CI use).
- `generate_mdx_stubs.py` — emit site MDX stubs for `featured: true` YAML records.
- `test_content_tooling.py` — stub tests for the two scripts above (`python3 scripts/test_content_tooling.py`).
- `build_typed_json.py` — regenerate `landscape/data/*.json` from the YAML records (consumed
  by LEBOK tooling and the ref validator).
- `add_people_from_json.py` — create person YAMLs from a JSON list of contributor specs
  (dry run by default; `--write` to apply).
- `add_provenance.py` — backfill a provenance `source` field on YAML records that lack one.
- `enrich_key_works.py` — top up `key_works` on person records via OpenAlex.
- `expand_corpus_from_chairs.py` — add top LE-relevant papers authored by conference-chair
  people to the paper corpus via OpenAlex.
- `convert_archive_to_yaml.py`, `convert_endnotes_to_yaml.py` — one-shot converters that
  seeded the YAML paper corpus from the archived pipeline's outputs.

The OpenAlex-backed scripts read `OPENALEX_MAILTO` (and optionally `OPENALEX_API_KEY`) from the
environment or a gitignored repo-root `.env` (see `.env.example`).
