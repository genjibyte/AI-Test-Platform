# 48 — Business-invariant *verification* (design, 2026-06-14)

> **Status: S1 implemented 2026-06-14 (descriptor + carry, no verification); S2/S3 DESIGN ONLY,
> not approved for code.** Sequel to `45` (invariant *tagging* —
> declared intent) and `46` (oracle-strength / mutation). Roadmap item **#1** of `docs/00_foundation/47`.
> Every signal here is **advisory**: it feeds `review_summary` only, never
> `recommend_with_reasons` / `conclusion`; `auto_accept` stays blocked; `conclusion` stays
> `NEED_HUMAN_REVIEW`; `trusted=False`. No oracle is ever auto-fixed or weakened.

## 0. The one reframing that keeps this on-thesis
"Invariant verification" here does **NOT** mean *verify the code obeys a true business rule*
(that would make the platform a correctness **oracle** — out of scope, charter). It means:

> **Given a *declared* invariant, does the candidate TEST actually pin it?** — i.e. does the
> test *execute* the invariant's code path, *assert* on its observable, and *kill mutants* of
> its logic. We judge the **test's grip on the declared property**, not the property's truth.

So the output is evidence about the *test*, advisory, and it never certifies the invariant is
correct. The invariant statement itself stays **untrusted** (see §2).

## 1. What a "business invariant" is (the kinds we target)
The owner's #1: order / coupon / permission / payment logic — the real targets are **state
transitions, boundary conditions, exception paths, side-effects**. We model an invariant as a
declared descriptor with a `kind`:

- `state_transition` — a legal/illegal state change (e.g. order PAID→SHIPPED allowed, →PAID twice not).
- `boundary` — a numeric/length/time edge (e.g. coupon min-spend, balance ≥ 0).
- `exception` — an illegal input/operation must throw a specific exception (e.g. expired coupon → `CouponExpiredException`).
- `side_effect` — an observable effect must (or must-not) happen (e.g. payment writes one ledger row; a rejected op writes none).

These map onto the existing `business_pattern` vocab (`app/benchmark/business_tags.py`:
`state_transition`, `eligibility`, `money_bound`, `time_currency_boundary`, `audit_trail`, …).

## 2. Provenance & the anti-self-certification rule (load-bearing)
An invariant has a source, and the source decides how far we trust the *statement* (never the
*verdict*):

- **manifest / human-declared** → authoritative **as intent** (still not a correctness oracle).
- **model-declared** (a candidate's own claim of what it tests) → **UNTRUSTED**
  (`declared_invariant_trusted=False`, already in `business_review_rubric`).

**Hard rule (anti-hallucination):** never check a *model-declared* invariant *against the same
model's test* and call it verified — that is circular self-certification, the exact LLM failure
mode this project exists to resist. Model-declared invariants may be shown to a human and may get
*structural* evidence ("this test asserts *something* on these lines"), but they can never reach
`pinned` status on their own authority. Only a **manifest/human** invariant anchors a real
verification target.

## 3. The three evidence dimensions (all reuse existing layers)
For a declared invariant `I` bound to `target_class[.method][:lines]`, compute three independent,
advisory facts about the candidate test — none new-from-scratch:

1. **addressed** — coverage: does any test method execute `I`'s lines/branch?
   Reuse `app/coverage/` (`jacoco_parser`, `jacoco_runner`). `addressed=False` ⇒ the test does
   not even touch the invariant.
2. **asserted** — structural: is there an assertion of the *right shape* on `I`'s observable?
   Reuse `app/quality/test_quality_gate.py` (`_assertion_names`, weak/tautology detection):
   - `exception`-kind ⇒ expect `assertThrows` (and ideally the declared exception type).
   - `boundary` / `state_transition` / `side_effect` ⇒ expect a **non-weak, non-tautological**
     assertion (not `assertNotNull` / `assertTrue(true)` — these are the `_WEAK_ASSERTIONS`).
3. **pinned** — semantic: **line-scoped** mutation. Filter PIT's `mutations.xml` to `I`'s lines
   and compute *killed / total* for just those mutants. High ⇒ the test grips `I`'s logic.
   Needs a small parser extension (see §5). This is the strongest, and it inherits the
   **equivalent-mutant caveat** from `46` §16 — a surviving line-mutant may be *equivalent*, not a
   gap, so survivors must be *explained* (ties to roadmap #3), never auto-scored as failure.

## 4. Roll-up — advisory `invariant_strength` (mirror `oracle_strength`)
Deterministic roll-up, same shape as `app/quality/oracle_strength.py`
(`{level, reasons, metrics, advisory, note}`):

```
invariant_strength ∈ ("unaddressed", "addressed_unasserted", "asserted_unpinned",
                      "pinned", "unknown")
```

- `unaddressed` — coverage shows the invariant's lines are not executed.
- `addressed_unasserted` — executed but no right-shape assertion on the observable.
- `asserted_unpinned` — addressed + asserted, but line-scoped mutants survive (or mutation off);
  may include *equivalent* survivors → must be explained, not condemned.
- `pinned` — addressed + asserted + line-scoped mutants killed. Strongest evidence; **still
  advisory, still `NEED_HUMAN_REVIEW`.**
- `unknown` — no declared invariant, no coverage, or mutation unavailable for the semantic part.

`semantic_strength` stays `"human_review"`. `pinned` is the *most* a machine says; a human still
decides whether the declared invariant was the *right* property.

## 5. Where computed / surfaced (no judging-path change)
- New (when built): `app/quality/invariant_verification.py` →
  `verify_invariant(descriptor, *, coverage, quality_gate, mutation_lines) -> dict`. Pure roll-up
  over inputs the platform already produces; no model, no network.
- Parser extension: `parse_pit_report` gains an **opt-in** per-mutation list
  (`[{line, method, status, mutator}]`) so the caller can line-scope; default return shape
  unchanged (back-compat with `46`).
- Surface in `app/report/generation_report.py` as
  `review_summary["invariant_verification"]` — exactly like `oracle_strength_estimate` is added
  **after** `recommend_with_reasons` with the comment *"does NOT change the recommendation /
  conclusion"*. It populates an **advisory** view; it does **not** silently overwrite the
  human-only rubric fields (`risk_covered`, `oracle_strength`) in `business_review_rubric` — those
  stay for the reviewer (the computed block is parallel + clearly machine-advisory).

## 6. Slices (independently testable; each needs its own go)
- **S1 — descriptor + carry (offline, no compute) — DONE 2026-06-14:** `InvariantDescriptor`
  (`id, statement, kind, target{class,method?,lines?}, observable, source`) +
  `parse_invariants` / `is_anchoring` / `invariant_review_view` in
  `app/benchmark/invariants.py`; declarable on `BenchCase`, carried through `BenchCaseResult`
  (`_case_tags`) and ledger `JudgedRecord` (`ingest`), surfaced **untrusted/unverified** as
  `review_summary["invariant_review"]` (`verified=None`, `auto_accept_blocked=True`). The
  anti-self-certification rule (§2) is enforced: model-declared invariants are non-anchoring.
  No verification computed. (`tests/test_invariants.py`.)
- **S2 — structural verification (deterministic):** compute `addressed` (coverage) + `asserted`
  (quality gate) → `invariant_strength` without mutation. Offline-testable with fixtures.
- **S3 — semantic verification (gated):** line-scoped mutation (`pinned`), behind
  `mutation_enabled` (so it inherits `46`'s gating); requires the §5 parser extension + a
  survivor *explanation* hook (real-gap vs equivalent vs trivial).

## 7. Scope guards — what this is NOT
- Not a correctness oracle: never decides the invariant is *true*, never compares to a "right"
  answer, never rewrites / weakens / adds an assertion to make an invariant "pass".
- Not self-certifying: a model-declared invariant never verifies itself (§2).
- Not a gate: `invariant_strength` never feeds `recommend_with_reasons`/`conclusion`; `pinned`
  ≠ accept. `auto_accept_blocked` stays `True`; `trusted=False`.
- No new dependency: reuses coverage + quality-gate + mutation. Mutation stays gated/opt-in.
- Historical `bench.db` read-only; no backfill of invariants onto past runs.

## 8. Acceptance (when/if implemented)
- A manifest case with a declared `exception`-kind invariant + a candidate test that uses
  `assertThrows` on the right path → `addressed=True, asserted=True`; with mutation on and
  line-mutants killed → `pinned`. The same candidate with the `assertThrows` removed →
  `addressed_unasserted`. A green-but-empty test (cf. `46` §15 negative control) →
  `unaddressed`/`addressed_unasserted`, **never** `pinned`.
- Across all states: `conclusion` stays `NEED_HUMAN_REVIEW`, `accept_rate=None`,
  `auto_accept_blocked=True` (regression-tested, like `run_kind`/oracle).
- A *model-declared* invariant can never reach `pinned` on its own authority (§2) — explicit test.

## 9. Relationship to siblings
`45` declares the invariant (intent). `48` (this) asks *did the test pin it?* using `46`'s
mutation as the semantic core, the quality gate as the structural core, and coverage as the
reachability core. It is the invariant-scoped, judge-side complement to the class-wide
`oracle_strength` — and it is where roadmap #1 (verify) and #3 (survivor explanation) meet.

---

> Records a signal; grants no scope; changes no verdict. The product stays the **judgment** —
> "does this candidate test actually pin the business rule it claims to?" — not a green checkmark.
