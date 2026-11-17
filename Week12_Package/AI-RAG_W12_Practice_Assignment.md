# Week 12 Activity — The Debugging Drill (mandatory hands-on)

**Time:** ~60 minutes · **Runs fully offline** (no API key, no cost) · this is the
week's core hands-on. You will diagnose **six broken RAG queries** from their
traces, using the failure taxonomy and the debugging runbook.

Keep open:
- `docs/debugging/rag_failure_taxonomy.md` — the four buckets
- `docs/runbooks/rag_debugging.md` — the 5-step workflow

---

## What to do

For **each** of the six scenarios (S1–S6):

1. Read the symptom and the trace:
   ```bash
   python3 scripts/debug_drill.py run S1
   ```
2. Apply the runbook's **Isolate** step — find the first stage whose output is
   wrong.
3. Decide the **bucket** (retrieval / generation / prompt / infra) and the
   **fix**, then check yourself:
   ```bash
   python3 scripts/debug_drill.py grade S1 retrieval
   ```
4. Record your diagnosis in the table below.

You must get all six classifications correct, and be able to state the trace
evidence and a fix for each.

---

## Your diagnosis table (fill this in)

| # | Symptom (one line) | Bucket | Trace evidence (what tipped you off) | Root cause | Smallest fix |
|---|---|---|---|---|---|
| S1 |  |  |  |  |  |
| S2 |  |  |  |  |  |
| S3 |  |  |  |  |  |
| S4 |  |  |  |  |  |
| S5 |  |  |  |  |  |
| S6 |  |  |  |  |  |

---

## Phase 2 consolidated decisions (v2 · M2)

| Area | Decision | Why |
|---|---|---|
| Chunking | 512-token, 64 overlap | balances recall vs precision |
| Hybrid weight | BM25 0.4 + dense | catches exact-term queries |
| Reranker + top-K | cross-encoder, top-K 3 | lifts context precision; small prompt |
| Cache | semantic (0.95) + tombstones | cost win, safe deletes |
| Eval | RAGAS thresholds (faithfulness 0.85, recall 0.80, ...) | defensible bar |
| KPIs | 8-KPI dashboard, kb_version-tagged | portfolio evidence |

| Area | Decision | Why |
|---|---|---|
| Chunking | 512-token, 64 overlap | balances recall vs precision |
| Hybrid weight | BM25 0.4 + dense | catches exact-term queries |
| Reranker + top-K | cross-encoder, top-K 3 | lifts context precision; small prompt |
| Cache | semantic (0.95) + tombstones | cost win, safe deletes |
| Eval | RAGAS thresholds (faithfulness 0.85, recall 0.80, ...) | defensible bar |
| KPIs | 8-KPI dashboard, kb_version-tagged | portfolio evidence |

Take **your** lowest-scoring golden question and run the full workflow on it:
**reproduce → narrow → isolate → fix → verify.** Write up what you found in
`docs/wk12-debug-trace.md`. Even a diagnosis without a complete fix is valuable —
it's exactly what production debugging looks like, and it's strong material for
your DR #2 "where does it still fail?" answer.

## What good looks like

- You name the **stage**, not just "the model is bad."
- You spot the **stale-cache** hit (S5) and the **missing grounding instruction**
  (S4) — the two that masquerade as something else.
- You argue **retrieval before generation**: if the context is wrong, don't blame
  the model.
- Your fix is the **smallest** change for the bucket, and you'd **verify** it by
  re-running the eval suite.

Answer key: `Activity_Solution.md`.
