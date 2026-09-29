# W6 Activity Solution — Chunk-size sweep + Local embeddings

> *Instructor reference for the W6 take-home. Two activities —
> Activity A (chunk-size sweep, primary, 60 min) and Activity B
> (local embeddings, stretch, 90 min).*

**Activity time:** 60 min (primary) + 90 min (stretch)
**Prerequisites:** W6 lab complete — naive RAG running, golden set
exists, `build_index.py` + `run_rag_eval.py` + `compute_kpis.py` work
**Files involved:** `data/embeddings_*.json`, `wk6-snapshot.md`

---

## What this activity is testing

**Activity A — Chunk-size sweep:** Can the learner run the *same*
measurement loop they ran for the W6 baseline, three times with
different chunk-size choices, then make a defensible recommendation?
This is the engineering-experimentation discipline being practised
before W7 formalises it.

**Activity B — Local embeddings:** Does the cohort have hands-on
intuition for the cost/quality trade-off when swapping embedding
backends? This previews W7 (embedding-model experiments) but
focuses on the *concrete numbers*, not the abstract framing.

---

## Activity A — Reference walkthrough

### The three profiles

The activity prescribes:

| Profile | size | overlap |
|---|---|---|
| Small | 300 | 30 |
| Medium | 500 | 50 (W6 baseline) |
| Large | 800 | 80 |

These are deliberately spread to expose any chunk-size sensitivity
in the learner's corpus.

### Expected results (illustrative — real numbers vary by corpus)

| Profile | size | overlap | Hit rate | Cost / q | p95 latency |
|---------|------|---------|----------|----------|-------------|
| Small   | 300  | 30      | 13 / 20  | $0.00018 | 1.1s        |
| Medium  | 500  | 50      | 14 / 20  | $0.00021 | 0.9s        |
| Large   | 800  | 80      | 14 / 20  | $0.00023 | 0.8s        |

Most common pattern: **all three are within 1-2 hit-rate points of
each other**. Chunk-size sensitivity is corpus-dependent and on a
small clean corpus rarely produces a clear winner.

### Patterns to expect across the cohort

| Pattern | Frequency | What it means |
|---|---|---|
| All identical | ~30% | Corpus too small/uniform for chunk size to matter |
| Small wins by 1-2 | ~25% | Questions ask about specific facts that fit in 300 chars |
| Medium wins | ~30% | The baseline pick was lucky; don't over-tune |
| Large wins by 1-2 | ~15% | Documents have ideas spanning multiple sentences |

### What a strong submission looks like

```markdown
## Activity A — chunk-size sweep

Tested (300/30), (500/50), (800/80). Winner: 500/50 (medium).

| Profile | Hit rate | Cost/q | p95 |
|---------|----------|--------|-----|
| Small   | 13/20    | $0.00018 | 1.1s |
| Medium  | 14/20    | $0.00021 | 0.9s |
| Large   | 14/20    | $0.00023 | 0.8s |

Hit rate range was 1 point across all three profiles, so chunk
size is not a high-leverage variable for my corpus. Sticking with
500/50 because it's the lowest-cost configuration that hits the
top number. Will revisit in W7 with section-aware chunking, which
should give a real lift if my corpus has internal structure.
```

The qualities: actual numbers, decision rule explicit ("lowest
cost at top hit rate"), connects to next week.

### What a weak submission looks like

- Doesn't include the comparison table
- Picks a winner without justification ("I'll use medium because
  it feels right")
- Misses that the spread is small (treats 14 vs 14 as different)
- No recommendation for W7

---

## Activity B — Reference walkthrough

### The setup (Step 1-3)

```bash
pip install --break-system-packages sentence-transformers
```

Then a small `embeddings_local.py`:

```python
from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(text: str) -> list[float]:
    return _get_model().encode(text, normalize_embeddings=True).tolist()
```

### Expected results (illustrative)

| KPI | OpenAI baseline | Local | Δ |
|---|---|---|---|
| Hit rate | 14 / 20 | 13 / 20 | -1 |
| Cost / q | $0.00021 | $0 (after setup) | savings: 100% |
| Latency p50 | 0.9s | 0.5s | -0.4s |
| Setup time | ~30s once | ~30s (model load) | similar |

### The patterns to expect

1. **Local is 1-3 points worse on hit rate**, not catastrophically
   worse. 384-dim vectors encode less than 1536-dim, but the
   semantic signal survives for most questions.

2. **Local is faster per query** on CPU — no network round-trip.
   This is counter-intuitive (people assume local is slow) but
   consistent.

3. **Local is free per query.** Cost ratio is mathematically
   infinite once the model is downloaded.

4. **Local handles multilingual badly.** If the corpus has
   non-English chunks, the drop is bigger (5-10 points). For
   the EKA's English-only corpus, the drop is small.

### What a strong submission looks like

A comparison table covering at least 5 specific questions:

| Question | OpenAI top source | Local top source | Same? |
|----------|-------------------|------------------|-------|
| g001 | leave_policy.md | leave_policy.md | ✓ |
| g004 | leave_policy.md | wfh_policy.md | ✗ |
| g010 | expense_policy.md | expense_policy.md | ✓ |
| g015 | vpn_setup.md | vpn_setup.md | ✓ |
| g020 | wfh_policy.md | vpn_setup.md | ✗ |

Plus a one-paragraph recommendation:

> If my corpus were 10× bigger, I'd still ship OpenAI for the EKA.
> The 1-point hit-rate drop is acceptable, but the cost savings
> ($0.00021 × 100k queries = $21/month) don't justify the
> operational overhead of running a local model in production. If
> I were shipping a privacy-sensitive product (medical, legal,
> regulated industries), the calculus flips — local becomes the
> obvious choice and the quality gap is the price of compliance.

### What a weak submission looks like

- No comparison table
- Reports only aggregate numbers, no question-level diffs
- Recommendation that doesn't engage with the trade-off
  ("local is cheaper so use local")
- Doesn't mention privacy or scale considerations

---

## Office hours hot questions

- *"My hit rate is identical across all three chunk sizes. Is that
  a bug?"* — No, that's a useful finding. Your corpus is too small
  or too uniform for chunk size to matter. Document and move on.
- *"Sentence-transformers download is slow / failing."* — First-run
  downloads ~80MB. On flaky networks, try `pip install -v`. If it
  fails entirely, skip Activity B — Activity A is the primary.
- *"Should I run the W7 lab now since I already know the answer?"*
  — No. W7 formalises this with multiple variables (embedder ×
  chunker), and the discipline of running the experiment yourself
  matters more than the result.
- *"Can I add more chunk-size profiles?"* — Yes, but 3 is enough
  to detect a pattern. Diminishing returns above 5.

---

## Common pitfalls

- **Same index for all three labels.** Learner forgets to use
  distinct `--out` paths and the second run overwrites the first.
  Spot-check: are there 3 distinct files in `data/embeddings_*.json`?
- **Hit rates near 100%.** Means the golden set is too easy for any
  chunk size to matter. Acceptable but worth noting.
- **Local model loaded inside the query loop.** Adds ~5s per query.
  Use the `_get_model()` lazy-loading pattern.
- **`build_index_local.py` not actually using the local embedding.**
  Spot-check: do the vector dimensions in `embeddings_local.json`
  match 384 (MiniLM-L6) rather than 1536 (OpenAI-small)?

---

## Files in this solution package

- `embeddings_local.py` — the sentence-transformers wrapper
- `build_index_local.py` — modified build_index that uses local
  embeddings
- `chunk_sweep_runner.sh` — convenience runner for Activity A
- `sample_wk6-snapshot-additions.md` — what the additions to
  wk6-snapshot.md look like for both activities

---

*End of W6 solution.*
