# Week 9 Precision Delta - Structure-Aware Index Evaluation

## Objective

Compare dense retrieval with hybrid retrieval and cross-encoder reranking using the same ten golden questions and the current manually reviewed relevance labels.

- Week 9 embedding index: `data/w9_embeddings_small.json`
- Relevance labels: `data/w9_relevance_labels.jsonl`
- Results artifact: `data/w9_precision_results.json`
- Baseline: Dense retrieval using the Week 9 embedding index
- Week 9 method: Dense retrieval + BM25 + Reciprocal Rank Fusion (RRF) + cross-encoder reranking

## Results

| Metric | Dense baseline | Hybrid + reranking | Delta |
|---|---:|---:|---:|
| Average Precision@3 | 0.533 | 0.633 | +0.100 (+10.0 percentage points) |
| Average Precision@5 | 0.380 | 0.440 | +0.060 (+6.0 percentage points) |

## Question-level comparison

| Question | Dense P@3 | Hybrid + rerank P@3 | Observation |
|---|---:|---:|---|
| q01 | 0.667 | 1.000 | Improved after relevance-label review |
| q02 | 0.667 | 1.000 | Improved |
| q03 | 0.333 | 0.667 | Improved |
| q04 | 0.333 | 0.667 | Improved |
| q05 | 0.667 | 0.667 | Unchanged after relevance-label review |
| q06 | 0.667 | 0.333 | Regressed; reranking weakness identified |
| q07 | 0.333 | 0.333 | Unchanged |
| q08 | 0.667 | 0.667 | Unchanged |
| q09 | 0.333 | 0.333 | Unchanged; second relevant chunk demoted |
| q10 | 0.667 | 0.667 | Unchanged |

## Interpretation

Hybrid retrieval and cross-encoder reranking improved average Precision@3 by 0.100, or 10.0 percentage points. Average Precision@5 improved by 0.060, or 6.0 percentage points.

The largest Precision@3 improvements occurred for q01, q02, q03, and q04. For q01, the relevance labels were updated after source-text review confirmed that `project_status_report::chunk-0` states that R-001 remains the top project risk. The q01 top three now all contain labelled relevant chunks. Q05's relevance labels were also reviewed and updated because the project overview independently supports the project objective.

Q06 regressed: both relevant risk-register chunks were available before reranking, but the cross-encoder demoted them to final ranks 3 and 5. For q09, the testing-status chunk remained first, while the other labelled relevant chunk moved from candidate rank 3 to final rank 5.

These findings suggest that the overall hybrid approach improves retrieval precision on this ten-question set, but some query-specific reranking weaknesses remain. The metrics measure chunk relevance, not generated-answer correctness.

## Limitations and follow-up

- The evaluation contains ten golden questions, so the results are an initial benchmark and may not generalize to a larger dataset.
- Q01 and Q05 relevance labels were reviewed against the source text and updated where the source supported additional relevant evidence. Interpret the metrics using the current labels in `data/w9_relevance_labels.jsonl`.
- Precision@k measures the proportion of retrieved chunks labelled relevant among the first k results.
- The Q06 and Q09 diagnostics identify ranking weaknesses; they do not establish generation failures.
- Add regression tests for direct risk-severity questions and current testing-status questions before changing the retrieval or reranking implementation.
- Re-run the evaluation after any further label or implementation changes and retain the resulting metrics.

## Results artifact

Detailed per-question results are stored in `data/w9_precision_results.json`.