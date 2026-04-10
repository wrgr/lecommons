# Learning Engineering Concept Ontology — Layer 2 Reference

This document is the human-readable companion to `corpus/tables/concept_ontology.json`.
It describes the 35 concept-level nodes that form **Layer 2** of the learning engineering
knowledge graph, sitting between the broad topic map (Layer 1) and the curated resource
and paper corpus (Layer 3).

---

## The Three-Layer Architecture

```
Layer 1  Topics (T00–T17)         18 broad topic areas — coarse-grained taxonomy
Layer 2  Concepts (C01–C35)       35 concepts — meso-level ontology (THIS DOCUMENT)
Layer 3  Papers + Resources       ~300 seed/hop papers + ~100 curated resources
```

**Why Layer 2 exists.**  
Topics (T00–T17) are too coarse to support sequenced learning or concept-level search.
Papers and resources are too granular to give learners orientation. Concepts bridge the
two: each concept names a specific, teachable idea, anchors it to one or more book
chapters, and connects it upward to topics and downward to papers and resources.

---

## All 35 Concepts — Summary Table

| ID  | Name | Cluster | Book Ch. | Bloom Level | Prerequisites |
|-----|------|---------|----------|-------------|---------------|
| C01 | What is Learning Engineering? | Foundation | 1 | Understand | — |
| C02 | LE vs. Instructional Design | Foundation | 1 | Analyze | C01 |
| C03 | Learning Engineering Teams & Roles | Foundation | 1 | Apply | C01 |
| C04 | How People Learn: Cognitive Foundations | Learning Science | 2 | Understand | C01 |
| C05 | Desirable Difficulties & Memory Principles | Learning Science | 2 | Apply | C04 |
| C06 | Cognitive Load Theory | Learning Science | 2 | Apply | C04 |
| C07 | Motivation, Engagement & Self-Regulation | Learning Science | 2 | Apply | C04 |
| C08 | Transfer of Learning | Learning Science | 2 | Analyze | C04 |
| C09 | Human Systems Integration | HCD & Process | 3 | Understand | C01 |
| C10 | Human-Centered Design | HCD & Process | 3 | Apply | C09 |
| C11 | The Learning Engineering Process | HCD & Process | 3, 4 | Apply | C01, C10 |
| C12 | Needs Analysis & Task Analysis | HCD & Process | 3 | Apply | C11 |
| C13 | Educational Data Mining | Measurement | 5 | Apply | C04 |
| C14 | Learning Analytics | Measurement | 5 | Apply | C13 |
| C15 | Assessment & Measurement Design | Measurement | 5 | Apply | C04, C11 |
| C16 | Tracking Decisions & Evidence Throughout the Process | Measurement | 4, 5 | Apply | C11 |
| C17 | Evaluation Frameworks | Measurement | 9 | Evaluate | C14, C15 |
| C18 | Knowledge-Learning-Instruction (KLI) Framework | Knowledge & Tech | 6, 7 | Understand | C04 |
| C19 | Competency Frameworks & Learning Objectives | Knowledge & Tech | 7 | Apply | C18 |
| C20 | Intelligent Tutoring Systems | Knowledge & Tech | 6 | Apply | C04, C18 |
| C21 | Adaptive Learning Systems | Knowledge & Tech | 6 | Analyze | C20 |
| C22 | Learning Infrastructure & Data Standards | Knowledge & Tech | 7 | Understand | C19 |
| C23 | AI & Foundation Models in Education | AI | — | Analyze | C20, C21 |
| C24 | AI Ethics & Responsible Use in Learning | AI | — | Evaluate | C23 |
| C25 | Simulation-Based Training | Simulation & Applied | 8 | Apply | C04, C06 |
| C26 | Serious Games & Gamification | Simulation & Applied | 8 | Apply | C04, C07 |
| C27 | Extended Reality (XR/VR/AR) in Learning | Simulation & Applied | 8 | Apply | C25 |
| C28 | Expert Knowledge Elicitation & Cognitive Task Analysis | Simulation & Applied | 3 | Apply | C12 |
| C29 | Workforce Development & Training Systems | Simulation & Applied | 4 | Apply | C28, C08 |
| C30 | Evidence Standards in Learning Research | Evidence & Methods | 9 | Evaluate | C15, C31 |
| C31 | Research Methods in Learning Engineering | Evidence & Methods | 9 | Apply | C11 |
| C32 | Standards, Credentialing & Professional Community | Evidence & Methods | — | Understand | C01 |
| C33 | High-Consequence Domain Learning | Context | — | Apply | C09 |
| C34 | Ethics & Equity in Learning Engineering | Context | — | Evaluate | — |
| C35 | Learning Engineering at Scale & Online Education | Context | — | Analyze | C21, C22 |

---

## Concept Clusters

### Foundation (C01–C03)
Entry-level concepts that define the field and its practitioners.

**C01 — What is Learning Engineering?**  
The founding definition: LE applies the learning sciences and engineering methods to
iteratively improve learning outcomes at scale. Key questions: How does LE differ from
research? From product development? What counts as "evidence"?  
Primary resources: `LE-T1-001`, `LE-T1-002`, `LE-IC-031`

**C02 — LE vs. Instructional Design**  
Where LE extends or departs from classical ID: emphasis on empirical iteration, data
use, and learning science grounding vs. process compliance.  
Primary resources: `LE-IC-022`, `LE-IC-029`, `LE-IC-001`

**C03 — Learning Engineering Teams & Roles**  
LE is a team sport. The canonical team includes learning scientist, data analyst,
instructional designer, subject matter expert, and engineer.  
Primary resources: `LE-IC-010`, `LE-IC-035`, `LE-IC-036`, `LE-IC-037`

---

### Learning Science (C04–C08)
The cognitive and motivational science foundations every LE practitioner must know.

**C04 — How People Learn: Cognitive Foundations**  
Working memory, long-term memory, schema formation, and the dual-process model. The
bedrock for all other learning science concepts.  
Primary resources: `LE-PP-052`, `LE-IC-012`

**C05 — Desirable Difficulties & Memory Principles**  
Retrieval practice, spaced practice, interleaving, and elaborative interrogation.
Evidence from Dunlosky et al. and related memory research.  
Primary resources: `LE-PP-052`

**C06 — Cognitive Load Theory**  
Intrinsic, extraneous, and germane load. Implications for instructional design:
worked examples, goal-free problems, split-attention effects.  
Primary resources: `LE-PP-052`

**C07 — Motivation, Engagement & Self-Regulation**  
Self-determination theory, expectancy-value, self-efficacy. How affective states
interact with cognitive processes to shape learning outcomes.  
Primary resources: `LE-PP-052`

**C08 — Transfer of Learning**  
Near and far transfer; conditions for transfer; the transfer-appropriate processing
principle. Critical for evaluating training effectiveness.  
Primary resources: `LE-PP-052`

---

### HCD & Process (C09–C12)
How learning engineering projects are scoped, framed, and run.

**C09 — Human Systems Integration**  
HSI treats the human as a top-level design constraint in complex systems. Relevant
for LE in defense, healthcare, and other high-consequence domains.  
Primary resources: `LE-PP-001`

**C10 — Human-Centered Design**  
Design thinking, empathy-based problem framing, rapid prototyping, and user testing
as precursors and complements to the formal LE process.  
Primary resources: `LE-IC-038`

**C11 — The Learning Engineering Process**  
The iterative LE cycle: problem framing → design → implementation → measurement →
improvement. The core procedural concept of the field.  
Primary resources: `LE-IC-002`, `LE-IC-003`, `LE-IC-009`, `LE-PP-051`

**C12 — Needs Analysis & Task Analysis**  
Cognitive task analysis, performance gap diagnosis, Five Whys, fishbone analysis.
The front end of every LE project.  
Primary resources: `LE-IC-005`, `LE-IC-006`, `LE-IC-007`

---

### Measurement (C13–C17)
Data collection, analysis, and evaluation throughout the LE process.

**C13 — Educational Data Mining**  
Extracting actionable patterns from learner trace data: knowledge tracing, clustering,
prediction. Foundation for learning analytics.  
Primary resources: `LE-PP-021`, `LE-PP-031`, `LE-IC-039`

**C14 — Learning Analytics**  
Real-time and retrospective analysis of learning data to support instructors,
learners, and administrators.  
Primary resources: `LE-PP-023`, `LE-PP-041`, `LE-IC-037`

**C15 — Assessment & Measurement Design**  
Constructing valid, reliable measures of learning. Formative vs. summative; embedded
vs. standalone; psychometric considerations.  
Primary resources: `LE-IC-033`, `LE-IC-008`

**C16 — Tracking Decisions & Evidence Throughout the Process**  
The LE evidence log: recording what decisions were made, why, and what data supported
them. Enables reproducibility and institutional learning.  
Primary resources: `LE-IC-008`, `LE-IC-009`, `LE-IC-033`

**C17 — Evaluation Frameworks**  
Kirkpatrick four levels; decision-grade evidence; logic models. How to structure a
program evaluation that is actionable for LE teams.  
Primary resources: `LE-IC-004`, `LE-IC-023`

---

### Knowledge & Tech (C18–C22)
Knowledge representation, intelligent systems, and learning infrastructure.

**C18 — Knowledge-Learning-Instruction (KLI) Framework**  
Koedinger et al.'s taxonomy of knowledge types (memory, induction, observation)
and the instructional events that support each. The theoretical backbone of ITS design.  
Primary resources: `LE-PP-002`, `LE-PP-004`

**C19 — Competency Frameworks & Learning Objectives**  
Bloom's taxonomy, learning progressions, competency-based education, standards
alignment. Translating expertise into teachable objectives.  
Primary resources: `LE-PP-054`, `LE-IC-011`

**C20 — Intelligent Tutoring Systems**  
ITS architecture: domain model, student model, pedagogical model, interface. History
from Cognitive Tutor through DKT.  
Primary resources: `LE-PP-030`, `LE-PP-002`, `LE-PP-020`

**C21 — Adaptive Learning Systems**  
Mastery-based progression, item-response theory-driven sequencing, learner modeling
in commercial and research adaptive platforms.  
Primary resources: `LE-PP-004`, `LE-PP-030`, `LE-IC-024`

**C22 — Learning Infrastructure & Data Standards**  
xAPI / Tin Can, LRS, LMS, IMS Global standards. Interoperability and data portability
in learning technology stacks.  
Primary resources: `LE-PP-032`, `LE-PP-031`, `LE-IC-033`

---

### AI (C23–C24)
AI-specific concepts added as the field intersects with foundation models.

**C23 — AI & Foundation Models in Education**  
LLM tutors, generative feedback, AI-generated content, hint systems. Opportunities
and failure modes at the frontier of AI-augmented learning.  
Primary resources: `LE-PP-022`, `LE-IC-013`, `LE-IC-014`

**C24 — AI Ethics & Responsible Use in Learning**  
Algorithmic fairness, data privacy, automation bias in assessment, equity in AI
access. Prerequisite: understand what the AI is doing (C23).  
Primary resources: `LE-PP-022`

---

### Simulation & Applied (C25–C29)
High-fidelity and experiential learning modalities; expert knowledge capture.

**C25 — Simulation-Based Training**  
Simulation fidelity, scenario design, after-action review, transfer to operational
settings. Grounded in cognitive load and transfer science.  
Primary resources: `LE-IC-032`, `LE-PP-001`

**C26 — Serious Games & Gamification**  
Game mechanics, flow state, narrative-based learning, gamified assessment.
Motivation science (C07) is the theoretical anchor.  
Primary resources: `LE-IC-030`, `LE-IC-032`

**C27 — Extended Reality (XR/VR/AR) in Learning**  
Immersive learning environments, presence, embodied cognition, VR for high-stakes
skill practice. Builds on simulation principles (C25).  
Primary resources: `LE-IC-032`

**C28 — Expert Knowledge Elicitation & Cognitive Task Analysis**  
CTA methods: PKSM, think-aloud protocol, critical decision method. Surfaces tacit
expertise for content development.  
Primary resources: `LE-IC-007`

**C29 — Workforce Development & Training Systems**  
Large-scale upskilling, apprenticeship, on-the-job learning, defense and healthcare
training ecosystems.  
Primary resources: `LE-PP-001`, `LE-IC-014`

---

### Evidence & Methods (C30–C32)
Research rigor, professional standards, and community infrastructure.

**C30 — Evidence Standards in Learning Research**  
What counts as decision-grade evidence? Randomized trials, quasi-experiments, design-
based research. Reproducibility and open science in LE.  
Primary resources: `LE-IC-018`, `LE-IC-023`

**C31 — Research Methods in Learning Engineering**  
Specific LE research designs: design-based research, A/B testing in learning contexts,
log-data studies, mixed methods.  
Primary resources: `LE-IC-018`, `LE-IC-039`

**C32 — Standards, Credentialing & Professional Community**  
IEEE ICICLE body of knowledge, LE credential pathways, adjacent academic programs.
How the field defines and certifies expertise.  
Primary resources: `LE-PP-040`, `LE-PP-054`, `LE-PP-024`, `LE-IC-034`

---

### Context (C33–C35)
Domain-specific and systemic contexts that shape how LE is applied.

**C33 — High-Consequence Domain Learning**  
Defense, healthcare, aviation, nuclear — domains where learning failures cost lives.
HSI (C09) is the prerequisite framing.  
Primary resources: `LE-PP-001`, `LE-PP-015`, `LE-IC-031`

**C34 — Ethics & Equity in Learning Engineering**  
Equity in access to LE benefits; power dynamics in data collection; responsible
innovation. No formal prerequisites — applies across all clusters.  
Primary resources: *(see `LE-T1-029` in paper corpus)*

**C35 — Learning Engineering at Scale & Online Education**  
MOOC-scale deployment, online learning infrastructure, the Dede/Richards/Saxberg
edited volume. Integrates adaptive systems (C21) and infrastructure (C22).  
Primary resources: `LE-IC-001`, `LE-IC-025`

---

## Learner Pathway Quick Reference

### J-01: LE Practitioner — From Scratch
`C01 → C02 → C04 → C05, C06, C07 → C11, C12, C13, C14, C18 → C20, C21, C23 → C17, C30, C32`

### J-05: AI/EdTech Practitioner (express)
`C01 → C02 → C04, C07 → C18, C20 → C21, C23 → C24, C14`

### J-06: Getting Up to Speed Fast (3-stage)
`C01, C02 → C04 → C11, C17`

For full journey details including topics, anchor resources, and learner type descriptions,
see `corpus/tables/learning_journeys.json`.

---

## File Locations

| Artifact | Path | Purpose |
|----------|------|---------|
| Concept definitions | `corpus/tables/concept_ontology.json` | Machine-readable; 35 concept records |
| Concept graph edges | `corpus/tables/concept_graph_seeds.json` | BELONGS_TO, PREREQ_FOR, BOOK_CHAPTER edges |
| Learning journeys | `corpus/tables/learning_journeys.json` | Sequenced concept paths by learner type |
| ICICLE resources | `corpus/tables/icicle_resources_registry.json` | 40 harvested ICICLE resources (LE-IC-*) |
| Build pipeline | `scripts/build_dataset.py` | Generates graph JSON artifacts from all of the above |
