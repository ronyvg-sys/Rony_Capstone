"""Build a JSON embedding index for the W6 RAG application."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline.settings import Settings
from src.rag.naive_rag import build_index, save_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a W6 RAG embedding index."
    )

    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/corpus"),
        help="Directory containing .md/.txt corpus files.",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=500,
        help="Chunk size in characters.",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Chunk overlap in characters.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/embeddings.json"),
        help="Output JSON index path.",
    )

    args = parser.parse_args()

    if args.overlap >= args.size:
        raise ValueError("--overlap must be smaller than --size")

    settings = Settings()

    print("Building RAG index...")
    print(f"Corpus : {args.corpus}")
    print(f"Size   : {args.size}")
    print(f"Overlap: {args.overlap}")
    print(f"Output : {args.out}")

    index = build_index(
        corpus_dir=args.corpus,
        size=args.size,
        overlap=args.overlap,
        settings=settings,
    )

    save_index(index, args.out)

    print()
    print("Index created successfully.")
    print(f"Documents/chunks: {len(index['chunks'])}")
    print(f"Embedding model : {index['embedding_model']}")
    print(f"Chunk size      : {index['chunk_size']}")
    print(f"Chunk overlap   : {index['chunk_overlap']}")
    print(f"Output file     : {args.out}")


if __name__ == "__main__":
    main()
