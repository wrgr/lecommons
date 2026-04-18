"""Enrich resource_keywords.json and topic_clusters.json for the Explore view.

Three modes:
  python3 enrich_tags.py             — process all resources (full refresh)
  python3 enrich_tags.py --new-only  — only process IDs not yet in the JSON
  python3 enrich_tags.py --llm       — call Claude API for richer keywords

Run --new-only as a pre-build hook; it's a no-op when there are no new entries.
"""

import argparse
import json
import re
import sys
import yaml
from pathlib import Path
from collections import Counter

CONTENT = Path(__file__).resolve().parent.parent / "src" / "content"
DATA_OUT = Path(__file__).resolve().parent.parent / "src" / "data"

COLLECTIONS = ["practice", "tools", "reading-list", "events", "community"]

# ── Cluster definitions ───────────────────────────────────────────────────

CLUSTERS = [
    {
        "id": 0,
        "name": "Foundations of Learning",
        "topics": ["T00", "T01"],
        "description": "What is learning engineering? Origins, definitions, and the learning science evidence base.",
    },
    {
        "id": 1,
        "name": "HSI & Human Performance",
        "topics": ["T02", "T09", "T13"],
        "description": "Human systems integration, expert knowledge elicitation, and high-consequence domain applications.",
    },
    {
        "id": 2,
        "name": "AI & Adaptive Learning",
        "topics": ["T06", "T07", "T08"],
        "description": "Intelligent tutoring systems, foundation models in learning, simulation, and experiential design.",
    },
    {
        "id": 3,
        "name": "Assessment & Evidence",
        "topics": ["T04", "T15", "T17"],
        "description": "Measurement, analytics, evidence standards, and research methods.",
    },
    {
        "id": 4,
        "name": "Workforce & Training Systems",
        "topics": ["T10", "T11", "T12"],
        "description": "Workforce development, learning infrastructure, and instructional design.",
    },
    {
        "id": 5,
        "name": "Ethics, Equity & Community",
        "topics": ["T14", "T16"],
        "description": "Algorithmic fairness, equity in access, standards, and professional credentialing.",
    },
    {
        "id": 6,
        "name": "LE Process & Knowledge",
        "topics": ["T03", "T05"],
        "description": "The learning engineering process, knowledge representation, and ontologies.",
    },
]

TOPIC_TO_CLUSTER: dict[str, int] = {}
for _c in CLUSTERS:
    for _t in _c["topics"]:
        TOPIC_TO_CLUSTER[_t] = _c["id"]

# ── Topic → representative keywords ──────────────────────────────────────

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "T00": ["field overview", "learning engineering", "ICICLE", "instructional design", "LE definition"],
    "T01": ["learning science", "cognitive load theory", "spaced practice", "retrieval practice", "worked examples", "transfer of learning"],
    "T02": ["human systems integration", "HSI", "systems engineering", "human factors", "sociotechnical systems", "human performance"],
    "T03": ["LE process", "iterative design", "rapid prototyping", "formative evaluation", "evidence-based design"],
    "T04": ["measurement", "learning analytics", "educational data mining", "psychometrics", "assessment"],
    "T05": ["knowledge representation", "ontology", "knowledge graph", "concept maps", "skill taxonomy"],
    "T06": ["intelligent tutoring", "adaptive systems", "knowledge tracing", "Bayesian student model", "ITS"],
    "T07": ["AI in learning", "foundation models", "LLM", "generative AI", "automated feedback"],
    "T08": ["simulation", "serious games", "VR", "experiential learning", "scenario-based training"],
    "T09": ["expert knowledge elicitation", "cognitive task analysis", "SME elicitation", "tacit knowledge"],
    "T10": ["workforce development", "training systems", "military training", "healthcare training", "upskilling"],
    "T11": ["learning infrastructure", "LMS", "xAPI", "learning record stores", "interoperability"],
    "T12": ["instructional design", "ADDIE", "backward design", "competency-based design", "curriculum mapping"],
    "T13": ["high-consequence domains", "defense", "healthcare", "aviation", "human error", "safety-critical"],
    "T14": ["ethics", "equity", "algorithmic fairness", "data privacy", "responsible AI"],
    "T15": ["evidence standards", "Kirkpatrick", "evaluation", "decision-grade evidence", "effectiveness research"],
    "T16": ["standards", "credentialing", "professional community", "IEEE ICICLE", "field development"],
    "T17": ["research methods", "randomized trials", "design-based research", "open science", "replication"],
}

HSI_SIGNALS = [
    "human systems integration", "hsi", "human factors", "crew resource management",
    "human error", "systems engineering", "sociotechnical", "human performance",
    "macrocognition", "human-centered", "human as", "ergonomics",
]

# ── Manual topic overrides (LLM-classified, no API key needed) ─────────────
# Every resource that had no topics assigned from frontmatter gets a curated
# topic list here. Keys are collection/slug (no .mdx extension).

MANUAL_TOPICS: dict[str, list[str]] = {
    # practice
    "practice/applying-learning-engineering-process-to-existing-military-training-pr": ["T03", "T10"],
    "practice/crucible-cyber-platform-brochure-they-have-learning-engineering-as-par": ["T07", "T08"],
    "practice/learning-engineering-new-profession-or-transformational-process": ["T00", "T16"],
    "practice/learning-engineering-virtual-training-systems-with-learning-science-da": ["T10", "T11", "T01"],
    # tools
    "tools/cmu-simon-initiative-learning-engineering-community": ["T16", "T00"],
    # reading-list
    "reading-list/7-things-to-know-about-learning-engineering": ["T00"],
    "reading-list/a-learning-engineering-model-for-learner-centered-adaptive-systems": ["T06", "T03"],
    "reading-list/aied-from-cognitive-simulations-to-learning-engineering-with-humans-in": ["T06", "T00"],
    "reading-list/applying-human-centered-learning-engineering-methods-to-learning": ["T03", "T02"],
    "reading-list/are-you-doing-learning-engineering-or-instructional-design": ["T00", "T12"],
    "reading-list/asu-learning-engineering-institute-website": ["T16", "T00"],
    "reading-list/at-advanced-distributed-learning-initiative-ifest-2022-conference-the-": ["T00", "T16"],
    "reading-list/beyond-benchmarks-responsible-ai-in-education-needs-learning-sciences": ["T07", "T14"],
    "reading-list/capturing-elusive-technology-designing-a-course-on-ai-for-learning-and": ["T07", "T12"],
    "reading-list/changing-the-production-function-in-higher-education": ["T00", "T15"],
    "reading-list/cold-rolled-steel-and-knowledge-what-can-higher-education-learn-about-": ["T03", "T15"],
    "reading-list/define-learning-engineering-with-the-trap-framework": ["T00"],
    "reading-list/developing-an-ontology-for-learning-engineering-learning-engineering-e": ["T05", "T00"],
    "reading-list/engaging-in-student-centered-educational-data-science-through-learning": ["T04", "T03"],
    "reading-list/engineering-learning-at-kaplan-university": ["T03", "T04"],
    "reading-list/exploring-learning-engineering-design-decision-tracking-emergent-theme": ["T03"],
    "reading-list/from-the-science-of-learning-and-development-to-learning-engineering": ["T01", "T00"],
    "reading-list/high-leverage-opportunities-for-learning-engineering-discusses-the-pot": ["T00", "T03"],
    "reading-list/how-cisco-networking-academy-s-learning-engineering-team-creates-a-pat": ["T03", "T14"],
    "reading-list/how-duolingo-s-ai-learns-what-you-need-to-learn-the-ai-that-powers-the": ["T07", "T06"],
    "reading-list/how-to-bring-learning-engineering-principles-to-your-classroom-intervi": ["T03", "T12"],
    "reading-list/how-to-improve-edtech-engagement-using-learning-engineering-principles": ["T03", "T04"],
    "reading-list/how-video-games-can-train-you-for-a-job-lessons-from-learning-engineer": ["T08", "T10"],
    "reading-list/icicle-2024-conference-proceedings": ["T16", "T00"],
    "reading-list/icicle-a-consortium-for-learning-engineering": ["T16"],
    "reading-list/in-the-2020-educause-horizon-report-teaching-and-learning-edition-the-": ["T00", "T16"],
    "reading-list/instructional-designer-or-learning-engineer-it-depends-on-how-you-brus": ["T00", "T12"],
    "reading-list/learning-engineering-a-caliper-example": ["T11", "T04"],
    "reading-list/learning-engineering-a-new-academic-discipline-and-engineering-profess": ["T00", "T16"],
    "reading-list/learning-engineering-a-primer-this-research-report-learning-engineerin": ["T00"],
    "reading-list/learning-engineering-a-view-on-where-the-field-is-at-where-it-s-going-": ["T00", "T16"],
    "reading-list/learning-engineering-at-a-glance-based-on-the-ifest-poster-winner-of-b": ["T00"],
    "reading-list/learning-engineering-is-learning-about-learning-we-need-that-now-more-": ["T00", "T01"],
    "reading-list/learning-engineering-leveraging-science-and-technology-for-effective-i": ["T03", "T00"],
    "reading-list/learning-engineering-making-its-way-in-the-world": ["T00", "T16"],
    "reading-list/learning-engineering-merging-science-and-data-to-design-powerful-learn": ["T00", "T04"],
    "reading-list/learning-engineering-past-present-and-future-note-icicle-images-and-re": ["T00"],
    "reading-list/learning-engineering-perspectives-for-supporting-educational-systems": ["T00", "T12"],
    "reading-list/learning-engineering-series-edsurge": ["T00"],
    "reading-list/learning-engineering-what-is-it-and-how-can-the-government-benefit": ["T00", "T10"],
    "reading-list/learning-engineering-workingoutloud-on-learning-science": ["T03", "T01"],
    "reading-list/learning-sciences-and-learning-engineering-a-natural-or-artificial-dis": ["T00", "T01"],
    "reading-list/leveraging-learning-engineering-to-advance-authentic-learning-in-virtu": ["T08", "T03"],
    "reading-list/online-education-a-catalyst-for-higher-education-reforms-mit": ["T00", "T11"],
    "reading-list/proceedings-of-the-2019-conference-on-learning-engineering": ["T16", "T00"],
    "reading-list/quinnsights-get-ready-for-learning-engineering": ["T00"],
    "reading-list/response-to-victor-lee-s-ls-and-le-learning-engineering-what-it-is-why": ["T00", "T01"],
    "reading-list/scaffolds-and-nudges-a-case-study-in-learning-engineering-design-impro": ["T03", "T01"],
    "reading-list/teaming-up-to-improve-medical-healthcare-education-instructional-desig": ["T10", "T13"],
    "reading-list/the-art-and-science-of-learning-engineering": ["T00", "T03"],
    "reading-list/the-job-of-a-college-president": ["T00"],
    "reading-list/the-rise-of-learning-engineering": ["T00"],
    "reading-list/the-value-proposition-of-e-generalized-intelligent-framework-for-tutor": ["T06", "T03"],
    "reading-list/why-we-need-learning-engineers": ["T00"],
    "reading-list/yet-analytics-learning-engineering-page": ["T04", "T11"],
    # events
    "events/a-practical-guide-to-using-open-tools-for-well-defined-competencies-le": ["T05", "T12"],
    "events/a-transformation-to-learning-engineering-bror-saxberg-2018-simon-initi": ["T00"],
    "events/advancing-expertise-development-through-adaptive-human-ai-training": ["T07", "T09", "T06"],
    "events/air-force-enterprise-learning-engineering-center-of-excellence-ele-coe": ["T10", "T13"],
    "events/are-you-curious-about-what-learning-engineering-is-listen-in-as-kateri": ["T00", "T07"],
    "events/asu-le-research-network-2026-convening": ["T16", "T00"],
    "events/bringing-learning-engineering-into-online-education": ["T00", "T11"],
    "events/bror-saxberg-gave-a-keynote-learning-engineering-what-we-know-what-we-": ["T00"],
    "events/but-how-do-you-know-they-learned-that": ["T04", "T15"],
    "events/carnegie-mellon-university-open-learning-institute-s-simon-approach-to": ["T00", "T03"],
    "events/cmu-learn-lab-learning-science-and-engineering-seminar-series": ["T01", "T00"],
    "events/cultural-dimensions-in-learning-engineering-redesigning-courses-for-in": ["T12", "T14"],
    "events/forging-effective-learning-with-bror-saxberg": ["T00"],
    "events/from-designer-to-engineer-new-roles-for-learning-professionals-dr-mich": ["T00", "T12"],
    "events/full-video-from-above-introduction-to-learning-engineering": ["T00"],
    "events/ifest-industry-keynote-bror-saxberg-learning-engineering-the-art-of-ap": ["T00"],
    "events/implementing-learning-in-military-environments-an-operational-tactical": ["T10", "T13"],
    "events/integrating-adaptive-interventions-into-learning-engineering-workflows": ["T06", "T03"],
    "events/intro-what-is-learning-engineering": ["T00"],
    "events/learning-engineering-competency-based-experiential-learning-within-ins": ["T12", "T03"],
    "events/learning-engineering-fellowship-program-a-case-study-in-data-driven-cu": ["T03", "T04"],
    "events/learning-engineering-in-practice-a-case-study-on-developing-llm-based-": ["T07", "T03"],
    "events/learning-engineering-the-art-of-applying-learning-science-to-real-worl": ["T00", "T10"],
    "events/learning-engineering-with-dr-bror-saxberg-why-doesn-t-education-have-m": ["T00"],
    "events/learning-engineering-with-kristin-torrence-head-of-learning-engineerin": ["T00"],
    "events/leveraging-deterministic-algorithms-to-personalize-education-and-enhan": ["T06", "T04"],
    "events/leveraging-learning-engineering-to-orchestrate-and-enhance-learning": ["T03", "T00"],
    "events/macrocognition-in-simulation-based-training-a-practical-application-of": ["T08", "T09", "T02"],
    "events/measuring-learning-technology-maturity-in-dod-acquisition": ["T11", "T10", "T15"],
    "events/mission-xrpossible-navigating-novice-to-expert-assessment-design-in-mi": ["T08", "T04"],
    "events/modern-learning": ["T00"],
    "events/overview-of-u-s-army-competency-based-training-and-the-role-of-simula": ["T10", "T08"],
    "events/qip-learning-engineering-videos": ["T00", "T03"],
    "events/webinar-learning-engineering-a-forum-with-bror-saxberg": ["T00"],
    # community
    "community/aetc-developing-enterprise-learning-engineering-center-of-excellence": ["T10", "T13", "T16"],
    "community/air-education-and-training-command-aetc-enterprise-learning-engineering": ["T10", "T13", "T16"],
    "community/air-force-enterprise-learning-engineering-center-of-excellence-ele-coe": ["T10", "T13"],
    "community/air-force-enterprise-learning-engineering-center-of-excellence": ["T10", "T13"],
    "community/airman-development-command-enterprise-learning-engineering-center-of-ex": ["T10", "T13"],
    "community/carnegie-mellon-open-learning-initiative-simon-initiative": ["T00", "T16", "T11"],
    "community/ele-coe-overview-presentation": ["T10", "T13"],
    "community/i-itsec-interservice-industry-training-simulation-education-conference": ["T10", "T08"],
}

# ── Helpers ───────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from an MDX file."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def slug_from_path(path: Path, collection: str) -> str:
    """Convert file path to collection-prefixed slug."""
    return f"{collection}/{path.stem}"


def assign_cluster(topics: list[str]) -> int:
    """Return best-match cluster for a topic list."""
    counts: Counter[int] = Counter()
    for t in topics:
        cid = TOPIC_TO_CLUSTER.get(t)
        if cid is not None:
            counts[cid] += 1
    if not counts:
        return 0
    return counts.most_common(1)[0][0]


def is_hsi_relevant(topics: list[str], title: str, summary: str) -> bool:
    """Flag Human Systems Integration relevance."""
    if "T02" in topics:
        return True
    text = (title + " " + (summary or "")).lower()
    return any(sig in text for sig in HSI_SIGNALS)


_STOP = {
    "a", "an", "the", "of", "in", "to", "for", "on", "at", "by", "with",
    "and", "or", "but", "is", "are", "was", "be", "as", "it", "its", "from",
    "how", "what", "why", "who", "when", "this", "that", "we", "our",
    "their", "using", "through", "into", "about", "up", "can", "new",
    "learning", "engineering",  # too broad to be distinguishing keywords alone
}


def title_keywords(title: str) -> list[str]:
    """Extract meaningful multi-word and single-word phrases from a title.

    Pulls 2-word bigrams first, then significant single words, filtering stop
    words and very short tokens. Returns up to 4 items.
    """
    words = re.sub(r"[^a-z0-9\s]", " ", title.lower()).split()
    meaningful = [w for w in words if len(w) > 3 and w not in _STOP]
    bigrams = [f"{meaningful[i]} {meaningful[i+1]}" for i in range(len(meaningful) - 1)]
    combined = bigrams[:2] + meaningful[:3]
    seen: set[str] = set()
    result: list[str] = []
    for k in combined:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result[:4]


def derive_keywords(topics: list[str], tags: list[str], title: str, summary: str) -> list[str]:
    """Build a deduplicated keyword list from topic codes, tags, and title."""
    kws: list[str] = []
    for t in topics:
        kws.extend(TOPIC_KEYWORDS.get(t, [])[:3])
    kws.extend(title_keywords(title))
    for tag in tags:
        if tag and not re.match(r"^T\d+$", tag) and not tag.startswith("http"):
            kws.append(tag.replace("-", " "))
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            result.append(kw)
    return result[:12]


def enrich_with_llm(resources: list[dict]) -> dict[str, list[str]]:
    """Call Claude API for richer keywords. Returns id → keywords map."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    results: dict[str, list[str]] = {}

    for i, res in enumerate(resources):
        rid = res["id"]
        prompt = (
            f"Resource: {res['title']}\n"
            f"Format: {res['format']}\n"
            f"Topics: {', '.join(res['topics'])}\n"
            f"Summary: {res.get('summary', '')[:400]}\n\n"
            "List 6-8 concise keyword phrases (2-4 words each) describing this resource's "
            "main themes. Focus on technical concepts, methods, and domain areas. "
            "Return only a JSON array of strings, no explanation."
        )
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            kws = json.loads(raw)
            if isinstance(kws, list):
                results[rid] = [str(k) for k in kws[:10]]
            else:
                results[rid] = []
        except Exception as e:
            print(f"  LLM error for {rid}: {e}", file=sys.stderr)
            results[rid] = []

        if (i + 1) % 10 == 0:
            print(f"  LLM enriched {i + 1}/{len(resources)}")

    return results


def main() -> None:
    """Entry point: parse args, scan content, write JSON outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Only process resource IDs not yet present in resource_keywords.json",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Call Claude API (claude-haiku) for keyword enrichment",
    )
    args = parser.parse_args()

    # Load existing keywords if running in incremental mode
    keywords_path = DATA_OUT / "resource_keywords.json"
    existing: dict[str, dict] = {}
    if args.new_only and keywords_path.exists():
        existing = json.loads(keywords_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(existing)} existing entries.")

    resources: list[dict] = []
    for collection in COLLECTIONS:
        col_dir = CONTENT / collection
        if not col_dir.exists():
            continue
        for mdx in sorted(col_dir.glob("**/*.mdx")):
            rid = slug_from_path(mdx, collection)
            if args.new_only and rid in existing:
                continue
            fm = parse_frontmatter(mdx.read_text(encoding="utf-8"))
            if not fm:
                continue
            topics = fm.get("topics") or []
            tags = [t for t in (fm.get("tags") or []) if t]
            resources.append({
                "id": rid,
                "title": fm.get("title", ""),
                "format": fm.get("format", ""),
                "topics": topics,
                "tags": tags,
                "summary": fm.get("summary", ""),
            })

    if not resources:
        print("No new resources to process.")
        return

    print(f"Processing {len(resources)} resources.")

    llm_keywords: dict[str, list[str]] = {}
    if args.llm:
        print("Calling Claude API for keyword enrichment …")
        llm_keywords = enrich_with_llm(resources)

    new_entries: dict[str, dict] = {}
    for res in resources:
        rid = res["id"]
        # Apply manual topic override if the resource has none from frontmatter
        topics = res["topics"] or MANUAL_TOPICS.get(rid, [])
        base_kws = derive_keywords(topics, res["tags"], res["title"], res["summary"])
        llm_kws = llm_keywords.get(rid, [])
        new_entries[rid] = {
            "keywords": llm_kws if llm_kws else base_kws,
            "hsi_relevant": is_hsi_relevant(topics, res["title"], res["summary"]),
            "cluster_id": assign_cluster(topics),
        }

    # Merge: existing entries first, new/updated entries override
    merged = {**existing, **new_entries}
    keywords_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {keywords_path} ({len(merged)} total entries)")

    # Always rewrite clusters (they don't change often, but keep them fresh)
    clusters_path = DATA_OUT / "topic_clusters.json"
    clusters_path.write_text(json.dumps(CLUSTERS, indent=2), encoding="utf-8")
    print(f"Wrote {clusters_path}")

    hsi_count = sum(1 for v in merged.values() if v["hsi_relevant"])
    no_topic_covered = sum(1 for v in new_entries.values() if v["cluster_id"] != 0 or v["keywords"])
    print(f"Done. {hsi_count} HSI-relevant resources. {no_topic_covered}/{len(new_entries)} newly enriched.")


if __name__ == "__main__":
    main()
