# DR #2 — <Your Name> — Retrieval + KB Lifecycle Defense

> One page (or 5 slides). You get 5 minutes to present, then two peers challenge
> you, then the instructor synthesises, then you commit an ADR update live.
> Score is on the 5-dimension rubric — each section below maps to a dimension.

## 1. Problem framing  *(rubric: Problem framing)*
_What does your assistant do, for whom, and under what constraints? One or two
sentences. Why is RAG the right approach here vs. fine-tuning / a plain LLM?_

## 2. Retrieval choices  *(rubric: Trade-off articulation)*
_Why hybrid (dense + BM25) and these weights? Why this reranker and top-K? What
did you try and reject, and what does the KPI evidence say?_
- Hybrid weighting: _<value + why>_
- Reranker + top-K: _<value + why>_
- Alternatives considered: _<…>_

## 3. KB lifecycle  *(rubric: Failure handling)*
_How do documents get updated/deleted without breaking eval reproducibility?_
- Tombstone policy: _<…>_
- Update workflow (link the runbook): _<…>_
- `kb_version` + cache invalidation: _<…>_

## 4. The 8-KPI dashboard  *(rubric: KPI reporting)*
_All 8 KPIs with the wk6→wk12 trajectory. Call out the two honest N/As._
- Paste/summarise `docs/kpi/wk12-snapshot.md` (8 KPIs + trend).

## 5. Open trade-offs & questions  *(rubric: ADR quality)*
_Where would you push with more time? What are you unsure about? What ADR
decision might change? (Shows the ADR is a living artifact.)_
- Open trade-off: _<…>_
- Open question for reviewers: _<…>_
