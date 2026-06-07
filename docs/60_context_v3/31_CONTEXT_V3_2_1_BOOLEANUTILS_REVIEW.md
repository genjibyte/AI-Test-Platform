# Context v3.2.1 BooleanUtils Validation Review

> Date: 2026-06-07. Scope: prompt-only guardrail plus one targeted
> `BooleanUtils` pro validation. No Phase 3 repair, no coverage restoration, no
> oracle auto-fix, no expected-to-actual rewrite, no full 4-case/10-case rerun.

## 1. Change Made

Implemented one prompt-only guardrail in `app/generate/prompt_builder.py`:

- primitive/boxed varargs overload positive-path calls must use a named typed
  array variable;
- individual varargs calls such as `BooleanUtils.and(true, true)` and
  `BooleanUtils.and(Boolean.TRUE, Boolean.TRUE)` are explicitly forbidden;
- uncertain cases must be skipped into `omitted_uncertain_cases`.

Pinned by:

- `tests/test_prompt_builder.py::test_v3_2_1_varargs_positive_paths_use_named_typed_arrays`

No repair code was added.

## 2. Local Tests

Commands:

- `.\.venv\Scripts\python.exe -m pytest tests\test_prompt_builder.py tests\test_generation.py -q --disable-warnings`
- `.\.venv\Scripts\python.exe -m pytest -q --disable-warnings`

Result:

- prompt/generation tests passed;
- full suite passed with the existing skipped tests.

Prompt size stayed bounded:

- system prompt: 3481 chars
- full sample prompt: 5644 chars
- `tests/test_generation.py::test_prompt_does_not_dump_whole_repo` remained under `<6000`

## 3. Real Validation Run

Target:

- `commons-lang3 BooleanUtils`
- commit: `598dfc163b8b410fb3bb8794521206ec8dcec82a`
- model: `deepseek-v4-pro`

Run outputs:

- failed setup attempt: `var/benchmark/v3_2_1-pro-booleanutils/`
- valid retry: `var/benchmark/v3_2_1-pro-booleanutils-retry1/`

The first attempt had `REPO_CLONE_FAILED` because GitHub was unreachable:

- `Failed to connect to github.com port 443`
- `generation_attempted = 0`

That attempt is not a model result. The valid retry reused the existing local
manifest mirror at the exact commit.

Retry result from
`var/benchmark/v3_2_1-pro-booleanutils-retry1/report.json`:

| Metric | Value |
|---|---:|
| buildable repos | 1 |
| generation attempted | 1 |
| baseline build outcome | `SUCCESS` |
| baseline tests green | true |
| generated outcome | `COMPILE_FAILURE` |
| compiled | false |
| quality gate | `FAIL` |
| recommendation | `REJECT_CANDIDATE` |

## 4. What Improved

The v3.2.1 guardrail did fix the original primitive/boxed varargs ambiguity
bucket in this generated file.

Evidence:

- Generated test:
  `var/benchmark/v3_2_1-pro-booleanutils-retry1/ws/b0a94d0a5ecc45409d78ea01e3a9367f/repo/src/test/java/org/apache/commons/lang3/BooleanUtilsAiGeneratedTest.java`

The generated test now uses typed arrays for `and`, `or`, and `xor`, for example:

- `boolean[] allTrue = {true, true, true}; BooleanUtils.and(allTrue);`
- `Boolean[] allTrue = {Boolean.TRUE, Boolean.TRUE, Boolean.TRUE}; BooleanUtils.and(allTrue);`
- similar typed-array calls for `or(...)` and `xor(...)`

This is a concrete improvement over the v3.2 4-case result, where the generated
test emitted ambiguous calls such as `BooleanUtils.and(true, true)`.

## 5. What Still Failed

The new compile failure is an API arity hallucination:

- generated call: `BooleanUtils.toBooleanObject(10, 10, 20)`
- compiler says no suitable method exists for `toBooleanObject(int,int,int)`

Evidence:

- compile log:
  `var/benchmark/v3_2_1-pro-booleanutils-retry1/ws/b0a94d0a5ecc45409d78ea01e3a9367f/logs/mvn-test-jacoco.log`
- error lines: generated test lines 262, 263, and 268

Actual target signatures in the rendered method list are:

- `Boolean toBooleanObject(int value)`
- `Boolean toBooleanObject(int value, int trueValue, int falseValue, int nullValue)`
- `Boolean toBooleanObject(Integer value)`
- `Boolean toBooleanObject(Integer value, Integer trueValue, Integer falseValue, Integer nullValue)`
- `Boolean toBooleanObject(String str)`
- `Boolean toBooleanObject(String str, String trueString, String falseString, String nullString)`

There is no 3-argument overload.

Likely cause:

- the neighbor test includes method names such as
  `test_toBooleanObject_int_int_int`, but the body actually calls the 4-argument
  API: `BooleanUtils.toBooleanObject(6, 6, 7, 8)`;
- the model appears to have copied the test-name pattern or older intuition
  instead of obeying the rendered method list.

## 6. Judgment

v3.2.1 is a partial success, not an acceptance success.

It proves:

- prompt-only can reduce one known compiler bucket when the rule is very
  concrete;
- the system still cannot rely on prompt compliance alone for "only use listed
  APIs".

It does **not** prove:

- `BooleanUtils` is ready for the full 4-case rerun;
- v3.2 is ready for the full 10-case benchmark;
- oracle or API hallucinations should be auto-fixed.

## 7. Recommendation

Stop prompt-only iterations for this failure class. The next prompt tweak would
likely chase one API hallucination at a time.

Recommended next design step, pending explicit approval:

1. Add a deterministic generated-test preflight that validates method-call
   names and arities against the rendered method list.
2. Classify violations as `REJECT_CANDIDATE` / compile-risk before expensive
   Maven execution.
3. Do **not** auto-edit the test yet.
4. If repair is later approved, keep it compile-only and bounded:
   - remove or skip calls to unlisted overloads;
   - do not change assertion expected values;
   - do not modify production code;
   - do not expand to whole-repository context.

This is adjacent to Phase 3 but should be treated as a separate gate/design
decision until repair is explicitly approved.

## 8. Do Not Do Yet

- Do not run the full 10-case benchmark.
- Do not run another BooleanUtils prompt tweak without a new design reason.
- Do not start oracle repair.
- Do not rewrite expected values to actual values.
- Do not restore coverage measurement.

