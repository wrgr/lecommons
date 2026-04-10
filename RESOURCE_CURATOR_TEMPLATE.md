# Resource Curation Guide

This document explains how to add new resources to the learning engineering knowledge
base so that they are correctly indexed, linked to concepts, and included in graph
builds.

---

## When to Add a Resource

A resource is worth adding if it meets at least one of the following criteria:

- **Empirical grounding** — reports findings from a study, evaluation, or data analysis
  relevant to learning engineering.
- **Practitioner utility** — a tool, template, or guide that LE practitioners actively
  use (or should use) in their work.
- **Field definition** — defines or debates what learning engineering is, does, or
  should become.
- **Community anchor** — represents a significant organization, program, conference, or
  person in the LE ecosystem.
- **Evidence base** — contributes to the evidentiary foundation of a specific concept
  (C01–C35).

Do **not** add resources that are:
- Paywalled with no abstract or summary publicly accessible.
- Duplicates of existing entries (check by name and URL before adding).
- General education or instructional design resources with no specific LE relevance.

---

## Scoring Rubric

Before committing a resource, rate it on each dimension below (1–5 scale). A score of
**18/25 or higher** is the inclusion threshold. Record scores in the `qa_notes` field.

| Dimension | 1 (poor) | 3 (acceptable) | 5 (excellent) |
|-----------|----------|----------------|---------------|
| **LE Relevance** | Tangential to LE | Relevant to an LE topic | Directly defines or advances LE practice |
| **Currency** | >10 years old, no update | 5–10 years, still cited | <5 years, or classic with lasting validity |
| **Practitioner Utility** | Academic only; no practical takeaways | Some guidance for practitioners | Actionable tools, templates, or evidence a practitioner can use today |
| **Clarity** | Dense jargon, no summary | Accessible with effort | Clear, well-structured, summary or abstract available |
| **Accessibility** | Paywalled, no alternative | Partially accessible | Freely available (open access, free download, public URL) |

**Scoring note for grey literature:** Currency and Practitioner Utility are the most
important dimensions for non-academic resources. A practitioner template (LE-IC-*) that
scores 4+4 on those two dimensions usually clears the threshold even if it scores lower
on Clarity.

---

## Resource ID Scheme

| Prefix | Registry file | Usage |
|--------|--------------|-------|
| `LE-IC-NNN` | `corpus/tables/icicle_resources_registry.json` | Resources harvested from IEEE ICICLE or directly affiliated with ICICLE |
| `LE-PP-NNN` | `corpus/tables/programs_people_registry.json` | Programs, people, organizations, tools, and general grey literature |

**Choosing the right prefix:**
- Use `LE-IC-NNN` if the resource appears on the IEEE ICICLE resources page
  (`sagroups.ieee.org/icicle/resources/`) or is produced by ICICLE.
- Use `LE-PP-NNN` for everything else: academic programs, practitioners, conferences,
  tools, and community organizations.

**Assigning the next ID:**
1. Open the relevant registry JSON file.
2. Find the highest existing number (e.g. `LE-IC-040` or `LE-PP-060`).
3. Increment by one (e.g. `LE-IC-041` or `LE-PP-061`).
4. Never reuse a retired ID.

---

## Required Fields

Every entry must include all of the following fields.

```json
{
  "resource_id":        "LE-IC-041",
  "status":             "APPROVED",
  "content_type":       "GL",
  "name":               "Full descriptive name of the resource",
  "affiliation_or_venue": "Publisher, institution, or hosting organization",
  "url":                "https://... (or \"[ICICLE resources page]\" if no direct URL)",
  "primary_topic":      "T00",
  "secondary_topics":   "T03, T15",
  "description":        "2–4 sentence description explaining what this resource is and why it matters to LE practitioners.",
  "notes":              "Provenance note, e.g. 'Harvested from sagroups.ieee.org/icicle/resources/ Apr 2026'"
}
```

### Content Type Codes

| Code | Meaning | Examples |
|------|---------|----------|
| `AP` | Academic paper | Peer-reviewed journal article, conference paper, preprint |
| `SG` | Standard / Guideline | IEEE ICICLE BoK, xAPI spec, IMS Global |
| `PC` | Program / Curriculum | Degree program, MOOC, certificate |
| `PP` | Person / Practitioner | Named researcher or field leader |
| `CE` | Conference / Event | Annual conference, symposium |
| `TP` | Tool / Platform | Software, template, computational infrastructure |
| `GL` | Grey Literature / Report | White paper, policy doc, practitioner article, video, podcast |
| `CO` | Community / Organization | Professional society, research consortium, working group |

### Status Values

| Value | Meaning |
|-------|---------|
| `APPROVED` | Verified, ready to include in builds |
| `SEED` | Included as a starting point; verify before promotion |
| `CANDIDATE` | Under review; not yet included in graph builds |
| `REJECTED` | Evaluated and excluded; keep entry to avoid re-evaluation |
| `RETIRED` | Was APPROVED but is now superseded, defunct, or no longer relevant. Set `retired_in_version`. Never delete retired entries. |

### Topic Codes

Assign the topic where the resource is most directly useful as `primary_topic`.
List up to three additional topics in `secondary_topics` (comma-separated string).

| Code | Topic |
|------|-------|
| T00 | Field Overview & History |
| T01 | Learning Science Foundations |
| T02 | Systems Engineering & Human Factors |
| T03 | Learning Engineering Process |
| T04 | Measurement & Analytics |
| T05 | Knowledge Representation |
| T06 | Intelligent Tutoring & Adaptive Systems |
| T07 | AI & Foundation Models in Learning |
| T08 | Simulation & Experiential Learning |
| T09 | Expert Knowledge Elicitation |
| T10 | Workforce Development & Training Systems |
| T11 | Learning Infrastructure & Platforms |
| T12 | Instructional Design & Curriculum |
| T13 | High-Consequence & Complex Domains |
| T14 | Ethics, Equity & Responsible LE |
| T15 | Evidence & Evaluation Standards |
| T16 | Standards, Credentialing & Community |
| T17 | Research Methods & Field Development |

---

## Seed Role

For resources that function as **seeds** in the citation expansion pipeline (i.e., T1 seeds
in `corpus/academic_papers.jsonl`), assign a `seed_role` in `metadata_schema.json`:

| Role | Meaning |
|------|---------|
| `expansion` | Active retrieval root — used to drive OpenAlex one-hop expansion |
| `landmark_anchor` | Foundational item that shapes graph structure; not an active retrieval root |
| `framing` | Used for scoring and topic shaping only; not a retrieval seed |
| `bridge` | Non-LE resource included because it bridges into LE topics |

Most T1 seeds are `expansion`. The Goodell/Kolodner textbook and Saxberg 2016 Atlantic
essay are `landmark_anchor` — they define the field but don't drive literature retrieval.

---

## Binding a Resource to Concepts

After adding the entry to the registry, update
`corpus/tables/concept_ontology.json` to link the resource to any concepts
it directly supports.

1. Find the concept record (e.g. `C11` for the LE process).
2. Add the new resource ID to its `primary_resources` array:

```json
{
  "concept_id": "C11",
  "name": "The Learning Engineering Process",
  ...
  "primary_resources": ["LE-IC-002", "LE-IC-003", "LE-IC-009", "LE-PP-051", "LE-IC-041"]
}
```

A resource can appear in multiple concept records if it spans more than one concept.

---

## How to Trigger a Rebuild

After editing any registry or ontology file, run the build pipeline to regenerate
all graph and dataset artifacts:

```bash
cd learning-engineering-resources
python3 scripts/build_dataset.py
```

The pipeline will:
1. Merge `icicle_resources_registry.json` + `programs_people_registry.json` into the resource index (deduplicating by `resource_id`).
2. Build concept-layer nodes and edges from `concept_ontology.json` and
   `concept_graph_seeds.json`.
3. Run `audit_resource_diversity()` and print any balance warnings.
4. Emit updated `data/*.json` artifacts consumed by the website.

If the build fails, check:
- All resource IDs referenced in `concept_ontology.json` actually exist in one of
  the registry files.
- All topic codes in new entries are valid (T00–T17).
- JSON is valid (no trailing commas, matched brackets).

---

## Maintenance Schedule

| Cadence | Task | Owner |
|---------|------|-------|
| **Quarterly** | Validate all URLs — automated bot pass + manual spot-check of failed URLs | Curator |
| **Quarterly** | Review `data/diversity_audit.json` warnings — address any topic with >60% single content type | Curator |
| **Annually** | Freshness review — scan resources added >3 years ago; flag for AGING or RETIRED | Domain lead |
| **Annually** | Solicit learner/community feedback; add or retire based on usage and feedback | Domain lead |
| **Per release** | Update `corpus/tables/update_log.json` with summary of changes | Curator |

**Retiring a resource:**
1. Set `"status": "RETIRED"` in the registry entry.
2. Set `"retired_in_version": "YYYY-MM"` (e.g. `"2026-09"`).
3. Remove the resource ID from any `concept_ontology.json → primary_resources` arrays.
4. Add a note in `corpus/tables/update_log.json` explaining why it was retired.
5. Run the build to confirm no dangling references.

Never delete a retired entry — keeping it prevents re-evaluation and provides an audit
trail.

---

## Checklist

Before committing a new resource:

- [ ] Scoring rubric completed in `qa_notes`; total ≥ 18/25 (or document exception).
- [ ] Resource ID is unique and follows the correct prefix scheme.
- [ ] All required fields are present and non-empty.
- [ ] `content_type` matches one of the eight valid codes.
- [ ] `status` is set to `APPROVED` (or `CANDIDATE` if still under review).
- [ ] `primary_topic` is the most relevant topic code.
- [ ] Description is 2–4 sentences; explains LE relevance, not just what the resource is.
- [ ] `notes` records the provenance and date.
- [ ] If relevant, `concept_ontology.json` updated to bind the resource to concepts.
- [ ] `python3 scripts/build_dataset.py` runs without errors.
- [ ] No new `diversity_audit.json` warnings introduced (or documented as acceptable).
