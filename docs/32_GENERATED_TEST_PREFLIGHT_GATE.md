# Generated Test Preflight Gate

> Date: 2026-06-07. Scope: deterministic preflight gate only. No repair, no
> oracle changes, no expected-to-actual rewrite, no coverage restoration.

## 1. Why This Exists

`docs/31_CONTEXT_V3_2_1_BOOLEANUTILS_REVIEW.md` showed a useful failure
migration:

- v3.2.1 fixed the original primitive/boxed varargs ambiguity in
  `BooleanUtils`;
- the generated test still failed compilation because it called an unlisted
  overload: `BooleanUtils.toBooleanObject(int,int,int)`;
- the rendered method list only contained arities `1` and `4`.

This is not an oracle problem and should not be auto-repaired. It is a cheap
deterministic validity check that can run before Maven.

## 2. What Was Added

New module:

- `app/quality/generated_test_preflight.py`

Pipeline integration:

- `app/pipeline/generate_pipeline.py`

Report/review surfacing:

- `app/report/generation_report.py`
- `app/review/review_policy.py`

Tests:

- `tests/test_generated_test_preflight.py`
- `tests/test_generate_pipeline.py`
- `tests/test_generation_report.py`

## 3. Behavior

After the LLM returns `test_source`, before writing the generated test file and
before Maven execution, the pipeline runs a deterministic preflight.

The preflight currently checks only class-qualified calls to the target class:

- examples checked: `BooleanUtils.toBooleanObject(...)`,
  `BooleanUtils.and(...)`
- examples intentionally not checked: `record.get(...)`,
  `parser.getRecords(...)`

That scope is deliberate. The gate does not infer local variable receiver types
and does not try to become a Java type checker.

The gate blocks:

- calls to target methods not present in the rendered method list;
- calls to target overload arities not present in the rendered method list;
- individual-value calls to primitive/boxed varargs overload pairs, such as
  `BooleanUtils.and(true, true)`, where one typed array is required.

If preflight fails:

- the generated test is **not written**;
- Maven is **not run**;
- the job still reaches `GEN_DONE`;
- `execution.gen_outcome` is recorded as `COMPILE_FAILURE`;
- `execution.build_outcome` is recorded as `PREFLIGHT_REJECT`;
- `generation.preflight` carries the exact blocker evidence;
- review recommendation stays advisory and conclusion remains
  `NEED_HUMAN_REVIEW`.

### 3.1 Post-audit fix (2026-06-07)

The ambiguous primitive/boxed varargs blocker now fires only when **no
fixed-arity overload matches the call arity**. Java binds a fixed-arity overload
before a varargs one (JLS 15.12.2), so a call that a fixed overload accepts is
not ambiguous; biasing toward "defer to Maven" prevents the gate from skipping a
compilable test. Pinned by
`tests/test_generated_test_preflight.py::test_preflight_allows_fixed_arity_overload_alongside_varargs_pair`.
Live preflight↔javac agreement is deferred to the next benchmark audit doc (an
offline replay of the gate over the generated tests already stored in
`var/benchmark/*/bench.db`, compared against their real Maven outcomes — zero
model cost).

## 4. Boundary

This is not Phase 3 repair.

The preflight:

- does not edit generated tests;
- does not remove bad calls;
- does not change expected values;
- does not call an LLM;
- does not modify production code;
- does not expand context.

It is a deterministic review/triage gate.

## 5. Validation

Targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_generated_test_preflight.py tests\test_generate_pipeline.py tests\test_generation_report.py -q --disable-warnings
```

Result: passed.

Full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
```

Result: passed with existing skipped tests.

Offline replay against the previous failed `BooleanUtils` generated test:

Input:

- `var/benchmark/v3_2_1-pro-booleanutils-retry1/ws/b0a94d0a5ecc45409d78ea01e3a9367f/repo/src/test/java/org/apache/commons/lang3/BooleanUtilsAiGeneratedTest.java`

Result:

- preflight status: `FAIL`
- blockers:
  - `BooleanUtils.toBooleanObject(10, 10, 20) arity=3 allowed=[1, 4]`
  - `BooleanUtils.toBooleanObject(20, 10, 20) arity=3 allowed=[1, 4]`
  - `BooleanUtils.toBooleanObject(30, 10, 20) arity=3 allowed=[1, 4]`

This exactly matches the Maven compile failure from `docs/31`.

## 6. What This Does Not Solve

This gate does not catch:

- instance receiver calls where the variable type must be inferred;
- wrong expected values / oracle hallucination;
- weak assertions;
- semantic mismatch between Javadoc and source;
- APIs called through helper methods or fluent chains unless the target class is
  the direct receiver.

Those remain quality gate / human review / future design topics.

## 7. Next Step

Do not run another prompt-only BooleanUtils tweak.

Recommended next validation:

1. Run one real `BooleanUtils` pro case with the preflight gate enabled.
2. Expected useful outcomes:
   - if the model repeats the 3-arg hallucination, Maven should be skipped and
     the report should show `PREFLIGHT_REJECT`;
   - if the model avoids the hallucination, Maven should run as before.
3. Do not run full 4-case or 10-case until this single-case behavior is
   confirmed.

