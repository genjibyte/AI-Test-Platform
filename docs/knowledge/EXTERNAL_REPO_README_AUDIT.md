# External Repo README Audit

> Date: 2026-07-21
> Status: template and empty audit ledger. No external README has been audited in this file yet.
> This file is not approval to clone into the project tree, install, download, execute, connect to
> external databases, vendor code, change schemas, or change verdicts.

## 0. Purpose

Use this file when an external asset moves from registry mention to focused README/license/runtime
audit.

The audit records facts only:

```text
external asset mention
  -> intake shape
  -> phase gate
  -> asset record block
  -> focused README audit record
  -> later owner gate before any runtime action
```

The pure validator is:

```text
app/governance/external_readme_audit.py::validate_external_repo_readme_audit
```

It validates the audit record and keeps:

```text
runtime_allowed = false
download_allowed = false
install_allowed = false
vendor_code_allowed = false
verdict_authority = false
```

## 1. Current Audit Ledger

### schemathesis-readme-2026-07-22

```yaml
schema_version: external_repo_readme_audit.v1
audit_id: schemathesis-readme-2026-07-22
audited_at: 2026-07-22
auditor: codex
asset_record:
  schema_version: external_asset_record.v1
  asset_id: schemathesis
  source_url: https://github.com/schemathesis/schemathesis
  intake_shape: readme_audit
  project_artifact: docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
  pinned_version_or_commit: "master README observed 2026-07-22; exact SHA not selected"
  license_spdx: MIT
  license_verified_at: 2026-07-22
  runtime_language: Python
  requires_network: true
  requires_docker: false
  writes_workspace: true
  secrets_or_payload_risk: true
  expected_evidence:
    - CLI command contract
    - schema failure summary
    - JUnit XML, Allure, or HAR report references
  red_lines:
    - no install
    - no execution
    - no vendor code
    - no verdict authority
  next_action: README audit only; future executor_adapter design requires owner gate
source_refs:
  - https://github.com/schemathesis/schemathesis#readme
  - https://schemathesis.readthedocs.io/en/stable/
  - https://github.com/schemathesis/schemathesis/blob/master/pyproject.toml
observed:
  license: MIT observed in repository metadata
  runtime: Python CLI/library
  input_format: OpenAPI or GraphQL schema; CLI URL/file schema or pytest integration
  output_or_evidence: CLI findings, minimal reproducer, Allure, JUnit XML, or HAR
  can_run_offline: true
  requires_network: true
  requires_docker: false
  requires_model_or_api_key: false
  writes_workspace: true
  secrets_or_payload_risk: true
project_fit:
  fit: future_adapter_candidate
  affects_artifact: future api_schema_candidate runner design
  expected_evidence:
    - command contract
    - schema failure summary
    - JUnit XML or HAR parser contract
  risks:
    - could become API automation framework if adopted too early
    - network/auth/payload handling requires isolation design
  next_action: record facts only
authority:
  runtime_allowed: false
  download_allowed: false
  install_allowed: false
  vendor_code_allowed: false
  verdict_authority: false
notes: README/docs audit only; no runtime action, dependency, or executor adoption.
```

### newman-readme-2026-07-22

```yaml
schema_version: external_repo_readme_audit.v1
audit_id: newman-readme-2026-07-22
audited_at: 2026-07-22
auditor: codex
asset_record:
  schema_version: external_asset_record.v1
  asset_id: newman
  source_url: https://github.com/postmanlabs/newman
  intake_shape: readme_audit
  project_artifact: docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
  pinned_version_or_commit: "master README observed 2026-07-22; exact SHA not selected"
  license_spdx: Apache-2.0
  license_verified_at: 2026-07-22
  runtime_language: Node.js
  requires_network: true
  requires_docker: false
  writes_workspace: true
  secrets_or_payload_risk: true
  expected_evidence:
    - collection runner command contract
    - JSON or JUnit reporter output
    - collection/environment input metadata
  red_lines:
    - no npm install
    - no collection execution
    - no vendor code
    - no verdict authority
  next_action: README audit only; future executor_adapter design requires owner gate
source_refs:
  - https://github.com/postmanlabs/newman#readme
  - https://learning.postman.com/docs/reference/newman-cli/newman-built-in-reporters/
observed:
  license: Apache-2.0 observed in repository README/license metadata
  runtime: Node.js CLI/library; README states Node.js >= v16
  input_format: Postman Collection JSON file or URL plus optional environment/globals
  output_or_evidence: CLI output, JSON reporter file, or JUnit XML reporter file
  can_run_offline: unknown
  requires_network: true
  requires_docker: false
  requires_model_or_api_key: false
  writes_workspace: true
  secrets_or_payload_risk: true
project_fit:
  fit: future_adapter_candidate
  affects_artifact: future api_collection_candidate runner design
  expected_evidence:
    - collection file or URL metadata
    - JSON or JUnit parser contract
    - environment/secrets redaction contract
  risks:
    - could become API automation framework if adopted too early
    - collection/environment variables may contain secrets or payloads
  next_action: record facts only
authority:
  runtime_allowed: false
  download_allowed: false
  install_allowed: false
  vendor_code_allowed: false
  verdict_authority: false
notes: README/docs audit only; no runtime action, dependency, or executor adoption.
```

### wiremock-readme-2026-07-22

```yaml
schema_version: external_repo_readme_audit.v1
audit_id: wiremock-readme-2026-07-22
audited_at: 2026-07-22
auditor: codex
asset_record:
  schema_version: external_asset_record.v1
  asset_id: wiremock
  source_url: https://github.com/wiremock/wiremock
  intake_shape: readme_audit
  project_artifact: docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
  pinned_version_or_commit: "master README observed 2026-07-22; exact SHA not selected"
  license_spdx: Apache-2.0
  license_verified_at: 2026-07-22
  runtime_language: Java/JVM
  requires_network: true
  requires_docker: false
  writes_workspace: true
  secrets_or_payload_risk: true
  expected_evidence:
    - stub mapping format
    - request verification evidence
    - standalone/admin API boundary
  red_lines:
    - no dependency
    - no server start
    - no Docker path
    - no payload capture
    - no verdict authority
  next_action: README audit only; future isolation_support design requires owner gate
source_refs:
  - https://github.com/wiremock/wiremock#readme
  - https://wiremock.org/docs/standalone/
observed:
  license: Apache-2.0 observed in repository README/license metadata
  runtime: Java/JVM library, standalone server, or container
  input_format: Java API, JSON files, or JSON over HTTP for mock APIs
  output_or_evidence: request verification, request journal, mappings, and logs
  can_run_offline: true
  requires_network: true
  requires_docker: false
  requires_model_or_api_key: false
  writes_workspace: true
  secrets_or_payload_risk: true
project_fit:
  fit: future_adapter_candidate
  affects_artifact: future API/integration isolation design
  expected_evidence:
    - stub mapping contract
    - request verification/journal evidence contract
    - network and payload redaction boundary
  risks:
    - could become service orchestration if adopted too early
    - record/playback or request journals may capture payloads
  next_action: record facts only
authority:
  runtime_allowed: false
  download_allowed: false
  install_allowed: false
  vendor_code_allowed: false
  verdict_authority: false
notes: README/docs audit only; no runtime action, dependency, service orchestration, or isolation adoption.
```

Do not fill this file with guesses from memory or broad knowledge packs. Each completed audit must
come from a focused source read and should cite the README/docs refs used in `source_refs`.

## 2. P0 Audit Queue

The first audit queue remains bounded to:

```text
SWE-bench
Claw-SWE-Bench
OpenHands Benchmarks
Inspect AI
TestExplora
TestBench
Defects4J
GitBug-Java
Spring PetClinic REST
Schemathesis
Newman
WireMock
Testcontainers
```

Stop after this list unless the owner explicitly widens the intake.

## 3. Audit Record Template

Use this shape for every completed audit:

```yaml
schema_version: external_repo_readme_audit.v1
audit_id:
audited_at: YYYY-MM-DD
auditor:
asset_record:
  schema_version: external_asset_record.v1
  asset_id:
  source_url:
  intake_shape:
  project_artifact:
  pinned_version_or_commit:
  license_spdx:
  license_verified_at: YYYY-MM-DD
  runtime_language:
  requires_network:
  requires_docker:
  writes_workspace:
  secrets_or_payload_risk:
  expected_evidence:
    - ...
  red_lines:
    - ...
  next_action:
  owner_gate_ref:
  readme_audit_ref:
  notes:
source_refs:
  - ...
observed:
  license:
  runtime:
  input_format:
  output_or_evidence:
  can_run_offline: true | false | unknown
  requires_network:
  requires_docker:
  requires_model_or_api_key:
  writes_workspace:
  secrets_or_payload_risk:
project_fit:
  fit: knowledge_only | metadata_seed_candidate | future_adapter_candidate | sut_reference_candidate | defer | reject_mainline
  affects_artifact:
  expected_evidence:
    - ...
  risks:
    - ...
  next_action:
authority:
  runtime_allowed: false
  download_allowed: false
  install_allowed: false
  vendor_code_allowed: false
  verdict_authority: false
notes:
```

## 4. Red Lines

- A README audit is not implementation approval.
- A README audit must not contain raw request/response payloads, tokens, cookies, credentials,
  `.env` values, database dumps, or service snapshots.
- A README audit must not set any authority field to true.
- A README audit must not create a benchmark headline, golden label, defect-discovery claim, or
  tool-quality claim.
- External runtime actions still require a later owner-approved design with candidate kind,
  command, evidence parser, isolation, and no-verdict-drift tests.
