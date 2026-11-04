# Week 11 Activity --- Diagnose the Broken Eval Report

**Application:** Enterprise Knowledge Assistant\
**Review:** M2 readiness assessment

## 1. Diagnosis

  -------------------------------------------------------------------------------------------
  \#             Symptom              Layer          Most likely cause     Evidence to
                                                                           confirm
  -------------- -------------------- -------------- --------------------- ------------------
  1              Faithfulness is      Generation     The prompt does not   Compare the
                 0.61; `g019`                        sufficiently enforce  generation prompt
                 confidently invents                 answering only from   with the last good
                 a 5% crypto match                   retrieved context or  run; inspect
                 that is not in the                  admitting when        `g019` and
                 documents.                          information is        graceful-refusal
                                                     unavailable.          case `g020`.

  2              Context precision is Retrieval      Retrieval is          Review W9
                 0.44; the top-3                     returning noisy top-K hybrid-search and
                 results for `g004`,                 results; hybrid       reranker
                 `g008` and `g011`                   weighting/reranking   configuration;
                 each contain two                    may have drifted, or  compare chunk
                 off-topic chunks.                   re-ingestion may have sizes before and
                                                     changed chunk sizes.  after
                                                                           re-ingestion.

  3              Context recall is    Retrieval      The second            Inspect the harder
                 0.58; `g015` answers                document/chunk needed multi-hop golden
                 the remote-work part                for this multi-hop    rows and check
                 but misses the                      question is not       whether both
                 in-person-meetings                  reaching the top-K    required sources
                 part (recall 0.33).                 results.              appear in
                                                                           retrieved context.

  4              Cache hit rate fell  Cache ---      Re-ingestion may have Check cache
                 from 65% to 12%;     volume         invalidated or        population after
                 cost and latency                    cleared cache         re-ingestion and
                 increased.                          entries, and the      whether
                                                     cache was not warmed  `--clear-cache`
                                                     after the update.     ran.

  5              Cache-hit accuracy   Cache ---      The cache is serving  Compare cached
                 is 0.70, below       correctness    stale answers because answers for
                 cache-miss accuracy                 invalidation did not  re-ingested
                 of 0.83.                            run for updated       documents with
                                                     documents.            current source
                                                                           content; inspect
                                                                           tombstone and
                                                                           invalidation
                                                                           events.

  6              One evaluation       Process        The knowledge base    Inspect each row's
                 contains rows tagged                changed during the    `kb_version` and
                 `v2.w10` and                        run, so the aggregate the re-ingestion
                 `v3.w11`.                           combines results from timestamps.
                                                     two different KB      
                                                     versions and is not a 
                                                     valid single-version  
                                                     evaluation.           

  7              Tool success rate    Process /      These capabilities    Check the
                 and escalation rate  reporting      are not applicable at course/ADR
                 are reported as                     this stage; reporting applicability
                 0.00.                               zero incorrectly      schedule: tool
                                                     implies they were     success is W13 and
                                                     measured and failed.  escalation is W17.

  8              All four RAGAS       Process /      The thresholds are    Review the
                 thresholds are 0.30, reporting      set too low to        threshold
                 so Sam declares                     provide meaningful    rationale and
                 every metric passed.                quality assurance     compare the
                                                     ("threshold           thresholds with a
                                                     theatre").            clean measured
                                                                           baseline.
  -------------------------------------------------------------------------------------------

## 2. Prescriptions

1.  **Generation:** Tighten the prompt to require answers based only on
    retrieved context and an explicit "I don't have enough information"
    response when evidence is absent; verify with `g019` and `g020`.
2.  **Retrieval:** Restore or retune W9 hybrid weighting and
    cross-encoder reranking; compare chunk sizes before and after
    re-ingestion.
3.  **Retrieval:** Increase top-K or add query expansion for multi-hop
    questions, then re-measure recall on the harder golden rows.
4.  **Cache:** Warm the cache after re-ingestion and confirm that
    entries repopulate; otherwise account for cold-cache cost and
    latency until it warms.
5.  **Cache:** Apply W10 tombstone-based invalidation to changed
    documents; never serve cached answers tied to updated or tombstoned
    sources.
6.  **Process:** Re-run the complete golden set against one fixed
    `kb_version`; do not aggregate results across KB versions.
7.  **Reporting:** Report tool success as `N/A (W13)` and escalation as
    `N/A (W17)`, rather than 0.00.
8.  **Reporting:** Establish thresholds from a clean baseline, set each
    bar slightly below its measured value to allow for normal judge
    variation while catching regressions, and record the values and
    rationale in the ADR.

## 3. Defensible thresholds

Sam's 0.30 thresholds are not defensible because they allow weak results
to pass. The rule should be to run a clean baseline against one fixed KB
version, measure each metric, and set its threshold a small margin below
that baseline so genuine regressions are detected without failing on
normal run-to-run judge variation. Record the selected values and
rationale in the ADR.

  RAGAS metric          Illustrative healthy baseline   Placeholder threshold
  ------------------- ------------------------------- -----------------------
  Faithfulness                                   0.91                    0.85
  Answer relevance                               0.93                    0.85
  Context precision                              0.82                    0.75
  Context recall                                 0.88                    0.80

These are illustrative placeholders, not defended acceptance criteria
for Sam's system. Sam must first run his own clean baseline and finalise
thresholds from those measured results.

## 4. DR #2 --- Design review statement

The Enterprise Knowledge Assistant is **not ready for M2 release**. The
results show real quality defects as well as problems with the
evaluation process. First, I would fix retrieval quality: context
precision is 0.44 and context recall is 0.58, meaning irrelevant chunks
are being retrieved and required information is being missed. Retrieval
comes before generation, so poor retrieval can contribute to
hallucinations and incomplete answers. Second, I would fix cache
invalidation immediately because cache-hit accuracy (0.70) is lower than
cache-miss accuracy (0.83), indicating that stale answers may be served
after source documents change. I would then rerun the complete golden
set against one fixed KB version, report tool success and escalation as
N/A at this stage, and establish thresholds from a clean baseline. I
would bring the assistant back for M2 approval only after retrieval and
cache correctness are fixed and the evaluation has been rerun with a
valid, defensible methodology.

## 5. Week 11 Practical Execution and Evaluation Results

### 5.1 Execution Environment

Successfully executed both Week 11 notebooks locally in Visual Studio Code.

- Python version: 3.12.10
- Virtual environment: `.venv-w7`
- Pydantic version: 2.13.5
- Golden dataset: `golden_set/capstone_v1.jsonl`
- Golden dataset size: 20 test cases
- Knowledge base version: `v2.w10`
- Evaluation mode: `offline-proxy`

The golden dataset contains:
- Happy-path cases: 14
- Harder cases: 4
- Edge cases: 2

### 5.2 RAG Evaluation Results

Notebook 1 successfully loaded and validated the golden dataset, constructed evaluation rows, and demonstrated the four evaluation metrics.

| RAG Evaluation Metric | Observed Score |
|---|---:|
| Faithfulness | 0.925 |
| Answer Relevance | 0.731 |
| Context Precision | 0.667 |
| Context Recall | 0.944 |

The lowest faithfulness scores were observed for:
- `g005`: 0.318 – Happy-path case with degraded retrieval.
- `g015`: 0.556 – Harder multi-hop retrieval case.
- `g019`: 0.630 – Edge case requiring a graceful refusal.

These cases highlight the importance of retrieval quality, evidence grounding, and appropriate refusal behaviour.

**Evaluation limitation:** The notebooks were run in offline-proxy mode. These scores are deterministic token-overlap proxy measurements, not actual RAGAS evaluation scores. A live evaluation run is required to obtain genuine RAGAS measurements.

### 5.3 Eight-KPI Evaluation Dashboard

Notebook 2 generated the following KPI results:

| KPI | Observed Result |
|---|---:|
| Task success rate | 80% |
| Grounded response rate | 92.52% |
| Hallucination rate | 7.48% |
| Retrieval hit rate | 66.67% |
| Tool success rate | N/A – Week 13 |
| Cost per query | USD 0.000171 |
| Latency P50 / P95 | 184 / 785 ms |
| Escalation rate | N/A – Week 17 |

Tool success and escalation are reported as N/A because these capabilities are scheduled for later course modules. Reporting them as zero would incorrectly imply that they were measured and failed.

### 5.4 Cache Evaluation

The evaluation also generated the following cache-related measurements:

| Cache KPI | Observed Result |
|---|---:|
| Cache hit rate | 65% |
| Cache-hit accuracy | 84.62% |
| Cache-miss accuracy | 71.43% |

The observed cache-hit accuracy was higher than cache-miss accuracy in this evaluation. This is an observed association and does not establish that caching itself improves answer quality; query characteristics and sample sizes should also be considered.

### 5.5 Threshold Evaluation

The notebook demonstrated the following threshold configuration:

| RAG Metric | Observed Score | Threshold | Result |
|---|---:|---:|---|
| Faithfulness | 0.925 | 0.85 | PASS |
| Answer Relevance | 0.731 | 0.85 | FAIL |
| Context Precision | 0.667 | 0.75 | FAIL |
| Context Recall | 0.944 | 0.80 | PASS |

Two metrics passed and two failed.

This demonstrates how evaluation thresholds can identify areas requiring improvement. However, because the current results are offline proxies, these pass/fail outcomes are illustrative and should not be treated as final production acceptance criteria. Thresholds should be validated using live evaluation results.

### 5.6 SQLite Results Validation

The Notebook 2 execution created a local SQLite database:

`W11_Package/Demo_Files/results.db`

The database contains an `eval_results` table with 20 evaluation records.

The table captures:
- Run label
- Knowledge base version
- Golden test case ID
- Cache-hit indicator
- Latency
- Query cost
- Record creation timestamp

The database validation confirmed:
- Run label: `wk11-baseline`
- Knowledge base version: `v2.w10`
- Total evaluation records: 20
- Cache hits: 13
- Average latency: 394.35 ms
- Average cost per query: USD 0.000171

The average latency stored in SQLite is a different statistic from the P50/P95 latency reported in the dashboard. These values are therefore not contradictory.

The database stores per-query operational evaluation data; it does not separately store all four aggregate RAG evaluation metrics or the complete KPI dashboard.

**Note:** `results.db` is retained locally and is not included in the GitHub repository.

### 5.7 Key Learnings

The Week 11 practical exercises provided hands-on experience with:

1. Building and validating a golden evaluation dataset.
2. Understanding faithfulness, answer relevance, context precision, and context recall.
3. Using an evaluation harness to assess RAG responses.
4. Understanding LLM-as-a-Judge scoring and mandatory success criteria.
5. Designing an eight-KPI evaluation dashboard.
6. Evaluating cache hit rate, cache-hit accuracy, and cache-miss accuracy.
7. Configuring metric thresholds and identifying failed quality checks.
8. Persisting per-query evaluation results in SQLite.
9. Distinguishing offline-proxy evaluation from actual live RAGAS measurements.
10. Recognising the importance of consistent knowledge base versioning and reproducible evaluation.

**Overall outcome:** Both Week 11 notebooks were executed successfully. The exercises demonstrated how to evaluate RAG system quality, monitor operational KPIs, assess caching behaviour, and persist evaluation results for subsequent analysis. Live RAGAS evaluation remains a separate step before treating these baseline measurements as production-quality evidence.