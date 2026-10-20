Week 9 — Retrieval Failure Analysis

1. Purpose and method

This analysis investigates five questions selected from the Week 9 golden set based on their hybrid retrieval and reranking Precision@3 results. The evaluation uses the Week 9 index and the manually reviewed relevance labels in data/w9\_relevance\_labels.jsonl.

The current evaluation, using the Week 9 embedding index and manually reviewed relevance labels, reports average Precision@3 of 0.633 and Precision@5 of 0.440 for hybrid retrieval plus reranking. The dense baseline using the same Week 9 index reports Precision@3 of 0.533 and Precision@5 of 0.380. The five questions below were selected to investigate weaker individual Precision@3 results and compare them with the retrieved evidence.

Precision@3 measures the proportion of the first three retrieved chunks that are labelled relevant. It does not directly measure answer correctness. A question can receive a low Precision@3 while still having sufficient evidence to answer correctly.

Diagnostic categories

Retrieval failure: relevant evidence is missing from the retrieved candidates or ranked too low.

Reranking failure: relevant evidence was available among the candidates but was not ranked sufficiently high.

Generation failure: the answer is incorrect or unsupported despite sufficient retrieved evidence.

Question or corpus issue: the wording is ambiguous or the available documents do not contain sufficient evidence.

A category should only be assigned as a confirmed cause after checking the candidate list, source text, and generated answer.

2. Question-by-question analysis

Q01 - Top priority risk

Question: What is the top priority risk in Project ABC?

Expected keywords: R-001, Data migration, billing reconciliation

Hybrid + reranking Precision@3: 1.000

Manually labelled relevant chunks:

- risk_register::chunk-0
- risk_register::chunk-1
- meeting_minutes_2026_09_29::chunk-0
- project_status_report::chunk-0

Retrieved top three:

1. meeting_minutes_2026_09_29::chunk-0
2. risk_register::chunk-1
3. project_status_report::chunk-0

Evidence assessment: The meeting minutes, risk register, and project status report all identify R-001 as the top priority or top project risk. The risk register describes the risk as data migration and billing reconciliation delay, with critical severity because both probability and impact are high.

Diagnosis: All three retrieved chunks are included in the reviewed relevance labels. Therefore, Precision@3 is 1.000. The evidence supports identifying R-001 as the top priority risk. These retrieval results do not, by themselves, establish whether the generated answer is correct.

Recommended action: Retain the reviewed relevance labels and use the updated evaluation results. Continue checking relevance against source evidence rather than changing labels solely to improve a metric.

Q05 — Main project objective

Question: What is the main objective of the Single Billing Transformation project?

Expected keywords: Single Billing

Hybrid + reranking Precision@3: 0.667

Manually labelled relevant chunks:

- project_charter::chunk-0
- project_overview::chunk-0

Retrieved top three:

1. project_charter::chunk-0
2. project_overview::chunk-0
3. project_charter::chunk-1

Evidence assessment: The project charter describes the objective of consolidating multiple independent billing platforms into a single enterprise billing solution. The project overview independently describes replacing multiple independent billing systems with a centralized enterprise billing platform. Both chunks directly support the answer and are now labelled relevant.

Diagnosis: The earlier low Precision@3 was partly caused by an incomplete relevance label. After reviewing the source text and updating the label, both relevant chunks appear in the retrieved top three. The current results do not establish a generation failure or demonstrate that the reranker needs to be changed for this question.

Recommended action: Retain the reviewed relevance labels and use the updated evaluation results. Continue assessing retrieval quality against the actual source evidence rather than changing labels solely to improve a metric.

Q06 — Severity of R-001

Question: What is the severity of risk R-001?

Expected keywords: CRITICAL

Hybrid + reranking Precision@3: 0.333

Manually labelled relevant chunks:

risk\_register::chunk-0

risk\_register::chunk-1

Retrieved top three:

project\_status\_report::chunk-0

meeting\_minutes\_2026\_09\_15::chunk-0

risk\_register::chunk-1

Evidence assessment: The first two chunks discuss the risk but are not labelled relevant. The third chunk is labelled relevant and explicitly identifies R-001 as CRITICAL, explaining that both its probability and impact are HIGH.

\*\*Preliminary diagnosis:\*\* Both relevant risk-register chunks were present before reranking. `risk\_register::chunk-1` moved from rank 1 to rank 3, while `risk\_register::chunk-0` moved from rank 2 to rank 5. This indicates a reranking weakness because the cross-encoder pushed the chunk explicitly stating the risk severity lower in the results. The final top three still contain `risk\_register::chunk-1`, which provides the answer.

\*\*Recommended action:\*\* Investigate why the cross-encoder ranks general mentions of the risk above the direct severity evidence. Add a regression test for questions asking for a risk's severity, and check whether the expected relevant chunks remain in the top three before changing the ranking strategy.

Q07 — Project release dependencies

Question: What are the main dependencies for the Project ABC release?

Expected keywords: data migration, UAT, billing

Hybrid + reranking Precision@3: 0.333

Manually labelled relevant chunk: project\_dependencies::chunk-0

Retrieved top three:

project\_dependencies::chunk-0

project\_governance::chunk-0

resource\_plan::chunk-0

Evidence assessment: The dependencies chunk is ranked first and contains the release dependency list. The other two chunks are not labelled relevant for this question.

Preliminary diagnosis: The directly relevant evidence is ranked first. The low Precision@3 reflects two non-relevant chunks in positions 2 and 3, rather than a failure to retrieve the dependency list. The saved results alone do not establish whether those chunks are entirely unhelpful to the generated answer.

Recommended action: Inspect whether the second and third chunks provide useful supporting evidence. If they do not, investigate whether candidate selection or reranking can improve the remaining ranks without displacing the dependency list.

Q09 — Current testing activities

Question: What are the key testing activities currently in progress?

Expected keywords: UAT, testing

Hybrid + reranking Precision@3: 0.333

Manually labelled relevant chunks:

testing\_status::chunk-0

project\_status\_report::chunk-0

Retrieved top three:

testing\_status::chunk-0

meeting\_minutes\_2026\_09\_15::chunk-0

project\_status\_report\_previous::chunk-0

Evidence assessment: The testing status chunk is labelled relevant and reports that SIT is in progress, UAT preparation and criteria are being finalized, and performance testing is planned rather than currently in progress. The current project status report is labelled relevant but is not present in the top three. The other two retrieved chunks are not labelled relevant.

\*\*Preliminary diagnosis:\*\* `testing\_status::chunk-0` was ranked first before and after reranking, providing direct evidence about testing activities. However, `project\_status\_report::chunk-0` moved from candidate rank 3 to final rank 5, outside the final top three. This indicates a reranking weakness for the second labelled relevant chunk. The primary testing-status evidence remains ranked first.

\*\*Recommended action:\*\* Investigate why the cross-encoder ranks the older project status report above the current project status report. Add a regression test to check whether current testing-status and project-status evidence are retained in the top three. Keep planned testing activities distinct from activities currently in progress.

3. Patterns and conclusions

The results show that Precision@3 must be interpreted alongside the retrieved evidence and the manually reviewed relevance labels.

- Q01, Q05, and Q07 each retrieve a directly relevant chunk in the top three. Their Precision@3 scores do not by themselves indicate an answer failure.

- Q06 demonstrates a reranking weakness: both relevant risk-register chunks were present before reranking, but the cross-encoder moved them from candidate ranks 1 and 2 to final ranks 3 and 5.

- Q09 demonstrates a ranking weakness for the second relevant chunk: project_status_report::chunk-0 was candidate rank 3 but final rank 5. The primary testing-status chunk remained ranked first.

- Q01's relevance labels were updated after source-text review confirmed that `project_status_report::chunk-0` identifies R-001 as the top project risk. Its Precision@3 is now 1.000. Q05's relevance labels were also reviewed and updated after confirming that both `project_charter::chunk-0` and `project_overview::chunk-0` directly support the project objective; its Precision@3 remains 0.667.

These diagnostics identify ranking behavior, but they do not establish a generation failure. Generated answers should be assessed separately against the retrieved evidence.

4. Limitations and next actions

1. Retain the reviewed Q01 and Q05 relevance labels and ensure that subsequent evaluation results use the current labels in `data/w9_relevance_labels.jsonl`.

2. Re-run the evaluation after any justified label changes and retain the resulting metric.

3. Compare retrieved evidence with the actual generated answer before classifying an issue as a generation failure.

4. Add regression tests for direct risk-severity questions and current testing-status questions.

5. Record any subsequent retrieval or reranking changes and evaluate them against the same golden set.

The current metrics are based on ten questions. They are useful for identifying targeted improvements, but a larger and carefully reviewed evaluation set would be needed to establish whether the observed gains generalize.
