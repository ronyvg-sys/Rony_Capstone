# AI-RAG · Week 10 · Application Growth Guide

> **Take-home · self-paced · Core ~2.5 hours; Stretch optional ~45 min**
>
> **Second Core+Stretch week** — same rules as W9. Core mandatory; Stretch
> only if Core is solid.
>
> Track A (the two W10 notebooks) taught semantic cache + tombstones +
> IsEmpty on the Acme corpus. This guide walks through applying the same
> patterns to your capstone corpus and measuring the cost + latency deltas.

---

## Core + Stretch framing (continuing from W9)

**🟢 Core (mandatory)** = every learner completes. Steps 1-4 below.

**🟡 Stretch (optional)** = depth for learners who finish Core with time and
energy. Step 5. Do NOT attempt Stretch before Core is solid.

If your Core cost/latency delta didn't move — that's the debugging
priority, not Stretch. On W10 the most common Core failure mode is a
broken cache invalidation (Step 2 done wrong) or an IsNull-vs-IsEmpty
mistake in your filter.

---

## What's changing this week

### Before W10 (end of W9)
- `src/rag/retrieval.py` — hybrid retrieve + rerank + `retrieve()` full stack
- `src/rag/qdrant_rag.py` — uses `retrieval.retrieve()`; no cache
- `wk9-snapshot.md` — precision baseline

### After W10 Core
- `src/rag/cache.py` — new module: semantic cache (SQLite backend)
- `src/rag/qdrant_rag.py` — modified: cache-first, RAG on miss
- `src/rag/pipeline.py` — modified: `tombstone_source()` + `ingest_or_update_source()` using `IsEmptyCondition`
- `src/rag/retrieval.py` — modified: `_live_filter()` applied by default
- `scripts/update_document.py` — new: end-to-end update runbook
- `tests/test_cache.py` + `tests/test_tombstones.py` — new
- `docs/kpi/wk10-snapshot.md` — cost + latency deltas
- `docs/adr/0001-capstone-framing.md` — extended with W10 decisions
- `docs/runbooks/document_update.md` — new: 5-step update runbook

### After W10 Stretch (optional)
- Either `src/rag/compression.py` (LLMLingua) OR `scripts/cold_start_prime.py`
- `docs/wk10-stretch-notes.md` with findings

---

## Prerequisites

- [ ] W9 complete: `retrieval.py` with hybrid+rerank; `wk9-snapshot.md` committed
- [ ] Both W10 notebooks (Day 1 + Day 2) run cleanly
- [ ] `qdrant-client >= 1.7` (for `IsEmptyCondition`)
- [ ] Existing `capstone_chunks_v2` collection in Qdrant

Estimated total cost: **<$0.05** — golden set is 20 questions × cold + warm passes; embeddings cheap; LLM calls modest.

---

# 🟢 CORE (mandatory)

## Core Step 1 (60 min) — Add `src/rag/cache.py` + wire into `qdrant_rag.py`

**Create `src/rag/cache.py`:**

```python
"""SQLite-backed semantic cache for the capstone.

Layer 1 of the 3-layer caching stack (Layer 2 = OpenAI prompt cache
auto-fires ≥1024 tokens; Layer 3 = embedding cache from W7).
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
import time
from pathlib import Path

CACHE_DB_DEFAULT = "results.db"   # reuse the file W2 created
DEFAULT_THRESHOLD = 0.95           # deck default; do not lower without measuring


def _connect(db_path: str = CACHE_DB_DEFAULT) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_cache (
            id             TEXT PRIMARY KEY,
            question       TEXT NOT NULL,
            embedding_blob BLOB NOT NULL,
            answer         TEXT NOT NULL,
            hit_count      INTEGER NOT NULL DEFAULT 0,
            created_ts     REAL NOT NULL,
            last_hit_ts    REAL
        )
    """)
    conn.commit()
    return conn


def _key(question: str) -> str:
    return hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na  = math.sqrt(sum(x*x for x in a))
    nb  = math.sqrt(sum(y*y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def lookup(question_embedding: list[float],
           threshold: float = DEFAULT_THRESHOLD,
           db_path: str = CACHE_DB_DEFAULT) -> dict | None:
    """Return {answer, similarity, matched_question} on hit; None on miss."""
    conn = _connect(db_path)
    try:
        best_score, best = -1.0, None
        for row in conn.execute(
            "SELECT id, question, embedding_blob, answer FROM query_cache"
        ):
            row_id, row_q, blob, ans = row
            n = len(blob) // 4
            emb = list(struct.unpack(f"{n}f", blob))
            s = _cosine(question_embedding, emb)
            if s > best_score:
                best_score, best = s, (row_id, row_q, ans)
        if best is None or best_score < threshold:
            return None
        row_id, matched_q, cached_ans = best
        conn.execute(
            "UPDATE query_cache SET hit_count=hit_count+1, last_hit_ts=? WHERE id=?",
            (time.time(), row_id),
        )
        conn.commit()
        return {
            "answer":            cached_ans,
            "matched_question":  matched_q,
            "similarity":        best_score,
        }
    finally:
        conn.close()


def put(question: str, embedding: list[float], answer: str,
        db_path: str = CACHE_DB_DEFAULT) -> None:
    conn = _connect(db_path)
    try:
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        conn.execute("""
            INSERT OR REPLACE INTO query_cache
            (id, question, embedding_blob, answer, hit_count, created_ts, last_hit_ts)
            VALUES (?, ?, ?, ?, 0, ?, NULL)
        """, (_key(question), question, blob, answer, time.time()))
        conn.commit()
    finally:
        conn.close()


def clear(db_path: str = CACHE_DB_DEFAULT) -> int:
    """Wipe all cache entries. Call this after any document update."""
    conn = _connect(db_path)
    try:
        cur = conn.execute("DELETE FROM query_cache")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def stats(db_path: str = CACHE_DB_DEFAULT) -> dict:
    """For dashboards: total entries, total hits, average similarity of hits."""
    conn = _connect(db_path)
    try:
        row = conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(hit_count), 0)
            FROM query_cache
        """).fetchone()
        return {"n_entries": row[0], "total_hits": row[1]}
    finally:
        conn.close()
```

**Wire into `qdrant_rag.py`** — cache-first pattern:

```python
# In src/rag/qdrant_rag.py — REPLACE ask_rag()

from openai import OpenAI
from src.rag.retrieval import retrieve      # from W9
from src.rag import cache                    # NEW W10

_openai = None
def _get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI()
    return _openai


def ask_rag(question: str, k: int = 3,
            cache_threshold: float = 0.95) -> dict:
    """Full RAG with 3-layer caching.

    Layer 1 (semantic cache) checked first — return early on hit.
    Layer 2 (OpenAI prompt cache) fires automatically on the LLM call.
    Layer 3 (embedding cache) transparent from W7.
    """
    client = _get_openai()

    # ── Layer 1: semantic cache ──
    q_vec = client.embeddings.create(
        model="text-embedding-3-small", input=[question]
    ).data[0].embedding

    hit = cache.lookup(q_vec, threshold=cache_threshold)
    if hit:
        return {
            "answer":     hit["answer"],
            "cache_hit":  True,
            "similarity": hit["similarity"],
            "matched":    hit["matched_question"],
        }

    # ── Miss: full RAG pipeline ──
    retrieved = retrieve(question, k=k)  # from W9: hybrid + rerank
    prompt = _build_prompt(question, retrieved)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = resp.choices[0].message.content

    # Store in cache for next time
    cache.put(question, q_vec, answer)

    return {
        "answer":     answer,
        "cache_hit":  False,
        "n_input_tokens":         resp.usage.prompt_tokens,
        "n_output_tokens":        resp.usage.completion_tokens,
        "n_cached_input_tokens":  getattr(resp.usage, 'prompt_tokens_details', None)
                                   and resp.usage.prompt_tokens_details.cached_tokens or 0,
        "retrieved":              retrieved,
    }


def _build_prompt(question: str, retrieved: list[dict]) -> str:
    """Stable prefix FIRST (cacheable), question + context LAST."""
    system = ("You are a helpful assistant. Answer using ONLY the context. "
              "If the context does not contain the answer, say 'I don't know'.")
    ctx = "\n\n".join(f"[{i+1}] {h['doc'].get('text', '')}"
                       for i, h in enumerate(retrieved))
    return f"{system}\n\n=== Context ===\n{ctx}\n\n=== Question ===\n{question}\n\n=== Answer ==="
```

**Verify** with a quick sanity script:
```python
from src.rag.qdrant_rag import ask_rag
from src.rag import cache
cache.clear()  # start cold
r1 = ask_rag("what is the leave policy?")
print(f"Cold: hit={r1['cache_hit']}, answer={r1['answer'][:80]}")
r2 = ask_rag("what is the leave policy?")
print(f"Warm: hit={r2['cache_hit']}, similarity={r2.get('similarity', 'n/a')}")
```

Should print `hit=False` then `hit=True`. If both show `hit=False`, cache_put/lookup isn't reaching the same DB — check `db_path`.

## Core Step 2 (45 min) — Add tombstone update flow to `pipeline.py`

**Add to `src/rag/pipeline.py`** (extending W8's `pipeline.py`):

```python
# Add these imports at the top of pipeline.py
from qdrant_client.models import (
    FieldCondition, Filter, IsEmptyCondition,   # NOT IsNullCondition
    MatchValue, PayloadField, PointStruct,
)
from src.rag import cache


def tombstone_source(store, source: str) -> int:
    """Mark all live chunks whose payload.source == source as tombstoned.

    Uses IsEmptyCondition — matches whether deleted_at is absent, null, or
    empty. IsNullCondition would only match explicit-null values and misses
    absent fields (silent bug). See W10 Day 2 Cell 4 for the diagnosis.

    Returns count of chunks tombstoned.
    """
    flt = Filter(must=[
        FieldCondition(key="source", match=MatchValue(value=source)),
        IsEmptyCondition(is_empty=PayloadField(key="deleted_at")),
    ])
    pre_count = store.client.count(
        collection_name=store.collection,
        count_filter=flt, exact=True,
    ).count
    store.client.set_payload(
        collection_name=store.collection,
        payload={"deleted_at": time.time()},
        points=flt,
        wait=True,
    )
    return pre_count


def ingest_or_update_source(store, source: str, body: str,
                             doc_type: str = "general",
                             clear_cache_after: bool = True) -> dict:
    """Re-ingest a document. Tombstone old chunks, insert new ones, clear cache.

    Returns {tombstoned, ingested, cache_cleared}.

    The clear_cache_after flag defaults True — critical to prevent stale
    answers from the semantic cache after a doc update. Turn off only if
    you're doing bulk updates and will call cache.clear() once at the end.
    """
    n_tombstoned = tombstone_source(store, source)

    chunks = chunk_text(body, source=source)
    vectors = embed_texts([c["text"] for c in chunks])

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                **chunk,
                "source":      source,
                "doc_type":    doc_type,
                "kb_version":  KB_VERSION,
                "ingested_at": time.time(),
                # NOTE: deliberately no deleted_at field. IsEmptyCondition
                # will match this — no explicit None needed.
            },
        )
        for chunk, vec in zip(chunks, vectors)
    ]
    store.client.upsert(collection_name=store.collection, points=points, wait=True)

    n_cleared = 0
    if clear_cache_after:
        n_cleared = cache.clear()

    return {
        "tombstoned":     n_tombstoned,
        "ingested":       len(points),
        "cache_cleared":  n_cleared,
    }
```

**Update `src/rag/retrieval.py`** — apply live filter by default:

```python
# In src/rag/retrieval.py — MODIFY dense_search()

from qdrant_client.models import Filter, IsEmptyCondition, PayloadField


def _live_filter():
    """Filter matching only not-yet-tombstoned chunks."""
    return Filter(must=[IsEmptyCondition(is_empty=PayloadField(key="deleted_at"))])


def dense_search(query: str, k: int = 10,
                 include_deleted: bool = False) -> list[dict]:
    """Dense retrieval with tombstone filter by default.

    include_deleted=True is the audit escape hatch — use only when
    re-running historical evaluations against past KB state.
    """
    openai = _get_openai()
    client = _get_client()
    q_vec = openai.embeddings.create(
        model="text-embedding-3-small", input=[query]).data[0].embedding

    query_filter = None if include_deleted else _live_filter()
    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=q_vec, limit=k, query_filter=query_filter,
    ).points
    return [{"id": str(h.id), "score": h.score,
             "doc": {**h.payload, "point_id": h.id}} for h in hits]
```

**Create `scripts/update_document.py`** — end-to-end runbook:

```python
"""Update a single document in the capstone KB.

Usage:
    python -m scripts.update_document data/policies/leave.md
"""
import sys
from pathlib import Path

from src.rag.pipeline import ingest_or_update_source
from src.rag.qdrant_store import QdrantStore

def main(doc_path: str):
    path = Path(doc_path)
    assert path.exists(), f"Not found: {path}"
    body = path.read_text()
    source = path.name

    store = QdrantStore()
    result = ingest_or_update_source(store, source, body)

    print(f"Update complete for {source}:")
    print(f"  Tombstoned: {result['tombstoned']} old chunks")
    print(f"  Ingested:   {result['ingested']} new chunks")
    print(f"  Cache cleared: {result['cache_cleared']} entries")

if __name__ == "__main__":
    main(sys.argv[1])
```

**Verify:**
```bash
# Pick a small doc from your capstone corpus
python -m scripts.update_document data/some_doc.md
```

Should show non-zero tombstoned count on any doc that already exists. Then re-run — should show 0 tombstoned (nothing live from that source anymore, only just-inserted fresh chunks).

## Core Step 3 (45 min) — Golden set cold + warm, KPI snapshot

**Create `scripts/measure_wk10_cache.py`:**

```python
"""Measure cost + latency delta from W9 → W10 (with caching).

Runs the golden set twice:
  Pass 1 (cold): cache empty; every query pays full RAG cost
  Pass 2 (warm): cache primed; ideally every query hits
"""
import json, time
from pathlib import Path

from src.rag.qdrant_rag import ask_rag
from src.rag import cache

GOLDEN = Path("data/golden_set.jsonl")
golden = [json.loads(l) for l in GOLDEN.read_text().splitlines() if l]

# Prices per 1M tokens (Aug 2026 — verify)
PRICING = {
    "input":       0.15,
    "output":      0.60,
    "input_cached":0.075,
    "embed":       0.02,
}

def cost_of(res: dict, q_len_tokens: int) -> float:
    if res["cache_hit"]:
        # Only paid for the query embedding
        return q_len_tokens * PRICING["embed"] / 1_000_000
    fresh = res["n_input_tokens"] - res["n_cached_input_tokens"]
    return (
        res["n_cached_input_tokens"] * PRICING["input_cached"] / 1_000_000
        + fresh                      * PRICING["input"]        / 1_000_000
        + res["n_output_tokens"]     * PRICING["output"]       / 1_000_000
        + q_len_tokens               * PRICING["embed"]        / 1_000_000
    )

def run_pass(label):
    latencies, cost = [], 0.0
    n_hits, n_misses = 0, 0
    for q in golden:
        t0 = time.time()
        res = ask_rag(q["question"])
        latencies.append((time.time() - t0) * 1000)
        cost += cost_of(res, q_len_tokens=len(q["question"].split()))
        if res["cache_hit"]: n_hits += 1
        else: n_misses += 1
    latencies.sort()
    return {"label": label, "cost": cost,
            "p50_ms": latencies[len(latencies)//2],
            "p95_ms": latencies[int(len(latencies)*0.95)],
            "hits": n_hits, "misses": n_misses}

cache.clear()
cold = run_pass("cold")
warm = run_pass("warm")

print(f"══ W10 cost + latency ══\n")
print(f"  {'Pass':<8s} {'hits':>5s} {'p50':>7s} {'p95':>7s} {'total cost':>12s}")
for p in [cold, warm]:
    print(f"  {p['label']:<8s} {p['hits']:>5d} {p['p50_ms']:>6.0f}ms {p['p95_ms']:>6.0f}ms  ${p['cost']:>10.5f}")

if cold['cost']:
    saved_pct = 100 * (cold['cost'] - warm['cost']) / cold['cost']
    print(f"\n  Warm-pass cost saved: {saved_pct:.1f}%")

# Save numbers to wk10-snapshot.md (create the file per template below)
```

**Update `docs/kpi/wk10-snapshot.md`:**

```markdown
# wk10-snapshot.md — Caching + lifecycle baseline

**Date:** YYYY-MM-DD
**Stack (v10):** hybrid + rerank (W9) + semantic cache (0.95 threshold, SQLite)
**Update flow:** tombstone (IsEmpty) → insert → cache.clear()

## Headline numbers

| Metric | W9 (no cache) | W10 cold | W10 warm | Change vs W9 |
|---|---|---|---|---|
| Precision@3 | X.XX | same | same | unchanged (cache doesn't affect quality on hit — same answer returns) |
| Cost/query (avg) | $X | $X | $Y | -Z% warm |
| Latency p50 | XXX ms | XXX ms | YYY ms | -Z% warm |
| Latency p95 | XXX ms | XXX ms | YYY ms | -Z% warm |
| Grounded response rate | X.XX | same | same | unchanged |
| Cache hit rate | n/a | 0% | ~100% | (workload-dependent in prod) |
| Eval reproducibility | broken | solved | solved | tombstones added |

## Method
- Same 20 golden-set questions as W5-W9
- Pass 1 cold: `cache.clear()` first
- Pass 2 warm: rerun immediately, expect all hits
- Pricing: OpenAI Aug 2026 ($0.15/M input, $0.075/M cached, $0.60/M output, $0.02/M embed)

## Interpretation
[fill in — did warm-pass savings match the deck's 60-70% range? if lower, why?
if higher, congratulations, high query repetition in your golden set]

## Known risks
- False cache hits — none observed on golden set, but production traffic
  will have more variety. Add sample-based monitoring: pull N cache hits per
  day, replay through full RAG, compare answers.
- Cache staleness after doc update — mitigated by clear-on-update in
  ingest_or_update_source(). Verify this is called on EVERY update path.
```

## Core Step 4 (30 min) — Update ADR + write update runbook

**Extend `docs/adr/0001-capstone-framing.md`** with a W10 section:

```markdown
## W10 — Caching + KB lifecycle

**Decisions:**
- **Layer 1 (semantic cache):** SQLite backend (reuse results.db); 0.95 cosine
  threshold; scan-based lookup (fine for <1K entries; migrate to Qdrant if
  cache grows > 10K)
- **Layer 2 (OpenAI prompt cache):** implicit auto-cache on gpt-4o-mini;
  system prompt placed FIRST for prefix matching
- **Layer 3 (embedding cache):** already in place from W7
- **Tombstone semantics:** IsEmptyCondition (not IsNullCondition) — matches
  absent OR null OR empty; robust to ingestion variations
- **Update flow:** tombstone old → insert new → clear cache (in that order)
- **Audit escape hatch:** dense_search(include_deleted=True) for historical
  evaluations against past KB state

**Rejected alternatives:**
- LLMLingua prompt compression: precision risk on technical docs; deferred
  to Stretch — measure groundedness before ever shipping
- Cohere semantic cache API: paid; local SQLite covers capstone scale
- Cache-per-source invalidation: complex; blunt clear-on-update is safer
  default at our scale
- IsNullCondition for tombstone filter: silent bug when field absent
  (see W10 Day 2 Cell 4 diagnosis)

**Operational KPIs** (see docs/kpi/wk10-snapshot.md):
[fill from Step 3]

**Known gaps to revisit:**
- No cache TTL (entries live forever until doc update). Fine at current
  scale; revisit if cache DB grows past ~10K entries.
- Cache invalidation is all-or-nothing. Per-source invalidation would let
  us keep cache warm for unaffected topics. Deferred until we measure how
  often full-clear hurts hit rate in practice.
```

**Create `docs/runbooks/document_update.md`:**

```markdown
# Document Update Runbook

**When to run:** a source doc has changed and needs to be reflected in
retrieval + generation.

## Steps

1. **Pull the updated file** into `data/`
2. **Run** `python -m scripts.update_document <path/to/file>`
   - Tombstones old chunks (marks deleted_at)
   - Inserts new chunks
   - Clears semantic cache
3. **Verify** with a query that would touch the updated doc:
   ```
   python -c "from src.rag.qdrant_rag import ask_rag; \\
              print(ask_rag('<relevant question>')['answer'])"
   ```
   Should reflect the new content.
4. **Optional: bump `kb_version`** if this is a major update
   - Edit `KB_VERSION` in `src/rag/pipeline.py`
   - New chunks going forward will carry the new version
5. **Log** the update in `docs/kb-changelog.md` (date, file, tombstoned count)

## Rollback

Un-tombstone the old chunks:
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue
store.client.delete_payload(
    collection_name=store.collection,
    keys=["deleted_at"],
    points=Filter(must=[FieldCondition(key="source", match=MatchValue(value="<source>"))]),
)
```
And delete the new chunks by their point_ids. Then re-clear the cache.
```

---

# 🟡 STRETCH (optional)

Pick ONE. Only start after Core is solid.

## Stretch A (45 min) — LLMLingua prompt compression

Install: `pip install llmlingua` (large — ~500MB).

Add `src/rag/compression.py`:
```python
"""Prompt compression via LLMLingua — Stretch W10.

Trades LLM cost for extra CPU. Risk: groundedness can drop on technical
content. ALWAYS measure before shipping.
"""
_compressor = None
def _get_compressor():
    global _compressor
    if _compressor is None:
        from llmlingua import PromptCompressor
        _compressor = PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank")
    return _compressor

def compress_context(context: str, ratio: float = 0.5) -> str:
    """Drop ~ratio of tokens from context, preserving important ones."""
    result = _get_compressor().compress_prompt(
        context, rate=ratio, force_tokens=[",", ".", "\n"]
    )
    return result["compressed_prompt"]
```

Run on 5 golden questions, measure precision@3 + grounded response rate
+ tokens saved. Write findings to `docs/wk10-stretch-notes.md` with a
clear KEEP/DROP verdict.

## Stretch B (45 min) — Cold-start synthetic Q+A cache primer

Pre-populate the cache with 20-30 synthetic FAQ-style questions BEFORE
first user traffic. First-week cost drops meaningfully.

```python
"""scripts/cold_start_prime.py

Generate synthetic questions from corpus + answer + cache them.
"""
from src.rag.qdrant_store import QdrantStore
from src.rag.qdrant_rag import ask_rag

# Method 1: hand-crafted questions per doc type
seed_questions = [
    "what is our leave policy",
    "how do I submit an expense report",
    "who approves my time off",
    # ... 20-30 total
]

for q in seed_questions:
    result = ask_rag(q)  # runs full RAG on cold cache, caches result
    print(f"Primed: {q!r} (hit={result['cache_hit']})")
```

Or use LLM to generate questions per doc chunk. Cost: ~$0.05 to prime
30 questions.

---

## Testing checklist

### Core
- [ ] `src/rag/cache.py` exists; `lookup` returns None on empty; `put` + `lookup` roundtrip works
- [ ] `qdrant_rag.ask_rag()` returns `cache_hit=False` first call, `True` second
- [ ] `pipeline.tombstone_source()` uses `IsEmptyCondition` (NOT IsNull)
- [ ] `pipeline.ingest_or_update_source()` returns non-zero `tombstoned` count for existing source; clears cache after
- [ ] `retrieval.dense_search()` applies `_live_filter` by default; `include_deleted=True` bypasses
- [ ] `scripts/update_document.py` runs end-to-end on a real capstone doc
- [ ] `docs/kpi/wk10-snapshot.md` shows cold vs warm cost + latency numbers
- [ ] `docs/adr/0001-capstone-framing.md` extended with W10 decisions
- [ ] `docs/runbooks/document_update.md` exists

### Stretch (if attempted)
- [ ] Either `compression.py` OR `cold_start_prime.py` works
- [ ] `docs/wk10-stretch-notes.md` with KEEP/DROP verdict

---

## Common issues + fixes

**Cache always misses even on identical repeat queries**
Check `db_path` — cache.py and qdrant_rag.py must use the same file.
Default is `results.db`; if you moved it, both need the change.

**Cache returns wrong answers occasionally**
False-hit rate too high. Raise threshold from 0.95 → 0.97. Also verify
your embeddings model is stable (`text-embedding-3-small`, not floating).

**Tombstone matched 0 despite live chunks existing**
The classic IsNull-vs-IsEmpty bug. Confirm `pipeline.py` imports
`IsEmptyCondition`, not `IsNullCondition`. Both exist — one silently
doesn't work for absent fields.

**After update, queries still return old chunks**
Cache invalidation didn't fire. Confirm `ingest_or_update_source()`
calls `cache.clear()` (or `clear_cache_after=True`). Also possible:
you have another cache layer (Redis?) not being cleared.

**W10 Verifier fails at C18 (tombstone check)**
The v2 Verifier checks for `IsEmpty`, not `IsNull`. If your code still uses
`IsNullCondition`, update it. If you're using the old shipped W10 Package
(v1), grab the v2 Package instead — the verifier grep pattern changed.

**Cost per query on cold pass is much higher than expected**
Your golden set questions are longer than average (>200 tokens each), or
you're using text-embedding-3-large instead of small. Both are legit; just
note in your snapshot.

---

## What you have when done

**Core (mandatory):**
- `src/rag/cache.py` (~100 lines)
- `src/rag/qdrant_rag.py` (modified for cache-first)
- `src/rag/pipeline.py` (tombstone + update flow added)
- `src/rag/retrieval.py` (live filter added)
- `scripts/update_document.py`
- `scripts/measure_wk10_cache.py`
- `tests/test_cache.py` + `tests/test_tombstones.py`
- `docs/kpi/wk10-snapshot.md`
- `docs/adr/0001-capstone-framing.md` (W10 section)
- `docs/runbooks/document_update.md`

**Stretch (optional):**
- Either `compression.py` OR `cold_start_prime.py`
- `docs/wk10-stretch-notes.md`

Total time: Core ~2.5 hours; Stretch ~45 min.

---

## What's coming in W11

**Back to normal pace.** W11 is RAG Evaluation Framework:
- pytest-based eval harness (CI-friendly)
- Regression tests that catch quality drops between commits
- Golden-set validation as a first-class part of your development loop
- The cache + tombstone patterns from W10 become things the harness
  explicitly tests ("did the cache invalidation fire on document update?")

The DANGER ZONE is behind you. W11 + W12 are calmer weeks — evaluation
harness and debugging patterns. Consolidate this weekend — re-read your
wk10-snapshot.md, run the update flow one more time, understand WHY the
IsEmpty fix works.

---

*W10 Application Growth Guide. Second Core+Stretch week. Track B of the
two-track W10 pattern. Companion to `wk10_day1_caching.ipynb`,
`wk10_day2_lifecycle.ipynb`, `wk10_pipeline.py`, and
`AI-RAG_W10_Lab_Guide.md`.*
