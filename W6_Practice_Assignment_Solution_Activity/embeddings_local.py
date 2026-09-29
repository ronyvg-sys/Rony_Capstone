"""embeddings_local.py — W6 Activity B (stretch).

Local embeddings via sentence-transformers. 384-dim vectors, free per
query, no network round-trip. Slightly worse hit rate than OpenAI's
text-embedding-3-small on most corpora.

Why MiniLM-L6-v2:
- ~80MB, small enough to download quickly
- 384 dimensions (vs OpenAI-small's 1536)
- CPU-friendly — no GPU needed
- Wide adoption — well-documented behaviour

Usage:
    from src.rag.embeddings_local import embed
    vec = embed("What is the leave policy?")
    # vec is a list of 384 floats, normalised
"""
from __future__ import annotations


# Lazy-loaded module-level cache — first call downloads (~80MB on first
# run); subsequent calls reuse the loaded model.
_model = None


def _get_model():
    """Load and cache the sentence-transformers model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    """Embed a single string. Returns 384 floats, L2-normalised.

    Use `normalize_embeddings=True` so cosine similarity reduces to
    a dot product downstream.
    """
    vec = _get_model().encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings in one batch call. Faster than calling
    embed() in a loop because the model batches internally.
    """
    vecs = _get_model().encode(texts, normalize_embeddings=True,
                                 show_progress_bar=False)
    return vecs.tolist()
