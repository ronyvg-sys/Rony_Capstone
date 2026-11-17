# Week 12 — RAG Debugging Drill Trace

## 1. Purpose

This document records the diagnosis of the six broken RAG scenarios (S1–S6) completed as part of the Week 12 Practice Assignment.

The exercise used the original Week 12 package in Vocareum:

`/voc/data/AI-RAG_W12`

Each scenario was investigated by running its trace, identifying the first stage where the pipeline failed, classifying the failure, and checking the diagnosis with the grading command.

## 2. Debugging approach

The scenarios were investigated using the following workflow:

1. **Reproduce** — run the scenario and inspect its trace.
2. **Narrow** — identify the first pipeline stage where the output is incorrect.
3. **Isolate** — classify the failure as retrieval, generation, prompt, or infrastructure.
4. **Fix** — identify the smallest corrective action.
5. **Verify** — run the scenario grading command.

The RAG pipeline stages examined were:

`Embed → Cache → Retrieve → Rerank → Prompt → Generate`

## 3. Scenario diagnosis summary

| Scenario | Symptom | Failure category | Root cause | Smallest fix |
|---|---|---|---|---|
| S1 — The multi-hop answer is missing half | The answer covers remote-work days but omits the in-person meeting requirement. | Retrieval | Recall miss: the second required chunk (the in-person-meetings hop) was never retrieved. | Raise top-K or add query expansion for multi-hop questions so both required chunks reach the context. |
| S2 — The answer is about the office kitchen | The answer discusses the kitchen/reception instead of the BYOD policy. | Retrieval | Precision failure: distractor chunks were scored highest and pushed the correct chunk out of the top-K. | Retune hybrid weighting or the reranker, or reduce chunk size, so relevant chunks outrank distractors. |
| S3 — A confident fact that isn't in the docs | The leave-policy answer adds an unsupported 150%-of-salary cash-out claim. | Generation | Hallucination: retrieval was correct, but the model asserted a fact absent from the retrieved context. | Lower temperature and/or tighten the prompt's grounding constraint; the retrieval layer is fine. |
| S4 — An extra step nobody asked for | The security-incident answer adds an unsupported instruction to post in the public `#general` Slack channel. | Prompt | The prompt template lost its “answer only from context” instruction, allowing an unsupported step to be added. | Restore the grounding instruction in the prompt template. |
| S5 — A fluent answer to a different question | Asked about working from home, the system returns standard working-hours information. | Infra | Stale cache: a cache hit returned an answer previously cached for a different question (`g003` rather than `g010`); retrieval and generation were skipped. | Fix the cache key and invalidate stale entries; tie invalidation to the tombstone and `kb_version` flow. |
| S6 — No answer at all | The request returns an error after approximately 30 seconds. | Infra | The generation model call timed out after 30 seconds and no retry was attempted. | Add retry with backoff and a timeout budget; check model/API health and latency. |

## 4. Trace evidence by scenario

### S1 — The multi-hop answer is missing half

- **Question ID:** `g015`
- **Trace evidence:** Retrieval returned `g015-a`, `kb-441`, and `kb-887`. The trace note stated that only the first hop was retrieved.
- **Diagnosis:** Retrieval recall failure. The second required chunk containing the in-person meeting requirement was missing from the retrieved context.
- **Fix:** Raise top-K or add query expansion for multi-hop questions.
- **Verification:** `python3 scripts/debug_drill.py grade S1 retrieval`
- **Result:** Correct — retrieval.

### S2 — The answer is about the office kitchen

- **Question ID:** `g004`
- **Trace evidence:** Retrieval returned `kb-441`, `kb-887`, and `kb-203`, with scores `0.9`, `0.85`, and `0.8`. The trace noted that the answer was generated from off-topic chunks.
- **Diagnosis:** Retrieval precision failure. Distractors outranked the relevant BYOD content, leaving generation with irrelevant context.
- **Fix:** Retune hybrid weighting or the reranker, or reduce chunk size.
- **Verification:** `python3 scripts/debug_drill.py grade S2 retrieval`
- **Result:** Correct — retrieval.

### S3 — A confident fact that isn't in the docs

- **Question ID:** `g001`
- **Trace evidence:** Retrieval returned `g001-a`, `g001-b`, and `kb-203`. The prompt included the grounding instruction. The generation trace noted that the answer added a claim not present in any retrieved chunk.
- **Diagnosis:** Generation hallucination. The answer introduced the unsupported claim that unused leave could be cashed out at 150% of salary.
- **Fix:** Lower temperature and/or tighten the grounding constraint. The retrieval layer did not need changing for this scenario.
- **Verification:** `python3 scripts/debug_drill.py grade S3 generation`
- **Result:** Correct — generation.

### S4 — An extra step nobody asked for

- **Question ID:** `g007`
- **Trace evidence:** Retrieval returned `g007-a`, `g007-b`, and `kb-441`. At the prompt stage, `has_grounding_instruction` was `false`.
- **Diagnosis:** Prompt failure. The prompt template was missing the instruction to answer only from the provided context.
- **Fix:** Restore the grounding instruction in the prompt template.
- **Verification:** `python3 scripts/debug_drill.py grade S4 prompt`
- **Result:** Correct — prompt.

### S5 — A fluent answer to a different question

- **Question ID:** `g010`
- **Trace evidence:** The cache stage reported `HIT`, `cache_hit: true`, and `cached_for_question: g003`. The trace stated that retrieval and generation were skipped.
- **Diagnosis:** Infrastructure/cache failure. A cached answer for a different question was returned.
- **Fix:** Fix the cache key and invalidate stale entries, using the tombstone and `kb_version` flow.
- **Verification:** `python3 scripts/debug_drill.py grade S5 infra`
- **Result:** Correct — infra.

### S6 — No answer at all

- **Question ID:** `g008`
- **Trace evidence:** Retrieval and prompt construction completed. The generation stage failed with `OpenAI timeout after 30000ms`; `retries: 0`.
- **Diagnosis:** Infrastructure failure. The model call timed out and the system did not retry.
- **Fix:** Add retry with backoff and a timeout budget; check model/API health and latency.
- **Verification:** `python3 scripts/debug_drill.py grade S6 infra`
- **Result:** Correct — infra.

## 5. Key learning points

### Retrieval: recall versus precision

- **S1 — Recall:** Required information was missing from the retrieved context.
- **S2 — Precision:** Irrelevant chunks were retrieved and ranked above the relevant content.

### Generation versus prompt

- **S3 — Generation:** The grounding instruction was present, but the model still introduced an unsupported claim.
- **S4 — Prompt:** The grounding instruction itself was missing from the prompt template.

### Infrastructure: cache versus timeout

- **S5 — Cache:** An incorrect cache hit returned an answer for another question and short-circuited the remaining pipeline.
- **S6 — Timeout:** The model call exceeded its timeout and no retry was attempted.

A fluent answer is not necessarily a correct answer. Trace inspection is needed to identify where the pipeline first went wrong.

## 6. Overall result

All six scenarios were run and graded individually. All six classifications were accepted by the grading script:

| Scenario | Submitted category | Grading result |
|---|---|---|
| S1 | retrieval | Correct |
| S2 | retrieval | Correct |
| S3 | generation | Correct |
| S4 | prompt | Correct |
| S5 | infra | Correct |
| S6 | infra | Correct |

**Final result: 6/6 scenarios correctly classified.**

## 7. Commands used

Run these commands from the Week 12 package directory:

```bash
cd /voc/data/AI-RAG_W12

# List the six scenarios
python3 scripts/debug_drill.py list

# Run an individual scenario
python3 scripts/debug_drill.py run S1

# Grade an individual diagnosis
python3 scripts/debug_drill.py grade S1 retrieval
```

The scenario ID and category should be changed as appropriate for each scenario.

## 8. Scope note

This document records completion of the six-scenario Week 12 debugging drill. It does not claim that the separate Capstone Milestone 2 implementation has been completed. Capstone M2 work is being kept separate and deferred until its project-specific materials are available.
