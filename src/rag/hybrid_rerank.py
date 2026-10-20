
"""Week 9 hybrid retrieval and cross-encoder reranking."""

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_INDEX = Path("data/w7_embeddings_small.json")
DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RRF_K = 60


def tokenize(text: str) -> list[str]:
    """Simple lowercase tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


def load_index(index_path: str | Path = DEFAULT_INDEX) -> dict:
    """Load the existing Week 7 embedding index."""
    path = Path(index_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    if not data.get("chunks"):
        raise ValueError(f"No chunks found in index: {path}")

    return data


class HybridRetriever:
    """Combine dense retrieval, BM25, RRF, and cross-encoder reranking."""

    def __init__(
        self,
        index: dict,
        cross_encoder_name: str = DEFAULT_CROSS_ENCODER,
    ) -> None:
        self.chunks = index["chunks"]
        self.chunk_by_id = {
            chunk["chunk_id"]: chunk for chunk in self.chunks
        }

        self.embeddings = np.asarray(
            [chunk["embedding"] for chunk in self.chunks],
            dtype=np.float32,
        )

        if self.embeddings.ndim != 2:
            raise ValueError("Chunk embeddings must form a 2D matrix.")

        self.bm25 = BM25Okapi(
            [tokenize(chunk["text"]) for chunk in self.chunks]
        )

        self.cross_encoder = CrossEncoder(cross_encoder_name)

    def dense_search(self, query_vector: list[float], top_k: int = 10):
        """Return the top chunks by cosine similarity."""
        vector = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)

        if vector.shape[1] != self.embeddings.shape[1]:
            raise ValueError(
                f"Query dimension {vector.shape[1]} does not match "
                f"index dimension {self.embeddings.shape[1]}."
            )

        scores = cosine_similarity(vector, self.embeddings)[0]
        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                **self.chunks[int(i)],
                "dense_score": float(scores[i]),
                "dense_rank": rank,
            }
            for rank, i in enumerate(ranked_indices, start=1)
        ]

    def keyword_search(self, query: str, top_k: int = 10):
        """Return the top chunks by BM25 score."""
        scores = self.bm25.get_scores(tokenize(query))
        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                **self.chunks[int(i)],
                "bm25_score": float(scores[i]),
                "bm25_rank": rank,
            }
            for rank, i in enumerate(ranked_indices, start=1)
        ]

    def fuse(self, dense_results: list[dict], bm25_results: list[dict]):
        """Fuse two rankings using Reciprocal Rank Fusion."""
        fused_scores: dict[str, float] = {}

        for results, rank_key in (
            (dense_results, "dense_rank"),
            (bm25_results, "bm25_rank"),
        ):
            for item in results:
                chunk_id = item["chunk_id"]
                rank = item[rank_key]
                fused_scores[chunk_id] = (
                    fused_scores.get(chunk_id, 0.0)
                    + 1.0 / (RRF_K + rank)
                )

        ranked_ids = sorted(
            fused_scores,
            key=fused_scores.get,
            reverse=True,
        )

        return [
            {
                **self.chunk_by_id[chunk_id],
                "rrf_score": fused_scores[chunk_id],
            }
            for chunk_id in ranked_ids
        ]

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5):
        """Rerank candidate chunks with a cross-encoder."""
        if not candidates:
            return []

        pairs = [
            (query, candidate["text"])
            for candidate in candidates
        ]
        scores = self.cross_encoder.predict(pairs)

        reranked = []
        for candidate, score in zip(candidates, scores):
            reranked.append(
                {
                    **candidate,
                    "rerank_score": float(score),
                }
            )

        reranked.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return reranked[:top_k]

    def search(
        self,
        query: str,
        query_vector: list[float],
        candidate_k: int = 10,
        top_k: int = 5,
    ) -> list[dict]:
        """Run dense + BM25 + RRF + cross-encoder reranking."""
        dense_results = self.dense_search(query_vector, top_k=candidate_k)
        bm25_results = self.keyword_search(query, top_k=candidate_k)
        fused_results = self.fuse(dense_results, bm25_results)

        return self.rerank(
            query,
            fused_results[:candidate_k],
            top_k=top_k,
        )
