# Agent Harness Evaluation Knowledge Pack

> Ingested: 2026-07-04  
> Sources: local PDFs `ai评测阿里.pdf` and
> `基于顶级 Agent（Claude Code）的 Harness 工程搭建式业务 Agent 评测方案.pdf`.
> This file is external knowledge distilled for TestAgent Lab. It is not proof that a feature
> exists and not an implementation backlog by itself.

## 0. Fit With This Project

The two PDFs converge on a useful idea: mature Agent evaluation is not a one-off score. It is an
engineering loop:

```text
case set -> execution trace -> scorers -> report -> root cause -> action item -> regression asset
```

For TestAgent Lab, translate that as:

```text
test candidate -> Maven/Surefire/JaCoCo evidence -> advisory scorers/signals
  -> review digest -> badcase ledger -> reproducible report -> human decision
```

The useful part is the harness discipline: stable cases, deterministic evidence, layered scoring,
trace-backed RCA, and reusable regression assets.

The risky part is treating prompt-written evaluator logic or LLM-as-Judge as the product. In this
repo, generation and prompt harnesses stay producer-side support. The product remains the judge.

## 1. Adopt / Downgrade / Reject

| External lesson | Project decision |
|---|---|
| Evaluation must be embedded in the development loop, not run as a final manual sample. | Adopt. This supports benchmark manifests, CI-ready verification, and reports with evidence. |
| Reusable harness skeleton: execute cases, collect trace, run scorers, generate report, classify causes. | Adopt as architecture language. Current equivalents are pipeline/report/quality/review/ledger. |
| Golden set should cover high-risk paths and failure modes, not random easy samples. | Adopt for benchmark manifest and badcase regression governance. |
| Rule scorers judge hard constraints; LLM Judge only helps semantic/strategy dimensions. | Adopt. Deterministic judge remains primary. LLM Judge is future gated and advisory only. |
| Skill should be evaluated by trigger correctness, process correctness, tool parameters, artifact quality, and fallback behavior. | Adopt as a future skill-evaluation checklist. |
| Every badcase should become structured evidence, root cause, owner/action, and regression candidate. | Adopt, but only with real judged records and human-declared root cause/fix fields. |
| A strong coding agent can rapidly design a harness from prompts and reports. | Downgrade. Useful for research/design, not as runtime authority or batch judge. |
| Evaluator prompt replaces test/evaluation code. | Reject as core. This repo prefers deterministic code for judge invariants. Prompt logic may produce candidates, never warrants. |
| Multi-agent RCA workflow and large web task platform. | Reject for mainline. Possible future adapter only after bounded design approval. |
| Automatic optimization, auto-fix, auto-ticket, auto-merge. | Reject. Actions are advisory and human-reviewed. |

## 2. Evaluation Structure We Should Keep

A useful candidate-evaluation run should expose four layers:

| Layer | In these PDFs | In TestAgent Lab |
|---|---|---|
| Case | Golden set / business case / prompt sample | benchmark case or submitted candidate |
| Trace | tool calls, intermediate state, logs | target, preflight, execution, coverage, quality gate, asset facts, optional mutation |
| Scorer | rule scorer, LLM judge, human scorer | deterministic judge + advisory signals + human review |
| Feedback | RCA, fix action, regression asset | badcase ledger + review digest + reproducible report |

This maps cleanly onto the current architecture and does not require a new platform layer.

## 3. Scoring Rule

Use a scorer ladder:

1. Deterministic rules first:
   compile result, test execution, assertion presence, production-code edits, preflight blockers,
   coverage deltas, schema/field presence, file safety, run_kind hygiene.
2. Advisory structural signals second:
   oracle strength, mock smell, invariant review, mutation survivor classification, Asset Gate.
3. LLM-assisted semantic scoring only after explicit design approval:
   it must output reason/evidence/confidence, be calibrated against human review, and never change
   `conclusion` or `trusted`.
4. Human review handles high risk, low confidence, rule-vs-judge conflict, and business-standard
   ambiguity.

Never reduce a review to only `pass/fail` or a numeric score. A useful result includes:

```text
phenomenon -> evidence -> confidence -> likely root cause -> suggested next human action
```

## 4. Golden Set And Benchmark Governance

Useful guidance from the PDFs:

- Start small and high quality before expanding. A compact golden set is more useful than a large
  easy set.
- Cover positive, negative, boundary, high-risk, and known-failure cases.
- Version the case set with the target capability. Do not compare incompatible generations of
  prompts, targets, or asset assumptions as if they were the same benchmark.
- Add badcases back only when they are reproducible or have stable trace + human confirmation.
- Avoid unbounded regression-set growth: keep representative samples per cluster, retain P0/P1
  risks, demote low-risk repeatedly passing samples to sampling sets.

Project translation:

```text
Benchmark Manifest = golden/regression case registry
Badcase Ledger = real failure memory
run_kind filter = headline hygiene
Asset Gate = whether the case has enough assets for a meaningful judgment
```

## 5. Badcase RCA Model

The PDFs recommend a chain that fits this project:

```text
collect evidence -> narrow candidate causes -> diagnose module/signal -> classify root cause
  -> store structured record -> propose regression/action
```

For TestAgent Lab, keep RCA fields evidence-bound:

- `failure_type`: observed failure bucket.
- `badcase_signature`: derived structural signature.
- `root_cause`: human-declared or explicitly marked unknown.
- `fix_note`: human-declared or explicitly marked unknown.
- `run_kind`: used for headline filtering.
- `producer_id`: context only, never proof.
- Asset fields: compact projections only, never full source/context dumps.

Good RCA labels should be stable, countable, and action-linked. Avoid free-form labels that cannot
group across runs.

## 6. Skill Knowledge Architecture

In this repo, a Skill is not a new product surface. It is a reusable operating procedure for using
the judge correctly.

A useful future skill should contain:

```text
trigger: when to use it
inputs: required files, reports, candidates, commands
steps: deterministic workflow
evidence: exact command outputs or report fields to collect
red_lines: what the skill must not do
output: report shape / handoff shape
fallback: when to stop for human review
```

Candidate skill map:

| Skill | Purpose | Must not do |
|---|---|---|
| `unit-test-candidate-eval` | Run/interpret the Java/Maven judge path for a candidate. | Generate value claims without command evidence. |
| `asset-gate-review` | Review asset sufficiency and test-level recommendation. | Start API/integration execution. |
| `badcase-rca` | Turn a judged failure into structured RCA and retrieval hints. | Fabricate root cause or backfill historical DBs. |
| `review-digest-report` | Produce a concise human-review report from existing signals. | Add new scoring logic inside the digest. |
| `ci-pr-handoff` | Prepare branch/PR/CI evidence and handoff. | Push, merge, or bypass human approval. |

Skill evaluation checklist:

- Did the skill trigger only when appropriate?
- Did it follow the intended workflow?
- Were tool parameters correct and bounded?
- Was the final artifact usable by a reviewer?
- Did it degrade safely on missing data, low confidence, or command failure?

## 7. CI And Large-Company Workflow Translation

Useful CI discipline from the PDFs and current repo rules:

```text
branch -> local deterministic checks -> commit -> push branch -> PR -> CI -> review -> merge
```

For this project:

- Local required checks: `pytest`, focused tests when relevant, and `git diff --check`.
- PR description should include changed surfaces, verification output, and boundary notes.
- CI red means investigate evidence first, not tune prompts.
- Agents may prepare branch/commit instructions, but push remains human-only.
- Never let CI become an auto-adoption path for candidate tests.

## 8. Knowledge Base Structure Going Forward

Authoritative current state:

```text
AGENTS.md
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
```

External knowledge:

```text
docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md
docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md
docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md
docs/knowledge/BENCHMARK_SOURCES_AND_STRATEGY.md
docs/knowledge/INTERNET_TECH_BUSINESS_KB.md
```

Rule of use:

```text
active docs decide what is true now;
knowledge docs provide patterns and warnings;
code/tests provide evidence.
```

## 9. Post-S4A Design Queue, Not Auto-Tasks

These are useful future design topics, but none should start without explicit approval. The order is
important because each step should strengthen the existing judge before opening new execution
levels.

### S5A - S4A Router Audit

Goal: prove the report-only Test-Level Router has not drifted into an executor or scoring path.

Check:

- exactly one helper owns routing logic: `app/quality/test_level_router.py`;
- exactly one report wiring point attaches `review_summary["test_level_router"]`;
- no benchmark carry, ledger field, markdown section, digest flag, API/integration execution, or
  candidate kind depends on the router;
- provenance evidence remains context only and never changes `recommended_level`;
- focused and full tests still prove verdict, aggregate, digest, and ledger invariants.

### S5B - Golden Set Governance Design

Goal: make benchmark manifests more legible as quality assets without changing the runner first.

Design questions:

- Which manifest cases are frozen baselines, regression sentinels, high-risk edge cases, or
  sampling cases?
- Which cases must remain stable across releases, and which can rotate?
- What makes a new case eligible for the golden set: reproducible build, clear target, declared
  business invariant, stable asset facts, and known risk bucket?
- How do we prevent easy cases from dominating headline confidence?
- How do we keep historical benchmark DB rows read-only while allowing new manifest versions?

First slice should be docs/tests only unless separately approved. It should not add new model calls,
new benchmark execution, or new database schema.

### S5C - Badcase RCA Taxonomy Design

Goal: turn existing `root_cause` / `fix_note` free text into more stable reviewer language while
keeping human declaration and advisory status.

Candidate buckets:

- `oracle_gap`: assertion exists but does not pin the behavior.
- `asset_gap`: missing business oracle, fixture, schema, DB state, mock, or code context.
- `preflight_contract_gap`: candidate calls unavailable target API or violates judge-side contract.
- `compile_or_dependency_gap`: import, dependency, source/target compatibility, or build mismatch.
- `mock_or_isolation_gap`: over-mocking, real dependency leakage, loose matcher, null stub.
- `mutation_survivor_gap`: mutant survives because behavior is not exercised or not asserted.
- `business_invariant_gap`: declared invariant is unaddressed or unpinned.
- `producer_format_gap`: candidate shape, filename, package, or metadata is invalid.
- `environment_or_flake`: unstable external state, timing, order dependence, or infra issue.
- `unknown_needs_human`: evidence insufficient for a confident root cause.

The taxonomy must not auto-fill `root_cause`. It can guide human entry, grouping, and retrieval.

### S5D - Skill/SOP Template Design

Goal: encode safe ways to use the judge, not create a new platform.

First SOP templates to design:

- `unit-test-candidate-eval`: how to judge a candidate and report command evidence.
- `asset-gate-review`: how to inspect asset sufficiency without launching a new executor.
- `badcase-rca`: how to map evidence to a human-declared root cause.
- `ci-pr-handoff`: how to prepare PR evidence without pushing or merging.

Each SOP should have trigger, inputs, deterministic steps, evidence, red lines, output, and fallback.

### S5E - Optional LLM Judge Calibration Design

Goal: decide whether semantic review can be added later without breaking the judge-first thesis.

Do not implement until owner-approved. Any design must require:

- human calibration set;
- explicit confidence/reason/evidence output;
- bias mitigation when scorer and producer share a model family;
- high-risk and low-confidence human routing;
- advisory-only output that never affects `conclusion`, `trusted`, or auto-accept.

All of them must preserve:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
producer provenance is not quality proof
no auto-accept / auto-merge / auto-warehouse entry
```

## 10. Design Selection Rule

Pick the next design by evidence bottleneck:

```text
If router boundary is uncertain -> S5A audit.
If benchmark confidence is uncertain -> S5B Golden Set governance.
If failure memory is noisy -> S5C RCA taxonomy.
If agent usage is inconsistent -> S5D Skill/SOP templates.
If semantic judgment is requested -> S5E LLM Judge calibration, gated.
```

Never choose a design because it improves the built-in generator's pass rate alone.
