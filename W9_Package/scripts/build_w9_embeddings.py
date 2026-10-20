
"""Build Week 9 embeddings from the structure-aware chunk file."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PACKAGE_ROOT / "data" / "w9_common_chunks.json"
OUTPUT_FILE = PACKAGE_ROOT / "data" / "w9_embeddings_small.json"
MODEL = "text-embedding-3-small"
DIMENSION = 1536
BATCH_SIZE = 100


def main():
    load_dotenv(PACKAGE_ROOT.parent / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    chunks = data["chunks"]

    if not chunks:
        raise ValueError(f"No chunks found in {INPUT_FILE}")

    client = OpenAI()
    texts = [chunk["text"] for chunk in chunks]
    vectors = []
    total_tokens = 0

    print(f"Model: {MODEL}")
    print(f"Chunks: {len(texts)}")
    print("Generating embeddings...")

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        response = client.embeddings.create(
            model=MODEL,
            input=batch,
        )
        vectors.extend(item.embedding for item in response.data)
        if response.usage:
            total_tokens += response.usage.prompt_tokens

    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Expected {len(chunks)} vectors, received {len(vectors)}."
        )

    if any(len(vector) != DIMENSION for vector in vectors):
        raise RuntimeError(f"Expected {DIMENSION}-dimension embeddings.")

    output_chunks = []
    for chunk, vector in zip(chunks, vectors):
        output_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "text": chunk["text"],
            "embedding": vector,
        })

    output = {
        "embedding_model": MODEL,
        "embedding_dimension": DIMENSION,
        "chunking_strategy": data["chunking_strategy"],
        "target_chunk_size": data["target_chunk_size"],
        "chunks": output_chunks,
        "usage": {"prompt_tokens": total_tokens},
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Embedded chunks: {len(output_chunks)}")
    print(f"Embedding dimension: {DIMENSION}")
    print(f"Prompt tokens: {total_tokens}")


if __name__ == "__main__":
    main()
