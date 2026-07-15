# 04 - S7 Smoke Path Selection

> Date: 2026-07-15  
> Status: S6C design plus V1 pure API-evidence validation slice. No API executor, dependency,
> schema discovery, candidate-kind implementation, benchmark schema change, ledger schema change,
> report wiring, external repo clone, or service orchestration is implied.

## 0. Decision

S7 should start with:

```text
junit_api_candidate using the existing Maven/Surefire boundary
```

This means the first API/interface proof line should evaluate Java/JUnit tests that exercise API
behavior, for example RestAssured, MockMvc, WebTestClient, or a similar project-local API testing
style, while still using the existing Java/Maven judge discipline.

S7 should not start with Schemathesis, Newman, RESTler, EvoMaster, Docker, Testcontainers, or a
general API automation surface.

## 1. Why This Path

The goal is to prove that TestAgent Lab is not unit-test-only without replacing the judge kernel.

`junit_api_candidate` is the smallest bridge because it can reuse:

- repository import / workspace rules;
- candidate submit posture;
- preflight and write boundaries;
- Maven/Surefire execution;
- existing report and review invariants;
- `JudgeEvidence` vocabulary;
- Asset Gate / Test-Level Router language.

It adds the least new platform surface. The new thing is not an executor; the new thing is the
API/interface evidence contract.

## 2. Options Considered

| Option | Candidate kind | Benefit | Cost | Decision |
|---|---|---|---|---|
| A | `junit_api_candidate` | Reuses Maven/Surefire and existing Java candidate path. | Needs service/base-url/fixture/mock evidence language. | Choose first. |
| B | `api_schema_candidate` with Schemathesis | Strong schema-oriented API evidence. | New tool, command parser, schema and service boundary. | Defer. |
| C | `api_collection_candidate` with Newman | Good fit for Postman-style collections. | New tool, environment redaction, collection parser. | Defer. |

Option A is not "better API testing." It is the safest proof that the existing judge kernel can
carry an API/interface candidate.

## 3. First S7 Proof Shape

The future S7 implementation should be a narrow owner-gated slice:

```text
input:
  test_source already written as a JUnit API test candidate
  candidate_kind = junit_api_candidate
  declared asset requirements:
    service_start_requirement?
    base_url_ref?
    fixture_requirement?
    mock_requirement?
    auth_requirement?

runner:
  current Maven/Surefire boundary only

evidence:
  existing compile/build/test facts
  compact review_summary["api_evidence"]
  no raw request/response bodies
  no secrets, .env, tokens, cookies, DB dumps, or service snapshots

report:
  conclusion = NEED_HUMAN_REVIEW
  trusted = False
```

## 4. V1 API Evidence Slice

Before an executor or submit path changes, add only a pure report-block validator:

```text
app/report/api_evidence.py
  validate_api_evidence_block(block) -> normalized dict
  empty_api_evidence(candidate_kind="junit_api_candidate") -> normalized dict

tests/test_api_evidence.py
  validates compact API evidence
  rejects raw payload/secrets/redaction violations
  preserves advisory/report-only invariants
  proves no verdict fields are accepted
```

This slice creates a stable target shape for future `review_summary["api_evidence"]`. It does not
wire the block into `assemble_generation_report(...)`.

## 5. Required Fields For The First Path

Minimum `junit_api_candidate` API evidence:

```text
candidate_kind: junit_api_candidate
asset_refs:
  base_url_ref_present: true | false | null
  auth_requirement: not_required | present | missing | failed | unknown
  fixture_requirement: not_required | present | missing | failed | unknown
  mock_requirement: not_required | present | missing | failed | unknown
environment:
  service_start: not_required | skipped | passed | failed | unknown
  base_url_available: true | false | null
  network_scope: local | sandbox | external | unknown
execution:
  runner_tool: maven_surefire_jacoco
traffic:
  request_count: integer >= 0
  status_summary: compact status-class counts only
checks:
  assertion_failures: integer >= 0
  auth_failures: integer >= 0
  fixture_failures: integer >= 0
  mock_misses: integer >= 0
  service_start_failures: integer >= 0
  runner_errors: integer >= 0
  timeouts: integer >= 0
redaction:
  request_body_persisted: false
  response_body_persisted: false
  secrets_persisted: false
```

Zero request count is not proof of failure by itself, but it is a review fact. HTTP 2xx is not
business correctness. A green Maven run is not API correctness.

## 6. External Asset Mapping

No external asset is needed for the V1 API evidence validator.

Future S7 smoke may use these only after a focused README audit and owner-approved implementation
scope:

| Asset | Intake shape | Use | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future smoke target manifest | no vendoring; pin URL/commit later |
| Schemathesis | `executor_adapter` + `readme_audit` | later `api_schema_candidate` runner | no install/run in S6C |
| Newman | `executor_adapter` + `readme_audit` | later `api_collection_candidate` runner | no install/run in S6C |
| WireMock | `isolation_support` + `readme_audit` | future mock requirement policy | no dependency in S6C |
| Testcontainers | `isolation_support` + `readme_audit` | future service/db fixture policy | no Docker path in S6C |

## 7. No-Drift Tests

S6C/S7 preparation must prove:

- `api_evidence` is advisory and report-only;
- `conclusion` and `trusted` cannot be supplied by the block;
- raw payloads/secrets are rejected;
- a missing fixture/mock/auth/base URL is evidence for review, not a verdict;
- no benchmark aggregate keys change;
- no ledger signature changes;
- no digest severity changes until future evidence proves which API codes need priority.

## 8. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future first compile/test pass for junit_api_candidate, future API smoke evidence,
  future asset-sufficiency calibration
- automated evidence:
  compact service/base-url/traffic/check/redaction facts
- human labels required:
  no for smoke evidence; yes for usability, defect discovery, and misjudgment
- denominator:
  future API candidate smoke rows, separate from unit-test headline rows
- headline eligibility:
  not eligible for current unit-test real headline; future separate API smoke section only
- red lines:
  no executor in S6C, no dependency, no external clone, no schema discovery, no raw payloads,
  no secrets, no auto-accept, no trusted=True
```

## 9. Next Implementation Boundary

The first S6C code slice is live:

```text
app/report/api_evidence.py
tests/test_api_evidence.py
```

The next S7A design is
`docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`. Do not wire
`api_evidence` into the runtime report until that design is approved for implementation.
