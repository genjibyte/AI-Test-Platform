# 08 - S7D API Smoke Manifest Carry-Through Design

> Date: 2026-07-20
> Status: S7D1 report-layer carry-through and S7D2 public submit carry are live. No executor,
> dependency, service orchestration, Docker path, external repo clone, benchmark schema change,
> ledger schema change, digest severity change, or verdict change is implied.

## 0. Purpose

S7A made compact `review_summary["api_evidence"]` report-only wiring live for explicit
`junit_api_candidate` bundles. S7C made the `api_smoke_manifest.v1` exam-bag validator live. S7D1
carries a validated manifest projection into reports. S7D2 lets the public submit endpoint carry
that compact manifest into the same report-only path.

S7D1 implements the report-layer link:

```text
junit_api_candidate
  -> compact api_smoke_manifest.v1
  -> compact api_evidence
  -> existing Maven/Surefire judge facts
  -> report review_summary with manifest + evidence
  -> conclusion = NEED_HUMAN_REVIEW
  -> trusted = False
```

The manifest is the proof denominator: it says which target, asset requirements, runner boundary,
and evidence contract governed the API candidate. It is not an executor and not an approval token.

## 1. Current Anchor

Live pieces:

```text
app/report/api_evidence.py
  validate_api_evidence_block(...)

app/report/generation_report.py
  attaches review_summary["api_evidence"] when generation explicitly carries
  candidate_kind="junit_api_candidate" or api_evidence
  attaches review_summary["api_smoke_manifest"] when generation explicitly carries
  candidate_kind="junit_api_candidate" and api_smoke_manifest

app/report/api_smoke_manifest.py
  validate_api_smoke_manifest(...)
```

Current gap:

```text
api_smoke_manifest.v1 can be validated and projected into reports
and accepted by submit_candidate as report-only carry
but it is not backed by a manifest registry,
not counted in benchmark/ledger,
and not denominator-ready.
```

S7D1 closes only the report-carry gap.

## 2. Decision

S7D1 adds a report-only carry contract for:

```text
generation["api_smoke_manifest"]
```

When present, report assembly:

1. validates it with `validate_api_smoke_manifest(...)`;
2. verifies it is compatible with the generation bundle;
3. attaches a compact report projection at:

```text
review_summary["api_smoke_manifest"]
```

This does not change the runner. The existing Java/Maven judge remains the only execution boundary.

## 3. Report Shape

Recommended report projection:

```text
review_summary["api_smoke_manifest"] = {
  "advisory": true,
  "report_only": true,
  "schema_version": "api_smoke_manifest.v1",
  "smoke_id": "s7c-junit-api-001",
  "candidate_kind": "junit_api_candidate",
  "status": "designed | approved | active | retired",
  "target": {
    "target_class": "...",
    "target_method": null,
    "api_style": "mockmvc | webtestclient | restassured_local | local_http | unknown",
    "sut_ref": {
      "intake_shape": "none | sut_target",
      "name": "...",
      "commit": "...",
      "readme_audit_ref": "..."
    }
  },
  "asset_requirements": {
    "service_start_requirement": "not_required | required | unknown",
    "base_url_requirement": "not_required | required | unknown",
    "auth_requirement": "not_required | required | unknown",
    "fixture_requirement": "not_required | required | unknown",
    "mock_requirement": "not_required | required | unknown",
    "business_oracle_ref_requirement": "present | missing | unknown"
  },
  "execution_policy": {
    "runner_tool": "maven_surefire_jacoco",
    "allowed_network_scope": "local | sandbox",
    "external_network_allowed": false,
    "docker_required": false,
    "real_model_allowed": false
  },
  "evidence_contract": {
    "report_path": "review_summary.api_evidence",
    "minimum_api_evidence": {
      "candidate_kind": "junit_api_candidate",
      "execution.runner_tool": "maven_surefire_jacoco",
      "redaction.request_body_persisted": false,
      "redaction.response_body_persisted": false,
      "redaction.secrets_persisted": false
    }
  },
  "alignment": {
    "target_matches_generation": true,
    "candidate_kind_matches": true,
    "api_evidence_present": true | false,
    "api_evidence_candidate_kind_matches": true | false | null,
    "runner_tool_matches": true | false | null,
    "redaction_contract_satisfied": true | false | null,
    "denominator_ready": true | false,
    "not_ready_reasons": [...]
  }
}
```

Rules:

- `denominator_ready` is S8-driven after `api_smoke_denominator.v1`; benchmark counting still
  remains disabled.
- This block is advisory and report-only.
- It must not feed digest severity.
- It must not create ledger signatures or benchmark carry fields.
- It must not add top-level report fields.

## 4. Compatibility Checks

S7D should reject manifest drift at report assembly, not silently attach a misleading manifest.

Required checks:

```text
generation["api_smoke_manifest"].candidate_kind == "junit_api_candidate"
generation["candidate_kind"] == "junit_api_candidate"
manifest.target.target_class == generation.target.target_class
manifest.target.target_method == generation.target.target_method when manifest target_method is set
manifest.execution_policy.runner_tool == "maven_surefire_jacoco"
manifest.evidence_contract.report_path == "review_summary.api_evidence"
```

If `api_evidence` is present:

```text
api_evidence.candidate_kind == manifest.candidate_kind
api_evidence.execution.runner_tool == manifest.execution_policy.runner_tool
api_evidence.redaction.request_body_persisted == false
api_evidence.redaction.response_body_persisted == false
api_evidence.redaction.secrets_persisted == false
```

If `api_evidence` is absent, report assembly may still attach the manifest projection, but
`alignment.api_evidence_present=false` and `alignment.denominator_ready=false`. This is important:
a manifest without observed API evidence is a review fact, not a smoke result.

## 5. Bundle Contract

Report-layer generation bundle extension:

```text
generation["candidate_kind"] = "junit_api_candidate"
generation["api_evidence"] = {...}                 # optional but needed for alignment
generation["api_smoke_manifest"] = {...}           # compact api_smoke_manifest.v1 row
```

Rules:

- `api_smoke_manifest` is accepted only for explicit `candidate_kind="junit_api_candidate"`.
- `api_smoke_manifest` with `candidate_kind="junit_unit_candidate"` is rejected.
- future `api_schema_candidate` / `api_collection_candidate` manifests are rejected in S7D.
- The manifest must not be used to choose a runner.
- The manifest must not authorize external network, Docker, real model calls, service start, or
  new dependencies.

## 6. Submit Boundary

S7D is split into two separable slices.

### S7D1 - Report Bundle Carry - Live

Live report-layer bundle wiring:

```text
assemble_generation_report(generation)
  if generation["api_smoke_manifest"] is present:
    validate_api_smoke_manifest(...)
    validate compatibility with generation and api_evidence
    attach review_summary["api_smoke_manifest"]
```

S7D1 itself made no public endpoint change; S7D2 below adds only public report-only carry.

### S7D2 - Public Submit Carry - Live

Live public submit carry:

```text
SubmitCandidateRequest:
  candidate_kind?: "junit_unit_candidate" | "junit_api_candidate"
  api_evidence?: compact api_evidence block
  api_smoke_manifest?: compact api_smoke_manifest.v1 row
```

Rules:

- existing callers remain unchanged;
- `api_smoke_manifest` requires `candidate_kind="junit_api_candidate"`;
- `api_smoke_manifest` without matching `api_evidence` is allowed but not denominator-ready;
- `api_smoke_manifest_ref` is deferred until a manifest registry exists;
- caller still cannot set `run_kind`, `trusted`, `conclusion`, or recommendation.

The public endpoint should translate validation failures to HTTP 422.

## 7. Denominator Policy

S7D prepares the future API-smoke denominator and S8 adds report-only eligibility facts, but
neither creates a benchmark section.

Future denominator eligibility should require at least:

```text
manifest.status in {"approved", "active"}
manifest.candidate_kind == "junit_api_candidate"
manifest target matches generation target
api_evidence present
api_evidence runner_tool == "maven_surefire_jacoco"
redaction contract satisfied
report conclusion remains NEED_HUMAN_REVIEW
trusted remains False
```

Even then, S7D/S8 should not add benchmark carry fields. A later benchmark projection design must
decide where API smoke rows are counted and how they stay separate from unit-test real headlines.

## 8. Relationship To Asset Gate

The manifest declares asset requirements. Asset Gate estimates asset sufficiency from the judged
bundle and context facts.

S7D must not force them to agree automatically.

Examples:

```text
manifest.fixture_requirement = required
asset_sufficiency.test_data = missing
  -> review fact; no auto-reject

manifest.business_oracle_ref_requirement = present
asset_sufficiency.business_oracle = partial
  -> review fact; no value claim

manifest.api_style = mockmvc
router.recommended_level = manual_oracle_first
  -> valid; assets may still be insufficient
```

The manifest is an exam bag; Asset Gate is an advisory judge-side risk signal.

## 9. Redaction And Forbidden Fields

S7D inherits S7C and S6C red lines:

Forbidden anywhere in the manifest carry path:

```text
trusted
conclusion
recommendation
auto_accept
raw request bodies
raw response bodies
tokens
cookies
credentials
.env values
database dumps
service snapshots
```

The report projection may include references, requirement statuses, status counts, method/path
templates, and log paths. It must not include payloads or secrets.

## 10. Tests Required

S7D1 report-layer tests are live in
`tests/test_generation_report_api_smoke_manifest.py`:

```text
tests/test_generation_report_api_smoke_manifest.py
  default unit report has no api_smoke_manifest
  junit_api_candidate attaches normalized api_smoke_manifest
  api_smoke_manifest requires candidate_kind=junit_api_candidate
  manifest target_class must match generation target_class
  manifest target_method mismatch is rejected when manifest specifies a method
  api_evidence candidate_kind mismatch is rejected
  api_evidence runner_tool mismatch is rejected
  absent api_evidence attaches manifest with denominator_ready=false
  redaction/authority violations are rejected
  digest does not read api_smoke_manifest
  recommendation/conclusion/trusted stay unchanged
```

S7D2 public submit tests are live in `tests/test_submit_candidate.py`:

```text
tests/test_submit_candidate.py
  existing request without candidate_kind/api_evidence/manifest still works
  candidate_kind=junit_api_candidate plus manifest is accepted
  manifest without junit_api_candidate is rejected
  unsupported candidate kind is rejected
  invalid manifest becomes HTTP 422
  normalized manifest reaches generation bundle
  report attaches review_summary["api_smoke_manifest"]
  run_kind remains external
  conclusion remains NEED_HUMAN_REVIEW
  trusted remains False
```

No test should start a service, Docker container, external API executor, or real model.

## 11. External Asset Mapping

S7D itself requires no external asset.

If a future manifest uses a real external SUT, it must include an asset record and focused README
audit before implementation:

| Asset | Intake shape | S7D role | Red line |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` + future `manifest_seed` | possible future `target.sut_ref` | no clone/vendor/run in S7D |
| WireMock | `isolation_support` + `readme_audit` | possible future mock requirement support | no dependency or service orchestration |
| Testcontainers | `isolation_support` + `readme_audit` | possible future fixture/service support | no Docker path |
| Schemathesis | `executor_adapter` + `readme_audit` | later `api_schema_candidate`, not S7D | no install/run |
| Newman | `executor_adapter` + `readme_audit` | later `api_collection_candidate`, not S7D | no install/run |

External Asset Mapping:

```text
assets consulted: none for S7D
intake shape chosen: none
project artifact affected: review_summary["api_smoke_manifest"] design
expected evidence: validated manifest projection and alignment facts
red lines: no external asset execution, no SUT import, no executor, no dependency
```

## 12. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future API smoke denominator discipline, future first compile/test pass split for
  manifest-bound junit_api_candidate rows, future asset-sufficiency calibration
- automated evidence:
  smoke_id, manifest target/assets/execution policy, compact api_evidence alignment,
  current Maven/Surefire facts
- human labels required:
  no for carry-through facts; yes for usable-test rate, defect discovery, diagnosis time,
  human handling time, and misjudgment rate
- denominator:
  not counted in S7D; future denominator requires approved/active manifest plus aligned evidence
- headline eligibility:
  never mixed into current unit-test real headline; future separate API smoke section only
- red lines:
  no executor, no dependency, no service orchestration, no external clone, no raw payloads,
  no secrets, no auto-accept, no trusted=True, no benchmark/ledger schema changes
```

## 13. Definition Of Done

S7D design is sufficient if the next implementer can answer:

- where manifest facts appear in the report;
- how the manifest is validated and projected;
- how manifest, generation target, candidate_kind, and api_evidence align;
- why manifest presence does not imply API correctness;
- why denominator readiness is explicitly false until a later benchmark policy;
- why the runner remains Maven/Surefire;
- why digest, benchmark, ledger, conclusion, recommendation, and trust do not drift;
- what remains deferred to API smoke benchmark/ledger projection.
