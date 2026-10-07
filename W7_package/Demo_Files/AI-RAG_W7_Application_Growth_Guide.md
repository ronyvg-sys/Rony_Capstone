# AI-RAG · Week 7 · Application Growth Guide

> **Take-home · self-paced · ~2 hours**
>
> Track A (the two notebooks you ran in class) taught you Qdrant on 10 animals.
> This document walks you through migrating your capstone's real corpus from
> W6's JSON cache to a Qdrant collection.
>
> The code changes are small — most of the work is putting familiar pieces in
> new places.

---

## What's changing this week

### Before W7
Your capstone's `naive_rag.py` uses:
- `data/embeddings.json` — JSON file with cached embeddings
- `numpy.dot` — linear scan over all vectors on every query
- Everything in-memory, rebuilt at server startup

### After W7
Your capstone's new `qdrant_rag.py` uses:
- **Qdrant collection** — vectors persisted on Qdrant's side
- **Qdrant's search** — HNSW-indexed, fast at any scale
- **Metadata payload** — source, chunk_id, category (setup for W8's filtering)

### Size of the change
- **2 new modules** (`qdrant_store.py`, `qdrant_rag.py`)
- **1 new script** (`migrate_to_qdrant.py`)
- **~5 lines modified** in `src/api/main.py`
- **~140 lines of new code** total

The `naive_rag.py` from W6 stays as-is (reference). Your capstone now has
BOTH — `qdrant_rag.py` is the default; `naive_rag.py` is the "how we used to
do it" module for teaching future cohorts.

---

## Prerequisites

Before starting:
- [ ] W6 complete: `naive_rag.py` working, `data/embeddings.json` exists, KPI snapshot 1 committed
- [ ] Both W7 notebooks (Day 1 and Day 2) run successfully — you've confirmed Qdrant Cloud works
- [ ] `QDRANT_URL` + `QDRANT_API_KEY` set in your `.env`
- [ ] `qdrant-client` installed (`pip install qdrant-client`)

Estimated cost: **negligible** — you already have embeddings in `data/embeddings.json` from W6. This week just moves them, no new embedding API calls.

---

## What you'll add

### 1. `src/rag/qdrant_store.py` — Qdrant wrapper

The store handles Qdrant client setup + collection management. About 60 lines.

```python
"""Qdrant vector store for the capstone.

Replaces W6's naive_rag.py in-memory list + JSON cache with a real
vector database. Same public interface — different engine underneath.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, HnswConfigDiff,
)

COLLECTION_NAME = "capstone_chunks"
EMBEDDING_DIM = 1536  # text-embedding-3-small


@dataclass
class QdrantStore:
    """Wraps a Qdrant client + a collection name.

    Convention: one QdrantStore instance per running app.
    Instantiate via load_store() below.
    """
    client: QdrantClient
    collection: str


def _get_client() -> QdrantClient:
    """Build a QdrantClient using QDRANT_URL + QDRANT_API_KEY env vars.

    Resolution order (matches the W7 lesson plan):
      1. QDRANT_URL + QDRANT_API_KEY → Qdrant Cloud
      2. QDRANT_URL only → local Docker
      3. Default → http://localhost:6333
    """
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    api_key = os.environ.get("QDRANT_API_KEY") or None
    if api_key:
        return QdrantClient(url=url, api_key=api_key)
    return QdrantClient(url=url)


def load_store() -> QdrantStore:
    """Return a QdrantStore pointing at the capstone_chunks collection."""
    return QdrantStore(client=_get_client(), collection=COLLECTION_NAME)


def ensure_collection(store: QdrantStore) -> None:
    """Create the capstone_chunks collection if it doesn't exist.

    Idempotent — safe to call on every app start.
    """
    existing = [c.name for c in store.client.get_collections().collections]
    if store.collection in existing:
        return
    store.client.create_collection(
        collection_name=store.collection,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def upsert_chunks(store: QdrantStore, chunks: list[dict], vectors: list[list[float]]) -> None:
    """Push (chunk, vector) pairs into the store.

    Each chunk is a dict with 'chunk_id', 'source_id', and 'text' keys
    (matches the shape produced by W6's naive_rag.load_corpus).
    """
    points = [
        PointStruct(
            id=idx,
            vector=vec,
            payload={
                "chunk_id":  chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "text":      chunk["text"],
            },
        )
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    store.client.upsert(collection_name=store.collection, points=points)


def collection_size(store: QdrantStore) -> int:
    """Return the number of points in the collection. Used for smoke tests."""
    info = store.client.get_collection(store.collection)
    return info.points_count
```

**How to verify:**
```bash
python -c "
from src.rag.qdrant_store import load_store, ensure_collection, collection_size
store = load_store()
ensure_collection(store)
print(f'Collection ready. Points: {collection_size(store)}')
"
```
Expected: `Collection ready. Points: 0` (empty at first).

### 2. `src/rag/qdrant_rag.py` — the new default pipeline

Parallel to W6's `naive_rag.py`. Same public shape (`ask_rag`), Qdrant underneath. About 80 lines.

```python
"""Qdrant-backed RAG for the capstone — W7 upgrade of W6's naive_rag.

Same public interface as W6's ask_rag: (question, store, k) → dict.
Storage layer swapped from JSON+numpy to Qdrant.
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from src.pipeline.settings import Settings
from src.rag.qdrant_store import QdrantStore, load_store

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"

_client = None
def _openai() -> OpenAI:
    """Lazy-init the OpenAI client (unit tests can import without a key)."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def embed_query(text: str) -> list[float]:
    """Single-string embedding. Used at query time."""
    resp = _openai().embeddings.create(model=EMBED_MODEL, input=[text])
    return resp.data[0].embedding


def retrieve(store: QdrantStore, query: str, k: int = 3) -> list[dict[str, Any]]:
    """Embed the query, ask Qdrant for top-K, return list of hits."""
    q_vec = embed_query(query)
    results = store.client.query_points(
        collection_name=store.collection,
        query=q_vec,
        limit=k,
    ).points
    return [
        {
            "chunk_id":  h.payload["chunk_id"],
            "source_id": h.payload["source_id"],
            "text":      h.payload["text"],
            "score":     h.score,
        }
        for h in results
    ]


SYSTEM = (
    "You are a helpful assistant. Answer the user's question using ONLY the "
    "provided context. If the context does not contain the answer, say so "
    "plainly. Cite the source_id in square brackets after any fact you use."
)


def ask_rag(question: str, store: QdrantStore | None = None,
            settings: Settings | None = None, k: int = 3) -> dict[str, Any]:
    """Full pipeline: embed → retrieve → prompt → generate. Returns dict."""
    if store is None:
        store = load_store()
    
    retrieved = retrieve(store, question, k=k)
    
    context = "\n\n".join(
        f"[{hit['chunk_id']}] (source: {hit['source_id']})\n{hit['text']}"
        for hit in retrieved
    )
    
    resp = _openai().chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content":
                f"Context:\n{context}\n\n---\n\nQuestion: {question}"},
        ],
    )
    
    return {
        "answer":     resp.choices[0].message.content,
        "sources":    [h["source_id"] for h in retrieved],
        "chunk_ids":  [h["chunk_id"] for h in retrieved],
        "tokens_in":  resp.usage.prompt_tokens,
        "tokens_out": resp.usage.completion_tokens,
    }
```

**How to verify:**
```bash
python -c "
from src.rag.qdrant_rag import ask_rag
result = ask_rag('what is the leave policy?')
print(result['answer'][:200])
"
```
Should return an answer citing your actual policy corpus (once the migration is done in step 3).

### 3. `scripts/migrate_to_qdrant.py` — one-off migration

Loads embeddings from W6's JSON cache and pushes them into Qdrant.

```python
"""Migrate embeddings from W6's data/embeddings.json into Qdrant.

Run once after adding qdrant_store.py. Idempotent — safe to re-run,
just overwrites.
"""
import json
from pathlib import Path

from src.rag.qdrant_store import (
    load_store, ensure_collection, upsert_chunks, collection_size,
)

INDEX_PATH = Path("data/embeddings.json")

print(f"Loading embeddings from {INDEX_PATH}...")
with INDEX_PATH.open() as f:
    index = json.load(f)  # list of {chunk_id, source_id, text, vector}
print(f"  {len(index)} chunks loaded from JSON")

# Separate chunks from vectors
chunks = [{k: c[k] for k in ("chunk_id", "source_id", "text")} for c in index]
vectors = [c["vector"] for c in index]

# Push to Qdrant
print("Connecting to Qdrant...")
store = load_store()
ensure_collection(store)

print(f"Upserting {len(chunks)} points into '{store.collection}'...")
upsert_chunks(store, chunks, vectors)

# Confirm
n = collection_size(store)
print(f"Done. Collection now has {n} points.")
```

**Run it:**
```bash
python scripts/migrate_to_qdrant.py
```

Expected output:
```
Loading embeddings from data/embeddings.json...
  156 chunks loaded from JSON
Connecting to Qdrant...
Upserting 156 points into 'capstone_chunks'...
Done. Collection now has 156 points.
```

Time: ~10 seconds for a typical capstone corpus. Cost: zero (no new embedding calls).

### 4. `docs/kpi/wk7-snapshot.md` — new KPI snapshot

You'll fill this in after running the golden set (Section below).

```markdown
# wk7-snapshot.md — Qdrant migration baseline

**Date:** YYYY-MM-DD
**Vector store:** Qdrant Cloud
**Collection:** capstone_chunks (N points, 1536 dim, cosine)
**Embedding model:** text-embedding-3-small

## Headline numbers

| Metric | W6 (JSON) | W7 (Qdrant) | Delta |
|---|---|---|---|
| Cost per query | $0.000XXX | $0.000XXX | ≈ 0 (no new embeds) |
| Latency p50 (ms) | XXX | XXX | may decrease slightly |
| Retrieval hit rate | XX% | XX% | should NOT change |
| Grounded response rate | XX% | XX% | should NOT change |

## Operational deltas (the real W7 win)

| Property | W6 | W7 |
|---|---|---|
| Persistence | file-based JSON | Qdrant-managed |
| Restart cost | O(N) load into memory | O(1) — Qdrant already loaded |
| Filtering | none | ready for W8 metadata |
| Scaling ceiling | ~10K chunks (RAM) | millions (HNSW) |

## Method
- Same 20 golden-set questions from W5
- W6 numbers from wk6-snapshot.md
- W7 numbers from a fresh run against Qdrant collection

## Embedding-model comparison (from Lab Step 2)
- text-embedding-3-small: XX/20 correct retrieval, $X.XX total
- text-embedding-3-large: XX/20 correct retrieval, $X.XX total
- **Choice for ADR:** text-embedding-3-small (default) OR text-embedding-3-large
- **Reason:** [why you picked what you picked]
```

---

## What you'll modify

### `src/api/main.py` — swap one import + one call

Currently your `/ask_batched` calls `naive_rag.ask_rag(...)`. Swap to `qdrant_rag`.

Find (from W6):
```python
from src.rag import naive_rag
# ...
result = naive_rag.ask_rag(q.question, ...)
```

Change to:
```python
from src.rag import qdrant_rag
# ...
result = qdrant_rag.ask_rag(q.question)
```

About 5 lines changed. The parallel-module design lets you swap back to
`naive_rag` if Qdrant ever goes down for maintenance.

### `docs/adr/0001-capstone-framing.md` — add a W7 section

Append at the end:

```markdown
## W7 — Qdrant-backed vector store

**Decision:** Capstone now uses Qdrant Cloud (free tier) as the vector store.
`naive_rag.py` retained as reference.

**Vector stack:**
- Embedding model: text-embedding-3-small (1536 dims, $0.02 per 1M tokens)
- Vector store: Qdrant Cloud
- Distance metric: cosine (programme default; see W7 Track A Day 2 for why)
- Index: HNSW with defaults (m=16, ef_construct=100)

**Rejected alternatives:**
- text-embedding-3-large — 6.5× cost, insufficient quality gain on our corpus (see Lab Step 2)
- FAISS — no service layer; we need persistence + REST
- Chroma — smaller ecosystem, less battle-tested
- pgvector — no existing Postgres; not worth adding

**Operational KPIs** (see docs/kpi/wk7-snapshot.md):
- Persistence: Qdrant-managed (was: JSON file on disk)
- Restart cost: O(1) — no re-load of vectors into memory
- Ready for W8 metadata filtering
```

---

## Testing checklist

Before you consider W7 done:

- [ ] `qdrant_store.py`, `qdrant_rag.py`, `migrate_to_qdrant.py` all exist
- [ ] `python scripts/migrate_to_qdrant.py` completes; collection has expected point count
- [ ] Sanity query works: `curl POST /ask_batched -d '{"question": "..."}'`
- [ ] Response includes `sources` field with real source IDs
- [ ] Retrieval hit rate on golden set is **unchanged** vs W6 (this is the important check — if it DROPPED, you have a bug)

---

## Run the golden set

Use your existing eval runner (from W5):

```bash
python scripts/run_eval.py --dataset data/golden_set.jsonl --output results.db
```

Save results. Fill in the W7 KPI snapshot with actual numbers.

---

## Embedding-model comparison (Lab Step 2 from lesson plan)

Beyond the migration, W7 has a second-day lab task: compare `3-small` vs `3-large`.

Approach:
1. Run all 20 golden questions with `3-small` (current); note retrieval hit rate
2. Rebuild your Qdrant collection with `3-large` embeddings; run same 20 questions
3. Compare hit rate. Note the delta in your KPI snapshot.
4. Update ADR with your final choice + reasoning.

Expected on a typical corpus: `3-large` gives marginally better hit rate (2-5 percentage points) at 6.5× the embedding cost. Most learners will stay on `3-small`. Log your choice.

**Cost warning:** re-embedding your whole corpus with `3-large` costs ~10× your W6 initial embed. Budget maybe $0.10-0.20 depending on corpus size.

---

## Common issues + fixes

**`qdrant_client.http.exceptions.UnexpectedResponse: Unexpected Response: 401`**
Your `QDRANT_API_KEY` is missing or wrong. Copy exactly from Qdrant Cloud dashboard.

**`ValueError: dimension mismatch: expected 1536, got X`**
Your Qdrant collection was created with the wrong dim. Delete and recreate:
```python
from src.rag.qdrant_store import load_store
store = load_store()
store.client.delete_collection(store.collection)
```
Then re-run the migration script.

**Retrieval hit rate DROPPED between W6 and W7**
This shouldn't happen — you swapped storage, not algorithm. Two likely causes:
1. Your migration script lost or corrupted embeddings — check that vector count matches `len(index)` before and after
2. You accidentally re-embedded with a different model — verify with `store.client.get_collection('capstone_chunks').config.params.vectors.size`

**Server startup is slow now**
`ensure_collection()` runs on every startup. That's a network call to Qdrant. Fine at 1-2 seconds; if it's much longer, check your Qdrant Cloud region matches your app region.

---

## What you should have when done

New files:
- `src/rag/qdrant_store.py`
- `src/rag/qdrant_rag.py`
- `scripts/migrate_to_qdrant.py`
- `docs/kpi/wk7-snapshot.md`

Modified files:
- `src/api/main.py` (~5 lines)
- `docs/adr/0001-capstone-framing.md` (W7 section added)

Preserved (do not delete):
- `data/embeddings.json` — keep as backup; also used by W10's caching work
- `src/rag/naive_rag.py` — reference for future cohorts

Total time: ~2 hours if you understood Track A. Longer if you hit Qdrant Cloud
setup issues — those add ~30 min the first time.

---

## What's coming in W8

W8 adds **document ingestion + PII awareness** to the pipeline. You'll:
- Add a proper ingestion pipeline (currently: manual placement in `data/corpus/`)
- Add PII scrubbing (email addresses, employee IDs, phone numbers)
- Add metadata to your Qdrant payload (source type, ingestion date, redaction flag)
- Start filtering retrieval by metadata (Qdrant's real superpower)

The `qdrant_store.py` module you built this week is what W8 extends. Small
additions, not rewrites.

---

*W7 Application Growth Guide. Track B of the two-track W7 pattern.*
