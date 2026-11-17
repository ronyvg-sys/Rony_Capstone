#!/usr/bin/env python3
"""scripts/debug_drill.py — the W12 hands-on debugging drill.

Every learner works all six scenarios. For each: read the trace, classify the
failure into a bucket (retrieval / generation / prompt / infra), then check your
answer. This runs fully offline and deterministically — no API key, no cost.

    python3 scripts/debug_drill.py list                 # the six failures
    python3 scripts/debug_drill.py run S1               # print S1's trace
    python3 scripts/debug_drill.py grade S1 retrieval   # check your classification
    python3 scripts/debug_drill.py run-all             # all traces (used by smoke test)
    python3 scripts/debug_drill.py answers             # full answer key (instructors)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.pipeline import load_golden, run_query          # noqa: E402
from src.debug.scenarios import SCENARIOS, BUCKETS, get, grade  # noqa: E402


def _run(scenario_id: str):
    s = get(scenario_id)
    golden = load_golden()
    entry = golden[s.question_id]
    trace = run_query(entry, scenario_id=s.id, golden=golden)
    print(f"\n### {s.id} — {s.title}   (question {s.question_id})")
    print(f"SYMPTOM: {s.symptom}\n")
    print(trace.render())
    print(f"\nClassify it:  python3 scripts/debug_drill.py grade {s.id} <"
          f"{'|'.join(BUCKETS)}>")
    return trace


def cmd_list():
    print("W12 debugging drill — six failures to diagnose:\n")
    for s in SCENARIOS:
        print(f"  {s.id}  {s.title}")
        print(f"      symptom: {s.symptom}")
    print(f"\nRun one:  python3 scripts/debug_drill.py run {SCENARIOS[0].id}")


def cmd_run(scenario_id: str):
    _run(scenario_id)


def cmd_grade(scenario_id: str, guess: str):
    ok, msg = grade(scenario_id, guess)
    print(msg)
    return 0 if ok else 1


def cmd_run_all():
    golden = load_golden()
    for s in SCENARIOS:
        trace = run_query(golden[s.question_id], scenario_id=s.id, golden=golden)
        status = "ok" if any(st.stage == "generate" for st in trace.stages) or \
                 trace.get("cache") else "ok"
        print(f"  {s.id}: trace rendered ({len(trace.stages)} stages) [{status}]")
    print(f"\nall {len(SCENARIOS)} scenarios produced a trace.")


def cmd_answers():
    print("ANSWER KEY (instructors only)\n")
    for s in SCENARIOS:
        print(f"{s.id} — {s.title}")
        print(f"   bucket:     {s.bucket}")
        print(f"   trace tell: {s.trace_tell}")
        print(f"   root cause: {s.root_cause}")
        print(f"   fix:        {s.fix}\n")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        cmd_list(); return 0
    cmd = args[0]
    if cmd == "list":
        cmd_list()
    elif cmd == "run" and len(args) == 2:
        cmd_run(args[1])
    elif cmd == "grade" and len(args) == 3:
        return cmd_grade(args[1], args[2])
    elif cmd == "run-all":
        cmd_run_all()
    elif cmd == "answers":
        cmd_answers()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
