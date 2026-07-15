# Minimal Judge Contract

> Date: 2026-07-11  
> Status: S6 design with the first pure JudgeEvidence projection implemented. No executor,
> dependency, schema discovery, candidate-kind implementation, or report-field migration is
> implied.

## 0. Purpose

This design tightens the "unified exam bag / proctor / evidence / scorecard" idea into the
smallest useful judge contract.

The goal is not a new framework. The goal is a thin contract that lets the current Java/Maven unit
judge and the next API/interface candidate evaluation speak the same evidence language:

```text
JudgeCase -> JudgeRunner -> JudgeEvidence -> JudgeReport
```

Current implementation names stay intact. This document defines vocabulary and boundaries, not a
repo-wide rename.

## 1. Anti-Abstraction Rule

Do not trade tool sprawl for abstraction sprawl.

Allowed:

- describe the minimum common contract;
- map each contract piece to current code;
- leave future API/interface fields as optional design fields;
- use existing report, benchmark, and ledger surfaces when possible.

Not allowed:

- registry/plugin framework;
- workflow engine;
- generic runner orchestration;
- dynamic provider platform;
- broad interface hierarchy;
- renaming `submit_candidate`, `generation_report`, `BenchCaseResult`, or `JudgedRecord` just to
  sound more general.

Every field must satisfy at least one of:

```text
used by current Java/Maven judge
needed by the next API/interface smoke design
needed to preserve a red-line invariant
```

## 2. Contract Terms

| Contract term | Plain meaning | Current mapping | Future API/interface mapping |
|---|---|---|---|
| `JudgeCase` | The exam bag: candidate + target + required assets + provenance. | `submit_candidate` request plus generation bundle fields: `target`, `result`, `producer_id`, `producer_meta`, `asset_facts`, `run_kind`. | `api_schema_candidate`, `api_collection_candidate`, or `junit_api_candidate` input with schema/collection/base URL/env/mock requirements. |
| `JudgeRunner` | The proctor: isolated execution boundary. | `write_generated_test` + `execute_generated_test` + Maven/Surefire + JaCoCo compare. | One owner-approved runner adapter later, such as Schemathesis or Newman, with explicit timeout/isolation/log capture. |
| `JudgeEvidence` | The evidence: deterministic facts, not opinions. | `GenExecResult`, coverage delta, preflight result, quality gate, asset sufficiency, router output. | Request/response/status/schema/assertion/env/mock facts, plus runner command/log path. |
| `JudgeReport` | The scorecard: human-review artifact. | `assemble_generation_report(...)` output with `NEED_HUMAN_REVIEW`, `trusted=False`, review digest. | Same report discipline with API evidence fields added only after design approval. |

These names are design handles. Only `JudgeEvidence` currently has a small projection helper
(`app/report/judge_evidence.py`) because it reduces S6/S7 report-design risk without changing the
runner or canonical report schema.

## 3. Minimal `JudgeCase`

Required now:

```text
case_id:
candidate_kind: junit_unit_candidate
target:
  repo_dir | repo_url/ref if benchmarked
  target_class
  target_method?
candidate_artifact:
  test_source
provenance:
  producer_id
  producer_meta?
  run_kind
asset_facts:
  compact facts only
owner_gate:
  required for non-unit candidate kinds
```

Future optional fields for API/interface:

```text
api_schema_ref?
api_collection_ref?
base_url_ref?
auth_requirement?
fixture_requirement?
mock_requirement?
service_start_requirement?
```

Rules:

- `candidate_kind` is descriptive until implemented; it must not trigger an executor by itself.
- Producer identity is context, never quality proof.
- `run_kind="external"` remains excluded from real-model headline metrics.
- Do not persist full source snapshots, `.env`, credentials, schemas, databases, or service dumps
  as part of the first contract.

## 4. Minimal `JudgeRunner`

Current unit runner boundary:

```text
input: JudgeCase(junit_unit_candidate)
steps:
  preflight
  write candidate test
  Maven/Surefire execution
  JaCoCo coverage compare
output: JudgeEvidence
```

Future API/interface runner boundary:

```text
input: JudgeCase(api_schema_candidate | api_collection_candidate | junit_api_candidate)
steps:
  validate required assets
  execute exactly one approved runner command
  collect deterministic logs and response evidence
output: JudgeEvidence
```

Runner invariants:

- no production-code edits;
- no oracle rewrite;
- no credential discovery;
- no `.env` reads;
- no network/model/API cost without explicit approval;
- timeout and workspace isolation are part of the runner contract;
- runner output cannot set `trusted=True` or auto-accept.

## 5. Minimal `JudgeEvidence`

Common fields:

```text
runner:
  tool:
  command_summary:
  started_at?
  duration_ms?
  log_path?
outcome:
  compiled?
  executed?
  passed?
  failure_type?
quality:
  quality_gate_status?
  blockers?
  warnings?
assets:
  asset_sufficiency?
  test_level_router?
provenance:
  producer_id?
  run_kind?
```

Current Java/Maven evidence maps to:

```text
compile/build outcome -> outcome.compiled / failure_type
Surefire result       -> outcome.executed / passed / counts
JaCoCo compare        -> coverage_delta
preflight             -> quality/pre-execution safety facts
Asset Gate            -> assets.asset_sufficiency
router                -> assets.test_level_router
```

Future API/interface evidence may add:

```text
api:
  request_count?
  response_status_summary?
  schema_failures?
  assertion_failures?
  auth_failures?
  fixture_failures?
  mock_misses?
  service_start_failure?
```

Rules:

- evidence is fact-only;
- coverage up is not value proof;
- green execution is not value proof;
- schema conformance is not business correctness proof;
- missing fixture/mock/schema should route to review, not auto-fail or auto-accept.

## 6. Minimal `JudgeReport`

Current report remains the canonical scorecard:

```text
app.report.generation_report.assemble_generation_report(...)
```

Required invariant output:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
review_recommendation = advisory
review_summary.digest = advisory
```

For API/interface later, prefer extending `review_summary` with a compact API evidence block
rather than creating a separate report type immediately.

Do not add API/interface rows to real-model unit-test headline metrics until there is a separate
headline policy.

## 7. First Implementation Slice (Live)

Implemented on 2026-07-11:

```text
app/report/judge_evidence.py
  build_judge_evidence_from_report(...)
  build_judge_evidence_from_generation(...)

tests/test_judge_evidence.py
  proves generation-bundle projection
  proves failure remains evidence, not verdict
  proves full patch/test source is not copied into the evidence view
```

The helper is intentionally a projection layer:

- it does not alter `assemble_generation_report(...)` output;
- it does not change benchmark schema, ledger schema, digest severity, recommendation,
  `conclusion`, or `trusted`;
- it does not launch an executor;
- it does not add API/interface candidate kinds.

Next S6B work should use this helper as the evidence vocabulary anchor when designing a compact API
report block.

## 8. External Asset Mapping

External assets are not required for this contract, but the first API/interface smoke design may
consult:

| Asset | Intake shape | Project artifact | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future API smoke manifest | pin URL/commit; do not vendor source |
| Schemathesis | `executor_adapter` + `readme_audit` | future `api_schema_candidate` runner design | no install/execution before owner-approved S7 design |
| Newman | `executor_adapter` + `readme_audit` | future `api_collection_candidate` runner design | no install/execution before owner-approved S7 design |
| WireMock/Testcontainers | `isolation_support` + `readme_audit` | future API/integration Asset Gate note | no Docker/service orchestration in S6 |

No external repo has been read, cloned, copied, or implemented by this document.

## 9. Open Questions For S6A/S6B

```text
candidate_kind names:
  junit_unit_candidate
  junit_api_candidate
  api_schema_candidate
  api_collection_candidate

minimum API evidence:
  request/response summary?
  schema failures?
  assertion failures?
  service/env/fixture/mock status?

report placement:
  review_summary["api_evidence"]?
  review_summary["asset_sufficiency"] extension?
  separate compact block?

benchmark policy:
  separate API smoke headline?
  no aggregate change until S7?

ledger policy:
  compact failure facts only?
  no signature changes until API failure taxonomy is designed?
```

## 10. Definition Of Done For This Design

This design is ready to guide the next step only if:

- it keeps the current Java/Maven judge as the kernel;
- it does not require code changes by itself;
- it does not introduce a general plugin/runner framework;
- it makes API/interface candidate evaluation easier to design;
- it keeps `NEED_HUMAN_REVIEW` and `trusted=False`;
- it maps any external asset to an intake shape;
- it leaves executor work owner-gated.
