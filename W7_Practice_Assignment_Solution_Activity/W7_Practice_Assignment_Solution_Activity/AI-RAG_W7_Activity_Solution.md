# W7 Activity Solution — Local embeddings comparison

> *Instructor reference for the W7 take-home activity. Use this to
> review submissions, run office hours, and anticipate questions.*

**Activity time:** 60 min (optional stretch)
**Files involved:** `src/rag/embeddings_local.py`, `scripts/eval_local.py`, third Qdrant collection, `wk7-snapshot.md` addition

---

## What this activity is testing

Three outcomes:

1. **Hosted-vs-local intuition.** Most learners reach for OpenAI by
   default. This activity makes the trade-off concrete by running
   the swap on their own corpus.

2. **Vector-space awareness.** When you swap the embedding model,
   you must use the same model for the query too — otherwise the
   query lands in a different space and retrieval is random. This
   activity forces that pattern.

3. **The privacy argument lands earlier.** W8 covers PII formally,
   but the "everything stays on my machine" property of local
   embeddings is the cleanest preview. Doing the swap once now
   means W8's PII discussion feels grounded, not abstract.

---

## Reference solution walk-through

### The wrapper module

```python
# src/rag/embeddings_local.py
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_local(texts: list[str]) -> list[list[float]]:
    vecs = _get_model().encode(texts, normalize_embeddings=True,
                                 show_progress_bar=False)
    return vecs.tolist()
```

The lazy `_get_model()` matters — sentence-transformers' import is
slow (~3 seconds), so deferring it keeps the smoke-test fast.

### The third collection

```python
chunks = chunk_corpus("data/corpus")
texts = [c.text for c in chunks]
vectors = embed_local(texts)
store = build_store(
    chunks, vectors,
    embedding_model="all-MiniLM-L6-v2",
    dim=384,
    collection_name="capstone_chunks_local",
)
```

Spend: $0. Time: ~30s on CPU for 50 chunks (first run is +60s for
the model download).

### Expected numbers (sample, on the EKA reference corpus)

| KPI | OpenAI 3-small (1536 dim) | MiniLM-L6 (384 dim) | Δ |
|---|---|---|---|
| Hit rate | 14/20 (70%) | 12/20 (60%) | -2 points |
| Query embed cost | ~$0.00001 | $0 | -100% |
| Query latency p50 | 180ms (mostly network) | 35ms (CPU) | -145ms |
| Setup time | 30s one-time | 60s + download | +30s |
| Vector storage | 1536 × 4 bytes × N | 384 × 4 bytes × N | -75% |

Your numbers will vary — these are illustrative. On clean corpora,
the gap is sometimes 0-1 points. On corpora with proper nouns,
brand names, or technical jargon, the gap can widen to 5+ points.

### Where the gap usually shows

Three failure patterns to expect:

1. **Brand-name questions.** Q11 in the EKA golden set asks about
   "Notion subscription". MiniLM's training data has weaker
   coverage of specific brand names; it sometimes confuses
   "Notion" with "notion" (the generic word).

2. **Negation handling.** Q06 asks "Can I expense a co-working
   space membership?" The policy says "co-working space costs are
   NOT reimbursable." Smaller models sometimes lose the negation
   in lower-dimensional space.

3. **Cross-document questions.** Q20 asks about VPN-when-WFH,
   which spans two documents. Smaller embedding models have less
   capacity for this kind of multi-concept retrieval.

If a learner reports MiniLM failing on different patterns
(e.g. simple lookup questions), spot-check their normalisation —
that's the most common bug.

---

## What to look for in submissions

### Strong signals

- **Comparison table is complete** with all 4-5 KPI rows filled in
- **Per-question diff** identifies 3-5 specific failing questions
  (not generic statements like "MiniLM was worse")
- **Verdict paragraph** commits to a choice and defends it with
  specific numbers (not "depends on the use case")
- **Privacy framing** appears explicitly — even one sentence about
  "would matter if my capstone were medical / legal" is good
- **Normalisation note** — learner mentions `normalize_embeddings=True`
  somewhere (proves they noticed)

### Weak signals

- Numbers reported but no per-question analysis
- Verdict is vague (*"both are pretty good"*) — defeats the purpose
- No mention of why the gap exists (or might not exist)
- No mention of privacy / cost beyond restating the brief
- Missing third Qdrant collection — they did the embedding but
  not the storage migration

### Common mistakes

**Forgot to normalise.** Sentence-transformers doesn't normalise by
default. Without `normalize_embeddings=True`, cosine similarity in
Qdrant produces near-random rankings (because the dot-product
doesn't behave like cosine on unnormalised vectors).

Symptom: hit rate drops to ~5/20 (random baseline). Quick fix:
re-embed with normalisation.

**Queried with the wrong model.** Learner built the local
collection but used `embed()` (OpenAI) for the query. The query
lands in 1536-dim space; the chunks live in 384-dim space. Qdrant
refuses with a dimension-mismatch error.

Symptom: `ValueError: Wrong vector size at index 0`. Fix: use
`embed_local()` for the query too.

**Used the small model for queries, large for chunks (or vice versa).**
Same root cause as above. If hit rate is suspiciously low and no
dim-mismatch error appears, check which model populated the
collection vs which is being used for queries.

**Model download timed out on Vocareum.** Sentence-transformers
pulls from HuggingFace, which sometimes has connectivity issues
from sandboxed environments. Workaround: skip the activity (it's
optional) or download on a laptop and scp the cached model.

---

## Patterns to expect across the cohort

| Pattern | Frequency | What it tells you |
|---|---|---|
| Local 0-2 points lower than OpenAI | ~50% | Clean, well-formed corpus |
| Local 3-5 points lower | ~30% | Some brand names or technical jargon |
| Local 6+ points lower | ~15% | Multilingual, highly technical, or normalisation bug |
| Local higher than OpenAI | ~5% | Small clean corpus + good question phrasing; sometimes a coincidence |

If more than half the cohort reports 6+ point drops, the cohort
corpus is likely an outlier (multilingual, code-heavy, etc.) — not
a sign of a teaching failure.

---

## Office hours hot questions

**Q: My local hit rate is 4/20. Is local really this bad?**
No — that's the random baseline. Something is broken. Most likely:
(a) you forgot to normalise, (b) you queried with the wrong model,
or (c) you populated the collection with one model and queried
with another. Walk through normalisation first.

**Q: Can I use BGE-small instead?**
Yes. The pattern is identical — same `SentenceTransformer(...)`
call with a different model name. Expect slightly better hit rate
than MiniLM, slightly larger download (~150 MB).

**Q: Should I add the LLM generation step too?**
Optional — the activity is about retrieval, which is what changes
with the embedding swap. Adding generation doubles the API spend
and doesn't change the conclusions.

**Q: Vocareum can't download the model. What now?**
Skip the activity. The W7 deliverables don't depend on it. Note
in your wk7-snapshot that you tried but the environment didn't
support local embeddings.

**Q: Does this carry into W8?**
Not directly. W8 builds on the OpenAI-embedded Qdrant collection
from your lab work, not the local one. But the privacy framing
you developed here lands again in W8's PII discussion.

---

## Files in this solution package

- `embeddings_local_reference.py` — the wrapper module
- `eval_local_reference.py` — the eval script
- `sample_wk7-snapshot-activity-section.md` — what a strong
  submission's snapshot addition looks like

---

*End of W7 activity solution.*
