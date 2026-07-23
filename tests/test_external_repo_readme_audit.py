"""External README audit record tests."""
from __future__ import annotations

import pytest

from app.governance.external_assets import EXTERNAL_ASSET_RECORD_SCHEMA_VERSION
from app.governance.external_readme_audit import (
    EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION,
    ExternalRepoReadmeAuditValidationError,
    validate_external_repo_readme_audit,
)


def _asset_record(**overrides):
    record = {
        "schema_version": EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
        "asset_id": "schemathesis",
        "source_url": "https://github.com/schemathesis/schemathesis",
        "intake_shape": "readme_audit",
        "project_artifact": "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
        "pinned_version_or_commit": "master README observed 2026-07-22; exact SHA not selected",
        "license_spdx": "MIT",
        "license_verified_at": "2026-07-22",
        "runtime_language": "Python",
        "requires_network": True,
        "requires_docker": False,
        "writes_workspace": True,
        "secrets_or_payload_risk": True,
        "expected_evidence": [
            "CLI command contract",
            "schema failure summary",
            "JUnit XML, Allure, or HAR report references",
        ],
        "red_lines": [
            "no install",
            "no execution",
            "no vendor code",
            "no verdict authority",
        ],
        "next_action": "README audit only; future executor_adapter design requires owner gate",
    }
    record.update(overrides)
    return record


def _audit(**overrides):
    audit = {
        "schema_version": EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION,
        "audit_id": "schemathesis-readme-2026-07-22",
        "audited_at": "2026-07-22",
        "auditor": "codex",
        "asset_record": _asset_record(),
        "source_refs": [
            "https://github.com/schemathesis/schemathesis#readme",
            "https://schemathesis.readthedocs.io/en/stable/",
            "https://github.com/schemathesis/schemathesis/blob/master/pyproject.toml",
        ],
        "observed": {
            "license": "MIT observed in repository metadata",
            "runtime": "Python CLI/library",
            "input_format": "OpenAPI or GraphQL schema; CLI URL/file schema or pytest integration",
            "output_or_evidence": "CLI findings, minimal reproducer, Allure, JUnit XML, or HAR",
            "can_run_offline": True,
            "requires_network": True,
            "requires_docker": False,
            "requires_model_or_api_key": False,
            "writes_workspace": True,
            "secrets_or_payload_risk": True,
        },
        "project_fit": {
            "fit": "future_adapter_candidate",
            "affects_artifact": "future api_schema_candidate runner design",
            "expected_evidence": [
                "command contract",
                "schema failure summary",
                "JUnit XML or HAR parser contract",
            ],
            "risks": [
                "could become API automation framework if adopted too early",
                "network/auth/payload handling requires isolation design",
            ],
            "next_action": "record facts only",
        },
        "authority": {
            "runtime_allowed": False,
            "download_allowed": False,
            "install_allowed": False,
            "vendor_code_allowed": False,
            "verdict_authority": False,
        },
    }
    audit.update(overrides)
    return audit


def _newman_asset_record(**overrides):
    record = {
        "schema_version": EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
        "asset_id": "newman",
        "source_url": "https://github.com/postmanlabs/newman",
        "intake_shape": "readme_audit",
        "project_artifact": "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
        "pinned_version_or_commit": "master README observed 2026-07-22; exact SHA not selected",
        "license_spdx": "Apache-2.0",
        "license_verified_at": "2026-07-22",
        "runtime_language": "Node.js",
        "requires_network": True,
        "requires_docker": False,
        "writes_workspace": True,
        "secrets_or_payload_risk": True,
        "expected_evidence": [
            "collection runner command contract",
            "JSON or JUnit reporter output",
            "collection/environment input metadata",
        ],
        "red_lines": [
            "no npm install",
            "no collection execution",
            "no vendor code",
            "no verdict authority",
        ],
        "next_action": "README audit only; future executor_adapter design requires owner gate",
    }
    record.update(overrides)
    return record


def _newman_audit(**overrides):
    audit = {
        "schema_version": EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION,
        "audit_id": "newman-readme-2026-07-22",
        "audited_at": "2026-07-22",
        "auditor": "codex",
        "asset_record": _newman_asset_record(),
        "source_refs": [
            "https://github.com/postmanlabs/newman#readme",
            "https://learning.postman.com/docs/reference/newman-cli/newman-built-in-reporters/",
        ],
        "observed": {
            "license": "Apache-2.0 observed in repository README/license metadata",
            "runtime": "Node.js CLI/library; README states Node.js >= v16",
            "input_format": "Postman Collection JSON file or URL plus optional environment/globals",
            "output_or_evidence": "CLI output, JSON reporter file, or JUnit XML reporter file",
            "can_run_offline": "unknown",
            "requires_network": True,
            "requires_docker": False,
            "requires_model_or_api_key": False,
            "writes_workspace": True,
            "secrets_or_payload_risk": True,
        },
        "project_fit": {
            "fit": "future_adapter_candidate",
            "affects_artifact": "future api_collection_candidate runner design",
            "expected_evidence": [
                "collection file or URL metadata",
                "JSON or JUnit parser contract",
                "environment/secrets redaction contract",
            ],
            "risks": [
                "could become API automation framework if adopted too early",
                "collection/environment variables may contain secrets or payloads",
            ],
            "next_action": "record facts only",
        },
        "authority": {
            "runtime_allowed": False,
            "download_allowed": False,
            "install_allowed": False,
            "vendor_code_allowed": False,
            "verdict_authority": False,
        },
    }
    audit.update(overrides)
    return audit


def _wiremock_asset_record(**overrides):
    record = {
        "schema_version": EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
        "asset_id": "wiremock",
        "source_url": "https://github.com/wiremock/wiremock",
        "intake_shape": "readme_audit",
        "project_artifact": "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
        "pinned_version_or_commit": "master README observed 2026-07-22; exact SHA not selected",
        "license_spdx": "Apache-2.0",
        "license_verified_at": "2026-07-22",
        "runtime_language": "Java/JVM",
        "requires_network": True,
        "requires_docker": False,
        "writes_workspace": True,
        "secrets_or_payload_risk": True,
        "expected_evidence": [
            "stub mapping format",
            "request verification evidence",
            "standalone/admin API boundary",
        ],
        "red_lines": [
            "no dependency",
            "no server start",
            "no Docker path",
            "no payload capture",
            "no verdict authority",
        ],
        "next_action": "README audit only; future isolation_support design requires owner gate",
    }
    record.update(overrides)
    return record


def _wiremock_audit(**overrides):
    audit = {
        "schema_version": EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION,
        "audit_id": "wiremock-readme-2026-07-22",
        "audited_at": "2026-07-22",
        "auditor": "codex",
        "asset_record": _wiremock_asset_record(),
        "source_refs": [
            "https://github.com/wiremock/wiremock#readme",
            "https://wiremock.org/docs/standalone/",
        ],
        "observed": {
            "license": "Apache-2.0 observed in repository README/license metadata",
            "runtime": "Java/JVM library, standalone server, or container",
            "input_format": "Java API, JSON files, or JSON over HTTP for mock APIs",
            "output_or_evidence": "request verification, request journal, mappings, and logs",
            "can_run_offline": True,
            "requires_network": True,
            "requires_docker": False,
            "requires_model_or_api_key": False,
            "writes_workspace": True,
            "secrets_or_payload_risk": True,
        },
        "project_fit": {
            "fit": "future_adapter_candidate",
            "affects_artifact": "future API/integration isolation design",
            "expected_evidence": [
                "stub mapping contract",
                "request verification/journal evidence contract",
                "network and payload redaction boundary",
            ],
            "risks": [
                "could become service orchestration if adopted too early",
                "record/playback or request journals may capture payloads",
            ],
            "next_action": "record facts only",
        },
        "authority": {
            "runtime_allowed": False,
            "download_allowed": False,
            "install_allowed": False,
            "vendor_code_allowed": False,
            "verdict_authority": False,
        },
    }
    audit.update(overrides)
    return audit


def test_valid_external_repo_readme_audit_normalizes_without_authority():
    normalized = validate_external_repo_readme_audit(_audit())

    assert normalized["schema_version"] == EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION
    assert normalized["audit_id"] == "schemathesis-readme-2026-07-22"
    assert normalized["asset_record"]["asset_id"] == "schemathesis"
    assert normalized["asset_record"]["intake_shape"] == "readme_audit"
    assert normalized["phase_policy"]["current_status"] == "allowed_now_audit_only"
    assert normalized["asset_record"]["runtime_actions_allowed_now"] is False
    assert normalized["asset_record"]["download_allowed_now"] is False
    assert normalized["asset_record"]["install_allowed_now"] is False
    assert normalized["asset_record"]["verdict_authority"] is False
    assert normalized["observed"]["requires_network"] is True
    assert normalized["observed"]["writes_workspace"] is True
    assert normalized["observed"]["secrets_or_payload_risk"] is True
    assert normalized["observed"]["can_run_offline"] is True
    assert normalized["project_fit"]["fit"] == "future_adapter_candidate"
    assert "JUnit XML or HAR parser contract" in normalized["project_fit"]["expected_evidence"]
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["vendor_code_allowed_now"] is False
    assert normalized["verdict_authority"] is False


def test_newman_readme_audit_is_future_adapter_metadata_only():
    normalized = validate_external_repo_readme_audit(_newman_audit())

    assert normalized["audit_id"] == "newman-readme-2026-07-22"
    assert normalized["asset_record"]["asset_id"] == "newman"
    assert normalized["asset_record"]["license_spdx"] == "Apache-2.0"
    assert normalized["asset_record"]["runtime_language"] == "Node.js"
    assert normalized["phase_policy"]["current_status"] == "allowed_now_audit_only"
    assert normalized["observed"]["can_run_offline"] is None
    assert normalized["observed"]["requires_network"] is True
    assert normalized["observed"]["writes_workspace"] is True
    assert normalized["observed"]["secrets_or_payload_risk"] is True
    assert normalized["project_fit"]["fit"] == "future_adapter_candidate"
    assert normalized["project_fit"]["affects_artifact"] == (
        "future api_collection_candidate runner design"
    )
    assert "JSON or JUnit parser contract" in normalized["project_fit"]["expected_evidence"]
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["vendor_code_allowed_now"] is False
    assert normalized["verdict_authority"] is False


def test_wiremock_readme_audit_is_isolation_metadata_only():
    normalized = validate_external_repo_readme_audit(_wiremock_audit())

    assert normalized["audit_id"] == "wiremock-readme-2026-07-22"
    assert normalized["asset_record"]["asset_id"] == "wiremock"
    assert normalized["asset_record"]["license_spdx"] == "Apache-2.0"
    assert normalized["asset_record"]["runtime_language"] == "Java/JVM"
    assert normalized["phase_policy"]["current_status"] == "allowed_now_audit_only"
    assert normalized["observed"]["can_run_offline"] is True
    assert normalized["observed"]["requires_network"] is True
    assert normalized["observed"]["writes_workspace"] is True
    assert normalized["observed"]["secrets_or_payload_risk"] is True
    assert normalized["project_fit"]["fit"] == "future_adapter_candidate"
    assert normalized["project_fit"]["affects_artifact"] == (
        "future API/integration isolation design"
    )
    assert "request verification/journal evidence contract" in (
        normalized["project_fit"]["expected_evidence"]
    )
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["vendor_code_allowed_now"] is False
    assert normalized["verdict_authority"] is False


def test_external_repo_readme_audit_accepts_unknown_offline_capability_as_none():
    audit = _audit(observed={
        **_audit()["observed"],
        "can_run_offline": "unknown",
    })

    normalized = validate_external_repo_readme_audit(audit)

    assert normalized["observed"]["can_run_offline"] is None


@pytest.mark.parametrize(
    "field",
    [
        "runtime_allowed",
        "download_allowed",
        "install_allowed",
        "vendor_code_allowed",
        "verdict_authority",
    ],
)
def test_external_repo_readme_audit_rejects_any_authority_flag(field):
    audit = _audit(authority={
        **_audit()["authority"],
        field: True,
    })

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match=field):
        validate_external_repo_readme_audit(audit)


def test_external_repo_readme_audit_rejects_forbidden_secret_fields():
    audit = _audit(notes={"token": "do-not-store"})

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="notes.token"):
        validate_external_repo_readme_audit(audit)


def test_external_repo_readme_audit_rejects_secret_bearing_source_ref():
    audit = _audit(source_refs=["https://example.test/readme?token=secret"])

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="source_refs\\[0\\]"):
        validate_external_repo_readme_audit(audit)


def test_external_repo_readme_audit_rejects_invalid_nested_asset_record():
    audit = _audit(asset_record=_asset_record(intake_shape="external_database"))

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="asset_record invalid"):
        validate_external_repo_readme_audit(audit)


def test_external_repo_readme_audit_rejects_unknown_fit_or_fields():
    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="project_fit.fit"):
        validate_external_repo_readme_audit(_audit(project_fit={
            **_audit()["project_fit"],
            "fit": "useful",
        }))

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="raw payload"):
        validate_external_repo_readme_audit(_audit(observed={
            **_audit()["observed"],
            "raw_response": "do-not-store",
        }))

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="unknown fields"):
        validate_external_repo_readme_audit(_audit(observed={
            **_audit()["observed"],
            "maintenance_status": "active",
        }))


def test_external_repo_readme_audit_requires_dates_lists_and_booleans():
    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="audited_at"):
        validate_external_repo_readme_audit(_audit(audited_at="2026/07/21"))

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="source_refs"):
        validate_external_repo_readme_audit(_audit(source_refs=[]))

    with pytest.raises(ExternalRepoReadmeAuditValidationError, match="requires_docker"):
        validate_external_repo_readme_audit(_audit(observed={
            **_audit()["observed"],
            "requires_docker": "false",
        }))
