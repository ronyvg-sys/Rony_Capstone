# RAG Failure Taxonomy

Before you debug, **classify**. The same symptom ("the answer is wrong") has very
different causes and fixes depending on *where* it broke. Every RAG failure falls
into one of four buckets. Read the trace, decide the bucket, then apply that
bucket's diagnostic move.

Each bucket below links to the drill scenario that demonstrates it
(`scripts/debug_drill.py run S…`) and the W11 metric that flags it in aggregate.

---

## 1. Retrieval failures — *the right chunk wasn't retrieved*

The generator never had a chance because the context handed to it was wrong or
incomplete. Two sub-modes:

- **Recall miss** — a chunk the answer needs never reached the top-K. Common on
  multi-hop questions that span two documents. *(Drill S1; W11 metric: context
  recall.)*
- **Precision noise** — distractor chunks outranked the relevant one and pushed
  it out of the top-K, so the model worked from noise. *(Drill S2; W11 metric:
  context precision.)*

**Trace tell:** in `retrieve` / `rerank`, the needed `chunk_id` is absent or
ranked low, or `kb-*` distractors sit on top with high scores.
**Typical fixes:** raise top-K or add query expansion (recall); retune hybrid
weighting / the reranker, or reduce chunk size (precision).

## 2. Generation failures — *right chunks, wrong answer*

Retrieval was correct, but the model produced a wrong or unsupported answer.

- **Hallucination** — the answer asserts a fact that appears in none of the
  retrieved chunks. *(Drill S3; W11 metric: faithfulness.)*
- **Off-topic / padded** — the answer wanders or hedges instead of answering.
  *(W11 metric: answer relevance.)*

**Trace tell:** `retrieve`/`rerank` are healthy (correct chunks, good scores) but
the answer contains content not in the context.
**Typical fixes:** lower temperature; tighten the grounding constraint; shorten
or restructure the answer instruction. Do **not** touch retrieval — it's fine.

## 3. Prompt failures — *the prompt itself is wrong*

Retrieval and the model are both fine, but the instructions assembled into the
prompt are broken — most often the "answer only from the context" line went
missing, so the model feels free to add unsupported content.

**Trace tell:** in `prompt`, `has_grounding_instruction` is false (or the wrong
template/version is in use); the answer then includes steps or claims not in the
context. *(Drill S4.)*
**Typical fixes:** restore the grounding instruction; pin the prompt template
version; diff the prompt against the last known-good run.

## 4. Infra failures — *the pipeline broke*

Nothing wrong with retrieval, prompt, or model reasoning — a piece of plumbing
failed.

- **Stale cache** — a cache hit returned a previously-cached answer for a
  *different* question (key collision or missing invalidation), so retrieval and
  generation never ran. *(Drill S5; W11 signal: cache-hit accuracy below
  cache-miss accuracy.)*
- **Timeout / API error** — a stage failed outright (e.g., the generation call
  timed out), so no answer came back. *(Drill S6.)*

**Trace tell:** `cache` shows a hit whose `cached_for_question` ≠ the asked
question, or a stage is marked failed (✗) with an error and a latency spike.
**Typical fixes:** fix the cache key / invalidate stale entries (tie to the W10
tombstone + `kb_version` flow); add retry-with-backoff and a timeout budget.

---

## The decision move

```
Symptom → read the trace → which stage's output is wrong?
   retrieve/rerank wrong  → RETRIEVAL   (recall vs precision)
   context good, answer invents/wanders → GENERATION
   prompt missing its instruction → PROMPT
   cache hit for wrong Q, or a stage errored → INFRA
```

One bucket, one place to look, one class of fix. Classify first; fix second.
The systematic workflow for doing this end-to-end is in
[`../runbooks/rag_debugging.md`](../runbooks/rag_debugging.md).
