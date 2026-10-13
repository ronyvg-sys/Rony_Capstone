# AI-RAG · Week 8 · Activity Solution
## PII stress test — instructor reference

> Reference answers for the W8 stress test activity. Use this in
> office hours or as the "model output" learners can self-compare
> against after submission.
>
> The point of the activity isn't to get a perfect score — it's to
> develop diagnostic intuition. A learner catching 18 / 30 with
> good failure analysis is in better shape than one catching 24
> with no fixes proposed.

---

## Expected catch rates by category

The numbers below are typical for the default hybrid scrubber
(regex baseline + Presidio with `score_threshold=0.5`). Real cohort
results vary ±15% based on Presidio version and spaCy model.

| Category | Items in corpus | Typical catch rate | Notes |
|---|---|---|---|
| Names | 7 | 4-6 / 7 (~70%) | Western names catch reliably; non-Western names miss ~30% |
| Obfuscated emails | 3 | 0-1 / 3 (~20%) | Default regex requires `@` literal; obfuscation defeats it |
| Phone numbers (non-standard) | 5 | 2-3 / 5 (~50%) | International with `+` catches; spelled-out and digit-spaced miss |
| Employee IDs | 5 | 0 / 5 (0%) | Out-of-the-box scrubber has no pattern for these |
| Addresses | 4 | 1-2 / 4 (~30%) | Presidio's LOCATION catches city names; full addresses miss |
| Financial | 3 | 1-2 / 3 (~50%) | IBAN matches; masked cards miss; project codes shouldn't fire (false positive risk) |
| **Total** | **~27** | **~10-14 / 27 (~45%)** | First-pass scrubber catches roughly half |

A learner reporting **>20 / 27 caught** on the first pass without
custom tuning is either (a) using a heavily customised regex set
already, (b) misreporting (didn't actually check), or (c) using a
newer Presidio version than the curriculum baseline. Worth a quick
1:1 to verify.

A learner reporting **<8 / 27 caught** likely has a broken
Presidio install — they're only getting the regex pass. Diagnose
with:

```python
from src.ingest.pii import _PRESIDIO_AVAILABLE
print(_PRESIDIO_AVAILABLE)  # should be True
```

---

## Per-item reference — what the default scrubber should catch

### Names

| Name | Default catches? | Why / why not |
|---|---|---|
| Dr. Yuki Tanaka | Maybe (50%) | "Dr." title sometimes prevents NER from recognising the name as PERSON |
| Fatima Al-Rashid | Often missed | Hyphenated cross-cultural names confuse Presidio's default model |
| Rajesh Patel | Usually caught | South Asian names are in the training data; "Patel" is a strong NER signal |
| Aisha Mohammed | Usually caught | Both tokens look like names; Presidio fires |
| Carlos Mendoza | Reliably caught | Latin American names are well-represented |
| Alice (single name) | Often missed | Single-token names without surname have lower NER scores |
| Bob Smith | Reliably caught | Textbook English name; Presidio fires confidently |

**Sample learner observation (good):** *"Presidio missed 'Fatima
Al-Rashid' — likely because hyphenated names of MENA origin aren't
well-represented in the default `en_core_web_lg` model. Confirmed
by lowering threshold to 0.3, which then catches it but also
triggers 4 false positives elsewhere."*

That observation shows the learner did the diagnostic work. Reward
generously.

### Obfuscated emails

| Format | Default catches? | Why / why not |
|---|---|---|
| `alice [at] example [dot] com` | No | EMAIL regex requires literal `@` |
| `bob.smith ＠ example ．com` (full-width) | No | Full-width `＠` doesn't match `[@]` in standard regex |
| `y.tanaka(at)hospital(dot)org` | No | Same reason — no literal `@` |

All three should miss with the default scrubber. This is the
strongest "regex is not enough" signal in the activity.

**Sample fix to propose:**

```python
# In src/ingest/pii.py, extend the email patterns:
OBFUSCATED_EMAIL_PATTERNS = [
    # [at] / (at) / ＠ variants
    re.compile(r"\b[\w.-]+\s*[\[\(]\s*at\s*[\]\)]\s*[\w.-]+\s*[\[\(]\s*dot\s*[\]\)]\s*[a-z]{2,}\b", re.I),
    # Full-width @ and .
    re.compile(r"\b[\w.-]+\s*[＠@]\s*[\w.-]+\s*[．.]\s*[a-z]{2,}\b", re.I),
]
```

This catches ~70% of common obfuscations. Pure unicode-lookalike
attacks (e.g., Cyrillic 'a') still slip — name that as a known
limitation rather than chasing every variant.

### Phone numbers

| Number | Default catches? | Why / why not |
|---|---|---|
| `+81 (0) 3 1234 5678` | Yes | International prefix; matches standard pattern |
| `zero zero nine seven one five zero...` | No | Spelled-out digits aren't in regex; no NER label for "PHONE" |
| `91-22-2570-1234 ext. 4501` | Partial | Catches the main number; `ext. 4501` may or may not be redacted |
| `+44 7700 900 123` | Yes | UK mobile format; standard catch |
| `4 0 4 . 5 5 5 . 0 1 8 2` | No | Digit-spacing breaks the pattern |

**Sample fix to propose:**

```python
# Spelled-out phone numbers — naive but works for common cases
DIGIT_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}

def _normalise_spelled_phones(text: str) -> str:
    # If we see 7+ consecutive digit-words, treat as a phone number
    pattern = r"(?:" + "|".join(DIGIT_WORDS.keys()) + r")(?:\s+(?:" + "|".join(DIGIT_WORDS.keys()) + r")){6,}"
    return re.sub(pattern, "[REDACTED_PHONE_SPELLED]", text, flags=re.I)

# Digit-spaced phone numbers — collapse and re-check
def _normalise_spaced_phones(text: str) -> str:
    pattern = r"\b(?:\d\s+\.?\s*){9,}\d\b"
    return re.sub(pattern, "[REDACTED_PHONE_SPACED]", text)
```

The "7+ consecutive digit-words" heuristic is good enough for the
common cases without over-firing on phrases like "I have three
options."

### Employee IDs

| ID | Default catches? | Why / why not |
|---|---|---|
| `EMP-04827` | No | Custom format; no built-in pattern |
| `Staff #4082` | No | Same |
| `RJP/2019/0451` | No | Same |
| `A.M.-2021-EUR-007` | No | Same |
| `Badge: CM18234` | No | Same |

Zero catches expected from the default scrubber. This is the
single biggest gap, and the most realistic one — every organisation
has its own ID conventions.

**Sample fix to propose:**

```python
# Custom employee ID patterns — organisation-specific
EMPLOYEE_ID_PATTERNS = [
    re.compile(r"\bEMP-\d{4,6}\b"),
    re.compile(r"\bStaff\s*#\s*\d{3,6}\b", re.I),
    re.compile(r"\b[A-Z]{2,4}/\d{4}/\d{3,5}\b"),
    re.compile(r"\b[A-Z]\.[A-Z]\.-\d{4}-[A-Z]{2,4}-\d{3,4}\b"),
    re.compile(r"\bBadge\s*:?\s*[A-Z]{2}\d{5,6}\b", re.I),
]

# Add to the regex pass:
def _custom_id_redact(text: str) -> str:
    for pat in EMPLOYEE_ID_PATTERNS:
        text = pat.sub("[REDACTED_EMPLOYEE_ID]", text)
    return text
```

The ADR note for this fix should say: *"Employee ID patterns are
organisation-specific. The patterns above match our reference
corpus. For your production corpus, audit the first 20 documents
to identify the actual ID formats in use, then extend this list."*

### Addresses

| Address | Default catches? | Why / why not |
|---|---|---|
| `1-2-3 Shibuya-ku, Tokyo 150-0002, Japan` | Partial | Presidio LOCATION catches "Tokyo" / "Japan"; full address stays |
| `Office 412, Sheikh Zayed Road, Dubai, UAE` | Partial | Catches "Dubai" / "UAE"; building info stays |
| `Flat 4B, 23rd Cross Road, Bandra West, Mumbai 400050` | Partial | Catches "Mumbai"; rest stays |
| `221B Baker Street, London NW1 6XE` | Partial | Catches "London"; "221B Baker Street" stays — even though it's iconic |

Default scrubber catches city names but not full addresses. For
most use cases this is acceptable (city alone isn't usually PII).
For high-sensitivity contexts (medical, legal), need a stronger
approach.

**Sample fix to propose:**

```python
# UK postcode catches the "NW1 6XE" pattern
UK_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s+\d[A-Z]{2}\b")

# US ZIP code
US_ZIP = re.compile(r"\b\d{5}(?:-\d{4})?\b")

# Japanese postcode (NNN-NNNN)
JP_POSTCODE = re.compile(r"\b\d{3}-\d{4}\b")
```

For full address structure (building + street + city + postcode
as a unit), no regex/NER combination is reliable. Name this as a
known limitation; the audit step catches what's missed.

### Financial

| Item | Default catches? | Why / why not |
|---|---|---|
| IBAN: `GB82 WEST 1234 5698 7654 32` | Yes | IBAN_CODE is a built-in Presidio entity |
| Card last 4: `****-****-****-4521` | No | Masked cards don't match credit card regex |
| Project code: `PRJ-2024-KHANJAR-EU` | Shouldn't fire | Not PII — project codes are operational, not personal |

The project code is a **deliberate distractor**. If a learner's
scrubber redacts it, they've over-tuned. Note in feedback:
*"Project codes aren't PII. Over-redaction degrades retrieval quality
without privacy benefit."*

For the masked card — debatable whether to scrub. The last 4 alone
isn't enough to identify a person, but combined with a name +
amount could be. Conservative answer: scrub it.

```python
MASKED_CARD = re.compile(r"\*{2,}[-\s]*\*{2,}[-\s]*\*{2,}[-\s]*\d{4}\b")
```

---

## What a "good" failure log looks like

This is roughly what a high-scoring submission contains. Use as
calibration when grading.

```markdown
# PII Stress Test — W8 Activity Findings

**Date:** 2026-06-27
**Run by:** [learner name]

## Summary
- Total PII items in source: 27
- Caught by scrubber: 12 / 27 (44%)
- Missed entirely: 13 / 27
- Partially redacted: 2 / 27

## Failure categories

### Names (4 / 7 caught)
- ✓ Rajesh Patel, Aisha Mohammed, Carlos Mendoza, Bob Smith caught
- ✗ Dr. Yuki Tanaka — title "Dr." reduces NER confidence below 0.5
- ✗ Fatima Al-Rashid — hyphenated MENA names underrepresented in en_core_web_lg
- ✗ Alice (single name) — Presidio scores single names lower

### Obfuscated emails (0 / 3 caught)
- All three missed. Confirmed: default regex requires literal `@`.

### Phones (2 / 5 caught)
- ✓ +81 and +44 formats caught (international prefix anchors regex)
- ✗ Spelled-out, digit-spaced, and ext-suffix formats missed

### Employee IDs (0 / 5 caught)
- None caught. Expected — no out-of-box pattern for custom IDs.

### Addresses (partial on 3 / 4)
- City names caught via Presidio LOCATION
- Building / street / postcode stayed in all cases

### Financial (2 / 3 caught; 1 false-positive risk)
- ✓ IBAN caught
- ✗ Masked card stayed
- ⚠ Project code PRJ-2024-KHANJAR-EU correctly NOT redacted (not PII)

## Proposed fixes

### Fix 1 — Obfuscated emails
Problem: Default regex requires `@`; obfuscated forms slip through.
Fix: Add patterns for `[at]` / `(at)` / full-width `＠`.
Trade-off: Slight risk of false positives on prose like "look at me".
Status: IMPLEMENTED — see commit a1b2c3d. Catches all 3 in re-test.

### Fix 2 — Employee IDs
Problem: No patterns for organisation-specific IDs.
Fix: Per-organisation pattern list in pii.py.
Trade-off: Maintenance — new ID formats need new patterns.
Status: PROPOSED — see EMPLOYEE_ID_PATTERNS in pii.py (commented out).

### Fix 3 — Spelled-out phone numbers
Problem: Words like "zero one two..." don't match digit regex.
Fix: Heuristic — 7+ consecutive digit-words → redact.
Trade-off: Naive; might miss "two thousand" type constructions.
Status: PROPOSED.

## What I'd not fix
- Hyphenated MENA names. Lowering Presidio threshold catches them
  but triggers 4+ false positives elsewhere. Net negative.
- Full addresses. No reliable pattern. Rely on audit step instead.

## ADR update
Logged in docs/adr/0001-capstone-framing.md under "PII handling":
"Known limitations: obfuscated emails partially handled (see commit
a1b2c3d); employee ID patterns are organisation-specific and must
be re-tuned per deployment; full addresses rely on the manual
audit step."
```

That's the shape of a thoughtful submission. Note especially:

- **Specific reasoning** — not "Presidio missed it" but
  "hyphenated MENA names underrepresented in en_core_web_lg"
- **Trade-off acknowledgement** — every proposed fix has a stated
  cost
- **What NOT to fix** — the most mature signal. A learner who can
  decline a fix has internalised the cost/benefit.
- **ADR linkage** — closes the loop from activity → ADR → audit

---

## Common partial-credit answers and how to coach

### "Presidio is just bad at names"

Push back: *"Which names? Which model? Which threshold? 'Bad at
names' isn't actionable. Try lowering `score_threshold` to 0.3 and
see what changes — both catches and false positives."*

### Lists everything as "missed" without categorising

Push back: *"You have a list. Now group it. What patterns in the
list share a root cause?"* The grouping is where the diagnostic
muscle gets built.

### Proposes 12 different fixes without picking priorities

Push back: *"If you could only ship 3 fixes, which 3? Why those?"*
The triage instinct matters more than the fix list.

### Catches >20 / 27 on first pass

Likely cause: they pre-tuned the scrubber before running the
activity. Ask: *"What did you change before running?"* If they
say "I added employee ID regex from the start" — that's fine and
actually shows initiative. Note it; don't penalise.

### Catches <8 / 27

Likely cause: Presidio not installed correctly. Check:

```python
from presidio_analyzer import AnalyzerEngine
print(AnalyzerEngine().analyze("Alice lives in London", language="en"))
# Should return list with PERSON and LOCATION
```

If empty list — spaCy model not downloaded. Fix:

```bash
python -m spacy download en_core_web_lg
```

---

## Threshold tuning recommendations

For the default Presidio analyzer, the curriculum's recommended
thresholds:

| Entity | Recommended threshold | Why |
|---|---|---|
| PERSON | 0.5 (default) | Lower triggers false positives on capitalised nouns |
| LOCATION | 0.6 | Cities OK; lower threshold fires on "Park" / "Center" generic nouns |
| ORGANIZATION | 0.7 | Org names overlap with common nouns; needs higher confidence |
| US_PASSPORT, US_DRIVER_LICENSE | 0.5 | Patterns are distinctive |
| IBAN_CODE | 0.6 | Format-specific; rarely false positive |
| DATE_TIME | **disabled** | Too noisy in policy text — every "30 days" fires |

Code to apply:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import PERSON_RECOGNIZER  # etc.

analyzer = AnalyzerEngine()
results = analyzer.analyze(
    text=text,
    language="en",
    entities=["PERSON", "LOCATION", "ORGANIZATION", "IBAN_CODE",
              "US_PASSPORT", "US_DRIVER_LICENSE"],
    score_threshold=0.5,  # global floor
)
# Then filter results further if needed
results = [r for r in results if not (r.entity_type == "LOCATION" and r.score < 0.6)]
```

Learners who include threshold tuning in their failure log get
extra credit — it shows they engaged with Presidio's internals,
not just its output.

---

## Activity grading rubric

| Criterion | Weight | What to look for |
|---|---|---|
| Completeness of failure log | 25% | All 30+ items checked; no skipped categories |
| Specificity of failure analysis | 30% | "Why" explanations, not just "missed" |
| Quality of proposed fixes | 25% | Fixes are concrete, trade-offs named |
| Implementation of ≥1 fix | 10% | Optional but rewarded |
| ADR linkage | 10% | Findings reach the ADR's "known limitations" |

A learner submitting all five gets full credit even if their catch
rate is only 14/27 — the activity assesses diagnostic skill, not
scrubber performance.

---

## Tying back to the curriculum

The PII discipline opens this week and threads through:

- **W14** — Multi-tenant routing. The `has_pii` and `pii_types`
  metadata learned here gates retrieval per-user / per-role.
- **W18** — Tool use and agents. Agents that touch external APIs
  need to know which retrieved chunks are PII-sensitive.
- **W25** — Production hardening. The audit cadence learned this
  week becomes a scheduled job in production.
- **W28** — Data residency deep dive. The "OpenAI embeds in US,
  Qdrant in EU" question we named this week gets answered.

In W14, learners who skipped the W8 activity hit walls. The
diagnostic muscle developed here is the load-bearing part of the
PII thread.

---

*End of activity solution. Pair with `AI-RAG_W8_Activity.md` for
delivery to learners during office hours or at the end of W8.*
