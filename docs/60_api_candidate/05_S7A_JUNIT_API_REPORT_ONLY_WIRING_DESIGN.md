# 05 - S7A JUnit API Report-Only Wiring Design

> Date: 2026-07-15  
> Status: S7A design with V1 report-only wiring live. No submit API change, executor, dependency,
> schema discovery, benchmark schema change, ledger schema change, digest severity change,
> external repo clone, or service orchestration is implied.

## 0. Purpose

S6C selected `junit_api_candidate` as the smallest S7 proof path and added the pure
`api_evidence` validator. S7A should define the first runtime wiring **before** any code changes
to `submit_candidate` or `assemble_generation_report(...)`.

The goal is narrow:

```text
allow a future JUnit API-test candidate to carry a compact report-only API evidence block
while reusing the existing Maven/Surefire judge path.
```

This is not an API automation framework and not an API executor.

## 1. Current Anchor

Live today:

```text
submit_candidate request
  -> run_external_candidate(...)
  -> generation bundle
  -> assemble_generation_report(...)
  -> review_summary with Asset Gate, Test-Level Router, digest
  -> conclusion = NEED_HUMAN_REVIEW
  -> trusted = False
```

S7A must preserve this path for all existing unit candidates.

Live S6C pure helper:

```text
app/report/api_evidence.py
  validate_api_evidence_block(...)
  empty_api_evidence(...)
```

V1 report-only wiring is live in `app/report/generation_report.py`: when a generation bundle
explicitly carries `candidate_kind="junit_api_candidate"` or `api_evidence`, the report validates
and attaches `review_summary["api_evidence"]`. Ordinary unit bundles remain unchanged.

## 2. First Report-Only Wiring Decision

The first implementation should not infer API behavior from source code and should not capture
HTTP traffic. It should only normalize and surface a compact API evidence block when the bundle
explicitly opts into the future API path.

Future first wiring:

```text
generation["candidate_kind"] == "junit_api_candidate"
or generation["api_evidence"] is present
  -> validate_api_evidence_block(...)
  -> review_summary["api_evidence"] = normalized block
```

If neither field is present, the current report shape remains unchanged.

Important: `candidate_kind` is descriptive input for report shaping only. It must not launch a
different runner.

## 3. Minimal Input Extension

Future `submit_candidate` extension, only after owner approval:

```text
SubmitCandidateRequest:
  candidate_kind?: "junit_unit_candidate" | "junit_api_candidate"
  api_evidence?: compact report-only block
```

Rules:

- default remains `junit_unit_candidate`;
- only `junit_unit_candidate` and `junit_api_candidate` are allowed in S7A;
- `api_evidence` is accepted only when `candidate_kind == "junit_api_candidate"`;
- API evidence cannot contain `trusted`, `conclusion`, `recommendation`, `auto_accept`, raw bodies,
  credentials, tokens, cookies, `.env`, or DB/service snapshots;
- request fields are references/statuses only, not secrets or payloads.

The first code slice may avoid the public API and test only `assemble_generation_report(...)` over
a constructed bundle. Public endpoint changes can wait until the report behavior is stable.

## 4. Report Placement

The only allowed report placement is:

```text
report["review_summary"]["api_evidence"]
```

Do not add top-level report fields in S7A. Do not add benchmark/ledger carry fields yet.

The block must remain:

```text
advisory = true
report_only = true
conclusion = NEED_HUMAN_REVIEW
trusted = false
```

These fields are facts about the block, not a second verdict system.

## 5. Candidate Kind And Router Relationship

`candidate_kind` and Test-Level Router are related but not the same:

```text
candidate_kind:
  what the submitted artifact claims to be

test_level_router:
  what Asset Gate recommends from available evidence
```

S7A must not force them to agree automatically.

Examples:

```text
candidate_kind = junit_api_candidate
router.recommended_level = api
  -> coherent; still owner-gated/report-only

candidate_kind = junit_api_candidate
router.recommended_level = manual_oracle_first
  -> valid; assets are insufficient

candidate_kind = junit_unit_candidate
router.recommended_level = api
  -> valid; current artifact may be unit-shaped but target likely needs API-level assets
```

The router remains advisory and does not launch an executor.

## 6. Failure And Missing-Asset Semantics

Missing API assets must be review facts:

```text
api_asset_missing_base_url
api_auth_unconfigured
api_fixture_missing
api_mock_missing
api_service_start_failure
```

They must not:

- auto-reject;
- auto-accept;
- change digest severity in S7A;
- change benchmark aggregates;
- write badcase signatures;
- create headline API metrics.

Digest integration is deferred until real API smoke evidence proves which API failure codes need
review priority.

## 7. Exact First Code Slice

V1 live implementation:

```text
app/report/generation_report.py
  if generation has candidate_kind/api_evidence:
    validate_api_evidence_block(...)
    attach review_summary["api_evidence"]

tests/test_generation_report_api_evidence.py
  default unit report has no api_evidence
  junit_api_candidate attaches normalized api_evidence
  invalid api_evidence raises or degrades in a documented way
  api_evidence authority fields are rejected
  api_evidence does not affect recommendation/conclusion/trusted
  digest does not treat api_evidence as a signal yet
```

Failure policy for invalid `api_evidence`:

```text
raise ApiEvidenceValidationError in pure report tests
```

At the public API boundary, the endpoint can later translate this to HTTP 422. Do not silently
drop invalid evidence because that hides redaction/authority violations.

## 8. No-Drift Tests Required

Any S7A code must keep these tests true:

```text
tests/test_submit_candidate.py
tests/test_generation_report.py
tests/test_review_digest.py
tests/test_benchmark.py
tests/test_api_evidence.py
tests/test_judge_evidence.py
```

Required assertions:

- existing report for ordinary unit bundles is unchanged;
- `review_summary["digest"]` does not read `api_evidence`;
- benchmark `aggregate(...)` keys do not change;
- `conclusion` remains `NEED_HUMAN_REVIEW`;
- `trusted` remains `False`;
- no executor/tool/dependency is invoked.

## 9. External Asset Mapping

S7A report-only wiring needs no external asset.

Future S7B smoke target work may use:

| Asset | Intake shape | Use | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` | future smoke target manifest | no vendoring; pin URL/commit |
| WireMock | `isolation_support` + `readme_audit` | future mock evidence | no dependency in S7A |
| Testcontainers | `isolation_support` + `readme_audit` | future service/db fixture evidence | no Docker path in S7A |

Schemathesis and Newman remain deferred executor-adapter options for later `api_schema_candidate`
or `api_collection_candidate` work, not this JUnit API path.

## 10. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future API smoke evidence, future first compile/test pass split for junit_api_candidate,
  future asset-sufficiency calibration
- automated evidence:
  Maven/Surefire facts plus compact API evidence block when explicitly supplied
- human labels required:
  no for report-only smoke facts; yes for usability, defect discovery, misjudgment
- denominator:
  future junit_api_candidate smoke rows, separate from current unit headline rows
- headline eligibility:
  not current real-model headline; future separate API smoke section only
- red lines:
  no executor, no dependency, no API automation framework, no raw payloads/secrets,
  no auto-accept, no trusted=True, no benchmark/ledger schema changes
```

## 11. Definition Of Done

S7A design is sufficient if the next implementer can answer:

- where `api_evidence` is attached;
- how `candidate_kind` enters without launching an executor;
- why existing unit reports remain unchanged;
- how invalid/redaction-unsafe evidence is rejected;
- why digest, benchmark, ledger, conclusion, and trust do not drift;
- what remains deferred to S7B/S8.
