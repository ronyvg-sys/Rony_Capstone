# AI-RAG · Week 6 · Activity

> Take-home. **Primary (~60 min)** is recommended for everyone.
> **Stretch (~90 min)** is optional, for learners with time and the
> appetite to swap an embedding model.
>
> Both activities are real interventions — they produce numbers that
> meaningfully change your W6 baseline understanding. Treat them as
> experiments and write up the results the same way you'd write up
> a snapshot row in `wk6-snapshot.md`.

---

## Activity A · Primary — Chunk-size sweep (~60 min)

You used `size=500, overlap=50` for the W6 baseline. But you chose
those numbers because that's what we said in the live build. Is that
the right choice for *your* corpus?

We'll run the same RAG eval against three different chunk-size choices,
compare retrieval hit rate across them, and write down a one-line
recommendation for next week.

### Why this matters

W7's section-aware chunking will land in a week. Before then, it's worth
knowing whether a simpler parameter tweak (just changing size + overlap)
gives you most of the upside. **Sometimes the boring intervention beats
the clever one.** This activity tells you whether that's true here.

### Step 1 · Plan the sweep (5 min)

Pick three (size, overlap) pairs to compare:

| Profile | size | overlap | Hypothesis |
|---------|------|---------|------------|
| Small   | 300  | 30      | Better precision; might split answers |
| Medium  | 500  | 50      | Your W6 baseline |
| Large   | 800  | 80      | Better recall; might dilute |

If your corpus has unusually short or long documents, adjust the upper
or lower ends. The goal is *meaningful spread* between the three, not
specific numbers.

### Step 2 · Build three indexes (15 min)

```bash
# Three independent indexes — pick distinct output paths
python scripts/build_index.py --corpus data/corpus \
    --size 300 --overlap 30 --out data/embeddings_small.json

python scripts/build_index.py --corpus data/corpus \
    --size 500 --overlap 50 --out data/embeddings_medium.json

python scripts/build_index.py --corpus data/corpus \
    --size 800 --overlap 80 --out data/embeddings_large.json
```

Each run is independent — no cache reuse across them.
Cost: ~$0.0001 per 100 chunks. For most corpora the total spend across
all three is well under $0.01.

### Step 3 · Run the eval three times (25 min)

```bash
# Symlink trick: run_rag_eval reads --index, so we point it at each
python scripts/run_rag_eval.py --label wk6-chunk-small  --index data/embeddings_small.json
python scripts/run_rag_eval.py --label wk6-chunk-medium --index data/embeddings_medium.json
python scripts/run_rag_eval.py --label wk6-chunk-large  --index data/embeddings_large.json
```

This is ~1 minute per run × 3 = 3 minutes of API calls + a couple of
minutes of waiting between. Total cost ~$0.05.

### Step 4 · Compute hit rate for each (10 min)

```bash
for label in wk6-chunk-small wk6-chunk-medium wk6-chunk-large; do
    echo "--- $label ---"
    python scripts/compute_kpis.py --metric retrieval_hit_rate --label "$label"
    python scripts/compute_kpis.py --metric cost_per_query     --label "$label"
done
```

Capture the numbers in a markdown table:

```markdown
| Profile | size | overlap | Hit rate | Cost / q | p95 latency |
|---------|------|---------|----------|----------|-------------|
| Small   | 300  | 30      | X / 20   | $X.XXXX  | X.Xs        |
| Medium  | 500  | 50      | X / 20   | $X.XXXX  | X.Xs        |
| Large   | 800  | 80      | X / 20   | $X.XXXX  | X.Xs        |
```

### Step 5 · Pick a winner + write the one-liner (5 min)

Add a section to your `docs/kpi/wk6-snapshot.md`:

```markdown
## Activity A — chunk-size sweep

Tested (300/30), (500/50), (800/80). Winner: <size>/<overlap>
because <one sentence: hit rate ↑ / cost ↓ / latency ↓ / specific
question type that improved>. Will keep this as the W7 starting point.
```

### What "done" looks like

- [ ] Three indexes built, three eval labels in `rag_runs`
- [ ] A 3-row comparison table in your snapshot
- [ ] A one-line recommendation for next week's chunker

### Things to look for

- If hit rate is **identical across all three** — your corpus is too
  small or too uniform for chunk-size to matter. That's a useful
  finding; note it.
- If **small wins** — your golden questions ask about specific facts
  that fit cleanly in 300 chars. Section-aware chunking (W7) will
  likely beat all three.
- If **large wins** — your documents have ideas that span multiple
  sentences/paragraphs. Section-aware chunking will probably help,
  but a smaller `large` (600/60) might be the sweet spot.
- If **medium wins by a lot** — your baseline pick was lucky. Treat
  this as a soft signal and don't over-tune.

---

## Activity B · Stretch — Local embeddings with sentence-transformers (~90 min)

OpenAI's `text-embedding-3-small` is fast, cheap, and good. But it sends
every chunk and every query to OpenAI. For privacy-sensitive corpora,
or cost-sensitive workloads at scale, a local embedding model is a real
alternative. This stretch activity swaps in `sentence-transformers`
(specifically `all-MiniLM-L6-v2`), re-runs the same golden set, and
compares.

### Why this matters

W7 covers embedding-model choice formally. Doing the swap once now
gives you intuition about what changes — concrete differences in cost,
latency, and quality, not abstract trade-off slides.

### Step 1 · Install sentence-transformers (15 min)

```bash
pip install --break-system-packages sentence-transformers
```

This downloads ~80MB of dependencies plus the `all-MiniLM-L6-v2` model
(~80MB) on first use. Heavy on the first call, but everything cached
after that. CPU-only is fine — the model is small.

### Step 2 · Build an `embed_local` function (15 min)

Create `src/rag/embeddings_local.py`:

```python
"""Local embeddings via sentence-transformers — 384-dim vectors, free."""
from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(text: str) -> list[float]:
    """Embed one string. Returns 384 floats."""
    return _get_model().encode(text, normalize_embeddings=True).tolist()
```

### Step 3 · Build a parallel index (20 min)

Make a copy of `build_index.py` as `scripts/build_index_local.py`,
swap the `embed` import to point at `embeddings_local`:

```python
# instead of:  from src.rag.store import build_store, ...
# patch via monkey-patch or just inline the build logic
```

Cleanest path: temporarily replace `embeddings.embed` with the local
one at runtime in a small wrapper script. Run it:

```bash
python scripts/build_index_local.py \
    --corpus data/corpus \
    --out data/embeddings_local.json
```

Cost: $0. Time: ~30s for ~100 chunks on CPU.

### Step 4 · Wire and run (25 min)

You'll need a parallel `ask_rag_local` that uses local embeddings for
both the query and the retrieve step. Save results under a new label:

```bash
python scripts/run_rag_eval.py --label wk6-local-embeds \
    --index data/embeddings_local.json --fake-only-chat=false
```

(If you don't want to write a fully parallel pipeline, do it in a
notebook — the goal is the numbers, not perfect code.)

### Step 5 · Compare the two on five questions (15 min)

For 5 of your 20 golden questions:

| Question | OpenAI top source | Local top source | Same? | Cosine OpenAI top | Cosine local top |
|----------|-------------------|------------------|-------|-------------------|------------------|
| g001     | leave_policy.md   | leave_policy.md  | ✓     | 0.71              | 0.55             |
| g002     | …                 | …                | …     | …                 | …                |

### Step 6 · Compute hit rate + write up (10 min)

```bash
python scripts/compute_kpis.py --metric retrieval_hit_rate --label wk6-local-embeds
```

Add to `wk6-snapshot.md`:

```markdown
## Activity B — local embeddings

Swapped OpenAI text-embedding-3-small → sentence-transformers
all-MiniLM-L6-v2 (384 dims, local, free).

| KPI            | OpenAI baseline | Local             | Δ              |
|----------------|-----------------|-------------------|----------------|
| Hit rate       | X / 20          | X / 20            | <better/worse> |
| Cost / q       | $0.0XX          | $0 (after setup)  | $$$$           |
| Latency p50    | X.Xs            | X.Xs              | …              |
| Setup time     | ~30s once       | ~30s (model load) | similar        |
```

One paragraph: which would you ship if your corpus were 10× bigger?

### What "done" looks like

- [ ] sentence-transformers installed, model downloaded
- [ ] A parallel index `data/embeddings_local.json` built
- [ ] 20 golden questions run through local embeddings
- [ ] Side-by-side comparison table with at least 5 specific question
  diffs noted
- [ ] One-paragraph recommendation

### Things to look for

- Local is **almost always cheaper** (free per query after setup).
- Local is **typically slightly worse** at retrieval — 384-dim vectors
  encode less information than 1536-dim ones. You'll probably see
  hit rate drop by 1-3 out of 20.
- Local is **faster per query** on CPU than the API round-trip
  (no network). Counter-intuitive but consistent.
- Local **does not** handle multilingual text as well — if your corpus
  has non-English chunks, expect bigger drops.

---

## Deliverables

For Activity A (everyone): added section to `wk6-snapshot.md` with
the 3-row sweep table + recommendation. Commit it.

For Activity B (optional): added section to `wk6-snapshot.md` with
the OpenAI-vs-local table + recommendation. Commit it.

Bring both to the W7 session opener — *"chunk-size sweep showed X;
local embeddings showed Y"* feeds directly into the W7 embedding-choice
discussion.

---

*End of W6 activity.*
