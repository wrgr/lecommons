# Learning Engineering Knowledge Base: Corpus Design Decisions
## Domain-Specific Document

*Version 1.0 | April 2026*
*Companion to: Corpus Construction Methodology (Generic) and le_corpus_specification_v1.xlsx*

---

## Purpose

This document records design decisions made in constructing the Learning Engineering Knowledge Base corpus. It is the audit trail for the corpus specification — explaining not just what was decided but why.

Intended readers: anyone who needs to understand, replicate, challenge, or extend the corpus — including future team members, LENS students, ICICLE contributors, and external reviewers.

---

## 1. Scope and Domain Definition

**Decision:** Define "learning engineering" using the IEEE ICICLE framing as the canonical reference, anchored by the *Learning Engineering Toolkit* (IEEE ICICLE, 2026) as the primary source document.

**Rationale:** The field does not have a single settled definition. IEEE ICICLE is the primary standards-adjacent body coordinating the field; using their framing and toolkit as the corpus anchor ensures the KB is coherent with the community's own self-definition.

**Decision:** Treat the ICICLE resources page (https://sagroups.ieee.org/icicle/resources/) as the canonical external curation source. Every item listed there carries `ieee_icicle_listed = true` in the corpus.

**Rationale:** ICICLE performs ongoing community curation. Rather than duplicating this work, the corpus makes it machine-readable and traceable. The `ieee_icicle_listed` field on every corpus row gives the connection between the internal KB and external ICICLE curation, enabling automated reconciliation when the resources page updates.

---

## 2. Mixed Artifact Corpus (Key Adaptation from Generic Methodology)

**Decision:** Retain all artifact types — papers, books, book chapters, conference proceedings, videos, webinars, podcasts, standards, software repositories, and web resources — rather than restricting to peer-reviewed literature.

**Rationale:** Learning engineering is a practice-oriented field. Practitioners learn from videos, toolkits, webinars, and standards as much as from journal articles. A corpus restricted to peer-reviewed literature would systematically misrepresent how the field actually operates and would fail practitioners using the KB for professional development.

The generic methodology's bias toward peer-reviewed literature is appropriate for biomedical domains. For LE, the `artifact_type` field on every corpus row substitutes for the peer-review filter — enabling users to filter by type without excluding non-journal sources at ingestion.

**Document type distribution (from Toolkit endnotes, MVP parse):**
- `article_report_or_web`: 196 (~66%)
- `paper_or_article`: 46 (~16%)
- `conference_artifact`: 16 (~5%)
- `book_or_chapter`: 16 (~5%)
- `video`: 11 (~4%)
- `standard_or_spec`: 9 (~3%)
- `webinar`, `software_or_repository`: 2 (~1%)

---

## 3. Programs & People as First-Class Registry

**Decision:** Include a Programs & People Registry as a first-class sheet in le_corpus_specification_v1.xlsx, not as a sidebar or appendix.

**Rationale:** Learning engineering is not just a literature — it is a community with people, programs, conferences, and tools that are as important as the papers. The programs registry is the coherence layer between the corpus and the practice community.

The MS KB template was literature-only. The LE KB explicitly diverges here: programs, people, and tools are primary entities.

**Decision:** LENS @ JHU is seeded as an anchor program tied to T13 (high-consequence domains) and the IEEE/ICICLE partnership.

**Rationale:** LENS represents the most explicitly systems-engineering-oriented LE program — framing LE for defense, healthcare, and high-stakes education. Its anchor to T13 ensures that the high-consequence domain topic cluster has a clear program-to-topic linkage. The IEEE/ICICLE partnership connection grounds LENS in the community infrastructure.

---

## 4. Learning Journeys as Coherence Layer

**Decision:** Include a Learning Journeys sheet in le_corpus_specification_v1.xlsx, with J-04 (LENS Student: High-Consequence Learning Systems) as the anchor journey.

**Rationale:** ICICLE currently lacks a coherence structure connecting resources to learner pathways. The Learning Journeys layer provides this — mapping topics, programs, and resources to specific entry paths. J-04 is designed to be usable directly in LENS program materials.

**Decision:** Learning journey topic sequences are linked to topic codes defined in le_corpus_specification_v1.xlsx. Initial sequences are sparse and are intended to be populated through the LENS student and ICICLE working group review process.

---

## 5. Seed Selection

**Decision:** Use Goodell et al. (2020) "Competencies of Learning Engineering Teams and Team Members" as a primary manual seed.

**Rationale:** This paper explicitly defines LE team competencies — the closest analogue to a consensus definition of LE as a professional practice. It is foundational to any competency-oriented curriculum mapping.

**Decision:** Seeds are drawn from Toolkit endnotes (DOI-first resolution via OpenAlex) plus explicit manual seeds for items not captured algorithmically.

**Rationale:** The Toolkit endnotes represent the field's own curated bibliography. DOI-first resolution maximizes precision; manual seeds address the systematic gap where non-DOI artifacts (videos, web resources, standards) would otherwise be excluded.

**Known gap:** The majority of Toolkit endnotes are non-DOI artifacts. Stronger title/URL matching for these is deferred to a later pass. Current match rate: ~20% (60 of 296 parsed endnotes matched to OpenAlex records).

---

## 6. The `ieee_icicle_listed` Field

**Decision:** Add `ieee_icicle_listed: bool` as a required field on every corpus row, program entry, and resource item.

**Rationale:** This field is the machine-readable bridge between the internal KB and external ICICLE curation. Once the ICICLE resources page is fully harvested (currently flagged as a blocking gap — see Gap Tracker in le_corpus_specification_v1.xlsx), every resource maps back through this field. It also enables provenance queries: "show me only ICICLE-curated resources" vs. "show me resources not yet surfaced by ICICLE."

---

## 7. OpenAlex as Primary Enrichment API

**Decision:** Use OpenAlex (api.openalex.org) as the primary metadata resolution and one-hop expansion API, consistent with the generic methodology.

**Rationale:** OpenAlex is free, open, and has good coverage of LE-adjacent literature (education, cognitive science, computer science). The LE field is smaller than biomedical MS literature, so the candidate pool from one-hop expansion is proportionally smaller (~500–2,000 papers rather than 5,000–15,000). This makes the pipeline tractable without pagination complexity.

**Decision:** Use DOI-first resolution with title-search fallback. Skip URL-only resolution for the MVP.

**Rationale:** DOI resolution is deterministic and produces high-precision matches. Title search introduces fuzzy matching risk but captures papers without DOIs. URL-only resolution has high false-positive risk and is deferred.

---

## 8. PDF Extraction Dependency

**Decision:** Support both `pdftotext` (system) and `pypdf` (Python) for PDF text extraction, with graceful fallback to cached text if PDFs are not provided.

**Rationale:** The Learning Engineering Toolkit PDFs are the primary source for chapter structure and endnotes. However, these are local files not committed to the repo. The pipeline should be runnable without PDFs if cached text exists, and should not fail hard when PDFs are unavailable.

**PDF paths are passed as CLI arguments — no hardcoded machine paths in the codebase.**

---

## 9. Known Limitations and Gaps

| Gap ID | Description | Status |
|--------|-------------|--------|
| G-01 | ICICLE resources page full harvest | Blocking |
| G-02 | Non-DOI endnote matching (title/URL) | Deferred |
| G-03 | One-hop expansion precision vs. recall balance | Deferred |
| G-04 | Learning journey topic sequence completion | In progress |
| G-05 | Programs & People people-level entries | Deferred |
| G-06 | Non-English and non-Western LE literature | Deferred |

---

*Version 1.0 — April 2026. Update version number and Gap Tracker in le_corpus_specification_v1.xlsx when methodology changes.*
