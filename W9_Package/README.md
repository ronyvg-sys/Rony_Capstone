# Week 9 — Hybrid Retrieval and Cross-Encoder Reranking

## Overview

The Week 9 package implements a retrieval pipeline that combines dense vector retrieval, BM25 keyword retrieval, Reciprocal Rank Fusion (RRF), and cross-encoder reranking.

The goal is to improve the relevance of retrieved project-management knowledge for downstream RAG question answering.

## Package Structure

```text
W9_Package/
├── data/
│   ├── w9_common_chunks.json
│   ├── w9_embeddings_small.json
│   ├── w9_precision_results.json
│   └── w9_relevance_labels.jsonl
├── docs/
│   ├── kpi/
│   │   └── wk9-snapshot.md
│   ├── wk9-failure-analysis.md
│   └── wk9-precision-delta.md
├── scripts/
│   ├── build_w9_chunks.py
│   ├── build_w9_embeddings.py
│   ├── diagnose_w9_reranking.py
│   ├── measure_wk9_precision.py
│   └── test_w9_hybrid.py
└── src/
    └── rag/
        └── hybrid_rerank.py
```

## Shared Repository Dependencies

This package reuses existing Week 8 and repository-level resources rather than duplicating them:

- `src/rag/naive_rag.py` — shared corpus-loading functionality.
- `data/corpus/` — source project documents.
- `data/golden_set_full.jsonl` — evaluation questions.
- `.env` — repository-level environment configuration, including `OPENAI_API_KEY`.

The Week 9 scripts reference these resources at the repository root. Run the commands below from the repository root.

## Retrieval Pipeline

1. **Dense retrieval:** retrieves chunks using embedding similarity.
2. **BM25 retrieval:** retrieves chunks using keyword matching.
3. **Reciprocal Rank Fusion:** combines the dense and BM25 rankings.
4. **Cross-encoder reranking:** reranks candidate chunks based on query-document relevance.

The embedding model is `text-embedding-3-small` with 1,536 dimensions. The cross-encoder configured in the retrieval implementation is `cross-encoder/ms-marco-MiniLM-L-6-v2`.

## Setup

Activate the existing Python virtual environment and ensure the required dependencies are installed.

Configure `OPENAI_API_KEY` in the repository-root `.env` file. Keep `.env` and API credentials out of version control.

## Run Commands

Run these commands from the repository root.

### Test the retrieval pipeline

```powershell
python W9_Package/scripts/test_w9_hybrid.py
```

This exercises dense retrieval, BM25, RRF, and cross-encoder reranking. It makes an OpenAI embedding API call.

### Measure retrieval precision

```powershell
python W9_Package/scripts/measure_wk9_precision.py
```

This evaluates dense retrieval against the hybrid-plus-reranking pipeline using the golden questions and Week 9 relevance labels. It makes OpenAI API calls and saves results to `W9_Package/data/w9_precision_results.json`.

### Rebuild chunks

```powershell
python W9_Package/scripts/build_w9_chunks.py
```

This reads the shared corpus and writes `W9_Package/data/w9_common_chunks.json`.

### Rebuild embeddings

```powershell
python W9_Package/scripts/build_w9_embeddings.py
```

This generates embeddings from the Week 9 chunks and writes `W9_Package/data/w9_embeddings_small.json`. It makes OpenAI API calls and may incur usage charges.

### Diagnose reranking

```powershell
python W9_Package/scripts/diagnose_w9_reranking.py
```

This examines reranking behavior using the configured retrieval index and evaluation questions.

## Precision Results

Evaluation over 10 questions produced the following average precision values:

| Metric | Dense Retrieval | Hybrid + Reranking |
|---|---:|---:|
| Precision@3 | 0.533 | 0.633 |
| Precision@5 | 0.380 | 0.440 |

The observed improvements were 0.100 for Precision@3 and 0.060 for Precision@5. These results apply to the current evaluation questions, labels, index, and retrieval configuration; they do not guarantee the same improvement on other datasets.

## Week 8 Regression Verification

After the Week 9 package reorganization, the following existing Week 8 checks completed successfully:

- `python test_w8_regression.py` — 6/6 checks passed.
- `python test_w8_completeness.py` — 14/14 checks passed.
- `python test_w8_emails.py` — all 3 obfuscated email examples were redacted.

## Notes

- Week 9 is organized as a separate package, but it is not fully standalone because it reuses repository-level code, data, and configuration.
- The Hugging Face Hub may display an unauthenticated-request warning when downloading the cross-encoder. The warning did not prevent the tested retrieval pipeline from completing.
- Keep evaluation outputs, labels, and generated artifacts aligned with the index and configuration used for the corresponding measurements.
