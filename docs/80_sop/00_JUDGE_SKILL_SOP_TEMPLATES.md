# Judge Skill SOP Templates

> Date: 2026-07-20
> Status: S5D template design. Documentation only; no Codex Skill package, plugin, agent
> workflow, model call, executor, endpoint, schema change, benchmark change, ledger change, or
> verdict change is implied.

## 0. Rule

A Skill/SOP in this project is a safe procedure for using the judge. It is not a new product
surface and not a runtime authority.

Every SOP must preserve:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
producer provenance is advisory
command evidence beats generated claims
green execution is not value proof
```

## 1. Common Template

Use this shape for every future Skill:

```text
name:
trigger:
inputs:
steps:
evidence:
red_lines:
output:
fallback:
verification:
```

Skill quality is evaluated by:

- correct trigger;
- bounded inputs;
- correct tool parameters;
- evidence actually collected;
- red lines preserved;
- usable handoff output;
- safe fallback when evidence is missing.

## 2. `unit-test-candidate-eval`

Trigger:

```text
Human, agent, or external producer submits a Java/Maven JUnit or TestNG unit-test candidate for
judgment.
```

Inputs:

```text
target_class
target_method?
test_source
producer_id
producer_meta?
```

Steps:

1. Submit through the existing candidate path.
2. Let the current Java/Maven judge collect compile, Surefire, and coverage evidence.
3. Read report fields, quality gate, Asset Gate, review digest, and conclusion.
4. Summarize only observed evidence and advisory review guidance.

Evidence:

```text
judge command or pipeline result
compile/build status
Surefire outcome and counts
coverage delta if available
quality gate blockers/warnings
review_summary.asset_sufficiency
review_summary.digest
conclusion/trusted fields
```

Red lines:

- do not claim the test has value from green execution or coverage;
- do not weaken assertions or rewrite expected values;
- do not edit production code, `pom.xml`, or existing tests;
- do not read `.env`;
- do not call a real model unless explicitly approved.

Output:

```text
candidate evidence summary
review risks
human-review checklist
commands/results cited
```

Fallback:

```text
If command evidence is missing or contradictory, say the candidate is unverified and stop.
```

## 3. `junit-api-candidate-report-review`

Trigger:

```text
A report or bundle explicitly carries candidate_kind=junit_api_candidate or compact api_evidence.
```

Inputs:

```text
generation report
review_summary.api_evidence?
api_smoke_manifest.v1?
asset_sufficiency?
```

Steps:

1. Verify `api_evidence` is advisory and report-only.
2. Check redaction flags and forbidden payload/secret fields.
3. Confirm the runner remains `maven_surefire_jacoco`.
4. Compare candidate_kind with Asset Gate/Test-Level Router output as review context only.
5. Report missing service, base URL, auth, fixture, mock, or oracle assets as review facts.

Evidence:

```text
review_summary.api_evidence
redaction flags
execution.runner_tool
asset requirement statuses
manifest smoke_id if present in a future design
```

Red lines:

- do not start a service or external API executor;
- do not install Schemathesis, Newman, WireMock, Testcontainers, Docker, or RestAssured;
- do not persist raw request/response bodies, tokens, cookies, `.env`, DB dumps, or service
  snapshots;
- do not treat HTTP 2xx or a green Maven run as API correctness.

Output:

```text
API evidence summary
asset gaps
redaction status
human-review notes
```

Fallback:

```text
If api_evidence is absent, evaluate the candidate as the existing Java/Maven path and say API
evidence was not provided.
```

## 4. `asset-gate-review`

Trigger:

```text
Design or report work needs to decide whether available assets are sufficient for unit/API/
integration/manual-oracle-first review.
```

Inputs:

```text
review_summary.asset_sufficiency
review_summary.test_level_router
asset_facts
candidate target
report evidence
```

Steps:

1. Identify which assets are sufficient, partial, missing, or unknown.
2. Separate source/target hints from real assets.
3. Treat dependency artifacts as corroboration only.
4. Compare router recommendation with candidate_kind as advisory context.
5. Produce human-review risks and missing-asset notes.

Evidence:

```text
asset_sufficiency fields
router recommended_level
missing_assets
risk_notes
candidate_kind if present
```

Red lines:

- do not launch API/integration execution;
- do not infer schemas, services, databases, credentials, or business oracles automatically;
- do not change recommendation, conclusion, digest severity, or trusted status.

Output:

```text
asset sufficiency summary
recommended test level context
missing assets
review action
```

Fallback:

```text
If assets are ambiguous, route to manual_oracle_first or human review instead of guessing.
```

## 5. `badcase-rca`

Trigger:

```text
A judged candidate failure or weak-candidate report needs RCA labeling or ledger handoff.
```

Inputs:

```text
report
quality gate findings
failure_type
badcase_signature
human_review_label?
root_cause/fix_note?
```

Steps:

1. Collect observed failure facts.
2. Map facts to the human-review RCA taxonomy only as suggestions.
3. Require human or verifier confidence for product-bug and usability claims.
4. Keep `root_cause` and `fix_note` human/external-author declared.
5. Prepare compact ledger/retrieval context if persistence is already supported.

Evidence:

```text
failure_type
quality blockers/warnings
human label fields
evidence_refs
misjudgment fields if present
```

Red lines:

- do not fabricate root cause;
- do not backfill historical DB rows;
- do not treat retrieval precedent as current fact;
- do not use an LLM Judge as RCA authority.

Output:

```text
observed failure summary
possible RCA bucket
required human label fields
badcase handoff note
```

Fallback:

```text
Use unknown_insufficient_evidence when facts do not support a stable label.
```

## 6. `external-asset-intake`

Trigger:

```text
A design mentions an external repo, dataset, tool, framework, paper, or service.
```

Inputs:

```text
asset name
URL/source if known
proposed project artifact
expected evidence
```

Steps:

1. Map the asset to an intake shape from `EXTERNAL_ASSET_MAPPING_MATRIX.md`.
2. Add an asset record block.
3. If required, perform a focused README/license/runtime audit in scratch space.
4. Record facts in a knowledge note or README audit.
5. Stop before install, clone into project tree, execution, or vendoring unless owner-approved.

Evidence:

```text
intake_shape
asset_record fields
README/license/runtime facts
red_lines
next_action
```

Red lines:

- do not write only "useful";
- do not use star count as approval;
- do not import datasets in bulk;
- do not execute external code without a runner/isolation design;
- do not turn producer or provenance support into a verdict source.

Output:

```text
external asset mapping block
audit summary if performed
defer/adopt/downgrade/reject decision
```

Fallback:

```text
If the intake shape is unclear, mark support_only and ask for owner scope before proceeding.
```

## 7. `ci-pr-handoff`

Trigger:

```text
Docs or code changes are ready for human handoff.
```

Inputs:

```text
git status
git diff
test command outputs
changed file list
uncommitted/unpushed state
```

Steps:

1. Summarize changed surfaces.
2. List commands run and exact result lines.
3. State unpushed commit count or dirty worktree state.
4. Note boundary constraints preserved.
5. Leave push/merge to the human.

Evidence:

```text
git status --short
git diff --stat
pytest summary line if run
focused command outputs
```

Red lines:

- do not push;
- do not auto-merge;
- do not claim tests pass without command evidence;
- do not hide unrelated user changes.

Output:

```text
handoff summary
verification
remaining gates
unpushed/dirty state
```

Fallback:

```text
If tests were not run, say so and explain why.
```

Live helper:

```text
app/governance/change_handoff.py
tests/test_change_handoff.py
```

The helper accepts supplied `git status --short` rows and command evidence, groups changed
surfaces, suggests review/commit batches, highlights residual runtime/tests/other changes,
reclassifies known completed-track leftovers, separates runtime doc-reference cleanups from
unknown residual code, keeps API-smoke handoff notes aligned with current report/projection/
ledger-presentation scope, and can render a compact Markdown handoff with per-batch review
per-surface/per-batch status counts, per-batch surface counts, checklists, per-batch review gates,
suggested verification targets, per-batch warning flags, per-batch paths grouped by observed git
status, suggested commit-message hints, top-level human-next-actions, top-level batch-action
counts, top-level batch-warning counts, top-level gate counts, top-level verification-target
counts, and a batch-path appendix. It does not read git by itself, run tests, stage, commit, push,
merge, or grant verdict/trust authority.

## 8. From SOP To Evaluation Skill

The open-source Skill direction is a good fit for this project when it is applied to evaluation
workflows instead of generation prompts. The safe interpretation is:

```text
article/knowledge idea -> bounded judge SOP -> Skill blueprint -> owner-gated Skill package
```

Do not jump directly from a generation-oriented article to an installed Skill. A project Skill
should first prove that it reuses the existing judge and keeps evidence, conclusion, and trust
boundaries intact.

The first code gate is:

```text
app/governance/skill_sop.py
tests/test_judge_skill_sop.py
```

Every Skill blueprint must state:

```text
name
skill_form
trigger
inputs
steps
evidence
red_lines
output
fallback
verification
pillars
judge_entrypoint
reuse_refs
```

Required red lines:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
no auto-accept
command evidence beats generated claims
```

Allowed now:

- `sop_template`: documentation-only operating procedure.
- `codex_skill_blueprint`: metadata-only future Skill design that maps to an existing SOP.

Future owner-gated:

- `installed_skill_candidate`: any real Codex Skill package, auto-trigger, bundled script/asset,
  agent workflow, model call, external execution, dependency install, service orchestration, or
  runtime invocation.

Use `app.governance.candidate_eval_skill_readiness_plan(...)` as the first metadata-only plan for
`unit-test-candidate-eval` and `junit-api-candidate-report-review`. Passing this plan means the
Skill idea is ready for design review, not ready for installation.
