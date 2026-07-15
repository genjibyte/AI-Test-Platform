# 07 - S7C JUnit API Smoke Manifest Design

> Date: 2026-07-16  
> Status: S7C design. Documentation only; no manifest validator, submit endpoint change, API
> executor, dependency, service orchestration, Docker path, external repo clone, benchmark schema
> change, ledger schema change, digest severity change, or verdict change is implied.

## 0. Purpose

S7A made report-only `api_evidence` attachable to a generation report. S7B designed how
`submit_candidate` can later accept `candidate_kind` and compact `api_evidence`.

S7C defines the missing proof object:

```text
the minimal smoke manifest that tells the judge what a junit_api_candidate is trying to prove,
which assets are required, and which evidence is allowed to reach the report.
```

This is the concrete "exam bag" for the first API/interface proof line. It is not a new platform
layer and not an API automation framework.

## 1. Decision

The first API/interface smoke proof should be:

```text
junit_api_candidate
  -> existing Maven/Surefire/JaCoCo judge boundary
  -> compact review_summary["api_evidence"]
  -> existing report with conclusion = NEED_HUMAN_REVIEW and trusted = False
```

The manifest exists to stop two kinds of drift:

- unit-only drift: never reaching API/interface candidate evaluation;
- abstraction drift: inventing generic "exam bag / invigilator / scorecard" layers before a real
  smoke proof is pinned.

S7C keeps the abstraction concrete by binding every field to an already-known artifact:

| Concept | S7C artifact | Current boundary |
|---|---|---|
| Exam bag | `api_smoke_manifest.v1` row | design doc first, future pure validator |
| Invigilation interface | existing Maven/Surefire judge call | no API executor |
| Evidence format | `JudgeEvidence` plus compact `api_evidence` | report-only facts |
| Grade sheet | existing generation report / benchmark markdown | advisory, no auto-accept |

## 2. Manifest Shape

Future S7C manifest rows should be small, redacted, and pinned:

```text
schema_version: "api_smoke_manifest.v1"
smoke_id: "s7c-junit-api-001"
candidate_kind: "junit_api_candidate"
status: "designed | approved | active | retired"

target:
  target_class: "com.example.OwnerController"
  target_method: null
  api_style: "mockmvc | webtestclient | restassured_local | local_http | unknown"
  sut_ref:
    intake_shape: "sut_target | none"
    name: "project-under-judge"
    url: null
    commit: null
    readme_audit_ref: null
    license_note: null

submission_contract:
  required_fields:
    - target_class
    - test_source
    - producer_id
    - candidate_kind
  optional_fields:
    - target_method
    - producer_meta
    - api_evidence
  fixed_values:
    candidate_kind: "junit_api_candidate"

asset_requirements:
  service_start_requirement: "not_required | required | unknown"
  base_url_requirement: "not_required | required | unknown"
  auth_requirement: "not_required | required | unknown"
  fixture_requirement: "not_required | required | unknown"
  mock_requirement: "not_required | required | unknown"
  business_oracle_ref_requirement: "present | missing | unknown"

execution_policy:
  runner_tool: "maven_surefire_jacoco"
  allowed_network_scope: "local | sandbox"
  external_network_allowed: false
  docker_required: false
  real_model_allowed: false
  timeout_policy_ref: "current judge timeout"

evidence_contract:
  report_path: "review_summary.api_evidence"
  minimum_api_evidence:
    advisory: true
    report_only: true
    candidate_kind: "junit_api_candidate"
    execution.runner_tool: "maven_surefire_jacoco"
    redaction.request_body_persisted: false
    redaction.response_body_persisted: false
    redaction.secrets_persisted: false
  forbidden:
    - raw request bodies
    - raw response bodies
    - tokens
    - cookies
    - credentials
    - .env values
    - database dumps
    - service snapshots
    - conclusion
    - trusted
    - auto_accept
```

This is a design contract, not a live schema. A later code slice may implement a pure validator
only after owner approval.

## 3. First Smoke Target Bias

The safest first smoke target should prefer an in-process API style:

```text
MockMvc or WebTestClient JUnit candidate
```

Reason:

- it proves API/interface candidate handling without service orchestration;
- `service_start_requirement` and `base_url_requirement` can be `not_required`;
- the existing Maven/Surefire judge remains the only invigilator;
- redaction risk is lower than external HTTP traffic;
- failures still surface as compile/test/quality evidence plus compact API facts.

`RestAssured` against a local service is still allowed by the manifest shape, but it should not be
the first proof unless the service start and base URL requirements are already pinned and redacted.

## 4. What The Manifest Must Not Do

The manifest must not:

- launch an executor;
- start a service;
- install RestAssured, Schemathesis, Newman, WireMock, Testcontainers, Docker, or any new
  dependency;
- infer OpenAPI schemas;
- store raw traffic;
- promote API evidence into digest severity, ledger signatures, or benchmark aggregate keys;
- turn a green API test into a value claim;
- change `conclusion`, `recommendation`, or `trusted`.

A missing base URL, fixture, mock, auth setup, or oracle source is an Asset Gate/review fact. It is
not an automatic rejection.

## 5. Relationship To Existing Pieces

S7C does not replace the current report-only path:

```text
submit_candidate (future S7B fields)
  -> existing run_external_candidate(...)
  -> generation bundle carries candidate_kind/api_evidence
  -> assemble_generation_report(...)
  -> review_summary["api_evidence"]
  -> report conclusion remains NEED_HUMAN_REVIEW
```

Instead, S7C gives future runs a pinned manifest row so the platform can later say:

```text
this API candidate was judged under smoke manifest X,
with these required assets,
and only these redacted evidence fields were allowed into the report.
```

This supports reproducibility without adding a second product.

## 6. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future first compile/test pass split for junit_api_candidate,
  future API smoke denominator,
  future asset-sufficiency calibration for API/interface candidates
- automated evidence:
  manifest id, candidate_kind, Maven/Surefire facts, compact api_evidence, redaction proof
- human labels required:
  no for smoke execution facts; yes for usable-test rate, defect discovery, diagnosis time,
  human handling time, and misjudgment rate
- denominator:
  only rows tied to an approved api_smoke_manifest.v1 smoke_id
- headline eligibility:
  never mixed into current unit-test real headline; future separate API smoke section only
- red lines:
  no executor, no dependency, no service orchestration, no external clone, no raw payloads,
  no secrets, no auto-accept, no trusted=True
```

The manifest is what prevents future API evidence from becoming anecdotal. It supplies the
denominator and asset context, while the existing judge supplies execution evidence.

## 7. External Asset Mapping

S7C itself requires no external asset.

Future smoke targets or support tools must keep the intake shape explicit:

| Asset | Intake shape | S7C mapping | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | possible future `sut_ref` manifest seed | no vendoring; no clone inside project tree |
| WireMock | `isolation_support` + `readme_audit` | possible future mock requirement policy | no dependency until an approved executor/asset design |
| Testcontainers | `isolation_support` + `readme_audit` | possible future service/db fixture policy | no Docker path in S7C |
| Schemathesis | `executor_adapter` + `readme_audit` | later `api_schema_candidate`, not this path | no install/run for JUnit API smoke |
| Newman | `executor_adapter` + `readme_audit` | later `api_collection_candidate`, not this path | no install/run for JUnit API smoke |

If a future design mentions any of these, it must first perform the focused README audit described
in `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md` and record facts before implementation.

## 8. Future Pure Validator Slice

If S7C is approved for implementation, the next code slice should still be non-executing:

```text
app/report/api_smoke_manifest.py
  validate_api_smoke_manifest(manifest) -> normalized dict

tests/test_api_smoke_manifest.py
  accepts minimal junit_api_candidate manifest
  defaults no external network and no Docker
  rejects unsupported candidate_kind
  rejects authority/verdict fields
  rejects raw payload, secret, .env, cookie, token, and service snapshot references
  proves runner_tool remains maven_surefire_jacoco
```

This validator should not wire into submit, benchmark, ledger, or report until a later bounded
design says where the manifest id is carried.

## 9. Definition Of Done

S7C design is sufficient if the next implementer can answer:

- what a first `junit_api_candidate` smoke row contains;
- why MockMvc/WebTestClient-style in-process API tests are the safest first proof;
- how the existing Maven/Surefire judge remains the only runner;
- which assets must be declared before a smoke claim is made;
- where compact API evidence appears in the report;
- why the future denominator is manifest-bound and separate from unit headlines;
- why external tools and SUTs are mapped but not imported;
- why conclusion, trust, digest, benchmark, and ledger behavior do not drift.
