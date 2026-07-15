# API Compact Report Contract

> Date: 2026-07-11  
> Status: S6B design. Documentation only; no API executor, dependency, schema discovery,
> candidate-kind implementation, benchmark schema change, ledger schema change, or report-field
> migration is implied.

## 0. Purpose

This document defines the compact report contract that future API/interface candidates must
produce before any S7 smoke executor is built.

The goal is not an API automation framework. The goal is to make API candidates speak the same
judge language as the current Java/Maven unit-test kernel:

```text
JudgeCase -> JudgeRunner -> JudgeEvidence -> JudgeReport
```

S6A defined candidate kinds and input boundaries. S6A1 implemented a pure `JudgeEvidence`
projection for the current Java/Maven report facts. S6B defines the future API evidence block that
can later plug into that same evidence vocabulary.

## 1. Design Autonomy Rule

Every future design should follow the three-layer read mechanism in `docs/README.md`:

```text
Layer 1: current state, boundaries, knowledge index, external asset matrix
Layer 2: only the docs routed by the active task
Layer 3: code/tests, external README audits, benchmark/ledger evidence only when needed
```

The agent may design autonomously from these docs, but autonomy is bounded:

- active docs beat older archive docs;
- code and tests beat aspirational docs;
- external assets require an intake shape before use;
- owner approval is required before installing tools, importing datasets, adding executors, or
  changing schemas.

External articles and repositories are pattern sources, not automatic backlog. They can shape the
design only through one of the intake shapes in
`docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`.

## 2. Report Placement

Future API/interface evidence should appear as a compact advisory block:

```text
review_summary["api_evidence"]
```

Do not create a separate report type first. Do not add API fields to the top-level report unless a
later implementation slice proves that report consumers need them.

`review_summary["api_evidence"]` is:

- fact-only;
- compact;
- redacted;
- advisory;
- not a digest detector by default;
- not a verdict source.

The canonical invariant remains:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
```

## 3. Compact Shape

Proposed future shape:

```text
review_summary["api_evidence"] = {
  "advisory": true,
  "report_only": true,
  "candidate_kind": "junit_api_candidate | api_schema_candidate | api_collection_candidate",
  "asset_refs": {
    "schema_ref_present": true | false | null,
    "collection_ref_present": true | false | null,
    "base_url_ref_present": true | false | null,
    "auth_requirement": "not_required | present | missing | failed | unknown",
    "fixture_requirement": "not_required | present | missing | failed | unknown",
    "mock_requirement": "not_required | present | missing | failed | unknown"
  },
  "environment": {
    "service_start": "not_required | skipped | passed | failed | unknown",
    "base_url_available": true | false | null,
    "network_scope": "local | sandbox | external | unknown"
  },
  "execution": {
    "runner_tool": "maven_surefire_jacoco | schemathesis | newman | unknown",
    "command_summary": "...",
    "duration_ms": 0,
    "log_path": "..."
  },
  "traffic": {
    "request_count": 0,
    "operation_count": 0,
    "status_summary": [{"class": "2xx | 3xx | 4xx | 5xx | other", "count": 0}],
    "method_path_summary": [{"method": "GET", "path_template": "/owners/{id}", "count": 0}]
  },
  "checks": {
    "schema_failures": 0,
    "assertion_failures": 0,
    "auth_failures": 0,
    "fixture_failures": 0,
    "mock_misses": 0,
    "service_start_failures": 0,
    "runner_errors": 0,
    "timeouts": 0
  },
  "failures": [
    {
      "code": "api_schema_violation",
      "severity": "blocker | warning",
      "evidence": "redacted short fact"
    }
  ],
  "redaction": {
    "request_body_persisted": false,
    "response_body_persisted": false,
    "secrets_persisted": false
  }
}
```

This is a design shape, not a live schema.

## 4. Field Rules

`asset_refs` records presence and requirement status only. It must not persist credentials,
`.env`, raw schemas, Postman environment secrets, DB dumps, or service snapshots.

`environment` records whether the necessary runtime context existed. A missing service, fixture,
mock, or auth setup is evidence for review, not an auto-verdict.

`execution` aligns with `JudgeEvidence.runner`. It should carry command/log facts when an approved
executor exists.

`traffic` is intentionally summarized. The first version should avoid storing raw request bodies,
raw response bodies, cookies, tokens, or large payloads.

`checks` is deterministic counter evidence. A count of zero is not proof of business correctness.

`failures` is compact and redacted. It should record codes and short evidence, not full payloads.

`redaction` exists so reports can prove what was not persisted.

## 5. Candidate-Kind Mapping

| Candidate kind | Earliest report evidence | Do not claim |
|---|---|---|
| `junit_api_candidate` | Maven/Surefire outcome plus service/base-url/fixture/mock status and any captured request summary. | API correctness from a green JUnit run alone. |
| `api_schema_candidate` | Runner command, schema identity, request/status summary, schema failure counts, runner log path. | Business correctness from schema conformance alone. |
| `api_collection_candidate` | Runner command, collection identity, assertion failures, auth/env/fixture status, request/status summary. | Business correctness from HTTP 2xx alone. |
| `integration_flow_candidate` | Ordered step evidence, dependency/fixture/mock status, side-effect evidence when available. | Architecture quality from one happy-path flow. |

`integration_flow_candidate` remains later than S7 smoke. It should not be the first API path.

## 6. Failure Taxonomy Draft

Draft API failure codes for future S7/S8:

```text
api_asset_missing_schema
api_asset_missing_collection
api_asset_missing_base_url
api_auth_unconfigured
api_fixture_missing
api_fixture_setup_failure
api_mock_missing
api_service_start_failure
api_no_requests_executed
api_schema_violation
api_assertion_failure
api_unexpected_status
api_http_5xx
api_runner_timeout
api_runner_error
api_environment_scope_violation
api_redaction_required
```

Rules:

- Codes are report facts, not verdicts.
- Do not add ledger signatures until this taxonomy is tested on real smoke evidence.
- Do not add digest severity until a later design proves which codes need reviewer prioritization.

## 7. Benchmark And Ledger Policy

S6B does not change benchmark or ledger schemas.

Future S7 policy should be separate from unit-test headline metrics:

```text
unit headline metrics  -> current Java/Maven real rows only
api smoke evidence     -> separate report/benchmark section when implemented
external rows          -> advisory provenance context, never real-model headline
historical unknown     -> read-only heuristic labels
```

Ledger ingestion should wait until API failure taxonomy and compact evidence are validated by a
small smoke run. No historical backfill.

## 8. External Asset Mapping

No external repository has been cloned, copied, installed, executed, or vendored by this design.

External assets may influence future work only through mapped intake shapes:

| Asset | Intake shape | Possible project artifact | S6B use | Red line |
|---|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future API smoke manifest | report evidence examples only | no vendoring; pin URL/commit later |
| Schemathesis | `executor_adapter` + `readme_audit` | future `api_schema_candidate` runner design | expected schema evidence vocabulary | no install/run before S7 approval |
| Newman | `executor_adapter` + `readme_audit` | future `api_collection_candidate` runner design | expected collection evidence vocabulary | no install/run before S7 approval |
| WireMock | `isolation_support` + `readme_audit` | future mock requirement policy | mock status vocabulary | no dependency/service orchestration in S6 |
| Testcontainers | `isolation_support` + `readme_audit` | future service/db fixture policy | fixture/service-start vocabulary | no Docker path before owner approval |

When a future design needs one of these assets, do a focused README audit in scratch space and
record facts in `docs/knowledge/EXTERNAL_REPO_README_AUDIT.md`. Do not copy implementation code or
bulk-import datasets.

## 9. What S6B Allows Next

S6C is drafted in `docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md` and selects
`junit_api_candidate` as the minimal S7 smoke path. It also defines the first safe code slice:
pure API evidence block validation only, with no executor.

The S6B output allowed S6C to:

```text
choose one minimal S7 smoke path candidate:
  option A: junit_api_candidate using existing Maven/Surefire boundary
  option B: api_schema_candidate with Schemathesis adapter design
  option C: api_collection_candidate with Newman adapter design

for the chosen path:
  identify required assets
  define exact command/evidence parser shape
  define redaction and timeout rules
  define no-verdict-drift tests
  still do not execute or install without owner approval
```

Recommended bias: start with the path that proves API evidence with the least new platform surface.

## 10. Anti-Drift Checks

Before implementation, an S7 design must prove:

- Which pillar it strengthens: Candidate, Provenance, Badcase, or Asset Gate.
- Which deterministic API evidence it adds.
- Why the evidence is not a business-correctness proof.
- How `NEED_HUMAN_REVIEW` and `trusted=False` stay fixed.
- How secrets and payloads are redacted.
- Which external assets were mapped and audited.
- Why no dependency, tool, or dataset is being imported prematurely.
- Which tests prove report, digest, benchmark, and ledger behavior do not drift.

## 11. Definition Of Done

S6B is complete when future designs can answer:

```text
where API evidence appears in the report;
which fields are allowed;
which fields are forbidden;
which failure codes exist as a draft;
how external tools and SUTs map into the project;
what S6C must decide before S7 implementation.
```

This document answers those questions without starting an API executor.
