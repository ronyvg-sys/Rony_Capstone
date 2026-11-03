# AI-RAG · Week 11 Activity
## Diagnose the broken eval report

> **~60 minutes · individual, discussed in pairs · preps DR #2 ("defend your numbers")**
>
> This week you learned to *produce* an eval. This activity is about *reading*
> one. Below is a real-looking W11 snapshot from a fictional teammate, "Sam".
> Every number is plausible and several are alarming. Your job is to diagnose
> what's wrong — which layer each problem implicates — prescribe a fix, and set
> thresholds Sam should have used. There is no code to write.

---

## Sam's snapshot (the artefact under review)

> *wk11-snapshot.md — Enterprise Knowledge Assistant — "all green, shipping it"*

**8-KPI dashboard** · eval mode: live RAGAS

| # | KPI | Value |
|---|---|---|
| 1 | Task success rate | 0.55 |
| 2 | Grounded response rate | 0.61 |
| 3 | Hallucination rate | 0.39 |
| 4 | Retrieval hit rate (context precision) | 0.44 |
| 5 | Tool success rate | 0.00 |
| 6 | Cost / query | $0.000402 |
| 7 | Latency p50 / p95 | 690 / 1,180 ms |
| 8 | Escalation rate | 0.00 |

**RAGAS metrics:** faithfulness 0.61 · answer relevance 0.74 · context precision
0.44 · context recall 0.58

**Cache-aware:** hit rate 12% · cache-hit accuracy 0.70 · cache-miss accuracy 0.83

**KB version evaluated:** rows tagged `v2.w10` *and* `v3.w11` (Sam re-ingested
three documents halfway through the run)

**Thresholds used:** faithfulness ≥ 0.30, relevance ≥ 0.30, precision ≥ 0.30,
recall ≥ 0.30 — *"all passed ✅"*

**Sam's note:** *"Tests are green, cost is fine, calling it done for M2."*

Per-row lowlights Sam pasted:
- `g019` (crypto benefit, not in docs): answer confidently described a 5% crypto
  match. Faithfulness 0.20.
- `g015` (remote work × in-person meetings, multi-hop): answer covered remote
  work only; the meetings half was missing. Recall 0.33.
- `g004`, `g008`, `g011`: answers correct, but the retrieved top-3 each contained
  two off-topic chunks. Precision ~0.33 each.
- Several repeated questions that hit the cache last week now miss.

---

## Your tasks

### 1. Diagnose (the core of the exercise)

For each problem you find, fill a row:

| Symptom (which number) | Layer it implicates (retrieval / generation / cache / process) | Most likely cause | Evidence you'd pull to confirm |
|---|---|---|---|

Find **at least six** distinct problems. They are not all about model quality —
some are retrieval, some are caching, and some are *process/reporting* errors in
how Sam ran or wrote up the eval.

### 2. Prescribe

For each diagnosed problem, give a **one-line fix** and say which layer it
touches. Be specific ("tighten the 'answer only from context' instruction in the
generation prompt" — not "improve the prompt").

### 3. Set defensible thresholds

Sam's thresholds are tutorial defaults. Propose the thresholds Sam *should* set,
and state the rule you used to pick them. (You won't have Sam's true baseline —
state the rule and a sensible placeholder, and say what you'd measure to finalise.)

### 4. The one-paragraph DR #2 statement

Write the paragraph Sam should say at the design review: is this assistant ready
to ship for M2? What are the top two things to fix first, and why those two? This
is exactly the muscle DR #2 tests.

---

## Deliverable

A single markdown file `wk11-activity-<yourname>.md` with the four sections
above. ~1 page. Bring it to the pairing discussion.

## Hints (use only if stuck)

- Walk the four-metric table from `docs/eval/README.md`: each low metric points
  at a layer.
- The cache section has *two* separate problems hiding in it — one about volume,
  one about correctness.
- Two of the "KPIs" should not be numbers at all this week.
- A test suite that passes only because the bar is on the floor hasn't tested
  anything.
