# Sample additions to wk6-snapshot.md

> *Both activities append a section to the learner's existing
> wk6-snapshot.md. This is what a strong learner's additions look
> like — short, numbers-driven, with a concrete recommendation.*

---

## Activity A — chunk-size sweep

Tested three (size, overlap) profiles against the 20-question
golden set. The W6 baseline is `(500, 50)` (medium).

| Profile | size | overlap | Hit rate | Cost / q | p95 latency |
|---------|------|---------|----------|----------|-------------|
| Small   | 300  | 30      | 13 / 20  | $0.00018 | 1.1s        |
| Medium  | 500  | 50      | 14 / 20  | $0.00021 | 0.9s        |
| Large   | 800  | 80      | 14 / 20  | $0.00023 | 0.8s        |

**Winner: Medium (500/50).** Hit rate ties with Large but at lower
cost. Small dropped 1 point because some answers got split across
chunk boundaries (verified by reading 3 failing rows in the small
run).

The spread across profiles is small (1 point), so chunk-size is
not a high-leverage variable for this corpus. Sticking with
medium as the W7 starting point. Will revisit with section-aware
chunking in W7 — that should give a real lift if my docs have
internal structure (headings, sections) that the current chunker
ignores.

**Time:** ~50 min. Total spend: $0.04.

---

## Activity B — local embeddings (stretch)

Swapped OpenAI `text-embedding-3-small` → sentence-transformers
`all-MiniLM-L6-v2` (384 dim, local, free). Same chunker
(500/50), same corpus, same golden set.

| KPI | OpenAI baseline | Local | Δ |
|---|---|---|---|
| Hit rate | 14 / 20 | 13 / 20 | -1 |
| Cost / q | $0.00021 | $0 (after setup) | -100% |
| Latency p50 | 0.9s | 0.5s | -0.4s |
| Setup time | ~30s once | ~30s (model load) | similar |

### Per-question diff (5 random samples)

| Question | OpenAI top source | Local top source | Same? |
|---|---|---|---|
| g001 — annual leave days | leave_policy.md | leave_policy.md | ✓ |
| g004 — sick leave certificate | leave_policy.md | wfh_policy.md | ✗ |
| g010 — receipt submission | expense_policy.md | expense_policy.md | ✓ |
| g015 — VPN mobile devices | vpn_setup.md | vpn_setup.md | ✓ |
| g020 — VPN when WFH | wfh_policy.md | vpn_setup.md | ✗ |

Two of five differed. The disagreement on g004 cost a hit (local
got the wrong doc). The disagreement on g020 was actually *better*
in the local case but still scored as a miss because the golden
`expected_source` is `wfh_policy.md`.

### Recommendation

If my corpus were 10× bigger, I'd still ship OpenAI for the EKA.
The 1-point hit-rate drop is acceptable but the cost savings
(~$0.0002 × 100k queries = $20/month) don't justify the
operational overhead of running a local model in production.

If I were shipping a privacy-sensitive product (medical, legal,
regulated industries), local becomes the obvious choice and the
quality gap is the price of compliance.

**Time:** ~80 min including pip install + model download. Total
spend: $0 (already covered by Activity A's baseline run).
