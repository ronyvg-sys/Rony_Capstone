# DR #2 — EXAMPLE — Enterprise Knowledge Assistant — Retrieval + KB Lifecycle Defense

> Filled example for the capstone use case. Yours will differ; match the depth.

## 1. Problem framing
The assistant answers employees' questions about HR/IT/Finance policies from an
internal document corpus. Constraints: answers must be **grounded** (no invented
policy), cheap at scale, and safe when a topic isn't covered. RAG is the right
approach: the policy corpus changes often and must be cited — fine-tuning would
bake in stale facts and can't cite sources.

## 2. Retrieval choices  (trade-offs with KPI evidence)
- **Hybrid, BM25 weight 0.4.** Dense retrieval alone missed exact-term queries
  (policy codes, section numbers); adding BM25 raised retrieval hit rate. 0.4 was
  the point where hit rate peaked without precision dropping.
- **Cross-encoder rerank, top-K = 3.** Reranking the top candidates lifted context
  precision from ~0.7 to 0.85; top-K = 3 keeps the prompt small (cost) while
  covering multi-hop answers after the S1 recall fix.
- **Rejected:** dense-only (missed exact terms); top-K = 5 (added ~600 prompt
  tokens for no measurable quality gain).

## 3. KB lifecycle  (failure handling)
- **Tombstone policy:** deletes set `deleted_at` and are filtered from retrieval;
  we never hard-delete, so eval runs stay reproducible.
- **Update workflow:** full re-ingest, tombstone the old chunks, bump
  `kb_version` — see `docs/runbooks/rag_debugging.md` and the W10 update runbook.
- **Cache invalidation:** stale-cache is a real failure mode (drill S5); cache
  entries are invalidated on `kb_version` change. Cache-hit accuracy (0.92) stays
  above cache-miss accuracy (0.88), so the cache isn't serving stale answers.

## 4. The 8-KPI dashboard  (KPI reporting, with trend)
Task success **0.92**, grounded **0.92**, hallucination **0.08**, retrieval hit
**0.90**, cost **$0.000131**, latency **184/312 ms**; tool success and escalation
**N/A** (arrive W13 / W17). Full wk6→wk12 trajectory in `docs/kpi/wk12-snapshot.md`
— quality climbed across the build weeks and again at wk12 after a retrieval fix;
cost/latency dropped an order of magnitude at wk10.

## 5. Open trade-offs & questions
- **Open trade-off:** the semantic-cache threshold (0.95) was tuned on only 20
  golden questions; at real traffic I'd tune it against a measured false-hit rate.
- **Open question for reviewers:** is 20 golden questions enough to trust the KPI
  trend, or should the golden set grow before Phase 3 adds tool-use complexity?
