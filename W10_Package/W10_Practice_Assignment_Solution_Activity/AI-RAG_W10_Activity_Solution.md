# AI-RAG · Week 10 · Activity Solution
## Sample Runbook + Grading Guide

> *Instructor reference. Don't share with learners until they've submitted.*

---

## Part 1 · Sample runbook (a strong submission)

What follows is a representative strong submission for the W10 activity.
A 90th-percentile learner produces something close to this — not
identical, but with the same operational sensibility.

---

> ### Incident · Stale answer from semantic cache after policy update
>
> **Affects:** Knowledge Assistant. Users get the OLD version of a
> document's content even after the document was updated and re-ingested.
>
> ---
>
> ### Symptoms
>
> - User asks a question about a recently updated document
> - The assistant returns content matching the OLD version
> - `cache_hit: true` in the response metadata
> - Document `update_document.py` log shows successful tombstone + ingest
>   on the relevant source
> - Multiple users may report the same issue across hours/days
>
> ### Likely root cause
>
> The semantic cache (`./results.db`, table `query_cache`) was not
> invalidated when the document was updated. The cache holds answers
> generated BEFORE the update. Queries with cosine ≥ 0.95 to a cached
> entry return the stale answer without ever re-running retrieval.
>
> The `update_document.py` script has a `--clear-cache` flag for
> exactly this reason; it was not used.
>
> ### Diagnostic steps
>
> ```bash
> # 1. Confirm cache is being hit
> python -c "
> from src.rag.qdrant_rag import ask_rag
> from src.rag.qdrant_store import load_store
> r = ask_rag('THE USER QUERY', load_store(), use_cache=True)
> print('cache_hit:', r.get('cache_hit'))
> print('cache_similarity:', r.get('cache_similarity'))
> print('answer:', r['answer'])
> "
> ```
> Expected: `cache_hit: True`, similarity ≥ 0.95, answer = OLD content.
>
> ```bash
> # 2. Verify the LIVE KB has new content
> python -c "
> from src.rag.qdrant_rag import ask_rag
> from src.rag.qdrant_store import load_store
> r = ask_rag('THE USER QUERY', load_store(), use_cache=False)
> print(r['answer'])
> "
> ```
> Expected: NEW content. This rules out a tombstone failure — if the
> live answer is still old, the issue is in the KB, not the cache.
>
> ```bash
> # 3. Inspect cache state
> python -c "
> from src.rag import cache
> import sqlite3
> print(cache.stats('./results.db'))
> conn = sqlite3.connect('./results.db')
> rows = conn.execute(
>     'SELECT question, created_at FROM query_cache ORDER BY created_at'
> ).fetchall()
> for q, t in rows[:10]: print(t, q[:60])
> "
> ```
> Expected: cache entries with `created_at` BEFORE the document update
> timestamp — these are the stale ones.
>
> ### Fix
>
> ```bash
> # 1. Clear the entire cache. Cheap; cohort traffic will repopulate.
> python -c "
> from src.rag.cache import clear_cache
> clear_cache('./results.db')
> "
> ```
>
> ```bash
> # 2. Confirm the cache is empty.
> python -c "
> from src.rag import cache
> print(cache.stats('./results.db'))
> "
> ```
> Expected: `total_entries: 0`.
>
> ```bash
> # 3. Re-ask the original question to verify fresh answer.
> python -c "
> from src.rag.qdrant_rag import ask_rag
> from src.rag.qdrant_store import load_store
> r = ask_rag('THE USER QUERY', load_store(), use_cache=True)
> print('cache_hit:', r.get('cache_hit'))  # should be False
> print('answer:', r['answer'])  # should be NEW content
> "
> ```
>
> ### Verification
>
> 1. Cache stats show `total_entries: 1` after the re-ask (one fresh entry)
> 2. Answer to the original user question is the NEW content
> 3. `cache_hit: False` on the first re-ask, `True` on the second
>    (confirms the new answer is being cached correctly)
>
> ### Post-incident actions
>
> 1. **Make `--clear-cache` the default on `update_document.py`.** Add a
>    `--keep-cache` opt-out for the rare case where the operator
>    genuinely doesn't want to clear. Default-safe is non-negotiable.
> 2. **Add a CI check** that fails if `update_document.py` is invoked
>    in any deployment workflow without `--clear-cache`.
> 3. **User remediation:** Post in the HR channel that the assistant
>    has been refreshed. Six users saw the stale answer; ask them
>    to re-confirm. Apologise.
> 4. **Monitoring add:** Alert if `cache_hit_rate > 90%` sustained
>    over 1 hour. A very high hit rate suggests either (a) traffic is
>    very repetitive (probably fine), or (b) cache invalidation is
>    not happening when it should (probably a bug).
>
> **Time budget:** 8 minutes diagnosis + 3 minutes fix + 15 minutes
> post-incident actions and user communication. Total ~25 minutes.

---

## Part 2 · Grading guide

### Criterion 1 — Correct root cause (30%)

| Score | Pattern |
|---|---|
| Full (30) | Identifies cache staleness as primary cause. References the `--clear-cache` flag explicitly. Distinguishes from tombstone failure (which is a DIFFERENT incident with similar symptoms). |
| Partial (15-25) | Identifies cache as the issue but doesn't explain WHY (cache survives KB updates). Misses the `--clear-cache` flag connection. |
| Low (0-10) | Diagnoses tombstone failure instead, or "the LLM is broken," or generic "something is stale." |

**Calibration:** This is the heart of the activity. A learner who
identifies the cache invalidation issue is showing they internalised
the W10 cache lifecycle. Anything else is a red flag for understanding.

### Criterion 2 — Diagnostic steps are executable (25%)

| Score | Pattern |
|---|---|
| Full (25) | At least 3 concrete commands with expected outputs. Commands reference real W10 modules (`cache.stats`, `ask_rag` with `use_cache=False`). Order is logical (confirm symptom → rule out alternatives → confirm root cause). |
| Partial (12-20) | Commands exist but are sketchy ("inspect the cache" with no actual command). Or commands exist but order is unclear. |
| Low (0-10) | "Check the logs" / "look at the cache" — instructions, not commands. A successor couldn't execute. |

### Criterion 3 — Fix is minimal and targeted (20%)

| Score | Pattern |
|---|---|
| Full (20) | Clear the cache (single function call). Re-ask to verify. No corpus changes. No KB reset. |
| Partial (10-15) | Clears cache but also does some unnecessary action (e.g., also re-ingests the document, which was already done). |
| Low (0-5) | "Reset everything" / "re-ingest the corpus" — overcorrection. Or worse: deletes the cache table entirely (the W10 cache schema doesn't drop the table, just empties it). |

### Criterion 4 — Verification is concrete (10%)

| Score | Pattern |
|---|---|
| Full (10) | Specific check: re-ask the original question; confirm `cache_hit: False` on first, `True` on second; confirm new answer text. |
| Partial (5) | "Verify it works" with one concrete signal. |
| Low (0-3) | "Test it" with no specifics, or no verification section. |

### Criterion 5 — Post-incident actions are systemic (15%)

| Score | Pattern |
|---|---|
| Full (15) | At least 2 process changes that prevent recurrence (e.g., default `--clear-cache`, CI check). Plus user remediation (6 users got stale answer; must communicate). |
| Partial (7-12) | One systemic change. Or several actions that are reactive but not systemic ("be more careful"). |
| Low (0-5) | "Add tests" / "be more careful" — no systemic prevention. Or no Section 7 at all. |

### Pass thresholds

- **Distinction (90%+):** All five criteria at full or near-full. Sample
  runbook quality.
- **Pass (70-89%):** Cause + fix correct. Diagnostics + verification
  reasonable. Maybe weaker on systemic post-incident actions.
- **Below pass (< 70%):** Wrong root cause, or fix is overcorrection,
  or post-incident is empty. Learner needs to re-read the runbook
  pattern and try again.

---

## Part 3 · Common pitfalls (and what to write back)

### Pitfall 1 — "Tombstone failure" instead of cache staleness

**What it looks like:** Learner says the old chunks weren't tombstoned;
diagnostic involves checking `count(deleted_at IS NULL)`.

**Feedback to write:** *"The brief says the runbook check passed at
update time — so tombstones are working. Look at the diagnostic
question: if the cache returns `cache_hit: True`, what does that tell
you about which layer is serving the answer?"*

### Pitfall 2 — Overcorrection: re-ingest everything

**What it looks like:** Fix section includes re-running the W8 ingest
pipeline on the whole corpus.

**Feedback:** *"Minimal fixes are a hallmark of good runbooks. The
KB is fine; only the cache is stale. Clearing the cache is one
function call; re-ingesting the corpus is hours of compute and risks
introducing new bugs."*

### Pitfall 3 — No user remediation

**What it looks like:** Section 7 covers process changes but ignores
the 6 users who got the wrong answer.

**Feedback:** *"You fixed the system. What about the people whose
trust the system just damaged? In production, communication IS the
fix. Always include user remediation in post-incident actions when
real users were affected."*

### Pitfall 4 — Process changes that aren't actually changes

**What it looks like:** "We should add more tests." / "We should be
careful." / "We should document this."

**Feedback:** *"These are all true and also useless. What SPECIFIC
change to which SPECIFIC file or workflow prevents the exact incident
from happening again? Default behaviour, CI gate, monitoring alert —
something concrete."*

### Pitfall 5 — Too academic

**What it looks like:** Runbook reads like a textbook. Long
explanatory paragraphs before any commands.

**Feedback:** *"At 02:00 on a worse incident, on-call you will skim
this looking for the diagnostic command. Lead with the command;
explanation in parens. Runbooks are not essays."*

### Pitfall 6 — Confusing the cache layers

**What it looks like:** Learner blames the OpenAI prompt cache, or
the W7 embedding cache.

**Feedback:** *"OpenAI's prompt cache only affects prompt-prefix
billing; the LLM still re-runs with whatever input you send. The
embedding cache (W7) maps text→vector and is invariant to KB updates.
Only the semantic cache (W10 Layer 1) can return a stale answer."*

### Pitfall 7 — Wrong tone

**What it looks like:** Self-deprecation ("I might be wrong about
this but…") or pedantic confidence ("Obviously the cause is…").

**Feedback:** *"Runbook tone is direct without being arrogant.
'Likely root cause: X' is right. 'Obviously X' invites pushback when
you're wrong. 'I might be wrong but…' loses the reader. Try the
first phrasing."*

---

## Part 4 · What this activity actually tests

Less about the W10 material per se — more about whether the learner
has the **incident-response shape** in their head. The W10 material
provides the diagnostic vocabulary; the runbook structure provides
the operational discipline.

A learner who writes a great runbook on the wrong root cause should
score higher than one who writes a sloppy runbook on the right one.
The shape is the lesson.

Calibration check for graders: if you'd hand the runbook to a
junior engineer at 02:00 on a similar incident, would they be able
to execute it without you in the room? That's the bar.
