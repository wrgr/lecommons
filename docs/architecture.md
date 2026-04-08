# Architecture

## System Overview
- This repo is a static knowledge workspace with a Python ingestion/enrichment layer.
- Build-time scripts generate graph/resource/paper artifacts under `data/`.
- The browser UI loads normalized JSON and renders graph + evidence navigation.

## Module Boundaries
- UI entrypoint: `app.js`.
- UI orchestration/state: `app/components/App.js`.
- UI sections: `app/components/sections/*.js`.
- Graph rendering implementation: `app/components/GraphCanvas.js`.
- Data shaping: `app/data-loader.js` and domain modules in `app/*.js`.
- Pipeline scripts: `scripts/*.py`.
- RAG runtime: `rag/*.py`.

## Data Flow
1. `scripts/build_dataset.py` collects/parses sources and emits `data/*.json`.
2. `app/data-loader.js` fetches and normalizes data files.
3. Derived UI views (filters, clusters, entity slices) are computed in `App` state.
4. Section components render focused views from precomputed state.
5. Optional RAG services consume/rebuild `data/rag_corpus.jsonl`.

## Separation of Concerns Rules
- Keep rendering logic in components, not data-loader modules.
- Keep data normalization in `app/*.js` domain modules, not section components.
- Keep scripts deterministic and reusable; avoid embedding UI assumptions in pipeline code.
- Keep side-effecting operations (fetch, file IO, subprocess) isolated from pure transforms.
