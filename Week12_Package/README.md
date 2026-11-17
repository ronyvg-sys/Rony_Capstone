# AI-RAG · Week 12 — RAG Debugging Lab (M2 + Design Review #2)

The Phase 2 finish line. Two things happen this week: you learn to **debug RAG
systematically**, and you package + defend your RAG capstone at the **M2**
milestone.

## 60-second start (offline, no credentials)

```bash
unzip AI-RAG_W12_Package.zip -d AI-RAG_W12/
cd AI-RAG_W12/
bash smoke_test.sh        # runs the debugging drill offline; checks M2 docs
```

## The hands-on: a debugging drill

Six broken RAG queries, one per common failure. For each: read the trace,
classify the failure, check your answer — all offline and deterministic.

```bash
python3 scripts/debug_drill.py list          # the six failures
python3 scripts/debug_drill.py run S1        # print S1's full trace
python3 scripts/debug_drill.py grade S1 retrieval   # check your classification
```

Failures span the four buckets of the taxonomy: **retrieval, generation, prompt,
infra** (see `docs/debugging/rag_failure_taxonomy.md`). The 5-step workflow for
diagnosing them is in `docs/runbooks/rag_debugging.md`.

## The M2 deliverable (5 items)

1. Production-ready RAG API (your W5 FastAPI + W6–W11 pipeline) — verify with the
   commands `scripts/m2_check.py` prints.
2. Full eval suite passing (`pytest eval/` — your W11 suite).
3. 8-KPI dashboard — `docs/kpi/wk12-snapshot.md` (8 KPIs + wk6→wk12 trajectory).
4. ADR updated to v2 (M2) — `docs/adr/0001-capstone-framing.md`.
5. DR #2 one-pager — `docs/dr/dr2-summary-template.md` (example alongside).

```bash
python3 scripts/m2_check.py     # checks docs 3–5 + prints the commands for 1–2
```

## What's here

```
src/rag/pipeline.py      deterministic offline staged RAG pipeline (emits a trace)
src/rag/trace.py         the Trace object you read to localise failures
src/debug/scenarios.py   the 6 drill scenarios + answer key + grader
scripts/debug_drill.py   the drill CLI (list / run / grade / run-all)
scripts/m2_check.py      M2 deliverable readiness check
tests/test_scenarios.py  proves each scenario reproduces its failure (offline)
docs/debugging/          the four-bucket failure taxonomy
docs/runbooks/           the 5-step RAG debugging runbook
docs/kpi/                the M2 KPI snapshot (8 KPIs + trajectory)
docs/adr/                ADR v2 (M2) — Phase 2 consolidation
docs/dr/                 DR #2 one-pager (template + example)
smoke_test.sh            offline end-to-end check
AI-RAG_W12_Lab_Guide.md  the lab
AI-RAG_W12_Verifier.py   deliverable compliance checker
```

Then, separately scheduled: **DR #2** — 15 min per learner, peer-reviewed, scored
on the 5-dimension Design Review Rubric ("Retrieval + KB lifecycle defense").
