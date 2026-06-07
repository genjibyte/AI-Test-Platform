# Phase 2.5 v2.1 and Minimal Compile Repair Review

> Date: 2026-06-06
> Scope: Prompt/Context v2.1, source-level grounding, and opt-in compile-only repair.
> Evidence: current code, tests, and real benchmark reports under `var/benchmark/`.

## 1. What Changed

This round did not add a broad fixer or refactor the main pipeline. It added two narrow pieces:

1. Prompt/context v2.1 grounding:
   - `app/context/maven_deps.py` now extracts Maven compiler source/target/release from `pom.xml`.
   - `app/models/context_snapshot.py` carries `build_constraints`.
   - `app/context/context_collector.py` includes those constraints in snapshots.
   - `app/generate/prompt_builder.py` exposes Java source-level rules to the model, especially Java 8 constraints such as avoiding `List.of`.

2. Opt-in deterministic compile repair:
   - `app/repair/compile_repair.py` adds a small compile-only repair function.
   - `app/pipeline/generate_pipeline.py` can run one repair round only when `repair_compile_failures=True`.
   - `.env.example` and `app/config.py` expose `TESTAGENT_REPAIR_COMPILE_FAILURES` and `TESTAGENT_REPAIR_MAX_ROUNDS`.
   - `app/report/generation_report.py`, `app/benchmark/models.py`, and `app/benchmark/report_md.py` surface repair traces and aggregate repair rounds.

The repair scope is intentionally small. It handles missing JUnit static assertion imports, Java 8 `List.of(...)` to `Arrays.asList(...)`, and simple method-local enum declarations. It does not change expected values and does not repair oracle failures.

## 2. Why This Direction Matches The Project Pain

The Phase 2.5 real-repo benchmark showed that the platform's useful pain is not "can an LLM write a test-looking file"; it is whether generated tests survive real project constraints and expose reviewable failure causes.

Evidence:

- `/docs/30_phase2_5_quality/15_PHASE2_5_RESULT_REVIEW.md` records the first 3-case run: 0/3 generated tests passed, with 2 compile failures and 1 oracle/test failure.
- `/docs/30_phase2_5_quality/16_MODEL_COMPARISON_REVIEW.md` records model comparison: stronger model helps but does not remove failures.
- `var/benchmark/v2-flash/report.md` and `var/benchmark/v2-pro/report.md` show v2 prompt/context still had 67% compile pass and 33% generated-test pass in both model tiers.

This round therefore focuses on two concrete enterprise-like constraints:

- Build-context grounding: the generator must know whether the target repo is Java 8, Java 11, etc.
- Deterministic post-generation triage: simple compile failures should be repaired or at least classified without asking the model to guess.

## 3. Benchmark Results

All runs used the same 3 Apache Commons targets in `benchmarks/spec.example.json`.

| Run | Model | Repair | Compile pass | Generated test pass | Per-case result |
|---|---|---:|---:|---:|---|
| `var/benchmark/v2-flash/report.md` | `deepseek-v4-flash` | off | 67% | 33% | Option PASS, CSVRecord COMPILE_FAILURE, WordUtils TEST_FAILURE |
| `var/benchmark/v2-pro/report.md` | `deepseek-v4-pro` | off | 67% | 33% | Option TEST_FAILURE, CSVRecord COMPILE_FAILURE, WordUtils PASS |
| `var/benchmark/v2-flash-repair/report.md` | `deepseek-v4-flash` | on | 67% | 33% | Option PASS, CSVRecord COMPILE_FAILURE, WordUtils TEST_FAILURE |
| `var/benchmark/v2-pro-repair/report.md` | `deepseek-v4-pro` | on | 100% | 67% | Option TEST_FAILURE, CSVRecord PASS, WordUtils PASS |

Interpretation:

- The best current configuration is v2.1 context plus `deepseek-v4-pro`: 3/3 compile, 2/3 generated tests pass.
- The flash repair run proves the repair trace can execute: WordUtils changed from compile failure to test failure after one static-import repair round.
- The flash aggregate did not improve because CSVRecord still failed compilation in a shape outside the current repair bucket.
- The pro repair run did not rely on repair rounds. Its improvement mainly comes from better model output plus v2.1 source-level grounding, not from the deterministic fixer.

## 4. What Is Actually Solved

Solved or improved:

- Java source-level context is now represented in `ContextSnapshot` and prompt text.
- Java 8 compatibility is explicitly visible to the model.
- Repair is opt-in and does not affect Phase 2/2.5 default flow.
- Compile repair results are visible in both per-generation reports and benchmark summaries.
- Human review remains the authority: generated tests stay `trusted=False`, and repair traces are metadata, not acceptance.

Evidence:

- `tests/test_context_collector.py` covers Maven build constraints and neighbor-test excerpt behavior.
- `tests/test_prompt_builder.py` covers the Java 8 prompt rule.
- `tests/test_compile_repair.py` covers the three deterministic repair buckets and the no-op unknown case.
- `tests/test_generation_report.py` covers grounding and repair trace reporting.
- `tests/test_benchmark.py` covers repair aggregate reporting.

Current full test result:

```powershell
.\.venv\Scripts\python.exe -m pytest
# 136 passed, 4 skipped, 1 warning
```

## 5. What Is Not Solved

Oracle correctness is still the core unsolved problem.

Evidence:

- `var/benchmark/v2-pro-repair/report.md` has only one remaining top failure type: `TEST_FAILURE`.
- The remaining failing case is `commons-cli Option`.
- The failure is behavioral/oracle-related, not harness setup, clone, or repo build: setup/clone/repo build failures are all 0 in the benchmark reports.

Do not solve this by automatically changing expected values to match runtime output. That would create weak or tautological tests, which conflicts with the direction in `/docs/00_foundation/07_SOURCE_NOTES.md` and `/docs/30_phase2_5_quality/15_PHASE2_5_RESULT_REVIEW.md`.

Also not solved:

- Coverage is still unavailable in these benchmark reports: `coverage_measured: 0/3`.
- The sample size is still only 3 targets. It proves the loop, not a stable product metric.
- Real enterprise integration is still absent: no IDE integration, no CI PR workflow, no multi-module build strategy beyond the current harness, and no security policy for proprietary code.

## 6. Risk Review

Risk 1: Model variance remains high.

The same target can fail differently across flash/pro and across runs. The project should treat benchmark outcome as distribution data, not a single deterministic score.

Risk 2: Repair scope can expand too easily.

Compile repair is safe only while it stays deterministic and narrow. Adding LLM-based repair now would blur the boundary between "fix compile syntax/imports" and "invent behavior."

Risk 3: Passing tests may still be low quality.

The current benchmark checks compile and test pass, not assertion strength, mutation resistance, branch coverage, or business relevance.

Risk 4: Reports are better than decisions.

Repair traces and grounding metadata help humans review the output, but the platform still lacks an acceptance gate that can reject weak tests automatically.

## 7. Recommended Next Step

Do not broaden Phase 3 yet.

The next most valuable work is a small quality gate before expanding the fixer:

1. Keep compile repair opt-in and limited to deterministic buckets.
2. Add a "test quality review" report section for weak assertions, tautological assertions, excessive `assertNotNull`, no meaningful branch assertion, and oracle-risk flags.
3. Expand the mini-benchmark from 3 targets to 5-8 targets using `deepseek-v4-pro` only.
4. Record failure distribution by bucket: compile/import, compile/language-level, target API hallucination, oracle mismatch, weak assertion, harness/build.
5. Only after that, decide whether Phase 3 should add another deterministic compile repair bucket.

## 8. Current Decision

Continue the current direction, but keep it narrower than a general autonomous fixer.

Should continue:

- Prompt/context grounding.
- Real-repo mini-benchmark.
- Opt-in deterministic compile repair.
- Human-reviewable reports.

Should not continue yet:

- LLM-based repair loops.
- Automatic oracle rewriting.
- Coverage optimization before generated-test quality is gated.
- Large multi-agent systems or agent orchestration.
- Broad Phase 3 expansion before more benchmark evidence.

The current best project story is now:

> TestAgent Lab is moving from "AI generates tests" to "AI-generated tests are judged, grounded, repaired only for deterministic compile issues, and reviewed with evidence on real repositories."

That is closer to the real pain than a simple generation demo, and still small enough to finish into a credible MVP.
