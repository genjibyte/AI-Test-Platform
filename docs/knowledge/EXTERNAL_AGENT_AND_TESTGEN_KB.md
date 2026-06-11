# External Agent & Test Generation Knowledge Base

> **Recorded 2026-06-11** into the repo as durable agent memory (`docs/knowledge/`).
> This is an **external-lessons** knowledge base. Per §9, it is **NOT proof any feature
> is implemented**. Many paths it references are **PLANNED, not yet present** — e.g.
> `AGENTS.md`, `docs/TASKS.md`, `docs/HANDOFF.md`, `docs/RUN_POLICY.md`,
> `docs/QUALITY_GATE.md`, `docs/ARTIFACT_SPEC.md`, `docs/FAILURE_LEDGER.md`,
> `artifacts/runs/`, `app/mutation/`, `app/reporting/`, `app/context_builder/`,
> `skills/`. **Current equivalents that DO exist:** quality gate = `app/quality/` +
> `docs/30_phase2_5_quality/19_MINIMAL_TEST_QUALITY_GATE.md`; reporting = `app/report/`;
> ledger = `app/ledger/`; benchmark audit = `scripts/audit_bench.py`; agent guide =
> `CLAUDE.md`. `run_kind` (P1-T3) is **designed but paused / not implemented**.

## Purpose
This knowledge base records external industrial and research lessons that are directly relevant to this project.
This project is not primarily an AI unit-test generator.
This project is an AI-generated test candidate evaluation, audit, and engineering-usability platform.
Generation is one producer.
The core product value is judging whether generated tests are reproducible, meaningful, non-fake-green, properly attributed, and safe for human review.
This document should guide future agents when they work on:
* agent harness design
* benchmark hygiene
* generated-test quality gates
* fake/real/dryrun/smoke separation
* mutation and coverage evaluation
* failure ledger design
* artifact evidence packages
* multi-agent builder/reviewer workflows
Do not use this document as permission to broaden the project scope.
Use it to strengthen the current architecture.

---

# 1. Core Thesis
## 1.1 Generation is not the product
External industrial practice shows that LLM-generated tests are only useful after filtering, execution, scoring, and human review.
For this project, a generated test should be treated as a candidate, not an accepted artifact.
A candidate must pass through a quality gate:
1. generated
2. compiles
3. tests pass
4. stable / non-flaky
5. contributes coverage
6. has behavioral assertion value
7. has mutation or fault-detection value if available
8. is not duplicate / placeholder / fake-green
9. is traceable to raw artifacts
10. remains `NEED_HUMAN_REVIEW` until reviewed

Project implication:
* `QualityGate` is core architecture.
* `Ledger` is core architecture.
* `scripts/audit_bench.py` is core architecture.
* `run_kind` is required for trustworthy metrics.
* Reports must distinguish raw harness runs from real model-quality metrics.

---

## 1.2 Harness beats prompt
Modern coding-agent productivity depends on the whole harness, not only the model or the prompt.
A useful agent workflow needs:
* task specification
* context selection
* project memory
* safe tool access
* permission boundaries
* verification commands
* observability
* failure attribution
* intervention recording
* artifact evidence
* reviewer workflow

Project implication:
* `CLAUDE.md` and `AGENTS.md` are soft guidance.
* `tests/conftest.py`, audit scripts, hooks, and verification commands are hard guards.
* Agent work must produce evidence, not just claims.
* Feature work should stay paused until foundation hardening is complete.

---

# 2. Industrial Lessons from AI Test Generation
## 2.1 Meta TestGen-LLM
Category: Industrial LLM test generation.
Key lesson:
Meta's TestGen-LLM did not simply generate tests and accept them. It improved existing human-written tests and required generated tests to pass filters that demonstrate measurable improvement. The important pattern is filter-backed recommendation, not blind generation.
Project pain point solved:
Prevents this project from treating a passing generated test as a useful generated test.
Project implication:
This project should not report "test pass rate" as model quality by itself. Reports should show each filter separately:
* build success
* reliable pass
* coverage delta
* quality verdict
* recommendation status
* human review status
Immediate tasks:
* Ensure `docs/QUALITY_GATE.md` defines filter layers.
* Ensure report generation separates each filter.
* Ensure ledger records why candidates were rejected.
* Keep `conclusion = NEED_HUMAN_REVIEW`.
Related project files:
* `docs/QUALITY_GATE.md`
* `app/ledger/`
* `app/benchmark/`
* `app/reporting/`
* `scripts/audit_bench.py`
Status: Immediate.

---

## 2.2 Meta ACH: mutation-guided test generation
Category: Industrial mutation-guided LLM test generation.
Key lesson:
Mutation-guided generation targets currently undetected faults. This is stronger than simply increasing line coverage because it asks whether a test can catch a meaningful behavioral regression.
Project pain point solved:
Avoids fake confidence from coverage-only improvements.
Project implication:
Long term, this project should use mutation evidence as a stronger signal than line coverage alone.
Immediate / later split:
Immediate:
* Document mutation value in `QUALITY_GATE.md`.
* Treat coverage-only improvement as insufficient for acceptance.
Later:
* Integrate PIT or another mutation tool for Java Maven targets.
* Add `mutation_killed_delta` or equivalent evidence to candidate verdicts.
Related project files:
* `docs/QUALITY_GATE.md`
* `app/coverage/`
* future `app/mutation/`
* `app/ledger/`
* `app/reporting/`
Status: Later, but should be documented now.

---

## 2.3 Meta observation-based TestGen
Category: Industrial test generation from runtime observations.
Key lesson:
Real execution observations can produce more realistic tests than source-only prompting. Existing usage patterns, object states, logs, and test traces are valuable context.
Project pain point solved:
Reduces hallucinated APIs, unrealistic mocks, and shallow tests.
Project implication:
The generator should eventually build context from:
* existing tests
* real method usages
* public API examples
* branch conditions
* coverage gaps
* failure logs
Immediate task:
Do not implement runtime observation now. First document this as a future direction.
Later task:
Add context builders that retrieve existing tests and focal usage examples before prompting.
Related project files:
* future `app/context_builder/`
* `app/pipeline/generate_pipeline.py`
* `docs/ROADMAP.md`
Status: Defer.

---

## 2.4 Meta Sapienz and CI-scale testing
Category: Industrial automated testing at scale.
Key lesson:
Automated testing systems become useful when they enter a repeatable CI / evidence loop, not when they merely demonstrate local generation.
Project pain point solved:
Prevents the project from becoming a demo-only generator.
Project implication:
Every important run should be reproducible and traceable:
* input manifest
* git commit
* model name
* prompt version
* run kind
* stdout/stderr
* report
* verdict
* failure attribution
Related project files:
* `artifacts/runs/`
* `docs/ARTIFACT_SPEC.md`
* `scripts/audit_bench.py`
* `scripts/verify.*`
* `docs/HANDOFF.md`
Status: Immediate.

---

# 3. Agent Engineering Lessons
## 3.1 OpenAI Harness Engineering
Category: Agent engineering / industrial practice.
Key lesson:
Agent productivity improves when the repository itself contains reusable guidance, verification commands, scaffolding, CI checks, and well-scoped tasks.
Project pain point solved:
Prevents future agents from rediscovering the same context and making uncontrolled architectural changes.
Project implication:
The project needs durable agent-facing assets:
* `CLAUDE.md`
* `AGENTS.md`
* `docs/TASKS.md`
* `docs/HANDOFF.md`
* `docs/RUN_POLICY.md`
* `docs/ARTIFACT_SPEC.md`
* `docs/QUALITY_GATE.md`
Immediate task:
Keep feature work paused until foundation-hardening files exist and are reviewed.
Related project files:
* `CLAUDE.md`
* `AGENTS.md`
* `docs/`
* `scripts/`
* `tests/conftest.py`
Status: Immediate.

---

## 3.2 Martin Fowler: Agent = Model + Harness
Category: Agent engineering.
Key lesson:
The model is only one part of the system. The surrounding harness provides context, tools, constraints, feedback, and verification.
Project pain point solved:
Avoids over-investing in prompt wording while under-investing in verification, evidence, and safety.
Project implication:
The project should optimize for:
* reproducible commands
* small tasks
* deterministic checks
* artifacts
* failure logs
* reviewer workflow
* safe rollback
Not for:
* longer prompts
* broader context dumps
* uncontrolled autonomous refactors
Related project files:
* `docs/agent_audit/`
* `scripts/audit_bench.py`
* `docs/FAILURE_LEDGER.md`
* `docs/HANDOFF.md`
Status: Immediate.

---

## 3.3 AI Harness Engineering taxonomy
Category: Agent harness research.
Key lesson:
A reliable software-agent harness needs multiple responsibilities:
* task specification
* context selection
* tool access
* project memory
* task state
* observability
* failure attribution
* verification
* permissions
* entropy auditing
* intervention recording
Project mapping:

| Harness responsibility | Project artifact                                       |
| ---------------------- | ------------------------------------------------------ |
| task specification     | `docs/TASKS.md`                                        |
| context selection      | `docs/CONTEXT_POLICY.md`                               |
| tool access            | `CLAUDE.md`, `AGENTS.md`, hooks                        |
| project memory         | `docs/knowledge/`                                      |
| task state             | `docs/HANDOFF.md`                                      |
| observability          | `artifacts/runs/`                                      |
| failure attribution    | `docs/FAILURE_LEDGER.md`                               |
| verification           | `pytest`, `scripts/audit_bench.py`, `scripts/verify.*` |
| permissions            | `docs/RUN_POLICY.md`, `tests/conftest.py`              |
| entropy auditing       | report-number audit scripts                            |
| intervention recording | `docs/HUMAN_INTERVENTION.md`                           |

Project implication:
The audit rubric should evaluate these harness components before allowing major feature work.
Status: Immediate.

---

## 3.4 GitHub Copilot agent workflow
Category: Agent workflow / branch-review practice.
Key lesson:
Agent work should happen through scoped branches, diffs, tests, and human review. The agent should not silently modify mainline project state.
Project pain point solved:
Prevents multi-agent overwrite, uncontrolled push, and unreviewed architecture drift.
Project implication:
Default policy:
* Builder agent implements small approved tasks.
* Reviewer agent reviews diff only.
* Human owner approves schema changes, benchmark expansion, real model runs, and pushes.
* No two agents should edit the same worktree at the same time.
Related project files:
* `docs/MULTI_AGENT_POLICY.md`
* `CLAUDE.md`
* `AGENTS.md`
* `docs/HANDOFF.md`
Status: Immediate.

---

## 3.5 Claude Code memory, hooks, and subagents
Category: Agent tooling.
Key lesson:
`CLAUDE.md` guides behavior, but deterministic guards and hooks are needed for hard safety constraints. Subagents can be useful, but only after roles and boundaries are clear.
Project pain point solved:
Prevents relying only on instructions for safety-critical rules such as "do not read `.env`" or "do not run real models."
Project implication:
Current hard guard:
* `tests/conftest.py` prevents accidental real LLM calls during tests.
Future hard guards:
* block `.env` printing
* block unauthorized `git push`
* block real model calls unless explicitly approved
* block destructive UI actions in future UI automation work
Related project files:
* `tests/conftest.py`
* `.claude/`
* `CLAUDE.md`
* future hooks
Status: Immediate for test guard, later for hooks.

---

## 3.6 Codex AGENTS.md and Skills
Category: Agent instruction and reusable workflows.
Key lesson:
Agent instructions should be repo-local, reusable, and operational. Skills should be small, task-specific workflows, not a large pile of generic advice.
Project pain point solved:
Prevents repeatedly teaching the same benchmark-audit, fake-green, and Maven/JUnit debugging procedures.
Project implication:
Create `AGENTS.md` for cross-agent rules.
First skills should be limited to:
* `benchmark-audit`
* `fake-green-detection`
* `maven-junit-debug`
Each skill must define:
* trigger
* inputs
* steps
* forbidden actions
* verification
* output format
Do not create a large skill library before the project has stable `run_kind`, quality gate, and artifact spec.
Related project files:
* `AGENTS.md`
* future `skills/benchmark-audit/SKILL.md`
* future `skills/fake-green-detection/SKILL.md`
* future `skills/maven-junit-debug/SKILL.md`
Status: Later.

---

# 4. Benchmark and Data Hygiene Lessons
## 4.1 Defects4J
Category: Java real-bug benchmark.
Key lesson:
Defects4J is a major Java benchmark for real bugs, but even established benchmarks require reproducibility and adequacy checks.
Project pain point solved:
Prevents treating benchmark datasets as automatically trustworthy.
Project implication:
Before any Defects4J pilot, each case must record:
* project
* bug id
* Java version
* Maven/Gradle version
* checked-out commit/version
* failing test
* reproduction command
* reproducibility status
* under-specified-test risk
Immediate decision:
Defer Defects4J pilot until after:
* `run_kind` exists
* benchmark audit is schema-based
* artifact evidence spec exists
Related project files:
* `docs/benchmark/BENCHMARK_POLICY.md`
* `docs/benchmark/BENCHMARK_SOURCES.md`
* future `benchmarks/defects4j/`
Status: Defer.

---

## 4.2 GitBug-Java
Category: Recent Java bug benchmark.
Key lesson:
Recent bugs reduce benchmark contamination risk and better reflect current development practices.
Project pain point solved:
Prevents over-relying on old benchmark tasks that may appear in model training data or public examples.
Project implication:
Future benchmark sources should include:
* source date
* commit SHA
* repo URL
* reproduction command
* model contamination risk
* artifact provenance
Related project files:
* `docs/benchmark/BENCHMARK_SOURCES.md`
* future benchmark manifests
Status: Later.

---

## 4.3 SWE-rebench and benchmark freshness
Category: Agent benchmark hygiene.
Key lesson:
Static benchmarks can become stale or contaminated. Fresh, traceable tasks are important for credible agent evaluation.
Project pain point solved:
Prevents inflated claims caused by benchmark leakage or undocumented task provenance.
Project implication:
Every benchmark result must record:
* model name
* model version if available
* prompt version
* run date
* git commit
* benchmark source
* benchmark source date
* run kind
* raw artifact path
Related project files:
* `scripts/audit_bench.py`
* future `docs/ARTIFACT_SPEC.md`
* future benchmark manifests
Status: Immediate for metadata policy, later for fresh benchmark collection.

---

## 4.4 Internal fake-client contamination
Category: Project-specific historical failure.
Key lesson:
The project already experienced a contamination case: raw benchmark `n=80` included fake-client / dry-run placeholder jobs, and the corrected real-model sample was `n=67`.
Project pain point solved:
Prevents recurrence of misleading headline metrics.
Project implication:
The project must add `run_kind` and stop relying on placeholder strings or model names to distinguish real/fake/dryrun/smoke.
Required rule:
Headline model-quality metrics must default to `run_kind == real`.
Raw totals may still be shown for harness/debugging, but they must not be presented as model-quality metrics.
Related project files:
* `scripts/audit_bench.py`
* future P1-T3 `run_kind`
* `docs/QUALITY_GATE.md`
* `app/benchmark/`
* `app/ledger/`
* `app/reporting/`
Status: Immediate.

---

# 5. Test Quality Lessons
## 5.1 AgoneTest
Category: Java LLM unit-test evaluation.
Key lesson:
Java LLM unit-test evaluation should include more than compilation and coverage. Mutation score and test smells are important dimensions.
Project pain point solved:
Prevents this project from optimizing only pass rate or line coverage.
Project implication:
QualityGate should eventually include:
* compilation
* execution
* coverage delta
* mutation score
* test smell risk
* duplicate-test risk
* fake-green risk
Immediate task:
Document the target quality dimensions.
Later task:
Implement mutation and test smell checks after `run_kind` and artifact spec are stable.
Related project files:
* `docs/QUALITY_GATE.md`
* future `app/mutation/`
* future `app/test_smells/`
* `app/ledger/`
Status: Later implementation, immediate documentation.

---

## 5.2 LLM-generated test smells
Category: Generated test maintainability and correctness risk.
Key lesson:
LLM-generated tests can compile and pass while still containing poor test design, such as magic numbers, assertion roulette, useless tests, empty tests, duplicate assertions, or unclear oracles.
Project pain point solved:
Explains why green tests can still be low value.
Project implication:
Fake-green detection should check for patterns such as:
* placeholder tests
* empty tests
* assertion-free tests
* assert-not-null-only tests
* constructor/getter/setter-only tests
* duplicate existing tests
* magic-number-heavy tests
* assertion roulette
* no behavioral oracle
* no new branch behavior
Related project files:
* `docs/quality/TEST_SMELL_AND_FAKE_GREEN_RULES.md`
* future `app/test_quality/`
* `app/ledger/`
* `docs/QUALITY_GATE.md`
Status: Immediate documentation, later implementation.

---

## 5.3 Software evolution and regression awareness
Category: Test generation under code changes.
Key lesson:
LLM-generated tests can be sensitive to superficial code changes and may not preserve regression awareness under software evolution.
Project pain point solved:
Prevents overclaiming that generated tests are robust to future changes.
Project implication:
Future project direction can include change-aware evaluation:
* diff-aware candidate generation
* changed-branch coverage
* regression-sensitive quality gate
* PR-aware benchmark
* old-test preservation tracking
Do not implement this now.
Related project files:
* `docs/ROADMAP.md`
* future `app/change_analysis/`
* future PR-aware benchmark
Status: Defer.

---

## 5.4 Mockless and dependency-aware Java test generation
Category: Advanced Java LLM test generation.
Key lesson:
Advanced Java unit-test generation benefits from real usage patterns, dependency awareness, symbol constraints, protocol constraints, repair loops, and experience memory.
Project pain point solved:
Explains why naive source-only prompting often hallucinates APIs, mocks, or invalid test setup.
Project implication:
Future generator improvements should prioritize:
* existing usage retrieval
* class index
* dependency summaries
* test repair under compiler feedback
* historical failure memory
* constraint-enforced fixing
Do not build this before foundation hardening is complete.
Related project files:
* future `app/context_builder/`
* future `app/repair/`
* future `docs/CONTEXT_POLICY.md`
* `docs/knowledge/`
Status: Defer.

---

# 6. Domestic / Industry Testing Direction
## 6.1 Multi-agent testing, UI automation, change-impact analysis
Category: Industry direction.
Key lesson:
Industry testing teams are moving toward multi-agent testing workflows, UI automation, multimodal defect detection, code-change impact analysis, and test recommendation.
Project pain point solved:
Helps position this project in a broader test-engineering roadmap without broadening the current implementation.
Project implication:
Current project should stay focused on unit-test candidate evaluation.
Later industrial extensions may include:
* change-impact analysis
* test recommendation
* UI safe-mode automation
* multi-agent review
* multimodal UI defect detection
Do not mix these into current foundation-hardening work.
Related project files:
* `docs/ROADMAP.md`
* future UI automation docs
Status: Defer.

---

# 7. Immediate Project Rules Derived from External Knowledge
## 7.1 Headline metrics rule
Headline model-quality metrics must use real model runs only.
Required future schema:
```text
run_kind ∈ {real, fake, dryrun, smoke}
```
Default reporting:
```text
headline metrics = rows where run_kind == real
raw metrics = all rows, shown separately
```
Until `run_kind` exists, any fake/real split is heuristic and must be labeled as incomplete.

---

## 7.2 Generated test acceptance rule
A generated test must not be accepted because it merely passes.
Minimum evidence:
* compiles
* passes
* not flaky if rerun is available
* has meaningful assertions
* not placeholder
* not duplicate
* improves coverage or behavior evidence
* mutation value if available
* remains human-review-required

---

## 7.3 Agent work rule
Agent output must include evidence:
* files changed
* commands run
* command results
* test results
* remaining risks
* whether `.env` was avoided
* whether real model calls were avoided
* whether P3 / architecture changes were avoided if out of scope

---

## 7.4 Benchmark rule
Every benchmark case or run should eventually record:
* benchmark source
* repo
* path
* commit SHA
* model name
* prompt version
* run date
* run kind
* git commit
* artifact path
* reproduction command
* known limitations

---

# 8. Immediate Backlog Derived from This Knowledge Base
## Immediate
1. Add or update `AGENTS.md`.
2. Add `docs/TASKS.md`.
3. Add `docs/HANDOFF.md`.
4. Add `docs/RUN_POLICY.md`.
5. Add `docs/PROJECT_HISTORICAL_CONTEXT.md`.
6. Design P1-T3 `run_kind`.
7. Update `docs/QUALITY_GATE.md` with filter-backed candidate evaluation.

## Next
1. Implement P1-T3 `run_kind`.
2. Update `scripts/audit_bench.py` to use schema-based run-kind separation.
3. Add regression test preventing fake/dryrun/smoke rows from entering real headline metrics.
4. Add artifact evidence package spec.
5. Add failure ledger entries for known contamination and fake-green risks.

## Later
1. Add mutation testing integration.
2. Add test smell detection.
3. Add fake-green detection rules.
4. Add benchmark source policy.
5. Add Defects4J or GitBug-Java pilot.
6. Add skills for benchmark audit, fake-green detection, and Maven/JUnit debugging.

## Defer
1. Defects4J pilot until run_kind and artifact spec exist.
2. UI automation expansion.
3. Multi-agent subagent system.
4. Real model large-scale experiments.
5. PR-aware / change-aware testing.

---

# 9. How Agents Should Use This Document
Before designing architecture or quality gates, read this document together with:
* `CLAUDE.md`
* `AGENTS.md`
* `docs/TASKS.md`
* `docs/QUALITY_GATE.md`
* `docs/HANDOFF.md`
* `scripts/audit_bench.py`

Do not cite this document as proof that a feature is implemented.
This document records external lessons and project implications.
Implementation still requires:
* code changes
* tests
* artifact evidence
* command output
* review

The project should remain narrow:
```text
AI-generated test candidate evaluation / audit / engineering-usability platform
```
Do not reposition it as:
```text
generic AI testing platform
generic coding agent framework
generic UI automation platform
generic benchmark suite
```
Current priority:
```text
foundation hardening -> run_kind -> quality gate evidence -> benchmark hygiene -> then P3
```
