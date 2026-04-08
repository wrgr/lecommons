#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.knowledge_ops import (  # noqa: E402
    load_external_docs,
    rebuild_rag_corpus,
    sync_knowledge,
)


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search/webscan/upload documents and refresh corpus/RAG artifacts."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--tag", action="append", default=[], help="Optional tag(s) for ingested docs.")
    common.add_argument(
        "--rebuild-dataset",
        action="store_true",
        help="Run scripts/build_dataset.py before rebuilding rag corpus.",
    )
    common.add_argument(
        "--skip-openalex",
        action="store_true",
        help="When used with --rebuild-dataset, skip OpenAlex network calls.",
    )

    search = sub.add_parser("search", parents=[common], help="Search the web, scan top results, and ingest them.")
    search.add_argument("--query", required=True, help="Web search query.")
    search.add_argument("--max-results", type=int, default=6, help="How many URLs to retrieve from web search.")
    search.add_argument(
        "--scan-results",
        type=int,
        default=4,
        help="How many search results to webscan and ingest.",
    )

    scan = sub.add_parser("webscan", parents=[common], help="Scan one or more URLs and ingest text.")
    scan.add_argument("--url", action="append", required=True, help="URL to scan. Repeat for multiple URLs.")

    upload = sub.add_parser("upload", parents=[common], help="Upload local documents by filesystem path.")
    upload.add_argument("--path", action="append", required=True, help="Path to document. Repeat for multiple.")

    sync = sub.add_parser(
        "sync",
        parents=[common],
        help="Combined flow: optional query search + URL scan + local upload in one run.",
    )
    sync.add_argument("--query", help="Optional web search query.")
    sync.add_argument("--max-results", type=int, default=6)
    sync.add_argument("--scan-results", type=int, default=4)
    sync.add_argument("--url", action="append", default=[], help="Optional URL to scan.")
    sync.add_argument("--path", action="append", default=[], help="Optional local path to upload.")

    sub.add_parser("rebuild-corpus", help="Rebuild data/rag_corpus.jsonl from dataset + extra docs.")
    view = sub.add_parser("list", help="List ingested extra docs.")
    view.add_argument("--limit", type=int, default=25)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "rebuild-corpus":
        _print(rebuild_rag_corpus())
        return

    if args.cmd == "list":
        payload = load_external_docs()
        docs = payload.get("documents", [])
        payload["documents"] = docs[: max(1, args.limit)]
        _print(payload)
        return

    if args.cmd == "search":
        report = sync_knowledge(
            query=args.query,
            max_search_results=args.max_results,
            scan_search_results=args.scan_results,
            tags=args.tag,
            rebuild_dataset_first=args.rebuild_dataset,
            skip_openalex=args.skip_openalex,
        )
        _print(report)
        return

    if args.cmd == "webscan":
        report = sync_knowledge(
            urls=args.url,
            tags=args.tag,
            rebuild_dataset_first=args.rebuild_dataset,
            skip_openalex=args.skip_openalex,
        )
        _print(report)
        return

    if args.cmd == "upload":
        report = sync_knowledge(
            paths=args.path,
            tags=args.tag,
            rebuild_dataset_first=args.rebuild_dataset,
            skip_openalex=args.skip_openalex,
        )
        _print(report)
        return

    if args.cmd == "sync":
        report = sync_knowledge(
            query=args.query,
            urls=args.url,
            paths=args.path,
            max_search_results=args.max_results,
            scan_search_results=args.scan_results,
            tags=args.tag,
            rebuild_dataset_first=args.rebuild_dataset,
            skip_openalex=args.skip_openalex,
        )
        _print(report)
        return

    parser.error(f"Unsupported command: {args.cmd}")


if __name__ == "__main__":
    main()
