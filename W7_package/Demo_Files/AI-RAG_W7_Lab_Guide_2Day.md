# AI-RAG · Week 7 · Lab Guide
## Embeddings + Vector DBs — Concept Demo

> **Two 90-minute in-session notebooks · standalone Jupyter · Track A**
>
> **Day 1:** Embedding space intuition + first Qdrant call.
> **Day 2:** Qdrant tour — indices, similarity metrics, mini-RAG on top.
>
> Both notebooks use a small animal corpus with nothing to do with your capstone.
> That's on purpose — Track A teaches the mechanics in isolation.
>
> **After the two sessions:** work through `AI-RAG_W7_Application_Growth_Guide.md`
> to migrate your capstone from W6's JSON cache to Qdrant (self-paced take-home).

---

## Package contents

Inside `demos/`:

| File | Session | Purpose |
|---|---|---|
| `wk07_day1_embedding_space.ipynb` | Day 1 (90 min) | Embedding models, semantic geometry, first Qdrant call |
| `wk07_day2_qdrant_tour.ipynb` | Day 2 (90 min) | Indices, metrics, mini-RAG on Qdrant |
| `wk07_pipeline.py` | Helper | Shared corpus + functions Day 2 imports from |

---

## Prerequisites (both days)

- [ ] Vocareum notebook environment (or local Jupyter with Python 3.10+)
- [ ] `openai`, `qdrant-client`, `numpy` installed
- [ ] `OPENAI_API_KEY` set
- [ ] `QDRANT_URL` + `QDRANT_API_KEY` set (Qdrant Cloud free tier — sign up at cloud.qdrant.io)

**Sign-up walk-through:** See `AI-RAG_W7_Qdrant_Cloud_Credentials.md` in your
cohort resources. Takes about 5 minutes; the free tier is enough for the whole
programme.

**Cost across both notebooks:** ~$0.02 in OpenAI credits. Qdrant is free.

---

## Day 1 · `wk07_day1_embedding_space.ipynb` (90 min)

Aligned to deck slides 7-17 — embedding models + vector DB landscape (Day 1 is
conceptual per deck slide 4).

### What we do

Explore what embedding models actually produce, build intuition for semantic
geometry, tour the vector-DB landscape, and end by making our first Qdrant call.

**Corpus:** 10 short paragraphs about animals — 2 mammals, 2 birds, 2 fish, 2
reptiles, 2 insects. Chosen so semantic clustering across categories is
interesting to explore.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1-2 | Setup + animals corpus | 8 min |
| 3 | Quick recap — what an embedding is | 5 min |
| **4** | **Compare 3-small vs 3-large** — same sentence, different vectors, different dims | **10 min** |
| **5** | **Does the larger model discriminate better?** — cosine on same/related/distant pairs | **10 min** |
| 6 | What dimension buys you — storage cost math at scale | 5 min |
| **7-9** | **Semantic geometry** — embed all 10, print pairwise cosine matrix, print top-3 neighbours per animal | **20 min** |
| 10 | Vector DB landscape — FAISS / Chroma / Qdrant / pgvector reference cards | 10 min |
| 11 | Connect to Qdrant Cloud (or local Docker) | 5 min |
| 12 | Create a collection with cosine metric + 1536 dims | 5 min |
| 13 | Upsert all 10 animals with payload metadata | 5 min |
| 14 | First retrieval — 4 test queries, top-3 each | 12 min |
| 15 | Wrap — 4 things learned; preview of Day 2 | 5 min |

**Bold cells are discussion-heavy blocks** — where instructor pauses to build intuition with the group.

### Discussion moments built in

- **Cell 5:** did `3-large` clearly out-discriminate `3-small`? At 6.5× cost, worth it?
- **Cell 8** (semantic geometry matrix): which cross-category matches surprise you? Do reptiles group with mammals or fish?
- **Cell 9:** what fraction of top-neighbours are in the same category? Rough measure of alignment.
- **Cell 14:** did the pet-question return cat + dog + gecko? (Gecko IS a pet — model gets it right.)

### What learners take away from Day 1

1. Concrete feel for what different embedding models produce (dim, cost, discrimination)
2. Intuition for semantic geometry (categories cluster; clustering is emergent)
3. Working Qdrant connection tested end-to-end BEFORE Day 2 depends on it
4. Understanding of why we picked Qdrant vs FAISS/Chroma/pgvector

### What Day 1 does NOT do

- HNSW / IVF (Day 2)
- Similarity metric comparison (Day 2)
- Full mini-RAG on Qdrant (Day 2)
- Anything capstone-related (Track B)

---

## Day 2 · `wk07_day2_qdrant_tour.ipynb` (90 min)

Aligned to deck slides 18-32 — indices, similarity metrics, live migration walkthrough.

### What we do

Same animals corpus (imported from `wk07_pipeline.py`). Now we go deeper on
what makes Qdrant fast (indices), what breaks silently if you pick the wrong
metric, and how to assemble a full mini-RAG on top of Qdrant.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup + import Day 1's helpers | 3 min |
| 2 | Reconnect to Qdrant + embed the corpus | 5 min |
| **3-4** | **The problem indices solve** — linear scan timing at 10, 100, 1K, 10K docs | **10 min** |
| 5 | HNSW with Qdrant defaults — show `m`, `ef_construct`, `full_scan_threshold` | 5 min |
| **6** | **HNSW tuned for higher recall** — `m=32, ef_construct=200`, discuss trade-offs | **10 min** |
| 7 | Query both HNSW collections; results match at this scale | 5 min |
| **8-9** | **Qdrant quantization** — enable scalar quantization, compare storage cost | **10 min** |
| 10 | Create three collections, one per distance metric | 5 min |
| 11 | Metric ranges compared — cosine, dot, L2 on same pair | 5 min |
| 12 | Programme default: cosine. Why. | 3 min |
| **13** | **The silent-bug pattern** — non-normalised vectors + dot product = wrong rankings that look fine | **12 min** |
| **14-15** | **Mini-RAG on Qdrant** — ask_qdrant_rag(); run all 5 test questions | **15 min** |
| 16 | Cleanup — delete demo collections | 2 min |
| 17 | Wrap + hand-off to Track B | 5 min |

**Bold cells are the pedagogical peaks** — where the concept lands hardest.

### Discussion moments built in

- **Cell 4** (index trade-offs): 10K linear scan takes ~700ms in the demo; at 10M it'd be minutes. Sets up "why indices."
- **Cell 6:** at production scale, `m=32` gives better recall at 2× memory. At our scale, both collections behave identically — teach the PARAMETER, not the behaviour.
- **Cell 9** (quantization): at 10 animals, saves 45 KB. At 10M vectors, saves 45 GB. Same idea, wildly different value.
- **Cell 13** (silent bug): **this is the memorable moment.** Cosine correctly ranks salmon + shark. Dot product ranks salmon + ant (because ant was scaled 3× for no reason). The bug is deployed and quietly wrong — cosine prevents it entirely.
- **Cell 15:** the pet question — did cat + dog + gecko come back?

### What learners take away from Day 2

- What HNSW does + concrete recall/speed/memory trade-offs (parameters `m`, `ef_construct`)
- What quantization is + when it's worth it (scale)
- Three metrics compared; why cosine is the safe default
- The silent-bug pattern made visible: non-normalised vectors × wrong metric = trouble
- A working Qdrant-backed mini-RAG (mental model for Track B migration)

### What Day 2 does NOT do

- Learner's capstone corpus (Track B)
- Embedding cache mechanics (already in W6; extended in Track B)
- Metadata filtering (W8)
- Advanced Qdrant features: payload indexes, collections management (W8/W10)

---

## How the two days connect

- **Day 1** builds functions inline in the notebook
- **Day 2** imports the same functions from `wk07_pipeline.py` — same corpus, same embedding functions, same metric implementations
- Both notebooks talk to the same Qdrant cluster
- Day 2 explicitly refers back to Day 1's Cell 9 (nearest-neighbour output) when discussing Cell 15's mini-RAG retrieval — the numbers should match

This mirrors real engineering: build the pipeline once, exercise it many times.

---

## When to stop and when to keep going

### Day 1
Stop when you've run all 15 cells and made a successful Qdrant query in Cell 14. Keep going if the class has time: try different queries in Cell 14, try `3-large` in Cell 5 with more animal pairs, discuss which cross-category matches surprise you in Cell 8.

### Day 2
Stop when you've completed the silent-bug demo (Cell 13) and the mini-RAG runs (Cell 15). Keep going: try adding a query the corpus can't answer (see what the LLM does), tune HNSW to `m=64` and see if it changes anything at this scale, add scalar quantization to the cosine collection and compare timing.

---

## Next up: Track B

After both sessions, work through `AI-RAG_W7_Application_Growth_Guide.md`. That
takes the same pattern and shows you how to migrate your capstone from W6's
`data/embeddings.json` to a Qdrant collection — new files to add, few lines
to modify, expected KPI numbers.

**Total Track B time: ~2 hours self-paced.**

Track B is not a "gradual growth" exercise in isolation — this week's work
is a genuine architectural upgrade to your capstone's storage layer. The old
`naive_rag.py` from W6 stays as a reference; your capstone now defaults to
`qdrant_rag.py`.

---

## Troubleshooting

**Cell 1 fails: `AssertionError: Set OPENAI_API_KEY`**
Your environment doesn't have the key. In Vocareum: `export OPENAI_API_KEY=sk-...`.

**Cell 1 fails: `AssertionError: Set QDRANT_URL`**
Sign up at cloud.qdrant.io, create a free-tier cluster, copy the URL + API
key from the dashboard into your environment. Only takes 5 minutes.

**Day 2 Cell 1 fails: `ModuleNotFoundError: No module named 'wk07_pipeline'`**
The helper module isn't on your Python path. Make sure `wk07_pipeline.py` is
in the same directory as the notebook (i.e., `demos/`), and that you started
Jupyter from that directory (or added it to `sys.path`).

**Cell 11 fails: connection error to Qdrant**
Check your `QDRANT_URL` includes `https://` and port `:6333`. Copy exactly
from the Qdrant Cloud dashboard.

**Cell 5 similarity numbers look weird (all near 0.7)**
Real OpenAI embeddings on English text typically score 0.5-0.9 for related
sentences and 0.1-0.4 for unrelated. If everything's identical, check that
your embeddings differ per input (print `vec[:5]` for different inputs — they
should be different).

**Day 2 Cell 13 — the silent-bug demo doesn't show the pattern**
Try different scaling factors (5x, 10x instead of 3x). The point is that
scaling AT ALL shouldn't affect cosine but SHOULD affect dot product.

---

## What we intentionally did NOT do

For completeness, so you know what's coming:

- **Local embeddings** (BGE, Nomic via sentence-transformers) — mentioned on deck slide 9 but not exercised. Simplifies install (no PyTorch). If you want to try local, pip install sentence-transformers and swap in.
- **Metadata filtering in Qdrant** — Qdrant's real superpower for W8. Held until then.
- **Payload indexes** — W10 concern.
- **Multiple embedding models in the same collection** — anti-pattern; each collection has one fixed embedding model.
- **Deep math of HNSW / IVF** — high-level intuition only, per curriculum instructor notes.

---

*W7 Lab Guide, Track A. Companion to `wk07_day1_embedding_space.ipynb`,
`wk07_day2_qdrant_tour.ipynb`, `wk07_pipeline.py`, and
`AI-RAG_W7_Application_Growth_Guide.md`.*
