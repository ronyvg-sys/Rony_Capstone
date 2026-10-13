"""Build OpenAI embeddings for the common W7 chunk set."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


INPUT_FILE = Path("data/w7_common_chunks.json")

MODELS = {
    "small": {
        "model": "text-embedding-3-small",
        "dimension": 1536,
        "price_per_million_tokens": 0.02,
        "output_file": Path("data/w7_embeddings_small.json"),
    },
    "large": {
        "model": "text-embedding-3-large",
        "dimension": 3072,
        "price_per_million_tokens": 0.13,
        "output_file": Path("data/w7_embeddings_large.json"),
    },
}


def build_embeddings(size: str) -> None:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    config = MODELS[size]

    client = OpenAI()

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    chunks = data["chunks"]
    texts = [chunk["text"] for chunk in chunks]

    print(f"Model: {config['model']}")
    print(f"Chunks: {len(texts)}")
    print("Generating embeddings...")

    response = client.embeddings.create(
        model=config["model"],
        input=texts,
    )

    vectors = [item.embedding for item in response.data]

    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Expected {len(chunks)} embeddings but received {len(vectors)}."
        )

    if len(vectors[0]) != config["dimension"]:
        raise RuntimeError(
            f"Expected dimension {config['dimension']} "
            f"but received {len(vectors[0])}."
        )

    prompt_tokens = response.usage.prompt_tokens
    estimated_cost = (
        prompt_tokens / 1_000_000
    ) * config["price_per_million_tokens"]

    output_chunks = []

    for chunk, vector in zip(chunks, vectors):
        output_chunks.append(
            {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
                "embedding": vector,
            }
        )

    output = {
        "embedding_model": config["model"],
        "embedding_dimension": config["dimension"],
        "chunk_size": data["chunk_size"],
        "chunk_overlap": data["chunk_overlap"],
        "chunks": output_chunks,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "estimated_cost_usd": estimated_cost,
        },
    }

    config["output_file"].write_text(
        json.dumps(output),
        encoding="utf-8",
    )

    print(f"Created: {config['output_file']}")
    print(f"Model: {config['model']}")
    print(f"Dimensions: {config['dimension']}")
    print(f"Chunks: {len(output_chunks)}")
    print(f"Prompt tokens: {prompt_tokens}")
    print(f"Estimated cost: ${estimated_cost:.8f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in MODELS:
        print("Usage: python -m scripts.build_openai_embeddings small")
        print("   or: python -m scripts.build_openai_embeddings large")
        raise SystemExit(1)

    build_embeddings(sys.argv[1])