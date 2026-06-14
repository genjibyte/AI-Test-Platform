# 50 — Badcase memory / retrieval (design, 2026-06-14)

> **Status: S1 in progress.** Roadmap item **#6** of `docs/00_foundation/47`. Builds on the
> precipitation ledger (`41`, `app/ledger/`). Every output is **advisory**: retrieval surfaces
> real past records as priors for human review only — it never feeds `recommend_with_reasons` /
> `conclusion`, never auto-accepts, and `conclusion` stays `NEED_HUMAN_REVIEW`.

## 0. The reframing that keeps this on-thesis
The ledger already **stores + aggregates** judged candidate tests (`store.py`, `analytics.py`).
#6 adds a **retrieval** layer: *given a new target (and optional failure signature), find the most
relevant past judged records and surface them as advisory precedent for the reviewer* — "on this
target / failure-type, here's what happened before". It is judge-side **memory**, not a generator
crutch.

**Anti-hallucination boundary (load-bearing):**
- Retrieval returns **only real stored records** — it never fabricates a precedent.
- Priors are **advisory**: they inform the human review, never decide; `conclusion` stays
  `NEED_HUMAN_REVIEW`, `auto_accept` stays blocked.
- Using precedent to *hint generation* is producer-side and out of scope here; #6 serves the
  **judge/reviewer**, with precedent that is itself the (already-judged) evidence.
- Historical data is **read-only** — retrieval never writes/backfills (`docs/42` §A).

## 1. Similarity — explainable structural signals first (no opaque embeddings in S1)
Rank candidates by a deterministic, **explainable** score over signals the records already carry
(`JudgedRecord`: `target_class/method`, `failure_type`, `business_pattern`, `test_fingerprint`,
`repo_url`, `conclusion`, `oracle_strength`, `mutation_score`). Every match contributes a *reason*:

| signal | weight | reason |
|---|---|---|
| same `target_class` + `target_method` | +3 | `same_target_method` |
| same `target_class` (any method) | +2 | `same_target_class` |
| same simple class name (last segment) | +1 | `same_simple_class` |
| same `failure_type` (when the query gives one) | +2 | `same_failure_type` |
| shared `business_pattern` | +1 | `same_business_pattern` |
| same `test_fingerprint` | +4 | `duplicate_fingerprint` (near-identical test) |
| same `repo_url` | +1 | `same_repo` |

Only records with a positive score are returned, ranked desc, top-k. The weights are a starting
point (tunable); the **reasons** make every ranking auditable — no black box.

## 2. API (S1)
`app/ledger/retrieval.py`:

```
find_similar(records, *, target_class, target_method=None, failure_type=None,
             business_pattern=None, test_fingerprint=None, repo_url=None, top_k=5) -> list[dict]
```

Pure over a list of `JudgedRecord` (caller supplies the candidate set, e.g. `store.all()` or a
pre-filtered `store.by_target(...)`), so it is fully testable offline. Each result:

```
{record_id, score, reasons, target_class, target_method, failure_type,
 conclusion, oracle_strength, mutation_score}
```

Plus a thin store-backed convenience `find_similar_in_store(store, **query)` = `find_similar(
store.all(), **query)`. Never raises; empty ledger -> `[]`.

## 3. Where consumed (later slices; S1 is the engine only)
- A reviewer-facing "prior cases" view (advisory) when judging a new candidate.
- NOT wired into the verdict. S1 ships the retrieval engine + tests; surfacing is a follow-up.

## 4. Slices
- **S1 — retrieval engine (offline):** `find_similar` + explainable scoring + store convenience.
  Pure, unit-tested. (This doc's focus.)
- **S2 — richer precedent schema:** add structured root-cause / fix fields to `JudgedRecord` (why
  it failed, how it was fixed) so a retrieved prior is *actionable*, not just a label.
- **S3 — (optional, gated) semantic retrieval:** embedding similarity with an explainable
  structural fallback; never replaces the auditable structural signals, never opaque-only.

## 5. Scope guards — what this is NOT
- Not a verdict: precedent never flips `conclusion`/`accept`; `auto_accept_blocked` stays True.
- Not fabrication: returns only real stored records; no synthesized "similar" cases.
- Not a generator feed (judge-side only); historical data read-only; no new dependency (SQLite +
  pure Python, like `store.py`); no embeddings in S1.

## 6. Acceptance (S1)
- A record on the same `target_class.target_method` ranks first and its `reasons` include
  `same_target_method`; a same-`test_fingerprint` record is flagged `duplicate_fingerprint`.
- Querying with a `failure_type` boosts same-failure precedents (`same_failure_type`).
- Empty ledger / no positive match -> `[]`. Retrieval changes no `conclusion` (regression-tested).

## 7. Relationship to siblings
`41` precipitates judged records; `43/45/46/48/49` enrich each record with provenance + advisory
value signals; `50` (this) **retrieves** the most relevant of them as advisory precedent — the
"badcase memory" the owner's #6 asks for, judge-side and never auto-accepting.

---

> Records a retrieval signal; grants no scope; changes no verdict. The product stays the
> **judgment** — here, *relevant precedent* for the reviewer — not a green checkmark.
