"""Naive RAG implementation for the W6 capstone."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.pipeline.settings import Settings


EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_TOP_K = 3


def chunk_text(
    text: str,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping character-based chunks."""

    if size <= 0:
        raise ValueError("size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    text = text.strip()

    if not text:
        return []

    chunks: list[str] = []
    start = 0
    step = size - overlap

    while start < len(text):
        chunk = text[start : start + size].strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


def load_corpus(corpus_dir: Path) -> list[dict[str, str]]:
    """Load .md and .txt files from the corpus directory."""

    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Corpus directory does not exist: {corpus_dir}"
        )

    documents: list[dict[str, str]] = []

    for path in sorted(corpus_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue

        text = path.read_text(encoding="utf-8")

        documents.append(
            {
                "doc_id": path.stem,
                "text": text,
            }
        )

    if not documents:
        raise ValueError(f"No .md or .txt documents found in {corpus_dir}")

    return documents


def build_index(
    corpus_dir: Path,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build an in-memory embedding index from the corpus."""

    settings = settings or Settings()

    documents = load_corpus(corpus_dir)

    chunks: list[dict[str, Any]] = []

    for document in documents:
        document_chunks = chunk_text(
            document["text"],
            size=size,
            overlap=overlap,
        )

        for index, chunk in enumerate(document_chunks):
            chunks.append(
                {
                    "chunk_id": f"{document['doc_id']}::chunk-{index}",
                    "doc_id": document["doc_id"],
                    "text": chunk,
                }
            )

    client = OpenAI(api_key=settings.openai_api_key)

    embeddings: list[list[float]] = []

    batch_size = 100

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[item["text"] for item in batch],
        )

        embeddings.extend(item.embedding for item in response.data)

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    return {
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": size,
        "chunk_overlap": overlap,
        "chunks": chunks,
    }


def save_index(index: dict[str, Any], output_path: Path) -> None:
    """Save an embedding index as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(index),
        encoding="utf-8",
    )


def load_index(index_path: Path) -> dict[str, Any]:
    """Load a previously created embedding index."""

    if not index_path.exists():
        raise FileNotFoundError(
            f"Embedding index does not exist: {index_path}"
        )

    return json.loads(index_path.read_text(encoding="utf-8"))


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    """Calculate cosine similarity between two vectors."""

    dot = sum(a * b for a, b in zip(vector_a, vector_b))

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def retrieve(
    question: str,
    index: dict[str, Any],
    settings: Settings | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Retrieve the top-K most similar chunks."""

    settings = settings or Settings()

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[question],
    )

    question_embedding = response.data[0].embedding

    scored: list[dict[str, Any]] = []

    for chunk in index.get("chunks", []):
        score = cosine_similarity(
            question_embedding,
            chunk["embedding"],
        )

        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
                "score": score,
            }
        )

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored[:top_k]


def ask_rag(
    question: str,
    index: dict[str, Any],
    settings: Settings | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Retrieve context and generate an answer."""

    settings = settings or Settings()

    retrieved = retrieve(
        question,
        index,
        settings,
        top_k=top_k,
    )

    context_parts = []

    for item in retrieved:
        context_parts.append(
            f"[Source: {item['chunk_id']}]\n{item['text']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""Answer the question using only the provided context.

If the context does not contain enough information to answer the question,
say that the information is not available in the provided project documents.

Context:
{context}

Question:
{question}
"""

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a project management knowledge assistant. "
                    "Use the supplied project context and do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    usage = response.usage

    return {
        "answer": response.choices[0].message.content or "",
        "sources": [item["chunk_id"] for item in retrieved],
        "retrieved": retrieved,
        "tokens_in": usage.prompt_tokens if usage else 0,
        "tokens_out": usage.completion_tokens if usage else 0,
    }
