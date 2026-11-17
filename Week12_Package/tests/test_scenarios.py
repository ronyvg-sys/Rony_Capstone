"""tests/test_scenarios.py — the drill is only useful if each broken scenario
actually reproduces the failure it claims, deterministically. These tests are
what smoke_test.sh runs to guarantee that. Offline, no API key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.pipeline import load_golden, run_query
from src.debug.scenarios import SCENARIOS, BUCKETS, get, grade

GOLDEN = load_golden()


def _trace(scenario_id):
    s = get(scenario_id)
    return s, run_query(GOLDEN[s.question_id], scenario_id=scenario_id, golden=GOLDEN)


def test_healthy_answer_is_correct_and_grounded():
    # A healthy run of the same questions must return the ideal answer.
    for qid in ("g001", "g004", "g007"):
        tr = run_query(GOLDEN[qid], scenario_id="healthy", golden=GOLDEN)
        assert tr.answer == GOLDEN[qid]["ideal_answer"]
        assert tr.get("generate").ok is True
        assert tr.get("prompt").detail["has_grounding_instruction"] is True


def test_all_scenarios_render_a_trace():
    for s in SCENARIOS:
        _, tr = _trace(s.id)
        assert tr.stages, f"{s.id} produced no stages"
        assert tr.render()          # human-readable render works
        assert tr.to_json()         # json render works


def test_s1_recall_miss_second_hop_absent():
    s, tr = _trace("S1")
    ids = tr.get("retrieve").detail["chunk_ids"]
    assert f"{s.question_id}-b" not in ids           # the 2nd hop is missing
    assert f"{s.question_id}-a" in ids
    assert tr.answer != GOLDEN[s.question_id]["ideal_answer"]  # incomplete


def test_s2_precision_distractors_on_top():
    _, tr = _trace("S2")
    top_ids = tr.get("rerank").detail["order"]
    assert top_ids[0].startswith("kb-"), "a distractor should rank first"
    assert "kitchen" in tr.answer or "parking" in tr.answer or "picnic" in tr.answer


def test_s3_hallucination_with_healthy_retrieval():
    s, tr = _trace("S3")
    # retrieval is healthy...
    assert tr.get("rerank").detail["order"][0] == f"{s.question_id}-a"
    # ...but the answer adds an unsupported claim
    assert "150%" in tr.answer
    assert "150%" not in GOLDEN[s.question_id]["ideal_answer"]


def test_s4_prompt_lost_grounding_instruction():
    _, tr = _trace("S4")
    assert tr.get("prompt").detail["has_grounding_instruction"] is False
    assert "#general" in tr.answer                   # invented, unsupported step


def test_s5_stale_cache_hit_skips_pipeline():
    _, tr = _trace("S5")
    cache = tr.get("cache")
    assert cache.detail["cache_hit"] is True
    assert cache.detail["cached_for_question"] == "g003"
    assert tr.get("generate") is None                # generation skipped
    assert tr.answer == GOLDEN["g003"]["ideal_answer"]  # wrong-question answer


def test_s6_generation_error_no_answer():
    _, tr = _trace("S6")
    gen = tr.get("generate")
    assert gen.ok is False
    assert gen.latency_ms >= 30000
    assert "error" in tr.answer.lower()


def test_scenarios_cover_all_four_buckets():
    covered = {s.bucket for s in SCENARIOS}
    assert covered == set(BUCKETS), f"buckets missing: {set(BUCKETS) - covered}"


def test_grader_accepts_correct_and_rejects_wrong():
    for s in SCENARIOS:
        ok, _ = grade(s.id, s.bucket)
        assert ok, f"grader rejected the correct bucket for {s.id}"
        wrong = next(b for b in BUCKETS if b != s.bucket)
        ok2, _ = grade(s.id, wrong)
        assert not ok2, f"grader accepted a wrong bucket for {s.id}"
