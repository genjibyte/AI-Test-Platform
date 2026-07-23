# 06 - S7B Submit API Report-Only Extension Design

> Date: 2026-07-16
> Status: S7B/S7D2 submit report-only carry is live. S6D2 also allows optional Java framework
> declaration carry. No executor, dependency, schema discovery, benchmark schema change, ledger
> schema change, digest severity change, external repo clone, or service orchestration is implied.

## 0. Purpose

S7A made `review_summary["api_evidence"]` live at the report layer when a generation bundle
explicitly carries `candidate_kind="junit_api_candidate"` or `api_evidence`.

S7B defines the smallest public submission extension that can feed that report-only path. S7D2
extends the same boundary with compact `api_smoke_manifest.v1` carry:

```text
submit_candidate request
  -> optional candidate_kind/api_evidence/api_smoke_manifest/java_test_framework validation
  -> existing run_external_candidate(...)
  -> generation bundle carries compact api_evidence/api_smoke_manifest/java_test_framework
  -> existing Maven/Surefire judge path
  -> review_summary["api_evidence"], review_summary["api_smoke_manifest"],
     and review_summary["java_test_framework"]
```

This still does not build an API executor. It only lets a caller submit a JUnit API-test candidate
and provide compact, redacted API evidence facts for the report.

## 1. Current Anchor

Live today:

```text
SubmitCandidateRequest:
  target_class:
  target_method?
  test_source:
  producer_id:
  producer_meta?
  candidate_kind?
  api_evidence?
  api_smoke_manifest?
  java_test_framework?
```

Endpoint invariants:

- `producer_id` is required and cannot be `fake-1`;
- `test_source` is required and size-capped;
- caller cannot set `run_kind`;
- pipeline forces `run_kind="external"`;
- `trusted=False`;
- report conclusion remains `NEED_HUMAN_REVIEW`.

S7B must keep existing callers working without adding required fields.

## 2. Live Request Shape

Live S7B/S7D2 request shape:

```text
SubmitCandidateRequest:
  target_class: str
  target_method?: str
  test_source: str
  producer_id: str
  producer_meta?: dict
  candidate_kind?: "junit_unit_candidate" | "junit_api_candidate"
  api_evidence?: compact api_evidence block
  api_smoke_manifest?: compact api_smoke_manifest.v1 row
  java_test_framework?: "junit4" | "junit5" | "testng" | "unknown"
```

Rules:

- omitted `candidate_kind` means the existing unit path;
- `candidate_kind="junit_unit_candidate"` is equivalent to the existing behavior;
- `candidate_kind="junit_api_candidate"` still uses the existing Maven/Surefire judge path;
- `api_evidence` is accepted only when `candidate_kind=="junit_api_candidate"`;
- `api_evidence` without explicit `candidate_kind=="junit_api_candidate"` is rejected;
- `api_smoke_manifest` is accepted only when `candidate_kind=="junit_api_candidate"`;
- `api_smoke_manifest` without matching `api_evidence` is allowed but not denominator-ready;
- `java_test_framework` is optional and normalized as report-only metadata;
- unsupported future kinds such as `api_schema_candidate` and `api_collection_candidate` are
  rejected at the public boundary in S7B/S7D2.

## 3. Validation Boundary

S7B should validate twice:

```text
API boundary:
  validate candidate_kind
  reject api_evidence unless candidate_kind == junit_api_candidate
  reject api_smoke_manifest unless candidate_kind == junit_api_candidate
  validate_api_evidence_block(...)
  validate_api_smoke_manifest(...)
  validate/normalize java_test_framework
  validate manifest target alignment
  return HTTP 422 on invalid evidence

Report boundary:
  generation_report validates again before attaching review_summary["api_evidence"]
  generation_report validates again before attaching review_summary["api_smoke_manifest"]
  generation_report validates again before attaching review_summary["java_test_framework"]
```

This is defense in depth. The API boundary protects callers and storage from invalid/redaction-
unsafe facts; the report boundary protects downstream report assembly if a bundle is constructed
outside the endpoint.

## 4. Pipeline Propagation

Live minimal pipeline signature:

```text
run_external_candidate(
  ...,
  candidate_kind: Optional[str] = None,
  api_evidence: Optional[dict] = None,
  api_smoke_manifest: Optional[dict] = None,
  java_test_framework: Optional[str] = None,
)
```

Bundle propagation:

```text
bundle["candidate_kind"] = "junit_api_candidate"     # only when explicitly supplied
bundle["api_evidence"] = validated compact block     # only when supplied
bundle["api_smoke_manifest"] = normalized manifest   # only when supplied
bundle["java_test_framework"] = normalized value      # only when supplied
```

Do not use `candidate_kind` to choose a runner. The runner remains the current Java/Maven
execution path.

Do not persist raw request bodies, raw response bodies, cookies, tokens, `.env`, database dumps,
service snapshots, or OpenAPI/Postman files in this S7B path.

## 5. Error Policy

Recommended public errors:

```text
unsupported candidate_kind -> HTTP 422
api_evidence without junit_api_candidate -> HTTP 422
api_evidence with trusted/conclusion/auto_accept -> HTTP 422
api_evidence with raw payload/secret field -> HTTP 422
api_evidence redaction flags true -> HTTP 422
api_smoke_manifest without junit_api_candidate -> HTTP 422
api_smoke_manifest target drift -> HTTP 422
api_smoke_manifest execution drift -> HTTP 422
unknown java_test_framework -> HTTP 422
```

Report-only wiring should continue raising `ApiEvidenceValidationError` in pure tests. The API
endpoint should translate that to 422 rather than silently dropping the evidence.

## 6. Report Semantics

When accepted:

```text
report["review_summary"]["api_evidence"] = normalized block
report["review_summary"]["api_smoke_manifest"] = normalized projection
report["review_summary"]["java_test_framework"] = normalized framework facts
```

Nothing else changes:

- no top-level report fields;
- no digest flags from `api_evidence`;
- no benchmark/ledger carry fields;
- no new headline metrics;
- no candidate acceptance;
- no trust escalation.

The report block remains:

```text
advisory = true
report_only = true
conclusion = NEED_HUMAN_REVIEW
trusted = false
```

## 7. Candidate Kind And Asset Gate

`candidate_kind` is caller-declared artifact shape. Asset Gate remains judge-side advisory
context.

S7B must not force:

```text
candidate_kind == router.recommended_level
```

Examples:

- a caller may submit `junit_api_candidate`, while Asset Gate recommends `manual_oracle_first`
  because business oracle, fixture, or mock assets are missing;
- a caller may omit `candidate_kind`, while Asset Gate recommends `api` from code structure;
- both cases are review facts, not verdicts.

## 8. Tests Required

S7B/S7D2 implementation tests cover:

```text
tests/test_submit_candidate.py
  existing request without candidate_kind still works
  candidate_kind=junit_api_candidate is accepted
  candidate_kind=api_schema_candidate is rejected
  api_evidence without junit_api_candidate is rejected
  candidate_kind=junit_unit_candidate plus api_evidence is rejected
  api_smoke_manifest without junit_api_candidate is rejected
  api_smoke_manifest target drift is rejected
  authority fields inside api_evidence are rejected
  raw payload/secret fields inside api_evidence are rejected
  validated compact api_evidence reaches generation bundle
  normalized api_smoke_manifest reaches generation bundle
  assemble_generation_report(job.generation) attaches review_summary["api_evidence"]
  assemble_generation_report(job.generation) attaches review_summary["api_smoke_manifest"]
  run_kind remains external
  trusted remains false
  conclusion remains NEED_HUMAN_REVIEW

tests/test_generation_report_api_evidence.py
  report-only behavior remains unchanged

tests/test_benchmark.py
  aggregate headline shape remains unchanged
```

No test should start a real service, Docker container, Schemathesis, Newman, or a real model.

## 9. External Asset Mapping

S7B needs no external asset.

Future API smoke target or benchmark-projection work may use:

| Asset | Intake shape | Use | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future pinned JUnit API smoke target | no vendoring; pin URL/commit |
| WireMock | `isolation_support` + `readme_audit` | future mock evidence/support | no dependency in S7B |
| Testcontainers | `isolation_support` + `readme_audit` | future service/db fixture support | no Docker path in S7B |
| Schemathesis | `executor_adapter` + `readme_audit` | later `api_schema_candidate` path | no install/run in S7B |
| Newman | `executor_adapter` + `readme_audit` | later `api_collection_candidate` path | no install/run in S7B |

## 10. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future API smoke evidence intake, future first compile/test pass split for junit_api_candidate,
  future asset-sufficiency calibration
- automated evidence:
  existing Maven/Surefire facts plus caller-supplied compact API evidence
- human labels required:
  no for report-only smoke facts; yes for usability, defect discovery, misjudgment
- denominator:
  future junit_api_candidate submissions, separate from current unit headline rows
- headline eligibility:
  not current real-model headline; future separate API smoke section only
- red lines:
  no executor, no dependency, no external clone, no raw payloads/secrets,
  no auto-accept, no trusted=True, no benchmark/ledger schema changes
```

## 11. Definition Of Done

S7B/S7D2 implementation is sufficient if the next maintainer can answer:

- what request fields are added;
- what defaults keep existing callers stable;
- which inputs are rejected at the public boundary;
- how the bundle carries report-only API evidence;
- how the bundle carries report-only API smoke manifest facts;
- why the runner remains Maven/Surefire;
- why digest, benchmark, ledger, conclusion, and trust do not drift;
- what remains deferred to API smoke benchmark/ledger projection.

S7C is drafted in `docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md`. It defines
the minimal `api_smoke_manifest.v1` exam-bag contract for the first `junit_api_candidate` proof
line: target, asset requirements, execution policy, compact evidence contract, denominator, and
external-asset intake rules. It still does not approve an executor or endpoint change.

S7D1/S7D2 are live in `app/report/generation_report.py`, `app/api/submit_candidate.py`, and
`app/pipeline/submit_pipeline.py`, with tests in `tests/test_generation_report_api_smoke_manifest.py`
and `tests/test_submit_candidate.py`. A supplied manifest can now be carried into
`review_summary["api_smoke_manifest"]` with alignment facts against target, `candidate_kind`, and
compact `api_evidence`. This still does not approve execution, benchmark/ledger carry, digest
severity changes, or verdict changes.
