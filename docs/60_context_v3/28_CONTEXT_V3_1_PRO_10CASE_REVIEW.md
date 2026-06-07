# Context v3.1 Pro 10-Case Review

> Date: 2026-06-07. Scope: audit Claude commit `e22810a` and run
> `benchmarks/manifest.v1.json` with Context v3.1 + `deepseek-v4-pro`.
> Repair disabled. Coverage skipped. No oracle auto-fix.

---

## 1. Pre-run audit

Commit audited: `e22810a feat(context): v3.1 prompt hardening — overload/reflection/state rules`.

Observed change scope:

- `app/generate/prompt_builder.py`: additive `SYSTEM_PROMPT` rules only.
- `tests/test_prompt_builder.py`: tests pin overload/generic, public API, and doc/source-conflict rules.
- `tests/test_generation.py`: bounded-context prompt-length heuristic raised from 4000 to 6000.
- `/docs/60_context_v3/27_CONTEXT_V3_1_PROMPT_HARDENING.md`: design note.

No parser, repair, coverage, benchmark runner, or production pipeline code changed in this commit.

Validation before benchmark:

- `python -m pytest tests/test_prompt_builder.py tests/test_generation.py -q` passed.
- `python -m pytest --disable-warnings` passed: `168 passed, 4 skipped, 1 warning`.
- Synthetic prompt length was `4905`, below the new `6000` bound. This supports the claim that v3.1 adds fixed rules rather than dumping repository context.

External rule sanity:

- Java overload ambiguity is a real compile-time concern under the Java method invocation / overload-resolution rules: Java Language Specification, method invocation expressions.
- JUnit exception testing should be explicit (`assertThrows`), but the exact exception still needs grounded evidence from source, Javadoc, or neighbor tests.
- GitHub Copilot testing guidance stresses relevant context and review; it does not imply generated tests should be auto-accepted.

References:

- Java Language Specification, §15 Method Invocation Expressions: <https://docs.oracle.com/javase/specs/jls/se24/html/jls-15.html>
- JUnit 5 User Guide, Assertions: <https://junit.org/junit5/docs/current/user-guide/#writing-tests-assertions>
- GitHub Copilot test-writing docs: <https://docs.github.com/en/copilot/tutorials/write-tests>

---

## 2. Run

Output directory:

- `var/benchmark/v3_1-pro-10case`

Command shape:

```powershell
$env:TESTAGENT_LLM_PROVIDER='openai'
$env:TESTAGENT_LLM_MODEL='deepseek-v4-pro'
$env:TESTAGENT_LLM_TIMEOUT_SECONDS='300'
$env:TESTAGENT_REPAIR_COMPILE_FAILURES='false'
$env:TESTAGENT_MVN_EXTRA_ARGS='-Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dlicense.skip=true -Denforcer.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dpmd.skip=true -Djacoco.skip=true'
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks\manifest.v1.json --out var\benchmark\v3_1-pro-10case
```

Operational note:

- First launch stalled while re-fetching a pinned mirror from GitHub.
- It had not reached model generation yet, so the launch was stopped.
- Existing pinned mirrors from `var/benchmark/manifest-dryrun/mirrors` were copied into the new output directory.
- All 4 mirror HEADs matched `benchmarks/manifest.v1.json` pins before restart.

Evidence:

- `var/benchmark/v3_1-pro-10case/report.json`
- `var/benchmark/v3_1-pro-10case/report.md`
- `var/benchmark/v3_1-pro-10case/bench.db`
- Generated tests and Maven logs under `var/benchmark/v3_1-pro-10case/ws/*`

---

## 3. Aggregate

| Metric | v3 (`docs/26`) | v3.1 (`report.json`) |
|---|---:|---:|
| total cases | 10 | 10 |
| buildable repos | 4 | 4 |
| setup / clone / repo build failures | 0 / 0 / 0 | 0 / 0 / 0 |
| generation attempted | 10 | 10 |
| compile pass rate | 60% | 80% |
| generated-test pass rate | 20% | 30% |
| quality gate pass rate | 20% | 30% |
| top failure types | `TEST_FAILURE:4`, `COMPILE_FAILURE:3`, `PIPELINE_FAILED:1` | `TEST_FAILURE:4`, `COMPILE_FAILURE:2`, `NO_TESTS:1` |
| recommendation distribution | `REJECT_CANDIDATE:5`, `NEEDS_REVISION:3`, `STRONG_REVIEW_CANDIDATE:2` | `REJECT_CANDIDATE:3`, `NEEDS_REVISION:4`, `STRONG_REVIEW_CANDIDATE:3` |
| need human review rate | 100% | 100% |
| coverage measured | 0/10 | 0/10 |

Result:

v3.1 improved compile rate and strong-candidate count, but it is not a clean win.
The run exposed regressions and one measurement/classification gap.

---

## 4. Per-case result

| Case | v3 result | v3.1 result | Judgment |
|---|---|---|---|
| `Option` | `TEST_FAILURE` | `TEST_FAILURE` | still state/conditional-exception oracle problem |
| `Options` | `COMPILE_FAILURE` | `TEST_FAILURE` | compile problem fixed, but required-option oracle wrong |
| `CommandLine` | `PASS` | `TEST_FAILURE` | regression |
| `CSVRecord` | `TEST_FAILURE` | `COMPILE_FAILURE` | regression to missing/non-public API use |
| `CSVFormat` | `TEST_FAILURE` | `PASS` | improvement |
| `WordUtils` | `TEST_FAILURE` / quality `FAIL` | `PASS` / quality `PASS` | improvement; reflection/private-constructor issue removed |
| `StringEscapeUtils` | `PASS` | `TEST_FAILURE` | regression |
| `NumberUtils` | `COMPILE_FAILURE` | `PASS` | improvement; overload/null issue fixed |
| `Validate` | `PIPELINE_FAILED` invalid JSON | `NO_TESTS` in report, but nested tests actually executed | JSON fixed; measurement gap exposed |
| `BooleanUtils` | `COMPILE_FAILURE` | `COMPILE_FAILURE` | overload/varargs rule still insufficient |

---

## 5. Acceptance against `docs/27`

### A. The 3 v3 compile failures should drop or move to PASS

Partly met.

- `Options`: moved from `COMPILE_FAILURE` to `TEST_FAILURE`.
- `NumberUtils`: moved from `COMPILE_FAILURE` to `PASS`.
- `BooleanUtils`: stayed `COMPILE_FAILURE`.

Net compile failures dropped from 3 to 2, but one new compile failure appeared
on `CSVRecord`.

### B. `WordUtils` should stop producing reflection/private-constructor tests

Met.

`WordUtils` is now `PASS`, quality `PASS`, recommendation `STRONG_REVIEW_CANDIDATE`.

### C. Existing strong candidates must not regress

Not met.

- `CommandLine`: `PASS` -> `TEST_FAILURE`.
- `StringEscapeUtils`: `PASS` -> `TEST_FAILURE`.

This confirms model nondeterminism and prompt side effects remain material.

### D. Genuine oracle/doc-conflict cases should stay reviewable, not auto-fixed

Mostly met.

`Option`, `Options`, `CommandLine`, and `StringEscapeUtils` failures stayed
`NEEDS_REVISION`, not auto-accepted or oracle-rewritten. This preserves the
project red-line.

---

## 6. Failure roots

### 6.1 `Option`: conditional body throw misused as unconditional oracle

Generated failure summary:

- `testCloneThrows`: expected `UnsupportedOperationException`, but nothing was thrown.
- `testSetTypeObject`: `String` cannot be cast to `Class`.
- `testGetValueIndexOutOfBounds`: expected `IndexOutOfBoundsException`, but nothing was thrown.
- `testGetValuesEmpty`: expected non-null empty array, actual `null`.

Evidence:

- `var/benchmark/v3_1-pro-10case/ws/cd9dd16d088b4d8cb82c22b4b1f35ed5/repo/src/test/java/org/apache/commons/cli/OptionAiGeneratedTest.java`
- `var/benchmark/v3_1-pro-10case/ws/cd9dd16d088b4d8cb82c22b4b1f35ed5/logs/mvn-test-jacoco.log`

Design implication:

v3.1 says body throws are only supporting evidence, but `body_throws` still
marks conditional throws. The model then treats conditional control flow as an
unconditional oracle. Context v3.2 needs either:

- prompt wording that explicitly says conditional `throw new` inside `catch` or
  branch is not enough to assert a normal-path exception; or
- a small parser/context distinction between direct unconditional throws and
  conditional/catch throws.

Do not repair this by changing expected values.

### 6.2 `Options`: required option oracle wrong

Failure:

- `testAddRequiredOption`: expected `true`, actual `false`.

Design implication:

This is not a compile problem. It is a state/API-semantics problem: generated
tests inferred required-option state without enough evidence. It belongs in
Context v3.2 state grounding / skip rules, not Phase 3 repair.

### 6.3 `CommandLine`: null argument oracle wrong

Failure:

- `testAddArgNull`: expected size `1`, actual `0`.

Design implication:

The model relied on neighbor-test names / inferred null behavior. This should
be skipped unless the exact neighbor test body or source branch is available.

### 6.4 `CSVRecord`: generated test calls unavailable API

Compile error:

- `CSVRecordAiGeneratedTest.java:[175,19] 找不到符号`
- missing method: `putInMap(Map<String,String>)` on `CSVRecord`.

Evidence:

- `var/benchmark/v3_1-pro-10case/ws/46a14d92c91f4c14beb10ed3b09d1d0a/logs/mvn-test-jacoco.log`

Design implication:

The prompt says use only context APIs, but the model still invoked a method not
available on the class in this pinned version. This is an API-grounding failure.
It can be prevented by stronger "if not in rendered method list, skip" wording
or by a deterministic preflight that flags generated calls outside the rendered
API list. It should not be handled by oracle repair.

### 6.5 `StringEscapeUtils`: entity oracle guessed

Failures:

- expected `>` but actual `&gt;`
- expected `a&lt;b>c` but actual `a&lt;b&gt;c`

Design implication:

This is exactly the oracle problem: entity-mapping behavior was guessed beyond
evidence. The model even listed many escaping values as omitted, but still
asserted XML escaping details. v3.2 should tighten "skip exact escaping maps
unless neighbor/source gives exact mapping".

### 6.6 `Validate`: benchmark classification gap for JUnit5 `@Nested`

Report outcome:

- `NO_TESTS`, quality `FAIL`.

But Maven log shows:

- `ValidateAiGeneratedTest$ExclusiveBetweenComparable`: 3 tests, 0 failures.
- `ValidateAiGeneratedTest$NotEmptyArray`: 3 tests, 0 failures.
- `ValidateAiGeneratedTest$IsTrue`: 3 tests, 0 failures.
- `ValidateAiGeneratedTest$NotNull`: 3 tests, 0 failures.
- build success.

Evidence:

- `var/benchmark/v3_1-pro-10case/ws/4306d31496234138a358cd7a3ba2d26d/logs/mvn-test-jacoco.log`
- `var/benchmark/v3_1-pro-10case/ws/4306d31496234138a358cd7a3ba2d26d/repo/target/surefire-reports/TEST-org.apache.commons.lang3.ValidateAiGeneratedTest.xml`
- nested surefire reports under the same directory.

Design implication:

The official report must remain as generated (`NO_TESTS`), but this case is not
an actual no-test generation. It is a measurement gap: generated tests using
JUnit5 `@Nested` can execute in nested surefire reports while the top-level
class report has `Tests run: 0`.

Minimal next options:

1. Prompt route: forbid `@Nested` in generated tests; require flat `@Test`
   methods only.
2. Harness route: aggregate `GeneratedTest$*` surefire reports into the generated
   test outcome.

The prompt route is smaller. The harness route is more correct if nested tests
are allowed.

### 6.7 `BooleanUtils`: overload/varargs prompt still too weak

Compile errors:

- `toBoolean(null)` ambiguous between `Boolean` and `String`.
- `toBooleanObject(null)` ambiguous between `Integer` and `String`.
- `and/or/xor/oneHot(true, false)` ambiguous between primitive and boxed varargs.

Evidence:

- `var/benchmark/v3_1-pro-10case/ws/39fa98d269f64ba5b538709aa2d0b07d/logs/mvn-test-jacoco.log`

Design implication:

v3.1's overload rule worked for `NumberUtils` but was not strong enough for
BooleanUtils. The model ignored "typed array" for ordinary two-argument varargs
calls. v3.2 should explicitly say:

- for any method with both primitive and boxed varargs overloads, never call it
  with individual vararg arguments;
- always call via `new boolean[]{...}` or `new Boolean[]{...}`;
- cast every `null` to the intended overload type, including `Boolean`, `String`,
  and `Integer`.

---

## 7. Direction decision

Do not start broad Phase 3 repair yet.

Why:

- `TEST_FAILURE` remains the largest failure bucket.
- Two v3 strong candidates regressed due model/oracle behavior, not compile syntax.
- One report failure (`Validate`) is a measurement gap, not a model compile error.
- BooleanUtils shows prompt compliance is still incomplete; a compile fixer could
  patch this mechanically, but doing so now would hide whether generation rules
  are actually improving.

Do not restore coverage yet.

Why:

- This run intentionally skipped coverage.
- The current bottleneck is generated-test correctness / classification, not
  coverage measurement.

Do not auto-repair oracles.

Why:

- `Option`, `Options`, `CommandLine`, and `StringEscapeUtils` are behavior/oracle
  failures. Rewriting expected values would violate the project red-line.

Recommended next step:

Implement a narrow **Context/Prompt v3.2** pass, not Phase 3 repair:

1. Strengthen overload/varargs rules for primitive-vs-boxed overloads.
2. Forbid or handle JUnit5 `@Nested`; prefer prompt-forbid first because it is smaller.
3. Tighten API grounding: if a method is not in the rendered method list, skip it.
4. Treat conditional/catch body throws as non-oracle evidence.
5. Tighten exact escaping/entity/state behavior: skip unless source/neighbor gives exact expected value.

Then run only a targeted 4-case validation first:

- `BooleanUtils`
- `Validate`
- `CSVRecord`
- one regression sentinel: `StringEscapeUtils` or `CommandLine`

If targeted validation is better, rerun the full 10-case benchmark.

---

## 8. Final conclusion

v3.1 is directionally useful but not sufficient.

It proves the project pain point more sharply:

- Better prompt/context can remove some mechanical failures (`NumberUtils`,
  `WordUtils`, `CSVFormat`).
- The same prompt can also create regressions when behavior evidence is weak.
- The platform's review loop is still necessary: every case remains
  `NEED_HUMAN_REVIEW`.

Current best direction is **v3.2 context/prompt hardening plus one small
measurement-policy fix**, not Phase 3 repair and not coverage restoration.
