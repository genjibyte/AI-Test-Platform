# 58 - Governance, Recovery, And Reuse Preparation

> Date: 2026-07-20
> Status: documentation and architecture-prep only. No code, endpoint, executor, dependency,
> external clone, benchmark import, model call, repair loop, automation workflow, schema change,
> ledger change, digest severity change, or verdict change is implied.

## 0. Purpose

This document reconciles the external open-source reuse note
`D:\AI_TEST_AGENT_OPEN_SOURCE_KNOWLEDGE_BASE_2026-07.md` with the current TestAgent Lab docs.

The source note is useful, but not authoritative. Its access dates, roadmap, priorities, and URLs
may be stale or mismatched to this repo. Current active docs, verified code, and AGENTS rules win.

The goal is to prepare the next design by improving five areas:

| Area | Owner score | Project response |
|---|---:|---|
| Documentation governance | 8/10 | Keep the three-layer read model; add a design-prep and recovery layer. |
| Context recovery | 5/10 | Add a small recovery packet so a future agent can resume without reading all docs. |
| Skill/SOP readiness | 2/10 | Define judge-use SOP templates plus a metadata-only blueprint readiness gate; do not create a new platform surface. |
| External asset intake governance | 6/10 | Add asset-record and vocabulary-normalization gates before any integration. |
| Automation constraints | 4/10 | Define an automation ladder that starts at report-only validation and preserves verdicts. |

## 1. Reconciliation Rule

External knowledge is classified before it changes architecture:

```text
adopt      -> strengthens candidate judging, evidence, comparison, RCA, or asset sufficiency
downgrade  -> useful adapter/support idea, but not current mainline
reject     -> would turn the project into generator, API automation, task platform, or auto-adoption
```

Adopt from the source note:

- unified candidate/evidence/verdict vocabulary;
- strict separation of declared producer evidence from platform-observed evidence;
- producer-agnostic comparison and provenance;
- failure families such as compile, execution, oracle, mock, asset, environment, product,
  platform, and unknown;
- supply-chain and sandbox checks before external assets are used;
- compact API evidence and redaction discipline.

Downgrade from the source note:

- a fixed 90-day implementation roadmap;
- broad P0 tool ingestion lists;
- Repair Agent loops;
- model gateways, observability stacks, PR comment sinks, and agent orchestration;
- external API executors before the current `junit_api_candidate` report-only path is proved.

Reject as mainline:

- rewriting the judge into LangGraph/PydanticAI or any workflow framework;
- building a generic provider/model gateway;
- bulk-importing benchmarks;
- making an LLM Judge the final scorer;
- letting repairers modify production code, business expected values, or existing tests;
- treating coverage, green execution, or producer identity as value proof.

## 2. Architecture Recovery Packet

When a future session needs to resume design work, read this packet in order:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md
docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
```

Then route by task:

```text
API/interface report path -> docs/60_api_candidate/03-07
human labels / RCA        -> docs/50_benchmark/56 + docs/50_benchmark/57
Skill/SOP usage           -> docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md
external reuse            -> docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md
external asset intake     -> docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md + docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md + docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
```

The recovery packet is intentionally small. Historical docs and large knowledge packs are Layer 3
only.

## 3. Current Architecture Readiness

The current architecture is ready for design work, not broad integration work:

```text
Candidate input
  -> current Java/Maven judge
  -> observed evidence
  -> advisory quality signals
  -> review digest
  -> badcase/benchmark projections
  -> report with NEED_HUMAN_REVIEW and trusted=False
```

S6/S10 API work has moved only as far as compact evidence, smoke manifest validation,
report-only submit carry, report-only denominator eligibility, separate benchmark projection
display, compact ledger JSON carry, and a pure ledger projection helper:

```text
junit_api_candidate
  -> report-only api_evidence validation
  -> report-only wiring
  -> pure api_smoke_manifest.v1 validator
  -> submit carry for candidate_kind/api_evidence/api_smoke_manifest
  -> report-only api_smoke_denominator eligibility
  -> named benchmark projection and conditional markdown display
  -> compact ledger JSON carry
  -> named pure ledger projection helper
  -> no executor
```

The next architecture step should carry more proof metadata through the same report path before
starting new execution machinery.

## 4. External Asset Gate

Before any external tool, repo, dataset, or service support enters a design, require:

```text
asset name
-> intake shape from EXTERNAL_ASSET_MAPPING_MATRIX.md
-> asset record block
-> focused README/license/runtime audit when needed
-> owner gate for implementation
-> no-verdict-drift tests
```

Minimum asset record block:

```text
asset_id:
source_url:
intake_shape:
project_artifact:
pinned_version_or_commit:
license_spdx:
license_verified_at:
runtime_language:
requires_network:
requires_docker:
writes_workspace:
secrets_or_payload_risk:
expected_evidence:
red_lines:
next_action:
```

This is documentation metadata first. It does not authorize cloning, installing, running, or
vendoring the asset.

Stage placement is now explicit in:

```text
docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
app/governance/external_assets.py
```

The pure helper also validates asset record blocks via
`validate_external_asset_record(...)` and summarizes batches through
`external_asset_intake_plan(...)`. The README audit helper validates focused audit records through
`validate_external_repo_readme_audit(...)`. A valid record, plan, or README audit is still metadata
only: it grants no download, install, external execution, database connection, vendoring, or
verdict authority.

Current answer:

- knowledge bases and README audits may enter now as docs only;
- benchmark/evaluation sets may enter as `manifest_seed` metadata in Golden Set governance;
- tiny dataset slices or SUT targets are future owner-gated pilots;
- open-source tools become producer/executor/isolation adapters only after their candidate kind,
  command, evidence parser, isolation, and no-verdict-drift tests are designed;
- external databases as platform storage are S14+ only, after local ledger/report scale proves the
  need.

## 5. Automation Ladder

Automation must climb one rung at a time:

| Rung | Meaning | Allowed now? |
|---|---|---:|
| Report-only validation | Validate compact facts or manifests without execution. | yes |
| Report carry | Carry validated facts through submit/report without changing runner. | design next |
| Existing-runner execution | Use the current Maven/Surefire judge only. | owner-gated |
| External executor adapter | Add one external runner such as Schemathesis/Newman. | future gated |
| Repair loop | Produce a new candidate from failure evidence. | future gated |
| Adoption sink | Push, merge, warehouse, or auto-accept tests. | no |

Every rung must preserve:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
producer provenance is context only
green execution is not value proof
no raw secrets, payloads, .env, DB dumps, or service snapshots
```

## 6. Skill/SOP Readiness

Skillization should mean reusable operating procedures for using the judge, not a runtime agent
platform. Generation-oriented Skill articles can be reused as a pattern, but the project adapts
that pattern to candidate evaluation: Skill captures a safe judge workflow; the judge kernel still
collects evidence and owns the report.

The first template set is:

```text
docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md
```

Those SOPs should cover:

- unit-test candidate evaluation;
- `junit_api_candidate` report-only review;
- Asset Gate review;
- badcase/RCA labeling;
- external asset intake;
- CI/PR handoff without pushing.

Any future Codex Skill or agent workflow should be generated from these SOPs only after the SOP is
stable and after its blueprint passes the metadata-only readiness gate:

```text
app/governance/skill_sop.py
tests/test_judge_skill_sop.py
```

The first ready-for-review plan is
`app.governance.candidate_eval_skill_readiness_plan(...)`. It covers `unit-test-candidate-eval`
and `junit-api-candidate-report-review` as future Skill blueprints, not installed Skills.

## 7. Next Design Preparation

Recommended next bounded designs:

1. **S10C API smoke ledger projection presentation, if explicitly approved**: S10A compact
   `JudgedRecord` JSON carry and S10B pure projection helper are live. The next implementation
   slice must be presentation only over existing helper output. No SQLite columns/indexes, badcase
   signatures, retrieval scoring, existing ledger analytics changes, or digest signals without
   separate approval.
2. **S5D SOP hardening**: S5D2/S5D3 are live as a pure change-set handoff and suggested-batch
   helper. Future SOP work may add more concrete checklists or Skill blueprints, but it must stay
   metadata/design-only unless separately approved.
3. **External asset phase policy / P0 README audit**: use
   `docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md` and audit only the first list in
   `EXTERNAL_ASSET_MAPPING_MATRIX.md`, record facts, and stop. No install.
4. **Golden set governance**: use external benchmark knowledge only as manifest seed language,
   not as bulk dataset ingestion.

## 8. Definition Of Done

This preparation layer is useful if future work can answer:

- which active docs must be read first;
- which external source claims are adopted, downgraded, or rejected;
- what asset metadata is required before any integration;
- which automation rung a design is proposing;
- which SOP describes the safe workflow;
- how `NEED_HUMAN_REVIEW` and `trusted=False` stay fixed;
- why historical docs and broad knowledge packs are not being treated as current plans.
