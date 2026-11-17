# wk12-snapshot.md — M2 · Production RAG (Phase 2 close)

> *The M2 milestone KPI dashboard. Phase 2 is done: the assistant is measured,
> debugged, and defensible. Numbers below are a filled example — replace with
> your own live run before DR #2. This is portfolio material: six snapshots from
> wk6 to wk12 showing real engineering progress.*

| # | KPI | wk12 | Source | vs wk11 |
|---|---|---|---|---|
| 1 | Task success rate | 0.92 | W5 judge (live) | ▲ 0.90 → 0.92 |
| 2 | Grounded response rate | 0.92 | RAGAS faithfulness | ▲ 0.91 → 0.92 |
| 3 | Hallucination rate | 0.08 | 1 − faithfulness | ▼ 0.09 → 0.08 (good) |
| 4 | Retrieval hit rate | 0.90 | correct chunk in top-K | reconciled — see note |
| 5 | Tool success rate | N/A (W13 — no tools yet) | — | unchanged (N/A) |
| 6 | Cost / query (warm) | $0.000131 | results.db | unchanged |
| 7 | Latency p50 / p95 | 184 / 312 ms | results.db | unchanged |
| 8 | Escalation rate | N/A (W17 — no HITL yet) | — | unchanged (N/A) |

**Supporting RAGAS metrics:** faithfulness 0.92 · answer relevance 0.93 · context
precision 0.85 · context recall 0.90. **KB version:** `v2.w10` · **golden set:** 20
questions · **eval mode:** live RAGAS.

---

## ⚠️ KPI #4 reconciliation (W11 → W12)

The programme defines KPI #4 (retrieval hit rate) as *"% of queries where the
correct chunk appears in top-K."* W11 reported it via RAGAS **context precision**
(0.82) as a stand-in. From M2 onward, KPI #4 is measured to its **canonical
definition** — the fraction of golden questions with the correct chunk in the
top-K — which reads **0.90**. Context **precision** (0.85) is retained as a
*supporting* retrieval-quality metric, not KPI #4 itself. This is a change of
definition, not a regression; compare KPI #4 to the canonical measure from here.

---

## W6 → W12 trajectory

| KPI | wk6 | wk7 | wk8 | wk9 | wk10 | wk11 | wk12 |
|---|---|---|---|---|---|---|---|
| Task success | 0.72 | 0.78 | 0.83 | 0.86 | 0.88 | 0.90 | **0.92** |
| Grounded (judge→RAGAS) | 0.80* | 0.85* | 0.90* | 0.93* | 0.94* | 0.91‡ | **0.92** |
| Retrieval hit rate | 0.70 | 0.78 | 0.85 | 0.91 | 0.91 | 0.82§ | **0.90** |
| Cost / query (warm) | $.0009 | $.0007 | $.0006 | $.0004 | $.00013 | $.00013 | **$.00013** |
| Latency p50 (ms) | 1100 | 950 | 870 | 785 | 184 | 184 | **184** |

`*` groundedness by the W5 judge. `‡` first RAGAS faithfulness measurement. `§`
W11 reported KPI #4 as context precision; wk12 reconciles to the canonical hit
rate. Do not read the wk10→wk11 steps on the starred/marked rows as regressions —
they are instrument/definition changes (documented in the ADR).

## KPI trajectory commentary

- **What improved most:** cost and latency, by an order of magnitude at wk10
  (semantic cache + tombstones). On quality, task success climbed steadily across
  the build weeks (wk6→wk9) and ticked up again at wk12 after a debugging fix.
- **What drove the wk12 gains:** the RAG debugging work. Isolating a multi-hop
  **recall miss** (drill bucket: retrieval) and raising top-K for those questions
  lifted retrieval hit rate and, with it, task success and groundedness. One
  well-diagnosed retrieval bug moved three KPIs.
- **What's still N/A:** tool success (#5) and escalation (#8) — the assistant has
  no tools (arrive W13) and no human-in-the-loop (arrives W17). Reporting a number
  there would be fabrication; they become real in Phase 3+.
- **Cache health:** cache-hit accuracy (0.92) remains at or above cache-miss
  accuracy (0.88) — the W10 cache is a cost win, not a correctness risk.

---

## M2 status

Production-ready RAG: FastAPI service (W5) wrapping the full W6–W11 pipeline,
`pytest eval/` green against baseline thresholds, all 8 KPIs reported (6 numeric,
2 honest N/A), architecture consolidated in ADR v2 (M2). Ready to defend retrieval
+ KB-lifecycle decisions at DR #2.

**Next snapshot:** M3 (W18) — after Phase 3 adds tools/agents (KPI #5 becomes
real) and injection defenses.
