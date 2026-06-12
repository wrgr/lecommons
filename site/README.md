# Learning Engineering Commons — site

The Astro site serving [lecommons.org](https://lecommons.org): a community library of
learning engineering resources (people, programs, papers, tools, events) adapted from IEEE
ICICLE and other community sources, organized around an 18-topic map of the field.

## Develop

```sh
npm install
npm run dev             # local dev server (regenerates the registry first)
npm run build           # prebuild: registry + ref validation, then astro build → dist/
npm run validate:refs   # strict provenance.ref validation (fails on orphans)
npm run test:scripts    # stub tests for the registry/validation tooling
```

The prebuild scripts need Python 3.11+ with PyYAML (`pip install -r ../scripts/requirements.txt`).

## Data flow

- `../landscape/resources/**/*.yaml` is the source of truth for people, organizations,
  programs, conferences, tools, journals, standards, and the history timeline.
- `../scripts/build_registry.py` (run automatically by `prebuild`/`predev`) flattens those
  YAML records into `src/data/programs_people_registry.json`, which `graph.astro` and the
  community pages consume.
- `../scripts/validate_mdx_refs.py` checks every `provenance.ref` in `src/content/**/*.mdx`
  against `../landscape/data/*.json`. After editing YAML records, run
  `python3 ../scripts/build_typed_json.py` so those typed exports stay current.
- Other `src/data/` files (topic map, concept ontology, graph seeds, papers seed, pathways)
  are curated and committed directly.

## Content collections

`src/content/` holds six MDX collections — `community`, `events`, `field-notes`, `practice`,
`reading-list`, `tools` — validated by `src/content.config.ts`. Import tooling (LEBOK citation
lists, stub generation for `featured: true` YAML records) lives in `scripts/` here and in
`../scripts/`.

## Deploy

Pushes to `main` that touch `site/`, `landscape/`, or the registry/validation scripts trigger
`.github/workflows/deploy-gh-pages.yml`, which builds the site and publishes `dist/` to the
`gh-pages` branch with `CNAME lecommons.org`.

## Related projects

- [LENS @ JHU](https://capabilitymatters.org) — the Johns Hopkins specialization's editorial
  lens site (`wrgr/capabilitymatters`).
- [LEBOK](https://github.com/wrgr/lebok) — the Learning Engineering Body of Knowledge wiki.
