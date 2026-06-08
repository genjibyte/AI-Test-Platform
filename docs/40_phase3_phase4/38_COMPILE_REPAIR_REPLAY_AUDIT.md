# Compile-Only Repair — Offline Replay Audit

> Date: 2026-06-07. **Audit only.** No model, no new benchmark, no bucket
> expansion, no code change. Replays the existing deterministic
> `app/repair/compile_repair.py` over every `COMPILE_FAILURE` generated test in
> the historical `var/benchmark/*/bench.db` (compile logs read from each run's
> `ws/`). Question: what does repair change, would it still need Maven, can it
> touch the oracle?

## 0. What the repair is

`repair_compile_failure(source, compile_log, java_source_level)` is **deterministic
(no LLM)** and does exactly three things:
1. `missing_static_import` — add `import static …Assertions.<name>;` for each JUnit
   assertion called (inserts import lines only);
2. `java_source_level` — on Java ≤ 8, global `source.replace("List.of(", "Arrays.asList(")` + add `import java.util.Arrays;`;
3. `method_local_type` — hoist a method-local `enum {…}` to a `private enum` at test-class scope.

## 1. Sample

**23 `COMPILE_FAILURE` generated tests** across all bench.db (0 were
preflight-rejected — all are real `javac` failures with logs).

| repair outcome | count |
|---|---:|
| **changed** | 9 |
| unchanged | 14 |

Change buckets: `missing_static_import` ×8, `method_local_type` ×2, `java_source_level` ×2.
Actual error classes (from logs): `cannot_find_symbol` ×8, `overload_ambiguous` ×8,
`incompatible_types` ×2, `no_suitable_method` ×1, other ×4.

## 2. Q1 — Which samples can the current repair change?

**9 of 23 (39%).** Repair only touches its three buckets:
- **8** add a missing JUnit static import (the recurring `cannot_find_symbol` for
  `assertNotEquals`/`assertX`, e.g. `v3_2_3-pro-10case Option`).
- **2** hoist a method-local enum.
- **2** rewrite `List.of(` → `Arrays.asList(`.

The **14 unchanged** are out of repair scope — and they are the *dominant* buckets:
all 8 `overload_ambiguous` (now the preflight's job, docs/36), the 2
`incompatible_types` (generics wildcard), and the instance-receiver `no_suitable_method`.
So compile-only repair, as built, addresses a **narrow minority** of real compile
failures (imports/enums/List.of), not the majority.

## 3. Q2 — Which still need Maven after the change?

**All of them — by design, and that is correct.** The repair runs in a bounded
loop that **re-runs Maven after every round**; it never declares a test compiled.
Concretely:
- **8** changed cases where the repair bucket matches the actual error → *may* now
  compile, but Maven must confirm (the repair cannot prove compilation);
- **1** changed case (`deepseek-pro-rerun Option`) where the change (added import)
  does **not** address the real error (`no_suitable_method`) → **will still fail Maven**;
- **14** unchanged cases → unchanged → still fail Maven.

So repair is best-effort; **Maven stays the compile verifier** (judge-first, docs/07 A2).
No repaired test is ever trusted as "fixed" without re-compilation.

## 4. Q3 — Can it touch the oracle? **YES — confirmed on 2/23.**

The `List.of(` → `Arrays.asList(` global replace (the `java_source_level` bucket)
**modified assertion expected values** in two historical samples:

| sample | rewritten assertion |
|---|---|
| `smoke Option` | `assertEquals(List.of("v1"), opt.getValuesList());` → `Arrays.asList("v1")` |
| `v2-flash CSVRecord` | `assertEquals(List.of("1","2","3"), list);` → `Arrays.asList(...)` (×2) |

Characterisation:
- It does **not** change `expected`→`actual`, does **not** delete or weaken any
  assertion, and `List.of(x)`/`Arrays.asList(x)` are `.equals`-equal as lists, so
  the oracle's *meaning* is preserved in these two cases.
- **But** it is a **textual rewrite of an expected-value expression inside an
  assertion**, which crosses the spirit of "never touch the oracle" (docs/07 A5).
  It is **not guaranteed** semantics-preserving in edge cases: `List.of` rejects
  null elements and is immutable; `Arrays.asList` permits nulls and is
  fixed-size-mutable — so a test asserting null-rejection or immutability would
  change meaning. And it fires whenever `List.of(` is present on Java 8, even when
  `List.of` is incidental to the primary error.
- The other two buckets are **oracle-safe**: `missing_static_import` only inserts
  import lines; `method_local_type` only moves helper enums. (Verified: every
  oracle-touch came from the `java_source_level` bucket, never the other two.)

## 5. Conclusions

1. Repair is **deterministic, model-free** — judge-first preserved; Maven always re-verifies.
2. **2 of 3 buckets are oracle-safe and useful** (`missing_static_import`,
   `method_local_type`) — the import bucket plausibly fixes the recurring
   missing-assertion-import compile failures.
3. **1 bucket (`List.of`→`Arrays.asList`) can modify oracle/expected-value text** —
   a real red-line risk, benign in the 2 observed cases but not guaranteed safe.
4. Repair scope is **narrow**: it does not address the dominant compile buckets
   (overload-ambiguity → preflight; generics, arg-type, no-suitable-method →
   nothing). Compile-only repair alone would not move the compile rate much.

## 6. Recommendation (for a future decision — NOT acted on here)

If/when compile-only repair is enabled:
- **keep** `missing_static_import` and `method_local_type` (oracle-safe, useful);
- **drop or guard** the `List.of`→`Arrays.asList` replace so it never rewrites text
  inside an assertion argument (e.g. skip when `List.of(` sits within an
  `assert…(`/`fail(` call), keeping repair strictly oracle-free;
- keep Maven as the verifier; never trust a repaired test without re-compilation.

## 7. Fix applied (2026-06-07, follow-up)

The audit (§0–§6) changed nothing. As a follow-up, §6 was implemented as a minimal
hardening of `app/repair/compile_repair.py` (repair stays gated off in benchmark
runs; this makes it oracle-safe for future enablement):

- **`missing_static_import` is now compile-log triggered** — a JUnit static import
  is added only for an assertion the compiler actually flagged missing (`找不到符号`
  / `cannot find symbol`, both locales); no log → source-scan fallback. Kills
  spurious imports (e.g. the `deepseek-pro-rerun Option` no-suitable-method case).
- **`List.of` span guard (first pass)** — `List.of(`→`Arrays.asList(` skipped any
  `List.of` inside an `assert…(`/`fail(` paren span.
- Not added: generics / receiver-type / overload-cast repair (out of scope).

### 7.1 Correction — the first pass over-claimed (2026-06-08)

The §7 first-pass conclusion ("oracle-touch = 0 … strictly oracle-free") was
**overstated**: the span guard only protects `List.of` inside the *first* paren of an
`assert…(` call. It does **not** cover an oracle whose expected value sits *outside*
that span — e.g. a fluent chain `assertThat(x).isEqualTo(List.of(…))`, or a
non-`assert*` matcher DSL `then(x).isEqualTo(List.of(…))`. Those would still be
rewritten. "0" was true *on this corpus*, not true *by construction*.

**Hardening (stable-point fix).** The `List.of` rewrite is now **confined to
local-variable initializer position** (`… = List.of(…)`), in addition to the span
guard. Oracle expected values are arguments *inside* a matcher call, never a
`= List.of` initializer — so the rewrite cannot reach oracle text **by construction,
independent of the assertion's name** (`_is_initializer_position` in
`app/repair/compile_repair.py`). Everything else (matcher args, `return List.of`,
call args) is left as a compile error for human review.

**Re-validation (offline replay, all `bench.db`, Java 8 forced = worst case for
`List.of` rewriting, zero model cost):**

| metric | value |
|---|---:|
| `COMPILE_FAILURE` samples | 23 |
| samples with any `List.of(` | 2 |
| samples with `List.of` **inside an assertion** (oracle-risk population) | 2 |
| in-assertion `List.of` **rewritten** (oracle-touch) | **0** |
| `java_source_level` (List.of) patches fired | **0** |
| initializer-position `List.of` in corpus | 0 |

So the `List.of` bucket is **dormant across the whole historical corpus** — both
`List.of` instances are oracle arguments (now structurally skipped) and there are
zero `= List.of` initializers to rewrite. It currently fixes *nothing* in practice;
it exists only as forward-looking, oracle-safe-by-construction handling. The
`missing_static_import` bucket still fixes the real `assertNotEquals`-not-imported
case. Full suite **201 passed, 4 skipped** (+2 regression tests: fluent chain,
non-`assert*` DSL).

**Honest residual (not eliminated).** `List.of` vs `Arrays.asList` differ in
mutability and null-handling. A `= List.of` *initializer* whose value is later
asserted for *value equality* is verdict-preserving (`AbstractList.equals` is
element-wise). The one case that can still change meaning: a test asserting the
*immutability/null-rejection of the list object itself* (testing JDK `List.of`, not
the SUT) — rare, and mitigated by the standing controls: Maven re-verifies every
repaired test and the conclusion stays `NEED_HUMAN_REVIEW` (`trusted=False`), so a
human sees it. The bucket is deliberately conservative (over-skips rather than risk
oracle text). This is the **pre-enablement stable point**; repair remains gated off
(`repair_compile_failures=False`). Enablement itself is designed separately in
**docs/39**.

> Boundaries held throughout: no model run, no new benchmark, no bucket expansion.
