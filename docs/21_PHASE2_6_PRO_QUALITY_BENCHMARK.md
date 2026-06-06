# Phase 2.6 Pro Quality Benchmark

> Date: 2026-06-06
> Run: `var/benchmark/v2-pro-quality-final`
> Model: `deepseek-v4-pro`
> Scope: current Prompt/Context v2.1 + opt-in compile repair + quality gate.

## 1. Setup

Command shape:

```powershell
$env:TESTAGENT_LLM_MODEL='deepseek-v4-pro'
$env:TESTAGENT_REPAIR_COMPILE_FAILURES='true'
$env:TESTAGENT_REPAIR_MAX_ROUNDS='1'
$env:TESTAGENT_LLM_TIMEOUT_SECONDS='300'
$env:TESTAGENT_MVN_EXTRA_ARGS='-Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dlicense.skip=true -Denforcer.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dpmd.skip=true -Djacoco.skip=true'
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks\spec.example.json --out var\benchmark\v2-pro-quality-final
```

Two earlier attempts in this session were not valid benchmark evidence:

- `v2-pro-quality-current`: `deepseek-v4-pro` timed out on Option and two repos failed clone.
- `v2-pro-quality-rerun`: clones/model calls worked, but Maven policy plugins were not explicitly skipped, so all cases were blocked by `POLICY_PLUGIN_FAILURE`.

The valid run is `v2-pro-quality-final`.

## 2. Aggregate Result

| Metric | Result |
|---|---:|
| total cases | 3 |
| buildable repos | 3 |
| setup / clone / repo build failures | 0 / 0 / 0 |
| compile pass rate | 100% |
| generated-test pass rate | 33% |
| quality gate pass rate | 33% |
| quality gate failures | 0 |
| need human review rate | 100% |
| top failure types | `{'TEST_FAILURE': 2}` |

Coverage remains unavailable because JaCoCo is explicitly skipped for the current real-repo benchmark mode.

## 3. Per-case Result

| Case | Outcome | Quality | Root cause |
|---|---|---|---|
| commons-cli `Option` | `TEST_FAILURE` | `REVIEW (0 blockers / 1 warning)` | Generated tests call `Option.addValue`, which throws `UnsupportedOperationException`; model assumed it was a valid client API. |
| commons-csv `CSVRecord` | `TEST_FAILURE` | `REVIEW (0 blockers / 1 warning)` | Generated tests guessed exception types incorrectly: out-of-bounds `get(int)` throws `ArrayIndexOutOfBoundsException`, and `get(String)` without headers throws `IllegalStateException`. |
| commons-text `WordUtils` | `PASS` | `PASS (0 blockers / 0 warnings)` | Generated 3 focused tests with 8 assertions, no weak assertions, no tautologies, and non-empty behavior grounding. |

## 4. Quality Gate Detail

Current quality gate behavior is useful:

- It found no structural blockers in the two failing generated tests.
- It classified both failures as `REVIEW`, not `FAIL`, because the generated tests compiled and executed but had wrong oracle assumptions.
- It produced `PASS` for the WordUtils case even though `risk_flags` were present, because `risk_flags` are now advisory rather than status-downgrading.

This confirms the intended separation:

- compile/pass metrics tell whether the generated test executes;
- quality gate catches structural bad smells;
- `TEST_FAILURE` still requires human review and must not be auto-repaired by rewriting expected values.

## 5. Interpretation

Phase 2.6 is now showing a sharper picture than Phase 2.5:

- Compile failure is currently not the main blocker for `deepseek-v4-pro`: 3/3 compiled.
- Structural test quality is not the main blocker either: 0/3 quality FAIL.
- The remaining blocker is oracle/API-behavior correctness: 2/3 generated tests ran but asserted wrong exception/API behavior.

This means broadening Phase 3 repair is not the best next move. The project should not auto-fix these by changing expected values or deleting assertions.

## 6. Next Decision

Recommended next phase:

1. Define Phase 4 review policy:
   - `PASS` quality gate does not mean auto-accept.
   - `TEST_FAILURE` should remain review-only and non-acceptable by default.
   - `risk_flags` stay advisory.
2. Add reviewer-facing failure summaries:
   - failure type;
   - failed generated test names;
   - expected vs actual exception/value;
   - grounding/risk/advisory notes.
3. Expand benchmark to 5-8 targets only after the review policy is documented.

Do not expand the fixer into oracle rewriting.
