# ADR 0001 — Capstone Framing

## (Prior W6–W11 entries elided in this snippet — keep the existing
## text from your repo. The block below is the W12 ADDITION, and it marks the
## ADR as **v2 (M2) — Defended at DR #2**.)

---

## W12 — M2 / Phase 2 Closure

W12 closes Phase 2. It adds the debugging discipline (a failure taxonomy, a
systematic workflow, a trace schema) and, for the M2 milestone, consolidates
every Phase 2 architectural decision into one table so the whole RAG design can
be defended at DR #2. Status of this ADR is now **v2 (M2)**.

### Consolidated Phase 2 decision table (the defensible architecture)

| Area | Decision | Current value | Set in |
|---|---|---|---|
| Ingestion — chunking | Recursive chunker, fixed target size | ~512 tokens, 64 overlap | W8 |
| Ingestion — PII | Presidio scrub before embedding | on; emails/names redacted | W8 |
| Ingestion — metadata | `source`, `section`, `kb_version` per chunk | stamped at ingest | W8/W10 |
| Retrieval — dense | OpenAI `text-embedding-3-small` + Qdrant | cosine, top-K candidates | W7 |
| Retrieval — hybrid | Dense + BM25 fusion | BM25 weight 0.4 | W9 |
| Retrieval — rerank | Cross-encoder rerank of candidates | top-K = 3 to context | W9 |
| Caching — semantic | Query cache, cosine threshold | ≥ 0.95 | W10 |
| Caching — provider | OpenAI prompt cache enabled | on | W10 |
| Lifecycle — deletes | **Tombstone** pattern, never hard-delete | `deleted_at` + filter | W10 |
| Lifecycle — updates | Full re-ingest + tombstone old; `kb_version` bump | runbook-driven | W10 |
| Eval — framework | **RAGAS** over the golden set, eval-as-code | offline + live dual-mode | W11 |
| Eval — thresholds | Set per-baseline, just below live numbers | recorded per metric | W11 |
| KPIs | All 8 reported (6 numeric, 2 N/A) | see wk12-snapshot | W6→W12 |

*This table is the DR #2 "why is your architecture this way" answer in one place.*

### Decision 6.1 — RAG failure taxonomy adopted (four buckets)

Failures are classified before they are fixed, into **retrieval / generation /
prompt / infra** (see `docs/debugging/rag_failure_taxonomy.md`). Each bucket has a
distinct diagnostic move and fix. **Rationale:** same symptom, different causes —
classification prevents changing the wrong layer. **Status:** Accepted.

### Decision 6.2 — Systematic debugging workflow is the standard

All RAG debugging follows **Reproduce → Narrow → Isolate → Fix → Verify**
(`docs/runbooks/rag_debugging.md`), with a mandatory eval re-run at Verify.
**Rationale:** a repeatable discipline that works on any non-deterministic system
and guarantees no silent regressions. **Status:** Accepted.

### Decision 6.3 — Trace schema for debugging

Every query can emit a per-stage trace (embed → cache → retrieve → rerank →
prompt → generate) with each stage's key inputs/outputs (`src/rag/trace.py`).
Langfuse is the eventual production trace tool (W25); the local trace is the
teaching/debugging instrument now. **Rationale:** you cannot debug what you cannot
see; trace reading is the core production skill. **Status:** Accepted.

### Decision 6.4 — KPI #4 aligned to its canonical definition

KPI #4 (retrieval hit rate) is measured as *"% of queries with the correct chunk
in top-K"* from M2 onward. W11 used RAGAS **context precision** as a stand-in;
that is retained as a *supporting* metric but is no longer KPI #4 itself.
**Rationale:** the milestone is where definitions get locked; report the KPI to
its stated definition. This is a definition change, not a regression (see
wk12-snapshot methodology note). **Status:** Accepted.

---

*End of W12 ADR additions. ADR status: **v2 (M2) — Defended at DR #2**. Next
update: W18 (M3 — agents + injection defense).*
