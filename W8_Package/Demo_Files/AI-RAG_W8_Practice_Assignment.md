# AI-RAG · Week 8 · Activity
## PII stress test — break your scrubber on purpose

> Take-home. ~60 minutes. **Recommended.** This activity
> reinforces the central lesson of W8 — *"Presidio is not enough.
> Neither is regex. Both together aren't enough either — audit
> is the third leg."*
>
> Unlike a normal lab step where you make something work, here
> you deliberately try to break what you built. The point is to
> develop intuition for the failure modes you'll hit on real
> corpora.

---

## Why this matters

In Lab Step 2 you audited 10 random chunks for PII leakage. That
audit was honest — but the sample was small and the documents
were the reference corpus, which was designed to be parseable.

Real corpora are adversarial in a quiet way. They contain:

- Names that don't look like names to a Western-trained NER model
- IDs that don't fit any standard pattern
- Email addresses written in formats people use to *avoid* email
  scrapers
- Phone numbers spelled out, formatted unusually, or split across
  lines
- Addresses in regional layouts the NER model has never seen

This activity gives you 30 minutes with a deliberately-crafted
stress test corpus, and asks you to **document where your
scrubber breaks**. That documentation is genuinely useful — it
goes into your ADR and informs the W14 / W18 / W25 / W28 deep
dives.

---

## Prerequisites

- Lab Steps 1-4 completed (capstone_chunks_v2 populated, ADR
  updated)
- `src/ingest/pii.py` (the hybrid regex + Presidio scrubber from
  the live coding)
- ~60 minutes of focused time
- Optional: a notebook for screenshots / failure log

---

## Step 1 · Build the stress test corpus (10 min)

Create a file `data/stress_test/pii_adversarial.md` with the
following content (copy-paste exactly — the formatting matters):

```markdown
# Internal Memo — Project Khanjar

## Project team

Please direct queries to **Dr. Yuki Tanaka** (Tokyo office),
**Fatima Al-Rashid** (Dubai office), or **Rajesh Patel** (Mumbai
office). Aisha Mohammed will cover the European leg.

For US contacts: Carlos Mendoza is the regional lead — you can
reach him via the Atlanta office.

## Reaching out

You can email the team lead at alice [at] example [dot] com
(spaces matter — the form scrapes a lot of bots otherwise).

Alternative inbox is bob.smith ＠ example ．com (the at-sign and
dot are full-width Japanese characters, copy carefully).

Or use the secure form: y.tanaka(at)hospital(dot)org

## Phone numbers

- Yuki's office: +81 (0) 3 1234 5678
- Fatima's mobile: zero zero nine seven one five zero two three four five six seven
- Rajesh's desk: 91-22-2570-1234 ext. 4501
- Aisha's WhatsApp: +44 7700 900 123
- Carlos's direct: 4 0 4 . 5 5 5 . 0 1 8 2

## Employee identifiers

- Yuki Tanaka — EMP-04827
- Fatima Al-Rashid — Staff #4082
- Rajesh Patel — RJP/2019/0451
- Aisha Mohammed — A.M.-2021-EUR-007
- Carlos Mendoza — Badge: CM18234

## Addresses

- Tokyo office: 1-2-3 Shibuya-ku, Tokyo 150-0002, Japan
- Dubai office: Office 412, Sheikh Zayed Road, Dubai, UAE
- Mumbai office: Flat 4B, 23rd Cross Road, Bandra West, Mumbai 400050
- London office: 221B Baker Street, London NW1 6XE

## Financial

- Project budget code: PRJ-2024-KHANJAR-EU
- Lead's IBAN for expenses: GB82 WEST 1234 5698 7654 32
- Petty cash card last four: ****-****-****-4521

## Signed

The above information is internal. Please do not forward.

— Compliance Team, Last Updated 2024-03-15
```

This document is deliberately packed with 30+ PII items in
formats that will challenge any scrubber.

---

## Step 2 · Run your scrubber on it (5 min)

Run your hybrid scrubber on this document:

```python
from src.ingest.parsers import parse_document
from src.ingest.chunkers import chunk_structurally
from src.ingest.pii import scrub_chunks

# Parse
doc = parse_document("data/stress_test/pii_adversarial.md")

# Chunk
chunks = chunk_structurally(doc, max_chars=800)

# Scrub
scrubbed, scrub_report = scrub_chunks(chunks, use_presidio=True)

# Inspect
for i, (chunk, report) in enumerate(zip(scrubbed, scrub_report)):
    print(f"\n--- Chunk {i} ---")
    print(f"Detected PII types: {report['detected_types']}")
    print(f"Redactions: {report['n_redactions']}")
    print(chunk.text[:400])
    print("...")
```

Capture the output. You'll come back to it.

---

## Step 3 · Build the failure log (25 min)

Open a new file `docs/adr/pii_stress_test_findings.md` and fill in
this template. **Be specific.** Don't say "names were missed" —
say *which* names and *why*.

```markdown
# PII Stress Test — W8 Activity Findings

**Date:** [today]
**Run by:** [your name]
**Corpus:** data/stress_test/pii_adversarial.md
**Scrubber config:** regex + Presidio (default thresholds)

## Summary

- Total PII items in source: ~30 (estimate)
- Caught by scrubber: __ / 30
- Missed entirely: __ / 30
- Partially redacted (e.g., name caught, ID missed): __ / 30

## Failure categories

### 1. Names

| Name | Caught? | Notes |
|---|---|---|
| Dr. Yuki Tanaka | | |
| Fatima Al-Rashid | | |
| Rajesh Patel | | |
| Aisha Mohammed | | |
| Carlos Mendoza | | |
| Alice (single name) | | |
| Bob Smith | | |

### 2. Emails (obfuscated)

| Format | Caught? | Notes |
|---|---|---|
| `alice [at] example [dot] com` | | |
| `bob.smith ＠ example ．com` (full-width) | | |
| `y.tanaka(at)hospital(dot)org` | | |

### 3. Phone numbers (non-standard)

| Number | Caught? | Notes |
|---|---|---|
| `+81 (0) 3 1234 5678` | | |
| `zero zero nine seven one...` (spelled out) | | |
| `91-22-2570-1234 ext. 4501` | | |
| `+44 7700 900 123` | | |
| `4 0 4 . 5 5 5 . 0 1 8 2` (digit-spaced) | | |

### 4. Employee IDs

| ID | Caught? | Notes |
|---|---|---|
| `EMP-04827` | | |
| `Staff #4082` | | |
| `RJP/2019/0451` | | |
| `A.M.-2021-EUR-007` | | |
| `Badge: CM18234` | | |

### 5. Addresses

| Address | Caught? | Notes |
|---|---|---|
| `1-2-3 Shibuya-ku, Tokyo` | | |
| `Office 412, Sheikh Zayed Road, Dubai` | | |
| `Flat 4B, 23rd Cross Road, Mumbai` | | |
| `221B Baker Street, London NW1 6XE` | | |

### 6. Financial

| Item | Caught? | Notes |
|---|---|---|
| IBAN: `GB82 WEST 1234 5698 7654 32` | | |
| Card last 4: `****-****-****-4521` | | |
| Project code: `PRJ-2024-KHANJAR-EU` (not PII — false positive risk) | | |
```

Take 25 minutes to fill this in honestly. **Mark "caught" or
"missed" for every row.** If a name was caught but flagged with
low confidence, note that.

---

## Step 4 · Propose your fixes (15 min)

Now the constructive part. Based on what you found, propose
concrete changes to your scrubber.

### Fix template

For each category where you found failures, write:

```markdown
## Fix for [category]

**Problem:** [one sentence — what's slipping through]

**Proposed fix:** [one sentence — what you'd change]

**Trade-off:** [one sentence — what this fix costs you]

**Example code:**
```python
# Custom regex addition for employee IDs:
EMPLOYEE_ID_PATTERNS = [
    r"\bEMP-\d{4,6}\b",
    r"\bStaff\s*#\s*\d{3,6}\b",
    r"\b[A-Z]{2,3}/\d{4}/\d{3,5}\b",
    # ...
]
```
```

You're not required to implement the fixes — just propose them.
The point is to develop the **diagnostic muscle** that turns
"the scrubber missed something" into "here's a specific patch."

---

## Step 5 · Optional — measure before and after (5 min)

If you want to go further, implement one of your proposed fixes
and re-run the scrubber on the stress test corpus. Update the
"Caught? / Notes" column with the new results.

You should see meaningful movement: 5-10 more catches if your fix
was targeted. If you see *no* movement, your fix didn't do what
you thought — debug it.

---

## Deliverable

Submit:

1. `docs/adr/pii_stress_test_findings.md` — your filled-in findings
2. (Optional) Updated `src/ingest/pii.py` with one implemented fix
3. A brief note in your `wk8-snapshot.md` under "Activity":
   *"Stress test surfaced N additional PII patterns the default
   scrubber missed (employee IDs, obfuscated emails, non-Western
   names). Findings logged in docs/adr/pii_stress_test_findings.md."*

---

## What good output looks like

A complete failure log will have:

- **All 30+ items checked** — not just the easy ones
- **Honest assessment** — most learners will catch fewer than half
  of these items on the first pass; that's expected and useful
- **Specific failure patterns named** — not "Presidio is bad at
  names" but "Presidio missed 'Fatima Al-Rashid' (likely because
  hyphenated/cross-cultural names confuse the default model)"
- **At least 3 concrete fix proposals** — one per category where
  you found multiple failures
- **One fix actually implemented** — even if it only catches 2-3
  more items

---

## Why this is worth the 60 minutes

The W8 lesson plan says: *"Presidio is imperfect — say so. Its
NER misses non-Latin names, custom ID formats, addresses in
unusual layouts. Tell learners explicitly: 'Presidio + regex +
manual audit is the policy. None of the three is sufficient
alone.'"*

That's the abstract claim. This activity makes you feel it
concretely. The next time you ingest a real corpus, you'll have
calibrated intuition for what to look for — not just "did my
scrubber run" but "what kinds of things does it miss?"

That intuition is what separates engineers who treat PII as a
checkbox from engineers who treat it as a discipline. The
program returns to this thread in W14, W18, W25, and W28. The
work you do this week is the foundation for all of it.

---

## A note on what's not in this activity

We deliberately don't include:

- **Real names of real people.** All names are fictional or
  composite. Don't substitute real names from your corpus.
- **Real bank details.** The IBAN is the official UK test IBAN.
- **Real addresses.** All addresses are real-world cities but
  fictional buildings.
- **Phone numbers from your real corpus.** Use only the ones
  provided here for the test.

If you do find PII in your real corpus during the lab audit,
treat it as a production incident — fix the scrubber, re-ingest,
and **do not include real PII in your stress test corpus** even
to "test the fix." The fix should be testable on the adversarial
data, not on real data.

---

*End of activity. Submit your findings before the W9 session.*
