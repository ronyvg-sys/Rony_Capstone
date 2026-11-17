# AI-RAG · Week 12 Lab Guide (Notebooks)
## RAG Debugging Lab + M2 · Design Review #2

W12 is delivered as **two runnable notebooks**, one per day. They contain the same code
as the package modules, lifted verbatim into narrated cells so you can run a cell, read
the trace or the check, and explain it. Both run **fully offline** — the debugging
pipeline is synthetic and deterministic, and the M2 checker reads local documents — so
there's **no API key and no cost** anywhere.

| Notebook | Day | Covers |
|---|---|---|
| **`AI-RAG_W12_Notebook_1.ipynb`** — Debugging RAG | Day 1 | the trace, the staged pipeline, the four-bucket taxonomy, the 6-scenario drill, the workflow |
| **`AI-RAG_W12_Notebook_2.ipynb`** — M2 & DR #2 | Day 2 | the five M2 items, the readiness checker, the 8-KPI dashboard, ADR v2, the DR #2 one-pager |

Each notebook is **self-contained**: Notebook 1's setup writes the golden set the
pipeline reads; Notebook 2's setup writes example M2 documents so the checker runs green.

---

## Before you start

```bash
jupyter lab            # or open the .ipynb in VS Code / Cursor
```

No packages to install — both notebooks are **pure standard library**. In each notebook:
**Kernel → Restart & Run All.** Every cell should go green. (They ship already-executed so
you can read the outputs first.)

---

## Notebook 1 — Debugging RAG (Day 1)

The mantra: **same symptom, different causes — classify first.** Work the sections in order:

1. **The trace** (`trace.py`) — the instrument. A `Trace` is every stage's input/output for
   one query; `render()` is what you scan for the one wrong stage.
2. **The staged pipeline** (`pipeline.py`) — embed → cache → retrieve → rerank → prompt →
   generate. Run the healthy query first and read a clean trace.
3. **The taxonomy** — the **four *primary runtime* buckets**: retrieval / generation /
   prompt / infra. These localise a failure *from the trace*. Note the framing: they are
   **not** the whole universe of RAG failures — cross-cutting ones (ingestion/data-quality,
   access/security, eval/reference, user-input/policy) live outside the runtime pipeline.
4. **The six scenarios** (`scenarios.py`) — each breaks exactly one stage; the answer key is
   revealed by the grader only on a correct classification.
5. **The drill** — the loop: read the trace → classify → check. Run `S1` (a recall miss),
   read the trace, then `grade('S1', 'retrieval')`. Try a wrong bucket to see the hint. Then
   grade `S3` yourself, and view the six-at-a-glance table (each maps to one bucket).
6. **The workflow** — Reproduce → Narrow → Isolate → **Fix** → Verify. Apply the *smallest*
   change for the isolated bucket, **one thing only** — and treat retrieval changes (raise
   top-K, smaller chunks) as **candidates you test against the golden set**, because each
   trades off. No layer is unconditionally "fine": if generation looks wrong but the evidence
   was insufficient, the real fix is retrieval. **Verify = re-run the whole eval suite.**
7. **The trace pays double** — one trace = one query's cost & latency (great for spotting an
   outlier); the mean cost/query and **p50/p95 come from aggregating many traces**, not one.

**Checkpoint ✅** — all cells green; you can read any scenario's trace, name the wrong stage,
and classify the bucket before revealing the key.

---

## Notebook 2 — M2 Milestone & Design Review #2 (Day 2)

Packaging and defending — lighter on code, heavier on structure:

1. **The five M2 items** — production API, eval suite, 8-KPI dashboard, ADR v2, DR #2
   one-pager. Items 1–2 are your code; 3–5 are documents.
2. **The readiness checker** (`m2_check.py`) — run it against the example docs; it verifies
   the three documents (all ✓) and prints the commands for the two code items.
3. **The 8-KPI dashboard + wk6→wk12 trajectory** — displayed inline. Read the **KPI #4
   reconciliation**: retrieval hit rate is now measured to its *canonical* definition
   (correct chunk in top-K, 0.90), with context precision (0.85) kept as a supporting
   metric — a **definition lock, not a regression**. Being explicit about it is what a top
   "ADR quality" score looks like.
4. **ADR v2 (M2)** — consolidate every Phase-2 decision (chunker, BM25 weight, reranker,
   top-K, cache threshold, tombstones, RAGAS thresholds, KPIs) into one table; mark v2 (M2).
5. **The DR #2 one-pager** — five sections mapped to the five rubric dimensions (worked
   example shown), the scoring rubric, and the "retrieval + KB-lifecycle defense" scope with
   the peer-challenge questions.

**Checkpoint ✅** — `m2_check` is all green on the example docs; you can explain the KPI #4
reconciliation and what evidence each DR #2 section needs.

---

## Taking it to your own capstone

The notebooks demonstrate the tools; the milestone is **your** system:

- **Debugging (from NB1):** when a golden question fails, apply the five-step workflow to
  *your* pipeline — get the trace, isolate the first wrong stage, make the smallest change,
  re-run `eval/`. Write up your worst case (a diagnosis without a fix still counts).
- **M2 (from NB2):** replace the example docs with your real ones — fill `wk12-snapshot.md`
  with your live 8 KPIs + trajectory, consolidate your ADR to v2, write your DR #2 one-pager
  — then run `m2_check.py` **against your repo** (not the example docs) until it's green.
- **Items 1–2** are verified with the commands the checker prints: `curl` your `/health` and
  `/ask` endpoints, and `python3 -m pytest eval/ -q`.

## Done when…

- [ ] Both notebooks: **Restart & Run All** → all cells green, no errors.
- [ ] You can classify all six drill scenarios from their traces before checking.
- [ ] `m2_check` is green (on the example docs here, then on your own repo).
- [ ] Your five M2 items are complete, with the KPI #4 reconciliation documented.
- [ ] Your DR #2 one-pager defends retrieval + KB lifecycle with KPI evidence.

## Notebook vs the suite & service

These notebooks are where you **see and explain** the debugging and the milestone. In the
repo, the eval lives as a **pytest suite** that gates every commit, and the API is your
**running FastAPI service** — the notebook to understand it, the suite and service to run
it. Next: **DR #2** (formative; first hard bar is DR #3 at W18), then **Phase 3 — Agents**.
