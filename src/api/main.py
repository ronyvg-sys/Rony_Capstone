"""W6 Capstone API with naive RAG."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.pipeline.cost import compute_cost_usd
from src.pipeline.models import Answer, Question
from src.pipeline.pipeline import stream_answer
from src.pipeline.settings import Settings
from src.pipeline.store import connect, save_answer
from src.rag.naive_rag import ask_rag, load_index

logger = logging.getLogger(__name__)

app = FastAPI(title="Capstone API — W6 RAG")

_settings = Settings()
_db_path = Path(_settings.results_db)

_index_path = Path("data/embeddings_medium.json")
_index = load_index(_index_path)


@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok"}


@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    """Answer a question using retrieved project-document context."""

    result = ask_rag(
        q.question,
        _index,
        _settings,
        top_k=3,
    )

    cost = compute_cost_usd(
        _settings.model,
        result["tokens_in"],
        result["tokens_out"],
    )

    answer = Answer(
        content=result["answer"],
        confidence=1.0,
        sources=result["sources"],
        cost_usd=cost,
        retries=0,
        schema_version="v1",
    )

    with connect(_db_path) as conn:
        save_answer(
            conn,
            question=q.question,
            content=answer.content,
            retries=answer.retries,
            cost_usd=answer.cost_usd,
            model=_settings.model,
            confidence=answer.confidence,
            sources=answer.sources,
            schema_version=answer.schema_version,
        )

    return answer


@app.post("/ask")
async def ask(q: Question) -> StreamingResponse:
    """Streaming endpoint preserved from W4."""

    async def _gen():
        async for chunk in stream_answer(q.question, _settings):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/plain",
    )
