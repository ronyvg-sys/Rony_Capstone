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
