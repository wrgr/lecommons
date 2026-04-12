#!/usr/bin/env python3
"""Build website data artifacts from the current Learning Engineering corpus."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

from utils import (
    load_json, load_jsonl, write_json, normalize_doi, doi_to_url,
    citation_plain, citation_bibtex, parse_authors, normalize_url, listify,
    ROOT, CORPUS_DIR, DATA_DIR,
)
from abstract_fetcher import (
    enrich_papers_with_openalex,
    Topic,
    load_topics,
    build_seed_topic_lookup,
)


def build_seed_papers(topic_by_code: Dict[str, Topic]) -> List[Dict]:
    rows = load_jsonl(CORPUS_DIR / "academic_papers.jsonl")
    papers: List[Dict] = []
    for row in rows:
        topic_codes = [row.get("primary_topic", "")] + listify(row.get("secondary_topics", []))
        topic_codes = [code for code in topic_codes if code in topic_by_code]

        title = (row.get("title") or "").strip()
        authors_text = (row.get("authors") or "").strip()
        year = row.get("year")
        venue = (row.get("venue") or "").strip()
        doi = normalize_doi(row.get("doi") or "")

        paper = {
            "id": (row.get("resource_id") or "").strip(),
            "openalex_id": (row.get("openalex_id") or "").strip(),
            "title": title,
            "abstract": "",
            "abstract_source": "",
            "abstract_is_proxy": False,
            "year": year,
            "doi": doi,
            "venue": venue,
            "type": "seed_record",
            "cited_by_count": int(row.get("citation_count") or 0) if str(row.get("citation_count") or "").isdigit() else 0,
            "authors": parse_authors(authors_text),
            "referenced_works": [],
            "citation_plain": citation_plain(title, authors_text, year, venue, doi),
            "citation_bibtex": citation_bibtex((row.get("resource_id") or "seed"), title, authors_text, year, venue, doi),
            "source_url": doi_to_url(doi),
            "scope": "seed",
            "status": (row.get("status") or "").strip(),
            "selection_tier": (row.get("selection_tier") or "").strip(),
            "topic_codes": topic_codes,
            "artifact_type": (row.get("content_type") or "AP").strip() or "AP",
            "topic_names": [topic_by_code[code].name for code in topic_codes if code in topic_by_code],
        }
        if paper["id"]:
            papers.append(paper)

    by_id = {}
    for paper in papers:
        by_id.setdefault(paper["id"], paper)
    return list(by_id.values())


def build_hop_papers(topic_by_code: Dict[str, Topic], seed_topic_lookup: Dict[str, Set[str]]) -> List[Dict]:
    rows = load_jsonl(CORPUS_DIR / "expansion" / "candidates_cross_seed_ge2_kcore2_indegree2.jsonl")
    papers: List[Dict] = []
    for row in rows:
        topic_codes: Set[str] = set()
        for seed_id in row.get("origin_seed_ids", []) or []:
            topic_codes.update(seed_topic_lookup.get(seed_id, set()))

        mapped_topics = sorted(code for code in topic_codes if code in topic_by_code)
        if not mapped_topics:
            continue

        work_id = (row.get("work_id") or "").strip()
        if not work_id:
            continue

        doi = normalize_doi(row.get("doi") or "")
        title = (row.get("title") or "Untitled").strip()
        year = row.get("publication_year")
        venue = (row.get("host_venue") or "").strip()

        papers.append(
            {
                "id": work_id,
                "openalex_id": (row.get("openalex_id") or "").strip(),
                "title": title,
                "abstract": "",
                "abstract_source": "",
                "abstract_is_proxy": False,
                "year": year,
                "doi": doi,
                "venue": venue,
                "type": (row.get("type") or "article").strip() or "article",
                "cited_by_count": int(row.get("cited_by_count") or 0),
                "authors": [],
                "referenced_works": [],
                "citation_plain": citation_plain(title, "", year, venue, doi),
                "citation_bibtex": citation_bibtex(work_id, title, "", year, venue, doi),
                "source_url": doi_to_url(doi) or (row.get("openalex_id") or ""),
                "scope": "hop",
                "topic_codes": mapped_topics,
                "topic_names": [topic_by_code[code].name for code in mapped_topics],
                "artifact_type": "derived_one_hop",
                "cross_seed_score": int(row.get("cross_seed_score") or 0),
                "origin_seed_ids": row.get("origin_seed_ids", []),
                "edge_types": row.get("edge_types", []),
            }
        )

    by_id = {}
    for paper in papers:
        by_id.setdefault(paper["id"], paper)
    return list(by_id.values())


def build_resources(topic_by_code: Dict[str, Topic]) -> Tuple[Dict, List[Dict]]:
    """Build the non-paper resource index, merging ICICLE and programs/people registries."""
    rows = load_jsonl(CORPUS_DIR / "non_paper_resources.jsonl")
    icicle_path = CORPUS_DIR / "tables" / "icicle_resources_registry.json"
    if icicle_path.exists():
        rows = rows + load_json(icicle_path)
    pp_path = CORPUS_DIR / "tables" / "programs_people_registry.json"
    if pp_path.exists():
        rows = rows + load_json(pp_path)
    # Deduplicate by resource_id (last entry for a given ID wins).
    seen: dict = {}
    for row in rows:
        rid = (row.get("resource_id") or "").strip()
        if rid:
            seen[rid] = row
        else:
            seen[id(row)] = row
    rows = list(seen.values())

    items_by_topic: Dict[str, List[Dict]] = defaultdict(list)
    flat_rows: List[Dict] = []

    for row in rows:
        primary = (row.get("primary_topic") or "").strip()
        if primary not in topic_by_code:
            continue

        secondary = [code for code in listify(row.get("secondary_topics", [])) if code in topic_by_code]
        topic_codes = [primary, *[code for code in secondary if code != primary]]

        title = (row.get("name") or "Untitled").strip()
        item = {
            "resource_id": (row.get("resource_id") or "").strip(),
            "title": title,
            "url": normalize_url(row.get("url") or ""),
            "context": (row.get("description") or "").strip(),
            "topic_codes": topic_codes,
            "content_type": (row.get("content_type") or "").strip(),
            "status": (row.get("status") or "").strip(),
            "section": f"{primary} {topic_by_code[primary].name}",
        }
        items_by_topic[primary].append(item)
        flat_rows.append(item)

    sections = []
    for code, topic in topic_by_code.items():
        entries = items_by_topic.get(code, [])
        if not entries:
            continue
        sections.append({"section": f"{code} {topic.name}", "items": entries})

    payload = {
        "source_url": "corpus/non_paper_resources.jsonl",
        "section_count": len(sections),
        "item_count": len(flat_rows),
        "sections": sections,
    }
    return payload, flat_rows


def build_programs(non_paper_rows: List[Dict]) -> Dict:
    category_map = {
        "AP": "academic_papers",
        "PC": "academic",
        "PP": "people",
        "CE": "events",
        "TP": "tools",
        "CO": "organizations",
        "GL": "grey_literature",
    }
    programs = []
    for row in non_paper_rows:
        if row.get("content_type") not in category_map:
            continue
        programs.append(
            {
                "name": row.get("title", ""),
                "category": category_map.get(row.get("content_type"), "other"),
                "summary": row.get("context", ""),
                "links": [row.get("url")] if row.get("url") else [],
            }
        )
    return {"programs": programs, "adjacent_program_mentions": []}


def build_endnotes() -> Tuple[Dict, Dict]:
    notes = load_jsonl(CORPUS_DIR / "book_endnotes_unique.jsonl")

    raw_notes = []
    enriched_rows = []
    for row in notes:
        artifact_type = (row.get("reference_category") or "grey_like").strip() or "grey_like"
        raw_notes.append(
            {
                "id": row.get("reference_id"),
                "artifact_type": artifact_type,
                "raw_text": row.get("citation_text", ""),
                "doi": row.get("doi", ""),
                "urls": row.get("urls", []),
                "expansion_eligible": bool(row.get("expansion_eligible")),
            }
        )
        enriched_rows.append(
            {
                "id": row.get("reference_id"),
                "chapter": None,
                "matched": bool(row.get("expansion_eligible")),
                "work_id": "",
                "artifact_type": artifact_type,
            }
        )

    raw_payload = {"notes": raw_notes, "count": len(raw_notes)}
    enriched_payload = {"rows": enriched_rows, "count": len(enriched_rows)}
    return raw_payload, enriched_payload


def build_gaps() -> Dict:
    rows = load_json(CORPUS_DIR / "tables" / "gap_tracker.json")
    gaps = []
    for row in rows:
        gap_id = (row.get("gap_id") or "").strip()
        if not gap_id:
            continue
        gaps.append(
            {
                "id": gap_id.lower().replace("-", "_"),
                "label": f"{row.get('topic', '').strip()} {row.get('gap_description', '').strip()}".strip(),
                "detail": (row.get("recommended_action") or "").strip(),
                "evidence_links": [],
                "evidence": {
                    "topic": row.get("topic"),
                    "severity": row.get("severity"),
                    "status": row.get("status"),
                },
            }
        )
    return {"gaps": gaps}


def build_topic_payload(topics: List[Topic]) -> Dict:
    return {
        "count": len(topics),
        "topics": [
            {
                "topic_code": topic.code,
                "layer": topic.layer,
                "topic_name": topic.name,
                "why_it_matters": topic.why,
            }
            for topic in topics
        ],
    }


def build_concept_graph(
    concepts: List[Dict],
    topic_codes: Set[str],
    paper_ids: Set[str],
    resource_ids: Set[str],
) -> Tuple[List[Dict], List[Dict]]:
    """Build concept-layer nodes and edges from the concept ontology and concept graph seeds."""
    nodes: List[Dict] = []
    edges: List[Dict] = []
    edge_seen: Set[Tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, edge_type: str) -> None:
        """Deduplicate and append a concept-layer edge."""
        if not source or not target or source == target:
            return
        key = (source, target, edge_type)
        if key in edge_seen:
            return
        edge_seen.add(key)
        edges.append({"source": source, "target": target, "type": edge_type})

    concept_ids: Set[str] = set()
    for concept in concepts:
        cid = concept.get("concept_id", "").strip()
        if not cid:
            continue
        concept_ids.add(cid)
        nodes.append({
            "id": cid,
            "label": concept.get("name", cid),
            "type": "concept",
            "hop": 0,
            "topic_codes": concept.get("topic_codes", []),
            "provenance": {
                "book_chapters": concept.get("book_chapter_anchors", []),
                "bloom_level": concept.get("bloom_level", ""),
                "layer": "concept",
            },
        })
        for code in concept.get("topic_codes", []):
            if code in topic_codes:
                add_edge(code, cid, "has_concept")
        for pid in concept.get("primary_papers", []):
            if pid in paper_ids:
                add_edge(cid, pid, "anchored_by")
        for rid in concept.get("primary_resources", []):
            if rid in resource_ids:
                add_edge(cid, rid, "learn_via")

    seeds_path = CORPUS_DIR / "tables" / "concept_graph_seeds.json"
    if seeds_path.exists():
        for row in load_json(seeds_path):
            if (row.get("node_type") or "") != "CONCEPT":
                continue
            src = (row.get("node_id") or "").strip()
            dst = (row.get("edge_target") or "").strip()
            edge_type = (row.get("edge_type") or "").strip()
            if edge_type == "PREREQ_FOR" and src in concept_ids and dst in concept_ids:
                add_edge(src, dst, "prereq")

    return nodes, edges


def build_graph(
    topics: List[Topic],
    seed_papers: List[Dict],
    hop_papers: List[Dict],
    resources_flat: List[Dict],
) -> Dict:
    nodes: List[Dict] = []
    edges: List[Dict] = []

    topic_codes = {topic.code for topic in topics}

    for topic in topics:
        nodes.append(
            {
                "id": topic.code,
                "label": f"{topic.code} {topic.name}",
                "type": "topic",
                "hop": 0,
                "topic_code": topic.code,
                "provenance": {
                    "layer": topic.layer,
                    "why_it_matters": topic.why,
                },
            }
        )

    for paper in seed_papers:
        nodes.append(
            {
                "id": paper["id"],
                "label": paper["title"],
                "type": "paper",
                "hop": 0,
                "topic_codes": paper.get("topic_codes", []),
                "provenance": {
                    "scope": "seed",
                    "selection_tier": paper.get("selection_tier"),
                    "artifact_type": paper.get("artifact_type"),
                },
            }
        )

    for paper in hop_papers:
        nodes.append(
            {
                "id": paper["id"],
                "label": paper["title"],
                "type": "paper",
                "hop": 1,
                "topic_codes": paper.get("topic_codes", []),
                "provenance": {
                    "scope": "hop",
                    "cross_seed_score": paper.get("cross_seed_score"),
                    "artifact_type": paper.get("artifact_type"),
                },
            }
        )

    for resource in resources_flat:
        rid = resource.get("resource_id")
        if not rid:
            continue
        nodes.append(
            {
                "id": rid,
                "label": resource.get("title", "Resource"),
                "type": "resource",
                "hop": 0,
                "topic_codes": resource.get("topic_codes", []),
                "provenance": {
                    "content_type": resource.get("content_type"),
                    "status": resource.get("status"),
                },
            }
        )

    edge_seen: Set[Tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, edge_type: str, provenance: Dict | None = None) -> None:
        if not source or not target or source == target:
            return
        key = (source, target, edge_type)
        if key in edge_seen:
            return
        edge_seen.add(key)
        edge = {"source": source, "target": target, "type": edge_type}
        if provenance:
            edge["provenance"] = provenance
        edges.append(edge)

    kg_rows = load_json(CORPUS_DIR / "tables" / "knowledge_graph_seeds.json")
    for row in kg_rows:
        if (row.get("node_type") or "") != "TOPIC":
            continue
        src = (row.get("node_id") or "").strip()
        dst = (row.get("edge_target") or "").strip()
        if src in topic_codes and dst in topic_codes:
            add_edge(src, dst, "prereq", {"edge_label": row.get("edge_label", "")})

    for paper in seed_papers + hop_papers:
        for code in paper.get("topic_codes", []):
            if code in topic_codes:
                add_edge(code, paper["id"], "contains")

    for resource in resources_flat:
        rid = resource.get("resource_id")
        for code in resource.get("topic_codes", []):
            if rid and code in topic_codes:
                add_edge(code, rid, "resource")

    for paper in hop_papers:
        for seed_id in paper.get("origin_seed_ids", []) or []:
            if not seed_id.startswith("WORKBOOK-LE-T1-"):
                continue
            seed_paper_id = seed_id.replace("WORKBOOK-", "", 1)
            add_edge(seed_paper_id, paper["id"], "expands_to")

    paper_id_set = {p["id"] for p in seed_papers + hop_papers}
    resource_id_set = {r.get("resource_id", "") for r in resources_flat if r.get("resource_id")}
    concept_ontology_path = CORPUS_DIR / "tables" / "concept_ontology.json"
    if concept_ontology_path.exists():
        concept_nodes, concept_edges = build_concept_graph(
            load_json(concept_ontology_path),
            topic_codes,
            paper_id_set,
            resource_id_set,
        )
        nodes.extend(concept_nodes)
        for ce in concept_edges:
            add_edge(ce["source"], ce["target"], ce["type"])

    return {"nodes": nodes, "edges": edges}


def build_summary(
    seed_papers: List[Dict],
    hop_papers: List[Dict],
    resources_flat: List[Dict],
    graph: Dict,
    endnotes_raw: Dict,
    openalex_enrichment: Dict,
) -> Dict:
    seed_resolution = load_jsonl(CORPUS_DIR / "expansion" / "seed_resolutions.jsonl")
    matched_endnotes = sum(
        1
        for row in seed_resolution
        if row.get("seed_kind") == "book_endnote_reference" and bool(row.get("matched"))
    )

    return {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "parsed_endnotes": endnotes_raw.get("count", 0),
        "matched_endnotes": matched_endnotes,
        "seed_papers": len(seed_papers),
        "one_hop_papers": len(hop_papers),
        "icicle_resource_items": len(resources_flat),
        "graph_nodes": len(graph.get("nodes", [])),
        "graph_edges": len(graph.get("edges", [])),
        "concept_nodes": len([n for n in graph.get("nodes", []) if n.get("type") == "concept"]),
        "openalex_papers_total": openalex_enrichment.get("papers_total", 0),
        "openalex_matches": openalex_enrichment.get("papers_with_openalex_match", 0),
        "openalex_abstracts_filled": openalex_enrichment.get("abstracts_filled", 0),
        "openalex_title_lookups": openalex_enrichment.get("openalex_title_lookups", 0),
        "openalex_resolved_by_title": openalex_enrichment.get("openalex_resolved_by_title", 0),
        "crossref_abstracts_filled": openalex_enrichment.get("crossref_abstracts_filled", 0),
        "arxiv_abstracts_filled": openalex_enrichment.get("arxiv_abstracts_filled", 0),
        "url_abstracts_filled": openalex_enrichment.get("url_abstracts_filled", 0),
        "url_pdf_abstracts_filled": openalex_enrichment.get("url_pdf_abstracts_filled", 0),
        "proxy_descriptions_filled": openalex_enrichment.get("proxy_descriptions_filled", 0),
        "papers_with_proxy_description": openalex_enrichment.get("papers_with_proxy_description", 0),
        "papers_without_source_abstract": openalex_enrichment.get("papers_without_source_abstract", 0),
        "papers_missing_abstract": openalex_enrichment.get("papers_missing_abstract", 0),
    }


def build_extra_docs() -> Dict:
    return {
        "count": 2,
        "documents": [
            {
                "source_type": "methodology",
                "title": "Corpus Construction Methodology (April 2026)",
                "url": "",
                "file_path": str(CORPUS_DIR / "methodology.md"),
                "summary": "Methodological framework for seed expansion, cross-seed filtering, subdomain scoring, and manual quality controls.",
            },
            {
                "source_type": "specification",
                "title": "Learning Engineering Corpus Specification Workbook v1",
                "url": "",
                "file_path": str(ROOT / "le_corpus_specification_v1.xlsx"),
                "summary": "Canonical topic map, registries, metadata schema, gaps, and selection pipeline for this corpus.",
            },
        ],
    }


def build_missing_abstracts(seed_papers: List[Dict], hop_papers: List[Dict]) -> Dict:
    rows = []
    for paper in seed_papers + hop_papers:
        has_abstract_text = bool((paper.get("abstract") or "").strip())
        is_proxy = bool(paper.get("abstract_is_proxy"))
        if has_abstract_text and not is_proxy:
            continue
        rows.append(
            {
                "id": paper.get("id", ""),
                "scope": paper.get("scope", ""),
                "type": paper.get("type", ""),
                "title": paper.get("title", ""),
                "doi": normalize_doi(paper.get("doi", "")),
                "openalex_id": paper.get("openalex_id", ""),
                "source_url": paper.get("source_url", ""),
                "topic_codes": paper.get("topic_codes", []),
                "abstract_source": paper.get("abstract_source", ""),
                "is_proxy_description": is_proxy,
                "has_abstract_text": has_abstract_text,
            }
        )
    rows.sort(key=lambda row: (row.get("scope", ""), row.get("id", "")))
    proxy_count = sum(1 for row in rows if row.get("is_proxy_description"))
    true_missing_count = sum(1 for row in rows if not row.get("has_abstract_text"))
    return {
        "count": len(rows),
        "proxy_count": proxy_count,
        "true_missing_count": true_missing_count,
        "rows": rows,
    }


def audit_resource_diversity(resources_flat: List[Dict], topic_by_code: Dict) -> Dict:
    """
    Lightweight bias / diversity audit for the resource registry.

    Checks:
    - No single content_type accounts for >60% of resources in any topic.
    - Each topic with >=3 resources has at least 2 distinct content_types.
    """
    from collections import Counter

    per_topic: Dict[str, Counter] = defaultdict(Counter)
    for r in resources_flat:
        for code in r.get("topic_codes", []):
            per_topic[code][r.get("content_type", "?")] += 1

    warnings = []
    topic_summaries = {}
    for code, counts in per_topic.items():
        total = sum(counts.values())
        topic_summaries[code] = dict(counts)
        for ctype, n in counts.items():
            pct = n / total
            if pct > 0.60 and total >= 3:
                topic_name = topic_by_code.get(code, type("T", (), {"name": code})()).name
                warnings.append(
                    f"{code} {topic_name}: content_type '{ctype}' is {pct:.0%} of {total} resources"
                )
        if total >= 3 and len(counts) < 2:
            topic_name = topic_by_code.get(code, type("T", (), {"name": code})()).name
            warnings.append(
                f"{code} {topic_name}: only 1 content_type across {total} resources — consider diversifying"
            )

    return {"warnings": warnings, "per_topic_content_types": topic_summaries}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    topics, topic_by_code = load_topics()
    seed_topic_lookup = build_seed_topic_lookup(topic_by_code)

    seed_papers = build_seed_papers(topic_by_code)
    hop_papers = build_hop_papers(topic_by_code, seed_topic_lookup)
    openalex_enrichment = enrich_papers_with_openalex(seed_papers, hop_papers)

    resources_payload, resources_flat = build_resources(topic_by_code)
    programs_payload = build_programs(resources_flat)
    endnotes_raw, endnotes_enriched = build_endnotes()
    gaps_payload = build_gaps()
    topic_payload = build_topic_payload(topics)

    graph_payload = build_graph(topics, seed_papers, hop_papers, resources_flat)
    summary_payload = build_summary(
        seed_papers,
        hop_papers,
        resources_flat,
        graph_payload,
        endnotes_raw,
        openalex_enrichment,
    )
    extra_docs_payload = build_extra_docs()
    missing_abstracts_payload = build_missing_abstracts(seed_papers, hop_papers)

    write_json(DATA_DIR / "build_summary.json", summary_payload)
    write_json(DATA_DIR / "graph.json", graph_payload)
    write_json(DATA_DIR / "icicle_resources.json", resources_payload)
    write_json(DATA_DIR / "papers_seed.json", {"papers": seed_papers})
    write_json(DATA_DIR / "papers_one_hop.json", {"papers": hop_papers})
    write_json(DATA_DIR / "endnotes_raw.json", endnotes_raw)
    write_json(DATA_DIR / "endnotes_enriched.json", endnotes_enriched)
    write_json(DATA_DIR / "programs_summary.json", programs_payload)
    write_json(DATA_DIR / "gaps.json", gaps_payload)
    write_json(DATA_DIR / "extra_docs.json", extra_docs_payload)
    write_json(DATA_DIR / "topic_map.json", topic_payload)
    write_json(DATA_DIR / "missing_abstracts.json", missing_abstracts_payload)
    diversity_audit = audit_resource_diversity(resources_flat, topic_by_code)
    write_json(DATA_DIR / "diversity_audit.json", diversity_audit)
    if diversity_audit["warnings"]:
        print("\n[diversity audit] warnings:")
        for w in diversity_audit["warnings"]:
            print(f"  ⚠  {w}")
    journeys_src = CORPUS_DIR / "tables" / "learning_journeys.json"
    if journeys_src.exists():
        write_json(DATA_DIR / "learning_journeys.json", load_json(journeys_src))

    print(json.dumps(summary_payload, indent=2))


if __name__ == "__main__":
    main()
