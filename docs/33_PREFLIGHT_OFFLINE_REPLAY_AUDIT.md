# Preflight Offline Replay Audit

> Date: 2026-06-07. Scope: deterministic replay only. No model calls, no
> pipeline changes, no generated-test repair, no oracle changes, no coverage
> restoration.

## 1. Purpose

`docs/32_GENERATED_TEST_PREFLIGHT_GATE.md` introduced a deterministic
generated-test preflight gate. Because a preflight `FAIL` skips Maven in the
current pipeline, the gate needs an explicit evidence check before the next paid
benchmark.

This audit replays the current preflight implementation over generated tests
already stored in existing benchmark databases and compares each replay verdict
with the Maven outcome already recorded by those historical runs.

The check is zero-cost: it reads only local `bench.db` files and their existing
workspace repositories.

## 2. Inputs

Primary sample:

- `var/benchmark/v3-pro-10case/bench.db`
- `var/benchmark/v3_1-pro-10case/bench.db`
- `var/benchmark/v3_2-pro-4case/bench.db`

Supplemental BooleanUtils sample:

- `var/benchmark/v3_2_1-pro-booleanutils/bench.db`
- `var/benchmark/v3_2_1-pro-booleanutils-retry1/bench.db`

One `v3-pro-10case` job was not replayable because it failed before generation:

- job `fc1d2c9443fa43c7ae89c8c5721ebcc8`
- stored error: invalid LLM JSON
- no generated test source existed to replay

`var/benchmark/v3_2_1-pro-booleanutils/bench.db` contained no jobs. The
retry database contained the replayable BooleanUtils job.

## 3. Method

For each replayable job:

1. Read `generation_json.result.test_source` from `bench.db`.
2. Reconstruct a fresh `ContextSnapshot` from the job workspace repo with
   `app.context.context_collector.build_snapshot(...)`.
3. Run
   `app.quality.generated_test_preflight.evaluate_generated_test_preflight(...)`.
4. Compare the preflight result with the historical
   `generation_json.execution.gen_outcome`.

Classification:

- `preflight_compile_agree`: preflight `FAIL` and historical Maven
  `COMPILE_FAILURE`.
- `over_reject_candidate`: preflight `FAIL` but historical generated test
  compiled far enough to become `PASS`, `TEST_FAILURE`, or `NO_TESTS`.
- `narrow_gate_miss_compile_failure`: preflight `PASS` but historical Maven
  `COMPILE_FAILURE`.
- `pass_no_over_reject`: preflight `PASS` and historical generated test was not
  a compile failure.

This replay uses `result.test_source`, matching the current pipeline location:
preflight runs after generation and before writer normalization / Maven.

## 4. Results

Primary sample:

| metric | value |
|---|---:|
| replayable jobs | 23 |
| preflight PASS | 20 |
| preflight FAIL | 3 |
| historical COMPILE_FAILURE | 6 |
| historical TEST_FAILURE | 9 |
| historical PASS | 7 |
| historical NO_TESTS | 1 |
| preflight compile agreement | 3 |
| over-reject candidates | 0 |
| narrow-gate missed compile failures | 3 |

Supplemental BooleanUtils sample:

| metric | value |
|---|---:|
| replayable jobs | 1 |
| preflight PASS | 0 |
| preflight FAIL | 1 |
| historical COMPILE_FAILURE | 1 |
| preflight compile agreement | 1 |
| over-reject candidates | 0 |

Combined replay:

| metric | value |
|---|---:|
| replayable jobs | 24 |
| preflight PASS | 20 |
| preflight FAIL | 4 |
| historical COMPILE_FAILURE | 7 |
| historical TEST_FAILURE | 9 |
| historical PASS | 7 |
| historical NO_TESTS | 1 |
| preflight compile agreement | 4 |
| over-reject candidates | 0 |
| narrow-gate missed compile failures | 3 |

Blocker codes observed:

| blocker code | count |
|---|---:|
| `ambiguous_varargs_overload_call` | 92 |
| `unlisted_target_overload_arity` | 3 |

## 5. Preflight FAIL Cases

All preflight `FAIL` cases matched historical Maven `COMPILE_FAILURE`.

| run | target | historical outcome | preflight blocker |
|---|---|---|---|
| `v3-pro-10case` | `org.apache.commons.lang3.BooleanUtils` | `COMPILE_FAILURE` | ambiguous primitive/boxed varargs calls such as `BooleanUtils.and(true, true)` |
| `v3_1-pro-10case` | `org.apache.commons.lang3.BooleanUtils` | `COMPILE_FAILURE` | ambiguous primitive/boxed varargs calls such as `BooleanUtils.and(Boolean.TRUE, Boolean.FALSE)` |
| `v3_2-pro-4case` | `org.apache.commons.lang3.BooleanUtils` | `COMPILE_FAILURE` | ambiguous primitive/boxed varargs calls such as `BooleanUtils.or(Boolean.TRUE, Boolean.FALSE)` |
| `v3_2_1-pro-booleanutils-retry1` | `org.apache.commons.lang3.BooleanUtils` | `COMPILE_FAILURE` | unlisted overload arity: `BooleanUtils.toBooleanObject(10, 10, 20) arity=3 allowed=[1, 4]` |

Interpretation: for historical BooleanUtils failures, the current preflight
would have stopped the same invalid generated tests before Maven, with exact
blocker evidence.

## 6. Preflight PASS But Maven Compile Failed

Three compile failures were not caught by preflight. These are expected misses
under the current narrow scope, not evidence of over-rejection.

| run | target | compile error shape | why preflight passed |
|---|---|---|---|
| `v3-pro-10case` | `org.apache.commons.cli.Options` | incompatible generic assignment: `List<?>` to `List<Option>` | no class-qualified target calls were present (`target_class_calls=0`) |
| `v3-pro-10case` | `org.apache.commons.lang3.math.NumberUtils` | ambiguous `toDouble(null, ...)` between `BigDecimal` and `String` overloads | current gate does not type-check null-literal overload ambiguity |
| `v3_1-pro-10case` | `org.apache.commons.csv.CSVRecord` | missing instance method `putInMap(...)` | current gate intentionally ignores instance receiver calls such as `record.putInMap(...)` |

These misses confirm the gate's design boundary:

- it is not a Java type checker;
- it does not infer receiver variable types;
- it does not reason about generic assignment compatibility;
- it only validates direct class-qualified target calls against the rendered
  method list.

## 7. Finding

The replay found **zero over-reject candidates** across 24 replayable jobs.

That is the key safety result. Since preflight `FAIL` skips Maven, the most
dangerous failure mode is blocking a test that historically compiled. This
replay did not find that behavior.

The replay also found that the gate catches a useful but narrow slice of compile
failures:

- 3 of 6 primary-sample compile failures;
- 4 of 7 combined compile failures when adding the BooleanUtils retry sample.

This is acceptable for the current design because the gate is a deterministic
triage guard, not a complete compiler replacement.

## 8. Boundaries

This audit does not prove the gate is complete. It only supports the narrower
claim:

> On the existing v3/v3.1/v3.2 generated-test artifacts, the current preflight
> implementation catches known BooleanUtils API-list failures without evidence
> of over-rejecting tests that historical Maven compiled.

Remaining uncertainty:

- future targets may expose parser gaps in the reconstructed method list;
- inherited static methods are still not modeled;
- instance receiver calls remain outside scope;
- null-literal overload ambiguity remains outside scope;
- generic type compatibility remains outside scope.

Do not add advisory mode yet. The replay does not justify expanding the
pipeline surface area.

## 9. Recommendation

Proceed to one live `BooleanUtils` pro validation with preflight enabled.

Expected acceptable outcomes:

1. If the model repeats an API-list or varargs hallucination, the report should
   show `PREFLIGHT_REJECT` and skip Maven.
2. If the model avoids those hallucinations, Maven should run normally.

Do not start Phase 3 repair, do not restore coverage, and do not add oracle
auto-repair. After the single-case live validation, run the full 10-case pro
quality benchmark only if the report preserves the same taxonomy:

- `PREFLIGHT_REJECT` for deterministic generated-test API violations;
- normal Maven outcomes for tests outside the preflight boundary;
- human review for semantic/oracle failures.
