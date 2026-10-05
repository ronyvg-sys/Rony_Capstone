# W6 RAG Evaluation Snapshot

## Activity A — chunk-size sweep

Tested three chunk configurations on the Project ABC banking corpus:

| Profile | Chunk size | Overlap | Chunks | Retrieval hit rate | Cost/query | P95 latency |
|---|---:|---:|---:|---:|---:|---:|
| Small | 300 | 30 | 56 | 100.00% | $0.000065 | 2008.47 ms |
| Medium | 500 | 50 | 35 | 100.00% | $0.000092 | 3456.16 ms |
| Large | 800 | 80 | 27 | 100.00% | $0.000112 | 2727.63 ms |

### Winner

**300/30**

All three configurations achieved a 100% retrieval hit rate on the 10-question W6 golden set. The 300/30 configuration had the lowest cost per query ($0.000065) and the lowest P95 latency (2008.47 ms), making it the best overall configuration for this evaluation.

**Decision:** Keep 300/30 as the W7 starting configuration.
