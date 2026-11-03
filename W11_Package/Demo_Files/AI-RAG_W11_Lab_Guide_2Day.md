# AI-RAG · Week 11 Lab Guide (Notebooks)
## RAG Evaluation (Applied) — the measure-it week, run interactively

W11 is delivered as **two runnable notebooks**. They contain the same evaluation code
as the package modules (`src/eval/*.py`), lifted verbatim into narrated cells so you
can run a cell, read a number, and explain it. Both run **offline** end-to-end — no
API key, no cost — using deterministic token-overlap *proxies*, and switch to **live
RAGAS** with one change.

| Notebook | Covers |
|---|---|
| **`AI-RAG_W11_Notebook_1.ipynb`** — The Four Metrics & RAGAS | the golden set → the four metric functions (offline + live) → the row-builder → the task-success judge |
| **`AI-RAG_W11_Notebook_2.ipynb`** — Eval as Code & the 8-KPI Dashboard | the 8-KPI dashboard → `results.db` (kb_version-tagged) → the baseline report → thresholds from a baseline |

Each notebook is **self-contained**: its setup cell writes the golden set locally and
forces the offline path, so it runs top-to-bottom on its own. Notebook 2 re-includes
the Notebook-1 helpers (under *Prerequisites*) so it also runs standalone.

---

## Before you start

```bash
pip install pydantic                 # the only dependency for the offline path
# for the LIVE path later:  pip install ragas datasets openai
jupyter lab                          # or open the .ipynb in VS Code / Cursor
```

Then, in each notebook: **Kernel → Restart & Run All**. Every cell should go green;
you'll see `faithfulness=0.925 (offline-proxy, n=20)`, the seeded dips, the 8-KPI
dashboard, and the persisted rows. (The notebooks ship already-executed so you can read
the outputs before running.)

> The offline numbers are **proxies**, labelled `offline-proxy` everywhere. They prove
> the wiring; they are **not** RAGAS numbers. Run live for the numbers you put in the
> snapshot and defend at M2.

---

## Notebook 1 — The Four Metrics & RAGAS

Work through the sections in order (they build on each other):

1. **The golden set** (`golden.py`). Run the load/validate cell — 20 entries,
   `g001..g020`, coverage `{happy, harder, edge}`. This is the ground truth every KPI
   is scored against; treat it as infrastructure.
2. **The four metrics** (`ragas_metrics.py`). Read the two paths: the offline proxies
   (deterministic, dependency-free) and the lazy live RAGAS calls. Note how each
   `MetricResult` carries its `mode` so a proxy is never mistaken for a real score.
3. **Build the rows** (`harness.py`). Run the build cell and find the **seeded
   failures** — `g019` hallucinates, `g015`/`g005` have retrieval misses. Real signal
   for the report to catch.
4. **Score the golden set.** Run `score_faithfulness` and read the lowest rows — the
   seeded dips should be at the bottom. Then `score_all` for the four aggregates.
5. **The task-success judge** (`judge.py`). It's live-only (needs a key), so the cell
   exercises its rule locally: KPI #1 counts an answer successful when
   accuracy ≥ 3 **and** groundedness ≥ 3 — a well-formatted wrong answer still fails.

**What to look for:** faithfulness and answer relevance read on the *answer*; context
precision and recall read on *retrieval*. A low score is a **first hypothesis** about
which layer to inspect — confirm before you fix (a low answer metric often has a
retrieval root cause, e.g. thin or wrong context).

**Checkpoint ✅** — all cells green; you can point to a low row and say which metric
moved and what you'd check first.

---

## Notebook 2 — Eval as Code & the 8-KPI Dashboard

1. **Prerequisites.** Run the setup + the three helper cells (golden, metrics,
   harness) — these are from Notebook 1 and make this notebook self-contained.
2. **The 8-KPI dashboard** (`kpi.py`). Run `compute_kpis` and read all eight rows plus
   the W11 extensions (the `kb_version` tag and the cache-hit vs cache-miss accuracy
   split). Note the two honest **N/A** rows — tool success (arrives W13) and escalation
   (arrives W17). `reportable_count` confirms 6 numeric + 2 N/A.

   *Definitions to be precise about:* faithfulness is claim-level (supported claims ÷
   total claims, averaged); grounded-response rate = faithfulness; KPI #3's
   `1 − faithfulness` is the **unsupported-claim density** (a claim-level proxy), not
   the share of hallucinated answers — the answer-level rate is higher. Report it as
   the proxy it is.
3. **Persist to `results.db`** (`init_results_db.py`). Run the write/read cells — 20
   rows logged, then a `GROUP BY kb_version`. This is what makes the snapshot
   reproducible without a live re-run, and why you **never aggregate across two
   kb_versions** in one number.
4. **The baseline report** (`run_eval.py`'s renderer). Run it to render the markdown
   report inline — note the offline **proxy banner** at the top.
5. **Thresholds from a baseline.** Run the threshold cell. Offline proxies won't all
   clear the live-set bars — that's expected; the point is the *wiring*. Live, you set
   each bar just below the real aggregate so a real regression trips it and judge noise
   doesn't.

**Checkpoint ✅** — dashboard renders with 6 numeric + 2 N/A; `results.db` has the
tagged rows; you can explain why a floor-level threshold tests nothing.

---

## Going live (once you want real numbers)

1. `pip install ragas datasets openai`
2. In each notebook's **setup cell**, delete the `os.environ["EVAL_OFFLINE"] = "1"`
   line and set your key: `os.environ["OPENAI_API_KEY"] = "sk-..."`.
3. Do a **5-question dry run** first (slice `rows[:5]`) to confirm the install and key
   before paying for all 20 × 4 metrics (~80 judge calls, ~$0.20–1.00).
4. Re-run. The `mode` flips to `live`, the proxy banner disappears, and these are the
   numbers for your snapshot. Live scores depend on the **judge model and RAGAS
   version** — record them alongside `kb_version` so a number stays comparable later.

---

## Done when…

- [ ] Both notebooks: **Restart & Run All** → all cells green, no errors.
- [ ] You can read the four metric aggregates and name which layer each reads on.
- [ ] The seeded failures (`g005`, `g015`, `g019`) surface as the lowest faithfulness rows.
- [ ] The 8-KPI dashboard shows 6 numeric + 2 honest N/A, tagged with `kb_version`.
- [ ] You've rendered the baseline report and seen the offline proxy banner.
- [ ] (Live, optional) a 5-question dry run, then a full live run for the snapshot.

## Notebook vs the pytest suite

These notebooks are where you **see and explain** the eval — run a cell, read a number,
talk to it. The one thing a notebook can't do is gate a deploy or run on every commit,
so the package keeps the *same* code as a **pytest suite** (`eval/test_*.py`) that runs
offline in CI and produces the live numbers on demand. Notebook to understand it; the
suite to enforce it. Next week (W12) is the eval regression runbook and **DR #2**, where
you present these numbers and defend your thresholds.
