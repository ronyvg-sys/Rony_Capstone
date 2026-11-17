# Runbook — Debugging a RAG Failure

The operational procedure for diagnosing any RAG failure in the capstone. It is
the W11 eval-regression triage playbook turned into a full incident runbook, and
it follows the same shape as the W10 `document_update.md` runbook (which W22/W29
reuse). Five steps: **Reproduce → Narrow → Isolate → Fix → Verify.**

Pair this with the four-bucket [failure taxonomy](../debugging/rag_failure_taxonomy.md).

---

## 0. Trigger

You have a failing case: a specific question whose answer is wrong, or a KPI that
moved on the W11 dashboard. Note the exact question (or golden id) before you
start.

## 1. Reproduce

Run the same input again. Does the failure repeat?

- **Repeats** → deterministic; continue to step 2.
- **Doesn't repeat** → it's flaky. That itself is a classification: suspect
  **infra** (timeout, transient API error) or non-deterministic **generation**
  (temperature). Capture a trace when it does fail.

```bash
# Reproduce against the capstone (live) or the drill pipeline (offline)
python3 scripts/debug_drill.py run S3          # offline example
# or, live: re-run the failing golden question through your API / eval
```

## 2. Narrow — get the trace

Get the input and output of **every** pipeline stage for that one query. This is
the whole game: you cannot debug what you cannot see.

```bash
python3 scripts/debug_drill.py run <Sn>        # prints the full stage-by-stage trace
```

The trace shows: embed → cache → retrieve (chunk_ids + scores) → rerank (order) →
prompt (grounding instruction? length) → generate (answer, tokens, cost, errors).

## 3. Isolate — which stage's output is wrong?

Scan the trace for the **one** outlier and classify it with the taxonomy:

| What you see in the trace | Bucket | Where it broke |
|---|---|---|
| Needed `chunk_id` absent, or distractors ranked top | **Retrieval** | retrieve / rerank |
| Chunks correct, but answer adds/omits content | **Generation** | generate |
| `has_grounding_instruction: false` (or wrong template) | **Prompt** | prompt |
| Cache hit for a different question; a stage errored | **Infra** | cache / generate |

Stop at the **first** stage whose output is wrong — that's your cause. Don't
change three things at once.

## 4. Fix — the smallest change that addresses the isolated cause

| Bucket | Smallest fix to try first |
|---|---|
| Retrieval (recall) | raise top-K or add query expansion for multi-hop |
| Retrieval (precision) | retune hybrid weight / reranker; check chunk size |
| Generation | lower temperature; tighten the grounding constraint |
| Prompt | restore the grounding instruction; pin the template version |
| Infra (cache) | fix cache key / invalidate stale entries (W10 tombstone + kb_version) |
| Infra (timeout) | add retry-with-backoff and a timeout budget |

Change **one** thing. Resist the urge to "improve" adjacent code in the same pass.

## 5. Verify — re-run the eval suite

A fix isn't done until the whole suite is green and nothing else regressed.

```bash
python3 -m pytest eval/ -q            # your W11 eval suite — all thresholds pass
python3 scripts/run_eval.py           # refresh the KPI numbers
```

Confirm: the failing case now passes, **and** no other KPI dropped. If a
different metric fell, you traded one bug for another — go back to step 2 on the
new failure. When green, record the fix (and any threshold change) in the ADR and
update the KPI snapshot.

---

## Quick reference

```
Reproduce → does it repeat?  (no → infra/generation flakiness)
Narrow    → get the full trace
Isolate   → first wrong stage → bucket (retrieval / generation / prompt / infra)
Fix       → smallest change for that bucket, ONE thing
Verify    → pytest eval/ green, no regressions → update ADR + snapshot
```
