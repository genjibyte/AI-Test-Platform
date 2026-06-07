# Context v3.2 4-Case Pro Validation Review

> Date: 2026-06-07. Scope: targeted validation only. No Phase 3 repair, no
> coverage restoration, no oracle auto-fix, no expected-to-actual rewrite.

## 1. Run Scope

Run output:

- `var/benchmark/v3_2-pro-4case/report.json`
- `var/benchmark/v3_2-pro-4case/report.md`
- `var/benchmark/v3_2-pro-4case/bench.db`

Model:

- provider: `openai`
- model: `deepseek-v4-pro`

Cases selected from the v3.2 acceptance risks in `docs/29_CONTEXT_V3_2_HARDENING.md`:

| Case | Why selected |
|---|---|
| `commons-csv CSVRecord` | API grounding regression target: previous generated test called an unlisted method. |
| `commons-text StringEscapeUtils` | Oracle regression sentinel: exact escaping/entity outputs should not be guessed. |
| `commons-lang3 Validate` | JUnit structure regression target: generated tests should avoid `@Nested` false `NO_TESTS`. |
| `commons-lang3 BooleanUtils` | Java overload/varargs regression target: primitive and boxed overloads require typed arrays/casts. |

One local setup issue occurred before the real run: the temporary spec was first
written with a UTF-8 BOM, causing `JSONDecodeError`. The spec was rewritten
without BOM before the successful run. No benchmark conclusion depends on that
failed setup attempt.

## 2. Aggregate Result

From `var/benchmark/v3_2-pro-4case/report.json`:

| Metric | Value |
|---|---:|
| total cases | 4 |
| buildable repos | 3 |
| setup / clone / repo build failures | 0 / 0 / 0 |
| generation attempted | 4 |
| compile pass rate | 75% |
| generated test pass rate | 50% |
| quality gate pass rate | 50% |
| quality gate reviews | 1 |
| quality gate failures | 1 |
| recommendation distribution | 2 strong review, 1 needs revision, 1 reject |

Per case:

| Case | Outcome | Quality | Recommendation |
|---|---|---|---|
| `CSVRecord` | `TEST_FAILURE` | `REVIEW` | `NEEDS_REVISION` |
| `StringEscapeUtils` | `PASS` | `PASS` | `STRONG_REVIEW_CANDIDATE` |
| `Validate` | `PASS` | `PASS` | `STRONG_REVIEW_CANDIDATE` |
| `BooleanUtils` | `COMPILE_FAILURE` | `FAIL` | `REJECT_CANDIDATE` |

## 3. Acceptance Check Against docs/29

`docs/29_CONTEXT_V3_2_HARDENING.md` defines the targeted validation acceptance:

- `BooleanUtils` compiles with typed varargs / cast null.
- `Validate` reports real test counts and avoids `@Nested`.
- `CSVRecord` does not call an unlisted method.
- The sentinel does not regress to a guessed oracle.
- Genuine oracle/doc-conflict cases surface as `NEEDS_REVISION`, not automatic fixes.

Status:

| Acceptance item | Status | Evidence |
|---|---|---|
| `BooleanUtils` compiles | **Not met** | `var/benchmark/v3_2-pro-4case/ws/6f59718258124b65a12d5d952d76641f/logs/mvn-test-jacoco.log` reports ambiguous calls for `and`, `or`, `xor`, and `oneHot`. |
| `Validate` reports real tests | **Met** | `report.json` marks `Validate` as `PASS` / quality `PASS`; its Maven log reports a green run. |
| `CSVRecord` avoids unlisted method compile failure | **Mostly met** | It now compiles. The previous `putInMap(...)` missing-symbol class of failure is gone. |
| Sentinel avoids guessed string/entity oracle regression | **Met** | `StringEscapeUtilsAiGeneratedTest` runs 19 tests with 0 failures. |
| Oracle/doc-conflict stays reviewable | **Met** | `CSVRecord` is `TEST_FAILURE`, quality `REVIEW`, recommendation `NEEDS_REVISION`; no oracle repair was applied. |

Conclusion: v3.2 partially passes the targeted validation, but it does **not**
meet the full acceptance bar because `BooleanUtils` still fails compilation.

## 4. Case Findings

### 4.1 CSVRecord

Result:

- `gen_outcome`: `TEST_FAILURE`
- compiled: true
- executed: true
- quality: `REVIEW`

Important nuance: this case is not a clean whole-repo signal because the
commons-csv baseline also has existing test failures in this workspace. However,
the generated test itself has clear failures, so the oracle conclusion still
stands.

Generated-test failures from
`var/benchmark/v3_2-pro-4case/ws/4519179ffbbd4cd089747a7b7e64dd6b/logs/mvn-test-jacoco.log`:

- `testGetWithEnum`: expected `1`, actual `A`.
- `testIsSetInt`: expected `false`, actual `true`.
- `testGetStringInconsistentRecord`: expected `IllegalArgumentException`, but nothing was thrown.
- `testIsSetString`: expected `false`, actual `true`.
- `testGetWithNullEnum`: expected `NullPointerException`, actual `IllegalArgumentException`.

Interpretation:

- v3.2 improved API grounding enough to avoid the previous compile failure.
- The remaining failure is semantic/oracle grounding, not a syntax or missing API problem.
- This must not be solved by expected-to-actual rewriting. It needs better
  evidence selection or human review.

### 4.2 StringEscapeUtils

Result:

- `gen_outcome`: `PASS`
- quality: `PASS`
- recommendation: `STRONG_REVIEW_CANDIDATE`

Evidence:

- `var/benchmark/v3_2-pro-4case/ws/fca39657051e400aa5d8a98ddff40210/logs/mvn-test-jacoco.log`
  reports `StringEscapeUtilsAiGeneratedTest`: 19 tests, 0 failures.

Interpretation:

- The v3.2 "do not guess exact string/entity outputs unless grounded" rule did
  not regress on this sentinel.
- This is a useful positive signal, but still needs human review because passing
  generated tests are review candidates, not auto-accepted assets.

### 4.3 Validate

Result:

- `gen_outcome`: `PASS`
- quality: `PASS`
- recommendation: `STRONG_REVIEW_CANDIDATE`

Evidence:

- `var/benchmark/v3_2-pro-4case/report.json` marks the case `PASS`.
- The Maven log for workspace
  `var/benchmark/v3_2-pro-4case/ws/1330ef7e95f64412bd4c821c483e2430/` is green.

Interpretation:

- The prompt-forbid route for `@Nested` is effective in this targeted case.
- No harness aggregation change is needed yet.

### 4.4 BooleanUtils

Result:

- `gen_outcome`: `COMPILE_FAILURE`
- quality: `FAIL`
- recommendation: `REJECT_CANDIDATE`

Evidence:

- Generated test:
  `var/benchmark/v3_2-pro-4case/ws/6f59718258124b65a12d5d952d76641f/repo/src/test/java/org/apache/commons/lang3/BooleanUtilsAiGeneratedTest.java`
- Compile log:
  `var/benchmark/v3_2-pro-4case/ws/6f59718258124b65a12d5d952d76641f/logs/mvn-test-jacoco.log`

Concrete errors:

- `BooleanUtils.and(true, true)` is ambiguous between `and(boolean...)` and `and(Boolean...)`.
- `BooleanUtils.and(Boolean.TRUE, Boolean.TRUE)` is also ambiguous.
- The same pattern repeats for `or`, `xor`, and `oneHot`.

Notable partial improvement:

- The model did cast some nulls correctly, for example
  `BooleanUtils.toBoolean((Boolean) null)`.
- It also used typed arrays in some exception tests, for example
  `BooleanUtils.and(new boolean[]{})`.
- It still ignored the core rule when generating ordinary positive-path
  assertions.

Interpretation:

- This is not primarily a missing-context problem. The v3.2 prompt already
  states the typed-array rule.
- It is a model compliance problem on a Java language edge case.
- Java overload resolution makes this a real compiler issue, not a stylistic
  preference. The Java Language Specification describes overload applicability
  in phases, including variable arity invocation and most-specific method
  selection:
  https://docs.oracle.com/javase/specs/jls/se22/html/jls-15.html#jls-15.12.2
- SEI CERT explicitly recommends avoiding ambiguous overloads of varargs
  methods because they are hard to reason about:
  https://cmu-sei.github.io/secure-coding-standards/sei-cert-oracle-coding-standard-for-java/recommendations/declarations-and-initialization-dcl/dcl57-j/

## 5. Design Judgment

v3.2 proves that narrow prompt/context hardening has value:

- API grounding improved `CSVRecord` from missing-symbol compile failure to
  compiled-but-wrong-oracle.
- Test structure improved `Validate` from the previous `@Nested` reporting risk
  to a real passing generated test.
- The string oracle sentinel passed.

But v3.2 also shows a limit:

- Some failures are not caused by absent evidence.
- Some failures are caused by model non-compliance with a concrete Java rule.
- Prompt-only hardening has diminishing returns for compiler-enforced language
  edge cases like primitive/boxed varargs overloads.

Therefore, this is **not ready for a full 10-case v3.2 rerun** if the full
acceptance bar still includes `BooleanUtils` compiling.

## 6. Recommended Next Step

Do not start broad Phase 3 repair yet. Do not restore coverage yet.

Recommended sequence:

1. Add one tiny v3.2.1 guardrail or policy decision for overloaded primitive /
   boxed varargs:
   - preferred prompt-only option: tell the model to skip ordinary positive-path
     assertions for overloaded primitive/boxed varargs unless every call uses a
     predeclared typed array variable;
   - stronger deterministic option: classify ambiguous primitive/boxed varargs
     compile errors as a bounded compile-only repair bucket, but this should be
     explicitly approved because it starts touching repair territory.
2. Re-run only `BooleanUtils` once with the chosen v3.2.1 route.
3. If `BooleanUtils` compiles, run the original v3.2 4-case validation again.
4. Only then run the full 10-case pro benchmark.

My recommendation is to try the prompt-only v3.2.1 route once, because it keeps
the current boundary intact. If the model still ignores it, stop spending prompt
iterations and design a very narrow compile-only repair bucket for varargs
ambiguity.

## 7. Explicit Non-Goals

- Do not auto-repair oracle failures.
- Do not rewrite expected values to actual values.
- Do not expand to whole-repository context.
- Do not resume coverage measurement yet.
- Do not run the full 10-case benchmark before the `BooleanUtils` compile issue
  is either fixed or intentionally accepted as a known failure bucket.

