# 49 — Survived-mutant classification (design, 2026-06-14)

> **Status: S1+S2 implemented 2026-06-14.** Builds on `46` (mutation)
> and `48` (the `scoped_mutants_survive` reason). Every output here is **advisory**: it feeds
> `review_summary` / the report only, never `recommend_with_reasons` / `conclusion`;
> `auto_accept` stays blocked; `conclusion` stays `NEED_HUMAN_REVIEW`; `trusted=False`.

## 0. The honest limit (what keeps this on-thesis)
**Equivalent-mutant detection is undecidable in general** — we cannot *prove* a surviving mutant
is equivalent. So this slice does NOT label mutants "equivalent" with authority and NEVER concludes a test
is bad because a mutant survived. It only:

1. separates the **decidable** facts (a mutant was *not covered* vs *covered-but-survived*), and
2. attaches an **advisory, low/medium-confidence** explanation + heuristic hint per survivor,

so a human reviewer sees *"8/10 killed; the 2 survivors are 1 uncovered line (add a test) + 1
boundary mutant that may be equivalent (review)"* instead of a bare *"0.8 = weak"*. The product is
the *explanation that guides review*, not a verdict (`46` §16 showed exactly these two kinds on
real Apache code).

## 1. Categories (per non-killed mutant)
A "survivor" here = any mutant not detected (`status != KILLED/TIMED_OUT`). Categories:

- **`not_covered`** (decidable) — `status == NO_COVERAGE`: the test never executes this line. A
  **coverage** gap, not an oracle weakness. *Action:* add a test that exercises it.
- **`survived_weak_oracle`** (the actionable majority) — `status == SURVIVED` on a mutator that is
  rarely equivalent (math, negate-conditionals, return-value): the test runs the code but its
  assertions don't catch the change. *Action:* strengthen the assertion.
- **`survived_maybe_equivalent`** (low-confidence hint) — `status == SURVIVED` on a mutator class
  that is *often* equivalent in practice (conditional-boundary, void-method-call,
  increments-on-unused): flagged for human review, **never asserted as equivalent**.
- **`survived_unclassified`** — survived, unknown mutator: review needed.

## 2. The mutator heuristic (advisory, not truth)
A small map from PIT's (short) mutator name to a default category + equivalence-likelihood
(`low`/`medium`), used ONLY to pick `survived_weak_oracle` vs `survived_maybe_equivalent`:

| mutator (short) | default for SURVIVED | equiv-likelihood |
|---|---|---|
| `MathMutator`, `NegateConditionalsMutator`, `PrimitiveReturnsMutator`, `EmptyObjectReturnValsMutator`, `BooleanFalseReturnValsMutator`, … | `survived_weak_oracle` | low |
| `ConditionalsBoundaryMutator`, `VoidMethodCallMutator`, `IncrementsMutator` | `survived_maybe_equivalent` | medium |
| unknown | `survived_unclassified` | unknown |

The table is **non-blocking and extensible**; an unknown mutator is allowed. An
`equivalence_likelihood` (`none`/`low`/`medium`/`unknown`) is always surfaced; nothing is proof.

## 3. Output schema + roll-up
`classify_survivors(mutations) -> dict` (pure; consumes the rows from
`parse_pit_report(..., include_mutations=True)`):

```
{
  "survivors": [ {line, method, mutator, status, category, explanation, equivalence_likelihood}, ... ],
  "counts": {not_covered, survived_weak_oracle, survived_maybe_equivalent, survived_unclassified},
  "total_survivors": int,
  "advisory": True,
  "note": "explanation only; survival is not proof a test is weak (equivalence undecidable)",
}
```

`explanation` is human text derived from the mutator (e.g. `ConditionalsBoundaryMutator` →
"changed a conditional boundary (e.g. > to >=); may be unreachable/equivalent — review").

## 4. Where consumed (no judging-path change)
- **Invariant verification (`48`):** when an invariant is `asserted_unpinned` with
  `scoped_mutants_survive`, attach the classified survivors *for that invariant's scope* so the
  reason is explained, not bare. (Enriches `review_summary["invariant_review"]`.)
- **Report (`report_md.py`):** a new advisory "Survived mutants" section (counts + top survivors
  with explanations) — survived mutation explanations enter the report. Rendered only when
  per-mutation rows exist (i.e. a gated run with `include_mutations`); otherwise omitted.

## 5. Slices
- **S1 — classifier core (offline) — DONE:** `app/mutation/survivors.py` `classify_survivors` +
  the mutator map + roll-up. Pure, unit-tested, no PIT.
- **S2 — surface — DONE 2026-06-14:** (1) the invariant view attaches each anchoring invariant's
  scoped, classified survivors to `verified["survivors"]` (explaining `scoped_mutants_survive`);
  (2) `run_case._attach_mutation_survivors` puts whole-run `classify_survivors` on
  `review_summary["mutation_survivors"]` (gated; `_maybe_mutation` now always requests rows);
  (3) `report_md._survivor_lines` renders an advisory "Survived mutants" aggregate section (omitted
  when no rows). All advisory; verdict unchanged.

## 6. Scope guards — what this is NOT
- Never asserts a mutant *is* equivalent (undecidable); `maybe_equivalent` is an advisory hint.
- Never condemns a test or changes a verdict from a survivor; `auto_accept_blocked` stays True,
  `conclusion` stays `NEED_HUMAN_REVIEW`.
- No new dependency; consumes the existing PIT rows. Mutation stays gated/opt-in.
- Read-only over historical data; no backfill.

## 7. Acceptance — live
- A `NO_COVERAGE` row → `not_covered`; a `SURVIVED` `MathMutator` → `survived_weak_oracle`; a
  `SURVIVED` `ConditionalsBoundaryMutator` → `survived_maybe_equivalent`; an unknown mutator →
  `survived_unclassified`. `KILLED`/`TIMED_OUT` are not survivors.
- On the `46` §16 real data (commons-cli `validate()`): the L125 `NO_COVERAGE` →
  `not_covered`, the L136 `ConditionalsBoundaryMutator` `SURVIVED` → `survived_maybe_equivalent` —
  matching the human analysis there.
- All advisory: classification never flips `conclusion`/`accept` (regression-tested).

## 8. Relationship to siblings
`46` produces the mutants; `48` line-scopes them to an invariant and flags survivors; `49` (this)
*explains* those survivors so review is guided. Together they connect assertion
strength + mutation + survived-mutant explanation, all in the report, all advisory.

---

> Records an explanation signal; grants no scope; changes no verdict. The product stays the
> **judgment** — here, *why* a mutant survived — not a green checkmark.
