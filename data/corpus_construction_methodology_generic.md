# Corpus Construction Methodology for Domain Knowledge Bases
## A Bibliometrically-Grounded Framework

*Version 1.0 | April 2026*
*Companion to: MS Knowledge Base Corpus Design Decisions*

---

## Purpose

This document describes a general methodology for constructing curated literature corpora intended to ground domain-specific AI knowledge bases, retrieval-augmented generation (RAG) systems, or structured learning resources. It is designed to be reusable across domains.

The methodology draws on established principles from bibliometrics, information science, and knowledge organization. Where design choices are made, the reasoning and supporting literature are documented so that practitioners can evaluate, adapt, or challenge them for their own domain.

---

## 1. The Core Problem: From Seeds to Corpus

A knowledge base corpus requires selecting a subset of a field's literature that is:

1. **Representative** — covering the field's canonical topics without systematic gaps
2. **Coherent** — internally consistent in scope and intellectual framing
3. **Balanced** — not over-representing dominant subfields, institutions, or methodologies at the expense of important minorities
4. **Auditable** — every document's inclusion can be justified with a specific rationale
5. **Updatable** — the selection process can be re-run as the field evolves

No automated process fully satisfies all five criteria. This methodology combines algorithmic filtering with structured human judgment, using each where it has comparative advantage.

---

## 2. Theoretical Foundations

### 2.1 Citation Analysis as Knowledge Organization

The use of citation networks to organize scientific knowledge has a long history in information science. Co-citation, defined as the frequency with which two documents are cited together, was introduced by Small (1973) as a new measure of the relationship between documents. The intuition is that the scientific community's collective citation behavior encodes semantic relationships: papers cited together are being used together to build arguments, and therefore are intellectually related.

**Key reference:** Small H. Co-citation in the scientific literature: A new measure of the relationship between two documents. *Journal of the American Society for Information Science* 1973;24(4):265–269. DOI: 10.1002/asi.4630240406

The complementary measure, bibliographic coupling (Kessler 1963), identifies similarity through shared references rather than shared citations: two papers that cite many of the same predecessors are likely working on related problems.

**Key reference:** Kessler MM. Bibliographic coupling between scientific papers. *American Documentation* 1963;14(1):10–25. DOI: 10.1002/asi.5090140103

### 2.2 Which Citation Approach Best Represents the Research Front?

Boyack and Klavans (2010) compared co-citation analysis, bibliographic coupling, direct citation, and hybrid approaches across 2,153,769 biomedical articles, finding that bibliographic coupling slightly outperforms co-citation analysis. For a knowledge base intended to support current practitioners, bibliographic coupling has advantages; for foundational coverage, co-citation is stronger. The methodology here uses a hybrid approach.

**Key reference:** Boyack KW, Klavans R. *JASIST* 2010;61(12):2389–2404. DOI: 10.1002/asi.21419

### 2.3 Graph Centrality and Structural Importance

PageRank — originally developed by Brin and Page (1998) — provides a structurally-grounded alternative to raw citation counts. When computed on a domain-specific citation subgraph, PageRank identifies papers that are structurally central within the domain regardless of absolute citation count or institutional origin.

**Key reference:** Brin S, Page L. *Computer Networks and ISDN Systems* 1998;30:107–117.

### 2.4 Within-Subdomain Normalization

Citation counts vary systematically across subfields. Within-subdomain percentile normalization corrects this by asking "how important is this paper relative to its peers?" rather than "how many citations does it have?" This is consistent with the Leiden Manifesto's principle that metrics should be adjusted for field differences.

**Key reference:** Hicks D et al. *Nature* 2015;520:429–431. DOI: 10.1038/520429a

### 2.5 Citation Velocity as a Leading Indicator

Citation velocity — the rate at which a paper is accumulating citations — provides a leading indicator of emerging importance. Velocity = citations received in last N years / paper age in years. Recommended N: 2 years.

---

## 3. The Pipeline Architecture

### Step 0: Seed Selection

Seeds are manually curated anchor documents representing the field's canonical topics. They serve as conceptual anchors, citation network origins, and quality anchors.

**Seed selection criteria:**
- Explicit topic coverage: every major topic should have at least two seeds
- Diversity of document type
- Author and institutional diversity
- Recency balance: foundational anchors + current papers

### Step 1: Expansion Source Augmentation

Include 5–8 high-quality, comprehensive review articles as expansion sources. These are hub documents with large, expertly curated reference lists.

**Critical constraint:** Cross-seed connectivity is scored against seeds, not review articles.

### Step 2: One-Hop Expansion

Perform one-hop citation expansion (backward + forward) from all expansion sources using the OpenAlex API.

Expected candidate pool: 5,000–15,000 papers.

### Step 3: Cross-Seed Connectivity Filter

```
cross_seed_score = count of seeds in whose one-hop neighborhood
                  the candidate appears
```

Threshold: ≥ 2 for Tier 2; ≥ 1 for Tier 3 (velocity-selected emerging papers).

### Step 4: Topic Assignment

- Primary topic (required, one only)
- Secondary topics (optional, 0–3): substantive content required, not merely citations

### Step 5: Within-Subdomain Citation Score

```
subdomain_score = max(citation_percentile, velocity_percentile)
```

Retain candidates where subdomain_score ≥ topic_threshold in any assigned topic.

### Step 6: Emerging Literature (Tier 3)

Recent papers (published within 4 years) using velocity_percentile ≥ 80th with cross_seed_score ≥ 1. Manual review required.

### Step 7: Expert Signal Tier (Tier 4)

Small, high-precision set selected by explicit expert signals. Keep to 5–15% of corpus. Every document must have its selection source documented.

### Step 8: Manual Review and Balance Check

1. Topic balance
2. Source diversity
3. Document type balance
4. Patient/community voice where relevant

---

## 4. Quality Assurance

### 4.1 QA Overlap Check

```
overlap_pct = (anchor's references in final corpus) / (total anchor references)
```

Expected: >70% per anchor. Below 60% for a specific topic signals thin seed coverage.

### 4.2 Known Limitations

- Recency bias of velocity filter
- English-language bias in OpenAlex
- Institutional bias in citation accumulation
- Document type imbalance (RCTs vs. qualitative/policy work)
- Grey literature gap

---

## 5. Adaptations for Different Domains

**Policy and practice domains:** Grey literature is more important. Tier 4 should be proportionally larger.

**Rapidly evolving fields:** Preprints are an important signal.

**Fields with strong international diversity:** Explicitly allocate Tier 4 slots to non-Western literature.

---

## 6. Implementation Tools

- **Citation data:** OpenAlex API (api.openalex.org) — free, open, no authentication required
- **PageRank:** Python NetworkX (`nx.pagerank()`)
- **Tracking:** Companion corpus specification workbook (Excel)

---

## 7. Reference Summary

| Reference | Role |
|-----------|------|
| Small 1973, *JASIS* 24:265–269 | Co-citation as knowledge organization |
| Kessler 1963, *American Documentation* 14:10–25 | Bibliographic coupling |
| Boyack & Klavans 2010, *JASIST* 61:2389–2404 | Hybrid citation approach |
| Brin & Page 1998, *Computer Networks* 30:107–117 | PageRank |
| Hicks et al. 2015, *Nature* 520:429–431 | Leiden Manifesto; within-field normalization |
| Priem et al. 2022, *arXiv*:2205.01833 | OpenAlex API |

---

*This document is a living methodological reference. Update the version number when the methodology evolves.*
