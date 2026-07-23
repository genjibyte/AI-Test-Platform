# Work Log - Current Snapshot

> Refreshed: 2026-07-23
> Purpose: one short handoff file. Read this first, then route to the few docs needed for the
> task. Do not turn the knowledge base into a default read pile.

## 1. Product Thesis

TestAgent Lab is an execution-based judge for test candidates from any producer.

It does not claim that generated tests are valuable. A candidate only becomes reviewable after:

```text
compile -> execute -> quality gate -> advisory signals -> review digest -> report
```

The final conclusion remains:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
```

## 2. Current Architecture Map

Current runtime shape:

```text
Producer entries
  built-in generator (legacy failed exploration) -> app.pipeline.generate_pipeline.run_generation
  submit_candidate   -> app.pipeline.submit_pipeline.run_external_candidate
    -> common generation bundle

Judge kernel
  repo import / workspace
  -> target select
  -> bounded context + tiny asset_facts
  -> preflight
  -> write candidate test
  -> Maven/Surefire execution
  -> JaCoCo coverage delta

Report and signals
  app.report.generation_report.assemble_generation_report
    -> quality gate
    -> review policy
    -> oracle strength
    -> mock smell
    -> asset sufficiency
    -> test level router, report-only
    -> Java test framework facts, report-only
    -> review digest
    -> conclusion = NEED_HUMAN_REVIEW, trusted = False

Comparison and memory
  benchmark runner -> BenchCaseResult / BenchReport -> run_kind-filtered aggregates
  ledger ingest    -> JudgedRecord -> analytics / retrieval
  validation line   -> automated evidence + human/golden label readiness
                     -> Golden Set defect-denominator readiness

Project progress
  app.governance.project_progress_snapshot()
    -> advisory weighted completion estimate
    -> current overall_completion_percent ~= 71
    -> no runtime/git/executor/verdict/trust authority
  app.governance.landing_readiness_snapshot(...)
    -> progress + supplied labels + supplied manifest_seed readiness rollup
    -> current landing_stage = pre_80_landing_readiness_gaps
    -> review_questions + evidence_checklist for human audit
    -> no persistence/headline/dataset/verifier/verdict/trust authority
  app.governance.validate_landing_readiness_snapshot(...)
    -> schema/review-aid/no-authority boundary validation
    -> typed percent/stage/source/input consistency validation
    -> derived consistency across blockers, inputs, metric counts, review aids, and checklist status
  app.governance.landing_readiness_blocker_summary(...)
    -> blocker-family planning projection over a validated snapshot
    -> no workspace scan/evidence collection/release authority
  app.governance.validate_landing_readiness_blocker_summary(...)
    -> blocker-summary handoff-artifact boundary validation
    -> no source snapshot recompute/evidence collection/release authority
  app.governance.render_landing_readiness_markdown(...)
    -> optional human handoff presentation over an existing snapshot
    -> no recompute/default-report wiring/release authority
  app.governance.render_landing_readiness_blocker_summary_markdown(...)
    -> optional human handoff presentation over an existing blocker summary
    -> no source recompute/default-report wiring/release authority
  S6 landing-readiness governance
    -> frozen for closure after S6Q
    -> no S6R/S6S-style hardening unless a concrete high-risk boundary bug is found
    -> next progress must come from one joint human-label + Golden Set evidence slice
    -> API/interface implementation design is lower priority until that joint slice exposes a concrete need

Change-set handoff
  app.governance.change_handoff_plan(...)
    -> supplied status/evidence rows only
    -> human-review commit batches, including landing readiness snapshots
    -> no git read/stage/commit/push or verdict/trust authority
```

Module boundaries:

- `app/pipeline/` orchestrates flows and persists job bundles; it should not own quality logic.
- `app/report/` shapes evidence into the review report; it should not execute Maven, mutate repos,
  or write ledger records.
- `app/quality/` owns pure advisory signal helpers; they should not read `.env`, call models,
  write DB rows, or change verdicts.
- `app/review/` owns recommendation and digest roll-up; digest reads existing signals and does not
  become a new detector.
- `app/benchmark/` compares judged cases and projects compact facts; headline views must filter
  `run_kind="real"`.
- `app/ledger/` stores and retrieves judged records; precipitation is best-effort and must not
  change benchmark outcomes.
- `app/governance/` owns pure policy/readiness/handoff helpers; it should not read git by itself,
  stage changes, execute external tools, call models, or mutate verdict/trust state.
- `app/llm/`, `app/generate/`, `app/repair/`, and prompt/context tuning are producer-side support,
  not product center. The built-in JUnit generator is a legacy failed exploration retained only as
  a removable compatibility producer.

Architecture invariants:

- Every producer enters the same judge/report path.
- Provenance is context, never quality proof.
- Asset Gate and Test-Level Router are advisory; S4A is report-only and launches no executor.
- Java test framework facts are advisory; submit candidates may optionally declare the Java test
  framework, but JUnit/TestNG visibility does not install dependencies, mutate POMs, change
  runner, or affect verdict/trust.
- JUnit generation is legacy producer support, not the product center. Do not let prompt/pass-rate
  cleanup displace harness, evidence, Asset Gate, badcase, or API/interface candidate evaluation.
- Benchmark/ledger carry fields are compact projections, not new scoring systems.
- Project progress percent is advisory planning metadata; it is not release readiness, product
  acceptance, or permission to add gated runtime work.
- Human/golden label readiness is advisory; it can say which metrics are computable from supplied
  labels, but it does not persist labels, create headline claims, or change verdict/trust.
- Golden Set denominator readiness is metadata-only; it identifies future denominator candidates
  but does not materialize datasets, execute verifiers, or create defect-discovery headlines.
- Landing readiness rollup only combines existing readiness facts; it is not a release gate,
  headline metric, dataset approval, verifier approval, or verdict/trust signal.
- S6 landing-readiness governance is frozen for normal progress work. Do not add another
  validator/projection/Markdown handoff layer unless there is a concrete high-risk boundary bug.
  The next progress slice must be a single human-label + Golden Set evidence closure, not two
  separate tracks. API/interface implementation design is lower priority until that joint slice
  exposes a concrete need.
- Change-set handoff is advisory human-review guidance; batch names do not authorize staging,
  committing, pushing, or keeping an unreviewed path.
- No layer may auto-accept, auto-merge, or turn `trusted` true.

## 3. Current Core Boundary

Freeze and protect:

- Repo Import / Maven Judge / Surefire / JaCoCo
- Candidate Submit
- Quality Gate
- Preflight
- Mutation, gated off by default
- Invariant Review
- Mock Smell
- Badcase Ledger
- Review Digest
- Benchmark Manifest
- Report

Downgraded producer-side support:

- LLM Client
- Prompt Builder
- Built-in JUnit Generator (legacy failed exploration; removable compatibility producer)
- Compile Repair
- Context Prompt Tuning

Rejected mainline:

- prompt pile-up
- generated pass-rate race
- multi-provider platform
- complex RAG
- large MCP or web backend
- automatic adoption / auto-merge / auto-warehouse entry

## 4. Current Asset Gate State

Implemented:

- `review_summary["asset_sufficiency"]`
- digest flags for Asset Gate findings
- tiny `bundle["asset_facts"]` persisted by both generation and submit pipelines
- compact benchmark carry fields on `BenchCaseResult`
- compact ledger carry fields on `JudgedRecord`
- descriptive benchmark/ledger breakdown helpers
- benchmark markdown Asset Gate RAW and HEADLINE(real-only) sections
- S3D audit completed; real-only benchmark headline explicitly excludes `external`
- S4 Test-Level Router boundary designed as report-only and owner-gated
- S4 audit completed; S4A report-only implementation design drafted
- S4A report-only Test-Level Router implemented as report field only
- S2 noise rule: dependency artifacts corroborate source/target hints; they do not trigger
  API/integration risks by themselves

Important files:

```text
app/quality/asset_sufficiency.py
app/quality/test_level_router.py
app/report/generation_report.py
app/report/java_test_framework.py
app/review/review_digest.py
app/api/submit_candidate.py
app/pipeline/generate_pipeline.py
app/pipeline/submit_pipeline.py
app/benchmark/models.py
app/benchmark/runner.py
app/benchmark/report_md.py
app/benchmark/validation_line.py
app/benchmark/manifest_governance.py
app/ledger/models.py
app/ledger/ingest.py
app/ledger/analytics.py
app/governance/landing_readiness.py
app/governance/landing_readiness_report.py
app/governance/project_progress.py
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md
```

## 4.5 Current Governance And Reuse State

Implemented as documentation/design prep:

- `docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md` reconciles the 2026-07 external
  open-source reuse note with the current judge-first boundary.
- `docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md` is the curated digest to read instead
  of treating `D:\AI_TEST_AGENT_OPEN_SOURCE_KNOWLEDGE_BASE_2026-07.md` as canonical project state.
- `docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md` drafts judge-use SOP templates for candidate
  eval, API report review, Asset Gate review, badcase/RCA, external asset intake, and CI handoff.
  S5D28 adds a pure Skill/SOP blueprint readiness gate so generation-oriented Skill ideas can be
  adapted into evaluation workflows without installing Skills or changing the judge runtime.
- `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md` now includes source-vocabulary normalization
  and a required asset record block for any external asset that moves beyond a knowledge mention.
- `docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` restores the compact current
  in-repo benchmark + external project/benchmark candidate registry after raw knowledge-pack
  pruning. It is the first stop for names such as SWE-bench, Defects4J, TestExplora,
  Schemathesis, Newman, WireMock, and Testcontainers.
- `docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md` now answers when external knowledge bases,
  benchmark/evaluation sets, dataset slices, SUTs, open-source tool code, and external databases
  may move beyond registry/audit. The matching pure policy helper lives in
  `app/governance/external_assets.py`; it also validates asset record blocks, mandatory design
  reuse checks, summarizes batch intake plans, routes new knowledge summaries to destination docs,
  and performs no external action.
- `docs/knowledge/EXTERNAL_REPO_README_AUDIT.md` is now the focused README/license/runtime audit
  ledger and template. S5D24-S5D26 record completed P0 audits for Schemathesis, Newman, and
  WireMock as metadata-only future executor/isolation evidence. Its pure validator lives in
  `app/governance/external_readme_audit.py` and grants no runtime authority.
- `docs/knowledge/README.md` now includes a "Where To Embed New Knowledge" routing table. The pure
  helper `app.governance.knowledge_embedding_destination(...)` mirrors it for tests and handoff
  checks, deciding whether a source belongs in a task design doc, README audit ledger, external
  registry, Golden Set governance, API candidate docs, provenance docs, or boundary notes.
- `app/governance/skill_sop.py` validates metadata-only judge Skill/SOP blueprints and summarizes
  readiness plans. `candidate_eval_skill_readiness_plan(...)` covers the first two future
  evaluation Skill candidates, `unit-test-candidate-eval` and
  `junit-api-candidate-report-review`, as design-review assets only.
- `docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md` records the current docs and
  module architecture audit after the 2026-07-21 pruning.
- Superseded per-phase docs and old foundation drafts were pruned from the working docs tree on
  2026-07-20. Recover them from git history only for explicit archaeology.
- Large raw knowledge packs plus stale context/preflight evolution digests were pruned from the
  working docs tree on 2026-07-21. Recover them from git history only for explicit archaeology or
  focused source audit.
- Follow-up recovery note: benchmark manifests and runner code were not pruned. External project
  and benchmark candidates are now preserved in the compact registry instead of the deleted raw
  packs.
- Legacy-change audit on 2026-07-21 kept the report-only API smoke, external-asset governance,
  Golden Set manifest governance, and docs-pruning tracks; stale runtime references to pruned docs
  were removed from comments/docstrings only.

These docs do not approve external execution, adapters, repair loops, model gateways,
observability stacks, PR sinks, benchmark imports, or automation workflows. They are context
recovery and governance rails for the next design.

## 4.6 Current Change-Set Handoff Snapshot

Observed on 2026-07-23 after S6 governance freeze validation:

```text
branch: main
unpushed_commits: 0
staged_changes_present: False
total_changes: 131
by_status: {'untracked': 50, 'modified': 49, 'deleted': 32}
blocking_flags: []
ready_for_human_handoff: True
warning_flags: ['docs_prune_requires_owner_awareness', 'untracked_files_present', 'dirty_worktree_not_staged']
batch_action_counts: {'keep': 5, 'keep_with_owner_awareness': 1}
batch_warning_counts: {'untracked_paths_present': 5, 'docs_prune_requires_owner_awareness': 1}
```

Suggested human-review batches:

```text
1. api_smoke_report_projection
   action: keep
   paths: 34
   status: {'untracked': 19, 'modified': 15}
   commit hint: Add API smoke report projection carry

2. java_framework_neutrality
   action: keep
   paths: 4
   status: {'untracked': 3, 'modified': 1}
   commit hint: Add Java test framework neutrality facts

3. landing_readiness_snapshots
   action: keep
   paths: 13
   status: {'untracked': 8, 'modified': 5}
   commit hint: Add landing readiness snapshots

4. governance_helpers
   action: keep
   paths: 19
   status: {'untracked': 18, 'modified': 1}
   commit hint: Add governance handoff helpers

5. active_docs_and_handoff_context
   action: keep
   paths: 29
   status: {'modified': 27, 'untracked': 2}
   commit hint: Refresh active docs and handoff context

6. historical_docs_prune
   action: keep_with_owner_awareness
   paths: 32
   status: {'deleted': 32}
   commit hint: Prune historical docs from active tree
```

Human next actions:

```text
- review untracked paths in each keep batch before staging
- confirm owner awareness before staging docs-prune batch
- rerun suggested verification targets for each batch before commit
- human may stage reviewed batches separately; agent must not stage or push
```

This snapshot is advisory and should be regenerated before a final local commit. It does not stage,
commit, push, merge, grant verdict authority, or change trusted status.

Latest validation:

```text
41 passed
71 passed, 1 warning
62 passed
123 passed, 1 warning
427 passed, 4 skipped, 1 warning
430 passed, 4 skipped, 1 warning
435 passed, 4 skipped, 1 warning
63 passed in 0.45s (S7C target tests)
492 passed, 4 skipped, 1 warning in 6.37s
501 passed, 4 skipped, 1 warning in 5.09s
509 passed, 4 skipped, 1 warning in 6.39s
515 passed, 4 skipped, 1 warning in 5.55s
39 passed in 0.17s (API smoke targeted tests after S9A + redundant-test prune)
518 passed, 4 skipped, 1 warning in 5.76s
6 passed in 0.07s (S9A audit: top-level run_kind authority)
519 passed, 4 skipped, 1 warning in 5.88s
25 passed in 0.26s (S9B benchmark markdown target tests)
521 passed, 4 skipped, 1 warning in 6.17s
26 passed in 0.24s (S9B render-order audit target tests)
522 passed, 4 skipped, 1 warning in 5.48s
47 passed in 0.30s (S10 ledger design adjacent targeted tests)
522 passed, 4 skipped, 1 warning in 5.63s
522 passed, 4 skipped, 1 warning in 5.46s (docs/architecture prune audit)
100 passed, 1 warning in 3.04s (benchmark/submit/ledger registry recovery target tests)
522 passed, 4 skipped, 1 warning in 5.91s (external project/benchmark registry recovery)
26 passed in 0.33s (S10A compact API smoke ledger carry target tests)
524 passed, 4 skipped, 1 warning in 7.11s (S10A full validation)
21 passed in 0.34s (S10B pure API smoke ledger projection target tests)
27 passed in 0.21s (S10B projection + ledger carry target tests)
530 passed, 4 skipped, 1 warning in 5.60s (S10B full validation)
11 passed in 0.10s (external asset phase policy target tests)
26 passed in 0.14s (external asset phase policy + asset-record validator target tests)
30 passed in 0.18s (external asset intake-plan target tests)
30 passed in 0.12s (external asset intake-plan target tests after batch summary)
541 passed, 4 skipped, 1 warning in 7.07s (external asset phase policy full validation)
556 passed, 4 skipped, 1 warning in 7.83s (external asset record validator full validation)
560 passed, 4 skipped, 1 warning in 5.66s (external asset intake-plan full validation)
42 passed in 0.10s (external README audit validator target tests)
572 passed, 4 skipped, 1 warning in 5.69s (external README audit validator full validation)
8 passed in 0.22s (S10C API smoke ledger presentation target tests)
574 passed, 4 skipped, 1 warning in 7.10s (S10C API smoke ledger presentation full validation)
78 passed in 0.42s (S5A Test-Level Router closeout audit target tests)
576 passed, 4 skipped, 1 warning in 5.57s (S5A Test-Level Router closeout audit full validation)
29 passed in 0.15s (S5B Golden Set manifest governance target tests)
605 passed, 4 skipped, 1 warning in 6.50s (S5B Golden Set manifest governance full validation)
4 passed in 0.12s (S5B2 Golden Set manifest governance presentation target tests)
33 passed in 0.10s (S5B + S5B2 Golden Set governance target tests)
75 passed in 0.18s (S5B/S5B2 plus external asset governance adjacent tests)
609 passed, 4 skipped, 1 warning in 6.64s (S5B2 Golden Set manifest governance presentation full validation)
609 passed, 4 skipped, 1 warning in 5.36s (legacy-change audit cleanup full validation)
53 passed in 0.13s (S5D2 change handoff + governance-adjacent target tests)
620 passed, 4 skipped, 1 warning in 5.48s (S5D2 change handoff full validation)
54 passed in 0.13s (S5D3 suggested commit-batch handoff target tests)
621 passed, 4 skipped, 1 warning in 6.06s (S5D3 suggested commit-batch handoff full validation)
77 passed in 0.30s (S8B API smoke red-line summary target tests)
625 passed, 4 skipped, 1 warning in 5.45s (S8B API smoke red-line summary full validation)
25 passed, 1 warning in 0.36s (S8C API smoke red-line markdown target tests)
628 passed, 4 skipped, 1 warning in 6.05s (S8C API smoke red-line markdown full validation)
35 passed in 0.35s (S9C API smoke benchmark red-line projection target tests)
630 passed, 4 skipped, 1 warning in 6.56s (S9C API smoke benchmark red-line projection full validation)
12 passed in 0.20s (S5D4 change handoff residual-warning target tests)
79 passed in 0.25s (S5D4 handoff/governance/API-smoke adjacent target tests)
630 passed, 4 skipped, 1 warning in 7.29s (S5D4 change handoff full validation)
13 passed in 0.15s (S5D5 change handoff surface-classification target tests)
51 passed in 0.69s (S5D5 handoff/Asset-Gate/API-smoke adjacent target tests)
631 passed, 4 skipped, 1 warning in 7.38s (S5D5 change handoff surface-classification full validation)
14 passed in 0.12s (S5D6 runtime doc-reference cleanup classification target tests)
52 passed in 0.26s (S5D6 handoff/Asset-Gate/API-smoke adjacent target tests)
632 passed, 4 skipped, 1 warning in 6.78s (S5D6 runtime doc-reference cleanup classification full validation)
15 passed in 0.25s (S5D7 change handoff batch-path appendix target tests)
53 passed in 0.28s (S5D7 handoff/Asset-Gate/API-smoke adjacent target tests)
633 passed, 4 skipped, 1 warning in 8.26s (S5D7 batch-path handoff package full validation)
15 passed in 0.17s (S5D8 change handoff batch-review checklist target tests)
53 passed in 0.25s (S5D8 handoff/Asset-Gate/API-smoke adjacent target tests)
633 passed, 4 skipped, 1 warning in 7.27s (S5D8 batch-review checklist full validation)
15 passed in 0.18s (S5D9 change handoff batch-review gates target tests)
53 passed in 0.31s (S5D9 handoff/Asset-Gate/API-smoke adjacent target tests)
633 passed, 4 skipped, 1 warning in 8.72s (S5D9 batch-review gates full validation)
15 passed in 0.19s (S5D10 change handoff top-level gate summary target tests)
53 passed in 0.28s (S5D10 handoff/Asset-Gate/API-smoke adjacent target tests)
633 passed, 4 skipped, 1 warning in 6.41s (S5D10 top-level gate summary full validation)
15 passed in 0.12s (S5D11 change handoff batch verification-target target tests)
53 passed in 0.39s (S5D11 handoff/Asset-Gate/API-smoke adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.98s (S5D11 batch verification-target full validation)
15 passed in 0.20s (S5D12 change handoff verification-target summary target tests)
53 passed in 0.49s (S5D12 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.26s (S5D12 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.97s (S5D12 verification-target summary full validation)
15 passed in 0.24s (S5D13 change handoff batch status-count target tests)
53 passed in 0.37s (S5D13 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.18s (S5D13 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 6.11s (S5D13 batch status-count full validation)
15 passed in 0.19s (S5D14 change handoff batch surface-count target tests)
53 passed in 0.44s (S5D14 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.31s (S5D14 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 8.25s (S5D14 batch surface-count full validation)
15 passed in 0.18s (S5D15 change handoff batch action-count target tests)
53 passed in 0.44s (S5D15 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.27s (S5D15 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.69s (S5D15 batch action-count full validation)
15 passed in 0.16s (S5D16 change handoff batch warning-flag target tests)
53 passed in 0.37s (S5D16 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.25s (S5D16 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.94s (S5D16 batch warning-flag full validation)
15 passed in 0.23s (S5D17 change handoff paths-by-status target tests)
53 passed in 0.38s (S5D17 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.25s (S5D17 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.62s (S5D17 paths-by-status full validation)
15 passed in 0.17s (S5D18 change handoff commit-message hint target tests)
53 passed in 0.28s (S5D18 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.16s (S5D18 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 5.36s (S5D18 commit-message hint full validation)
15 passed in 0.23s (S5D19 change handoff human-next-actions target tests)
53 passed in 0.43s (S5D19 handoff/Asset-Gate/API-smoke adjacent target tests)
75 passed in 0.29s (S5D19 governance adjacent target tests)
633 passed, 4 skipped, 1 warning in 6.10s (S5D19 human-next-actions full validation)
1 passed in 0.15s (S10D cross-layer API smoke projection boundary target test)
52 passed in 0.40s (S10D API smoke benchmark/ledger projection adjacent tests)
634 passed, 4 skipped, 1 warning in 6.84s (S10D cross-layer API smoke projection boundary full validation)
16 passed in 0.11s (S10D handoff snapshot + API smoke projection boundary target tests)
634 passed, 4 skipped, 1 warning in 9.22s (handoff snapshot full validation)
16 passed in 0.34s (S5D20 handoff verification target includes S10D boundary test)
634 passed, 4 skipped, 1 warning in 8.11s (S5D20 handoff verification target full validation)
40 passed in 0.18s (S5D21 mandatory design reuse-check target tests)
96 passed in 0.25s (S5D21 governance-adjacent target tests)
644 passed, 4 skipped, 1 warning in 7.68s (S5D21 mandatory design reuse-check full validation)
42 passed in 0.19s (S5D22 design reuse-check plan target tests)
98 passed in 0.21s (S5D22 governance-adjacent target tests)
646 passed, 4 skipped, 1 warning in 9.24s (S5D22 design reuse-check plan full validation)
43 passed in 0.25s (S5D23 API/interface reuse-plan sample target tests)
99 passed in 0.17s (S5D23 governance-adjacent target tests)
647 passed, 4 skipped, 1 warning in 7.10s (S5D23 API/interface reuse-plan sample full validation)
12 passed in 0.11s (S5D24 Schemathesis README audit target tests)
99 passed in 0.18s (S5D24 external asset governance adjacent tests)
647 passed, 4 skipped, 1 warning in 6.67s (S5D24 Schemathesis README audit full validation)
13 passed in 0.11s (S5D25 Newman README audit target tests)
100 passed in 0.20s (S5D25 external asset governance adjacent tests)
648 passed, 4 skipped, 1 warning in 5.86s (S5D25 Newman README audit full validation)
14 passed in 0.11s (S5D26 WireMock README audit target tests)
101 passed in 0.18s (S5D26 external asset governance adjacent tests)
649 passed, 4 skipped, 1 warning in 5.65s (S5D26 WireMock README audit full validation)
48 passed in 0.20s (S5D27 knowledge embedding destination target tests)
77 passed in 0.22s (S5D27 governance-adjacent target tests)
654 passed, 4 skipped, 1 warning in 7.13s (S5D27 knowledge embedding destination full validation)
42 passed in 0.16s (S5D28 Skill/SOP readiness target tests)
104 passed in 0.25s (S5D28 governance-adjacent target tests)
681 passed, 4 skipped, 1 warning in 5.92s (S5D28 Skill/SOP readiness full validation)
51 passed in 0.18s (S6D Java framework neutrality target tests)
688 passed, 4 skipped, 1 warning in 7.17s (S6D Java framework neutrality full validation)
78 passed, 1 warning in 1.35s (S6D2 submit java_test_framework target tests)
95 passed, 1 warning in 1.25s (S6D2 submit java_test_framework + handoff target tests)
690 passed, 4 skipped, 1 warning in 7.97s (S6D2 submit java_test_framework full validation)
82 passed in 0.27s (S6E project progress snapshot target tests)
99 passed in 0.96s (S6E project progress snapshot + governance target tests)
698 passed, 4 skipped, 1 warning in 7.73s (S6E project progress snapshot full validation)
26 passed in 0.16s (S6F human/golden label readiness target tests)
701 passed, 4 skipped, 1 warning in 6.33s (S6F human/golden label readiness full validation)
51 passed in 0.26s (S6G Golden Set defect-denominator readiness target tests)
704 passed, 4 skipped, 1 warning in 6.53s (S6G Golden Set defect-denominator readiness full validation)
18 passed in 0.19s (S6H landing readiness handoff classification target tests)
76 passed in 0.36s (S6H landing readiness + validation target tests)
705 passed, 4 skipped, 1 warning in 7.09s (S6H landing readiness handoff classification full validation)
68 passed in 0.21s (S6I landing readiness rollup target tests)
708 passed, 4 skipped, 1 warning in 6.60s (S6I landing readiness rollup full validation)
24 passed in 0.27s (S6J landing readiness Markdown presentation target tests)
32 passed in 0.28s (S6J landing readiness presentation + progress/handoff target tests)
711 passed, 4 skipped, 1 warning in 8.24s (S6J landing readiness Markdown presentation full validation)
24 passed in 0.25s (S6K landing readiness review checklist target tests)
32 passed in 0.21s (S6K landing readiness review checklist + progress/handoff target tests)
711 passed, 4 skipped, 1 warning in 8.12s (S6K landing readiness review checklist full validation)
10 passed in 0.20s (S6L landing readiness snapshot validator target tests)
36 passed in 0.16s (S6L landing readiness validator + progress/handoff target tests)
715 passed, 4 skipped, 1 warning in 6.36s (S6L landing readiness snapshot validator full validation)
17 passed in 0.24s (S6M landing readiness typed validator target tests)
43 passed in 0.28s (S6M landing readiness typed validator + progress/handoff target tests)
722 passed, 4 skipped, 1 warning in 6.28s (S6M landing readiness typed validator full validation)
55 passed in 0.31s (S6N landing readiness derived-consistency target tests)
734 passed, 4 skipped, 1 warning in 9.73s (S6N landing readiness derived-consistency full validation)
57 passed in 0.29s (S6O landing readiness blocker-family summary target tests)
736 passed, 4 skipped, 1 warning in 6.61s (S6O landing readiness blocker-family summary full validation)
65 passed in 0.29s (S6P landing readiness blocker-summary validator target tests)
744 passed, 4 skipped, 1 warning in 6.12s (S6P landing readiness blocker-summary validator full validation)
68 passed in 0.21s (S6Q landing readiness blocker-summary Markdown target tests)
747 passed, 4 skipped, 1 warning in 5.65s (S6Q landing readiness blocker-summary Markdown full validation)
68 passed in 0.25s (S6 governance freeze target tests)
747 passed, 4 skipped, 1 warning in 9.12s (S6 governance freeze full validation)
68 passed in 0.19s (joint human-label + Golden Set route target tests)
747 passed, 4 skipped, 1 warning in 6.92s (joint human-label + Golden Set route full validation)
```

## 5. Next Design Queue

Next work should keep the product mainline open beyond Java/Maven unit tests: toward
producer-agnostic API/interface candidate evaluation and automated-test-generation outputs as
candidate inputs. Do a bounded S4A audit, then prefer S6 boundary design over more prompt,
generator, or pass-rate tuning unless that work fixes a concrete evidence/red-line issue.
Governance and external-asset work are support tracks, not blockers for the mainline.

```text
S5A   Live V1: closeout audit proves S4A report-only Test-Level Router stays advisory,
      pure, non-executing, and absent from benchmark/ledger carry, markdown, digest flags,
      signatures, aggregate headlines, and verdicts
      (`docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md`,
      `tests/test_test_level_router.py`)
S6A   Drafted: API/interface Candidate boundary from Minimal Judge Contract
S6A1  Live: pure JudgeEvidence projection for current Java/Maven report facts
      (`app/report/judge_evidence.py`, `tests/test_judge_evidence.py`)
S6B   Drafted: compact API report contract from JudgeEvidence fields
      (`docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md`)
S6C   Live V1: selected `junit_api_candidate` as the minimal S7 smoke path
      and added pure API evidence block validation; still no executor
      (`docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`,
      `app/report/api_evidence.py`, `tests/test_api_evidence.py`)
S6D/S6D2 Live V1: Java test framework neutrality facts. JUnit4/JUnit5/TestNG/mixed/unknown
      framework facts are detected or accepted from a declaration and surfaced under
      `review_summary["java_test_framework"]`. S6D2 lets `submit_candidate` carry an optional
      normalized `java_test_framework` declaration into the same report-only path. JUnit remains a
      thin compatibility path; TestNG is now visible for enterprise Java review. The built-in JUnit
      generator is legacy failed exploration retained only as a removable producer. No
      candidate-kind migration, dependency install, POM mutation, runner change, digest signal,
      benchmark/ledger carry, recommendation, conclusion, or trusted-status change.
      (`docs/60_api_candidate/10_JAVA_TEST_FRAMEWORK_NEUTRALITY.md`,
      `app/report/java_test_framework.py`, `app/report/generation_report.py`,
      `app/api/submit_candidate.py`, `app/pipeline/submit_pipeline.py`,
      `tests/test_java_test_framework.py`, `tests/test_generation_report.py`,
      `tests/test_submit_candidate.py`)
S6E   Live V1: pure project progress snapshot for the recurring "what percent is complete"
      question. Current weighted estimate is about 71%, with the stage
      `late_core_harness_hardening_pre_80`. It explains why the project is not yet 80%:
      API/interface evaluation is report/submit/projection only, real-world validation and Golden
      Set labels are still thin, and the large working tree still needs human review/staging. No
      runtime, git, executor, dependency, digest, verdict, or trust authority.
      (`docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md`,
      `app/governance/project_progress.py`, `tests/test_project_progress.py`)
S6F   Live V1: pure human/golden label metric readiness summary for real-world validation. It
      consumes supplied `HumanReviewLabel` rows or compact projections and reports whether
      usable-test rate, average edit count, handling time, diagnosis-time readiness, misjudgment
      rate, and defect-discovery label presence are computable. It creates no persistence,
      headline metric, aggregate key, digest signal, recommendation, conclusion, or trust change.
      (`docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`,
      `docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`,
      `app/benchmark/validation_line.py`, `tests/test_validation_line.py`)
S6G   Live V1: pure Golden Set defect-denominator readiness summary. It consumes metadata-only
      `manifest_seed` rows and identifies future defect-discovery denominator candidates from
      bug/defect/verifier evidence hints, requested task counts, and pinned task ids. It always
      keeps `defect_denominator_ready_now=False` until owner-gated dataset slices and verifier
      evidence exist. No download, dataset materialization, external execution, benchmark
      headline, aggregate key, recommendation, conclusion, or trust change.
      (`docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md`,
      `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`,
      `app/benchmark/manifest_governance.py`, `tests/test_golden_manifest_governance.py`)
S6H   Live V1: change-set handoff now has a dedicated `landing_readiness_snapshots` keep batch
      for project progress and human/golden landing-metric readiness paths. This reduces residual
      runtime/test/doc review noise while preserving human-only review/staging. It reads only
      supplied status/evidence rows and grants no git, executor, persistence, headline metric,
      recommendation, verdict, or trust authority.
      (`app/governance/change_handoff.py`, `tests/test_change_handoff.py`)
S6I   Live V1: pure landing-readiness rollup for the recurring "why not 80 / what blocks landing"
      question. It combines `project_progress_snapshot(...)`, supplied human/golden label metric
      readiness, and supplied Golden Set defect-denominator readiness into one planning view. It
      creates no new metric, persistence, dataset slice, verifier execution, release gate,
      headline claim, recommendation, conclusion, or trust change.
      (`docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md`,
      `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`,
      `app/governance/landing_readiness.py`, `tests/test_landing_readiness.py`)
S6J   Live V1: optional Markdown presentation for an existing landing-readiness snapshot. It is a
      human handoff view only: absent/wrong-version snapshots render empty, blockers and next
      steps are escaped for tables, and authority fields stay explicitly false. No readiness
      recompute, default report wiring, persistence, release gate, headline claim, recommendation,
      conclusion, or trust change.
      (`app/governance/landing_readiness_report.py`,
      `tests/test_landing_readiness_report.py`)
S6K   Live V1: landing-readiness snapshot now includes `review_questions` and
      `evidence_checklist` fields, and the optional Markdown renderer presents both for human
      audit. These are blocker-derived review aids only: they do not collect evidence, execute
      verifiers, approve dataset slices, create release/headline claims, alter recommendations,
      or change conclusion/trust.
      (`app/governance/landing_readiness.py`,
      `app/governance/landing_readiness_report.py`,
      `tests/test_landing_readiness.py`, `tests/test_landing_readiness_report.py`)
S6L   Live V1: pure landing-readiness snapshot boundary validator. It validates v1 schema,
      required planning fields, review-aid structure, and top-level/nested no-authority flags.
      The Markdown renderer now reuses it for v1 snapshots, rejecting forged headline, dataset,
      verifier, verdict, or trust authority instead of rendering them as normal handoff material.
      It does not recompute readiness, collect evidence, persist labels, wire default reports, or
      change recommendation/conclusion/trust.
      (`app/governance/landing_readiness.py`,
      `app/governance/landing_readiness_report.py`,
      `tests/test_landing_readiness.py`, `tests/test_landing_readiness_report.py`)
S6M   Live V1: landing-readiness validator now also checks typed planning fields and consistency:
      percent values stay in 0..100, stage/band fields are known planning enums, source versions
      match nested schema versions, inputs are non-negative integers, human-ready metric counts
      match their name list, and nested progress fields match the top-level snapshot. This rejects
      malformed handoff material without recomputing readiness or granting release/headline,
      dataset, verifier, recommendation, conclusion, or trust authority.
      (`app/governance/landing_readiness.py`, `tests/test_landing_readiness.py`)
S6N   Live V1: landing-readiness validator now checks derived-field consistency across
      `landing_blockers`, `next_best_steps`, `landing_stage`, `ready_for_80_stage`, inputs,
      human-ready metric names/counts, defect-denominator flags, review questions, and
      evidence-checklist statuses. This keeps hand-crafted snapshots from claiming readiness not
      supported by nested progress, human-label readiness, Golden Set denominator readiness, or
      blocker families, while still granting no recompute, evidence collection, dataset/verifier,
      release/headline, recommendation, conclusion, or trust authority.
      (`app/governance/landing_readiness.py`,
      `tests/test_landing_readiness.py`, `tests/test_landing_readiness_report.py`)
S6O   Live V1: landing-readiness blocker-family projection over a validated snapshot. It groups
      current blockers, review questions, and unresolved evidence by project-progress,
      human-label, Golden Set denominator, and change-batch review families, and the optional
      Markdown handoff now renders this table. It is review navigation only and grants no
      workspace scan, evidence collection, persistence, dataset/verifier, release/headline,
      recommendation, conclusion, or trust authority.
      (`app/governance/landing_readiness.py`,
      `app/governance/landing_readiness_report.py`,
      `tests/test_landing_readiness.py`, `tests/test_landing_readiness_report.py`)
S6P   Live V1: pure validator for standalone landing-readiness blocker-family summaries. It checks
      schema, no-authority flags, canonical family order, per-family blocker counts,
      `total_blockers`, evidence-status counts, `next_clearance_family`, and
      `clearance_status` consistency. It does not recompute the source snapshot, collect
      evidence, persist labels, materialize datasets, execute verifiers, create release/headline
      claims, or change recommendation/conclusion/trust.
      (`app/governance/landing_readiness.py`, `app/governance/__init__.py`,
      `tests/test_landing_readiness.py`)
S6Q   Live V1: optional Markdown presentation for standalone landing-readiness blocker-family
      summaries. It validates `landing_readiness_blocker_summary.v1` before rendering and returns
      empty output for absent or wrong-version inputs. It does not recompute the source snapshot,
      wire default reports, collect evidence, persist labels, materialize datasets, execute
      verifiers, create release/headline claims, or change recommendation/conclusion/trust.
      (`app/governance/landing_readiness_report.py`, `app/governance/__init__.py`,
      `tests/test_landing_readiness_report.py`)
S7A   Live V1: report-only `api_evidence` wiring for `junit_api_candidate`
      (`docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`,
      `app/report/generation_report.py`, `tests/test_generation_report_api_evidence.py`)
S7B   Live V1: `submit_candidate` report-only carry for `candidate_kind` and
      compact `api_evidence`; still no executor
      (`docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`,
      `app/api/submit_candidate.py`, `app/pipeline/submit_pipeline.py`,
      `tests/test_submit_candidate.py`)
S7C   Live V1: pure `junit_api_candidate` smoke manifest / exam-bag validator
      (`docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md`,
      `app/report/api_smoke_manifest.py`, `tests/test_api_smoke_manifest.py`)
S7D1/S7D2 Live V1: report-only API smoke manifest carry-through from submit bundle to
      `review_summary["api_smoke_manifest"]` and alignment facts; still no executor,
      benchmark/ledger carry, digest signal, or verdict change
      (`docs/60_api_candidate/08_S7D_API_SMOKE_MANIFEST_CARRY_THROUGH_DESIGN.md`,
      `app/report/generation_report.py`, `app/api/submit_candidate.py`,
      `app/pipeline/submit_pipeline.py`, `tests/test_generation_report_api_smoke_manifest.py`,
      `tests/test_submit_candidate.py`)
S8/S8B/S8C Live V1: report-only API smoke denominator eligibility facts, reviewer-facing
      red-line summary over evidence/manifest/denominator authority boundaries, and optional
      Markdown rendering for that summary; still no benchmark/ledger carry, endpoint, digest
      signal, executor, or verdict change
      (`docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md`,
      `app/report/api_smoke_denominator.py`, `app/report/api_smoke_redlines.py`,
      `app/report/api_smoke_redlines_report.py`, `app/report/generation_report.py`,
      `tests/test_api_smoke_denominator.py`, `tests/test_api_smoke_redlines.py`,
      `tests/test_api_smoke_redlines_report.py`)
S9A   Live V1: pure API smoke benchmark projection helper; defines separate RAW and API-smoke
      HEADLINE views without changing current unit-test aggregate headlines, ledger, digest,
      executor, or verdict
      (`docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md`,
      `app/benchmark/api_smoke_projection.py`,
      `tests/test_api_smoke_benchmark_projection.py`)
S9B   Live V1 + render-order audit: conditional benchmark markdown rendering of the S9A
      projection. It renders no sections when there are no API smoke source rows, appears after
      validation-line sections and before survived-mutant/per-case rows, and still does not change
      aggregate, ledger, digest, executor, or verdict
      (`app/benchmark/report_md.py`, `tests/test_benchmark.py`)
S9C   Live V1: descriptive benchmark projection/markdown counts for existing
      `review_summary["api_smoke_redlines"]` flags and red-line satisfied buckets inside the
      named API smoke projection only. Still no aggregate key, ledger change, digest signal,
      executor, recommendation, conclusion, or trust authority change.
      (`app/benchmark/api_smoke_projection.py`, `app/benchmark/report_md.py`,
      `tests/test_api_smoke_benchmark_projection.py`, `tests/test_benchmark.py`)
S10A  Live V1: compact API smoke `JudgedRecord` JSON carry from valid
      `review_summary["api_smoke_denominator"]` blocks only. No SQLite columns/indexes,
      badcase signature change, retrieval change, existing analytics change, digest signal,
      executor, or verdict change.
      (`docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md`,
      `app/ledger/models.py`, `app/ledger/ingest.py`, `tests/test_ledger.py`)
S10B  Live V1: pure API-smoke ledger projection helper, separate from existing
      `ledger_summary(...)`, `aggregate_badcases(...)`, badcase signatures, retrieval,
      digest, executor, and verdict.
      (`app/ledger/api_smoke_projection.py`, `tests/test_api_smoke_ledger_projection.py`)
S10C  Live V1: conditional Markdown presentation for the named API-smoke ledger projection.
      It renders RAW plus separate API-smoke HEADLINE sections only when S10A source records
      exist and still does not change existing ledger analytics, retrieval, signatures, digest,
      executor, or verdict.
      (`app/ledger/api_smoke_report.py`, `tests/test_api_smoke_ledger_projection.py`)
S10D  Live V1: cross-layer API smoke projection boundary regression. It feeds matching API smoke
      source facts into the named benchmark and ledger projections, then proves those projection
      views stay separately named and do not mutate existing aggregate views, ledger summaries,
      badcase aggregation, badcase signatures, executor state, verdicts, or trust.
      (`tests/test_api_smoke_projection_boundary.py`)
S5B   Live V1: Golden Set / benchmark-manifest governance metadata gate. Validates only
      `manifest_seed` records for future benchmark drafts or the external registry, rejects
      dataset content, authority, secret/raw payload fields, artifact drift, duplicate seed IDs,
      and headline-metric claims, and summarizes future owner gates. No manifest edit, dataset
      import, executor, aggregate, ledger, digest, recommendation, conclusion, or trusted-status
      change.
      (`docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md`,
      `app/benchmark/manifest_governance.py`, `tests/test_golden_manifest_governance.py`)
S5B2  Live V1: conditional Markdown presentation for Golden Set manifest-seed governance plans.
      Renders a metadata-only audit section when seed rows are supplied, omits empty plans, reuses
      seed validation, and remains opt-in rather than default benchmark report wiring. No manifest
      edit, dataset import, executor, aggregate, ledger, digest, recommendation, conclusion, or
      trusted-status change.
      (`app/benchmark/manifest_governance_report.py`,
      `tests/test_golden_manifest_governance_report.py`)
S5D1/S5D21-S5D28 Live V1: external asset phase policy helper, asset-record validator,
      mandatory design reuse-check validator and plan summary, API/interface reuse-plan sample,
      batch intake-plan summary, README audit record validator/template, first
      Schemathesis/Newman/WireMock P0 README audit records, and the knowledge embedding
      destination router/table for choosing which docs receive new summaries, plus the
      metadata-only Skill/SOP blueprint readiness gate for future evaluation Skills. External
      knowledge/README audit can happen now; manifest seeds are metadata-only; design reuse
      checks, README audit records, embedding destinations, and Skill blueprints are metadata-only;
      installed Skills, dataset slices, producer adapters, executor adapters, isolation support,
      external DB connections, and vendored code are future owner-gated.
      (`docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md`,
      `docs/knowledge/README.md`,
      `docs/knowledge/EXTERNAL_REPO_README_AUDIT.md`,
      `docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md`,
      `app/governance/external_assets.py`, `app/governance/external_readme_audit.py`,
      `app/governance/skill_sop.py`, `tests/test_external_asset_phase_policy.py`,
      `tests/test_external_repo_readme_audit.py`, `tests/test_judge_skill_sop.py`)
S5D2-S5D20/S6H Live V1: CI/PR change-set handoff helper for final human review. It parses supplied
      `git status --short` rows, groups changed surfaces, records command evidence, suggests
      review/commit batches, renders an optional Markdown handoff, highlights residual
      runtime/tests/other changes, keeps API smoke batch notes aligned with S9C/S10C
      report/projection/ledger-presentation scope, and reclassifies known completed-track
      leftovers such as folded `app/governance/`, API smoke report exports, handoff self-tests,
      S5A Test-Level Router audit tests, and runtime/test doc-reference cleanups that only move
      pruned-doc links to active docs. S6H adds a `landing_readiness_snapshots` batch for project
      progress and human/golden landing-metric readiness paths, while the Golden Set batch notes
      explicitly keep defect-denominator readiness metadata-only and future-gated. The Markdown
      renderer includes a batch-path appendix for human review/staging reference plus
      per-surface/per-batch status counts, per-batch surface counts, per-batch paths grouped by
      observed git status, per-batch review checklists, review gates, suggested verification
      targets, suggested commit-message hints, a per-batch warning flag section, a top-level
      human-next-actions checklist, a top-level `batch_action_counts` summary, a top-level
      `batch_warning_counts` summary, a top-level `review_gate_counts` summary, and a top-level
      `verification_target_counts` summary. S5D20 updates the API-smoke batch verification target
      so it explicitly includes the S10D cross-layer projection boundary test. It never reads git
      by itself, stages, commits, pushes, merges, runs tests, changes
      verdicts, or grants trust.
      (`app/governance/change_handoff.py`, `tests/test_change_handoff.py`)

Support tracks, only when needed:
S5B0  Run P0 external asset README audit from docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
      and docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
S5B1  Live V1: real-world validation automated evidence line
      (`docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`,
      `app/benchmark/validation_line.py`, `tests/test_validation_line.py`)
S5C   Live V1: human review and RCA label pure validator
      (`docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`,
      `app/review/human_labels.py`, `tests/test_human_labels.py`)
S5D   Drafted: governance/context recovery and Skill/SOP templates for using the judge safely
      (`docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md`,
      `docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md`,
      `docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md`,
      `docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md`)
S5E   Design optional LLM Judge calibration only if explicitly approved
```

S4A is live only as a report field: one pure helper plus
`review_summary["test_level_router"]` wiring. "Continue" alone is not approval to add execution,
benchmark carry, ledger carry, markdown sections, digest flags, or candidate kinds.

The next design should strengthen the same judge kernel across candidate levels, not generation
pass rate:

- API/interface work starts as a candidate/evidence/report contract, not an API automation
  framework.
- API/interface candidate evaluation should not be treated as a distant optional topic. It is the
  preferred next design direction once S4A report-only invariants are checked.
- S5A closes the S4A Test-Level Router audit. Future router expansion still requires a separate
  owner-approved design and no-drift tests.
- API smoke benchmark projection and display are live: S9A counts only
  `review_summary["api_smoke_denominator"]` rows in a named projection, S9B renders conditional
  RAW/HEADLINE markdown sections only when source rows exist, and S9C adds descriptive counts for
  existing `review_summary["api_smoke_redlines"]` flags inside that same named projection. There is
  still no executor, dependency, external SUT import, ledger carry, generic aggregate key, digest
  signal, or verdict change.
- API smoke ledger compact carry is live as S10A, the named pure ledger projection helper is live
  as S10B, conditional projection Markdown is live as S10C, and S10D now pins the cross-layer
  benchmark/ledger projection boundary with a regression test. Do not add signatures, indexes,
  retrieval scoring, existing ledger analytics changes, digest signals, or executor work. Keep the
  current unit-test
  `Aggregate - HEADLINE` unchanged.
- Real-world validation metrics must separate automated evidence from human/golden labels; do not
  headline usable-test rate, defect discovery, diagnosis time, or misjudgment rate before their
  required labels exist.
- Golden Set work belongs to benchmark manifest governance, not new model runs. S5B is live as
  metadata-only `manifest_seed` validation; actual dataset slices remain future owner-gated.
- External asset work starts with phase mapping plus README/design audit, not downloads,
  vendoring, external DB connections, or installing/running tools.
- RCA work guides human-declared root causes; it must not fabricate root cause.
- Skill/SOP work describes safe workflows; it must not create a new platform surface.
- LLM Judge remains future gated and advisory only.
- External reuse work starts with asset records and focused audits; external P0/P1 labels do not
  become project implementation priority by themselves.
- Current docs cleanup state: raw knowledge packs and old context/preflight evolution digests are
  deleted from the active tree; use `docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md`
  for current architecture audit.

Do not change:

- aggregate headline metrics
- SQLite indexes
- badcase signatures
- verdict, recommendation, conclusion, or trusted status
- candidate kinds or API/integration executors
- digest severity/flags

Recently pruned as redundant:

- S7C/S7D/S8 tests no longer each re-check generic benchmark aggregate shape; S9A owns that
  projection boundary in `tests/test_api_smoke_benchmark_projection.py`.
- Matching S7D/S8 doc checklist entries were removed so old stage docs do not duplicate S9A.
- S9B design and implementation remain folded into
  `docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md` instead of creating a new
  numbered doc.

## 6. Three-Layer Read Rules

Follow the canonical mechanism in `docs/README.md`. For quick handoff, the Layer 1 thin set is:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
```

This is the required read set for every design. It is intentionally small: do not read all
numbered docs or all knowledge packs unless the task routes to them.

Layer 2 routes by need:

```text
API/interface -> docs/40 §10 + docs/60_api_candidate/00 + docs/60_api_candidate/01 + docs/60_api_candidate/02
API smoke     -> docs/60_api_candidate/03 + docs/60_api_candidate/04 + docs/60_api_candidate/05 + docs/60_api_candidate/06 + docs/60_api_candidate/07 + docs/60_api_candidate/08 + docs/60_api_candidate/09 + docs/50_benchmark/59 + docs/50_benchmark/60
Asset Gate    -> docs/50_benchmark/55
Metrics       -> docs/42 + docs/50_benchmark/43 + docs/50_benchmark/56
Golden Set    -> docs/50_benchmark/23 + docs/50_benchmark/62 + docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN + docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY
Human labels  -> docs/50_benchmark/56 + docs/50_benchmark/57
External asset-> docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md + docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md + docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md + docs/knowledge/EXTERNAL_REPO_README_AUDIT.md, then README audit if needed
Knowledge     -> docs/knowledge/README.md, then only the named knowledge file
Governance    -> docs/00_foundation/58 + docs/00_foundation/61 + docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07 + docs/80_sop/00
```

Mandatory reuse check for every design input:

```text
Before inventing a new mechanism, check the curated knowledge base, registry, articles/papers,
tools, evaluation sets, and existing code patterns. Prefer borrow/adapt over rebuilding wheels.
State source/source family, intake shape, project artifact, evidence, and red lines.
```

The pure helpers `app.governance.validate_design_reuse_check(...)` and
`app.governance.design_reuse_check_plan(...)` validate/summarize this metadata and never grant
clone, install, vendor, execute, verdict, or trust authority.
For API/interface design, start with
`app.governance.api_interface_candidate_reuse_check_plan(...)` and adapt it to the concrete design
topic before proposing new mechanisms.
After choosing the intake shape, use
`app.governance.knowledge_embedding_destination(...)` or `docs/knowledge/README.md` to decide which
docs should receive the summary.

Layer 3 is only for proof, implementation detail, or archaeology: code/tests for touched modules,
large knowledge packs, git history for pruned historical docs, external repo audits, benchmark
reports, or ledger records. Read them only when Layer 2 proves they are needed.

External asset rule:

```text
asset -> intake shape -> project artifact -> evidence -> red lines
```

Never stop at "useful". Use `EXTERNAL_ASSET_MAPPING_MATRIX.md` to choose one of:
`knowledge_note`, `readme_audit`, `manifest_seed`, `dataset_slice`, `producer_adapter`,
`executor_adapter`, `sut_target`, `isolation_support`, `provenance_support`, `discovery_index`,
`support_only`, or `reject_mainline`.

Then use `EXTERNAL_ASSET_PHASE_PLAN.md` or `app/governance/external_assets.py` to decide the
earliest stage. Current default: knowledge notes and README audits are allowed; manifest seeds are
metadata-only; dataset slices, executor adapters, producer adapters, external DB connections, and
vendored code require future owner-gated designs.

## 7. Machine Rules

- Use venv Python: `E:\AI-Test-Platform\.venv\Scripts\python.exe`
- Do not read `.env`.
- Do not make real model/API calls without explicit approval.
- Push is human-only.
- Historical benchmark DBs are read-only; never backfill.
- Tests must not contact real LLM providers.
