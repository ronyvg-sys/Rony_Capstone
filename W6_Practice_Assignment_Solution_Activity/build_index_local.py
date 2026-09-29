"""build_index_local.py — W6 Activity B (stretch).

Variant of build_index.py that uses sentence-transformers embeddings
instead of OpenAI. Same chunker, same corpus, different embedder.

Output: a parallel embeddings file with 384-dim vectors instead of
1536-dim. Use it as --index to run_rag_eval.py.

Usage:
    python scripts/build_index_local.py \\
        --corpus data/corpus \\
        --out data/embeddings_local.json
"""
import argparse
import json
from pathlib import Path

from src.rag.chunker import chunk_corpus
from src.rag.embeddings_local import embed_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/corpus")
    parser.add_argument("--out", default="data/embeddings_local.json")
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    args = parser.parse_args()

    print(f"Chunking {args.corpus} with size={args.size} overlap={args.overlap}...")
    chunks = chunk_corpus(args.corpus, size=args.size, overlap=args.overlap)
    print(f"  Got {len(chunks)} chunks.")

    print(f"Embedding with sentence-transformers (local, free)...")
    texts = [c.text for c in chunks]
    vectors = embed_batch(texts)
    print(f"  Embedded {len(vectors)} chunks; dim = {len(vectors[0])}")

    # Write to JSON in the same format as build_index.py
    output = {
        "metadata": {
            "embedder": "sentence-transformers/all-MiniLM-L6-v2",
            "embedder_dim": len(vectors[0]),
            "chunk_size": args.size,
            "chunk_overlap": args.overlap,
            "n_chunks": len(chunks),
            "cost_usd": 0.0,
        },
        "chunks": [
            {"text": c.text, "source": c.source, "embedding": v}
            for c, v in zip(chunks, vectors)
        ],
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(output, f)
    print(f"Wrote {args.out}.")


if __name__ == "__main__":
    main()
