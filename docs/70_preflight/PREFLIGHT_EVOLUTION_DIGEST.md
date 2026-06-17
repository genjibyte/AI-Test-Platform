# Generated-Test Preflight — Evolution Digest (consolidated)

> **Consolidates** the four preflight docs `32,33,34,36` (2026-06-07) into one digest.
> Originals removed; full text recoverable via git history. The preflight is **live
> code** (`app/quality/generated_test_preflight.py`), not just a design. It is a
> **deterministic triage gate**, never repair: on a block it skips Maven, records
> `COMPILE_FAILURE` + `build_outcome=PREFLIGHT_REJECT`, and `conclusion` stays
> `NEED_HUMAN_REVIEW`. No LLM, no edit, no oracle rewrite, no production-code change.

## 0. Why it exists
The Context-v3.x arc proved **prompt compliance is unreliable for compiler-enforced
overload edge cases** (see `../60_context_v3/CONTEXT_V3_EVOLUTION_DIGEST.md` §3.2). A
deterministic, pre-Maven check of generated calls against the *rendered method list* is
the prompt-independent backstop.

## 1. What the gate checks (docs/32)
Runs after the LLM returns `test_source`, before writing the file / running Maven.
Scope is deliberately narrow — **class-qualified calls to the target class only** (e.g.
`BooleanUtils.and(...)`); it does **not** infer local-variable receiver types or act as a
Java type checker. It blocks:
- calls to target methods **not in** the rendered method list;
- calls to target **overload arities not in** the list;
- individual-value calls to primitive/boxed **varargs** overload pairs (`and(true,true)` →
  needs one typed array).
Post-audit fix: the varargs blocker fires only when **no fixed-arity overload matches** the
call arity (JLS 15.12.2 binds fixed-arity before varargs) — bias toward "defer to Maven".

## 2. Offline replay audit (docs/33) — the key safety result
Replayed the gate over generated tests already in `var/benchmark/*/bench.db`, comparing to
each job's recorded Maven outcome (zero model cost):
| metric | combined (24 jobs) |
|---|---:|
| preflight FAIL | 4 |
| **over-reject candidates** | **0** |
| preflight↔compile agreement | 4 |
| narrow-gate missed compile failures | 3 |
**Zero over-rejection** is the load-bearing result: since a block skips Maven, blocking a
historically-compilable test is the dangerous error — it never happened. The 3 misses
(generics `List<?>`→`List<Option>`, `null`-overload ambiguity, instance-receiver
`record.putInMap`) are **out-of-scope by design**, not over-rejection.

## 3. Live validation (docs/34)
One live `BooleanUtils` pro run: preflight **PASS** (the model did *not* repeat the unlisted
`toBooleanObject(int,int,int)` nor `and(true,true)`), so the gate correctly deferred to
Maven — which then caught a `toBoolean(null)` ambiguity (outside the gate's then-scope).
Validated the **non-reject path**: no over-reject, Maven ran normally.

## 4. Overload-ambiguity extension (docs/36) — designed, then implemented + validated
Two recurring shapes the v3.2.x prompts kept chasing:
- **Shape A — bare-null overload**: `toBoolean(null)` ambiguous across same-arity reference
  overloads.
- **Shape B — mixed boxed/primitive**: `toBoolean(Integer.valueOf(3),1,2)` ambiguous across
  an all-primitive vs all-boxed (exact wrapper) family.
Mechanism: **lexical arg classification only** (`NULL`/`PRIMITIVE_LITERAL`/`BOXED_LITERAL`/
`UNKNOWN`) against already-parsed signatures — never type inference. **Conservative: any
`UNKNOWN` in a deciding position → PASS (defer to Maven).** Blocker codes
`ambiguous_null_overload_call` / `ambiguous_boxed_primitive_overload_call`.
- **Status: IMPLEMENTED + VALIDATED** (greenlit "允许最小实现"). A first cut over-rejected
  two *compilable* calls; the applicability filter was tightened (Shape A requires all other
  positions identical + confirmed-fitting; Shape B requires the exact wrapper family) and
  both counterexamples pinned as regression tests.
- **Broad historical replay (28 runs, 80 generated tests, zero model cost): over-rejection
  = 0**, while catching **7** real overload-ambiguity compile failures across 5 runs
  (BooleanUtils + NumberUtils, both shapes). Full suite 195 passed at the time.

## 5. Durable lessons
1. **Deterministic gate > nondeterministic prompt** for compiler-enforced classes — but
   only as a *triage/backstop*, since it skips Maven.
2. **Conservatism is the safety contract:** over-rejection (skipping Maven on compilable
   code) is the costly error; `UNKNOWN → defer to Maven` keeps over-reject at 0 across all
   replays. The reverse miss is safe (Maven still catches it).
3. **Offline replay over `bench.db` is the noise-robust BUILD/SHELVE decision tool** —
   dozens of samples, zero model cost; do it before wiring any new detector into the pipeline.
4. **Still out-of-scope by design:** generics-assignment checks, instance-receiver type
   inference, inherited static methods — these need real type analysis, not lexical heuristics.

## 6. Boundary (held throughout)
Deterministic, lexical-only, conservative; no repair, no oracle rewrite, no coverage, no
model call, no production-code edit; `conclusion` stays `NEED_HUMAN_REVIEW`.
