"""src/debug/scenarios.py — the W12 debugging drill: six broken RAG queries.

Each scenario runs the pipeline with exactly one stage broken. The learner reads
the trace, classifies the failure into one of the four taxonomy buckets, and
names the fix. The bucket / root_cause / fix below are the answer key — revealed
by the drill only after a correct classification.

Four buckets (the taxonomy):
    retrieval  — the right chunk wasn't retrieved (precision or recall)
    generation — right chunks retrieved, but the LLM answered wrong / hallucinated
    prompt     — the prompt itself is wrong (e.g. missing the grounding instruction)
    infra      — the pipeline broke (timeout, API error, stale cache)
"""
from __future__ import annotations

from dataclasses import dataclass

BUCKETS = ("retrieval", "generation", "prompt", "infra")


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    question_id: str          # which golden question to run it on
    symptom: str              # what the learner is told up front
    bucket: str               # ANSWER KEY — the correct taxonomy bucket
    root_cause: str           # ANSWER KEY — what actually went wrong
    fix: str                  # ANSWER KEY — the smallest correct fix
    trace_tell: str           # ANSWER KEY — the outlier to spot in the trace


SCENARIOS: list[Scenario] = [
    Scenario(
        id="S1",
        title="The multi-hop answer is missing half",
        question_id="g015",
        symptom="The answer covers remote-work days but says nothing about the in-person meeting requirement.",
        bucket="retrieval",
        root_cause="Recall miss: the second required chunk (the in-person-meetings hop) was never retrieved, so the model couldn't answer it.",
        fix="Raise top-K or add query expansion for multi-hop questions so both required chunks reach the context.",
        trace_tell="In retrieve, only the '-a' chunk is present; the '-b' (second hop) chunk is absent and distractors fill the top-K.",
    ),
    Scenario(
        id="S2",
        title="The answer is about the office kitchen",
        question_id="g004",
        symptom="The answer is fluent but talks about kitchens/parking instead of the BYOD policy that was asked about.",
        bucket="retrieval",
        root_cause="Precision failure: distractor chunks were scored highest and pushed the correct chunk out of the top-K, so generation had only noise to work from.",
        fix="Retune hybrid weighting / the reranker (or reduce chunk size) so relevant chunks outrank distractors.",
        trace_tell="In retrieve/rerank, the top chunk_ids are 'kb-*' distractors with high scores; the relevant chunk is ranked last or missing.",
    ),
    Scenario(
        id="S3",
        title="A confident fact that isn't in the docs",
        question_id="g001",
        symptom="The answer is mostly right but adds a specific claim (a 150%-of-salary cash-out) that no policy contains.",
        bucket="generation",
        root_cause="Hallucination: retrieval was correct, but the model asserted a fact absent from the retrieved context.",
        fix="Lower temperature and/or tighten the prompt's grounding constraint; the retrieval layer is fine.",
        trace_tell="retrieve is healthy (correct '-a'/'-b' chunks, good scores) but the answer contains a claim not present in any chunk.",
    ),
    Scenario(
        id="S4",
        title="An extra step nobody asked for",
        question_id="g007",
        symptom="The security-incident answer is correct but tacks on 'post it in the public #general Slack channel', which is not policy.",
        bucket="prompt",
        root_cause="The prompt template lost its 'answer only from context' instruction, so the model felt free to add unsupported steps.",
        fix="Restore the grounding instruction in the prompt template.",
        trace_tell="In prompt, has_grounding_instruction is false; the answer then includes content not in the context.",
    ),
    Scenario(
        id="S5",
        title="A fluent answer to a different question",
        question_id="g010",
        symptom="Asked about working from home, the answer describes standard working hours instead — fluent, but off-topic.",
        bucket="infra",
        root_cause="Stale cache: a cache hit returned a previously-cached answer for a different question (key collision / not invalidated), so retrieve and generate never ran.",
        fix="Fix the cache key / invalidate stale entries (tie invalidation to the W10 tombstone + kb_version flow).",
        trace_tell="cache shows cache_hit=true with cached_for_question=g003, and the retrieve/generate stages are skipped entirely.",
    ),
    Scenario(
        id="S6",
        title="No answer at all",
        question_id="g008",
        symptom="The request returns an error instead of an answer, and it was slow before failing.",
        bucket="infra",
        root_cause="Infrastructure failure: the generation model call timed out (30s) and there was no retry, so nothing came back.",
        fix="Add a retry with backoff and a timeout budget; check model/API health and latency.",
        trace_tell="The generate stage is marked failed (✗) with error 'timeout after 30000ms' and a 30000ms latency.",
    ),
]

_BY_ID = {s.id: s for s in SCENARIOS}


def get(scenario_id: str) -> Scenario:
    if scenario_id not in _BY_ID:
        raise KeyError(f"unknown scenario {scenario_id!r}; try one of {list(_BY_ID)}")
    return _BY_ID[scenario_id]


def grade(scenario_id: str, guess_bucket: str) -> tuple[bool, str]:
    """Check a learner's bucket classification. Returns (correct, message)."""
    s = get(scenario_id)
    guess = (guess_bucket or "").strip().lower()
    if guess not in BUCKETS:
        return False, f"'{guess_bucket}' is not a bucket. Pick one of: {', '.join(BUCKETS)}."
    if guess == s.bucket:
        return True, (f"✓ Correct — {s.bucket}.\n"
                      f"  Root cause: {s.root_cause}\n"
                      f"  Fix:        {s.fix}")
    return False, (f"✗ Not {guess}. Re-read the trace — hint: look at the "
                   f"'{_hint_stage(s.bucket)}' stage.")


def _hint_stage(bucket: str) -> str:
    return {"retrieval": "retrieve/rerank", "generation": "generate",
            "prompt": "prompt", "infra": "cache/generate"}[bucket]
