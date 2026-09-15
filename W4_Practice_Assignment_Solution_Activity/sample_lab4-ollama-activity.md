# W4 Activity — Ollama three-way comparison

## Setup

- Ollama installed via macOS installer; `llama3.2:3b` pulled (~2 GB)
- `cost.py` updated with `"llama3.2:3b": (0.0, 0.0)` entry
- `pipeline.py` updated with `_make_client` helper
- 10 questions run through all three models

## Three-way comparison (from `data/answers.db`)

```
model         n     total_cost_usd   avg_cost_usd   avg_confidence
gpt-4o        10    0.013648         0.001365       0.91
gpt-4o-mini   10    0.000832         0.000083       0.87
llama3.2:3b   10    0.000000         0.000000       0.75
```

**Cost ratios:** gpt-4o is ~16× more expensive than gpt-4o-mini.
Local is *infinitely* cheaper than either (assuming the hardware is
sunk cost).

## Where the quality gap shows

The schema-versioning question (Q10) — a synthesis question
requiring multiple ideas — is where the gap is most visible.

**gpt-4o:**
> Schema versioning is the practice of tracking changes to a
> database schema systematically over time. It typically involves
> using migration files numbered sequentially, allowing you to
> evolve the schema safely, roll back problematic changes, and
> keep multiple environments (dev, staging, prod) in sync. Tools
> like Alembic, Flyway, or Liquibase formalise this pattern...

**llama3.2:3b:**
> Schema versioning means adding a version number to your schema so
> you can track which version is in use.

Both are technically correct, but llama3.2:3b misses the *why* —
safety, rollback, environment sync. This is the synthesis vs.
recall gap.

## Reflection

Three observations:

1. **Local is genuinely free.** The cost ratio between hosted and
   local is mathematically infinite. For development iteration
   where I'm tweaking prompts and re-running the same questions
   100x, this is a big deal.

2. **The quality gap is real but narrower than I expected.** On
   definitional questions ("what is RAG?", "what is a token?"),
   llama3.2:3b is fine. On synthesis ("compare X and Y", "why is X
   designed that way?"), gpt-4o-mini is clearly better.

3. **Confidence numbers self-correct.** Average confidence drops as
   model size drops — 0.91 → 0.87 → 0.75. That's a *good* sign —
   the smaller model knows its limitations and reports them honestly.

If I were shipping a privacy-sensitive product (medical records,
legal documents), local would be the obvious choice and the quality
gap would be acceptable. For everything else, gpt-4o-mini is the
sweet spot — cheap enough to use freely, smart enough for most
real questions.
