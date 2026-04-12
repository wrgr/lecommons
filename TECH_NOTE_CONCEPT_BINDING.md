# Tech Note: Three-Layer Architecture & Concept Binding

**Status:** Stable design — applies to the current corpus build.  
**Related files:** `corpus/tables/concept_ontology.json`, `corpus/tables/concept_graph_seeds.json`, `scripts/build_dataset.py`

---

## Why Three Layers?

The learning engineering knowledge graph uses three layers of representation. Each layer
answers a different question:

| Layer | Granularity | What it answers | Files |
|-------|-------------|-----------------|-------|
| **L1 Topics** (T00–T17) | Coarse | "What broad area is this?" | `topic_map.json` |
| **L2 Concepts** (C01–C35) | Meso | "What specific idea does this teach?" | `concept_ontology.json` |
| **L3 Resources** | Fine | "What should I read/use?" | `academic_papers.jsonl`, registries |

Topics alone are too coarse to support sequenced learning or prerequisite reasoning. A
resource tagged only as "T04 — Measurement & Analytics" doesn't tell a learner whether
they need to understand cognition first (C04), or whether they're ready for advanced
evaluation frameworks (C17). Concepts bridge that gap.

---

## Layer 2: The Concept Ontology

`corpus/tables/concept_ontology.json` defines 35 concepts (`C01`–`C35`), each with:

```jsonc
{
  "concept_id": "C11",
  "name": "The Learning Engineering Process",
  "topic_codes": ["T03"],            // connects up to Layer 1
  "book_chapter_anchors": [3, 4],    // anchored to IEEE LE Toolkit chapters
  "bloom_level": "Apply",            // cognitive target
  "prerequisites": ["C01", "C10"],  // ordered learning dependencies
  "primary_papers": ["LE-T1-007"],  // connects down to Layer 3 papers
  "primary_resources": ["LE-IC-002", "LE-IC-003"]  // connects down to Layer 3 resources
}
```

The `book_chapter_anchors` field is specific to this knowledge base: the IEEE Learning
Engineering Toolkit (Goodell & Kolodner 2022) is the canonical textbook of the field, and
anchoring each concept to its chapter makes the concept layer navigable by practitioners
who already own the book.

---

## Layer 2: Concept Graph Seeds

`corpus/tables/concept_graph_seeds.json` stores explicit concept-level edges:

| Edge type | Meaning | Example |
|-----------|---------|----------|
| `BELONGS_TO` | Concept → Topic | C11 belongs_to T03 |
| `PREREQ_FOR` | Concept → Concept | C04 prereq_for C11 |
| `BOOK_CHAPTER` | Concept → Chapter | C11 anchored to chapter 3 |

These edges are emitted by `build_concept_graph()` in `scripts/build_dataset.py` and
merged into `data/graph.json` as part of the standard build.

---

## How Concept Nodes Enter the Graph

`build_dataset.py:build_concept_graph()` does four things:

1. **Creates concept nodes** — type `"concept"`, carrying `topic_codes`, `bloom_level`,
   and `book_chapters` in the `provenance` block.

2. **Emits topic→concept edges** (`has_concept`) — anchors each concept to its **primary
   topic only** (`topic_codes[0]`). Secondary topic codes remain on the node as metadata
   for filtering and coloring, but do not produce additional structural edges. Each concept
   has exactly one topic anchor in the graph.

3. **Emits concept→paper edges** (`anchored_by`) — from `primary_papers` in the ontology.
   Only emits the edge if the paper ID exists in the current corpus (avoids dangling refs).

4. **Emits concept→resource edges** (`learn_via`) — from `primary_resources`. Only emits
   if the resource ID exists in the merged resource index (icicle + programs_people +
   non_paper_resources).

5. **Emits concept→concept prereq edges** (`prereq`) — from `concept_graph_seeds.json`,
   **intra-topic pairs only**. Both concepts must share the same primary topic code. This
   keeps the concept layer organized into topic clusters; cross-topic prerequisite ordering
   is preserved in `concept_ontology.json` (the `prerequisites` field) and in
   `learning_journeys.json` for sequencing purposes. Cross-cluster structural relationships
   are expressed at the topic level via topic-to-topic edges in `knowledge_graph_seeds.json`.

---

## Difference from MSKB

The MSKB knowledge base (wrgr/mskb) uses the same three-layer model but is anchored to a
medical domain (multiple sclerosis). The LE Resources knowledge base diverges in two ways:

1. **Anchor document**: MSKB concepts are anchored to disease progression and clinical
   guidelines. LE concepts are anchored to the IEEE LE Toolkit chapters, because the
   Toolkit is the closest thing the field has to a canonical reference.

2. **Resource layer scope**: MSKB Layer 3 is primarily peer-reviewed papers with some
   curated multimedia. LE Resources Layer 3 includes grey literature, programs, people,
   communities, and tools — because LE is a practitioner field and much of its knowledge
   lives outside academic journals.

The graph filtering logic (cross_seed_score ≥ 2, 2-core + in-degree ≥ 2) is identical
between both repos — it was validated in MSKB and applied unchanged here.

---

## Adding a New Concept

1. Add a record to `corpus/tables/concept_ontology.json` with all required fields.
2. Add `BELONGS_TO` and `PREREQ_FOR` edges to `corpus/tables/concept_graph_seeds.json`.
3. Bind it to resources in `concept_ontology.json → primary_resources`.
4. Run `python3 scripts/build_dataset.py` to rebuild.
5. Update `LEARNING_CONCEPT_ONTOLOGY.md` to include the new concept in the summary table
   and the appropriate cluster section.

---

## Invariants the Build Enforces

- Concept→paper edges are only emitted if the paper ID is in `seed_papers` or `hop_papers`.
- Concept→resource edges are only emitted if the resource ID is in the merged resource index.
- Prereq edges are only emitted if both concept IDs exist in `concept_ontology.json` **and**
  share the same primary topic code (`topic_codes[0]`).
- Each concept produces exactly one `has_concept` edge — from its primary topic only.

These checks prevent dangling references and make the graph safe to render without
client-side null-checks.

---

## File Map

```
corpus/tables/
  concept_ontology.json        35 concept definitions (authoritative)
  concept_graph_seeds.json     explicit concept edges (BELONGS_TO, PREREQ_FOR, BOOK_CHAPTER)
  learning_journeys.json       sequenced concept paths by learner type (J-01 through J-06)
  icicle_resources_registry.json    LE-IC-* resources (IEEE ICICLE harvested)
  programs_people_registry.json     LE-PP-* resources (programs, people, orgs, tools)

scripts/
  utils.py                     shared constants and pure utility functions
  openalex_client.py           OpenAlex, Crossref, ArXiv API clients
  abstract_fetcher.py          URL/PDF abstract fetching, enrichment pipeline, Topic model
  build_dataset.py             corpus builders + main() entry point
    build_concept_graph()      Layer 2 node/edge construction
    build_resources()          merges all three resource registries with dedup

data/
  graph.json                   merged L1+L2+L3 graph (nodes + edges)
  learning_journeys.json       copy of corpus/tables version, for frontend
  diversity_audit.json         per-topic resource-type balance report

LEARNING_CONCEPT_ONTOLOGY.md  human-readable companion to concept_ontology.json
RESOURCE_CURATOR_TEMPLATE.md  how to add new resources and bind them to concepts
```
