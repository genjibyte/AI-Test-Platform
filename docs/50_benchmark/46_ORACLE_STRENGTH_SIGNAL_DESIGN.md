# Oracle-strength signal — design

> Date: 2026-06-12. **DESIGN ONLY. NOT implemented.** No code, no model, no benchmark,
> no data mutation, **no new dependency**. Follow-up to the business-tag rubric
> (`docs/50_benchmark/45_BUSINESS_INVARIANT_TAGGING_DESIGN.md` §15, which left the rubric's
> `oracle_strength` field for a human to fill) and the gap named in
> `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` / `44_DECISIONS_AND_FAILURES.md`
> ("semantic oracle strength is not measured; stays NEED_HUMAN_REVIEW").
>
> Upstream: the existing quality gate `app/quality/test_quality_gate.py`;
> `docs/30_phase2_5_quality/19_MINIMAL_TEST_QUALITY_GATE.md`;
> `docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md` (§2.2 mutation-guided generation;
> test-smell / fake-green patterns); thesis `docs/00_foundation/40_…`.

## 0. Why

The platform measures **structural** oracle quality already — `evaluate_test_quality`
flags `no_assertions`, `only_weak_assertions`, `tautological_assertion`,
`weak_assertion_heavy`, `missing_behavior_sources`, and counts `weak`/`tautological`
assertions (gating the worst as FAIL). What it does **not** measure is **semantic**
oracle strength: whether the assertions pin the *right, meaningful* behavior and would
actually catch a real regression. A test can be structurally fine (`assertEquals` with a
concrete value) yet still assert the wrong thing, echo its own input, or check a value
derived from the same buggy code. That dimension stays `NEED_HUMAN_REVIEW`, and the
business-tag rubric (docs/45 S3) deliberately left `oracle_strength` for a human.

Goal: an **advisory** signal that (a) consolidates the structural facts we already
compute into one human-facing `oracle_strength` hint, and (b) frames the real semantic
dimension honestly — **without inventing a fake "this test is valuable" verdict.**

## 1. Two dimensions of oracle strength (keep them separate)

- **Structural strength** — deterministic, offline, cheap, **mostly already exists**.
  Assertion presence / weakness / tautology / test-smells (assertion roulette, duplicate
  assertions, no behavioral oracle — KB test-smell list). The quality gate gates the
  worst; the rest is a roll-up.
- **Semantic / fault-detection strength** — the *real* signal: does the test **kill
  mutants**? **Mutation score** (KB §2.2: "stronger than line coverage because it asks
  whether a test can catch a meaningful behavioral regression"). This is the only
  automatic thing that actually evidences a meaningful oracle. Deterministic but
  **expensive** and needs a mutation tool (PIT for Java/Maven) → a new dependency →
  **deferred, owner-approved** (future `app/mutation/`).
- **The human rubric (docs/45 S3)** ties them to the business invariant: `expected_invariant`
  says *what* should be caught; structural says *is the assertion non-trivial*; mutation
  says *does it actually catch faults*; the human decides.

## 2. The load-bearing rule (anti-hallucination)

- **A structural estimate is NOT semantic proof.** `structural_ok` must never be presented
  as "the test is strong / valuable." It only means "not obviously a weak/empty oracle."
- **Only mutation evidence (real) or human review establishes semantic strength.** The
  signal must say which dimension it is, every time.
- **An LLM-judged oracle strength is UNTRUSTED** (a declared claim, like the business
  `*_declared` tag): advisory, surfaced for human review, never aggregated as fact, never
  feeds accept/score.
- **Advisory only.** Never auto-accept; `conclusion` stays `NEED_HUMAN_REVIEW`,
  `trusted=False`. **Never rewrite/weaken/delete an assertion** (oracle-safety, charter).

## 3. v1 — structural oracle-strength estimate (cheap, no new dependency)

A deterministic roll-up of the facts `evaluate_test_quality` already produces into one
advisory value + reasons:

```
oracle_strength_estimate ∈ { none, weak, mixed, structural_ok, unknown }   # STRUCTURAL only
```

- `none` — `no_assertions` / `no_test_methods` (gate FAIL).
- `weak` — `only_weak_assertions` or `tautological_assertion` (gate FAIL): structurally empty.
- `mixed` — `weak_assertion_heavy` (gate REVIEW): mostly weak.
- `structural_ok` — has non-weak, non-tautological assertions **and** passed the structural
  checks. **Semantic strength still unknown** (carry `missing_behavior_sources` if set).
- `unknown` — no source / not analyzed.

Reuse the gate's `metrics` (`assertions`, `weak_assertions`, `tautological_assertions`) and
issue codes — **no new parser, no duplication.** Optionally extend with a few more
deterministic test-smell reasons (assertion roulette, duplicate assertions, no-behavioral-
oracle — KB) as **advisory reasons only** (not gate blockers). Output also carries an
explicit `semantic_strength: "human_review"` until mutation evidence exists.

## 4. Deferred — semantic/fault evidence via mutation (the real signal)

Integrate a mutation tool (PIT for Java/Maven) to compute a **mutation score /
`mutation_killed_delta`** for the target — real evidence that the candidate's oracle
catches injected faults (KB §2.2 backlog: "Add `mutation_killed_delta` … to candidate
verdicts", future `app/mutation/`). It is the strongest semantic-strength signal and the
honest answer to docs/42/44's gap. **Heavy** (runs the suite against mutants) and needs a
**new dependency** → a separate, owner-approved slice. Still **advisory** (informs review;
never auto-accepts; never rewrites oracles).

## 5. Where it is computed / surfaced

- **Structural estimate:** a pure function (e.g. `app/quality/oracle_strength.py`) over a
  `QualityGateResult` (or its metrics/issues). Offline, deterministic, no model.
- **Surface:** fill the docs/45 S3 rubric's `oracle_strength` field as an **advisory hint**
  (the human can override); include in `review_summary`; allow benchmark/ledger group-by
  to compose with `run_kind == real` (docs/43 S2) and `business_pattern` (docs/45 S2) —
  e.g. "of real payments-idempotency candidates, how many are `structural_ok`."

## 6. Relationship to existing pieces (refine, don't duplicate or re-gate)

- **Quality gate** stays the gate — it still FAILs `no_assertions` / `only_weak` /
  `tautological`. The estimate is **advisory** and refines the PASS/REVIEW middle; it does
  **not** change gate verdicts.
- **Business tags (docs/45)** — `expected_invariant` frames *what* the oracle should catch;
  oracle-strength estimates *how strongly it does* (structural) and mutation *whether it
  actually does* (semantic).
- **Review policy** — see §12 open decision 2: v1 keeps the estimate advisory and does
  **not** change the recommendation.

## 7. Backward compatibility / historical data

No backfill (same discipline as `run_kind` / business tags). Historical rows / un-analyzed
candidates → `unknown`. Group-by views count only analyzed rows; the rest go to a labeled
`unknown` bucket. Historical artifacts stay read-only.

## 8. Scope guard — what NOT to do

- **No auto-accept / auto-score / auto-reward** from any oracle-strength value;
  `conclusion` stays `NEED_HUMAN_REVIEW`.
- **Never rewrite/weaken/delete an assertion**, and never "repair" an oracle.
- **No claim that `structural_ok` = valuable / correct.** Structural ≠ semantic.
- **No new dependency in v1** (mutation/PIT is the deferred slice, owner-approved).
- The pipeline must not infer semantic strength from source text; only mutation (real) or a
  clearly-untrusted LLM-judged path may estimate semantics, and the latter is never trusted.

## 9. Files likely touched (when implemented — NOT now)

- v1 (structural): `app/quality/oracle_strength.py` (roll-up over `QualityGateResult`); wire
  the hint into the docs/45 S3 rubric (`app/benchmark/runner.py` / `app/report/generation_report.py`);
  optional benchmark/ledger group-by; `tests/`.
- Deferred (semantic): `app/mutation/` + Maven/PIT integration; `mutation_killed_delta` on
  `BenchCaseResult` / `JudgedRecord`; `docs/quality/TEST_SMELL_AND_FAKE_GREEN_RULES.md`.

## 10. Rollout (small, independently testable slices)

- **S1 — structural estimate + rubric hint** (cheap, no new dep): roll up the gate facts
  into `oracle_strength` and surface it advisory into the S3 rubric / review summary.
- **S2 — group-by** in reports/ledger, composing with `run_kind == real` and `business_pattern`.
- **S3 (deferred, owner-approved, NEW DEP)** — mutation evidence (`mutation_killed_delta`)
  as the real semantic signal.

Each slice is small and paused until approved.

## 11. Acceptance (when implemented)

`pytest` green incl. new tests; the estimate is **advisory** — no change to gate verdicts,
recommendation, `conclusion`, `trusted`, or `accept_rate`; it **reuses** the gate's facts
(no duplicate parser); `structural_ok` never implies semantic value; mutation (if/when
added) is advisory and never auto-accepts.

## 12. Open decisions for the owner

1. **Extend test-smell reasons now, or reuse the gate's facts only?** Recommend: reuse the
   gate in v1; add a *small* set of advisory test-smell reasons only if cheap and clearly
   deterministic.
2. **May a `weak`/`mixed` estimate feed a CONSERVATIVE downgrade (STRONG→REVIEW)?** A
   downgrade never accepts, so it is safe — but it acts on a heuristic. Recommend: **No** in
   v1 (advisory only); revisit once **mutation** (real) evidence exists.
3. **Approve a mutation dependency (PIT) for the deferred semantic slice?** Recommend: defer;
   decide when v1 has landed and `run_kind`/tags are stable (KB §2.2 sequencing).
4. **Capture an LLM-judged oracle strength (untrusted `*_declared`) at all?** Recommend: not
   in v1; if ever, only as an explicitly-untrusted rubric hint.

## 13. Relationship to the deferred / sibling work

This closes the honest version of the docs/42/44 gap: **structural** strength is
consolidated + surfaced (cheap), and **semantic** strength is correctly attributed to
**mutation evidence** (real, deferred) or **human review** — never to a heuristic dressed up
as a verdict. Together with `run_kind` (real-only headlines) and business tags (what risk a
candidate protects), oracle strength completes the *"is this generated test actually
valuable?"* picture — while the **judgment stays human**, never auto-accepted.

## 14. Real PIT run — validation + JUnit5 finding (2026-06-13)

The dormant mutation subsystem (`app/mutation/`, merged gated-off in `5c4365f`) was
exercised once for real against a throwaway copy of `samples/calc` (gitignored
`var/pit_run/calc`; the fixture and the live benchmark were untouched, `mutation_enabled`
stayed `False`).

- **Validation (good):** PIT reported *Generated 5 / Killed 4 / 80%*. `parse_pit_report`
  on the real `mutations.xml` returned `total=5, detected=4, killed=4, survived=1,
  mutation_score=0.8` — i.e. `0.8 == PIT's 80%`. The real report format
  (`<mutation detected='true' status='KILLED' …>`) matches the parser exactly, so the one
  previously-untested assumption (the report schema) is **confirmed correct**.
- **Finding (refines §3 / §5 / §8):** `samples/calc` is **JUnit 5**, and PIT only discovers
  JUnit 5 tests when the **`pitest-junit5-plugin`** is on the pitest-maven plugin's
  classpath. The pure command-line, **no-pom-edit** `build_pit_command` cannot supply that
  plugin, so a vanilla run finds **no tests** on a JUnit 5 target — the run only succeeded
  because the throwaway pom declared the junit5 plugin. **So "command-line, no pom edit"
  holds for JUnit 4 but NOT for JUnit 5 (the modern norm)** — the concrete form of the
  "per-repo feasibility varies" caveat (§4).
- **Implication:** before mutation is useful on real (mostly JUnit 5) targets, the PIT
  invocation must be **JUnit5-aware** (provide the junit5 plugin), which effectively needs
  plugin/pom configuration — a follow-up. Until then mutation gracefully reports
  `available=False` on JUnit 5 targets (advisory; never blocks judging).

## 15. Gated run through the merged path — negative control + Windows fix (2026-06-14)

Re-ran on throwaway copies of `samples/calc` (gitignored `var/pit_run/*`; tracked
`samples/calc` and its pom untouched; `TESTAGENT_MUTATION_ENABLED=1` set only for the run),
this time through the **merged** `run_pit` (JUnit5-aware sidecar pom + `mvn -f`), and added a
**negative control** to prove the signal resists fake / green-but-empty tests.

- **Merged-path validation:** `run_pit` wrote the sidecar `pom-pit.xml` (original pom +
  `pitest-maven 1.15.0` + `pitest-junit5-plugin 1.2.1`; original untouched), ran PIT, and
  `parse_pit_report` returned `total=5, killed=4, survived=1, mutation_score=0.8` — verified
  **line-by-line against PIT's raw `mutations.xml`** (independent hand count = 5/4/1, not the
  parser's word). The surviving mutant is the **`max` `>`→`>=` ConditionalsBoundary**:
  `CalcTest.max()` only tests `max(7,3)`, never the boundary `max(x,x)`, so 0.8 is a *real,
  explainable* test-strength gap. `killingTest` entries carry `[engine:junit-jupiter]`,
  confirming the junit5 plugin actually drove the run.
- **Negative control (fake-pass guard — the load-bearing result for §2):** a second copy with
  the **same code, same coverage, GREEN and passing**, but `CalcTest` gutted to **zero
  assertions** (executes `add`/`max`, asserts nothing) → `mvn test` = 2 run / 0 fail (green),
  `NO_COVERAGE=0` (the code *is* executed), yet **`mutation_score=0.0` (5/5 SURVIVED)**.
  Coverage and green status cannot tell the real test (0.8) from the empty one (0.0);
  **mutation can.** This is exactly the "green but empty" / AI-fake-pass trap the platform
  exists to catch — and even the 0.8 stays **advisory** (`conclusion=NEED_HUMAN_REVIEW`,
  nothing auto-accepts).
- **Defect found + fixed (`app/mutation/run.py`):** `run_pit` defaulted `mvn="mvn"`; on Windows
  bare `mvn` is `mvn.cmd` and `subprocess` (no shell) raises `FileNotFoundError`, so the signal
  silently degraded to `available=False` on **every** Windows run. Fixed by resolving the
  launcher with `shutil.which(mvn) or mvn` (honours `PATHEXT`; falls back to the original string
  → safe degrade when Maven is absent). The default-path run then yields 0.8. Two offline
  regression tests added (`test_run_pit_resolves_mvn_launcher`,
  `test_run_pit_falls_back_when_mvn_unresolved`); full suite **267 passed / 4 skipped**.

## 16. First real-repo run — commons-cli OptionValidator (2026-06-14)

Ran the gated mutation on a real Apache library (throwaway copy of the benchmark mirror for
`commons-cli`, JUnit 5; copied to gitignored `var/pit_run/commons-cli`, `.git` removed, the
historical benchmark workspace untouched; `TESTAGENT_MUTATION_ENABLED=1` only for the run).
Scoped to one class + its real (human, Apache) test:
`targetClasses=org.apache.commons.cli.OptionValidator`,
`targetTests=org.apache.commons.cli.OptionValidatorTest`. 13 s, **default `mvn`** (post-fix path).

- **Result:** total=19, killed=17, survived=1, no_coverage=1, **mutation_score=0.8947** —
  verified by an independent grep count of PIT's raw `mutations.xml` (19/17/1/1), matching the
  parser exactly. A production-grade suite scores high but **not 100 %**.
- **The two non-killed mutants differ in KIND (this is why survivors need explanation):**
  - `validate` L125 `return null` → **NO_COVERAGE** (EmptyObjectReturnVals): `OptionValidatorTest`
    never calls `validate(null)` — a genuine **coverage gap** in this test class.
  - `validate` L136 `if (option.length() > 1)` → **SURVIVED** (ConditionalsBoundary `>`→`>=`):
    for a single-char option the inner `for (i = 1; i < chars.length; …)` guard makes `>1` and
    `>=1` behaviourally identical — an **equivalent mutant**, unkillable, NOT a test weakness.
- **Implication:** a survived mutant is **not** automatically a bad test; a future report must
  *classify* survivors (real gap vs equivalent vs trivial), not just count them. Mutation stays
  advisory; `conclusion=NEED_HUMAN_REVIEW`. Confirms the merged `run_pit`/sidecar path scales
  from the toy `samples/calc` to a real multi-class Maven repo unchanged.

---

> This design records the signal it adds; it grants no new scope and changes no judging
> verdict. The project stays: *AI-generated test candidate evaluation / audit / engineering-
> usability platform* — the product is the judgment, not a green checkmark.
