# Tech Stack

## Frontend
- Runtime: Browser-native ES modules.
- UI: `React` + `htm` loaded via pinned `esm.sh` imports in `app/lib.js`.
- Visualization: `d3` force-graph rendering in `app/components/GraphCanvas.js`.
- Delivery: Static assets served from repository root (`index.html`, `app.js`, `styles.css`).

## Data Pipeline
- Primary build script: `scripts/build_dataset.py`.
- Input artifacts: ICICLE resources, toolkit text, adjacent program extracts, and seed citations.
- Output artifacts: structured JSON in `data/` used by UI and RAG flows.
- Auxiliary operations: `scripts/knowledge_ops.py` for ingest/sync/rebuild workflows.

## RAG/Backend
- Python package: `rag/` modules (`api.py`, `engine.py`, `corpus.py`, `policy.py`, `vertex.py`).
- API framework: FastAPI endpoints in `rag/api.py`.
- Corpus artifact: `data/rag_corpus.jsonl`.

## Quality Tooling
- SWE guardrail linter: `scripts/swe_lint.py`.
- Unit tests: `tests/test_rag_engine.py`, `tests/test_rag_policy.py`.
