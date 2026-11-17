#!/usr/bin/env bash
# =============================================================================
# AI-RAG Week 12 — smoke_test.sh
#
# Proves the RAG debugging drill runs end-to-end with NO network, NO API key,
# and NO Qdrant, and that the M2 deliverable documents are complete — so an
# instructor or learner following the Lab Guide and the Python files can be
# confident everything executes.
#
# Usage:  bash smoke_test.sh
# Exit:   0 = all green.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; BOLD=$'\033[1m'; NC=$'\033[0m'
pass() { echo "${GREEN}  ✓ $1${NC}"; }
fail() { echo "${RED}  ✗ $1${NC}"; exit 1; }
step() { echo; echo "${BOLD}[$1/7] $2${NC}"; }

# Broken third-party pytest plugins (e.g. langsmith on Vocareum) load at startup
# and crash pytest; disable third-party plugin autoload. Our tests need none.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

step 1 "Check Python is available"
command -v python3 >/dev/null 2>&1 || fail "python3 not found on PATH"
pass "python3 $(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"

step 2 "Install test dependency (pytest)"
if python3 -c "import pytest" >/dev/null 2>&1; then
  pass "pytest already present"
else
  python3 -m pip install --break-system-packages -q pytest || fail "pip install pytest failed"
  pass "installed pytest"
fi

step 3 "List the six drill scenarios"
python3 scripts/debug_drill.py list >/dev/null || fail "debug_drill.py list failed"
pass "drill lists 6 scenarios"

step 4 "Render every scenario's trace (offline, deterministic)"
python3 scripts/debug_drill.py run-all >/dev/null || fail "run-all failed to render traces"
pass "all 6 traces render"

step 5 "Prove each scenario reproduces its failure (pytest)"
python3 -m pytest tests/ -q || fail "scenario tests failed — the drill is not sound"
pass "scenario tests passed"

step 6 "Check the drill grader (correct bucket accepted for all 6)"
for s in S1 S2 S3 S4 S5 S6; do
  b=$(python3 - "$s" <<'PY'
import sys; sys.path.insert(0,".")
from src.debug.scenarios import get
print(get(sys.argv[1]).bucket)
PY
)
  python3 scripts/debug_drill.py grade "$s" "$b" >/dev/null || fail "grader rejected correct bucket for $s"
done
pass "grader accepts the correct bucket for all 6"

step 7 "Check the M2 deliverable documents are complete"
python3 scripts/m2_check.py >/dev/null || fail "M2 documents missing/incomplete (run: python3 scripts/m2_check.py)"
pass "M2 documents complete"

echo
echo "${GREEN}${BOLD}ALL CHECKS PASSED.${NC}"
echo "The debugging drill runs offline and the M2 docs are in shape. Next: open"
echo "AI-RAG_W12_Lab_Guide.md and start with the drill (Activity), then the M2 steps."
