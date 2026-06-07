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

> Status: parked pending the v3.2.3 10-case result. No code until the data picks
> BUILD vs SHELVE.
