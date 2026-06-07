# Minimal Test Quality Gate

> Date: 2026-06-06
> Scope: deterministic quality checks for generated Java unit tests.
> Boundary: no LLM judge, no oracle rewriting, no auto-accept.

## 1. Why Add This

Phase 2.5 proved that compile/pass alone is not enough. The best current run,
`var/benchmark/v2-pro-repair/report.md`, reached 100% compile and 67% generated
test pass, but the remaining blocker is oracle/test quality. A generated test can
compile and pass while still being weak, tautological, unstable, or unrelated to
the target behavior.

This is the exact Phase 4 direction described in `/docs/00_foundation/07_SOURCE_NOTES.md`:
assertion quality checks, production-code boundary checks, coverage comparison,
and weak assertion detection.

## 2. What Was Implemented

Added a deterministic quality gate in `app/quality/test_quality_gate.py`.

It checks generated test source plus existing execution/coverage facts:

- generated test did not execute;
- generated patch touched production code;
- coverage dropped;
- no `@Test` methods;
- no assertions;
- only weak assertions such as `assertNotNull` / `assertNull` / `fail`;
- tautological assertions such as `assertEquals(x, x)` or `assertTrue(true)`;
- unstable behavior such as sleeps, randomness, wall-clock time, environment reads,
  external file/network APIs;
- reflection/internal implementation access;
- missing obvious target reference;
- missing `behavior_sources` for oracle review.
- model-declared `risk_flags` as reviewer advisories, without changing status.

The gate returns:

- `PASS`: no blocker and no warning; advisories may still be present;
- `REVIEW`: warnings only;
- `FAIL`: at least one blocking quality issue.

## 3. Where It Surfaces

Generation report:

- `app/report/generation_report.py` now includes `quality_gate`.
- The existing `conclusion` remains `NEED_HUMAN_REVIEW`.
- The gate does not change generated code and does not mark tests trusted.

Benchmark report:

- `app/benchmark/models.py` records per-case `quality_gate_status`,
  `quality_blockers`, and `quality_warnings`.
- Aggregates now include `quality_gate_pass_rate`,
  `quality_gate_failures`, and `quality_gate_reviews`.
- `app/benchmark/report_md.py` renders quality status as `STATUS (blockers/warnings)`.

## 4. What It Does Not Do

It does not:

- call a model to judge the test;
- rewrite expected values;
- mutate generated tests;
- accept a generated test automatically;
- compute mutation score;
- prove oracle correctness.

This is intentional. The gate is a first deterministic screen before expanding
Phase 3 or adding heavier enterprise PoC behavior.

## 5. Tests

Added:

- `tests/test_quality_gate.py`

Updated:

- `tests/test_generation_report.py`
- `tests/test_benchmark.py`

Current targeted result:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_quality_gate.py tests\test_generation_report.py tests\test_benchmark.py -q
# 34 passed
```

## 6. Next Use

The next real benchmark should use `deepseek-v4-pro` and inspect:

- compile pass rate;
- generated test pass rate;
- `quality_gate_pass_rate`;
- quality failure buckets.

If many passing tests fail the quality gate, the next design step should be
prompt/context oracle grounding and review policy, not a broader repair loop.
