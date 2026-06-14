# 52 — Review digest (design, 2026-06-14)

> **Status: implemented 2026-06-14.** The **consolidation / capstone** of the advisory judging
> signals (`46` oracle+mutation, `48` invariant, `49` survivors, `51` mock smells, the quality
> gate). Advisory: it READS signals already on `review_summary` and emits a prioritized checklist;
> it computes nothing new, never feeds `recommend_with_reasons`/`conclusion`, `auto_accept` stays
> blocked, `conclusion` stays `NEED_HUMAN_REVIEW`. A flag is a place to look, not a rejection.

## 0. Why
The judge-side value layer now emits many separate signals on `review_summary`
(`oracle_strength_estimate`, `mutation_survivors`, `invariant_review`, `mock_smells`, `quality`).
A human reviewer should not have to assemble them. The **digest** rolls them into one ordered
"what to look at" view — the unified **judgment surface**. It is the product (*the judgment*) made
usable, not a new detector.

## 1. What
`app/review/review_digest.py`:

```
build_review_digest(review_summary) -> {
  headline, flags:[{signal, severity, message}], flag_count,
  auto_accept_blocked: True, conclusion: "NEED_HUMAN_REVIEW", advisory: True, note
}
```

Pure; never raises; reads only the keys present (signals are attached at different layers).

## 2. Flag rules (advisory severity, not a verdict)
| source signal | condition | severity |
|---|---|---|
| `quality.blockers` | any | high |
| `oracle_strength_estimate` | `none` / `weak` | high |
| `oracle_strength_estimate` | `mixed` | medium |
| `mock_smells` | `mock_of_target` | high |
| `mock_smells` | `real_dependency` | medium |
| `mock_smells` | `stub_returns_null` / `loose_matchers` | low |
| `mutation_survivors` | `survived_weak_oracle` / `not_covered` | medium |
| `mutation_survivors` | `survived_maybe_equivalent` | low |
| `invariant_review` (anchoring only) | `unaddressed` / `addressed_unasserted` | medium |
| `invariant_review` (anchoring only) | `asserted_unpinned` | low |

Flags are sorted high→medium→low. `headline` names the top flag (or "no advisory flags (still
human review)"). Non-anchoring (model-declared) invariants are skipped (they never self-certify).

## 3. Where built (twice — reads what's present each time)
- **`generation_report`** (per-candidate): after `oracle_strength_estimate` + `mock_smells` →
  `review_summary["digest"]` covers the per-candidate signals (the API/report path).
- **`runner._attach_digest`** (benchmark): rebuilt **last**, after `invariant_review` /
  `mutation_survivors` / `business_rubric` are attached, so the benchmark digest reflects those too.

## 4. Scope guards — what this is NOT
- Not a verdict / not a score: it never feeds `recommend_with_reasons`/`conclusion`;
  `auto_accept_blocked` stays True; flags are review pointers, never rejections.
- Not a new detector: it only reads existing signals (no new computation, no new judging logic).
- No new dependency; pure; reads-only over `review_summary`.

## 5. Acceptance
- `oracle none` -> a high flag + "needs careful review" headline; `mock_of_target` -> high;
  `survived_weak_oracle` -> medium; an anchoring `addressed_unasserted` invariant -> medium; a
  non-anchoring invariant -> no flag. No signals -> "no advisory flags", `flag_count == 0`.
- Flags ordered high→medium→low. `auto_accept_blocked` True and `conclusion` `NEED_HUMAN_REVIEW`
  in every digest. Surfaced as `review_summary["digest"]`; changes no `recommendation`/`conclusion`
  (regression-tested).

---

> Consolidates signals; grants no scope; changes no verdict. The product stays the **judgment** —
> here, the *one prioritized review view* — not a green checkmark.
