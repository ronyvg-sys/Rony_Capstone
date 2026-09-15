# W4 — How to run and verify on Vocareum

This package is a fully laid-out W4 capstone repo at the end of Lab Step 4
(ADR extended; tests passing; service runnable). All files are byte-identical
to the published references in `/mnt/user-data/outputs/`.

**Two bugs were caught and fixed before this package was assembled** — see
"What was fixed" below.

## What's inside

```
W4_package/
├── src/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── settings.py            ← W2 carry-over
│   │   ├── logging_config.py      ← W2 carry-over
│   │   ├── fake_llm.py            ← W2 carry-over
│   │   ├── query_results.py       ← W2 carry-over
│   │   ├── pipeline.py            ← W4 reference (replaces W2)
│   │   ├── store.py               ← W4 reference (replaces W2)
│   │   ├── models.py              ← W4 NEW (Answer with confidence/sources/schema_version)
│   │   └── cost.py                ← W4 NEW (RATES + compute_cost_usd)
│   └── api/
│       ├── __init__.py
│       └── main.py                ← W4 reference (now under src/api/, not top-level)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cost.py               ← W4 NEW (9 tests)
│   └── test_pipeline_w4.py        ← W4 NEW (10 tests)
├── scripts/
│   ├── migrate_store.py           ← W4 NEW (with sys.path fix)
│   └── compare_models.py          ← W4 NEW (with sys.path fix)
├── data/
│   └── questions.csv
├── reference/                      ← W4 starters + ADR templates + anthropic reference
├── requirements.txt
├── pytest.ini
├── logs/
├── RUN_W4.sh
└── RUN_W4.md                       ← this file
```

## How to run on Vocareum

```bash
unzip AI-RAG_W4_Package.zip
cd W4_package
bash RUN_W4.sh
```

Wall-clock: ~60 seconds. Stop any prior `uvicorn` on port 8000 first.

## Expected output — all PASS

```
step0_python_version                       PASS
step0_openai_key                           PASS
step0_pip_install                          PASS
step0_imports_ok                           PASS
step1_layout_complete                      PASS
step2_cost_rates_dict                      PASS
step2_cost_known_model                     PASS
step2_cost_diff_models                     PASS
step3_answer_defaults                      PASS
step3_answer_w3_compat                     PASS
step3_question_shape                       PASS
step4_store_ensure_schema                  PASS
step4_store_idempotent                     PASS
step4_store_save_query                     PASS
step5_answer_tool                          PASS
step5_ask_llm_fake                         PASS
step6_app_imports                          PASS
step6_health                               PASS
step6_ask_batched_w4                       PASS
step6_ask_streaming                        PASS
step7_uvicorn_start                        PASS
step7_curl_health                          PASS
step7_curl_ask_batched                     PASS
step7_uvicorn_stop                         PASS
step8_migrate_lab_command                  PASS  ← was FAIL before fix
step8_migrate_with_pythonpath              PASS
step8_migrate_idempotent                   PASS
step9_compare_models_parses                PASS
step9_compare_models_lab_command           PASS  ← was FAIL before fix
step9_compare_models_with_pythonpath       PASS
step10_pytest                              PASS
```

**31 PASS, 0 FAIL** on Vocareum.

## What was fixed

Two real bugs were caught during verifier development:

### Bug 1 — `src/api/main.py` accessed a non-existent Settings field

The original W4 reference had:
```python
_db_path = Path(_settings.db_path)   # ← AttributeError on startup
```

W2 `Settings` has a field called `results_db`, not `db_path`. **Fix:**
```python
_db_path = Path(_settings.results_db)
```

This was fixed in `AI-RAG_W4_api_main_reference.py` in `/mnt/user-data/outputs/`.

### Bug 2 — `scripts/migrate_store.py` + `scripts/compare_models.py` couldn't import `src.pipeline...`

The lab guide says (W4 Step 2e):
```bash
python scripts/migrate_store.py data/answers.db
```

That failed with `ModuleNotFoundError: No module named 'src'` because
Python's `sys.path[0]` defaults to the script's directory (`scripts/`), not
the project root.

**Fix (applied at the top of both scripts):**
```python
# Make the `src` package reachable when invoked as `python scripts/X.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

That's 4 lines of comment + 1 line of code per script. The lab guide
commands now work as written — no lab guide changes needed.

## What's deliberately skipped

- **Streamlit UI** — UI surface; instructor verifies in browser.
- **Real cross-model comparison run** — `compare_models.py` end-to-end would
  make 20 real OpenAI calls. That's the instructor's lab Step 3 work.

## What to send back to me

```bash
cat logs/_SUMMARY.log
```

If all 31 lines are PASS, W4 is good to ship to the instructor.
