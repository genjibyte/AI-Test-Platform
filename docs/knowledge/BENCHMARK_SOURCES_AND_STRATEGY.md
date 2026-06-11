# Benchmark Sources and Dataset Strategy

## Purpose

This document defines benchmark and sample-source strategy for this project.

This project is not primarily an AI unit-test generator.
This project is an AI-generated test candidate evaluation, audit, and engineering-usability platform.

The benchmark goal is not to collect as many datasets as possible.
The benchmark goal is to build a trustworthy, reproducible, contamination-aware evaluation pipeline for AI-generated Java test candidates.

A benchmark source is useful only if it can help evaluate at least one of the following:

* whether generated tests compile
* whether generated tests pass
* whether generated tests improve coverage
* whether generated tests have behavioral value
* whether generated tests can catch real bugs
* whether generated tests avoid fake-green patterns
* whether results can be reproduced from raw artifacts
* whether fake / dryrun / smoke / real model runs are separated
* whether model-quality claims are trustworthy

---

# 1. Current Benchmark Thesis

## 1.1 Generation is only one producer

The platform should treat every generated test as a candidate.

A candidate is not accepted just because it exists or passes. It must be evaluated through a quality gate:

1. generated
2. compiles
3. tests pass
4. stable / non-flaky if rerun is available
5. contributes coverage
6. has meaningful assertions
7. is not duplicate
8. is not placeholder / fake-green
9. has mutation or fault-detection evidence if available
10. remains human-review-required until reviewed

## 1.2 Benchmark hygiene is mandatory

The project already encountered benchmark contamination: raw benchmark `n=80` included fake-client / dry-run / placeholder jobs, and the corrected real-model sample was `n=67`.

Therefore:

* headline model-quality metrics must default to real model runs only
* fake / dryrun / smoke runs must be shown separately
* raw totals may be used for harness debugging, not model-quality claims
* every benchmark claim must be reproducible from raw artifacts
* `run_kind` is required for trustworthy metrics

Required future field:

```text
run_kind ∈ {real, fake, dryrun, smoke}
```

Until `run_kind` exists, any fake/real separation is heuristic and must be labeled as incomplete.

---

# 2. Benchmark Layering Strategy

Do not connect every dataset at once. Use a layered benchmark strategy.

## Layer 0: Harness Smoke Benchmark

Purpose:

Validate that the platform can run end-to-end.

Sources:

* local `samples/calc`
* current Apache Commons small samples
* QuixBugs Java small cases
* IntroClassJava small cases

Expected value:

* fast feedback
* stable local verification
* no headline model-quality claims

Do not use Layer 0 for formal model-quality conclusions.

---

## Layer 1: Java Maven Real-Project Unit-Test Benchmark

Purpose:

Evaluate generated JUnit test candidates on real Java Maven projects.

Sources:

* current Apache Commons Lang / CLI / CSV / Text samples
* ProjectTest Java subset
* AgoneTest / Classes2Test subset
* Microsoft Methods2Test sample
* JetBrains TestSpark / EvoSuite / Randoop as baseline references

Expected metrics:

* compile pass
* test pass
* coverage delta
* branch coverage delta if available
* test smell risk
* fake-green risk
* duplicate-test risk
* human-review-required verdict

This should be the immediate benchmark direction after foundation hardening.

---

## Layer 2: Real-Bug / Fail-to-Pass Benchmark

Purpose:

Evaluate whether generated tests can expose real bugs.

Sources:

* Defects4J
* GitBug-Java
* Bugs.jar
* Bears
* BugSwarm

Expected oracle:

A generated test should:

* fail on the buggy version
* pass on the fixed version
* avoid flaky behavior
* avoid overfitting
* provide meaningful regression evidence

This layer should not start until:

* `run_kind` exists
* benchmark audit is schema-based
* artifact evidence package exists
* QualityGate is stable

Recommended first step:

* 3-bug Defects4J pilot only

---

## Layer 3: Issue / Agent Benchmark

Purpose:

Evaluate future coding-agent ability on real issue-style software engineering tasks.

Sources:

* SWT-Bench
* SWE-bench-java
* SWE-bench Multilingual
* Multi-SWE-bench
* SWE-rebench methodology

This layer is not current scope.

Use it only as future roadmap reference for:

* issue-to-regression-test generation
* PR-aware test generation
* change-impact testing
* agentic issue resolution

---

# 3. Immediate Recommended Sources

## 3.1 Current Apache Commons Samples

Category:

Local Java Maven real-project seed benchmark.

Likely projects:

* Apache Commons Lang
* Apache Commons CLI
* Apache Commons CSV
* Apache Commons Text

Why relevant:

These projects are Java/Maven-friendly and suitable for deterministic unit-test candidate generation. They are small enough for local iteration and large enough to reveal real test-generation problems.

Project pain point solved:

Provides a controllable Layer 1 benchmark before connecting large external datasets.

Immediate use:

Yes.

Candidate task type:

* generate JUnit tests
* evaluate compile/test pass
* evaluate coverage delta
* inspect fake-green risk

Required metadata:

* repo name
* repo URL
* commit SHA
* module path
* source file
* existing test file if available
* Maven command
* Java version
* JUnit version
* run_kind
* artifact path

Risks:

* sample selection bias
* too easy if only utility methods are selected
* may overrepresent string/collection utilities
* must not mix fake-client smoke runs with real model metrics

Status:

Immediate.

---

## 3.2 ProjectTest Java Subset

Category:

Project-level unit-test generation benchmark.

Why relevant:

ProjectTest is closer to this project than algorithmic coding benchmarks because it evaluates unit-test generation inside real repositories, not isolated toy functions.

Project pain point solved:

Tests whether the platform can handle project-level Java context, build systems, compilation errors, and cascading test failures.

Immediate use:

Pilot.

Candidate task type:

* project-level unit-test generation
* compile/test/coverage evaluation
* generated-test failure classification

Required metadata:

* ProjectTest source project
* repo URL
* commit SHA
* Java version
* Maven/Gradle version
* test framework
* build command
* test command
* source file
* target class/method
* artifact path

Risks:

* environment setup may be heavier than Apache Commons
* projects may use different build systems
* task extraction may require adaptation
* must avoid claiming full ProjectTest support after only a small subset

Recommended pilot:

Start with 3–5 Java Maven projects only.

Status:

Pilot after current benchmark hygiene improves.

---

## 3.3 AgoneTest / Classes2Test

Category:

Java LLM unit-test generation and assessment benchmark.

Why relevant:

AgoneTest / Classes2Test is highly aligned with this project because it focuses on Java unit-test generation assessment and includes quality dimensions such as mutation score and test smells.

Project pain point solved:

Prevents pass-rate-only evaluation. Pushes the project toward stronger generated-test quality assessment.

Immediate use:

Methodology first, dataset later.

Candidate task type:

* class-level Java test generation
* existing human test comparison
* mutation score evaluation
* test smell analysis

Required metadata:

* project
* class under test
* mapped test class
* test framework
* build command
* mutation command if available
* source/test pair provenance

Risks:

* full dataset may be too large
* build reproducibility must be verified
* licensing and download workflow need review
* mutation/test smell tooling should not be implemented before `run_kind`

Recommended action:

Create a feasibility note before data integration.

Status:

Later dataset, immediate knowledge reference.

---

## 3.4 Microsoft Methods2Test

Category:

Large-scale focal method to test case dataset.

Why relevant:

Methods2Test provides a large mapping between Java focal methods and JUnit tests. It is useful for learning test patterns and building retrieval examples.

Project pain point solved:

Helps future context builders avoid shallow or hallucinated tests by retrieving real human-written method-test patterns.

Immediate use:

No full integration.

Candidate task type:

* test pattern mining
* few-shot example retrieval
* fake-green rule design
* generated-test structure comparison

Required metadata:

* focal method
* test method
* project
* license
* original repo
* commit or provenance if available

Risks:

* too large for immediate use
* may not be directly executable
* may not include full project context
* can become a pattern source rather than a benchmark

Recommended action:

Use small samples only after quality-gate design stabilizes.

Status:

Later / knowledge source.

---

# 4. Real-Bug Benchmark Sources

## 4.1 Defects4J

Category:

Java real-bug benchmark.

Why relevant:

Defects4J is the most practical first real-bug benchmark for this project because it provides buggy/fixed versions and reproducible test infrastructure for Java projects.

Project pain point solved:

Moves evaluation from “does the generated test pass?” to “can the generated test expose a real regression?”

Immediate use:

Not yet. Use after foundation hardening.

Candidate task type:

* generate regression test
* fail on buggy version
* pass on fixed version
* compare with existing failing test
* evaluate generated test as bug-revealing evidence

Required metadata:

* Defects4J project
* bug id
* buggy version
* fixed version
* Java version
* reproduction command
* failing test
* fixed-version verification command
* artifact path
* reproducibility status

Risks:

* some cases may be hard to reproduce under modern Java
* some cases may have under-specified test suites
* environment setup can be heavy
* not all bugs are suitable for generated-test evaluation

Recommended pilot:

3 bugs only.

Selection preference:

* Maven-friendly
* small project
* clear failing test
* stable Java version
* avoid complex legacy build systems initially

Status:

Pilot after `run_kind` and artifact spec.

---

## 4.2 GitBug-Java

Category:

Recent Java real-bug benchmark.

Why relevant:

GitBug-Java focuses on more recent Java bugs and therefore can reduce benchmark contamination risk compared with older public benchmarks.

Project pain point solved:

Helps address model-training contamination and benchmark freshness.

Immediate use:

No.

Candidate task type:

* bug reproduction
* fail-to-pass test generation
* CI-log-based failure analysis
* recent-bug benchmark comparison

Required metadata:

* repo
* issue/commit reference
* bug-fix commit
* GitHub Action logs if available
* reproduction command
* Java version
* build tool
* artifact path
* contamination risk

Risks:

* CI logs may be noisy
* reproduction may require original CI environment
* bug isolation may be less clean than Defects4J
* requires stronger artifact handling

Recommended path:

Use only after a Defects4J pilot succeeds.

Status:

Later.

---

## 4.3 Bugs.jar

Category:

Large Java bug dataset.

Why relevant:

Bugs.jar provides a larger set of real Java bugs and patches across multiple Java projects.

Project pain point solved:

Useful for scaling real-bug evaluation after the harness proves itself on Defects4J.

Immediate use:

No.

Candidate task type:

* real-bug regression test generation
* generated-test bug exposure
* cross-project robustness testing

Required metadata:

* project
* bug id
* buggy/fixed versions
* build command
* test command
* Java version
* known failing tests
* artifact path

Risks:

* larger scope
* heavier integration
* not suitable before small pilot
* may introduce environment complexity

Status:

Later.

---

## 4.4 Bears

Category:

CI fail/pass Java bug benchmark.

Why relevant:

Bears is based on CI fail/pass pairs from Java projects, often using Maven. It resembles real engineering failures more than synthetic bugs.

Project pain point solved:

Can evaluate whether generated tests and agent workflows work under CI-like regression conditions.

Immediate use:

No.

Candidate task type:

* fail/pass pair analysis
* regression test generation
* CI failure reproduction

Required metadata:

* project
* failed build
* passed build
* Maven command
* CI environment
* Java version
* artifact path

Risks:

* Travis-era environment may be stale
* reproduction cost may be high
* failures may include non-test issues

Status:

Later.

---

## 4.5 BugSwarm

Category:

Large-scale CI fail/pass artifacts.

Why relevant:

BugSwarm provides containerized fail/pass CI artifacts across Java and Python. It is valuable for realistic CI failure evaluation.

Project pain point solved:

Useful for long-term agent benchmark and CI failure handling.

Immediate use:

No.

Candidate task type:

* CI failure reproduction
* test repair
* environment-aware benchmark
* agent issue debugging

Required metadata:

* artifact id
* language
* Docker image
* fail/pass build references
* test command
* artifact path

Risks:

* heavy Docker workflow
* broad failure types
* not focused only on unit-test generation
* high setup cost

Status:

Defer.

---

## 4.6 QuixBugs

Category:

Small Java/Python program repair benchmark.

Why relevant:

QuixBugs is small and fast, useful for harness smoke tests and demo scenarios.

Project pain point solved:

Provides quick controlled checks for fail/pass infrastructure.

Immediate use:

Optional smoke only.

Candidate task type:

* harness smoke
* generated regression test demo
* quick fail/pass verification

Risks:

* too toy-like
* algorithmic rather than real project
* should not support headline model-quality claims

Status:

Smoke only.

---

## 4.7 IntroClassJava

Category:

Small Java buggy program benchmark.

Why relevant:

IntroClassJava can provide small JUnit-based buggy programs for fast harness checks.

Project pain point solved:

Useful for small local regression checks.

Immediate use:

Optional smoke only.

Risks:

* educational/small programs
* not representative of production Java Maven projects
* not suitable for strong claims

Status:

Smoke only.

---

# 5. Issue and Fail-to-Pass Benchmarks

## 5.1 SWT-Bench

Category:

Issue-to-regression-test benchmark.

Why relevant:

SWT-Bench focuses on generating a test that fails before the fix and passes after the fix. This is exactly the strongest form of generated-test evidence.

Project pain point solved:

Defines a stronger oracle than “generated test passes.”

Immediate use:

No, because it is not the current Java Maven mainline.

Project implication:

Adopt the fail-to-pass principle:

```text
Best regression evidence = fails on buggy version and passes on fixed version.
```

Status:

Methodology reference now, possible later extension.

---

## 5.2 SWE-bench-java

Category:

Java issue-resolving benchmark.

Why relevant:

SWE-bench-java brings SWE-bench-style issue evaluation to Java. It can inform future agentic software-engineering tasks.

Project pain point solved:

Useful if the project later expands from generated-test evaluation to issue-driven test generation or code-change testing.

Immediate use:

No.

Risks:

* issue resolving is broader than unit-test generation
* Docker/evaluation setup may be heavy
* not suitable before Layer 1 and Layer 2 stabilize

Status:

Later.

---

## 5.3 SWE-bench Multilingual

Category:

Multi-language real issue benchmark.

Why relevant:

Includes Java among multiple languages and can support future cross-language comparison.

Immediate use:

No.

Project implication:

Useful as future roadmap reference only.

Status:

Defer.

---

## 5.4 Multi-SWE-bench

Category:

Large multilingual issue benchmark.

Why relevant:

Multi-SWE-bench includes Java and preserves inference logs, execution logs, trajectories, and results. Its artifact structure is useful as a model for evidence packages.

Project pain point solved:

Shows that serious agent benchmarks preserve more than final pass/fail status.

Immediate use:

Do not integrate data.

Project implication:

Borrow artifact structure ideas:

* prediction
* execution logs
* trajectory
* result
* metadata

Status:

Artifact-design reference.

---

## 5.5 SWE-rebench

Category:

Benchmark freshness / contamination-aware SWE benchmark methodology.

Why relevant:

SWE-rebench emphasizes fresh task collection and contamination-aware evaluation.

Project pain point solved:

Prevents benchmark claims from becoming stale or inflated by training-data leakage.

Immediate use:

No dataset integration.

Project implication:

Benchmark manifests should record:

* source date
* commit SHA
* model version
* prompt version
* run date
* contamination risk
* artifact path

Status:

Policy reference.

---

# 6. Industrial and Tooling References

## 6.1 Meta TestGen-LLM

Category:

Industrial LLM test generation.

Why relevant:

Meta TestGen-LLM demonstrates filter-backed test recommendation, not blind acceptance of generated tests.

Project pain point solved:

Supports this project’s core design: generated tests are candidates and must pass filters before recommendation.

Immediate use:

Methodology.

Project implication:

QualityGate should track:

* build success
* reliable pass
* coverage improvement
* recommendation status
* human acceptance status

Status:

Immediate knowledge source.

---

## 6.2 Meta ACH

Category:

Industrial mutation-guided LLM test generation.

Why relevant:

Meta ACH shows that mutation-guided test generation can target specific uncaught regression risks.

Project pain point solved:

Prevents overreliance on coverage-only quality metrics.

Immediate use:

Document now, implement later.

Project implication:

Add mutation value as a later QualityGate dimension.

Status:

Later implementation.

---

## 6.3 Meta Observation-based TestGen

Category:

Industrial execution-observation-based test generation.

Why relevant:

Execution observations, real object states, and usage patterns can make generated tests more realistic.

Project pain point solved:

Reduces hallucinated setup and unrealistic mocks.

Immediate use:

No implementation.

Project implication:

Future context builder should retrieve existing tests and usage examples.

Status:

Defer.

---

## 6.4 Diffblue

Category:

Commercial Java unit testing agent.

Why relevant:

Diffblue represents enterprise Java unit-test generation as orchestration, not a single prompt. It includes coverage analysis, build fixes, test planning, generation, verification, cleanup, and PR/report preparation.

Project pain point solved:

Supports the idea that this project should focus on orchestration and evaluation, not just generation.

Immediate use:

Product reference.

Project implication:

Possible future pipeline:

```text
scope -> plan -> generate -> execute -> verify -> cleanup -> report
```

Status:

Knowledge reference.

---

## 6.5 JetBrains TestSpark

Category:

Java/Kotlin test-generation tool.

Why relevant:

TestSpark combines LLM-based and traditional search-based generation, including EvoSuite-style local generation.

Project pain point solved:

Supports using traditional generators as baselines rather than comparing only LLM models.

Project implication:

Future baseline experiments can compare:

* LLM
* EvoSuite
* Randoop
* hybrid approaches

Status:

Later.

---

## 6.6 GitHub Next TestPilot

Category:

Early LLM test generation prototype.

Why relevant:

TestPilot is useful as a historical reference for LLM test generation tooling, but not as a main benchmark source.

Project implication:

Do not confuse prototype generation tools with production-grade evaluation harnesses.

Status:

Reference only.

---

# 7. Security and Fuzzing Future Sources

## 7.1 OWASP Benchmark Java

Category:

Java security benchmark.

Why relevant:

OWASP Benchmark Java is useful if the project later evaluates security-oriented generated tests or vulnerability detection.

Immediate use:

No.

Project implication:

Could support future security test candidate evaluation.

Risks:

* servlet/security focus
* not aligned with current JUnit candidate evaluation
* should not distract current phase

Status:

Defer.

---

## 7.2 Google OSS-Fuzz / Jazzer

Category:

Fuzzing / JVM coverage-guided testing.

Why relevant:

Jazzer brings coverage-guided fuzzing to JVM languages and can provide future fault-finding evidence.

Immediate use:

No.

Project implication:

Long-term expansion could combine generated tests with fuzzing-based regression evidence.

Status:

Defer.

---

# 8. Traditional Java Baseline Generators

## 8.1 EvoSuite

Category:

Search-based Java JUnit test generator.

Why relevant:

EvoSuite is a strong classical baseline for Java unit-test generation.

Project pain point solved:

Prevents the project from only comparing LLMs against no baseline.

Candidate comparison:

* LLM vs EvoSuite compile/pass
* LLM vs EvoSuite coverage
* LLM vs EvoSuite mutation score
* LLM vs EvoSuite readability / maintainability
* LLM vs EvoSuite fake-green risk

Status:

Later baseline.

---

## 8.2 Randoop

Category:

Randomized Java unit test generator.

Why relevant:

Randoop is a simple baseline for generated Java tests and distinguishes error-revealing tests from regression tests.

Project pain point solved:

Provides a low-cost non-LLM baseline.

Status:

Later baseline.

---

## 8.3 JaCoCo

Category:

Java coverage tool.

Why relevant:

JaCoCo is appropriate for coverage collection in Maven/JUnit workflows.

Project implication:

Coverage should be reported as evidence, not final acceptance.

Status:

Immediate / already aligned.

---

## 8.4 PIT / Pitest

Category:

Java mutation testing.

Why relevant:

Mutation testing provides stronger test-quality evidence than line coverage alone.

Project implication:

PIT should be considered after:

* `run_kind`
* artifact evidence spec
* stable QualityGate
* Java Maven benchmark pilot

Status:

Later.

---

# 9. Sources Not Recommended for Current Mainline

These may be useful as references but should not be integrated into the current benchmark pipeline.

## 9.1 BugsInPy

Reason to defer:

Python-focused, not Java Maven. Useful only as a Defects4J-like design reference.

## 9.2 BugsJS

Reason to defer:

JavaScript-focused, outside current Java Maven target.

## 9.3 CrashJS

Reason to defer:

Node.js crash reproduction; useful conceptually but not current scope.

## 9.4 ManyBugs / IntroClass

Reason to defer:

C repair benchmarks; useful for APR history but not Java Maven candidate evaluation.

## 9.5 Defects4C

Reason to defer:

C/C++ benchmark; not current project scope.

## 9.6 JavaBench

Reason to defer:

More focused on Java code generation than generated-test candidate evaluation.

---

# 10. Required Benchmark Manifest Schema

Every benchmark case should eventually include the following fields.

```json
{
  "case_id": "string",
  "benchmark_source": "ProjectTest|Defects4J|GitBug-Java|Methods2Test|Custom|Other",
  "source_type": "smoke|real_project|real_bug|issue_reproduction|baseline",
  "language": "java",
  "repo_url": "string",
  "repo_name": "string",
  "commit_sha": "string",
  "module_path": "string",
  "build_tool": "maven|gradle|unknown",
  "java_version": "string",
  "test_framework": "junit4|junit5|testng|unknown",
  "source_file": "string",
  "existing_test_file": "string|null",
  "task_type": "generate_test|improve_test|reproduce_bug|evaluate_candidate",
  "bug_id": "string|null",
  "buggy_commit": "string|null",
  "fixed_commit": "string|null",
  "reproduction_command": "string",
  "verification_command": "string",
  "expected_oracle": "compile_pass|test_pass|fail_to_pass|coverage_delta|mutation_delta",
  "run_kind": "real|fake|dryrun|smoke",
  "model_name": "string|null",
  "prompt_version": "string|null",
  "artifact_path": "string",
  "known_limitations": ["string"],
  "contamination_risk": "low|medium|high|unknown",
  "status": "candidate|verified|excluded"
}
```

Required rule:

Unknown commit SHAs must be recorded as `TODO`, not invented.

---

# 11. Benchmark Source Registry Template

Use this template when adding a new source.

```md
## <Benchmark Name>

Category:
smoke / real_project / real_bug / issue_reproduction / baseline / security / fuzzing

Language:
Java / Python / JavaScript / multi-language

Build system:
Maven / Gradle / Docker / unknown

Why relevant:
Explain the concrete project pain point it helps evaluate.

Immediate use:
immediate / pilot / later / defer

Candidate task type:
generate_test / improve_test / reproduce_bug / evaluate_candidate / baseline_compare

Expected oracle:
compile_pass / test_pass / fail_to_pass / coverage_delta / mutation_delta

Required metadata:
- repo
- commit SHA
- Java version
- build command
- test command
- source type
- run_kind
- artifact path

Risks:
- contamination
- flaky tests
- heavy environment
- not Java
- not Maven
- under-specified tests
- unavailable commit SHA
- unclear license
```

---

# 12. Recommended First 10 Benchmark Cases

Do not implement all sources first. Start with a small controlled set.

## First 10 candidate cases

1. Existing `samples/calc` smoke case
2. Apache Commons Lang simple utility class
3. Apache Commons Lang branch-heavy class
4. Apache Commons CLI parser class
5. Apache Commons CSV parser/format class
6. Apache Commons Text string transformation class
7. ProjectTest Java Maven project #1
8. ProjectTest Java Maven project #2
9. Defects4J bug #1, Maven-friendly
10. Defects4J bug #2 or #3, only after bug #1 is reproducible

Do not start GitBug-Java, Bugs.jar, BugSwarm, or SWE-bench-java until these first cases are stable.

---

# 13. Immediate Backlog

## Immediate

1. Add `docs/benchmark/BENCHMARK_SOURCES.md`.
2. Add `docs/benchmark/BENCHMARK_POLICY.md`.
3. Add or update benchmark manifest schema.
4. Implement P1-T3 `run_kind`.
5. Update `scripts/audit_bench.py` to use schema-based `run_kind`.
6. Add regression test: fake/dryrun/smoke rows must be excluded from real headline metrics.

## Next

1. Create a small ProjectTest Java pilot.
2. Create a 3-bug Defects4J pilot design.
3. Add benchmark source registry.
4. Add artifact evidence spec.
5. Add quality-gate documentation for fail-to-pass evidence.

## Later

1. Add GitBug-Java pilot.
2. Add EvoSuite / Randoop baseline comparison.
3. Add mutation testing via PIT.
4. Add test smell detection.
5. Add SWE-bench-java or Multi-SWE-bench reference experiment.

## Defer

1. BugSwarm full CI artifact integration.
2. OWASP Benchmark Java.
3. OSS-Fuzz / Jazzer.
4. UI automation benchmark.
5. Large-scale real model benchmark runs.

---

# 14. Policy for Future Agents

When adding or modifying benchmark sources:

* Do not download large datasets without human approval.
* Do not run real models without human approval.
* Do not read or print `.env`.
* Do not invent commit SHAs.
* Do not treat smoke runs as real model-quality evidence.
* Do not mix fake/dryrun/smoke with real model headline metrics.
* Do not report a benchmark number unless it can be reproduced from raw artifacts.
* Do not add a benchmark source only because it sounds advanced.
* Prefer small verified pilots over broad unverified integrations.

Current priority:

```text
benchmark hygiene -> run_kind -> schema-based audit -> Layer 1 Java Maven pilot -> Defects4J 3-bug pilot
```

Do not jump directly to:

```text
large-scale model comparison
Defects4J full run
GitBug-Java full integration
SWE-bench-java integration
UI automation expansion
```

---

# 15. One-Sentence Benchmark Strategy

Use small, pinned, reproducible Java Maven benchmarks first; separate fake/dryrun/smoke/real runs with `run_kind`; verify every headline number from raw artifacts; then expand from real-project test generation to real-bug fail-to-pass evaluation.
