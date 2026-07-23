# Knowledge Base - Agent Memory

These files are external lessons and reference material. They are not current architecture and
not proof that a feature exists.

For current state, do not start here. Read:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
```

Then return here only when the active task needs an external lesson, repo intake, benchmark
source, or skill/SOP pattern. For project or benchmark names, start with
`EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` before opening deleted raw packs.

## Files

| File | Use |
|---|---|
| `EXTERNAL_ASSET_MAPPING_MATRIX.md` | Required mapping matrix for external assets. Every asset must map to an intake shape before design or implementation. |
| `EXTERNAL_ASSET_PHASE_PLAN.md` | Stage ladder for when knowledge bases, benchmarks, datasets, SUTs, tool code, and external databases may move beyond registry/audit. |
| `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` | Compact registry of current in-repo benchmarks and external project/benchmark candidates retained after raw pack pruning. |
| `EXTERNAL_REPO_README_AUDIT.md` | Template and ledger for focused external README/license/runtime audits. |
| `OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md` | Curated digest of the 2026-07 open-source reuse note; filters useful adapter/sandbox/governance lessons through the current judge-first boundary. |

Pruned on 2026-07-21:

```text
AGENT_HARNESS_EVALUATION_KB.md
EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md
EXTERNAL_AGENT_AND_TESTGEN_KB.md
BENCHMARK_SOURCES_AND_STRATEGY.md
INTERNET_TECH_BUSINESS_KB.md
```

These were large reference packs, not current architecture. The compact project/benchmark asset
set is preserved in `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`. Recover raw packs from git
history only for explicit archaeology or a focused source audit.

## Knowledge Architecture

Role in the project three-layer read mechanism:

```text
Layer 1: this index + EXTERNAL_ASSET_MAPPING_MATRIX.md
Layer 2: only the named knowledge/design file required by the active design
Layer 3: external repo README audits, benchmark reports, ledger records, or source evidence
```

Knowledge docs should be read as patterns, warnings, and design vocabulary. They should not be
treated as implementation truth or an automatic backlog.

The local file `D:\AI_TEST_AGENT_OPEN_SOURCE_KNOWLEDGE_BASE_2026-07.md` is intentionally not a
canonical project doc. Use the curated digest
`OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md` first; open the source file only for a focused audit or
when the owner explicitly asks for it.

Design knowledge gate:

```text
Every design must read docs/knowledge/README.md and
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md before using external assets.
If an external asset is mentioned, the design must name its intake shape.
```

## Where To Embed New Knowledge

After the intake shape is chosen, put the summary in the narrowest doc that owns the project
artifact. Do not spread one source across many docs unless the source has multiple distinct intake
shapes.

| Intake shape | Summary form | Primary destination |
|---|---|---|
| `knowledge_note` | Design lesson, metric, warning, or vocabulary. | The task-routed design doc; use `OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md` for the curated open-source reuse digest. |
| `readme_audit` | Focused README/license/runtime facts. | `EXTERNAL_REPO_README_AUDIT.md`; mirror only the compact asset row in `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`. |
| `manifest_seed` | Pinned URL, commit/tag, task id, license, risk, and expected evidence. | `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` and `docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md`. |
| `dataset_slice` | Owner-gated tiny-slice design, never raw imported rows. | `docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md` until a slice-specific design exists. |
| `producer_adapter` | Candidate-input adapter boundary. | `docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md`; for API producers also check `docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`. |
| `executor_adapter` | Runner command, compact evidence parser, isolation, and no-verdict-drift tests. | `docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md` plus `docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md`. |
| `sut_target` | SUT reference metadata for smoke-manifest design. | `docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md` and `docs/60_api_candidate/08_S7D_API_SMOKE_MANIFEST_CARRY_THROUGH_DESIGN.md`. |
| `isolation_support` | Mock/container/contract isolation design note. | `docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md`; keep source facts in `EXTERNAL_REPO_README_AUDIT.md`. |
| `provenance_support` | Advisory producer trace and `run_kind` field mapping. | `docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md` and `docs/50_benchmark/43_RUN_KIND_DESIGN.md`. |
| `discovery_index` | Compact source list or deferred asset row. | `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`. |
| `support_only` | Deferred reference with a concrete revisit trigger. | `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`. |
| `reject_mainline` | Boundary warning explaining why it is not project mainline. | `docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md`. |

The pure helper `app.governance.knowledge_embedding_destination(...)` mirrors this routing table
for tests and handoff checks. It is documentation metadata only and grants no clone, copy, install,
vendor, execute, verdict, or trust authority.

When importing a new external lesson, classify it first:

```text
adopt      -> strengthens candidate judging, evidence, comparison, RCA, or asset sufficiency
downgrade  -> useful producer-side support, demo aid, or research note
reject     -> prompt race, generic RAG/platform, auto-accept, auto-merge, or broad web/backend drift
```

For Skill-style knowledge, use the same filter. A Skill should encode a bounded judge workflow:
trigger, inputs, steps, evidence, red lines, output, and fallback. It should not smuggle in a new
product surface.

The first project-local Skill/SOP templates are in
`docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md`. They are operating procedures, not installed
Codex Skills and not runtime agent workflows. The first pure readiness gate for turning these
templates into future Skill blueprints is `app/governance/skill_sop.py`, with tests in
`tests/test_judge_skill_sop.py`. A passing blueprint means ready for design review only, not ready
for Skill installation.

## Caveat

Some deleted historical knowledge docs mentioned planned paths such as `docs/TASKS.md`,
`docs/HANDOFF.md`, `docs/RUN_POLICY.md`, `docs/QUALITY_GATE.md`, `artifacts/runs/`, or `skills/`.
Do not treat those mentions as current repo facts.

Built capabilities must be verified from code and active docs. Current live areas include:

- `run_kind` hygiene
- quality gate and review policy
- gated mutation subsystem
- invariant review
- mock smell
- badcase ledger and retrieval
- producer-agnostic `submit_candidate`
- Asset Gate S1-S4A, including report-only Test-Level Router; not a live executor
- Golden Set manifest governance for metadata-only `manifest_seed` records; not a dataset slice
  or headline metric path
- Agent/Harness external evaluation lessons are retained only through the curated governance
  digest; the project does not become a prompt-based evaluator or multi-agent workflow platform.

External asset lists should first pass through `EXTERNAL_ASSET_MAPPING_MATRIX.md`, then through
`EXTERNAL_ASSET_PHASE_PLAN.md` when the question is "when can this be introduced?". The compact
current project/benchmark list lives in `EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`. Do not
clone, vendor, copy, install, execute, download, or connect to tools/data/services from an external
list before the asset has an intake shape, a stage gate, a small README audit when needed, and an
owner-approved design deciding its role.

Focused README audits should be recorded in `EXTERNAL_REPO_README_AUDIT.md` and validated with
`app/governance/external_readme_audit.py`. A valid audit record is still fact metadata only.

External source vocabulary must be normalized to project intake shapes. For example,
`repair_adapter` is not a current allowed intake shape; it is support-only until a future design
treats the repairer output as a new candidate. `knowledge_reference` maps to `knowledge_note`.

## Current North-Star

TestAgent Lab is an execution-based judge for test candidates from any producer.

Every new design should strengthen Candidate, Provenance, Badcase, or Asset Gate. If a change only
improves the built-in generator's compile/pass rate, downgrade it unless it fixes a false-trust or
oracle-safety issue.

Historical benchmark DB rows without `run_kind` remain read-only and heuristic-labeled.
