# 07_SOURCE_NOTES.md

# Source-Derived Engineering Notes for TestAgent Lab

> Purpose: This document distills engineering lessons from large-company AI testing practices, open-source research projects, public docs, and technical blogs. It is project guidance for Coding Agents and human reviewers. It is **not** a runtime RAG knowledge base in Phase 1.

---

## 1. Core Positioning

TestAgent Lab is not a traditional unit-test platform.

Traditional test platforms execute existing tests, collect reports, and enforce CI gates. TestAgent Lab focuses on the harder question:

> Can AI-generated unit tests become compileable, executable, measurable, repairable, and reviewable engineering assets?

Therefore, the first milestone is not “AI generates tests”. The first milestone is:

> Build the judge before the generator.

---

## 2. Source Families Reviewed

The following source families inform this project:

1. Kuaishou intelligent unit-test generation practice: adoption improved through workflow evolution from prompt exploration to repair loops and rule/knowledge-driven generation.
2. Uber AutoCover paper: production-scale LLM test generation requires preparation, generation, execution, validation, repair, build integration, and quality gates.
3. GitHub Copilot testing docs: basic test generation works with explicit prompts, existing test context, and human review; complex cases need decomposition and verification.
4. Microsoft TiCoder: tests can formalize user intent and help rank/prune generated code.
5. Microsoft TestExplora: repository-level test-generation evaluation should use realistic repos, executable benchmarks, and Fail-to-Pass style evidence rather than text-only outputs.
6. Airbnb LLM-driven test migration: scalable AI code/test transformation needs step-based validation, retry loops, rich relevant context, and systematic long-tail failure analysis.
7. HuoLaLa UI self-healing practice: AI testing systems need diagnosis, structured actions, baselines, and feedback loops; however UI self-healing is deferred from Phase 1.

---

## 3. Non-Negotiable Principles

### P1. Judge first, generator second

Before any LLM-generated test is accepted, the platform must be able to:

- import a Git repository;
- detect a Maven project;
- execute `mvn test`;
- parse Surefire reports;
- parse JaCoCo coverage;
- store execution logs;
- expose a report API.

Phase 1 must not call an LLM.

### P2. Treat AI output as untrusted code

AI-generated tests are not assets until they pass engineering checks.

A generated test must be rejected or marked for human review if it:

- does not compile;
- does not execute;
- modifies production code;
- deletes existing tests;
- lowers coverage;
- contains no meaningful assertion;
- relies only on weak assertions such as `assertNotNull`;
- asserts internal implementation details instead of externally observable behavior;
- introduces unstable behavior such as sleeps, randomness, external I/O, or environment-dependent state.

### P3. Coverage is necessary but insufficient

Coverage increase is a useful signal, but not proof of value.

A test is valuable only when it combines:

- executable behavior;
- coverage or scenario signal;
- meaningful assertions;
- stable oracle;
- limited mocking;
- reviewable patch.

### P4. Context must be bounded and relevant

Do not feed the whole repository to the model.

Preferred context order:

1. target method source;
2. target class fields and constructors;
3. direct method signatures and imports;
4. nearby existing tests;
5. project test conventions;
6. Maven dependency summary;
7. previous failure logs;
8. active rules.

If required context is missing, fail explicitly. Do not let the model invent dependencies, constructors, return values, or imports.

### P5. Repair must be minimal and reversible

Every repair attempt must:

- modify only generated test files;
- preserve production code;
- produce a diff;
- be traceable to a failure type;
- have a maximum retry count;
- stop after 3 failed rounds.

Do not repair by weakening the oracle.

### P6. Human review remains the final gate

The platform outputs one of:

- `ACCEPT`
- `REJECT`
- `NEED_HUMAN_REVIEW`

Uncertain cases must default to `NEED_HUMAN_REVIEW`, not forced acceptance.

---

## 4. What Large-Company Practices Actually Teach

### 4.1 Kuaishou unit-test generation: the problem is usability, not generation

Key lessons:

- Early LLM-generated unit tests fail because of missing code context, import hallucination, compile errors, runtime errors, and shallow scenario coverage.
- Adoption improves only after introducing execution feedback, multi-round repair, better context, grouping, and rule/knowledge recall.
- For a personal MVP, do not copy the final “no-human-intervention入库” target. Copy only the smallest reliable loop:

```text
Generate -> Execute -> Diagnose -> Repair -> Validate -> Report
```

Phase 1 should implement only the judge side of this loop.

### 4.2 Uber AutoCover: general coding agents are insufficient without build integration

Key lessons:

- General IDE agents may write plausible tests, but fail when they cannot invoke builds, discover generated artifacts, resolve mocks, or enforce repository conventions.
- The durable pattern is agent specialization:

```text
Preparer -> Generator -> Executor -> Validator -> Fixer
```

- For this project, Phase 1 implements only the deterministic substrate:

```text
Repository -> Build -> Test -> Coverage -> Report
```

Generator and Fixer come later.

### 4.3 GitHub Copilot docs: simple generation is not enough for complex code

Key lessons:

- Prompt specificity matters: ask for edge cases, exception handling, and data validation explicitly.
- Existing nearby test files improve consistency with project conventions.
- Generated tests must still be run and reviewed.

Project rule:

> When Phase 2 begins, Generator Agent must use nearby existing tests as style context whenever available.

### 4.4 TiCoder: tests help formalize intent

Key lessons:

- Tests can act as partial specifications.
- User feedback on tests can prune bad code suggestions and improve intent alignment.

Project implication:

> The report page should make tests reviewable. Human feedback should later become training data for rules and badcases.

### 4.5 TestExplora: evaluation must be repository-level and executable

Key lessons:

- Text-only evaluation is weak.
- Useful evaluation should run against real repositories and executable test tasks.
- Fail-to-Pass style evidence is stronger than “looks correct”.

Project implication:

> The benchmark must include public Maven repositories and must report build/test/coverage outcomes, not just generated code samples.

### 4.6 Airbnb test migration: pipeline beats one-shot prompting

Key lessons:

- Break transformation into steps.
- Validate each step before moving forward.
- Use retry loops with validation feedback.
- Use relevant neighboring files and examples as context.
- Analyze failure clusters systematically instead of debugging one file forever.

Project implication:

> Each task must persist step status, logs, failures, patch history, and retry count.

### 4.7 UI self-healing practices: defer high-complexity domains

UI self-healing needs screenshots, OCR, DOM trees, element profiles, pop-up taxonomies, device baselines, and multimodal reasoning.

Project implication:

> UI automation and self-healing are deferred. They are not Phase 1 or Phase 2.

---

## 5. Phase Mapping

### Phase 1: Judge Field

Allowed:

- Git import;
- workspace management;
- Maven detection;
- command runner;
- `mvn test` execution;
- Surefire parsing;
- JaCoCo parsing;
- logs;
- report API.

Forbidden:

- LLM calls;
- Generator Agent;
- Fixer Agent;
- RAG;
- knowledge graph;
- multi-language support;
- Gradle;
- IDE plugin;
- auto PR;
- UI automation.

### Phase 2: Minimal Generator

Allowed after Phase 1 passes:

- target class/method selection;
- bounded context collection;
- independent `*AiGeneratedTest.java` generation;
- execute generated test;
- coverage comparison.

Still forbidden:

- modifying production code;
- modifying existing tests;
- auto merge;
- complex RAG.

### Phase 3: Repair Loop

Allowed:

- failure classification;
- limited Fixer Agent;
- maximum 3 repair rounds;
- patch history;
- badcase storage.

Fixable categories:

- missing imports;
- symbol not found;
- constructor mismatch;
- type mismatch;
- Mockito stubbing error;
- assertion failure;
- test data construction issue.

### Phase 4: Quality Gate

Allowed:

- assertion quality checks;
- production-code modification checks;
- coverage comparison;
- weak assertion detection;
- accept/reject/human-review recommendation.

### Phase 5: Benchmark

Required:

- at least 3 public Java Maven repositories;
- at least 5 target methods per repo;
- report success and failure cases;
- no success-only demo.

---

## 6. Rules for Coding Agents

Coding Agents must follow these rules:

1. Read `docs/00_PROJECT_CHARTER.md` before every major task.
2. Read this file before making scope decisions.
3. Do not start a later phase before the current phase is accepted.
4. Do not introduce LLM calls before Phase 2.
5. Do not implement runtime RAG in Phase 1.
6. Do not add new languages or Gradle support in Phase 1.
7. Do not implement front-end polish before judge-field APIs work.
8. Do not modify production code in target repositories.
9. Do not skip execution because generated code “looks correct”.
10. Do not silently swallow errors.
11. Do not fake build/test/coverage results.
12. Do not commit secrets, tokens, `.env`, workspaces, logs, or generated repo contents.

---

## 7. Anti-Patterns

Avoid these patterns:

### A1. Building a platform shell before the judge works

Bad:

```text
Dashboard -> user system -> role system -> settings -> beautiful UI
```

Good:

```text
Git clone -> mvn test -> Surefire -> JaCoCo -> report
```

### A2. Letting the LLM become the validator

Bad:

```text
Model says the test is good.
```

Good:

```text
Maven compiles it.
JUnit executes it.
JaCoCo measures it.
Validator checks assertions and patch boundaries.
```

### A3. Expanding to UI/API/full testing too early

Bad:

```text
Unit + API + UI + PRD + RAG + knowledge graph in MVP.
```

Good:

```text
Java Maven unit-test judge first.
```

### A4. Hiding failures

Bad:

```text
Only show success demos.
```

Good:

```text
Show error type distribution and badcases.
```

### A5. Repairing by weakening tests

Bad:

```text
Remove assertion until test passes.
```

Good:

```text
Fix import/type/mock/data construction while preserving meaningful behavior validation.
```

---

## 8. Minimal Benchmark Template

Each benchmark task should record:

```text
repo_name:
git_url:
commit_hash:
target_class:
target_method:
baseline_build_status:
baseline_test_status:
baseline_coverage:
generation_status:
compile_status:
execution_status:
coverage_after:
coverage_delta:
repair_rounds:
failure_type:
validator_result:
human_review_note:
```

Aggregate metrics:

```text
total_tasks:
buildable_repos:
generation_success_rate:
compile_pass_rate:
test_pass_rate:
coverage_improvement_rate:
average_repair_rounds:
accept_rate:
need_human_review_rate:
reject_rate:
top_failure_types:
average_runtime:
```

---

## 9. Recommended One-Line Project Narrative

> TestAgent Lab is an AI unit-test generation judge field: it first builds the deterministic engineering loop for importing Java Maven repositories, running tests, collecting coverage, and reporting results; only after that does it introduce LLM-based generation, repair, and quality gates, so AI-generated tests become reviewable engineering assets rather than unverified text.

---

## 10. Current Action

The next implementation task must remain:

```text
Phase 1 T02: Project Import + Git Clone + Workspace Management
```

Do not start Phase 2.
