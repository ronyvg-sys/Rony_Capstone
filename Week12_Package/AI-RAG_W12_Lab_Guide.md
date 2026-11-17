# AI-RAG · Week 12 Lab Guide
## RAG Debugging Lab — and the M2 milestone

> **Phase 2 finish line · Medium difficulty · ~3 hrs.**
>
> Two parts. **Part A** is the hands-on debugging drill — six broken RAG queries
> you diagnose from their traces (fully offline, no API key, no cost). **Part B**
> packages your RAG capstone for **M2** and prepares your **DR #2** defense.

---

## Before you start

```bash
unzip AI-RAG_W12_Package.zip -d AI-RAG_W12/
cd AI-RAG_W12/
bash smoke_test.sh        # runs the drill offline + checks the M2 docs → ALL CHECKS PASSED
```

No credentials needed — the drill is deterministic and offline.

> **Troubleshooting — pytest crashes at startup** with `ModuleNotFoundError: No
> module named 'langsmith.pytest_plugin'` (or similar): a broken third-party
> pytest plugin in the environment loads before any test. `pytest.ini` blocks the
> usual culprit and `smoke_test.sh` sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. For a
> differently-named one, prefix your command:
> `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/`.

---

# PART A — The debugging drill (the hands-on)

**Goal:** classify all six failures correctly and name the fix for each, using
the trace, the taxonomy, and the runbook. This is the skill of the week.

Keep two files open: the **taxonomy** (`docs/debugging/rag_failure_taxonomy.md` —
the four buckets) and the **runbook** (`docs/runbooks/rag_debugging.md` — the
5-step workflow).

### A.1 — See the six failures

```bash
python3 scripts/debug_drill.py list
```

Each has a one-line symptom, no bucket given. Your job is to find the bucket.

### A.2 — For each scenario: run → read → classify → check

```bash
python3 scripts/debug_drill.py run S1        # prints S1's full stage-by-stage trace
```

Read the trace top to bottom. Apply the runbook's **Isolate** step: find the one
stage whose output is wrong, and match it to a bucket
(retrieval / generation / prompt / infra). Then check yourself:

```bash
python3 scripts/debug_drill.py grade S1 retrieval
```

A correct classification reveals the root cause and the fix. A wrong one gives a
hint. Work S1 through S6.

**Checkpoint ✅** — you have classified all six, and for each you can say *which
stage broke, why, and the smallest fix*. (Record your six diagnoses — that's the
Activity deliverable; see `Activity.md`.)

> The six span the whole taxonomy: two retrieval (recall miss, precision noise),
> one generation (hallucination), one prompt (lost grounding instruction), two
> infra (stale cache, timeout). If you can diagnose these, you can diagnose your
> own capstone's failures.

---

# PART B — The M2 deliverable

M2 is five items. Run the readiness check any time to see what's left:

```bash
python3 scripts/m2_check.py
```

### Step 1 (Core, ~60 min) — Production-ready RAG API

Confirm your FastAPI service (from W5) wraps the full W6–W11 pipeline, and
smoke-test it end to end:

```bash
uvicorn src.api.main:app --reload            # your service
curl -s localhost:8000/health | python3 -m json.tool         # Qdrant + cache + model
curl -s -XPOST localhost:8000/ask -d '{"question":"What is the leave policy?"}'   # ×3 questions
# call the same question twice → 2nd response should be a cache hit
```

**Checkpoint ✅** — `/ask` answers 3 capstone questions with citations, the 2nd
identical call is a cache hit, and `/health` reports Qdrant connection, cache
status, and model name.

### Step 2 (Core, ~45 min) — Eval suite + KPI dashboard

```bash
python3 -m pytest eval/ -q                   # your W11 suite — all thresholds pass
python3 scripts/run_eval.py                  # refresh the 8-KPI numbers
```

Then update `docs/kpi/wk12-snapshot.md` with your latest 8 KPIs, the **wk6→wk12
trajectory**, and a short **commentary** (which KPIs improved most, what drove
them, what's still N/A). A filled example ships in this package.

**Checkpoint ✅** — `pytest eval/` green; `wk12-snapshot.md` has 8 KPIs + trajectory
+ commentary.

### Step 3 (Core, ~30 min) — ADR v2 (Phase 2 closure)

Update `docs/adr/0001-capstone-framing.md` so it captures **every** Phase 2
decision with its current value (chunker, PII, BM25 weight, reranker, top-K, cache
threshold, tombstone policy, `kb_version`, RAGAS thresholds, KPI numbers). Mark it
**v2 (M2)**. The shipped ADR has the consolidated decision table to model.

**Checkpoint ✅** — ADR marked v2 (M2); the Phase 2 decision table is complete.

### Step 4 (Core, ~45 min) — DR #2 one-pager

Fill `docs/dr/dr2-summary-template.md` (or 5 slides): problem framing, retrieval
choices (why hybrid + rerank vs alternatives), KB lifecycle (tombstones + update
runbook), the 8-KPI dashboard with trajectory, open trade-offs, open questions.
Each section maps to a rubric dimension. **Dry-run once with a peer** (5 minutes).

**Checkpoint ✅** — `dr2-summary.md` committed; peer dry-run done.

### Step 5 (Stretch, ~20 min) — Debug your own worst failure

Optional but recommended. Take your **lowest-scoring golden question**, apply the
5-step workflow (reproduce → narrow → isolate → fix → verify), and write up what
you found in `docs/wk12-debug-trace.md`. Even a diagnosis without a full fix is
valuable — it's exactly what you'll do in production.

---

## Done when…

- [ ] `bash smoke_test.sh` → ALL CHECKS PASSED.
- [ ] All six drill scenarios classified correctly (Part A / `Activity.md`).
- [ ] Production API smoke-tested (`/ask` + cache + `/health`).
- [ ] `pytest eval/` green; `wk12-snapshot.md` has 8 KPIs + trajectory + commentary.
- [ ] ADR marked v2 (M2) with the full Phase 2 decision table.
- [ ] `dr2-summary.md` committed; peer dry-run done.
- [ ] (Stretch) `wk12-debug-trace.md` written.

If you're struggling to debug, it usually means a **foundation gap** from an
earlier week (caching not fully wired, eval suite broken). Find the gap before
piling on — that's the whole point of a debugging week at the end of Phase 2.

**Next:** DR #2 (scheduled separately, 15 min), then Phase 3 — agents that *use
tools*. Different failures; same debugging discipline.
