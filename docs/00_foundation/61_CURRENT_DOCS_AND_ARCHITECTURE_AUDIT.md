# 61 - Current Docs And Architecture Audit

> Date: 2026-07-22
> Status: current audit and documentation governance. No code, endpoint, executor, dependency,
> schema/index, digest severity, verdict change, model call, external asset use, or
> auto-accept is implied.

## 0. Audit Result

The repository is still on the correct product thesis:

```text
candidate -> deterministic judge evidence -> advisory signals -> review digest -> ledger/report
```

The project is a candidate-evaluation harness/judge, not a test generator, API automation
framework, repair platform, provider hub, or auto-adoption workflow.

Docs were pruned again on 2026-07-21 to reduce context pollution:

- large raw knowledge packs were removed from the current docs tree;
- stale context/preflight evolution digests were removed from the current docs tree;
- the root README was rewritten as a current architecture entry;
- `CLAUDE.md` was reduced to a pointer to `AGENTS.md`;
- active docs now route through the thin layer and task-specific design docs only.
- follow-up recovery preserved the compact external project/benchmark candidate set in
  `docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` instead of restoring raw packs.

Current tracked docs tree after this pass and the external README-audit template addition:

```text
41 files
docs/
docs/00_foundation/
docs/50_benchmark/
docs/60_api_candidate/
docs/80_sop/
docs/knowledge/
```

## 1. Current Docs Shape

Current default read set:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
```

Current architecture/audit docs:

```text
docs/00_foundation/00_PROJECT_CHARTER.md
docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md
docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md
docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md
```

Current API smoke path docs:

```text
docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md
docs/60_api_candidate/01_MINIMAL_JUDGE_CONTRACT.md
docs/60_api_candidate/02_API_CANDIDATE_BOUNDARY_DESIGN.md
docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md
docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md
docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md
docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md
docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md
docs/60_api_candidate/08_S7D_API_SMOKE_MANIFEST_CARRY_THROUGH_DESIGN.md
docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md
docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md
docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md
```

Current knowledge docs:

```text
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md
docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md
```

Deleted raw knowledge/history docs can be recovered from git only for explicit archaeology. Current
project/benchmark names should be read from the compact registry first.

## 2. Deleted As Context Pollution

Removed from the current docs tree:

```text
docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md
docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md
docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md
docs/knowledge/BENCHMARK_SOURCES_AND_STRATEGY.md
docs/knowledge/INTERNET_TECH_BUSINESS_KB.md
docs/60_context_v3/CONTEXT_V3_EVOLUTION_DIGEST.md
docs/70_preflight/PREFLIGHT_EVOLUTION_DIGEST.md
```

Reason:

- they were large reference packs or historical evolution notes;
- they mixed source ideas, old roadmap language, stale access assumptions, and non-current
  implementation direction;
- their useful governance lessons are now represented by the curated digest, asset matrix, and
  compact project/benchmark registry;
- keeping them in the default tree encouraged over-reading and design drift.

## 3. Current Module Architecture

Current module boundary:

```text
app/api
  public endpoints; should normalize inputs and call pipelines, not own judge semantics

app/pipeline
  generation and submit orchestration; should persist bundles and invoke judge/report paths

app/report
  report assembly and report-only API smoke facts; should not execute services or write ledger

app/quality
  pure advisory quality and asset-sufficiency helpers

app/review
  recommendation policy and digest roll-up; digest is not a detector or verdict

app/benchmark
  run_kind-aware aggregate views and named projections; current API smoke projection/display live

app/ledger
  judged-record storage, badcase analytics, retrieval; API smoke S10A compact JSON carry and S10B
  named pure projection helper are live

app/governance
  pure design-time policy helpers; external asset phase gates, asset-record validation, and batch
  intake-plan summaries are live; README audit record validation and mandatory design reuse-check
  validation/plan summaries plus an API/interface reuse-plan sample are live; all perform no
  external actions

app/llm, app/generate, app/repair
  producer-side support; not the product center
```

No module may auto-accept, auto-merge, turn `trusted=True`, treat producer identity as quality
proof, or treat green execution as engineering value.

## 4. Live Capability Audit

Live:

```text
unit-test judge kernel
submit_candidate
run_kind hygiene
quality gate
review policy and digest
preflight
oracle-strength structural estimate
gated mutation subsystem
invariant review
mock smell
badcase ledger/retrieval
Asset Gate S1-S4A report-only Test-Level Router
S6C-S9C API smoke report/submit/projection/display path, including benchmark red-line counts
S10A API smoke compact ledger JSON carry
S10B API smoke pure ledger projection helper
S10C API smoke ledger projection presentation
S10D API smoke cross-layer projection boundary regression
S5B/S5B2 Golden Set governance metadata validation/planning and optional Markdown presentation
S5D1 external asset phase policy helper, asset-record validator, intake-plan summary, README audit
record validator/template, first Schemathesis/Newman/WireMock P0 README audit records, mandatory
design reuse-check validator/plan summary, API/interface reuse-plan sample, and docs
S5D2-S5D20 CI/PR change-set handoff helper, suggested batches, residual runtime/test warning,
completed-track reclassification, runtime doc-reference cleanup classification, and current
API-smoke progress notes, with batch-path appendix rendering, per-surface/per-batch status counts,
per-batch surface counts, per-batch paths grouped by observed git status, per-batch review
checklists, per-batch review gates, suggested verification targets, suggested commit-message hints,
per-batch warning flags, top-level human-next-actions checklist, top-level batch-action summary,
top-level batch-warning summary, top-level gate summary, top-level verification-target summary, and
S10D boundary-test coverage in the API-smoke verification target
```

Design-only:

```text
external asset README audits
optional LLM Judge calibration
```

Not built:

```text
API/interface executor
new live API candidate kinds
external SUT import
Docker/service orchestration
Defects4J/GitBug dataset slice
multi-model/provider platform
repair/adoption sink
auto-merge or auto-warehouse entry
```

## 5. Current Risks

Residual risks:

- Several active design docs still contain historical encoding damage. They are usable but not
  pleasant to read. Do not rewrite all of them unless a task touches that doc.
- S10A compact ledger JSON carry, S10B pure helper, S10C conditional Markdown presentation, and
  S10D cross-layer boundary regression are live. Do not treat them as existing ledger analytics
  changes, retrieval, signature, digest, executor, or correctness proof.
- Existing root history still has deleted docs; recover only by explicit archaeology.
- The current API smoke path is still report/projection/display only. It must not be described as
  an API executor or API correctness proof.
- Large external asset decisions remain design-only. Do not clone, install, vendor, or execute
  external assets without a named intake shape and owner gate.
- The external asset phase helper, asset-record validator, intake-plan summary, and README audit
  validator/template are policy data only. They must not be treated as approval to download
  datasets, connect databases, install tools, or vendor open-source code.

## 6. Next Safe Step

After S9C/S10D/S5D20 presentation and boundary hardening, the next implementation step should stay
in pure governance/reporting unless the owner explicitly approves a new design. Good narrow options
are:

```text
one focused external README audit record
optional final commit-batch review checklist refresh
optional final handoff markdown snapshot artifact
```

Still requires explicit owner approval before implementation:

- API/interface executor;
- external SUT import, dataset slice, or tool execution;
- SQLite columns or indexes;
- badcase signature, retrieval scoring, or existing ledger analytics changes;
- digest severity, verdict, trusted status, or auto-accept changes.

Otherwise, continue using the change-handoff helper to split final human review batches and keep
residual runtime/test changes explicit before staging.
