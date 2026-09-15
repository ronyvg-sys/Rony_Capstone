# Week 4 — Take-home Activity

**Local models via Ollama: the third option in your pipeline**

Time: ~30–45 minutes · Requires your own laptop (the Vocareum lab can't run Ollama) · Optional submission

---

## Builds on

This activity assumes you've finished the W4 lab — specifically:

- `src/pipeline/cost.py` exists with a `RATES` dict and `compute_cost_usd`
- `src/pipeline/pipeline.py` has `ask_llm` using tool-calling
- `scripts/compare_models.py` runs cleanly with `--models gpt-4o-mini,gpt-4o`
- `data/answers.db` has rows from both OpenAI models after Lab Step 3

If you haven't done Lab Step 3, do it first — this activity *extends* that
comparison with a third row.

---

## Goal

Stand up a local LLM via Ollama, integrate it as a third model option in
your existing W4 pipeline (without rewriting anything), run the lab's 10
questions through it, and compare cost + quality with `gpt-4o-mini` and
`gpt-4o`.

The cost story will be dramatic: local is **$0 marginal**. The quality
story will be honest: a 3-billion-parameter model on a laptop will be
visibly worse than `gpt-4o-mini` on some questions, surprisingly close
on others. That contrast is the point of the exercise — local is a
*development iteration* tool and a *privacy* tool, not a quality
replacement for hosted models.

---

## Materials

You'll need:

- Your own machine (macOS, Linux, or Windows). Apple Silicon or a recent
  CPU with ≥ 16 GB RAM works well; 8 GB will run `llama3.2:3b` but
  slowly.
- ~3 GB free disk for the model.
- ~5 minutes of internet to download the model.
- Your existing W4 cohort repo, with `src/pipeline/cost.py` and the
  tool-calling `ask_llm`.

---

## Step 1 — Install Ollama (~5 min)

Ollama bundles a model server, a CLI, and an OpenAI-compatible HTTP API
endpoint at `http://localhost:11434/v1`. You don't need to learn a new
SDK — the OpenAI Python client talks to it directly.

### macOS / Windows

Download the installer from [ollama.com/download](https://ollama.com/download)
and run it. On macOS you'll get a menu-bar icon; on Windows a system-tray
icon. The server starts automatically.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Verify

```bash
ollama --version
curl -s http://localhost:11434/api/tags
```

If `ollama --version` prints a version number and the `curl` returns a
JSON object (possibly with an empty `models` list), you're good.

---

## Step 2 — Pull `llama3.2:3b` (~2 min)

```bash
ollama pull llama3.2:3b
```

This downloads ~2 GB. When it's done:

```bash
ollama list
```

You should see `llama3.2:3b` with a size around 2.0 GB.

Quick smoke test from the CLI:

```bash
echo "What is RAG, in two sentences?" | ollama run llama3.2:3b
```

You'll get an answer in 1–10 seconds depending on your hardware. It
won't be as polished as `gpt-4o-mini`, but it'll be coherent.

---

## Step 3 — Wire Ollama into your W4 pipeline (~10 min)

Ollama exposes an OpenAI-compatible endpoint, which means your existing
`ask_llm` code mostly already works. Two small adjustments.

### 3a — Add the model to `cost.py`

Open `src/pipeline/cost.py`. The reference already has the entry, but
double-check that `RATES` includes:

```
"llama3.2:3b": (0.0, 0.0),
```

Local models cost $0 marginal. The entry exists so the same
`compute_cost_usd` function handles all three providers without
branching.

### 3b — Make the OpenAI client point at Ollama when the model name starts with `llama`

In `src/pipeline/pipeline.py`, inside `ask_llm` (and `stream_answer` if
you want streaming too), the client construction currently looks like:

```
client = AsyncOpenAI(api_key=settings.openai_api_key)
```

Switch to a conditional that points at Ollama for local models. Add this
helper near the top of `pipeline.py`:

```python
def _make_client(settings):
    if settings.model.startswith("llama") or settings.model.startswith("ollama:"):
        return AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # any string — Ollama doesn't check it
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)
```

Then replace the two `AsyncOpenAI(...)` calls in `ask_llm` and
`stream_answer` with `_make_client(settings)`.

> **Note about tool-calling.** `llama3.2:3b` *does* support tool-calling
> via Ollama's OpenAI-compatible endpoint, but its compliance is less
> reliable than `gpt-4o-mini`. If your `ask_llm` raises
> `"LLM did not call the answer_question tool"` more than half the time,
> fall back to JSON mode (`response_format={"type":"json_object"}`) for
> the local model only.

### 3c — Smoke test

```bash
python -c "
import asyncio
from src.pipeline.pipeline import ask_llm
from src.pipeline.models import Question
from src.pipeline.settings import Settings

settings = Settings(model='llama3.2:3b', openai_api_key='not-used')
ans = asyncio.run(ask_llm(Question(question='What is RAG?'), settings))
print('content   :', ans.content[:120])
print('confidence:', ans.confidence)
print('sources   :', ans.sources)
print('cost_usd  :', ans.cost_usd)
"
```

You should see:
- `content` — a reasonable 2–3 sentence answer
- `confidence` — some number in `[0, 1]`
- `cost_usd` — exactly `0.0` (it's free)

If the smoke test fails with the "LLM did not call the answer_question
tool" error, apply the JSON-mode fallback from the note above and try
again.

---

## Step 4 — Run the lab's 10 questions through Ollama (~10 min)

Use the same comparison script you ran in Lab Step 3.

```bash
python scripts/compare_models.py --models llama3.2:3b
```

This runs the 10 `data/questions.csv` questions through Ollama, persists
each row to SQLite with `model='llama3.2:3b'`, and prints a summary.

The cost will be `$0.000000` — Ollama is free locally. The time-per-call
depends entirely on your laptop's CPU/GPU; expect 2–15 seconds per
question.

---

## Step 5 — Three-way comparison (~10 min)

You now have rows in `data/answers.db` from three models. Pull a
three-way summary:

```bash
sqlite3 -header -column data/answers.db <<'SQL'
SELECT
  model,
  COUNT(*)                          AS n,
  ROUND(SUM(cost_usd), 6)           AS total_cost_usd,
  ROUND(AVG(cost_usd), 6)           AS avg_cost_usd,
  ROUND(AVG(confidence), 2)         AS avg_confidence
FROM answers
WHERE model IN ('gpt-4o-mini', 'gpt-4o', 'llama3.2:3b')
GROUP BY model
ORDER BY total_cost_usd DESC;
SQL
```

Expected shape:

```
model        n     total_cost_usd  avg_cost_usd  avg_confidence
-----------  ----  --------------  ------------  --------------
gpt-4o       10    0.013648        0.001365      0.91
gpt-4o-mini  10    0.000832        0.000083      0.87
llama3.2:3b  10    0.000000        0.000000      0.75
```

Then **read the answers** for a few questions where you suspect the
local model would struggle. The schema-versioning question (Q10 in
`questions.csv`) tends to expose the quality gap clearly.

```bash
sqlite3 data/answers.db \
  "SELECT model, substr(content, 1, 180) FROM answers WHERE question LIKE '%schema_version%' ORDER BY model;"
```

---

## What you should notice

Three things, in order of importance:

1. **Local is genuinely free.** The cost ratio between `gpt-4o` and
   `llama3.2:3b` is infinity — useful when you want to iterate on a
   prompt without watching the OpenAI bill tick up.
2. **The quality gap is real but narrower than you'd expect** on simple
   definitional questions. The smaller model knows what RAG is and what
   a token is; it struggles on questions that require synthesising
   multiple ideas (schema versioning, the API contract question).
3. **Confidence numbers self-correct in surprising ways.** A well-tuned
   model usually reports lower confidence when it's uncertain. Compare
   the average `confidence` field across the three models — the local
   model often reports lower confidence overall, which is a *good* sign
   (it's calibrated to its own limitations).

---

## Stretch goals

If you have extra time:

- **Pull a bigger Ollama model** — `llama3.2:8b` or `qwen2.5:7b` — and
  add it to the comparison. The quality gap closes noticeably.
- **Time the streaming path.** Run `/ask` against `llama3.2:3b` and
  measure TTFT on your laptop. Local TTFT can be faster than hosted on
  short prompts because there's no network round-trip.
- **Privacy demo.** Disconnect from the internet. Run a question
  through Ollama. It works. That's the value proposition for any use
  case where data sensitivity rules out hosted APIs.

---

## Optional submit

There's no graded artefact for this activity, but if you write up your
three-way comparison as a short note (4-6 sentences), drop it into
`docs/lab4-ollama-activity.md` in your repo. It's the same evidence
pattern as the Lab 3d comparison note, just with three rows instead of
two — and it'll be useful at DR #1 if a stakeholder asks the inevitable
"have you considered local models?" question.
