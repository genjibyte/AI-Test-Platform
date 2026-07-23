# External Asset Phase Plan

> Date: 2026-07-21
> Status: design contract plus pure policy helper. No external database, dataset, knowledge
> runtime, tool install, clone into the project tree, executor, dependency, service
> orchestration, schema/index change, verdict change, or auto-accept is implied.

## 0. Answer

External databases, benchmarks, knowledge bases, and open-source tool code should not enter the
project in one step. They enter by evidence maturity:

```text
knowledge/registry
  -> focused README/license/runtime audit
  -> pinned manifest metadata
  -> tiny owner-approved slice or SUT target
  -> producer adapter or executor adapter
  -> optional external storage only after local ledger/report scale proves the need
```

Current status: the project has S10C API smoke report/submit/benchmark/ledger projection
presentation and S5B Golden Set manifest governance live. External assets are still
governance/support work, not runtime integration.

## 1. Category Placement

| Asset category | Stage where it can start | What is allowed now | What waits |
|---|---|---|---|
| External knowledge base | S5D/S5B0 | Curated notes, vocabulary, warnings, README audits. | Runtime RAG, vector DB, knowledge graph, or LLM Judge authority. |
| External benchmark or evaluation set | S5B metadata, S11 tiny slice | Manifest seed: URL, commit/tag, task id, license, expected evidence. | Dataset download, bulk import, headline metrics, historical DB backfill. |
| Open-source tool code | S5B0 audit, S12/S13 adapters | README/license/runtime audit and adapter design. | Install, execute, vendor code, new dependency, tool-as-core architecture. |
| External database as SUT asset | S7C reference, S11+ pilot | Schema/fixture requirement notes, audited `sut_target` metadata. | Service orchestration, DB dumps, runtime secrets, Testcontainers/Docker path. |
| External database as platform storage | S14+ only if scale proves need | No live work now. Keep local ledger/report canonical. | Postgres/vector DB/warehouse backend, network connection, telemetry export. |

Two database meanings must stay separate:

- **SUT database**: a database used by the code under test. It belongs to Asset Gate and future
  API/integration execution design.
- **Platform database**: a storage backend for TestAgent Lab itself. This is not needed while the
  local SQLite ledger, benchmark manifests, and reports remain sufficient.

## 2. Stage Ladder

| Stage | Name | External assets allowed | Red line |
|---|---|---|---|
| S5D | Governance and SOP | `knowledge_note`, `discovery_index`, curated registry entries. | Knowledge is not project truth. |
| S5B0 | README audit | `readme_audit` for P0 assets only. Scratch read outside the project tree. | No install, execution, vendoring, or dependency. |
| S5B | Golden Set manifest governance | `manifest_seed` metadata only. | No dataset content and no metric claim. |
| S7C/S8 | API smoke manifest/report denominator | Audited `sut_target` reference in `api_smoke_manifest`. | No service start, Docker, external SUT import, or executor. |
| S9/S10 | Projection and presentation | Benchmark/ledger projections over already-observed local facts. | No generic aggregate drift, DB schema/index change, or retrieval scoring change. |
| S11 | Tiny external slice pilot | 3-5 pinned `dataset_slice` or SUT cases, owner-approved. | No bulk import and no historical backfill. |
| S12 | Producer adapter | External tool output can become a submitted candidate. | Producer identity is never quality proof. |
| S13 | Executor/isolation adapter | One isolated runner such as Schemathesis/Newman, with parser tests. | No executor without candidate kind, command, evidence parser, and isolation design. |
| S14+ | External platform storage | Optional only after local ledger/report scale requires it. | No runtime DB/vector/warehouse before privacy, schema, migration, and rollback design. |
| Never as mainline | Adoption sink | None. | No auto-merge, auto-warehouse, or auto-accept. |

## 3. Current Implementation Contract

The pure helper is live:

```text
app/governance/external_assets.py
app/governance/external_readme_audit.py
app/benchmark/manifest_governance.py
app/benchmark/manifest_governance_report.py
tests/test_external_asset_phase_policy.py
tests/test_external_repo_readme_audit.py
tests/test_golden_manifest_governance.py
tests/test_golden_manifest_governance_report.py
```

It answers four questions without touching external systems:

```text
external_asset_intake_policy("manifest_seed")
external_asset_category_policy("external_benchmark_dataset")
validate_external_asset_record({...})
external_asset_intake_plan([{...}, {...}])
validate_external_repo_readme_audit({...})
validate_golden_manifest_seed({...})
golden_manifest_governance_plan([{...}, {...}])
render_golden_manifest_governance_markdown([{...}, {...}])
```

The helper is policy data only. It does not approve external execution. It exists so future design
and tests can reject phase drift before code starts.

`validate_external_asset_record(...)` enforces the asset-record block before an asset moves beyond
a casual mention. A valid record still grants no runtime authority:

```text
runtime_actions_allowed_now = False
download_allowed_now = False
install_allowed_now = False
verdict_authority = False
```

`external_asset_intake_plan(...)` validates a batch of records and returns only compact planning
buckets:

```text
by_intake_shape
by_current_status
metadata_or_reference_only_records
future_owner_gated_records
runtime_risk_records
runtime_actions_allowed_records = []
download_allowed_records = []
install_allowed_records = []
verdict_authority_records = []
```

Duplicate `asset_id` values are rejected so a future README audit or manifest seed cannot silently
overwrite another external asset.

`validate_external_repo_readme_audit(...)` validates a focused README/license/runtime audit record.
It reuses the asset-record validator and rejects audit records that attempt to authorize runtime,
download, install, vendoring, or verdict authority.

`validate_golden_manifest_seed(...)` validates S5B Golden Set `manifest_seed` records for future
benchmark drafts or the external project/benchmark registry. It rejects dataset content, authority,
secret/raw payload fields, artifact drift, duplicate seed IDs in batch plans, and headline-metric
claims. Valid seeds are metadata-only:

```text
metadata_only = True
runtime_actions_allowed_now = False
download_allowed_now = False
install_allowed_now = False
benchmark_headline_allowed_now = False
verdict_authority = False
```

`render_golden_manifest_governance_markdown(...)` is presentation only. It renders a conditional
metadata-plan audit section for supplied seeds and renders nothing for empty input. It is not
default benchmark report wiring and does not authorize metrics or dataset materialization.

## 4. Intake Shapes By Stage

| Intake shape | Earliest stage | Current handling |
|---|---|---|
| `knowledge_note` | S5D | Allowed now as curated docs only. |
| `readme_audit` | S5B0 | Allowed now as focused audit only. |
| `manifest_seed` | S5B | Allowed as metadata-only design. |
| `sut_target` | S7C | Allowed as audited manifest reference only. |
| `provenance_support` | S12 design | Metadata-only design; never verdict authority. |
| `dataset_slice` | S11 | Future owner-gated tiny slice. |
| `producer_adapter` | S12 | Future owner-gated adapter into `submit_candidate`. |
| `executor_adapter` | S13 | Future owner-gated isolated runner and parser. |
| `isolation_support` | S13 | Future owner-gated mock/container/contract support. |
| `support_only` | future | Keep as deferred reference. |
| `reject_mainline` | never | Boundary warning only. |

## 5. Examples

### Defects4J

```text
intake_shape: readme_audit -> manifest_seed -> dataset_slice
current stage: README audit or metadata only
future stage: S11 tiny pinned 3-5 case pilot
red lines: no bulk import, no historical backfill, no defect-discovery headline without verifier
```

### TestExplora / TestBench

```text
intake_shape: readme_audit -> manifest_seed
current stage: benchmark governance design
future stage: small manifest seed only after Golden Set contract
red lines: no provider leaderboard, no coverage/pass-rate-only value claim
```

### Schemathesis / Newman

```text
intake_shape: readme_audit -> executor_adapter
current stage: README audit only
future stage: S13 after API candidate kind, command contract, parser, and isolation design
red lines: no install or execution before owner approval
```

### Spring PetClinic REST

```text
intake_shape: readme_audit -> sut_target -> manifest_seed
current stage: audited reference in api_smoke_manifest only
future stage: S11/S13 API smoke SUT pilot
red lines: no service orchestration or Docker before runner design
```

### External Database

```text
if SUT database:
  intake_shape: sut_target or isolation_support
  stage: S7C reference, S11/S13 owner-gated pilot

if platform storage:
  intake_shape: support_only until S14+
  stage: after local ledger/report scale proves a backend need

red lines:
  no DB dumps, no secrets, no runtime connection, no vector/warehouse backend now
```

## 6. Next Safe Design Move

The next coding move can stay local:

The next external-asset move should stay non-runtime:

```text
S5B0 P0 README audit
```

Do not skip from the registry directly to downloads, Docker, external DB connections, or tool
execution. The judge kernel should see external assets only after they have a mapped intake shape,
an asset record block, a focused audit, an owner gate, and no-verdict-drift tests.
