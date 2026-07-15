# 54 - Core Freeze and Boundary Reference

> Date: 2026-07-03  
> Nature: design reference and boundary memo.  
> Input: external knowledge note `D:\AI测试新范式综合总结_结合AI评测项目_v2_2026-07-03.md`, reconciled with the current charter and V2 thesis.  
> Status: documentation only. No implementation is implied by this file.

This document records what should be treated as the stable core of TestAgent Lab, what should be
kept as downgraded producer-side support, and what should be rejected as mainline drift.

If this document conflicts with `docs/00_foundation/00_PROJECT_CHARTER.md`,
`docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md`, or the AGENTS/CLAUDE operating guide,
the charter and thesis files win.

## 0. One Sentence

TestAgent Lab is not a better prompt generator. It is an execution-based judge for test
candidates from any producer.

The platform value is:

```text
Candidate
  -> deterministic execution evidence
  -> quality and value signals
  -> review recommendation
  -> badcase memory
  -> reproducible report
```

The product is the judgment layer. Generation is only one upstream producer.

## 1. Why This Boundary Exists

The external knowledge note reaches the same conclusion as the current V2 thesis:

- Industrial AI testing systems do not succeed by single-shot test generation alone.
- The hard part is turning AI-produced test assets into executable, reviewable, explainable,
  comparable, and reusable quality evidence.
- Coverage growth and green execution are necessary signals, not proof of engineering value.
- Badcase memory, quality gates, red lines, and human review boundaries are more important than
  prompt cleverness.

Therefore, the project must keep its center of gravity on candidate evaluation and quality
governance, not on competing as a generic AI test generator.

## 2. Stable Core To Freeze

"Freeze" means the capability is part of the core judgment surface. Future work may harden it,
clarify reports, or fix evidence accuracy, but should avoid semantic churn, broad rewrites, or
producer-specific optimization.

| Core capability | Role in the thesis | Freeze rule |
|---|---|---|
| Repo Import / Maven Judge / Surefire / JaCoCo | Deterministic execution and coverage evidence for Java/Maven unit-test candidates. | Keep as the execution kernel. Prefer correctness, reproducibility, and parser robustness over feature expansion. |
| Candidate Submit | Author-agnostic entry for human, platform, Codex, Copilot, EvoSuite, or other producer output. | Treat as a first-class product boundary. Do not couple it back to the built-in generator. |
| Quality Gate | Detects empty, weak, unsafe, or low-review-value candidates. | Advisory quality judgment only. Never convert gate output into auto-accept. |
| Preflight | Early candidate sanity and red-line screening before full execution. | Keep as judge-side safety. Add rules only when they prevent false trust, oracle risk, or invalid candidate handling. |
| Mutation (gated) | Stronger semantic signal for green-but-empty or weak-oracle tests. | Keep gated off by default. Use only as advisory evidence when explicitly enabled. Do not reroute the product around PIT. |
| Invariant Review | Checks whether declared business invariants are addressed, asserted, and anchored. | Anchoring matters. Model/self-declared invariants do not self-certify value. |
| Mock Smell | Flags over-mocking, real dependency leakage, null stubs, and loose matchers. | Keep as review guidance. A smell is a place to inspect, not a verdict. |
| Badcase Ledger | Stores judged failures and reusable precedent. | Only store and retrieve real records. Do not fabricate precedent or backfill historical data. |
| Review Digest | Consolidates advisory signals into a prioritized human-review checklist. | Keep it as a digest, not a new detector or scorer. |
| Benchmark Manifest | Defines reproducible candidate comparisons and metric slices. | Headline metrics must respect `run_kind`; fake, dryrun, smoke, external, and historical unknown must not pollute real-model headlines. |
| Report | The final evidence chain for review and handoff. | Reports must show command/evidence provenance and keep `conclusion=NEED_HUMAN_REVIEW`. |

These are the "judge kernel plus evidence surface". They should be protected from drift.

## 3. Downgraded Producer-Side Capabilities

These capabilities may remain in the repo because they help produce candidates or make the
platform demoable. They are not the product center.

| Capability | Correct status | Allowed work |
|---|---|---|
| LLM Client | One producer adapter among many. | Maintenance, offline test safety, provider isolation, cost controls. No multi-provider platform as a main goal. |
| Prompt Builder | Producer-side helper. | Only stabilize prompts when needed for demos or bounded experiments. Do not optimize prompt quality as the core metric. |
| Platform Generator | Built-in producer. | Keep useful as a baseline producer. It should emit candidates into the same judge path as everyone else. |
| Compile Repair | Gated auxiliary repair. | Allow only oracle-safe, evidence-preserving repair. Default should not hide candidate failures, especially for external submissions. |
| Context Prompt Tuning | Producer-side context packaging. | Maintain bounded context rules, but do not keep iterating prompt/context versions just to raise built-in pass rate. |

Important distinction:

```text
Oracle-safety / false-trust prevention = may be core.
Pass-rate optimization for our own generator = downgraded.
```

For example, compile repair is acceptable when it prevents unsafe oracle edits or makes a
failure classification clearer. It is not acceptable as a silent mechanism for making a weak
candidate look successful.

## 4. Mainline Drift To Reject

The following directions should not be treated as project mainline:

- Continuing to pile prompt variants.
- Competing on generated test compile/pass rate.
- Building a multi-model provider platform.
- Building complex RAG, knowledge graph, or large agent orchestration as the base system.
- Building a large MCP ecosystem around the project.
- Building a large web backend, enterprise permission system, multi-tenant platform, or task
  management system.
- Auto-accepting, auto-rejecting, auto-merging, or auto-committing candidate tests.

These directions either weaken the candidate-judging thesis or create a different product.

Some can appear later as adapters or sinks, but only if they submit candidates into the same
judge kernel and do not become the core architecture.

## 5. Four Pillars After Freeze

The stable abstraction is the V2 four-pillar model:

| Pillar | Meaning | Current posture |
|---|---|---|
| Candidate | The submitted test asset, independent of author. | Live. Keep strengthening the submit and report path. |
| Provenance | Who produced it and how it arrived. | Live. Advisory only, never a warrant of quality. |
| Badcase | Structured memory of judged failures and precedents. | Live. Retrieval is advisory and evidence-bound. |
| Asset Gate | Whether available assets are sufficient, and which test level is appropriate. | S1-S3D advisory signal and compact carry live; S4A Test-Level Router is report-only live. No executor/API harness. |

The next design frontier is not another generator improvement. It is a bounded closeout audit of
the report-only router plus early API/interface Candidate boundary design. This is a near-term
mainline direction: move the judge beyond unit-test-only candidates without jumping into an API
automation framework.

## 6. Asset Gate Is The Next Core Design

Asset Gate should answer two judge-side questions:

1. Are the assets sufficient for a trustworthy judgment?
2. Should this target be evaluated as unit, API, integration, or manual-oracle-first?

Minimum advisory shape:

```text
AssetSufficiencyReport = {
  code_context: sufficient | partial | missing,
  existing_tests: sufficient | partial | missing,
  business_oracle: sufficient | partial | missing,
  test_data: sufficient | partial | missing,
  api_schema: sufficient | partial | missing,
  db_schema: sufficient | partial | missing,
  external_dependency_mock: sufficient | partial | missing,
  test_level_recommendation: unit | api | integration | manual_oracle_first,
  missing_assets: [...],
  risk_notes: [...]
}
```

Rules:

- Advisory only.
- Does not change `recommendation`, `conclusion`, or `trusted`.
- Does not make model-declared assets trustworthy.
- Does not introduce complex RAG in v1.
- Should feed the review digest as another review signal.

S1-S4A status, 2026-07-04: the advisory signal is implemented as
`review_summary["asset_sufficiency"]`, compact benchmark/ledger carry fields, descriptive
breakdowns, and `review_summary["test_level_router"]`. It uses existing bundle/report facts plus
tiny persisted pipeline asset facts from `ContextSnapshot`; it does not persist source excerpts or
the full snapshot. The router is report-only and owner-gated; this is still not an API harness.

This is the clean bridge from the current Java/Maven unit-test kernel to future API candidate
evaluation without becoming an API automation framework.

## 7. Near-Term API Evaluation Boundary

API/interface testing is a near-term candidate-evaluation direction. It should be designed early
as part of the mainline, while execution remains owner-gated and design-first.

Allowed framing:

```text
API test candidate
  -> isolated execution harness
  -> deterministic response/schema/data evidence
  -> quality signals
  -> badcase ledger
  -> NEED_HUMAN_REVIEW report
```

Disallowed framing:

```text
Build a general API automation framework.
Replace the unit-test judge kernel with an API platform.
Auto-generate and auto-adopt API suites.
Build full data factory / environment orchestration before Asset Gate.
```

Preferred order:

1. Stabilize the current unit-test judge kernel and evidence surface.
2. Close out a bounded audit that Asset Gate / report-only Test-Level Router remains advisory.
3. Design the API/interface Candidate boundary early as a mainline direction: candidate kind,
   input shape, evidence contract, report fields, and asset requirements.
4. Only after that design, choose a minimal API smoke path and executor adapter.
5. Keep every new level owner-gated, advisory, and report-first.

## 8. Decision Filter For Every New Requirement

Before accepting any new feature, ask:

```text
Does this strengthen judging, managing, comparing, or precipitating candidates of any origin?
```

If yes, it may be core or near-core.

If it only improves the built-in generator's compile rate, pass rate, or prompt output quality,
downgrade it unless it fixes an oracle-safety or false-trust red line.

If it requires new dependencies, real model calls, external services, or broad platform work,
stop for explicit approval.

## 9. Evidence Rules

The boundary is also an evidence discipline:

- Never claim a candidate "passes" without judge command evidence.
- Never claim a test has engineering value from coverage alone.
- Never treat a green test as useful without quality-gate and review evidence.
- Never present fake-client output as real-model data.
- Never include `run_kind!="real"` rows in real-model headline metrics.
- Never summarize, read, print, or commit `.env`.
- Never make real model/API calls without explicit user approval and cost disclosure.

Reports and handoffs should prefer this wording:

```text
The candidate compiled/executed under the judge with the following evidence...
The review recommendation is advisory.
The conclusion remains NEED_HUMAN_REVIEW.
```

Avoid this wording:

```text
The AI generated a valuable test.
The test is accepted.
Coverage increased, so this is good.
The producer is trustworthy because it is Codex/Copilot/human.
```

## 10. Benchmark And Metrics Boundary

Benchmark data should compare candidate value signals, not celebrate a generator.

Useful metrics:

- Compile result.
- Execution result.
- Coverage delta.
- Quality gate issues.
- Oracle-strength structural estimate.
- Mutation signal when gated on.
- Invariant review findings.
- Mock smell findings.
- Badcase similarity and recurrence.
- Review digest flags.
- Provenance/run_kind split.

Risky metrics when used as headlines:

- Built-in generator pass rate alone.
- Coverage delta alone.
- LLM-judged quality score.
- Number of generated tests.
- Provider leaderboard without identical targets and evidence schema.

Default headline views must remain honest about `run_kind`. Historical data with missing
`run_kind` remains read-only and labeled as heuristic/unknown.

### 10.1 Real-World Landing Validation Line

Future benchmark/report/review designs should use
`docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md` as the metric contract for proving real
project value.

Core validation metrics:

| Metric | What it proves | Evidence requirement |
|---|---|---|
| First Compile Pass Rate | Candidate can compile on first judged execution. | Maven/Surefire first-run evidence; repair cannot count as first pass. |
| First Test Pass Rate | Candidate executes and its own tests pass. | First-run `gen_outcome == PASS`; green is not value proof. |
| Usable Test Rate | Human ultimately keeps the test. | Human disposition labels; never inferred from recommendation. |
| Weak Assertion Detection Rate | Platform catches fake-green / weak-oracle tests. | Quality/mutation signals plus labeled weak-test set for recall/precision. |
| Defect Discovery Rate | Candidate exposes real or seeded defects. | Pinned real-bug or seeded-defect verifier; `TEST_FAILURE` alone is not enough. |
| Human Edit Count | Effort from candidate to usable test. | Human review/edit annotations. |
| Human Handling Time | Human review and repair cost. | Review timestamps, not job runtime. |
| Diagnosis Time | Time from failure to root-cause understanding. | Failure surfaced timestamp plus human/verifier RCA timestamp. |
| Misjudgment Rate | Whether platform guidance misleads humans. | Human/golden labels compared with platform signals. |

Rule: separate automated judge evidence from human/golden validation. Automated compile/pass and
weak-structure signals may be reported earlier with `run_kind` hygiene; usable-test rate, defect
discovery, human effort, diagnosis time, and misjudgment rate must not be headlined until their
labels/verifiers exist.

V1 status, 2026-07-12: the automated evidence line is implemented as
`app/benchmark/validation_line.py` and rendered in benchmark markdown as RAW plus HEADLINE(real)
sections. It changes no `aggregate(...)` keys, schemas, ledger fields, recommendations,
conclusions, trust, or digest severity.

S5C status, 2026-07-15: human review and RCA label language is drafted in
`docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`, and the V1 pure validator is live in
`app/review/human_labels.py`. It validates disposition, root-cause, fix-note, timestamp,
manual-edit, and misjudgment labels and projects compact metric facts; it does not implement
storage, indexes, backfill, auto-RCA, LLM judging, or any verdict change.

S6C status, 2026-07-15: the minimal S7 API/interface smoke path is selected in
`docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`: start with `junit_api_candidate` on the
existing Maven/Surefire boundary. The V1 `api_evidence` validator is live in
`app/report/api_evidence.py`; it validates compact report-only API facts and redaction rules, but
does not wire runtime reports, add candidate kinds, start executors, install tools, change
benchmark/ledger schemas, or change verdict semantics.

S7A status, 2026-07-15: report-only wiring for `junit_api_candidate` is live in
`app/report/generation_report.py` and specified in
`docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`. A generation bundle may now
attach validated `review_summary["api_evidence"]` when it explicitly carries
`candidate_kind="junit_api_candidate"` or `api_evidence`; ordinary unit bundles remain unchanged.
This still does not implement a submit API change, executor, dependency, benchmark/ledger schema
change, digest severity change, or verdict change.

S7B status, 2026-07-16: submit API exposure of `candidate_kind` and compact `api_evidence` is
designed in `docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`. The design
keeps existing submit callers stable, accepts API evidence only for explicit
`junit_api_candidate`, requires public-boundary redaction/authority validation, and still does not
implement an endpoint change, executor, dependency, benchmark/ledger schema change, digest severity
change, or verdict change.

## 11. Skill/SOP Reference Boundary

The external knowledge notes recommend Skill-style SOPs and Agent/Harness evaluation templates.
In this repo, the right interpretation is:

- Skill is a reusable evaluation procedure, not a new product surface.
- A useful Skill encodes steps, red lines, evidence, and human fallback.
- Skill docs should not smuggle in UI automation, complex RAG, or provider-platform scope.
- Skill docs should help use the judge correctly: trigger, inputs, workflow, evidence, red lines,
  output, and fallback.
- Prompt-written evaluator logic may help design a harness, but it must not replace deterministic
  judge invariants or become a runtime authority.

Candidate Skill candidates, if created later:

| Skill | Scope |
|---|---|
| `unit-test-eval` | Run the candidate through the Java/Maven judge and report evidence. |
| `failure-triage` | Classify compile/runtime/quality failures using real evidence. |
| `badcase-memory` | Retrieve real ledger precedents as advisory context. |
| `test-quality-review` | Guide human review of oracle, invariant, mock, flaky, and maintainability risks. |
| `eval-report` | Produce an audit-grade report with `NEED_HUMAN_REVIEW`. |
| `ci-pr-handoff` | Prepare local verification evidence and PR handoff without pushing or merging. |

These should describe how to use the judge. They should not become a new generator roadmap.

For the detailed external lesson mapping, see
`docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md`. Its lessons are knowledge, not automatic tasks.

## 12. Current Core Map

The current project can be summarized as:

```text
Frozen core:
  Repo Import / Maven Judge / Surefire / JaCoCo
  Candidate Submit
  Quality Gate
  Preflight
  Mutation (gated)
  Invariant Review
  Mock Smell
  Badcase Ledger
  Review Digest
  Benchmark Manifest
  Report

Downgraded support:
  LLM Client
  Prompt Builder
  Platform Generator
  Compile Repair
  Context Prompt Tuning

Rejected mainline:
  prompt pile-up
  generation pass-rate race
  multi-model provider platform
  complex RAG
  large MCP system
  large web backend
  automatic adoption / automatic warehouse entry
```

This map should be used as the quick boundary check before opening new design or implementation
work.

## 13. Definition Of Done For Future Designs

Any future design that claims to be on-thesis should explicitly state:

1. Which pillar it strengthens: Candidate, Provenance, Badcase, or Asset Gate.
2. Which deterministic evidence it adds or preserves.
3. How it keeps `conclusion=NEED_HUMAN_REVIEW` and `trusted=False`.
4. How it prevents producer self-certification.
5. How it handles fake/dryrun/smoke/external/historical unknown data.
6. Whether it needs new dependencies, model calls, network access, or cost approval.
7. Which existing report or digest field will surface the signal.
8. Which tests prove that no auto-accept or headline metric drift occurred.
9. If it mentions an external asset, the asset's intake shape from
   `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`, the project artifact it affects, and the red
   lines that prevent copying, vendoring, or premature execution.

If a design cannot answer these, it is probably not ready to implement.

Recommended external asset block:

```text
External Asset Mapping:
- asset:
- intake shape:
- project artifact:
- expected evidence:
- red lines:
```

## 14. Final Boundary

The project should be legible as:

> A trustworthy judge and evidence ledger for AI-era test candidates.

It should not become:

> A prompt playground, provider hub, RAG platform, automation suite, or auto-merge bot.

The strongest next move is to close out the S4A router audit and start S6 API/interface Candidate
boundary design as the preferred mainline direction, not another round of generation tuning or
broad external-tool ingestion.
