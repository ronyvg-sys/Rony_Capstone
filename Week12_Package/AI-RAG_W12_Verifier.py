#!/usr/bin/env python3
"""W12 Verifier — RAG Debugging Lab (M2).

Runs OFFLINE checks for the W12 deliverables:
- the staged pipeline + trace + scenarios import and run
- the debugging drill: 6 scenarios, all render, cover the 4 taxonomy buckets,
  each reproduces its intended failure, and the grader works
- M2 docs: failure taxonomy, debugging runbook, wk12 KPI snapshot (8 KPIs +
  trajectory + commentary), ADR v2 (M2) consolidation, DR #2 one-pager
- smoke_test.sh, pytest.ini plugin guard, requirements, .env, Lab Guide

Run from the package root:  python3 AI-RAG_W12_Verifier.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

PASS, FAIL, SKIP = "✓", "✗", "○"
results: list[tuple[str, str]] = []


def step(sid: str, verdict: str, detail: str = "") -> None:
    results.append((verdict, sid))
    icon = {PASS: "\033[32m✓\033[0m", FAIL: "\033[31m✗\033[0m", SKIP: "\033[33m○\033[0m"}[verdict]
    print(f"  {icon} {sid}: {detail}" if detail else f"  {icon} {sid}")


def section(t: str) -> None:
    print(f"\n── {t} ──")


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text() if p.exists() else ""


# ═══ A · Files & imports ═════════════════════════════════════════════════
section("A · Files present & offline imports")

EXPECTED = [
    "src/rag/pipeline.py", "src/rag/trace.py", "src/debug/scenarios.py",
    "scripts/debug_drill.py", "scripts/m2_check.py", "tests/test_scenarios.py",
    "golden_set/capstone_v1.jsonl",
    "docs/debugging/rag_failure_taxonomy.md", "docs/runbooks/rag_debugging.md",
    "docs/kpi/wk12-snapshot.md", "docs/adr/0001-capstone-framing.md",
    "docs/dr/dr2-summary-template.md", "docs/dr/dr2-summary-EXAMPLE.md",
    "smoke_test.sh", "pytest.ini", "requirements.txt", ".env.example",
    "AI-RAG_W12_Lab_Guide.md",
]
missing = [f for f in EXPECTED if not (ROOT / f).exists()]
step("A1", FAIL if missing else PASS,
     f"missing: {missing}" if missing else f"all {len(EXPECTED)} files present")

try:
    from src.rag.pipeline import run_query, load_golden
    step("A2", PASS, "pipeline imports (run_query, load_golden)")
except Exception as e:
    step("A2", FAIL, str(e)); run_query = None

try:
    from src.rag.trace import Trace, StageRecord
    t = Trace("q"); t.add("embed", "x"); ok = bool(t.render()) and bool(t.to_json())
    step("A3", PASS if ok else FAIL, "trace imports + renders")
except Exception as e:
    step("A3", FAIL, str(e))

try:
    from src.debug.scenarios import SCENARIOS, BUCKETS, get, grade
    step("A4", PASS if len(SCENARIOS) == 6 else FAIL, f"{len(SCENARIOS)} scenarios (expect 6)")
except Exception as e:
    step("A4", FAIL, str(e)); SCENARIOS = []

drill = _read("scripts/debug_drill.py")
step("A5", PASS if all(k in drill for k in ("list", "run", "grade", "run-all")) else FAIL,
     "debug_drill has list/run/grade/run-all")

try:
    G = load_golden()
    step("A6", PASS if len(G) == 20 else FAIL, f"golden set {len(G)} entries (expect 20)")
except Exception as e:
    step("A6", FAIL, str(e)); G = {}


# ═══ B · Drill mechanics ═════════════════════════════════════════════════
section("B · Debugging drill mechanics")

traces = {}
if run_query and SCENARIOS and G:
    try:
        for s in SCENARIOS:
            traces[s.id] = run_query(G[s.question_id], scenario_id=s.id, golden=G)
        step("B7", PASS if len(traces) == 6 else FAIL, f"{len(traces)}/6 scenarios render a trace")
    except Exception as e:
        step("B7", FAIL, str(e))

    covered = {s.bucket for s in SCENARIOS}
    step("B8", PASS if covered == set(BUCKETS) else FAIL,
         f"buckets covered: {sorted(covered)}")

    healthy = run_query(G["g001"], scenario_id="healthy", golden=G)
    step("B9", PASS if healthy.answer == G["g001"]["ideal_answer"] else FAIL,
         "healthy run returns the correct grounded answer")

    good = all(grade(s.id, s.bucket)[0] for s in SCENARIOS)
    step("B10", PASS if good else FAIL, "grader accepts the correct bucket for all 6")

    wrong_ok = all(not grade(s.id, next(b for b in BUCKETS if b != s.bucket))[0]
                   for s in SCENARIOS)
    step("B11", PASS if wrong_ok else FAIL, "grader rejects a wrong bucket")


# ═══ C · Each scenario reproduces its failure ════════════════════════════
section("C · Scenarios reproduce their failures")

if traces:
    t1 = traces["S1"]
    step("C12", PASS if "g015-b" not in t1.get("retrieve").detail["chunk_ids"] else FAIL,
         "S1 recall miss: 2nd hop chunk absent")

    t2 = traces["S2"]
    step("C13", PASS if t2.get("rerank").detail["order"][0].startswith("kb-") else FAIL,
         "S2 precision: distractor ranked top")

    t3 = traces["S3"]
    step("C14", PASS if ("150%" in t3.answer and "150%" not in G["g001"]["ideal_answer"]) else FAIL,
         "S3 hallucination: unsupported claim in answer")

    t4 = traces["S4"]
    step("C15", PASS if (t4.get("prompt").detail["has_grounding_instruction"] is False
                         and "#general" in t4.answer) else FAIL,
         "S4 prompt: grounding dropped + invented step")

    t5 = traces["S5"]
    c5 = t5.get("cache")
    step("C16", PASS if (c5.detail["cache_hit"] and c5.detail["cached_for_question"] == "g003"
                         and t5.get("generate") is None) else FAIL,
         "S5 stale cache: hit for g003, generate skipped")

    t6 = traces["S6"]
    g6 = t6.get("generate")
    step("C17", PASS if (g6.ok is False and g6.latency_ms >= 30000) else FAIL,
         "S6 infra: generation error + latency spike")


# ═══ D · M2 docs ═════════════════════════════════════════════════════════
section("D · M2 documents")

tax = _read("docs/debugging/rag_failure_taxonomy.md").lower()
step("D18", PASS if all(b in tax for b in ("retrieval", "generation", "prompt", "infra")) else FAIL,
     "taxonomy names all 4 buckets")

rb = _read("docs/runbooks/rag_debugging.md").lower()
step("D19", PASS if all(k in rb for k in ("reproduce", "narrow", "isolate", "fix", "verify")) else FAIL,
     "runbook has the 5-step workflow")

import re
snap = _read("docs/kpi/wk12-snapshot.md")
rows = all(re.search(rf"^\|\s*{n}\s*\|", snap, re.M) for n in range(1, 9))
step("D20", PASS if rows else FAIL, "snapshot has all 8 KPI rows")
step("D21", PASS if ("trajectory" in snap.lower() and "commentary" in snap.lower()) else FAIL,
     "snapshot has wk6→wk12 trajectory + commentary")
step("D22", PASS if ("kpi #4" in snap.lower() and "reconcil" in snap.lower()) else FAIL,
     "snapshot documents the KPI #4 reconciliation")

adr = _read("docs/adr/0001-capstone-framing.md")
step("D23", PASS if ("v2 (m2)" in adr.lower()) else FAIL, "ADR marked v2 (M2)")
step("D24", PASS if all(k in adr.lower() for k in ("rerank", "tombstone", "ragas", "kb_version")) else FAIL,
     "ADR consolidates Phase 2 decisions")
step("D25", PASS if all(d in adr for d in ("6.1", "6.2", "6.3", "6.4")) else FAIL,
     "ADR has W12 decisions 6.1–6.4")

dr_t = _read("docs/dr/dr2-summary-template.md").lower()
dr_e = _read("docs/dr/dr2-summary-EXAMPLE.md").lower()
step("D26", PASS if all(k in dr_t for k in ("retriev", "lifecycle", "kpi")) else FAIL,
     "DR #2 template covers retrieval + lifecycle + KPIs")
step("D27", PASS if all(k in dr_e for k in ("retriev", "lifecycle", "kpi")) else FAIL,
     "DR #2 example is filled")


# ═══ E · Smoke test, config, Lab Guide ═══════════════════════════════════
section("E · Smoke test, config, Lab Guide")

smoke = _read("smoke_test.sh")
step("E28", PASS if all(k in smoke for k in ("debug_drill.py", "pytest tests", "m2_check.py",
                                             "PYTEST_DISABLE_PLUGIN_AUTOLOAD")) else FAIL,
     "smoke_test runs drill + tests + m2_check + guards plugins")

pini = _read("pytest.ini")
step("E29", PASS if "langsmith" in pini else FAIL, "pytest.ini blocks the broken plugin")

req = _read("requirements.txt")
step("E30", PASS if "pytest" in req else FAIL, "requirements pins pytest")

env = _read(".env.example")
lines = [ln for ln in env.splitlines() if ln.strip() and not ln.strip().startswith("#")]
step("E31", PASS if lines and all(ln.strip().startswith("export ") for ln in lines) else FAIL,
     f".env.example: all {len(lines)} active lines use export")

lab = _read("AI-RAG_W12_Lab_Guide.md")
step("E32", PASS if all(k in lab for k in ("debug_drill", "M2", "PYTEST_DISABLE_PLUGIN_AUTOLOAD")) else FAIL,
     "Lab Guide covers the drill + M2 + troubleshooting")

m2 = _read("scripts/m2_check.py")
step("E33", PASS if "wk12-snapshot" in m2 else FAIL, "m2_check verifies the snapshot")

standalones = ["Deck.pptx", "Facilitator_Guide.md", "Quiz_1.md", "Activity.md",
               "Activity_Solution.md"]
found = [s for s in standalones if (ROOT / s).exists() or (ROOT.parent / s).exists()]
if len(found) == len(standalones):
    step("E34", PASS, f"all {len(standalones)} standalone deliverables found")
elif found:
    step("E34", SKIP, f"{len(found)}/{len(standalones)} standalones co-located (rest in ALL bundle)")
else:
    step("E34", SKIP, "standalones shipped separately (ALL bundle)")


# ═══ Summary ═════════════════════════════════════════════════════════════
passed = sum(1 for v, _ in results if v == PASS)
failed = sum(1 for v, _ in results if v == FAIL)
skipped = sum(1 for v, _ in results if v == SKIP)
print("\n" + "═" * 56)
print(f"  RESULT: {passed}/{len(results)} passed · {failed} failed · {skipped} skipped")
print("  \033[32mW12 package verified.\033[0m" if not failed
      else "  \033[31mFailures above must be fixed.\033[0m")
print("═" * 56)
sys.exit(1 if failed else 0)
