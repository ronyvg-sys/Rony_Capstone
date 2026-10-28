# AI-RAG · Week 10 · Lab Guide

**Topic:** RAG Optimisation, Caching & Knowledge Base Lifecycle
**Phase 2 · Week 5 of RAG · Second DANGER ZONE week**

**⚠ Read this first:** W10 is the second DANGER ZONE week in a row. Two dense
themes stack this week — optimisation (caching at three layers + prompt
compression) and lifecycle (how the KB changes over time without breaking
retrieval). Pace matters. Slow down on the threshold tuning demo (Day 1
Cell 6) and the IsNull bug diagnosis (Day 2 Cell 4-5). Those are where
this week's ideas land.

---

## Two-Track structure

**Track A — in-class demos, split across two days.** Two notebooks —
`wk10_day1_caching.ipynb` and `wk10_day2_lifecycle.ipynb` — teach the
concepts on the W9 Acme Analytics Platform corpus (reused for continuity).
Standalone, Vocareum-compatible, run in ~75 and ~90 minutes.

**Track B — take-home Application Growth Guide** (`AI-RAG_W10_Application_
Growth_Guide.md`). Wire the same concepts into YOUR capstone codebase.
Core+Stretch tagging continues from W9.

**Deck alignment:**
- Deck slides 3-20 → Day 1 (context optimisation + 3-layer caching + Block 1)
- Deck slides 21-44 → Day 2 (lifecycle + tombstones + KPI wrap + Block 2)

---

## Day 1 — Context Optimisation + Three Caching Layers

**~75 min · `wk10_day1_caching.ipynb`**

**Learning arc:**
1. Count where your prompt tokens actually live (Cell 2)
2. Reduce k safely — measure precision AND recall (Cell 3)
3. Build the semantic cache from scratch (Cell 5)
4. Live threshold tuning + a false-hit demo (Cell 6 — the pedagogical peak)
5. Prompt cache (OpenAI provider-side) — inspect the `cached_tokens` field (Cell 7)
6. Cost + latency comparison, cold vs warm (Cell 9)

**Key teaching moment — Cell 6 false-hit demo:**
The cache is primed with "what is error code AC-1042" (a query timeout).
User asks "what is error code AC-4408" (a dashboard failure). At threshold
0.85 the cache returns the AC-1042 answer — a plausible but WRONG answer
served with confidence. This is why the programme default is 0.95.

**Cost:** ~$0.01 per full run (embeddings + a handful of LLM calls).

**Homework before Day 2 (~2 min):** verify `IsEmptyCondition` and
`IsNullCondition` both import cleanly from `qdrant_client.models` — if
`IsEmpty` fails, your `qdrant-client` is pre-1.7 and needs `pip install -U qdrant-client`.

---

## Day 2 — KB Lifecycle: Tombstones + the IsNull Bug + KPI Wrap

**~90 min · `wk10_day2_lifecycle.ipynb`**

**Learning arc:**
1. See the naive-update problem (duplicate versions in retrieval — Cell 2)
2. Understand the tombstone pattern conceptually (Cell 3)
3. **Live IsNull bug diagnosis** — write the filter with `IsNullCondition`,
   watch it silently match 0 chunks, diagnose live (Cell 4)
4. Fix with `IsEmptyCondition`, understand Qdrant's absent-vs-null semantics (Cell 5-6)
5. End-to-end update flow: tombstone → insert → verify (Cell 7)
6. **Cache invalidation gotcha** — the cache from Day 1 serves stale answers
   after a document update; fix by clearing on every update (Cell 8)
7. Re-indexing cost formula (post-audit correction — Cell 9)
8. KPI comparison across W8→W9→W10 (Cell 12)

**Key teaching moment — Cell 4-5 IsNull bug:**
This is the memorable moment of the week. The audit found this bug in the
shipped W10 code; we turn it into pedagogy. Learners write the "obvious"
filter with `IsNullCondition`, run it, see 0 matches, diagnose live via a
controlled experiment (set `deleted_at=None` explicitly on one point and
watch what changes), then fix with `IsEmptyCondition`. Emphasises the
generic rule: prefer defensive primitives even when the offensive one
would work today.

**Cost:** ~$0.01 per full run.

---

## Track A file inventory

Both notebooks in `demos/`:

| File | Role |
|---|---|
| `wk10_pipeline.py` | Helpers: cache primitives, tombstone filter builders, cost estimator, prompt token accounting. Imports from `sample_docs/` (reused W9 corpus). |
| `wk10_day1_caching.ipynb` | Day 1 notebook, 8 code cells, ~75 min |
| `wk10_day2_lifecycle.ipynb` | Day 2 notebook, 11 code cells, ~90 min |
| `sample_docs/acme_docs.jsonl` | 15 Acme docs (reused from W9 unchanged) |
| `sample_docs/acme_test_queries.jsonl` | 6 test queries (reused from W9 unchanged) |

---

## Track B — Application Growth Guide (take-home)

Open `AI-RAG_W10_Application_Growth_Guide.md`. Structured as:

**🟢 Core (~2.5 hours — mandatory)**
- Step 1 (60 min): `src/rag/cache.py` new + wire into `qdrant_rag.py`
- Step 2 (45 min): tombstone update flow in `pipeline.py`; retrieval-time filter in `retrieval.py`; `scripts/update_document.py`
- Step 3 (45 min): golden set cold + warm; `docs/kpi/wk10-snapshot.md`
- Step 4 (30 min): extend ADR; write `docs/runbooks/document_update.md`

**🟡 Stretch (~45 min — optional)**
- Either LLMLingua prompt compression, or cold-start synthetic Q+A cache primer

**Cost:** total <$0.05 (golden set × 2 passes + embeddings).

---

## Environment & prerequisites

```
Python 3.10+
qdrant-client >= 1.7            # required for IsEmptyCondition
openai                          # any current version
sentence-transformers           # from W9, still needed for reranker
sqlite3 (stdlib)                # no install needed
tiktoken (optional)             # graceful fallback if missing
```

Environment variables (from W7 setup, unchanged):
```
OPENAI_API_KEY=sk-…
QDRANT_URL=https://<your-cluster>.qdrant.tech:6333
QDRANT_API_KEY=…
```

**No new heavy downloads this week** — unlike W9's ~80 MB cross-encoder,
W10 uses only libraries already installed by W7-W9.

---

## Verifier update — W10 v2

The shipped verifier (`AI-RAG_W10_Verifier.py` v2) has been updated:

- **C18 (retrieval tombstone check):** now accepts EITHER `IsEmptyCondition`
  (v2 preferred) OR `IsNullCondition` (v1 legacy) as valid — grace period
  for learners still on the v1 shipped package.
- **`_count_live_chunks` helper:** uses `IsEmptyCondition` (matches both
  v1 and v2 payload conventions).

If your Track B code uses `IsNullCondition`, the verifier will still pass
C18 but with a note recommending migration to `IsEmpty`. If you're starting
from scratch, use `IsEmpty`.

---

## Common issues + fixes

**Day 1 Cell 5 sanity check shows `cache_hit=False` on both calls**
The cache DB isn't shared across calls. Confirm `cache_init(CACHE_DB)` uses
the same DB file both times (Cell 5 stores to `wk10_day1_cache.db`; Cell 6
must use the same file, not create a new one).

**Day 1 Cell 7 (prompt cache) always shows `cached_tokens=0`**
Prompt < 1,024 tokens (OpenAI's minimum for auto-cache). Either use a
longer question, or add extra system-prompt context to push the total past
the threshold.

**Day 2 Cell 4 raises `UnexpectedResponse: 400 Bad Request — Index required but not found for "source"`**
Qdrant requires a payload index on any field you filter on. The notebook's
Cell 1 creates indexes on `source` (keyword) and `deleted_at` (float) right
after `create_collection` — if you started from an older notebook version
that skipped this, add the index-creation block before running Cell 4. In
the shipped capstone code, `pipeline.ensure_payload_indexes()` handles this
automatically.

**Day 2 Cell 4 IsNull bug demo shows > 0 matches (defeats the pedagogy)**
Your Qdrant collection was seeded with `deleted_at: None` explicitly — the
IsNull filter matches those. Delete the collection and re-run Cell 1
(which seeds without setting deleted_at at all — the setup that reveals
the bug).

**Day 2 Cell 6 IsEmpty tombstones ZERO chunks despite live chunks existing**
Either the filter condition is malformed, or the seed didn't populate
correctly. Run `qdrant.count(COLLECTION, exact=True)` to confirm live
population, then re-verify the filter builder.

**Track B: Cache always misses on identical repeat queries**
Check `db_path` — cache.py and qdrant_rag.py must use the same file
(default `results.db`; if you moved it, both need the change).

**Track B: `pytest` finds no tests**
Run `python -m pytest` from the project root, not just `pytest`. The `-m`
form uses your project's Python + PYTHONPATH.

---

## What learners have when done

**After Day 1 (Track A):**
- Working semantic cache with tunable threshold
- Prompt token accounting habit
- Understanding of the 3 caching layers + when each fires
- Latency + cost measurement muscle memory

**After Day 2 (Track A):**
- Live experience of the IsNull silent-failure mode
- End-to-end document update flow
- Understanding of why cache invalidation is a first-class step
- W8→W9→W10 KPI arc grasped

**After Track B Core:**
- Cache wired into capstone's `qdrant_rag.py`
- Tombstone update flow in capstone's `pipeline.py`
- `wk10-snapshot.md` with real cost + latency deltas from YOUR corpus
- Update runbook + ADR extended

**After Track B Stretch (if attempted):**
- LLMLingua compression measured on real questions with KEEP/DROP verdict
  OR cold-start cache primer functioning

---

## Coming in W11

Back to normal pace. RAG Evaluation Framework:
- pytest-based eval harness (CI-friendly)
- Regression tests catching quality drops between commits
- Cache + tombstone patterns become things the harness explicitly tests

The DANGER ZONE ends here. W11 and W12 are calmer. Consolidate over the weekend.

---

*W10 Lab Guide v2 — updated for the Two-Track split (Day 1 / Day 2 notebooks)
and IsNull → IsEmpty auditor fix. Companion to `AI-RAG_W10_Deck_v2.pptx`,
`wk10_day1_caching.ipynb`, `wk10_day2_lifecycle.ipynb`,
`AI-RAG_W10_Application_Growth_Guide.md`, and the v2 shipped Package.*
