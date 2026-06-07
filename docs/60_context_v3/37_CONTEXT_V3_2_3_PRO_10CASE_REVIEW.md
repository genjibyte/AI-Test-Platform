# Context v3.2.3 + Preflight Pro 10-Case Review

> Date: 2026-06-07. Scope: results audit only. **Ends with a BUILD / SHELVE /
> DEFER recommendation for `docs/36` (the preflight overload-ambiguity extension)
> and implements nothing.** No Phase 3 repair, no oracle auto-fix, no coverage,
> no `app/` change in this doc.

Run: `var/benchmark/v3_2_3-pro-10case` · model `deepseek-v4-pro` · repair OFF ·
coverage skipped · preflight ON · pinned mirrors reused · 10/10 generated.

---

## 1. Aggregate + trend (vs v3 / v3.1)

| Metric | v3 (`docs/26`) | v3.1 (`docs/28`) | **v3.2.3 (this run)** |
|---|---:|---:|---:|
| compile pass rate | 60% | **80%** | **50%** |
| generated-test pass rate | 20% | 30% | 20% |
| quality PASS / REVIEW / FAIL | — | — | 1 / 4 / 5 |
| recommendation dist | R5 / NR3 / S2 | R3 / NR4 / S3 | **R5 / NR3 / S1 / REV1** |
| top failure types | TEST4 COMP3 PIPE1 | TEST4 COMP2 NOTESTS1 | **COMP5 TEST3** |
| need_human_review | 100% | 100% | **100%** |

> **Headline caveat — read before interpreting anything below: v3.2.3 *regressed*
> against v3.1 (compile 50% vs 80%, strong 1 vs 3) on n=10 with one sample per
> case.** Model output is nondeterministic; docs/26 §5 already saw cases flip
> between runs. So this is **not** evidence that the v3.2/v3.2.x prompt hardening
> made things worse — it is evidence that **a single 10-case run is too noisy to
> rank prompt versions.** Treat the numbers as *failure-class discovery*, not a
> quality score.

Notably, compile failures went 3 → 2 → **5** while the overload-rule count grew.
That is at least noise; at most a hint that **prompt-rule bloat has hit
diminishing (possibly negative) returns**. Either reading argues against piling on
more prompt rules.

---

## 2. Per-case

| Case | outcome | quality | rec | conclusion | root cause |
|---|---|---|---|---|---|
| commons-cli Option | COMPILE_FAILURE | FAIL | REJECT | NEED_HUMAN_REVIEW | `assertNotEquals` used without static import |
| commons-cli Options | COMPILE_FAILURE | FAIL | REJECT | NEED_HUMAN_REVIEW | generics: `List<?>` → `List<Option>` |
| commons-cli CommandLine | TEST_FAILURE | REVIEW | NEEDS_REVISION | NEED_HUMAN_REVIEW | oracle/semantic |
| commons-csv CSVRecord | COMPILE_FAILURE | FAIL | REJECT | NEED_HUMAN_REVIEW | `record.get(TestEnum.values())` arg-type (instance receiver) |
| commons-csv CSVFormat | TEST_FAILURE | REVIEW | NEEDS_REVISION | NEED_HUMAN_REVIEW | oracle/semantic |
| commons-text WordUtils | PASS | PASS | STRONG_REVIEW | NEED_HUMAN_REVIEW | — |
| commons-text StringEscapeUtils | PASS | REVIEW | REVIEW_CANDIDATE | NEED_HUMAN_REVIEW | passes; a quality warning keeps it REVIEW |
| commons-lang3 NumberUtils | COMPILE_FAILURE | FAIL | REJECT | NEED_HUMAN_REVIEW | `toDouble(...)` overload ambiguous |
| commons-lang3 Validate | TEST_FAILURE | REVIEW | NEEDS_REVISION | NEED_HUMAN_REVIEW | oracle/semantic |
| commons-lang3 BooleanUtils | COMPILE_FAILURE | FAIL | REJECT | NEED_HUMAN_REVIEW | `toBoolean(null)` overload ambiguous |

---

## 3. Compile-failure taxonomy (decisive for docs/36)

| Case | javac error | bucket | in `docs/36` scope? |
|---|---|---|---|
| BooleanUtils | `toBoolean(null)` 引用不明确 | **bare-null overload (Shape A)** | **YES** |
| NumberUtils | `toDouble(...)` 引用不明确 | **overload ambiguity** | **YES** |
| Option | `assertNotEquals` cannot find symbol | static-import (v2 bucket) | no |
| CSVRecord | `record.get(TestEnum.values())` no method | arg-type on **instance receiver** | no |
| Options | `List<?>` → `List<Option>` | generics wildcard | no (explicitly excluded) |

**Overload-ambiguity = 2 distinct cases (BooleanUtils + NumberUtils).** The other
three compile failures are *different* buckets (import, instance-arg-type,
generics) that `docs/36` does not address.

**The most important single fact:** BooleanUtils emitted `toBoolean(null)` here —
the exact form **v3.2.2 forbids** and that the model *avoided* in the docs/35
single-case run. It complied once, regressed now. This is concrete proof that
**prompt compliance is nondeterministic and cannot be relied on for
compiler-enforced overload edge cases** (the docs/31 §7 thesis), which is the core
argument for a deterministic gate.

---

## 4. Preflight live behavior

Every compile failure recorded `build=None` — i.e. **the preflight rejected none
of them; all reached real `javac`.** Expected: its current contract checks
unlisted target method/arity + the ambiguous-varargs pair, none of which match
these five (bare-null/scalar-overload ambiguity, generics, instance-arg,
missing-import). **No over-rejection** (0 false `PREFLIGHT_REJECT`), consistent
with `docs/33`. So `docs/36` would have caught 2 of the 5 deterministically,
pre-Maven; the gate is currently silent on exactly the recurring overload class.

---

## 5. Red-line invariants (all held)

- All 10 conclusions `NEED_HUMAN_REVIEW`. No auto-accept, no oracle rewrite; the 3
  TEST_FAILUREs stay `NEEDS_REVISION`.
- Preflight: no over-reject.
- **Minor follow-up (not fixed here):** `review_summary.failures` came back empty
  for the 3 TEST_FAILUREs, so the reviewer-facing expected/actual was not
  surfaced for them — likely a `@Nested`/surefire-classname mismatch in
  `_failure_views`. Worth a separate look; out of scope for this audit.

---

## 6. Recommendation on docs/36 — **DEFER (leaning BUILD)**

The pre-registered BUILD gate ("overload-ambiguity in ≥2 distinct cases") **is
met** (BooleanUtils + NumberUtils), and the `toBoolean(null)` regression is a
textbook case for a deterministic gate. So the long-run answer is probably BUILD.

But I recommend **DEFER, not BUILD-now**, for two reasons:

1. **One noisy run.** This run regressed vs v3.1; nondeterminism dominates n=10.
   Standing up new gate code off a single noisy sample is premature — the "2
   overload cases" could be 0 or 4 next run.
2. **`docs/36` is detection-only.** It improves gate coverage and skips Maven, but
   does **not** lift compile/pass rate, and it touches only 2 of the 5 (diverse)
   compile shapes. The other three (import, instance-arg, generics) stay.

**The DEFER unblock is also the careful BUILD path (when you greenlight):**
implement the `docs/36` detector → **offline-replay it across every historical
`var/benchmark/*/bench.db` generated test** (dozens of samples, zero model cost,
like `docs/33`) to confirm (a) overload-ambiguity is genuinely frequent and (b)
**zero over-rejection** → only then wire it into the pipeline. That offline replay
is the noise-robust BUILD/SHELVE decision — but it requires the detector code, so
it stays gated on your explicit go-ahead.

> Not SHELVE: the failure class is real, recurring, and prompt-resistant — leaving
> it to nondeterministic prompt compliance is the weakest option.

---

## 7. Bigger picture (separate decision, not this turn)

- **Single 10-case is too noisy to rank versions.** For a stable claim, either run
  multiple samples per case (raises cost) or use the benchmark only for
  failure-*class* discovery (which it does well).
- **Prompt hardening has plateaued.** The five compile failures are diverse;
  neither more prompt rules nor `docs/36` alone will lift compile rate. The lever
  that actually *fixes* compile failures is the charter-sanctioned **narrow
  compile-only repair** (feed the `javac` error back, regenerate only the failing
  generated test, never touch the oracle). That is a distinct strategic decision
  for a later turn — flagged, not recommended here.

---

## 8. Do not do

- Do not implement `docs/36` in response to this audit (DEFER).
- Do not auto-fix oracle / rewrite expected values.
- Do not restore coverage; do not start Phase 3 repair without an explicit decision.
- Do not read 50% / 20% as a stable quality number — n=10, nondeterministic.
