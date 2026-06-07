# Context v3 Pro 10-Case Review

> Date: 2026-06-07. Scope: `benchmarks/manifest.v1.json` full 10-case
> run with Context v3 + `deepseek-v4-pro`. Repair disabled. Coverage skipped.
> No oracle auto-fix.

---

## 1. Run

Output directory: `var/benchmark/v3-pro-10case`

Command shape:

```powershell
$env:TESTAGENT_LLM_PROVIDER='openai'
$env:TESTAGENT_LLM_MODEL='deepseek-v4-pro'
$env:TESTAGENT_LLM_TIMEOUT_SECONDS='300'
$env:TESTAGENT_REPAIR_COMPILE_FAILURES='false'
$env:TESTAGENT_MVN_EXTRA_ARGS='-Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dlicense.skip=true -Denforcer.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dpmd.skip=true -Djacoco.skip=true'
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks\manifest.v1.json --out var\benchmark\v3-pro-10case
```

Local pinned mirrors from `var/benchmark/manifest-dryrun/mirrors` were reused to
avoid GitHub network noise. This run reached all 10 cases.

---

## 2. Aggregate

| Metric | Result |
|---|---:|
| total cases | 10 |
| buildable repos | 4 |
| generation attempted | 10 |
| setup / clone / repo build failures | 0 / 0 / 0 |
| compile pass rate | 60% |
| generated-test pass rate | 20% |
| quality gate pass rate | 20% |
| quality gate failures | 5 |
| need human review rate | 100% |
| coverage measured | 0/10 |
| top failure types | `{'TEST_FAILURE': 4, 'COMPILE_FAILURE': 3, 'PIPELINE_FAILED': 1}` |
| recommendation distribution | `{'REJECT_CANDIDATE': 5, 'NEEDS_REVISION': 3, 'STRONG_REVIEW_CANDIDATE': 2}` |

Result: the 10-case run is useful but not yet a high-pass benchmark. It exposes
the next bottlenecks clearly.

---

## 3. Per-Case

| Case | Outcome | Quality | Recommendation | Root cause |
|---|---|---|---|---|
| commons-cli `Option` | `TEST_FAILURE` | `REVIEW` | `NEEDS_REVISION` | `getValue()` / `getValues()` no-value behavior still guessed from contract/Javadoc; actual `getValues()` can return `null`. |
| commons-cli `Options` | `COMPILE_FAILURE` | `FAIL` | `REJECT_CANDIDATE` | Generic wildcard mismatch: `List<?>` not assignable to `List<Option>`. |
| commons-cli `CommandLine` | `PASS` | `PASS` | `STRONG_REVIEW_CANDIDATE` | Strong candidate. |
| commons-csv `CSVRecord` | `TEST_FAILURE` | `REVIEW` | `NEEDS_REVISION` | Negative index expected `IllegalArgumentException`, actual `ArrayIndexOutOfBoundsException`. |
| commons-csv `CSVFormat` | `TEST_FAILURE` | `REVIEW` | `NEEDS_REVISION` | Expected `withRecordSeparator("invalid")` to throw; actual does not. |
| commons-text `WordUtils` | `TEST_FAILURE` | `FAIL` | `REJECT_CANDIDATE` | Uses reflection/private-constructor pattern and fails constructor assertion. |
| commons-text `StringEscapeUtils` | `PASS` | `PASS` | `STRONG_REVIEW_CANDIDATE` | Strong candidate. |
| commons-lang3 `NumberUtils` | `COMPILE_FAILURE` | `FAIL` | `REJECT_CANDIDATE` | Ambiguous overload: `toDouble(null, default)` matches `BigDecimal` and `String`. |
| commons-lang3 `Validate` | `PIPELINE_FAILED` | `FAIL` | `REJECT_CANDIDATE` | Model output was not valid JSON. |
| commons-lang3 `BooleanUtils` | `COMPILE_FAILURE` | `FAIL` | `REJECT_CANDIDATE` | Ambiguous overloads / varargs: primitive vs boxed boolean arrays (`and`, `or`, `xor`, `oneHot`) and `toBoolean(null)`. |

---

## 4. Failure Taxonomy

### 4.1 Compile Failures: Deterministic But Not Yet Fixed

The 3 compile failures are good future candidates for **compile-only** repair or
prompt hardening, but this review does not start Phase 3.

- `Options`: generic wildcard mismatch.
- `NumberUtils`: overloaded method ambiguity with `null`.
- `BooleanUtils`: overloaded primitive/boxed varargs ambiguity.

Design implication: Context v3 grounded method contracts, but not overload
resolution. The next prompt/context improvement could require explicit casts or
typed arrays for overloaded methods, especially when passing `null` or varargs.

### 4.2 Test Failures: Still Oracle/API Semantics

The 4 test failures are not compile repair problems.

- `Option`: Javadoc/API contract can conflict with implementation; no-value
  `getValues()` returned `null` despite contract language suggesting an empty
  array.
- `CSVRecord`: negative index exception still differs from generated oracle.
- `CSVFormat`: generated invalid-record-separator oracle is too aggressive.
- `WordUtils`: reflection/private constructor case is not a useful generated
  test and quality gate correctly rejects it.

These should remain `NEEDS_REVISION` or `REJECT_CANDIDATE`; do not rewrite
expected values automatically.

### 4.3 Pipeline Failure

`Validate` failed before execution because the model output was not valid JSON.
This should be tracked separately from generation quality. A future bounded
retry for invalid JSON may be reasonable, but it is not Phase 3 oracle repair.

---

## 5. Comparison With 3-Case Result

The frozen 3-case bodyfix run (`docs/25`) was:

- compile pass rate 100%
- generated-test pass rate 67%
- quality gate pass rate 67%
- `CSVRecord` and `WordUtils` strong candidates

The 10-case run was:

- compile pass rate 60%
- generated-test pass rate 20%
- quality gate pass rate 20%

Interpretation:

1. Context v3 works on some contract-heavy cases, but does not generalize enough
   across overload-heavy and state-heavy APIs.
2. Model nondeterminism is visible: `CSVRecord` and `WordUtils` passed in the
   3-case run but failed in the 10-case run.
3. The benchmark is now doing useful work: it reveals distinct failure buckets
   instead of only showing demo success.

---

## 6. Decision

Do **not** move directly into broad Phase 3 repair.

Recommended next step is a narrow **Context v3.1 / prompt hardening** pass:

1. Overload disambiguation rule:
   - never call overloaded methods with bare `null`;
   - use explicit casts for `null` arguments when the target overload is known;
   - use explicitly typed arrays for primitive/boxed varargs.
2. Constructor/state grounding:
   - for stateful APIs, do not infer field defaults from constants alone;
   - prefer neighbor-test examples or selected constructor body evidence.
3. Reflection/private API rule:
   - do not use reflection or private constructors just because neighbor tests
     do; only use public observable APIs unless the target is explicitly a
     constructor behavior test.
4. Invalid JSON retry policy:
   - optionally add a bounded provider retry for invalid JSON, separate from
     compile repair and oracle repair.

Only after Context v3.1 should compile-only Phase 3 repair be reconsidered.
The compile failures here are mechanically fixable, but the stronger project
move is to prevent obvious overload ambiguity at generation time first.

---

## 7. What Not To Do

- Do not auto-fix `TEST_FAILURE` by changing expected values.
- Do not start oracle repair.
- Do not restore coverage yet; this run did not test coverage.
- Do not treat the 20% pass rate as a final model quality number; n=10 with one
  sample per case is still small and nondeterministic.
- Do not expand beyond 10 cases until overload/state/reflection rules are
  tightened.

---

## 8. Evidence Files

- `var/benchmark/v3-pro-10case/report.json`
- `var/benchmark/v3-pro-10case/report.md`
- `var/benchmark/v3-pro-10case/bench.db`
- Generated tests and Maven logs under `var/benchmark/v3-pro-10case/ws/*`
- Baseline 3-case comparison: `docs/21`, `docs/25`
