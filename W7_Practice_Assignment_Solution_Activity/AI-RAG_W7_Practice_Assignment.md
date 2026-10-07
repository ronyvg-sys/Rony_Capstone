# AI-RAG · Week 7 · Activity
## Local embeddings — when free beats hosted

> Take-home. ~60 minutes. **Optional stretch.** Skip if you're
> behind on the lab — the W7 deliverables don't depend on this.
>
> This activity is for learners who want to feel the
> hosted-vs-local trade-off concretely. We swap OpenAI's embedding
> model for a local one (`sentence-transformers/all-MiniLM-L6-v2`)
> and re-run the W7 comparison.

---

## Why this matters

Topic 1 introduced four model options. Two were hosted (OpenAI
small + large). Two were local (BGE, Nomic). Lab Step 2 compared
the two hosted models on your corpus.

This activity completes the picture: **what changes when you swap
hosted for local?** Specifically:

- Cost per query drops to zero (after the model downloads)
- Latency may actually drop (no network round-trip)
- Vector dimensionality drops from 1536 → 384 (less information)
- Hit rate usually drops 1-3 points (the price of compression)
- Privacy posture flips from "every query sent to OpenAI" to "nothing leaves your machine"

If you ever ship RAG at scale, this trade-off matters. Doing the
swap once now gives you intuition you'll keep using.

---

## Prerequisites

- Lab Steps 1-3 completed (Qdrant migration + embedding comparison + KPI snapshot)
- ~80 MB of disk space (the sentence-transformers model + dependencies)
- About 60 minutes of focused time

---

## Step 1 · Install sentence-transformers (5 min)

```bash
pip install sentence-transformers
```

This pulls in ~500 MB of dependencies (PyTorch is the big one). On
Vocareum or constrained machines, this may take 2-3 minutes.

Smoke-test the install:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
vec = model.encode("hello world", normalize_embeddings=True)
print(f"Dim: {len(vec)}")   # 384
print(f"First few: {vec[:5]}")
```

First call downloads the model (~80 MB). Subsequent calls reuse it.

---

## Step 2 · Build a local-embeddings wrapper (10 min)

Create `src/rag/embeddings_local.py`:

```python
"""Local embeddings via sentence-transformers — 384 dim, free."""

# Lazy-load the model: first call downloads + caches it
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_local(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns 384-dim vectors, normalised."""
    vecs = _get_model().encode(texts, normalize_embeddings=True,
                                 show_progress_bar=False)
    return vecs.tolist()
```

Why normalise? OpenAI normalises by default; sentence-transformers
doesn't unless you ask. Forcing it here means cosine and dot product
behave equivalently — which matches our W7 metric choice.

---

## Step 3 · Build a third Qdrant collection (15 min)

You already have `capstone_chunks` (small) and possibly
`capstone_chunks_large` (3-large). Add a third:

```python
from src.rag.chunker import chunk_corpus
from src.rag.embeddings_local import embed_local
from src.rag.qdrant_store import build_store

chunks = chunk_corpus("data/corpus")
texts = [c.text for c in chunks]

print("Embedding locally (first run downloads model ~80MB)...")
vectors = embed_local(texts)

store = build_store(
    chunks, vectors,
    embedding_model="all-MiniLM-L6-v2",
    dim=384,
    collection_name="capstone_chunks_local",
)
print(f"Collection populated: {len(vectors)} chunks.")
```

About 30 seconds on CPU for a 50-chunk corpus, no API spend.

---

## Step 4 · Run the golden set against the local collection (15 min)

You'll need a `qdrant_rag_local.py` variant that uses local
embeddings for the QUERY too (since the query needs to be in the
same vector space as the chunks):

```python
# scripts/eval_local.py — minimal eval against the local collection
import json, time
from pathlib import Path

from src.rag.embeddings_local import embed_local
from src.rag.qdrant_store import load_store, retrieve

store = load_store(
    collection_name="capstone_chunks_local",
    embedding_model="all-MiniLM-L6-v2",
    dim=384,
)

golden = [json.loads(l) for l in
          Path("data/golden_set_full.jsonl").read_text().splitlines() if l.strip()]

hits = 0
latencies = []
for entry in golden:
    t0 = time.time()
    query_emb = embed_local([entry["question"]])[0]
    chunks = retrieve(store, query_emb, k=3)
    latencies.append(int((time.time() - t0) * 1000))
    sources = [c.source for c in chunks]
    if entry.get("expected_source", "") in sources:
        hits += 1
    print(f"  {entry['id']}: hit={entry.get('expected_source', '') in sources}")

print(f"\nHit rate: {hits}/{len(golden)} ({100*hits/len(golden):.0f}%)")
print(f"p50 latency: {sorted(latencies)[len(latencies)//2]}ms")
```

This skips the LLM generation step — we're only measuring
retrieval, which is what changes with the embedding swap. (Adding
the LLM step is straightforward but doubles the spend.)

---

## Step 5 · Write the comparison (10 min)

Add a section to `docs/kpi/wk7-snapshot.md`:

```markdown
## Activity — hosted vs local embeddings

Compared OpenAI text-embedding-3-small (hosted, 1536 dim) vs
sentence-transformers all-MiniLM-L6-v2 (local, 384 dim) on the
same golden set + same Qdrant infrastructure.

| KPI | OpenAI 3-small | Local MiniLM-L6 | Δ |
|---|---|---|---|
| Hit rate | __ / 20 | __ / 20 | __ |
| Query embed cost | $______ | $0 (after setup) | -100% |
| Query latency p50 | ___ms | ___ms | __ |
| Setup time first run | ~30s once | ~60s once (model download) | ~2× |
| Vector storage | 1536 floats × N | 384 floats × N | 4× smaller |
| Privacy | every query → OpenAI | nothing leaves machine | major shift |

### Per-question patterns I noticed

> *(Pick 3-5 golden questions where the local model retrieved a
> different source than OpenAI. Note which one was right.)*

- gNN: question about XYZ. OpenAI got `_____.md` (correct). Local
  got `_____.md` (wrong because ...).
- ...

### Verdict for my capstone

> *(One paragraph: would you ship local? Why or why not?)*
```

---

## Step 6 · Reflect on the trade-off (5 min)

Three things to write about, briefly:

1. **The cost win.** Local is genuinely free per query (after the
   model downloads). At what query volume would this start to
   matter for your capstone? (Hint: 10k queries/day at $0.0001/q
   is ~$1/day. Not life-changing for most projects, but real.)

2. **The privacy win.** This is the *killer use case* — corpora
   that can't legally leave your machine (medical, legal,
   regulated industries). For those, the small hit-rate drop is
   the price of compliance.

3. **The quality price.** You'll usually lose 1-3 hit-rate points.
   Sometimes more on multilingual or highly technical corpora.
   Worth it when privacy or cost matters; not worth it when
   neither does.

---

## What "done" looks like

- [ ] `src/rag/embeddings_local.py` committed
- [ ] `scripts/eval_local.py` (or notebook equivalent) runs
- [ ] Third Qdrant collection populated (`capstone_chunks_local`)
- [ ] Comparison table added to `wk7-snapshot.md`
- [ ] Verdict paragraph written

Bring your numbers to the W8 session opener — *"local embeddings
gave me X hit rate vs Y for OpenAI"* is the kind of grounded
finding that anchors the W8 PII + ingestion discussion (where the
privacy argument becomes much more concrete).

---

## Things to look out for

### "My local hit rate is 8 points lower than OpenAI."

Possible causes, in order of likelihood:

1. **Your corpus has lots of proper nouns or domain jargon.**
   384-dim models struggle more with rare-word retrieval. Check
   which questions failed — likely the ones with specific names
   or technical terms.

2. **Your queries are short and the chunks are long.** Smaller
   models lose more signal with length asymmetry. Check if the
   failing questions are unusually short.

3. **You forgot to normalise.** Setting
   `normalize_embeddings=True` in the encode call is critical for
   cosine similarity to work correctly.

If hit rate dropped by 8+ points and the above don't explain it,
flag for office hours.

### "My local hit rate is HIGHER than OpenAI."

Possible — sometimes happens on clean corpora with well-formed
questions. Document it. Don't over-interpret a single comparison —
run it again with `temperature=0` (no LLM in this path so
temperature doesn't apply, but if you added the LLM step, set it
to 0) to confirm.

### "Model download is slow / times out."

Try `pip install -v sentence-transformers` to see where it's
stuck. If the model itself fails to download:

```python
from sentence_transformers import SentenceTransformer
import os
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"   # 5 min timeout
model = SentenceTransformer("all-MiniLM-L6-v2")
```

If that still fails, skip the activity — it's optional.

---

## Why MiniLM-L6-v2 and not BGE or Nomic?

Honest reasoning:

- **MiniLM-L6-v2** is small (~80 MB), well-supported, widely cited.
  The canonical "default local model" in the sentence-transformers
  ecosystem. Fast to download, fast to run on CPU.

- **BGE-small** is a stronger model on benchmarks but ~3× larger
  download. Worth trying if you have time after MiniLM.

- **Nomic-embed-text-v1.5** is excellent but has a less standard
  interface — you'd need to read their docs to swap it in cleanly.
  Save for a separate exploration.

MiniLM is the right "first local model" experience. Once you have
the pattern, swapping to BGE or Nomic is a one-line change.

---

*End of W7 activity.*
