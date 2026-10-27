# Incident Runbook: Stale Semantic Cache After Policy Update

## 1. Summary

Six employees received an outdated parental-leave answer after `parental_leave_policy.md` was updated. The correct policy is 12 weeks paid plus 4 weeks unpaid leave. Suspect stale semantic-cache data.

## 2. Symptoms

- Assistant answers 6 weeks paid plus 6 weeks unpaid.
- The policy source contains the new entitlement.
- Six employees reported the same outdated answer.
- Document update and tombstone/ingestion checks passed.

## 3. Likely Root Cause

The semantic cache may retain an answer generated before the policy update. A question whose embedding has cosine similarity of at least 0.95 to a cached question can receive the old answer without fresh retrieval. If bypassing the cache returns the updated policy, cache invalidation is the likely cause. If the live answer is also wrong, investigate the knowledge base and tombstone filtering.

## 4. Diagnosis

Run from the Week 10 Capstone root where the specified modules and knowledge base are configured.

### 1. Confirm the cache hit

```bash
python -c "
from src.rag.qdrant_rag import ask_rag
from src.rag.qdrant_store import load_store
r = ask_rag('How much parental leave is available?', load_store(), use_cache=True)
print('cache_hit:', r.get('cache_hit'))
print('cache_similarity:', r.get('cache_similarity'))
print('answer:', r['answer'])
"
```

Expected: `cache_hit: True`, similarity at least 0.95, and the old answer.

### 2. Bypass cache and check live retrieval

```bash
python -c "
from src.rag.qdrant_rag import ask_rag
from src.rag.qdrant_store import load_store
r = ask_rag('How much parental leave is available?', load_store(), use_cache=False)
print(r['answer'])
"
```

Expected: 12 weeks paid plus 4 weeks unpaid. If the answer remains old, investigate the knowledge base and tombstone filter before clearing the cache.

### 3. Inspect cache state

```bash
python -c "
from src.rag import cache
import sqlite3
print(cache.stats('./results.db'))
conn = sqlite3.connect('./results.db')
rows = conn.execute(
    'SELECT question, answer, hit_count, created_ts '
    'FROM query_cache ORDER BY created_ts'
).fetchall()
for row in rows:
    print(row)
conn.close()
"
```

Expected: cache statistics and entries that can be checked against the policy-update time.

## 5. Remediation

1. Preserve the stale answer and diagnostic output.
2. Clear the cache using the Week 10 Capstone helper:

   ```bash
   python -c "from src.rag.cache import clear_cache; print(clear_cache('./results.db'))"
   ```

3. Confirm the cache is empty:

   ```bash
   python -c "from src.rag import cache; print(cache.stats('./results.db'))"
   ```

4. Re-ask the original question through `ask_rag()` with `use_cache=True`.

Do not restart the service, delete the database, or re-ingest the whole knowledge base.

## 6. Verification

- First re-ask returns the corrected policy and `cache_hit: False`.
- Repeating the equivalent question returns the corrected answer and `cache_hit: True`.
- If cache bypass still returns the old policy, investigate retrieval and tombstone filtering.

## 7. Post-Incident Actions

- Make `--clear-cache` the default for `update_document.py`; allow `--keep-cache` only as an explicit opt-out.
- Add a CI check that rejects document-update workflows without `--clear-cache`.
- Notify the six affected employees through the approved HR channel, apologise, provide the corrected policy, and ask them to reconfirm.
- Alert when `cache_hit_rate > 90%` persists for one hour; review the alert alongside document-update and cache-invalidation logs.

## 8. Time Budget

- Diagnosis: 8 minutes
- Fix and verification: 3 minutes
- Communication and follow-up: 15 minutes

**Target total: 26 minutes.**

*Validation note: The demo SQLite schema and read-only SQL inspection were verified. The application commands above require the Week 10 Capstone implementation. They have not been executed against the current GitHub clone because its required Week 10 modules are absent.*