"""Build the common 500/50 chunk set for the W7 embedding comparison."""

import json
from pathlib import Path

from src.rag.naive_rag import chunk_text, load_corpus


CORPUS_DIR = Path("data/corpus")
OUTPUT_FILE = Path("data/w7_common_chunks.json")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def main() -> None:
    documents = load_corpus(CORPUS_DIR)

    chunks = []

    for document in documents:
        document_chunks = chunk_text(
            document["text"],
            size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
        )

        for index, text in enumerate(document_chunks):
            chunks.append(
                {
                    "chunk_id": f"{document['doc_id']}::chunk-{index}",
                    "doc_id": document["doc_id"],
                    "text": text,
                }
            )

    output = {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunks": chunks,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")


if __name__ == "__main__":
    main()