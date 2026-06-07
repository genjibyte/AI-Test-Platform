# Preflight Overload-Ambiguity Extension — Design / Decision Prep

> Date: 2026-06-07. **DESIGN ONLY — not implemented.** Boundary: no pipeline
> change, no repair, no oracle change, no model run in this doc. Build only **if**
> the running v3.2.3 10-case pro benchmark shows overload-ambiguity is *widespread*
> (≥2 distinct cases), not BooleanUtils-specific. Prepares step-6 ("扩 preflight")
> so the post-benchmark decision is fast and evidence-driven.

---

## 0. Why now (and why deterministic, not more prompt)

The v3.2 → v3.2.1 → v3.2.2 → v3.2.3 prompt iterations each fixed one Java
overload-ambiguity sub-case and surfaced the next (varargs individual values →
named array → bare null → mixed boxed/primitive). `docs/31` §7 already concluded
**prompt compliance alone is unreliable** for compiler-enforced overload edge
cases. The durable answer is the deterministic preflight (it already blocks
unlisted method/arity + the ambiguous varargs pair). Extending it to the two
*shapes* the prompt rules chase would make the fix prompt-independent.

Whether to build it depends on the benchmark. This doc preps **both branches**.

---

## 1. The two ambiguity shapes (both near-detectable in today's preflight)

`evaluate_generated_test_preflight` already extracts target calls
(owner/method/arity) and can split args (`_split_args`). It uses **arity only**.
These two shapes need **light lexical arg classification**, *not* type inference:

**Shape A — bare-null overload ambiguity** (v3.2.2 target)
- e.g. `BooleanUtils.toBoolean(null)` — ambiguous between `toBoolean(Boolean)` and `toBoolean(String)`.
- Trigger: a `null` literal at a position where ≥2 same-arity overloads have *different reference types*, and no overload disambiguates.

**Shape B — mixed boxed/primitive ambiguity** (v3.2.3 target)
- e.g. `BooleanUtils.toBoolean(Integer.valueOf(3), 1, 2)` — ambiguous between `toBoolean(int,int,int)` and `toBoolean(Integer,Integer,Integer)`.
- Trigger: a same-arity overload family has both an all-primitive and an all-boxed variant, and the call mixes a clearly-boxed arg with a clearly-primitive literal.

---

## 2. Minimal mechanism (lexical only, conservative)

Classify each argument lexically — never infer variable types:
- `NULL` — arg is exactly `null`.
- `PRIMITIVE_LITERAL` — int/long/double/boolean/char literal (`123`, `1.0`, `true`, `'c'`, `0x..`).
- `BOXED_LITERAL` — `Integer.valueOf(..)`, `Boolean.TRUE/FALSE`, `Boolean.valueOf(..)`, `new Integer(..)`, `Character.valueOf(..)`, …
- `UNKNOWN` — anything else (variables, expressions).

Param kinds come from the already-parsed overload signatures: REFERENCE
(`Boolean/String/Integer/BigDecimal/…`) vs PRIMITIVE (`boolean/int/double/…`).

- **Shape A:** a `NULL` arg + ≥2 same-arity overloads differ in reference type at that position + nothing disambiguates → flag.
- **Shape B:** same-arity family has both all-primitive and all-boxed variants + the call mixes `BOXED_LITERAL` and `PRIMITIVE_LITERAL` → flag.
- **Conservatism (critical):** flag **only when certain**. Any `UNKNOWN` in a deciding position → PASS (defer to Maven). This matches the existing gate's FP-averse philosophy: it *skips Maven* on a block, so over-rejection is the costly error — bias toward letting Maven judge.

New blocker codes (mirroring the existing ones): `ambiguous_null_overload_call`,
`ambiguous_boxed_primitive_overload_call`.

---

## 3. Boundary / red-lines (unchanged)

- Deterministic, no LLM (`docs/07` A2).
- No edit / auto-fix / oracle rewrite (`docs/07` P5/A5). On flag → `COMPILE_FAILURE`
  + `PREFLIGHT_REJECT`, conclusion stays `NEED_HUMAN_REVIEW` — reuses the existing chain.
- **Narrow.** Only these two shapes. Explicitly **not** doing: generic-assignment
  checks, instance-receiver type inference (the user's listed gaps) — those need
  real type analysis and stay out of scope.
- Lexical classification only; conservative; defer to Maven on any doubt.

---

## 4. Decision gate (set by the running benchmark)

- **BUILD** if Shape A/B appears in **≥2 distinct manifest cases** → a class-of-failure worth a deterministic backstop.
- **SHELVE + accept-outlier** if **only BooleanUtils** hits it → document BooleanUtils as a known overload-pathological case; keep the prompt guardrails; do not over-engineer the gate for one class.
- Either way the v3.2.1–v3.2.3 prompt guardrails stay (cheap; help compliant models). The preflight extension is the robust backstop only if widespread.

---

## 5. If built: validation (zero model cost first)

1. Offline replay over existing `var/benchmark/*/bench.db` generated tests (like `docs/33`): confirm it flags the known `toBoolean(null)` / `toBoolean(Integer.valueOf(3),1,2)` cases and **over-rejects nothing** (0 false-kills on the historical jobs).
2. Then one single-case live BooleanUtils to confirm `PREFLIGHT_REJECT` fires (needs confirmation).

---

## 6. Risk

Lexical classification can misjudge an exotic arg; mitigated by `UNKNOWN → PASS`.
Worst case under conservatism: a real ambiguity isn't flagged → Maven catches it
(safe direction). The reverse (flagging a compilable call, skipping Maven) is what
the conservatism prevents.

---

## 7. Implementation status (2026-06-07) — IMPLEMENTED + VALIDATED (minimal)

Greenlit ("允许最小实现"). Built minimally and validated offline before trusting it.

- **Code** (`app/quality/generated_test_preflight.py`): `_Call` now carries `args`;
  added lexical `_classify_arg` (NULL / BOXED / PRIMITIVE / UNKNOWN), `_param_is_reference`,
  and the two conservative detectors `_null_overload_ambiguous` (Shape A) +
  `_boxed_primitive_mix_ambiguous` (Shape B), wired into
  `evaluate_generated_test_preflight` with blocker codes
  `ambiguous_null_overload_call` / `ambiguous_boxed_primitive_overload_call`.
  No pipeline/report change beyond the existing `PREFLIGHT_REJECT` path;
  conclusion stays `NEED_HUMAN_REVIEW`. UNKNOWN args → defer to Maven.
- **Tests** (`tests/test_generated_test_preflight.py`, +5): both shapes flag;
  single-reference-overload null, all-primitive, all-boxed, and UNKNOWN-arg calls
  do **not** flag. Full suite **193 passed, 4 skipped**.
- **Offline replay over `var/benchmark/v3_2_3-pro-10case` (zero model cost):**
  caught the 2 overload-ambiguity compile failures — BooleanUtils `toBoolean(null)`
  and NumberUtils `toDouble(null,…)`, both `ambiguous_null_overload_call`;
  **over-rejection = NONE** (no compiled PASS/TEST_FAILURE flagged), and the 3
  other-bucket compile failures (Option import, Options generics, CSVRecord
  instance-arg) were correctly **not** claimed. Precision 100% on this run.

**Boundary held:** deterministic, lexical-only (never type inference), conservative,
no repair, no oracle rewrite, no coverage, no model run.

### 7.1 Correction (2026-06-07) — false-positive fix + broad replay

A manual review found the first cut **over-rejected two *compilable* calls** (it
would have skipped Maven on valid code):
- Shape B flagged `T.f(Integer.valueOf(1), 2)` with `f(int,int)` / `f(String,String)`
  — Java binds `f(int,int)`; `String` is not the wrapper of `int`.
- Shape A flagged `T.f(null, 1)` with `f(String,int)` / `f(Integer,String)` — the
  `1` excludes `f(Integer,String)`, so Java binds `f(String,int)`.

Root cause: the applicability filter only excluded null→primitive and treated all
other args as possibly-applicable — inconsistent with "only when certain / UNKNOWN
defers to Maven". Tightened:
- **Shape A** now flags only when ≥2 overloads are identical at every *other*
  position and differ solely by the reference type at the null position, AND each
  other position is a primitive the call's arg confirmedly fits; otherwise defer.
- **Shape B** now requires the reference overload to be the *exact wrapper family*
  of an all-primitive overload (`f(int,int)` ↔ `f(Integer,Integer)`); a non-wrapper
  reference overload, or any UNKNOWN/NULL arg, defers.

Both counterexamples are pinned as regression tests.

**Broad historical replay (28 runs, 80 generated tests, zero model cost):**
**over-rejection = 0** — no compiled test flagged anywhere — while the detector
still caught **7** real overload-ambiguity compile failures across 5 runs
(BooleanUtils + NumberUtils; both Shape A null and Shape B boxed/primitive). Full
suite **195 passed**.

**Still deferred:** generics-assignment and instance-receiver detection (out of
scope by design); a durable `scripts/` replay tool (the broad replay above was a
one-off temp script).
