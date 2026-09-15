#!/usr/bin/env bash
# ============================================================================
# RUN_W4.sh — Verifies W4 reference code on Vocareum.
#
# What this script does:
#   1. Confirms Python + OPENAI_API_KEY.
#   2. Installs requirements.txt (W4 is a superset — includes W2+W3+tiktoken).
#   3. Runs lab-guide verifications against the shipped W4 reference code:
#       - cost.py (RATES table + compute_cost_usd)
#       - models.py (Answer 6-field shape, W3 backward compat, Question)
#       - store.py (ensure_schema, idempotent, save+query roundtrip)
#       - pipeline.py (ANSWER_TOOL schema, use_fake ask_llm)
#       - api/main.py via TestClient (W4 6-field contract)
#       - Real uvicorn `uvicorn src.api.main:app` + curl
#       - scripts/migrate_store.py (run against fresh + existing db)
#       - scripts/compare_models.py (parse-check; real run = real $)
#       - pytest tests/ (test_cost + test_pipeline_w4)
#   4. Captures each step's output to logs/<step_id>.log.
#   5. Writes logs/_SUMMARY.log with PASS/FAIL per step.
#
# Skipped (deliberately):
#   - Streamlit UI checks (UI surface, instructor verifies in browser).
#   - Actually running compare_models.py end-to-end (it makes 20 real OpenAI
#     calls — that's the instructor's lab Step 3, not the verifier's job).
# ============================================================================

set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 2

LOG_DIR="$ROOT/logs"
SUMMARY="$LOG_DIR/_SUMMARY.log"
UVICORN_PORT=8000
UVICORN_LOG="$LOG_DIR/_uvicorn_real.log"
UVICORN_PID_FILE="$LOG_DIR/_uvicorn.pid"

mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*.log "$UVICORN_PID_FILE"
rm -f "$ROOT/results.json" "$ROOT/results.db" "$ROOT/data/answers.db"
find "$ROOT" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
find "$ROOT" -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null

cleanup() {
    if [ -f "$UVICORN_PID_FILE" ]; then
        local pid; pid=$(cat "$UVICORN_PID_FILE")
        kill "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
        rm -f "$UVICORN_PID_FILE"
    fi
}
trap cleanup EXIT INT TERM

{
    echo "W4 Verification Run"
    echo "==================="
    echo "Timestamp:    $(date -Iseconds)"
    echo "PWD:          $ROOT"
    echo "Python:       $(python --version 2>&1)"
    echo "Has API key:  $(python -c "import os; print(bool(os.getenv('OPENAI_API_KEY')))" 2>&1)"
    echo "Uvicorn port: $UVICORN_PORT"
    echo
    printf "%-46s  %-30s  %s\n" "STEP" "VERDICT" "DESCRIPTION"
    printf "%-46s  %-30s  %s\n" "----" "-------" "-----------"
} > "$SUMMARY"

run_step () {
    local step_id="$1"; local description="$2"; local expected_rc="$3"; local cmd="$4"
    local log_file="$LOG_DIR/${step_id}.log"
    {
        echo "STEP:        $step_id"
        echo "DESCRIPTION: $description"
        echo "EXPECTED RC: $expected_rc"
        echo "TIMESTAMP:   $(date -Iseconds)"
        echo "COMMAND:"; echo "$cmd" | sed 's/^/    /'
        echo "--- OUTPUT ---"
    } > "$log_file"
    bash -c "$cmd" >> "$log_file" 2>&1
    local rc=$?
    local verdict
    if [ "$expected_rc" = "any" ]; then verdict="DONE  (rc=$rc)"
    elif [ "$rc" = "$expected_rc" ]; then verdict="PASS"
    else verdict="FAIL  (rc=$rc, expected $expected_rc)"; fi
    echo "  [$verdict]  $step_id  —  $description"
    printf "%-46s  %-30s  %s\n" "$step_id" "$verdict" "$description" >> "$SUMMARY"
    { echo "--- END ---"; echo "EXIT_CODE: $rc"; echo "VERDICT:   $verdict"; } >> "$log_file"
}

# ===========================================================================
# Step 0 — Environment
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 0 — Environment"; echo "=========================================="

run_step "step0_python_version"   "Python version"                       0 \
    "python --version"

run_step "step0_openai_key"       "OPENAI_API_KEY present"               0 \
    "python -c \"import os; ok=bool(os.getenv('OPENAI_API_KEY')); print('OPENAI_API_KEY present:', ok); raise SystemExit(0 if ok else 1)\""

run_step "step0_pip_install"      "pip install -r requirements.txt (W4 superset)"  0 \
    "pip install --break-system-packages -q -r requirements.txt"

run_step "step0_imports_ok"       "All required packages importable (incl. tiktoken)"  0 \
    "python -c \"import openai, pydantic, dotenv, httpx, fastapi, uvicorn, pytest, tiktoken; print('OK · fastapi', fastapi.__version__, '· tiktoken', tiktoken.__version__, '· pydantic', pydantic.VERSION)\""

# ===========================================================================
# Step 1 — Layout
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 1 — File layout"; echo "=========================================="

run_step "step1_layout_complete"  "Every canonical W4 file at expected path"  0 \
    "for f in src/api/main.py src/pipeline/pipeline.py src/pipeline/models.py src/pipeline/cost.py src/pipeline/store.py src/pipeline/settings.py tests/test_cost.py tests/test_pipeline_w4.py tests/conftest.py scripts/migrate_store.py scripts/compare_models.py pytest.ini data/questions.csv; do
        if [ -f \"\$f\" ]; then echo \"  ✓  \$f\"; else echo \"  ✗  MISSING: \$f\" && exit 1; fi
    done"

# ===========================================================================
# Step 2 — cost.py
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 2 — cost.py"; echo "=========================================="

run_step "step2_cost_rates_dict"  "RATES dict contains expected model entries"  0 \
    "python -c \"
from src.pipeline.cost import RATES
print('models in RATES:', sorted(RATES.keys()))
assert 'gpt-4o-mini' in RATES, 'gpt-4o-mini missing'
assert 'gpt-4o' in RATES, 'gpt-4o missing'
mini_rate = RATES['gpt-4o-mini']
print('gpt-4o-mini rates:', mini_rate)
\""

run_step "step2_cost_known_model" "compute_cost_usd known model — sane number"  0 \
    "python -c \"
from src.pipeline.cost import compute_cost_usd
cost = compute_cost_usd('gpt-4o-mini', 100, 50)
print(f'compute_cost_usd(gpt-4o-mini, 100, 50) = \${cost:.6f}')
assert 0 < cost < 0.001, f'unexpected cost magnitude: {cost}'
\""

run_step "step2_cost_diff_models" "gpt-4o is more expensive than gpt-4o-mini"  0 \
    "python -c \"
from src.pipeline.cost import compute_cost_usd
mini = compute_cost_usd('gpt-4o-mini', 1000, 500)
full = compute_cost_usd('gpt-4o',      1000, 500)
print(f'gpt-4o-mini @ 1k/500: \${mini:.6f}')
print(f'gpt-4o      @ 1k/500: \${full:.6f}')
print(f'ratio:                {full/mini:.2f}x')
assert full > mini, 'expected gpt-4o > gpt-4o-mini in cost'
\""

# ===========================================================================
# Step 3 — models.py
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 3 — models.py"; echo "=========================================="

run_step "step3_answer_defaults"  "Answer constructs with defaults, schema_version='v1'"  0 \
    "python -c \"
from src.pipeline.models import Answer
a = Answer(content='hi', cost_usd=0.0, retries=0)
print(f'schema_version: {a.schema_version!r}')
print(f'confidence:     {a.confidence}')
print(f'sources:        {a.sources}')
print(f'all fields:     {sorted(a.model_dump().keys())}')
assert a.schema_version == 'v1'
assert isinstance(a.sources, list)
for f in ('content', 'cost_usd', 'retries', 'confidence', 'sources', 'schema_version'):
    assert f in a.model_dump(), f'missing field: {f}'
\""

run_step "step3_answer_w3_compat" "W3-shape constructor still works (additive change)"  0 \
    "python -c \"
from src.pipeline.models import Answer
# A W3 caller only supplies three fields — must keep working.
a = Answer(content='Hello.', cost_usd=0.001, retries=0)
print('W3 shape OK:', a.model_dump_json())
assert a.content == 'Hello.'
\""

run_step "step3_question_shape"   "Question has 'question' field"  0 \
    "python -c \"
from src.pipeline.models import Question
q = Question(question='What is RAG?')
print(f'Question: {q.model_dump()}')
assert q.question == 'What is RAG?'
\""

# ===========================================================================
# Step 4 — store.py (W4 extended)
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 4 — store.py"; echo "=========================================="

run_step "step4_store_ensure_schema"  "ensure_schema creates the W4 columns"  0 \
    "python -c \"
import sys, tempfile, os, sqlite3; sys.path.insert(0, '.')
from src.pipeline.store import ensure_schema
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f: path = f.name
ensure_schema(path)
conn = sqlite3.connect(path)
cols = [r[1] for r in conn.execute('PRAGMA table_info(answers)').fetchall()]
conn.close(); os.unlink(path)
print(f'answers columns: {cols}')
for c in ('content', 'cost_usd', 'retries', 'model', 'confidence', 'sources_json', 'schema_version'):
    assert c in cols, f'missing column: {c}'
\""

run_step "step4_store_idempotent" "ensure_schema can be re-run without error"  0 \
    "python -c \"
import sys, tempfile, os, sqlite3; sys.path.insert(0, '.')
from src.pipeline.store import ensure_schema
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f: path = f.name
ensure_schema(path)
ensure_schema(path)  # twice
ensure_schema(path)  # thrice
conn = sqlite3.connect(path)
cols_count = len(conn.execute('PRAGMA table_info(answers)').fetchall())
conn.close(); os.unlink(path)
print(f'columns after 3x ensure_schema: {cols_count}')
\""

run_step "step4_store_save_query" "save_answer + query roundtrip"  0 \
    "python -c \"
import sys, tempfile, os, sqlite3; sys.path.insert(0, '.')
from src.pipeline.store import connect, save_answer
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f: path = f.name
with connect(path) as conn:
    save_answer(
        conn,
        question='Q?',
        content='hi',
        retries=0,
        cost_usd=0.001,
        model='gpt-4o-mini',
        confidence=0.9,
        sources=['doc1'],
    )
    rows = conn.execute('SELECT question, content, cost_usd, retries, model, confidence, schema_version FROM answers').fetchall()
print(f'roundtripped rows: {rows}')
os.unlink(path)
assert len(rows) == 1
assert rows[0][0] == 'Q?'
assert rows[0][1] == 'hi'
assert rows[0][6] == 'v1'
\""

# ===========================================================================
# Step 5 — pipeline.py (tool-calling)
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 5 — pipeline.py (tool-calling)"; echo "=========================================="

run_step "step5_answer_tool"      "ANSWER_TOOL schema is well-formed"  0 \
    "python -c \"
import sys; sys.path.insert(0, '.')
from src.pipeline.pipeline import ANSWER_TOOL
import json
print(json.dumps(ANSWER_TOOL, indent=2)[:500])
# Should be a valid OpenAI tool schema
assert ANSWER_TOOL['type'] == 'function'
assert 'function' in ANSWER_TOOL
assert 'name' in ANSWER_TOOL['function']
assert 'parameters' in ANSWER_TOOL['function']
assert ANSWER_TOOL['function']['name'] == 'answer_question'
print('PASS — well-formed tool schema with name:', ANSWER_TOOL['function']['name'])
\""

run_step "step5_ask_llm_fake"     "ask_llm with use_fake=True returns 6-field Answer"  0 \
    "python -c \"
import sys, asyncio; sys.path.insert(0, '.')
from src.pipeline.pipeline import ask_llm
from src.pipeline.models import Question
from src.pipeline.settings import Settings
s = Settings(use_fake=True)
a = asyncio.run(ask_llm(Question(question='What is RAG?'), settings=s))
print(f'type:           {type(a).__name__}')
print(f'content head:   {a.content[:80]!r}')
print(f'cost_usd:       {a.cost_usd}')
print(f'retries:        {a.retries}')
print(f'confidence:     {a.confidence}')
print(f'sources:        {a.sources}')
print(f'schema_version: {a.schema_version!r}')
assert a.schema_version == 'v1'
\""

# ===========================================================================
# Step 6 — FastAPI via TestClient
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 6 — FastAPI (TestClient)"; echo "=========================================="

run_step "step6_app_imports"      "from src.api.main import app — imports cleanly"  0 \
    "python -c \"
import sys; sys.path.insert(0, '.')
from src.api.main import app
print('app:', type(app).__name__)
print('routes:', sorted([r.path for r in app.routes if hasattr(r, 'path')]))
\""

run_step "step6_health"           "GET /health returns 200"  0 \
    "python -c \"
import sys; sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from src.api.main import app
client = TestClient(app)
r = client.get('/health')
print('status:', r.status_code, 'body:', r.json())
assert r.status_code == 200
\""

run_step "step6_ask_batched_w4"   "POST /ask_batched returns 6-field W4 Answer"  0 \
    "python -c \"
import sys; sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from src.api.main import app
client = TestClient(app)
r = client.post('/ask_batched', json={'question': 'What is RAG?'})
print('status:', r.status_code)
body = r.json()
print('keys:', sorted(body.keys()))
for f in ('content', 'cost_usd', 'retries', 'confidence', 'sources', 'schema_version'):
    assert f in body, f'missing W4 field: {f}'
print('schema_version:', body['schema_version'])
print('content head:', body['content'][:80])
\""

run_step "step6_ask_streaming"    "POST /ask streaming returns chunks"  0 \
    "python -c \"
import sys; sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from src.api.main import app
client = TestClient(app)
with client.stream('POST', '/ask', json={'question': 'What is RAG?'}) as r:
    print('status:', r.status_code)
    assert r.status_code == 200
    chunks = list(r.iter_text())
    full = ''.join(chunks)
    print(f'chunks: {len(chunks)}, total bytes: {len(full)}')
    print(f'head: {full[:80]!r}')
    assert len(full) > 0
\""

# ===========================================================================
# Step 7 — Real uvicorn (per W4 lab guide: src.api.main:app)
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 7 — Real uvicorn"; echo "=========================================="

run_step "step7_uvicorn_start"    "Start uvicorn src.api.main:app (lab guide command)"  0 \
    "uvicorn src.api.main:app --port $UVICORN_PORT --log-level warning > '$UVICORN_LOG' 2>&1 &
    UV_PID=\$!
    echo \$UV_PID > '$UVICORN_PID_FILE'
    echo \"uvicorn started, pid=\$UV_PID\"
    for i in 1 2 3 4 5 6 7 8 9 10; do
        sleep 1
        if curl -s -f -o /dev/null http://localhost:$UVICORN_PORT/health 2>/dev/null; then
            echo \"server ready after \${i}s\"
            exit 0
        fi
    done
    echo 'SERVER NEVER BECAME READY'
    cat '$UVICORN_LOG'
    exit 1"

run_step "step7_curl_health"      "curl /health against live server"  0 \
    "out=\$(curl -s -i http://localhost:$UVICORN_PORT/health)
    echo \"\$out\"
    echo \"\$out\" | head -1 | grep -q '200' || { echo 'EXPECTED 200'; exit 1; }
    echo \"\$out\" | tail -1 | grep -q '\"status\":\"ok\"' || { echo 'EXPECTED status:ok'; exit 1; }"

run_step "step7_curl_ask_batched" "curl /ask_batched against live server → W4 6-field Answer"  0 \
    "out=\$(curl -s -i -X POST http://localhost:$UVICORN_PORT/ask_batched \\
                   -H 'Content-Type: application/json' \\
                   -d '{\"question\": \"What is RAG?\"}')
    echo \"\$out\"
    echo \"\$out\" | head -1 | grep -q '200' || { echo 'EXPECTED 200'; exit 1; }
    body=\$(echo \"\$out\" | tail -1)
    for field in content cost_usd retries confidence sources schema_version; do
        echo \"\$body\" | grep -q \"\\\"\$field\\\"\" || { echo \"MISSING W4 FIELD: \$field\"; exit 1; }
    done"

run_step "step7_uvicorn_stop"     "Stop uvicorn cleanly"  0 \
    "if [ -f '$UVICORN_PID_FILE' ]; then
        pid=\$(cat '$UVICORN_PID_FILE')
        echo \"stopping uvicorn, pid=\$pid\"
        kill \$pid 2>/dev/null
        sleep 1
        kill -0 \$pid 2>/dev/null && kill -9 \$pid 2>/dev/null
        rm -f '$UVICORN_PID_FILE'
        echo 'uvicorn stopped'
    else
        echo 'no pid file'
        exit 1
    fi"

# ===========================================================================
# Step 8 — migrate_store.py (runs against fresh DB)
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 8 — Migration script"; echo "=========================================="

run_step "step8_migrate_lab_command"  "scripts/migrate_store.py — EXACT lab guide invocation"  0 \
    "set -e
    rm -f /tmp/_w4_migrate_test.db
    # Exact lab guide command (Step 2e): python scripts/migrate_store.py <db-path>
    python scripts/migrate_store.py /tmp/_w4_migrate_test.db
    # Verify the schema landed
    python -c \"
import sqlite3
conn = sqlite3.connect('/tmp/_w4_migrate_test.db')
cols = [r[1] for r in conn.execute('PRAGMA table_info(answers)').fetchall()]
print(f'columns after migration: {cols}')
for c in ('model', 'confidence', 'sources_json', 'schema_version'):
    assert c in cols, f'missing W4 column: {c}'
print('PASS — all W4 columns present')
\"
    rm -f /tmp/_w4_migrate_test.db"

run_step "step8_migrate_with_pythonpath"  "Same migrate_store run with PYTHONPATH=. — proves code itself works"  0 \
    "set -e
    rm -f /tmp/_w4_migrate_test.db
    # With PYTHONPATH=., the 'src' package is reachable — bypass the script's
    # default sys.path issue. This confirms migrate_store.py's LOGIC is correct.
    PYTHONPATH=. python scripts/migrate_store.py /tmp/_w4_migrate_test.db
    python -c \"
import sqlite3
conn = sqlite3.connect('/tmp/_w4_migrate_test.db')
cols = [r[1] for r in conn.execute('PRAGMA table_info(answers)').fetchall()]
print(f'columns after migration: {cols}')
for c in ('model', 'confidence', 'sources_json', 'schema_version'):
    assert c in cols, f'missing W4 column: {c}'
print('PASS — code itself works fine when invoked with PYTHONPATH set')
\"
    rm -f /tmp/_w4_migrate_test.db"

run_step "step8_migrate_idempotent"  "Re-running migrate_store reports already-migrated (with PYTHONPATH fix)"  0 \
    "set -e
    rm -f /tmp/_w4_migrate_test.db
    PYTHONPATH=. python scripts/migrate_store.py /tmp/_w4_migrate_test.db
    out=\$(PYTHONPATH=. python scripts/migrate_store.py /tmp/_w4_migrate_test.db)
    echo \"\$out\"
    echo \"\$out\" | grep -qE 'already migrated|none' || { echo 'expected idempotency mention'; exit 1; }
    rm -f /tmp/_w4_migrate_test.db"

# ===========================================================================
# Step 9 — compare_models.py (parse-check only — real run is lab Step 3)
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 9 — compare_models.py (parse-only)"; echo "=========================================="

run_step "step9_compare_models_parses"  "scripts/compare_models.py parses + imports cleanly"  0 \
    "python -c \"
import ast
src = open('scripts/compare_models.py').read()
ast.parse(src)
print(f'compare_models.py: {len(src.splitlines())} lines, parses OK')
\" && python -c \"
# Also confirm imports resolve (without executing main)
import sys; sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('cm', 'scripts/compare_models.py')
mod = importlib.util.module_from_spec(spec)
# Don't run main(); just exec the module so imports happen
spec.loader.exec_module(mod)
print('imports resolved OK')
print('(Not executed end-to-end — 20 real OpenAI calls. That is lab Step 3.)')
\""

run_step "step9_compare_models_lab_command"  "scripts/compare_models.py --help — EXACT lab guide invocation"  0 \
    "python scripts/compare_models.py --help"

run_step "step9_compare_models_with_pythonpath"  "Same compare_models --help with PYTHONPATH=. — proves code works"  0 \
    "PYTHONPATH=. python scripts/compare_models.py --help"

# ===========================================================================
# Step 10 — Pytest
# ===========================================================================
echo ""; echo "=========================================="; echo " Step 10 — Pytest tests/"; echo "=========================================="

run_step "step10_pytest"          "pytest tests/ -q (test_cost.py + test_pipeline_w4.py)"  0 \
    "python -m pytest tests/ -q --tb=short"

# ===========================================================================
# Done
# ===========================================================================
echo ""; echo "=========================================="; echo " Summary"; echo "=========================================="
cat "$SUMMARY"
echo ""
echo "All step logs are in: $LOG_DIR/"
echo "Top-line summary is in: $SUMMARY"
echo ""
echo "To share, either zip the logs/ directory or just paste the contents of:"
echo "  $SUMMARY"
echo "plus any individual log file where you see FAIL."
