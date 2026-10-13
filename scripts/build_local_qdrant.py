"""Build the W7 Local MiniLM collection in Qdrant Cloud."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


INPUT_FILE = Path("data/w7_embeddings_local.json")
COLLECTION_NAME = "capstone_chunks_local"


def main() -> None:
    load_dotenv()

    qdrant = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    chunks = data["chunks"]

    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE,
        ),
    )

    points = [
        PointStruct(
            id=index,
            vector=chunk["embedding"],
            payload={
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
            },
        )
        for index, chunk in enumerate(chunks)
    ]

    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    info = qdrant.get_collection(COLLECTION_NAME)

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Vector size: {info.config.params.vectors.size}")
    print(f"Distance: {info.config.params.vectors.distance}")
    print(f"Points: {info.points_count}")


if __name__ == "__main__":
    main()