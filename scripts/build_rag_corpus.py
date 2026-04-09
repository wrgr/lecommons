#!/usr/bin/env python3
"""Build retrieval chunks for the Learning Engineering RAG service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.corpus import build_documents_from_dataset, write_documents_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data", help="Directory containing dataset JSON files.")
    parser.add_argument(
        "--output",
        default="data/rag_corpus.jsonl",
        help="Path to write retrieval corpus JSONL.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    output = Path(args.output).resolve()

    docs = build_documents_from_dataset(data_dir)
    write_documents_jsonl(docs, output)
    print(f"Wrote {len(docs)} retrieval documents to {output}")


if __name__ == "__main__":
    main()
