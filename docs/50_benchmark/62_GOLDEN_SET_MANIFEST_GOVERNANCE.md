# 62 - Golden Set Manifest Governance

> Date: 2026-07-21
> Status: S5B/S5B2 Live V1. Pure metadata governance and presentation only.
> Scope: external benchmark or bug-set assets that may become future Golden Set manifest seeds.

## 0. Purpose

The current benchmark manifests are:

- `benchmarks/manifest.v1.json`: frozen Java/Maven unit benchmark pins.
- `benchmarks/manifest.v2.json`: the same pins plus advisory business/invariant metadata.

S5B does not edit those manifests and does not import external datasets. It adds a narrow
governance gate for future Golden Set seed metadata so external assets cannot jump from a registry
row into dataset content, execution, or headline claims.

## 1. Contract

A Golden Set seed is a `manifest_seed` record:

```text
asset_id
intake_shape = manifest_seed
project_artifact
source_url
pinned_version_or_commit
license_spdx
task_count_requested
candidate_kind
expected_evidence
requires_network
requires_docker
requires_model_or_api_key
red_lines
next_action
```

Optional metadata may include `task_ids`, `license_verified_at`, `runtime_language`,
`risk_bucket`, `readme_audit_ref`, `owner_gate_ref`, and `notes`.

Allowed project artifacts are only:

```text
benchmarks/*
docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md
```

This keeps Golden Set planning attached to benchmark manifests or the external registry, not to
runner code, storage, dependencies, or report verdicts.

## 2. Live Helper

Implemented artifacts:

```text
app/benchmark/manifest_governance.py
app/benchmark/manifest_governance_report.py
tests/test_golden_manifest_governance.py
tests/test_golden_manifest_governance_report.py
```

Public helpers:

```text
validate_golden_manifest_seed(record) -> normalized metadata record
golden_manifest_governance_plan(records) -> compact planning summary
golden_defect_denominator_readiness(records) -> future defect-denominator readiness summary
render_golden_manifest_governance_markdown(records) -> conditional audit Markdown
```

The helper is pure:

- no file reads;
- no network;
- no clone/download;
- no install;
- no executor or service start;
- no benchmark aggregate mutation;
- no ledger/schema/index mutation;
- no digest, recommendation, conclusion, trusted, or auto-accept behavior.

The presentation helper renders an empty string for empty input and a single
`Golden Set manifest governance - METADATA PLAN` section when seed rows are supplied. It is not
wired into the default benchmark report; it is an opt-in audit view for future manifest planning.

S6G adds `golden_defect_denominator_readiness(...)`, a pure metadata summary for future
`defect_discovery_rate` denominators. It can identify manifest seeds that look like future
bug/defect/verifier denominator candidates and count requested/pinned task metadata, but it always
returns `defect_denominator_ready_now=False` until an owner-gated dataset slice and verifier
evidence exist. It grants no download, execution, headline, verdict, or trust authority.

Every normalized seed returns:

```text
metadata_only = True
runtime_actions_allowed_now = False
download_allowed_now = False
install_allowed_now = False
benchmark_headline_allowed_now = False
verdict_authority = False
owner_gate_required_before_dataset_slice = True
```

## 3. Owner Gates

S5B can record metadata for future Golden Set candidates. It cannot materialize them.

Always owner-gated later:

- dataset slice materialization;
- downloading task data;
- executing external tools or SUTs;
- Docker or service orchestration;
- real model/API calls;
- headline metrics;
- historical benchmark backfill.

`task_count_requested > 5`, `requires_network=true`, `requires_docker=true`, or
`requires_model_or_api_key=true` are accepted as metadata but surfaced as future owner-gate
reasons.

## 4. External Asset Mapping

External Asset Mapping:

- assets consulted: external benchmark/bug-set rows in
  `docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`
- intake shape chosen: `manifest_seed`
- project artifact affected: future `benchmarks/manifest.golden.*.json` draft or the external
  project/benchmark registry
- evidence expected: pinned URL/version/task ids, candidate kind, license note, risk flags, and
  expected judge evidence
- red lines: no dataset content, no bulk import, no execution, no headline metrics, no verdict
  authority, no historical DB backfill

Examples that may use this path later:

- Defects4J or GitBug-Java: Java real-bug calibration seed metadata.
- TestExplora or TestBench: generated-test benchmark seed metadata.
- Spring PetClinic REST: API/SUT smoke seed metadata after README audit.

## 5. Validation

V1 tests cover:

- valid metadata-only seed normalization;
- future API/schema candidate seeds staying metadata-only;
- registry entry vs benchmark manifest artifact routing;
- wrong intake shape, unknown candidate kind, artifact drift, secret-bearing URLs;
- dataset content, authority, headline metrics, and raw/secret fields rejected;
- duplicate `asset_id` values rejected;
- `aggregate(...)` headline shape unchanged.
- conditional Markdown presentation;
- presentation preserving aggregate headline shape and rejecting invalid seed records.
- defect-denominator readiness metadata staying future-only and headline-disabled.

Command evidence:

```text
E:\AI-Test-Platform\.venv\Scripts\python.exe -m pytest tests/test_golden_manifest_governance.py
29 passed in 0.15s

E:\AI-Test-Platform\.venv\Scripts\python.exe -m pytest tests/test_golden_manifest_governance.py tests/test_golden_manifest_governance_report.py
33 passed in 0.10s

E:\AI-Test-Platform\.venv\Scripts\python.exe -m pytest
609 passed, 4 skipped, 1 warning in 6.64s
```
