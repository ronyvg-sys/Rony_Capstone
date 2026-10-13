# AI-RAG · Week 8 · Lab Guide
## Document Ingestion + PII Awareness — Concept Demo

> **Two in-session notebooks · standalone Jupyter · Track A**
>
> **Day 1 (75 min):** Parsing real document formats + 4 chunking strategies compared.
> **Day 2 (90 min):** Metadata schema, PII scrubbing (regex + Presidio + audit), mini-pipeline wired end-to-end.
>
> Both notebooks use 3 bundled sample documents — a policies PDF, product HTML, onboarding DOCX. All fake PII embedded is invented for the demos.
>
> **After the two sessions:** work through `AI-RAG_W8_Application_Growth_Guide.md`
> to re-ingest your capstone corpus with the new pipeline (self-paced take-home).

---

## Package contents

Inside `demos/`:

| File | Session | Purpose |
|---|---|---|
| `wk08_day1_parsing_chunking.ipynb` | Day 1 (75 min) | Parsing + chunking strategies |
| `wk08_day2_metadata_pii_pipeline.ipynb` | Day 2 (90 min) | Metadata, PII, mini-pipeline |
| `wk08_pipeline.py` | Helper | Shared parse/chunk/scrub functions Day 2 imports |
| `generate_sample_docs.py` | Setup | Regenerates the 3 sample documents |
| `sample_docs/company_policies.pdf` | Sample | 3-page PDF with headings + table + fake PII |
| `sample_docs/product_page.html` | Sample | HTML with nav/main/footer (no PII) |
| `sample_docs/onboarding.docx` | Sample | DOCX with heading styles + fake PII |

**Want more sample variety?** Two options:
1. Modify `generate_sample_docs.py` — add more sections, headings, PII patterns
2. Substitute public-domain samples (any short PDF/HTML/DOCX) at `sample_docs/` with the expected filenames

---

## Prerequisites (both days)

### Day 1
- [ ] Vocareum notebook environment
- [ ] `pip install pymupdf pdfplumber beautifulsoup4 python-docx reportlab openai numpy`
- [ ] `OPENAI_API_KEY` set (for Day 1 Cell 10 semantic chunking demo — costs ~$0.0001)
- [ ] Sample docs generated: `python demos/generate_sample_docs.py`

### Day 2 (additional)
- [ ] `pip install presidio-analyzer presidio-anonymizer` **(homework between days — ~150 MB)**
- [ ] `python -m spacy download en_core_web_sm`
- [ ] `pip install qdrant-client` (already installed if W7 was done)
- [ ] `QDRANT_URL` + `QDRANT_API_KEY` set (Qdrant Cloud, from W7)

**Cost across both notebooks: ~$0.002** in OpenAI credits. Presidio + Qdrant are free.

---

## Day 1 · `wk08_day1_parsing_chunking.ipynb` (75 min)

Aligned to deck slides 8-19 — Topic 1 (Parsing) + Topic 2 (Chunking).

### What we do

Learn to parse real document formats (PDF, HTML, DOCX), see the failure modes each has, and compare four chunking strategies (fixed, recursive, semantic, structure-aware) on real content.

### Section-by-section walkthrough (75 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup + confirm sample docs exist | 3 min |
| **2** | **PyMuPDF on the PDF** — extract text page-by-page, see the jumbled table | **8 min** |
| **3** | **pdfplumber on the same PDF** — same file, better table extraction | **7 min** |
| **4** | **BeautifulSoup on the HTML** — naive vs clean extraction (strip nav/footer) | **7 min** |
| **5** | **python-docx on the DOCX** — extract paragraphs + heading styles | **7 min** |
| **6** | **The scanned PDF trap** — image-only PDF → empty text → silent failure | **5 min** |
| 7 | Topic 1 recap — 4-library decision matrix | 3 min |
| **8** | **Fixed-size chunking** — W6's baseline, count mid-sentence cuts | **5 min** |
| **9** | **Recursive chunking** — paragraph → sentence fallback, cleaner boundaries | **10 min** |
| **10** | **Semantic chunking (simplified)** — 6 sentences, embed, group by cosine threshold | **10 min** |
| **11** | **Structure-aware chunking** — use DOCX heading styles, section_path falls out naturally | **8 min** |
| 12 | Wrap + Presidio install homework for Day 2 | 2 min |

**Bold cells are the hands-on peaks.**

### Discussion moments built into the notebook

- **Cell 2 vs 3:** how does the leave-approval table look under PyMuPDF vs pdfplumber? (Jumbled vs structured.)
- **Cell 4:** count the extra chars the naive HTML extraction included. That's noise your retrieval will match against.
- **Cell 6 (scanned PDF trap):** the parser succeeds silently. Discuss where in your pipeline you'd add a size check to catch this.
- **Cell 8 vs 9:** count mid-sentence cuts in fixed vs recursive. Recursive nearly always wins on clean-ending chunks.
- **Cell 11:** notice `section_path` = `'Week 1 > IT Support Contacts'` comes for free from heading styles. That's the biggest single quality lift.

### What learners take away from Day 1

1. Practical familiarity with 4 parse libraries + when to reach for each
2. Awareness of the scanned-PDF silent-failure trap
3. Concrete comparison of 4 chunking strategies on real content
4. Confidence that structure-aware chunking is the best default when documents have headings

### What Day 1 does NOT do

- PII detection (Topic 4 — Day 2)
- Metadata schema (Topic 3 — Day 2)
- Wiring parts into a pipeline (Topic 5 — Day 2)
- Anything capstone-related (Track B)
- Qdrant interaction (Day 2 introduces filter DSL)

---

## Day 2 · `wk08_day2_metadata_pii_pipeline.ipynb` (90 min)

Aligned to deck slides 21-38 — Topic 3 (Metadata) + Topic 4 (PII) + Topic 5 (Pipeline).

### What we do

Build the 9-field metadata schema, run filtered Qdrant queries, compare regex vs Presidio PII detection, wire regex + Presidio + audit into a hybrid scrubber, articulate data residency, and wrap by wiring parse → chunk → scrub → enrich into a mini-pipeline on ONE sample document.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup + **HARD assertion Presidio is installed** (yesterday's homework) | 5 min |
| **2** | **The 9-field metadata schema** — show a real chunk with all 9 fields populated | **8 min** |
| **3** | **Qdrant filter DSL** — 6-chunk demo collection; filtered queries by doc_type + year | **10 min** |
| **4** | **PII discoverability demo** — embed a chunk with PII, retrieve it, see the leak | **7 min** |
| **5** | **Regex baseline** — 3 patterns catch 4/6 items in a test paragraph | **8 min** |
| **6** | **Presidio NER** — same paragraph, all 6 items + person names, with scores | **10 min** |
| **7** | **Presidio anonymization** — analyze then anonymize; `<PERSON>`, `<EMAIL_ADDRESS>` tokens | **5 min** |
| **8** | **Three legs: regex + Presidio + audit** — hybrid `scrub_pii()` function | **8 min** |
| **9** | **Data residency** — `describe_stack()` prints where your data lives | **5 min** |
| **10** | **Mini-pipeline synthesis** — parse → chunk → scrub → enrich on SAMPLE_PDF, print ingestion-ready chunks | **15 min** |
| 11 | Wrap + hand-off to Track B | 4 min |

**Bold cells are the hands-on peaks.**

### Discussion moments built into the notebook

- **Cell 1:** if Presidio isn't installed, the notebook stops here. That's intentional — quietly skipping content is worse than a loud stop.
- **Cell 3:** without the year filter, does the 2022 legacy policy appear? With it, does it get excluded? This is the W9 filtering preview.
- **Cell 4:** the PII leak demo. Instructor emphasis: "once it's in the vector store, it's discoverable. Redact BEFORE ingest, not after."
- **Cell 5 vs 6:** count what regex missed (names). This is why Presidio matters. But Presidio has its own limits — non-Latin scripts, novel formats.
- **Cell 8 (three legs):** why audit? Because neither tool is complete. Real production PII discipline is regex + NER + human eyes on samples.
- **Cell 9:** every learner articulates their residency stack in one sentence. Puts it in the ADR.
- **Cell 10:** the ingested chunk has all 9 metadata fields + scrubbed text. This is the shape Track B will scale to the full capstone corpus.

### What learners take away from Day 2

- Working 9-field metadata schema attached to every chunk
- Fluency with Qdrant's filter DSL (`FieldCondition`, `Range`, `MatchValue`)
- Three-legs PII pattern: regex + Presidio + audit
- One-sentence articulation of data residency for their stack
- A mini-pipeline that turns a raw document into ingestion-ready chunks

### What Day 2 does NOT do

- Learner's actual capstone corpus (Track B)
- Full `ingest_corpus(dir)` wrapper — Track B builds this
- Re-running golden set + KPI snapshot — Track B step 3
- Manual PII audit on 10 real chunks — Track B step 2
- ADR update — Track B step 4

---

## How the two days connect

- **Day 1** builds parsers and chunkers inline in the notebook
- **Day 2** imports those functions from `wk08_pipeline.py` (same code — learners can open it and confirm)
- The **sample documents are shared** across both days
- **Day 2 Cell 10** synthesizes everything: parse (Day 1) → chunk (Day 1) → scrub (Day 2) → enrich (Day 2) → ingestion-ready chunk

This is the classic build-once, exercise-many pattern — same as W6 and W7.

---

## When to stop and when to keep going

### Day 1
Stop when you've completed structure-aware chunking on the DOCX (Cell 11). Keep going: try recursive chunking on the HTML file, or attempt Cell 10's semantic threshold with different values (0.3, 0.7, 0.9).

### Day 2
Stop when you've built the mini-pipeline (Cell 10) and printed the ingestion-ready chunks. Keep going: modify `ingest_one_pdf()` to actually upsert to Qdrant with a temporary collection, then run a filtered query.

---

## Next up: Track B

After both sessions, work through `AI-RAG_W8_Application_Growth_Guide.md`. That takes the mini-pipeline and shows you how to scale it to your capstone corpus — full `ingest_corpus(dir)`, PII audit doc, KPI snapshot delta, ADR update.

**Total Track B time: ~3 hours self-paced.**

Track B is a genuine architectural upgrade to your capstone. The naive chunker from W6 is retired (kept as reference); your capstone now defaults to the structure-aware, metadata-rich, PII-scrubbed pipeline built this week.

---

## Troubleshooting

**Cell 1 (Day 1) fails: `FileNotFoundError: Missing sample docs`**
Run `python demos/generate_sample_docs.py` from your notebook working directory.

**Cell 1 (Day 2) fails: `ImportError: PRESIDIO NOT INSTALLED`**
You skipped yesterday's homework. Run:
```
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_sm
```
Then **restart the kernel** and re-run the cell.

**Cell 6 (Day 2) — Presidio detects wrong things or misses obvious names**
Presidio's NER model is `en_core_web_sm` (small). It's fast but imperfect. For better recall, install `en_core_web_lg` (larger, slower). For high-stakes production, use `en_core_web_trf` (transformer-based, much slower but higher recall). The three-legs pattern (Cell 8) compensates for any single tool's gaps.

**Cell 10 semantic chunking (Day 1) — all sentences end up in ONE chunk**
Your threshold is too low. Try 0.7 or 0.75 for OpenAI embeddings.

**Cell 3 (Day 2) filtered query — filter doesn't seem to work**
Qdrant's `Range` filter requires **numeric** fields. That's why the demo stores both `date` (string, for display) and `year` (int, for filtering). If you want date-range filtering, either use `MatchValue` for exact matches, or store dates as Unix timestamps.

**Anything in Day 2 fails on Vocareum but works locally**
Presidio + spaCy sometimes has environment-specific quirks. Try `pip install --upgrade presidio-analyzer` and confirm `python -c "import spacy; spacy.load('en_core_web_sm')"` works. If not, re-download the model.

---

## What we intentionally did NOT do

- **OCR** for scanned PDFs — Cell 6 shows the trap but doesn't fix it. W10 introduces OCR if needed.
- **Full semantic chunking at scale** — Day 1 Cell 10 uses 6 sentences. On real corpora it'd be 2000+ sentences per doc.
- **Non-English NER** — Presidio with `en_core_web_sm` only. Multi-language corpora need `xx_ent_wiki_sm` or per-language models.
- **Advanced Qdrant filter grammar** — Cell 3 covers `must` + `Range`. Qdrant also has `should` (OR), `must_not` (NOT), and nested filters. See Qdrant docs.
- **Vector-level ACL** — filter DSL enforces payload-based access. True row-level security is a W28 topic.

---

*W8 Lab Guide, Track A. Companion to `wk08_day1_parsing_chunking.ipynb`,
`wk08_day2_metadata_pii_pipeline.ipynb`, `wk08_pipeline.py`, and
`AI-RAG_W8_Application_Growth_Guide.md`.*
