# API Candidate Boundary Design

> Date: 2026-07-11  
> Status: S6A design. Documentation only; no candidate-kind implementation, executor,
> dependency, schema discovery, service discovery, benchmark schema change, or ledger schema
> change is implied.

## 0. Purpose

This document refines `01_MINIMAL_JUDGE_CONTRACT.md` into the smallest API/interface candidate
boundary.

The project should accept more kinds of test candidates over time, but every candidate must still
enter the same judge posture:

```text
candidate input -> isolated execution evidence -> advisory signals -> digest -> ledger -> report
```

The boundary here is not an API automation framework. It is a submission and evidence contract for
future API/interface candidates.

## 1. Current Anchor

Current live path:

```text
submit_candidate
  -> run_external_candidate
  -> generation bundle
  -> preflight/write/execute/coverage
  -> assemble_generation_report(...)
  -> NEED_HUMAN_REVIEW, trusted=False
```

S6A must preserve this. The existing Java/Maven unit candidate remains the only implemented
candidate kind.

## 2. Candidate Kind Vocabulary

Use these names as design vocabulary only until an owner-approved code slice implements them:

| Candidate kind | Meaning | Earliest posture |
|---|---|---|
| `junit_unit_candidate` | A Java/JUnit test source targeting a class/method. | Live behavior, not yet named this way in code. |
| `junit_api_candidate` | A Java/JUnit test source that exercises HTTP/API behavior, for example RestAssured/WebTestClient-style tests. | Future design; likely easiest bridge from current Maven runner. |
| `api_schema_candidate` | API tests derived from or expressed against an OpenAPI/GraphQL schema. | Future S7 smoke candidate; executor adapter needed. |
| `api_collection_candidate` | Postman/Newman-style collection or request set. | Future S7 smoke candidate; executor adapter needed. |
| `integration_flow_candidate` | Multi-step service/database/message flow candidate. | Later; requires fixture/env design first. |

Do not add `ui_candidate`, `performance_candidate`, `security_scan_candidate`, or broad workflow
candidate kinds under S6A.

## 3. Minimal Input Shapes

### 3.1 `junit_unit_candidate`

Current implemented shape, expressed in contract terms:

```text
candidate_kind: junit_unit_candidate
target_class:
target_method?
test_source:
producer_id:
producer_meta?
```

Maps to current `SubmitCandidateRequest`.

### 3.2 `junit_api_candidate`

Future shape:

```text
candidate_kind: junit_api_candidate
target:
  repo/job reference
  test class name or generated test source target
candidate_artifact:
  test_source
required_assets:
  service_start_requirement?
  base_url_ref?
  fixture_requirement?
  mock_requirement?
  auth_requirement?
producer:
  producer_id
  producer_meta?
```

Why this kind matters: it can reuse Maven/Surefire execution before adding an external API runner.

### 3.3 `api_schema_candidate`

Future shape:

```text
candidate_kind: api_schema_candidate
target:
  sut_ref
candidate_artifact:
  schema_ref
  generated_cases_ref?      # optional; never auto-trusted
required_assets:
  base_url_ref
  service_start_requirement?
  auth_requirement?
  fixture_requirement?
  mock_requirement?
producer:
  producer_id
  producer_meta?
```

This kind is compatible with a future Schemathesis-like executor adapter, but the adapter is not
part of S6A.

### 3.4 `api_collection_candidate`

Future shape:

```text
candidate_kind: api_collection_candidate
target:
  sut_ref
candidate_artifact:
  collection_ref
  environment_ref?
required_assets:
  base_url_ref
  auth_requirement?
  fixture_requirement?
  mock_requirement?
producer:
  producer_id
  producer_meta?
```

This kind is compatible with a future Newman-like executor adapter, but the adapter is not part of
S6A.

## 4. Required Asset Policy

Every non-unit candidate must declare which assets it needs. Missing assets should produce
reviewable evidence, not automatic acceptance or hidden execution.

Allowed asset requirement fields:

```text
api_schema_ref?
api_collection_ref?
base_url_ref?
service_start_requirement?
auth_requirement?
fixture_requirement?
mock_requirement?
db_requirement?
external_dependency_requirement?
business_oracle_ref?
```

Rules:

- These are references or requirements, not secrets or embedded files.
- Do not persist `.env`, credentials, live tokens, DB dumps, or service snapshots.
- Do not discover services, schemas, databases, or credentials automatically in S6A.
- Asset absence should route to Asset Gate / human review.

## 5. Submission Boundary

The future submission API should remain producer-agnostic:

```text
submit_candidate(kind, artifact, target, provenance, asset_requirements)
```

But implementation should not jump to a generic endpoint until one small candidate kind proves the
need. The likely sequence is:

```text
1. Keep current /submit_candidate for junit_unit_candidate behavior.
2. Design a normalization function from current request -> JudgeCase.
3. Add future non-unit submit path only when a runner/report contract exists.
```

Do not replace the current endpoint with a broad polymorphic API in S6A.

## 6. Routing Rules

Candidate kind controls only validation and evidence expectations. It must not automatically
launch an executor.

```text
junit_unit_candidate       -> current supported kernel
junit_api_candidate        -> future_gated until service/env contract exists
api_schema_candidate       -> future_gated until schema runner contract exists
api_collection_candidate   -> future_gated until collection runner contract exists
integration_flow_candidate -> manual_oracle_first or future_gated
unknown                    -> manual review required
```

This aligns with the S4A Test-Level Router: routing is advisory and owner-gated.

## 7. Evidence Expectations By Kind

| Candidate kind | Minimum evidence before report | Must not claim |
|---|---|---|
| `junit_unit_candidate` | compile/build outcome, Surefire counts, coverage delta if available, quality gate, Asset Gate. | Value from green/coverage alone. |
| `junit_api_candidate` | Maven/Surefire facts plus service/base URL/fixture/mock status if present. | API correctness without request/response evidence. |
| `api_schema_candidate` | runner command, schema input identity, request/response summary, schema failures, runner logs. | Business correctness from schema conformance alone. |
| `api_collection_candidate` | runner command, collection identity, request/response summary, assertion failures, env/auth/fixture status. | Business correctness from HTTP 2xx alone. |
| `integration_flow_candidate` | ordered step evidence, dependency/fixture status, durable side-effect evidence when available. | Architecture quality from one happy-path flow. |

The detailed report shape belongs to S6B.

## 8. Benchmark And Ledger Policy

S6A does not change benchmark or ledger schemas.

Future policy should be:

```text
unit headline metrics       -> current Java/Maven real rows only
api smoke metrics           -> separate section/slice
external/provenance rows    -> advisory, not real-model headline
historical unknown rows     -> read-only heuristic labels
```

Ledger should receive compact facts only after API failure taxonomy is designed. Do not add API
badcase signatures in S6A.

## 9. External Asset Mapping

S6A uses external assets only as mapped references:

| Asset | Intake shape | Project artifact | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future `sut_ref` / API smoke manifest | no vendoring; pin URL/commit later |
| Schemathesis | `executor_adapter` + `readme_audit` | future `api_schema_candidate` runner design | no install/run in S6A |
| Newman | `executor_adapter` + `readme_audit` | future `api_collection_candidate` runner design | no install/run in S6A |
| WireMock/Testcontainers | `isolation_support` + `readme_audit` | future asset requirement policy | no Docker/service orchestration in S6A |

No external repo is cloned, read, copied, installed, or executed by this document.

## 10. Anti-Drift Rules

S6A must not:

- implement candidate kinds;
- add an API executor;
- install Schemathesis/Newman/RESTler/EvoMaster/Docker dependencies;
- create a generic plugin system;
- create a generic test-management platform;
- add auto-adoption, auto-merge, or auto-warehouse behavior;
- change `conclusion`, `trusted`, review recommendation semantics, digest severity, aggregate
  headline metrics, SQLite indexes, ledger signatures, or benchmark markdown.

## 11. Next Design Part

S6B is drafted in `docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md`:

```text
API Report Contract:
  review_summary["api_evidence"]? or compact evidence block
  request/response/schema/assertion/service/fixture/mock facts
  failure taxonomy draft
  benchmark/report display policy
  no executor yet
```

S6C can select a smoke path only after S6B defines what evidence that smoke path must report.

## 12. Definition Of Done

This design is acceptable if it:

- keeps current `submit_candidate` behavior intact;
- defines candidate kinds without implementing them;
- maps every non-unit kind to required assets and evidence expectations;
- keeps routing advisory and owner-gated;
- keeps reports human-review-only;
- maps external assets to intake shapes;
- does not introduce a new abstraction framework.
