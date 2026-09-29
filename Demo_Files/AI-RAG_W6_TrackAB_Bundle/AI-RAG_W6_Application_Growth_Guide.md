# AI-RAG · Week 6 · Application Growth Guide

> **Take-home · self-paced · ~2 to 2.5 hours**
>
> Track A (the notebook you ran in class) taught you naive RAG in isolation.
> This document walks you through adding the same pattern to your capstone —
> the code changes are small and the application grows gradually.
>
> You already understand every function. This document is about **placement**:
> which files, which directory, which line of `main.py` changes.

---

## What's changing this week

### Before W6
Your capstone's `/ask_batched` endpoint calls `ask_llm(q, settings)` directly.
The LLM answers from its training data. The `sources` field on `Answer` exists
in the schema, but it's empty. Your API is a **thin wrapper around an LLM**.

### After W6
Your capstone's `/ask_batched` endpoint first **retrieves** the top-K most
relevant chunks from your document corpus, then calls the LLM with those chunks
in the prompt. The `sources` field now has real chunk IDs. Your API is a
**RAG system**.

### Size of the change
- **5 new files** (one directory, one module, one script, one data folder, one KPI snapshot)
- **~5 lines modified** in `src/api/main.py`
- **~80 lines of new code** total across the new module + script

Small footprint. Large capability increase. This is the pattern for the rest of Phase 2 — each week's application change should feel modest, because the concept was learned in Track A already.

---

## Prerequisites

Before starting:
- [ ] W1-W5 complete: FastAPI running, `ask_llm` working, golden set at `data/golden_set.jsonl`
- [ ] You've already run the Track A notebook (`demos/wk06_naive_rag_demo.ipynb`) end-to-end — that's the concept
- [ ] You have **10-20 real documents** you want to use as your capstone corpus (from your ADR)
- [ ] `OPENAI_API_KEY` in your `.env` (already there since W2)

Estimated cost for this week's work: **~$0.01-$0.05** (depends on corpus size — 20 documents × ~200 chunks × $0.02 per 1M embedding tokens ≈ 2 cents).

---

## What you'll add

Five new artifacts. Add them in this order.

### 1. `data/corpus/`
A folder. Drop your 10-20 policy documents inside — plain text (`.txt`) or
markdown (`.md`). File names become source IDs, so name them meaningfully
(`leave_policy.md` is better than `doc_1.txt`).

```bash
mkdir -p data/corpus
# drop your documents in here
ls data/corpus
```

Rough guideline: each document 500 to 5000 words. Very short (< 200 words)
won't chunk meaningfully; very long (> 10,000 words) is slow to embed.

### 2. `src/rag/` (new module)

```bash
mkdir -p src/rag
touch src/rag/__init__.py
```

Empty `__init__.py` — just marks the directory as a Python package.

### 3. `src/rag/naive_rag.py` (the main new file)

This is the naive RAG logic, distilled from the notebook. About 80 lines.

```python
"""Naive RAG for the capstone — W6.

Pure functions. Same pattern as the W6 demo notebook.
No frameworks (LangChain / LlamaIndex land in W11).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

from src.pipeline.settings import Settings

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o-mini"

_client = None
def _openai() -> OpenAI:
    """Lazy-init OpenAI client so imports don't require the key."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# ─── Chunking ────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Sliding window over characters."""
    if len(text) <= size:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        chunks.append(text[i:end])
        if end == len(text):
            break
        i = end - overlap
    return chunks


# ─── Corpus loading + indexing ───────────────────────────────────────

def load_corpus(corpus_dir: Path) -> list[dict]:
    """Load every .md and .txt file from corpus_dir, chunk each, return
    a flat list of {chunk_id, source_id, text}."""
    all_chunks = []
    for path in sorted(corpus_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for idx, chunk in enumerate(chunk_text(text)):
            all_chunks.append({
                "chunk_id":  f"{path.stem}#{idx}",
                "source_id": path.stem,
                "text":      chunk,
            })
    return all_chunks


def embed_batch(texts: list[str]) -> list[list[float]]:
    """One API call, list of vectors back."""
    resp = _openai().embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def build_index(chunks: list[dict]) -> list[dict]:
    """Attach a 'vector' field to each chunk. Returns the same list."""
    texts = [c["text"] for c in chunks]
    # Batch in groups of 100 to stay under API limits
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        vectors = embed_batch(batch)
        for chunk, vec in zip(chunks[i:i+100], vectors):
            chunk["vector"] = vec
    return chunks


def save_index(index: list[dict], path: Path) -> None:
    """Persist the indexed chunks to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False))


def load_index(path: Path) -> list[dict]:
    """Load a previously saved index."""
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Retrieval + generation ──────────────────────────────────────────

def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


def retrieve(query: str, index: list[dict], k: int = 3) -> list[dict]:
    q_vec = embed_batch([query])[0]
    scored = [(cosine(q_vec, c["vector"]), c) for c in index]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [{**c, "score": s} for s, c in scored[:k]]


SYSTEM = (
    "You are a helpful assistant. Answer the user's question using ONLY the "
    "provided context. If the context does not contain the answer, say so "
    "plainly. Cite the source id in square brackets after any fact you use."
)


def ask_rag(question: str, index: list[dict], settings: Settings,
            k: int = 3) -> dict[str, Any]:
    """Full naive RAG: retrieve → prompt → generate. Returns dict."""
    retrieved = retrieve(question, index, k=k)
    context = "\n\n".join(
        f"[{hit['chunk_id']}]\n{hit['text']}"
        for hit in retrieved
    )
    resp = _openai().chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content":
                f"Context:\n{context}\n\n---\n\nQuestion: {question}"},
        ],
    )
    return {
        "answer":     resp.choices[0].message.content,
        "sources":    [hit["chunk_id"] for hit in retrieved],
        "tokens_in":  resp.usage.prompt_tokens,
        "tokens_out": resp.usage.completion_tokens,
    }
```

**How to verify it works:**
```bash
python -c "
from pathlib import Path
from src.rag.naive_rag import load_corpus, build_index

chunks = load_corpus(Path('data/corpus'))
print(f'{len(chunks)} chunks from {len(set(c[\"source_id\"] for c in chunks))} documents')
"
```

Expected: a chunk count somewhere between 50 and 300 depending on your corpus.

### 4. `scripts/build_index.py` (one-off indexing script)

Runs the ingestion once so the API server has a pre-built index to load.

```python
"""Build the RAG index. Run once, or whenever the corpus changes."""
from pathlib import Path
from src.rag.naive_rag import load_corpus, build_index, save_index

CORPUS_DIR = Path("data/corpus")
INDEX_PATH = Path("data/embeddings.json")

print(f"Loading corpus from {CORPUS_DIR}...")
chunks = load_corpus(CORPUS_DIR)
print(f"  {len(chunks)} chunks loaded.")

print(f"Building embeddings (this may take a minute)...")
build_index(chunks)

print(f"Saving to {INDEX_PATH}...")
save_index(chunks, INDEX_PATH)
print(f"Done. Index has {len(chunks)} chunks.")
```

**Run it:**
```bash
python scripts/build_index.py
```

Expected output:
```
Loading corpus from data/corpus...
  156 chunks loaded.
Building embeddings (this may take a minute)...
Saving to data/embeddings.json...
Done. Index has 156 chunks.
```

Time: ~30 seconds for a modest corpus. Cost: ~1-2 cents.

### 5. `docs/kpi/wk6-snapshot.md` — first KPI snapshot

You'll fill this in after running the golden set (Section 6 below).

Create the file with this template:

```markdown
# wk6-snapshot.md — Naive RAG baseline

**Date:** YYYY-MM-DD
**Corpus:** N documents, M chunks
**Golden set:** 20 questions

## Headline numbers

| Metric | W6 baseline | Target for W7 |
|---|---|---|
| Cost per query (USD) | $0.000XXX | ↓ (embed cache) |
| Latency p50 (ms) | XXX | ↓ (vector DB, no full scan) |
| Retrieval hit rate | XX% | ↑ (structure-aware chunking) |
| Grounded response rate | XX% | ↑ (better retrieval) |
| Hallucination rate | XX% | ↓ (better retrieval) |

## Method
- Ran all 20 golden-set questions through `ask_rag` with k=3
- Judged with W5 `judge.py` (grounded rubric)
- Cost = embedding tokens (~$0.02/1M) + gpt-4o-mini tokens

## Top 3 limits observed
1. [Chunking cuts mid-sentence — example: chunk XX]
2. [Retrieval picks off-topic chunks for questions like: XX]
3. [Prompt doesn't always cite sources — example: question YY answered without brackets]

## What W7-W11 will improve
- W7: proper chunking + Qdrant vector DB
- W8: cost tracking via embedding cache
- W9: hybrid search (BM25 + dense) + rerank
- W10: caching + KB lifecycle
```

---

## What you'll modify

### `src/api/main.py` — one function call swap

Find the `/ask_batched` endpoint. Currently it looks something like:

```python
@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    answer = await ask_llm(q, _settings)   # ← W5: direct LLM call
    ...
```

Change it to:

```python
from pathlib import Path
from src.rag.naive_rag import ask_rag, load_index

# At module top, after `_settings = Settings()`:
_index = load_index(Path("data/embeddings.json"))

@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    result = ask_rag(q.question, _index, _settings)  # ← W6: RAG call
    answer = Answer(
        content=result["answer"],
        sources=result["sources"],
        cost_usd=(result["tokens_in"] * 0.15 + result["tokens_out"] * 0.60) / 1_000_000,
        # ... other fields as your W5 Answer schema requires
    )
    ...
```

That's it — about **5 lines changed**.

**How to verify:**
```bash
# 1. Restart the server
uvicorn src.api.main:app --reload

# 2. Ask a question
curl -X POST http://localhost:8000/ask_batched \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the leave policy?"}'
```

Expected response: JSON with a `content` field that references your actual
corpus content, and `sources` array with real chunk IDs (like `leave_policy#0`
or similar).

### `docs/adr/0001-capstone-framing.md` — add a W6 section

At the end of your ADR (which was locked in W5), append:

```markdown
## W6 — Naive RAG live

**Decision:** Naive RAG is now the default answer path. `/ask_batched` retrieves
top-3 chunks from `data/corpus/` before generating.

**Baseline KPIs** (see docs/kpi/wk6-snapshot.md):
- Cost/query: $0.000XXX
- Latency p50: XXX ms
- Grounded response rate: XX%

**Top 3 known limits** (to be addressed W7-W11):
1. Chunking cuts mid-sentence — W7 fixes with structure-aware chunker
2. Retrieval is pure dense — W9 adds BM25 hybrid
3. No metadata filtering — W7 introduces via Qdrant payload

**Status:** In production for the demo API. Not yet suitable for real users;
retrieval quality needs W7-W9 improvements first.
```

---

## Testing checklist

Before you consider W6 done:

- [ ] `data/corpus/` has 10-20 files
- [ ] `python scripts/build_index.py` completes without error
- [ ] `data/embeddings.json` exists and is 5-50 MB (depending on corpus size)
- [ ] `uvicorn src.api.main:app` starts with no import errors
- [ ] `curl -X POST /ask_batched -d '{"question": "..."}'` returns an answer
- [ ] The `sources` field in the response is populated (not empty)
- [ ] The answer text references actual corpus content (spot-check 3 questions)
- [ ] Answer format follows your W5 `Answer` schema

---

## Run the golden set

Use your existing eval runner from W5:

```bash
python scripts/run_eval.py --dataset data/golden_set.jsonl --output results.db
```

Adjust flags to match your W5 script exactly. If your `run_eval.py` doesn't
support the file paths, that's fine — just call `ask_rag` in a loop over your
golden set and save results manually.

The important thing: **all 20 golden-set questions answered by the new RAG
pipeline, results saved somewhere queryable.**

---

## Fill in the KPI snapshot

Open `docs/kpi/wk6-snapshot.md` and complete it with real numbers from your run.

Expected ranges on a typical enterprise corpus with naive RAG:

| Metric | Typical range | Interpretation |
|---|---|---|
| Cost/query | $0.0002 – $0.0005 | Naive RAG is cheap |
| Latency p50 | 1000 – 3000 ms | Full scan across chunks is slow |
| Retrieval hit rate | 60 – 80% | k=3 usually finds *something* relevant |
| Grounded response rate | 50 – 75% | Naive prompt + naive chunks = mixed |
| Hallucination rate | 10 – 25% | Retrieval finds wrong chunks → LLM invents |

**If your numbers are outside these ranges:**
- Grounded rate < 40% → your prompt isn't strong enough; check the SYSTEM string
- Retrieval hit rate < 40% → your chunks may be too large or too small
- Cost > $0.001/query → your prompts are longer than expected; check chunk sizes

These are **naive-RAG numbers**, not final numbers. Every remaining Phase 2
week will push them in the right direction.

---

## Common issues + fixes

**`ModuleNotFoundError: No module named 'src.rag'`**
You forgot the `__init__.py`. Add it: `touch src/rag/__init__.py`.

**Embedding API rate limits**
The `build_index` function already batches in groups of 100. If you still hit
limits (unlikely at W6 scale), add `time.sleep(0.5)` between batches.

**`data/embeddings.json` too big to commit**
Add it to `.gitignore`. It's a build artifact, regenerable via
`python scripts/build_index.py`.

**Retrieval returns clearly wrong chunks**
This is normal at naive RAG. Log 3 examples in your ADR under "Top 3 limits."
W7's structure-aware chunker + Qdrant will improve this materially.

**`sources` field not showing in API response**
Check your `Answer` pydantic model has `sources: list[str]`. If it does,
check that you're actually assigning `result["sources"]` to it in
`ask_batched`.

**Server takes 20+ seconds to start**
The `load_index(Path("data/embeddings.json"))` call at module top blocks until
the index is loaded. For a large corpus this can be slow. Acceptable at W6;
W7 fixes it by moving the index to Qdrant (server startup no longer blocks on
loading vectors into memory).

---

## What you should have when done

New files:
- `data/corpus/` (with your documents)
- `data/embeddings.json` (auto-generated)
- `src/rag/__init__.py`
- `src/rag/naive_rag.py`
- `scripts/build_index.py`
- `docs/kpi/wk6-snapshot.md`

Modified files:
- `src/api/main.py` (5 lines)
- `docs/adr/0001-capstone-framing.md` (W6 section added)

Total time: 2-2.5 hours if you already understood Track A. Longer if you need
to refer back to the demo notebook — that's fine, it's why the notebook exists.

---

## What's coming in W7

The naive-RAG limits you noted this week are what W7 addresses:

- **Better chunking** — structure-aware, respects sentence and paragraph boundaries
- **Qdrant vector DB** — no more full scan; sub-100ms retrieval regardless of corpus size
- **Embedding cache** — don't re-embed the same chunk twice (Layer 3 of what will become the W10 3-layer cache stack)

You'll extend `src/rag/naive_rag.py` — you'll rename it to `pipeline.py` and split retrieval into `retrieval.py`. The application growth stays gradual: mostly renaming and small function extractions, not rewrites.

---

*W6 Application Growth Guide. Track B of the two-track W6 pattern.*
