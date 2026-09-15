# W4 Activity Solution — Ollama as third model

> *Instructor reference for the W4 Ollama activity. Take-home,
> requires the learner's own laptop (Vocareum can't run Ollama).
> The point of this exercise is to feel the cost/quality trade-off
> concretely.*

**Activity time:** 30-45 min
**Prerequisites:** W4 Lab Step 3 completed (gpt-4o-mini + gpt-4o rows in `answers.db`)
**Files involved:** `src/pipeline/cost.py`, `src/pipeline/pipeline.py`, `scripts/compare_models.py`

---

## What this activity is testing

Three outcomes:

1. **Provider abstraction.** Same `ask_llm` code, different
   `base_url` and `api_key` — Ollama exposes an OpenAI-compatible
   endpoint, so the existing pipeline mostly *just works*.

2. **Cost reality.** Local is $0 marginal per call. The cost ratio
   between `gpt-4o` and `llama3.2:3b` is mathematically infinite.

3. **Quality reality.** A 3-billion-parameter model on a laptop is
   visibly worse than `gpt-4o-mini` on synthesis questions but
   surprisingly close on definitional questions.

This is the foundation for W5 (judge calibration across models),
W9 (rerank cost trade-offs), and any decision about hosted vs local
inference later in the programme.

---

## Reference solution walkthrough

### Step 3a — `cost.py` entry

```python
RATES = {
    "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o":      (2.50 / 1_000_000, 10.00 / 1_000_000),
    "llama3.2:3b": (0.0, 0.0),   # local — $0 marginal
}
```

The `(0.0, 0.0)` entry exists so `compute_cost_usd` doesn't branch on
provider type — same function handles all three.

### Step 3b — `_make_client` helper

```python
def _make_client(settings):
    """Return an AsyncOpenAI client pointed at the right backend.

    Ollama exposes an OpenAI-compatible endpoint at localhost:11434/v1
    so we can reuse the OpenAI SDK with a different base_url.
    """
    if settings.model.startswith("llama") or settings.model.startswith("ollama:"):
        return AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # any string — Ollama ignores it
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)
```

Then replace the `AsyncOpenAI(...)` calls in `ask_llm` and
`stream_answer` with `_make_client(settings)`.

### Smoke test expected output

```
content   : RAG (Retrieval-Augmented Generation) combines a retriever that fetches relevant context with a generator that produces the final answer using that context...
confidence: 0.78
sources   : ['knowledge_base', 'documentation']
cost_usd  : 0.0
```

The `cost_usd: 0.0` is the visible win. Confidence is *usually*
lower than gpt-4o-mini (calibrated to model's actual capability).

### Expected three-way comparison output

```
model        n     total_cost_usd  avg_cost_usd  avg_confidence
-----------  ----  --------------  ------------  --------------
gpt-4o       10    0.013648        0.001365      0.91
gpt-4o-mini  10    0.000832        0.000083      0.87
llama3.2:3b  10    0.000000        0.000000      0.75
```

Specific patterns to expect:

- **gpt-4o is ~16x more expensive than gpt-4o-mini**, ~infinitely
  more expensive than local
- **Average confidence drops** as model size decreases — usually a
  *good* sign (the model knows what it doesn't know)
- **Total time** varies massively: hosted ~0.5-2s per call, local
  2-15s per call depending on hardware

### Where the quality gap shows up

The schema-versioning question (Q10) is the canonical "synthesis"
question. Sample diff:

**gpt-4o-mini answer:**
> Schema versioning is the practice of tracking changes to a database
> schema over time, typically using migration files that are applied
> sequentially. This allows you to evolve the schema safely, roll back
> changes, and keep multiple environments (dev/staging/prod) in sync.

**llama3.2:3b answer:**
> Schema versioning means adding a version number to your schema so
> you know which version you're using.

Both are technically correct, but the small model misses the *why*
(safety, rollback, environment sync). This is the synthesis-vs-recall
gap.

---

## What to look for in submissions

**Strong signals:**
- All three models present in `data/answers.db` with the same set of
  10 questions
- Three-way comparison table with `total_cost_usd`, `avg_cost_usd`,
  `avg_confidence`
- Reflection identifies at least one concrete quality gap (with
  evidence — specific question + diff)
- Either privacy or cost-iteration use case named as the value
  proposition for local

**Weak signals:**
- Only Ollama row present (didn't do Lab Step 3 first)
- Reflection that says *"local is worse"* without specifics
- No mention of the cost ratio
- Missing or zero confidence on Ollama rows (indicates tool-calling
  failure and the fallback wasn't applied)

**Common mistakes:**
- Forgot the `cost.py` entry for `llama3.2:3b` — `compute_cost_usd`
  errors out
- Used `OpenAI()` instead of `AsyncOpenAI()` — async pipeline breaks
- Tool-calling silently failing on Ollama, returning empty content;
  fallback to JSON mode not applied
- Tried to run on Vocareum (it can't — clarify in office hours)

---

## Stretch outcomes

For learners who attempted the stretch:

- **`llama3.2:8b` or `qwen2.5:7b`.** Quality gap narrows
  significantly. Expect avg_confidence closer to 0.85.
- **TTFT measurement.** Local TTFT *can* be faster than hosted on
  short prompts (no network round-trip). Counter-intuitive but
  consistent.
- **Privacy demo.** Disconnect from the internet, query Ollama, get
  an answer. The killer use case for any regulated industry.

---

## Office hours hot questions

- *"Vocareum can't run Ollama, right?"* — Correct. Skip this activity
  if you don't have your own laptop with ≥8GB RAM. It's optional.
- *"Why doesn't my tool-calling work with Ollama?"* — llama3.2:3b's
  tool-calling compliance is shaky. Apply the JSON-mode fallback.
- *"Should I add Ollama to the W4 lab's required output?"* — No, the
  lab requires the two OpenAI models. Ollama is the take-home extension.
- *"Is local always the right choice for development?"* — No. Local
  is right when (a) cost matters and (b) you can tolerate the
  quality gap. For production, the right answer is almost always
  hosted unless privacy/compliance rules it out.

---

## Files in this solution package

- `ollama_integration_snippet.py` — the `_make_client` helper +
  `cost.py` entry + tool-calling fallback
- `compare_three_models.py` — the SQL-based three-way comparison
  script
- `sample_three_way_output.md` — expected output table + question
  diff
- `sample_lab4-ollama-activity.md` — what a strong learner submission
  looks like

---

*End of W4 solution.*
