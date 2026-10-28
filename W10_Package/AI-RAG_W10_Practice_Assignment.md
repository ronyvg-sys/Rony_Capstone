# AI-RAG · Week 10 · Activity
## Write an Operations Runbook for a Likely Incident

> **~60 minutes · take-home · individual work**
>
> Per the W10 instructor framing: *"in production, operational
> reliability is the differentiator. Algorithm gains plateau; ops
> gains compound."* This activity makes you the on-call engineer.

---

## The brief

You're three months into running the capstone Enterprise Knowledge
Assistant in production. It's serving ~200 employees across HR, IT,
and Finance. Caching is on (0.95 threshold). Tombstones are in place.
The system has run smoothly for 11 weeks.

On a Tuesday morning at 09:47, an HR business partner pings the
shared channel:

> *"Hey — I asked the assistant about parental leave policy and it told
> me '6 weeks paid + 6 weeks unpaid.' But the policy was updated last
> Friday to 12 weeks paid + 4 weeks unpaid. Why is it giving the old
> answer?"*

You check the corpus. `parental_leave_policy.md` was indeed updated
on Friday. Your colleague pushed the update through `update_document.py`
and confirmed the runbook checks passed at the time.

**Your task: write the runbook for this incident.**

Six employees have asked the same question this week. The HR partner
is escalating to the head of People Operations by lunch.

---

## What you write

Create `wk10-incident-runbook.md` with these sections:

### 1. Title + one-line summary (1 line)
A clear, searchable title. Future-you needs to find this.

### 2. Symptoms (3-5 bullets)
What the user sees. What signals tell you it's THIS incident, not a
different one with similar symptoms.

### 3. Likely root cause (1 paragraph)
Your best guess at what's wrong, based on the W10 material. Be specific
— "the system has a bug" is not a root cause; "the semantic cache was
not invalidated when the document was updated" is.

### 4. Diagnostic steps (3-6 commands or queries)
Ordered. Each step has an expected output that confirms or rules out
the root cause. Include actual code/commands a successor could run.

### 5. Fix (the steps to resolve, ordered, with commands)
What you'd actually type. Be specific. Assume the successor is
competent but does not have your context — they need exact commands.

### 6. Verification (2-3 checks to confirm it's fixed)
How the on-call engineer confirms the issue is resolved BEFORE marking
the incident closed.

### 7. Post-incident actions (2-4 items)
Process changes to prevent the next recurrence. These are the
medium-term fixes that don't ship in the heat of the moment.

### 8. Time budget
Approximate time for diagnosis + fix at the bottom of the doc.

---

## Constraints

- **Real commands.** Anything you write should actually work against
  the W10 build. Test it before submitting.
- **Self-contained.** The runbook should be readable by someone who
  was not in the original incident. Don't assume context.
- **Under 600 words for sections 1-6.** Runbooks must be skim-able
  under stress. Post-incident actions (Section 7) can be longer if
  warranted.
- **Tone: incident-channel direct.** Not academic, not chatty. Future-you
  at 02:00 on a worse incident will thank present-you.

---

## What good looks like

A strong runbook for THIS incident will:

1. Diagnose **cache staleness** as the likely cause (not a tombstone
   failure — the runbook check confirmed the tombstone worked).
2. Run `cache.stats('./results.db')` to check cache state.
3. Inspect specific cache rows for the affected question text.
4. Fix by `clear_cache` + re-ask to repopulate.
5. Verify with one fresh query that returns the new answer.
6. Post-incident: **make `--clear-cache` mandatory on document updates**
   (either in the script default, or in a CI check, or both).

Bonus credit for:
- Considering the alternative root cause (tombstone bug) and how to
  rule it out
- Recognising that 6 employees got the stale answer — what's the
  remediation? (Probably: post in the HR channel; clarify.)
- Suggesting a monitoring change that would catch this faster next
  time (e.g., alert on `cache_hit_rate > 90% over 1 hour` — possibly
  the cache is too generous)

---

## What weak runbooks look like (avoid these)

- **"Restart the service."** Doesn't apply here; there's no service
  restart. Also: runbooks that begin with "restart" are usually
  evidence of unfinished thinking.
- **"Run all the verifier tests."** The verifier validates the build,
  not the production state. Tests aren't a debugging tool in this
  context.
- **"Clear the entire database."** Overcorrection. Clearing the cache
  is enough; clearing the KB is destructive.
- **"Re-ingest every document."** Same — over-broad. The issue is
  cache staleness for ONE document, not corpus corruption.
- **Vague Section 7.** "Add more tests" is not a post-incident action.
  "Add a CI check that fails if `update_document.py` is called
  without `--clear-cache`" is.

---

## Submission

Push to your capstone repo as `docs/runbooks/wk10_incident_stale_cache.md`.
This becomes your **second** runbook artifact — the first was
`document_update.md` (procedural). This one is reactive (incident
response). Real systems have both flavours.

Tag your commit message: `W10 activity: stale cache incident runbook`

---

## Grading

| Criterion | Weight | What we look for |
|---|---|---|
| Correct root cause identified | 30% | Cache invalidation, not tombstone failure |
| Diagnostic steps are executable | 25% | Real commands, in order, with expected outputs |
| Fix is minimal and targeted | 20% | Cache clear + re-ask, not corpus reset |
| Verification is concrete | 10% | Specific check, not "test it" |
| Post-incident actions are systemic | 15% | Process change that prevents recurrence |

Pass mark: 70%. Distinction: 90%+.

---

## Why this activity exists

By W29 (deployment + CI/CD) you will have 4-5 runbooks of this shape
in your capstone repo. This is the first reactive one. The pattern is
the same in every senior engineering role you'll ever hold:
**incident → diagnosis → fix → prevention.** Get the muscle now.

Algorithms are interesting. Operations are what get paid.
