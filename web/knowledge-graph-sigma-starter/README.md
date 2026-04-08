# Knowledge Graph Sigma Starter

A lightweight React + Sigma.js starter for two loosely coupled graph visualizations:

- Topic graph: concept clusters connected to representative papers
- Citation graph: paper-to-paper citation network

The two graphs are intentionally independent in layout and structure, but share stable paper IDs so they can be cross-referenced.

## Stack

- React
- Vite
- Sigma.js
- Graphology

## Run locally

```bash
npm install
npm run dev
```

Then open the local URL shown by Vite.

## Build for production

```bash
npm run build
npm run preview
```

## Project structure

```text
.
├── public/
│   └── data/
│       ├── topic-graph.json
│       ├── citation-graph.json
│       └── sample-graph.json
├── scripts/
│   └── generate-sample-graph.mjs
├── src/
│   ├── App.jsx
│   ├── graph.js
│   ├── main.jsx
│   └── styles.css
├── index.html
├── package.json
└── vite.config.js
```

## Graph data format

Each graph file is standard node/edge JSON:

```json
{
  "nodes": [
    {
      "id": "paper-123",
      "label": "Example Paper",
      "type": "paper",
      "x": 0.12,
      "y": -0.44,
      "size": 7,
      "color": "#22c55e"
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "paper-123",
      "target": "paper-456",
      "label": "cites",
      "relation": "cites",
      "weight": 1
    }
  ]
}
```

## Loosely coupled workflow

1. Build topic and citation graphs offline, independently.
2. Compute node coordinates offline for each graph.
3. Keep shared paper IDs stable across both graph files.
4. Export `public/data/topic-graph.json` and `public/data/citation-graph.json`.
5. Use the UI toggle to switch visualizations.

## Important Sigma note

Node attribute `type` is reserved by Sigma for render programs. The loader in `src/graph.js` preserves your semantic `type` in `semanticType` and forces Sigma render type to `circle` to avoid runtime errors.

## Sample generator

```bash
npm run generate:sample
```

This rewrites `public/data/sample-graph.json` with a synthetic graph.
