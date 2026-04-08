# Vertex-Hosted RAG (KG + Topic Model)

This repository now includes a grounded RAG service over your generated dataset (`data/*.json`) with refusal behavior for controversial and out-of-scope requests.

## What It Does

- Builds retrieval chunks from your topic model + paper graph artifacts.
- Retrieves grounded evidence from the chunked corpus.
- Uses Vertex Gemini for synthesis (or a local fallback when Vertex is not configured).
- Refuses:
  - controversial/polarizing prompts,
  - high-risk advisory requests,
  - out-of-domain questions,
  - answers that fail grounding/citation checks.

## Files Added

- `scripts/build_rag_corpus.py` - creates `data/rag_corpus.jsonl`.
- `rag/corpus.py` - corpus builders + lexical retriever.
- `rag/policy.py` - controversial/out-of-scope refusal policy.
- `rag/engine.py` - end-to-end ask pipeline with grounding checks.
- `rag/api.py` - FastAPI endpoint (`/ask`, `/healthz`).

## Local Run

1. Build corpus:

```bash
python3 scripts/build_rag_corpus.py
```

2. Install runtime deps:

```bash
pip install -r requirements-rag.txt
```

3. Configure Vertex (required for production synthesis):

```bash
export VERTEX_PROJECT_ID="your-gcp-project"
export VERTEX_LOCATION="us-central1"
export VERTEX_MODEL_NAME="gemini-2.5-flash"
```

4. Start API:

```bash
uvicorn rag.api:app --host 0.0.0.0 --port 8126
```

5. Ask:

```bash
curl -s http://127.0.0.1:8126/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What do chapters 5 and 13 suggest about instrumentation in learning engineering?"}'
```

## Response Shape

`POST /ask` returns:

- `status`: `answer` or `refused`
- `answer`: grounded answer text (when `status=answer`)
- `refusal_reason`: e.g., `out_of_scope`, `controversial_or_high_risk`, `grounding_failure`
- `refusal_message`: refusal explanation
- `citations`: ranked evidence docs (`doc_id`, `title`, `score`, `source_url`)

## Vertex Deployment Options

- **Cloud Run**: containerize this API, deploy with env vars above, and attach a service account with Vertex AI User permissions.
- **Vertex AI custom container endpoint**: deploy this API container as a prediction service.

Both options keep inference/synthesis in Vertex while preserving grounded retrieval and explicit refusal policy.
