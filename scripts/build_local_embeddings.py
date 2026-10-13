"""Build local MiniLM embeddings for the common W7 chunk set."""

import json
from pathlib import Path

from src.rag.embeddings_local import embed_local


INPUT_FILE = Path("data/w7_common_chunks.json")
OUTPUT_FILE = Path("data/w7_embeddings_local.json")


def main() -> None:
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    chunks = data["chunks"]

    texts = [chunk["text"] for chunk in chunks]

    print(f"Embedding {len(texts)} chunks locally...")
    vectors = embed_local(texts)

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
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "chunk_size": data["chunk_size"],
        "chunk_overlap": data["chunk_overlap"],
        "chunks": output_chunks,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output),
        encoding="utf-8",
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Model: {output['embedding_model']}")
    print(f"Dimensions: {output['embedding_dimension']}")
    print(f"Chunks: {len(output_chunks)}")


if __name__ == "__main__":
    main()