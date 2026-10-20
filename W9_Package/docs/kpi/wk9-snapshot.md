Week 9 KPI Snapshot — Updated Evaluation



Evaluation setup



Golden questions: 10 (data/golden\_set\_full.jsonl)

Relevance labels: data/w9\_relevance\_labels.jsonl

Embedding index: data/w9\_embeddings\_small.json

Baseline: Dense retrieval using the Week 9 embedding index

Week 9 method: Dense retrieval + BM25 + Reciprocal Rank Fusion (RRF) + cross-encoder reranking

Results: data/w9\_precision\_results.json

Relevance labels: Manually reviewed against the source chunks; Q05 was updated to include the project overview chunk, and Q01 was updated to include project\_status\_report::chunk-0 after confirming that it identifies R-001 as the top project risk.



Updated retrieval metrics



| Metric | Dense baseline | Hybrid + reranking | Change |

|---|---:|---:|---:|

| Average Precision@3 | 0.533 (53.3%) | 0.633 (63.3%) | +0.100 (+10.0 percentage points) |

| Average Precision@5 | 0.380 (38.0%) | 0.440 (44.0%) | +0.060 (+6.0 percentage points) |

Interpretation



Hybrid retrieval and cross-encoder reranking improved average Precision@3 by 10.0 percentage points and average Precision@5 by 6.0 percentage points across the ten golden questions.

Question-level results show improvements in Precision@3 for q01, q02, q03, and q04. Q01 improved to Precision@3 of 1.000 after its relevance labels were updated to include the project status report chunk. Q05's relevance labels were also updated after the project overview chunk was confirmed to contain evidence equivalent to the project charter. q06 regressed from Precision@3 of 0.667 with dense retrieval to 0.333 with hybrid retrieval and reranking; the diagnostic showed that the cross-encoder demoted the relevant risk-register chunks. q07 and q09 remain at Precision@3 of 0.333.



The results support a positive overall retrieval improvement on this ten-question evaluation set, while also identifying question-specific ranking weaknesses. The dense baseline uses the Week 9 embedding index; these results are not a direct comparison against the original Week 8 index.



Limitations



Results use the structure-aware Week 9 chunk and embedding index and the current manually reviewed relevance labels.

Q01 and Q05 relevance labels were updated after source-text review. The latest metrics should be interpreted using these revised labels.

Precision measures the relevance of retrieved chunks, not the correctness of generated answers.

Q06 and Q09 diagnostics indicate ranking weaknesses; these results alone do not establish generation failures.

The evaluation contains only ten questions, so the results should be treated as an initial benchmark rather than proof that the improvement will generalize to a larger dataset.
