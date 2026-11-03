# AI-RAG · Week 11 Activity — Solution & Rubric
## Diagnose the broken eval report

> Facilitator copy. The point is the *reasoning*, not matching this wording.
> A strong submission finds the retrieval, generation, cache, **and** process
> problems — not just "the model is bad". Eight problems are seeded; six is a pass.

---

## 1. Worked diagnosis

| # | Symptom | Layer | Most likely cause | Confirming evidence |
|---|---|---|---|---|
| 1 | Faithfulness 0.61; `g019` invents a 5% crypto match (0.20) | **Generation** | Prompt isn't enforcing "answer only from context / say when unknown"; the refusal/edge case isn't handled | Diff the generation prompt vs last green run; inspect `g019`/`g020` (the graceful-refusal golden rows) |
| 2 | Context precision 0.44; `g004/g008/g011` top-3 carry 2 off-topic chunks | **Retrieval** | Noisy top-K — W9 hybrid weighting/reranker drifted, or a re-ingest shrank chunk size and diluted the pool | Re-check W9 hybrid/rerank config; compare chunk sizes pre/post re-ingest |
| 3 | Context recall 0.58; `g015` misses the meetings half (0.33) | **Retrieval (coverage)** | Multi-hop questions: the second document's chunk never reaches top-K | Filter the `harder · multi-hop` golden rows; try higher K or a better query for them |
| 4 | Cache hit rate collapsed 65% → 12%; cost up to $0.0004; latency up | **Cache (volume)** | The re-ingest invalidated/!cleared cached entries and the run wasn't warmed; hits fell so full-pipeline cost/latency returned | Check cache population after re-ingest; confirm whether `--clear-cache` ran |
| 5 | Cache-hit accuracy 0.70 **<** miss accuracy 0.83 | **Cache (correctness)** | The cache is serving **stale** answers for documents that changed — tombstone/invalidation didn't fire for the updated docs | Spot-check cache hits on the re-ingested documents against current source |
| 6 | Rows tagged `v2.w10` **and** `v3.w11` in one run | **Process** | Sam re-ingested mid-run, so the aggregate mixes two KBs — the comparison is invalid | Re-run the whole golden set against a single, fixed `kb_version` |
| 7 | Tool success = 0.00 and escalation = 0.00 | **Process / reporting** | These should be **N/A** (W13/W17). Reporting 0.0 fabricates a failing number for capabilities that don't exist | Replace with `N/A (W13…)` / `N/A (W17…)` per ADR §5.7 |
| 8 | All thresholds = 0.30, "all passed" | **Process / reporting** | Threshold theatre — the bar is on the floor, so the suite tests nothing | Set thresholds from the measured baseline (ADR §5.5) |

(7 and 8 are both "process" but are distinct problems — accept them separately.)

## 2. Prescriptions (one line each)

1. Tighten the generation prompt's "answer only from retrieved context; if the
   answer isn't present, say so" instruction; verify on `g019`/`g020`. *(generation)*
2. Restore/retune the W9 hybrid weighting + reranker; re-check chunk size after
   re-ingest. *(retrieval)*
3. Raise K (or add a query-expansion step) for multi-hop questions; re-measure
   recall on the `harder` rows. *(retrieval)*
4. Warm the cache after re-ingest, or accept the cold cost until it warms; confirm
   the cache repopulates. *(cache)*
5. Invalidate cache entries for the changed documents (W10 tombstone → cache
   invalidation); never serve a cached answer for a tombstoned/updated source. *(cache)*
6. Re-run the entire golden set against one fixed `kb_version`; never aggregate
   across versions in a single reported run. *(process)*
7. Report tool success and escalation as `N/A (W13…)` / `N/A (W17…)`. *(reporting)*
8. Set thresholds just below the live baseline and record the rationale in the
   ADR. *(reporting)*

## 3. Defensible thresholds

**Rule:** run the live baseline, read each aggregate, set each bar a small margin
below it so a real regression trips the test but run-to-run judge noise doesn't;
record the number and the reason in the ADR.

Sam can't use 0.30. With a healthy baseline (~faithfulness 0.91, relevance 0.93,
precision 0.82, recall 0.88) sensible bars are ≈ 0.85 / 0.85 / 0.75 / 0.80 — but
the honest answer is *"I'd set them from my own clean baseline run, which I must
do first; until then these are placeholders, not defended numbers."* Reward the
**rule**, not the specific digits.

## 4. Model DR #2 statement

> "It's **not** ready for M2. The headline numbers are depressed by two real
> defects and a broken measurement process. First, retrieval quality dropped
> (precision 0.44, recall 0.58) after the re-ingest — I'd fix retrieval before
> anything else, because the low faithfulness is partly the model hallucinating
> when it isn't given the right context. Second, the cache is serving stale
> answers (hit accuracy below miss accuracy) — that's a correctness risk I'd
> invalidate immediately. The mixed `kb_version` run and floor-level thresholds
> mean the 'all green' is meaningless; I'll re-run against a single KB with
> baseline-set thresholds and report tool/escalation as N/A. Once retrieval and
> cache invalidation are fixed and the run is clean, I'll bring real numbers."

Top-two justification: fix **retrieval** first (it's upstream of faithfulness),
then **cache invalidation** (a live correctness hazard). Everything else is
reporting hygiene.

---

## Rubric (100 pts)

| Criterion | Pts | What "full marks" looks like |
|---|---|---|
| Diagnosis breadth | 30 | ≥ 6 of the 8 problems found, each with the right layer |
| Diagnosis depth | 20 | Causes are specific and name confirming evidence, not generic |
| Identifies process/reporting errors | 15 | Catches the mixed `kb_version`, the 0.0-not-N/A, and the floor thresholds |
| Prescriptions | 15 | Fixes are specific and target the right layer |
| Threshold reasoning | 10 | States the baseline-anchored rule (not just numbers); calls out the theatre |
| DR #2 paragraph | 10 | Clear ship/no-ship call with a defended top-two |

**Pass:** ≥ 60 and at least one process error caught. **Distinction:** ≥ 85 with
the retrieval-before-faithfulness ordering argued explicitly.

Common misses to watch for:
- Calling everything "the model is bad" and missing the retrieval/cache/process splits.
- Treating the 0.0 tool/escalation as a real failure instead of a reporting error.
- Proposing tidy thresholds without stating the baseline-anchored rule.
