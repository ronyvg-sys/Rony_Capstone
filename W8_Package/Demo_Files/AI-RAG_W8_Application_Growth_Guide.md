# AI-RAG · Week 8 · Application Growth Guide

> **Take-home · self-paced · ~3 hours**
>
> Track A (the two notebooks) taught you the ingestion pipeline on 3 sample
> documents. This document walks you through applying it to your capstone's
> real corpus — full `ingest_corpus()`, PII audit, KPI snapshot delta,
> ADR update.

---

## What's changing this week

### Before W8 (end of W7 state)
- `capstone_chunks` — Qdrant collection with basic payload: `chunk_id`, `source_id`, `text`
- W6's naive chunker (sliding window) → fed the vectors
- No metadata beyond source; no PII scrubbing; no filtering possible

### After W8
- `src/ingest/pipeline.py` — full ingestion pipeline (~120 lines)
- `capstone_chunks_v2` — new Qdrant collection **alongside** `capstone_chunks`
- Rich 9-field metadata on every chunk
- PII scrubbed at ingestion (regex + Presidio + manual audit)
- `docs/wk8-pii-audit.md` — audit log
- `docs/kpi/wk8-snapshot.md` — KPI comparison vs W7

### Size of the change
- **1 new module** (`src/ingest/pipeline.py`)
- **2 files modified** (`src/rag/qdrant_store.py`, `src/rag/qdrant_rag.py`)
- **2 new docs** (`wk8-pii-audit.md`, `wk8-snapshot.md`)
- **1 ADR extension**

W7's `capstone_chunks` stays as a rollback point. Once wk8-snapshot.md
shows the delta, you can delete it.

---

## Prerequisites

Before starting:
- [ ] W7 complete: `capstone_chunks` collection exists in Qdrant, `wk7-snapshot.md` committed
- [ ] Both W8 notebooks (Day 1 and Day 2) run successfully
- [ ] Presidio + spaCy `en_core_web_sm` installed (Day 2 requirement)
- [ ] `QDRANT_URL` + `QDRANT_API_KEY` still set
- [ ] Your capstone corpus at `data/corpus/` — 10-20 real documents

Estimated cost: **~$0.10-0.30** in OpenAI embedding credits, depending on
corpus size. You're re-embedding everything with the new chunking.

---

## What you'll add

### 1. `src/ingest/pipeline.py` — the corpus ingester

Adapts the Day 2 mini-pipeline to work across your whole corpus. Dispatches
by file extension.

```python
"""End-to-end ingestion pipeline for the capstone corpus.

Reads files from data/corpus/, parses by extension, chunks with
structure-aware strategy when possible, scrubs PII, enriches with the
9-field metadata schema, embeds, and upserts to Qdrant.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup
from docx import Document
from openai import OpenAI
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from src.rag.qdrant_store import _get_client, ensure_collection, upsert_chunks

# Lazy-init the heavy things (analyzer takes ~5s to build)
_analyzer = None
_anonymizer = None
_openai = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer

def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

def _get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI()
    return _openai


# ─── Step 1: parse ────────────────────────────────────────────────────

def parse_document(path: Path) -> str:
    """Dispatch to the right parser by file extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        doc = pymupdf.open(str(path))
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    elif ext in (".html", ".htm"):
        soup = BeautifulSoup(path.read_text(), "html.parser")
        for tag in soup(["nav", "footer", "script", "style"]):
            tag.decompose()
        main = soup.find("main") or soup.find("body") or soup
        return main.get_text(separator="\n", strip=True)
    elif ext == ".docx":
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif ext == ".md" or ext == ".txt":
        return path.read_text()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ─── Step 2: chunk ────────────────────────────────────────────────────

def chunk_document(text: str, max_size: int = 400) -> list[str]:
    """Recursive chunker — paragraphs first, sentences if too long."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= max_size:
            chunks.append(para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_size:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        chunks.append(current)
                    current = sent
            if current:
                chunks.append(current)
    return chunks


# ─── Step 3: scrub PII ────────────────────────────────────────────────

PII_PATTERNS = {
    "EMAIL":  re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    "PHONE":  re.compile(r'\+?\d{0,2}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3,4}(?:[-.\s]?\d{4})?\b'),
    "EMP_ID": re.compile(r'\bEMP-\d{4,6}\b'),
}

def scrub_pii(text: str) -> tuple[str, list[dict]]:
    """Regex + Presidio hybrid scrubber. Returns (clean_text, flags)."""
    flags = []
    scrubbed = text
    
    # Leg 1: regex
    for label, pattern in PII_PATTERNS.items():
        for match in pattern.findall(scrubbed):
            flags.append({"source": "regex", "type": label, "matched": match})
            scrubbed = scrubbed.replace(match, f"[{label}]")
    
    # Leg 2: Presidio
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()
    results = analyzer.analyze(text=scrubbed, language="en")
    if results:
        anonymized = anonymizer.anonymize(text=scrubbed, analyzer_results=results)
        scrubbed = anonymized.text
        for r in results:
            flags.append({"source": "presidio", "type": r.entity_type,
                         "matched": text[r.start:r.end], "score": r.score})
    
    return scrubbed, flags


# ─── Step 4: enrich metadata ──────────────────────────────────────────

def enrich_metadata(text: str, path: Path, chunk_idx: int, pii_count: int) -> dict:
    """Build the 9-field metadata payload for one chunk."""
    return {
        "chunk_id":        f"{path.stem}#{chunk_idx}",
        "source":          path.name,
        "doc_type":        path.suffix.lstrip(".").lower(),
        "section_path":    path.stem,  # improve with structure-aware chunker later
        "page":            None,        # improve for PDFs via per-page chunking
        "date":            datetime.now(timezone.utc).strftime("%Y-%m-%d"),  # or from file metadata
        "language":        "en",
        "version":         "v1",
        "ingested_at":     datetime.now(timezone.utc).isoformat(),
        "text":            text,
        "pii_flags_count": pii_count,
    }


# ─── Step 5: ingest the whole corpus ──────────────────────────────────

def ingest_corpus(corpus_dir: Path, collection_name: str = "capstone_chunks_v2") -> dict:
    """Walk corpus_dir, ingest every supported file, upsert to Qdrant.
    
    Returns summary stats: n_files, n_chunks, n_pii_flags, per_file_breakdown.
    """
    store = type('Store', (), {})()
    store.client = _get_client()
    store.collection = collection_name
    ensure_collection(store)
    
    openai = _get_openai()
    
    all_chunks = []
    all_flags = []
    per_file = {}
    
    for path in sorted(corpus_dir.iterdir()):
        if path.suffix.lower() not in (".pdf", ".html", ".htm", ".docx", ".md", ".txt"):
            continue
        
        try:
            text = parse_document(path)
        except Exception as e:
            print(f"  ✗ FAILED to parse {path.name}: {e}")
            continue
        
        # Check for silent-failure trap (empty parse output)
        if len(text) < 50:
            print(f"  ⚠  {path.name}: only {len(text)} chars extracted — likely scanned/broken")
            continue
        
        chunk_texts = chunk_document(text, max_size=400)
        
        file_chunks = []
        for idx, chunk_text in enumerate(chunk_texts):
            scrubbed, flags = scrub_pii(chunk_text)
            chunk = enrich_metadata(scrubbed, path, idx, len(flags))
            file_chunks.append(chunk)
            all_flags.extend(flags)
        
        per_file[path.name] = {"chunks": len(file_chunks),
                              "pii_flags": sum(c["pii_flags_count"] for c in file_chunks)}
        all_chunks.extend(file_chunks)
        print(f"  ✓ {path.name}: {len(file_chunks)} chunks, "
              f"{sum(c['pii_flags_count'] for c in file_chunks)} PII flags")
    
    # Embed all chunks (batched for efficiency)
    print(f"\nEmbedding {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    # OpenAI accepts up to 2048 inputs per call; batch if needed
    vectors = []
    BATCH = 100
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i+BATCH]
        resp = openai.embeddings.create(model="text-embedding-3-small", input=batch)
        vectors.extend([item.embedding for item in resp.data])
    
    # Upsert
    print(f"Upserting to Qdrant collection {collection_name!r}...")
    upsert_chunks(store, all_chunks, vectors)
    
    return {
        "n_files": len(per_file),
        "n_chunks": len(all_chunks),
        "n_pii_flags": len(all_flags),
        "per_file": per_file,
    }


if __name__ == "__main__":
    stats = ingest_corpus(Path("data/corpus"))
    print(f"\n══ Summary ══")
    print(f"Files ingested: {stats['n_files']}")
    print(f"Total chunks:   {stats['n_chunks']}")
    print(f"PII flags:      {stats['n_pii_flags']}")
```

**Run it:**
```bash
python -m src.ingest.pipeline
```

Expected output:
```
  ✓ leave_policy.pdf: 8 chunks, 3 PII flags
  ✓ onboarding_guide.docx: 12 chunks, 2 PII flags
  ✓ product_faq.html: 15 chunks, 0 PII flags
  ...

Embedding 156 chunks...
Upserting to Qdrant collection 'capstone_chunks_v2'...

══ Summary ══
Files ingested: 12
Total chunks:   156
PII flags:      18
```

Time: 30-90 seconds depending on corpus size. Cost: ~$0.10.

### 2. Extend `src/rag/qdrant_store.py`

You already have `qdrant_store.py` from W7. It handles `capstone_chunks`.
For W8, you need it to also handle `capstone_chunks_v2` with the enriched
payload.

Add this to `qdrant_store.py`:

```python
def upsert_chunks_v2(store: QdrantStore, chunks: list[dict], vectors: list[list[float]]) -> None:
    """Upsert with the full 9-field metadata payload from W8's pipeline.
    
    chunks[i] is a dict with keys: chunk_id, source, doc_type, section_path,
    page, date, language, version, ingested_at, text, pii_flags_count.
    """
    from qdrant_client.models import PointStruct
    points = [
        PointStruct(id=idx, vector=vec, payload=chunk)
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    store.client.upsert(collection_name=store.collection, points=points)
```

Now the `upsert_chunks` from W7 is unchanged (still works for `capstone_chunks`),
and `upsert_chunks_v2` handles the enriched payload for v2.

Actually — simpler approach: **have `ingest_corpus` in `pipeline.py` call
`upsert_chunks` directly** (which is a generic wrapper around Qdrant upsert).
It doesn't care about payload keys. Just make sure `upsert_chunks` in
`qdrant_store.py` uses `payload=chunk` (the whole dict) rather than picking
specific fields.

Check your W7 `qdrant_store.py`. If it's:
```python
payload = {"chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"], "text": chunk["text"]}
```
Change to:
```python
payload = {k: v for k, v in chunk.items() if k != "vector"}
```

That way, W8's richer payload just goes in without a schema change.

### 3. Point `qdrant_rag.py` at v2

Currently `qdrant_rag.py` (from W7) uses `capstone_chunks`. Point it at v2:

```python
# In src/rag/qdrant_rag.py, change:
from src.rag.qdrant_store import load_store   # uses default "capstone_chunks"
# to:
from src.rag.qdrant_store import _get_client
def load_store():
    """Load a store pointing at the v2 collection."""
    from src.rag.qdrant_store import QdrantStore
    return QdrantStore(client=_get_client(), collection="capstone_chunks_v2")
```

Or cleaner: parameterise the collection name in `qdrant_store.load_store()`
so you can pass either.

### 4. `docs/wk8-pii-audit.md` — audit log

After Track B step 2, you'll fill this in:

```markdown
# W8 PII Audit — capstone_chunks_v2

**Date:** YYYY-MM-DD
**Corpus:** data/corpus/ (N documents)
**Total chunks ingested:** N
**PII flags raised:** N (X% of chunks)

## Sample audit — 10 random chunks

Fetched via:
```python
from src.rag.qdrant_store import _get_client
client = _get_client()
sample = client.scroll(collection_name="capstone_chunks_v2", limit=10, with_payload=True)[0]
```

| Chunk ID | Text preview | PII detected? | Notes |
|---|---|---|---|
| policies#3 | "Contact HR at [EMAIL]..." | ✓ scrubbed | good |
| onboarding#7 | "Priya Sharma leads IT..." | ✗ MISSED | Presidio should have caught this |
| ... | ... | ... | ... |

## Gaps identified

- [ ] Non-Latin names not detected — e.g. `<name in non-Latin script>` in doc X
- [ ] Custom ID format `ACME-\d+` not in regex — add to PII_PATTERNS
- [ ] ...

## Action items

- [ ] Extend regex with `ACME-\d+` pattern before final capstone submission
- [ ] Manual review of remaining N chunks flagged as high-recall risk
```

### 5. `docs/kpi/wk8-snapshot.md` — KPI comparison

Fill this in after Track B step 3:

```markdown
# wk8-snapshot.md — Post-ingestion baseline

**Date:** YYYY-MM-DD
**Vector store:** Qdrant Cloud
**Collection:** capstone_chunks_v2 (N points, 1536 dim, cosine)
**Chunking strategy:** recursive (or structure-aware where possible)
**PII scrubbing:** regex + Presidio hybrid

## Headline numbers

| Metric | W7 (capstone_chunks) | W8 (capstone_chunks_v2) | Delta |
|---|---|---|---|
| Cost per query | $0.000XXX | $0.000XXX | ~0 (same models) |
| Latency p50 (ms) | XXX | XXX | ~0 (Qdrant handles both) |
| Retrieval hit rate | XX% | XX% | +Y pp (better chunks) |
| Grounded response rate | XX% | XX% | +Y pp (less garbage in chunks) |
| PII items scrubbed | 0 | N | ← new capability |

## Operational deltas

| Property | W7 | W8 |
|---|---|---|
| Metadata fields per chunk | 3 | 9 |
| Filtered retrieval possible | no | yes |
| PII risk | leak-prone | scrubbed at ingest |

## Method
- Same 20 golden-set questions from W5
- W7 baseline from wk7-snapshot.md
- W8 numbers from a fresh run against capstone_chunks_v2

## Interpretation
[why did hit rate move? Was it chunking or metadata? Anything surprising?]
```

---

## What you'll modify

### `src/api/main.py` — no change needed
If `qdrant_rag.py` loads from `capstone_chunks_v2` by default, the API layer
doesn't need changes.

### `docs/adr/0001-capstone-framing.md` — add a W8 section

Append at the end:

```markdown
## W8 — Structure-aware ingestion + PII discipline

**Decision:** Capstone corpus is now ingested via `src/ingest/pipeline.py`,
which parses by extension, chunks recursively (structure-aware where possible),
scrubs PII with regex + Presidio, enriches with the 9-field metadata schema,
and upserts to `capstone_chunks_v2`.

**Ingestion pipeline steps:**
1. Parse (PyMuPDF for PDF, BeautifulSoup for HTML, python-docx for DOCX)
2. Chunk (recursive, max_size=400)
3. Scrub PII (regex + Presidio + audit)
4. Enrich metadata (9 fields)
5. Embed (text-embedding-3-small)
6. Upsert (Qdrant collection capstone_chunks_v2)

**PII detection:** hybrid regex + Presidio. Regex catches EMAIL, PHONE, EMP_ID.
Presidio catches PERSON, LOCATION, ORGANIZATION. Manual audit on 10 random
chunks per ingestion run — see docs/wk8-pii-audit.md.

**Known gaps:** [what your audit found — non-Latin names, custom formats, etc.]

**Data residency:**
- Embeddings computed by: OpenAI API (US)
- Vectors stored at: Qdrant Cloud [region]
- LLM inference at: OpenAI API (US)
- App layer: [where you deploy]
- Cross-jurisdictional flows: US ↔ [Qdrant region] ↔ [app region]

**Rejected alternatives:**
- Structure-aware chunking on all doc types — DOCX supports it well;
  PDFs would need custom logic per document; not worth it for MVP.
- Semantic chunking as default — cost-prohibitive at corpus scale.
- Presidio only (no regex) — slower; misses obvious patterns Presidio
  weights lower.

**Operational KPIs** (see docs/kpi/wk8-snapshot.md):
[fill in]
```

---

## Testing checklist

Before W8 is done:

- [ ] `src/ingest/pipeline.py` exists and runs end-to-end without crashes
- [ ] `capstone_chunks_v2` collection exists in Qdrant with N points > 0
- [ ] `docs/wk8-pii-audit.md` filled in for 10 random chunks (real audit, not placeholder)
- [ ] `docs/kpi/wk8-snapshot.md` shows retrieval hit rate delta vs W7
- [ ] ADR extended with W8 section
- [ ] `qdrant_rag.py` retrieval works against v2 collection
- [ ] No real PII in any committed file (walk repos on Friday)

---

## Common issues + fixes

**`ImportError: cannot import name 'AnalyzerEngine'`**
Install Presidio: `pip install presidio-analyzer presidio-anonymizer`. Also
need spaCy model: `python -m spacy download en_core_web_sm`.

**Parse failure on some PDFs — returns <50 chars**
Those PDFs are likely scanned (image-only, no text layer). Options:
1. Skip them for now (`pipeline.py` already logs a warning and skips)
2. Add OCR (W10 covers this if you need it)
3. Manually swap for text-based versions

**Presidio very slow on first chunk**
Model load takes ~5 seconds. Subsequent chunks are fast. Batch your ingestion
runs to amortize.

**KPI hit rate DROPPED from W7 to W8**
Something's wrong with your chunking. Common causes:
- `max_size` too small — chunks lose context
- `max_size` too big — chunks are less semantically focused
- Structure-aware chunker broke on your specific doc format (edge case)

Debug: pull 5 chunks that used to return correct answers in W7 and see if
they're still findable in v2.

**Presidio detects too many false positives (redacts non-PII)**
Presidio's default confidence threshold is low. Filter results by score:
```python
results = [r for r in analyzer.analyze(text=..., language="en") if r.score >= 0.6]
```

---

## What you should have when done

New files:
- `src/ingest/pipeline.py`
- `docs/wk8-pii-audit.md`
- `docs/kpi/wk8-snapshot.md`

Modified files:
- `src/rag/qdrant_store.py` (payload handling generalized)
- `src/rag/qdrant_rag.py` (points at v2 collection)
- `docs/adr/0001-capstone-framing.md` (W8 section added)

Qdrant state:
- `capstone_chunks_v2` — new collection with enriched payload
- `capstone_chunks` — from W7, retained as rollback point (delete after wk9 stable)

Total time: ~3 hours self-paced. Longer if your corpus has scanned PDFs or
non-English content that trips Presidio.

---

## What's coming in W9

**W9 is the first DANGER ZONE** per the difficulty heatmap. Three heavy topics
back-to-back:
- Hybrid search (vector + keyword)
- Reranking (BGE reranker or Cohere)
- Query rewriting (LLM rewrites vague queries before retrieval)

The **metadata you built this week** is what W9 uses to filter retrieval —
"only search 2025 policies," "prefer canonical version." Without W8's
metadata payload, W9's precision lift isn't possible.

Plan extra lab time. Bring specific failure cases from your capstone (queries
that return wrong docs) — W9's whole point is fixing those.

---

*W8 Application Growth Guide. Track B of the two-track W8 pattern. Companion
to `wk08_day1_parsing_chunking.ipynb`, `wk08_day2_metadata_pii_pipeline.ipynb`,
`wk08_pipeline.py`, and `AI-RAG_W8_Lab_Guide.md`.*
