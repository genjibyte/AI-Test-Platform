# Context v3 Pro 3-Case Review

> Date: 2026-06-07. Scope: frozen 3-case comparison only
> (`Option`, `CSVRecord`, `WordUtils`). No Phase 3 repair, no coverage restore,
> no oracle auto-fix, no 10-case expansion.

---

## 1. Boundary

This review evaluates whether Context v3 method-contract grounding improves the
same 3 frozen cases used by `docs/21`:

- commons-cli `Option` at `ae44dcdffd28d6a1a32dc4e0801b715adcef162e`
- commons-csv `CSVRecord` at `8192d9d196a554d67d7d65b0a131001b9d1eb412`
- commons-text `WordUtils` at `e910b53a90308dbd70d54b4f69843805b53fc0fa`

The run uses `deepseek-v4-pro`, explicit Maven skip flags, and
`TESTAGENT_REPAIR_COMPILE_FAILURES=false`. Coverage remains unavailable because
`-Djacoco.skip=true` is still required for the current real-repo benchmark mode.

External direction re-checked before interpreting the result:

- GitHub Copilot testing docs: generated tests still require review and benefit
  from existing-test context.
- JUnit 5 user guide: `assertThrows` is the right mechanism for exception
  assertions, but only if the expected exception type is grounded.
- EvoSuite paper: oracle correctness is a core limitation of generated tests;
  generated assertions still require developer review.
- ProjectTest / MultiFileTest (`arXiv:2502.06556`): project-level, executable
  benchmarks and failure distributions are the right evidence shape.

Links: GitHub Copilot docs
<https://docs.github.com/en/copilot/tutorials/write-tests>, JUnit 5
<https://docs.junit.org/current/user-guide/>, EvoSuite paper
<https://www.evosuite.org/wp-content/papercite-data/pdf/esecfse11.pdf>,
ProjectTest/MultiFileTest <https://arxiv.org/abs/2502.06556>.

---

## 2. Run Validity

Three attempts happened; only the last one is full evidence.

| Run | Evidence status | Reason |
|---|---|---|
| `var/benchmark/v3-pro-3case` | Invalid | `REPO_CLONE_FAILED` for all 3 cases; no model generation attempted. GitHub network failed. |
| `var/benchmark/v3-pro-3case-rerun` | Partial | Local mirrors fixed clone. `Option` generated and executed, but `CSVRecord` / `WordUtils` hit LLM connection failures. |
| `var/benchmark/v3-pro-3case-bodyfix` | Valid | 3/3 generated, 3/3 compiled, 3/3 executed. This is the comparison run. |

The partial rerun exposed a Context v3 boundary bug: `body_throws` was presented
too strongly, so the model treated a `clone()` catch-block throw as an
unconditional exception. Commit `35c8649` fixed the prompt boundary:
`body contains throw` is now supporting evidence only; exact exception oracles
need declared `throws`, Javadoc `@throws`, or neighbor-test evidence.

---

## 3. Aggregate Comparison

| Metric | v2 pro (`docs/21`) | v3 pro bodyfix |
|---|---:|---:|
| total cases | 3 | 3 |
| generation attempted | 3 | 3 |
| clone / setup / repo build failures | 0 / 0 / 0 | 0 / 0 / 0 |
| compile pass rate | 100% | 100% |
| generated-test pass rate | 33% | 67% |
| quality gate pass rate | 33% | 67% |
| quality gate failures | 0 | 0 |
| top failure types | `{'TEST_FAILURE': 2}` | `{'TEST_FAILURE': 1}` |
| recommendation distribution | not present in old report | `{'STRONG_REVIEW_CANDIDATE': 2, 'NEEDS_REVISION': 1}` |
| need human review rate | 100% | 100% |

Interpretation: Context v3 is directionally useful on the frozen evidence set.
It preserved compilation, reduced `TEST_FAILURE` from 2 to 1, and turned
`CSVRecord` from a wrong-exception failure into a passing strong review
candidate.

This is still n=3 and model-nondeterministic. It is evidence for proceeding to
a broader benchmark, not a stable pass-rate claim.

---

## 4. Per-Case Result

| Case | v2 result | v3 bodyfix result | Interpretation |
|---|---|---|---|
| `Option` | `TEST_FAILURE`, quality `REVIEW` | `TEST_FAILURE`, quality `REVIEW`, `NEEDS_REVISION` | Improved in the original failure area: no longer misuses `addValue`, and no longer asserts `clone()` always throws. Still guesses `getArgs()` and `getValues()` behavior. |
| `CSVRecord` | `TEST_FAILURE`, quality `REVIEW` | `PASS`, quality `PASS`, `STRONG_REVIEW_CANDIDATE` | Main win. Javadoc/body contract evidence prevents wrong exception guesses and the generated test compiles and passes. |
| `WordUtils` | `PASS`, quality `PASS` | `PASS`, quality `PASS`, `STRONG_REVIEW_CANDIDATE` | No regression. The model uses documented examples/null behavior and omits uncertain behavior. |

### Option Remaining Failures

`OptionAiGeneratedTest` has 12 tests; 10 pass, 1 fails, 1 errors.

- `testConstructorOptionHasArgDescription`: expected `Option.UNINITIALIZED`
  (`-1`) for `new Option("a", true, "desc").getArgs()`, actual is `1`.
- `testGetValueEmpty`: calls `option.getValues().length`, but actual
  `getValues()` returns `null` when no values exist, despite Javadoc saying an
  empty array.

This is not a compile problem and should not enter Phase 3 repair. It is a
remaining oracle/API semantics problem, plus a source/Javadoc mismatch for
`getValues()`.

---

## 5. What Context v3 Fixed

The intended v3 signal is visible in real output:

- `Option.addValue` has strong contract evidence:
  `@throws UnsupportedOperationException always` and direct body throw.
  The v3-bodyfix generated test asserts that behavior correctly.
- `CSVRecord.get(String)` has `@throws IllegalStateException` for no header and
  `@throws IllegalArgumentException` for inconsistent/missing mappings.
  The generated test now uses those exception types correctly.
- `WordUtils` stays conservative. It skips many non-null behavior cases where
  expected values are not grounded.

The boundary fix matters: raw `body_throws` is not enough to assert an exact
exception, because it can occur only on rare control-flow paths. The prompt now
reflects that.

---

## 6. Residual Problems

1. **Option still needs better constructor/state grounding.**
   Method contracts alone are not enough for `argCount` and `values` state
   after constructors. This suggests Context v4 should consider compact
   constructor/state summaries or selected constructor bodies, not oracle repair.

2. **Javadoc can conflict with implementation.**
   `Option.getValues()` Javadoc says empty array, but implementation returns
   `null` for no values. The model followed documentation and failed. This is a
   real enterprise pain point: docs/spec/source may disagree. The platform must
   surface it to reviewers, not auto-fix it.

3. **Run stability is still a concern.**
   The first valid rerun attempt had two LLM connection failures. The final run
   succeeded, but future benchmark reporting should separate provider/network
   failures from model-quality failures.

4. **No coverage evidence yet.**
   Coverage remains unavailable by design. This run validates generation and
   review policy, not coverage improvement.

---

## 7. Decision

Continue the current direction. Context v3 is worth keeping and is good enough
to justify the next controlled step.

Recommended next step:

1. Run the full 10-case `manifest.v1` with v3 + `deepseek-v4-pro`.
2. Keep repair disabled for that run.
3. Keep coverage skipped.
4. Analyze failure distribution by bucket:
   api-contract / exception-semantics / pure-function.

Do not start Phase 3 repair yet. The remaining `Option` failure is not a compile
repair problem. It is a context/spec/source conflict problem.

Do not auto-fix `Option` by changing expected values. That would violate
`docs/07` A5 and erase exactly the signal this platform is supposed to expose.

---

## 8. Concrete Acceptance for Next Run

For the 10-case run, success is not "all pass". The expected useful outputs are:

- no clone/setup/repo-build failures;
- compile pass rate remains high;
- `recommendation_distribution` shows how many cases are strong candidates vs
  needs revision/reject;
- failed cases include reviewer-facing expected/actual summaries;
- failures are grouped by bucket so the next design step is evidence-driven.

If the 10-case run shows many failures like `Option.getValues()` where docs and
implementation disagree, the next design work should be Context v4
state/constructor grounding, not oracle repair.
