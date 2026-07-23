# Open Source Reuse Governance Digest - 2026-07

> Source: `D:\AI_TEST_AGENT_OPEN_SOURCE_KNOWLEDGE_BASE_2026-07.md`
> Ingested: 2026-07-20
> Status: knowledge note and governance digest only. This file is not an implementation roadmap,
> not proof that an external asset is current, and not approval to clone, install, execute, or
> vendor anything.

## 0. How To Use This Digest

The source file gives a broad open-source reuse map for testing agents, repair agents, API testing,
agent orchestration, model gateways, observability, and benchmarks.

For this project, use it through the existing project boundary:

```text
candidate -> deterministic evidence -> advisory signals -> digest -> ledger -> report
```

Do not use the source as:

- a replacement for `docs/WORK_LOG.md`;
- a default read set;
- a direct backlog;
- a current URL/license guarantee;
- a reason to start an executor, repair loop, model gateway, or agent orchestration layer.

## 1. Adopted Lessons

The following lessons fit the current architecture:

- keep Candidate, Evidence, and Report contracts owned by this repo;
- keep declared evidence from producers separate from platform-observed evidence;
- compare producers only after they enter the same judge path;
- record provenance as context, never as proof of quality;
- classify failures into stable families: compile, execution, oracle, mock, asset, environment,
  product, platform, and unknown;
- preserve command evidence, log digests, artifact hashes, and redaction facts where possible;
- use external assets as adapters, manifest seeds, SUT targets, or knowledge notes, not as code
  copied into the main repo;
- treat compact API traffic summaries as evidence, while excluding raw payloads, tokens, cookies,
  `.env`, database dumps, and service snapshots.

## 2. Downgraded Lessons

The source recommends many useful tools, but most are not current mainline:

| External idea | Current project handling |
|---|---|
| Producer adapters such as EvoSuite, Randoop, ChatUniTest, Pynguin, CoverUp | Future `producer_adapter` designs; output must enter `submit_candidate`. |
| API executors such as Schemathesis, Newman, RESTler, EvoMaster, Keploy | Future `executor_adapter` designs only after `junit_api_candidate` report path is proved. |
| Repair agents such as mini-SWE-agent, OpenHands, AutoCodeRover, RepairAgent | Support-only until a repair-candidate contract is owner-approved; never mutate old evidence. |
| LangGraph / PydanticAI orchestration | Optional outer orchestration only; never inside the judge kernel. |
| LiteLLM, vLLM, SGLang, Ollama | Producer-side/model-support references; no provider platform mainline. |
| OpenTelemetry, Langfuse, Phoenix | Future provenance support; never a verdict source. |
| reviewdog / PR-Agent | Possible report sinks later; no auto-adoption or push/merge path. |
| TestExplora, Defects4J, ProjectTest, TestGenEval | Manifest seed or tiny owner-approved slice only; no bulk import. |

## 3. Rejected Mainline Moves

Do not adopt these from the source note as architecture:

- rewrite current pipeline into a generic adapter framework before one small need proves it;
- start a real API executor before manifest/report evidence is carried safely;
- add a repair loop before human-label and oracle-safety contracts are stable;
- add a model gateway or self-hosted model serving as platform center;
- build a dashboard, task platform, PR bot, or auto-warehouse sink;
- use external benchmark scores as product claims without run_kind and evidence hygiene;
- use star count, roadmap claims, or access dates instead of README/license/runtime audit.

## 4. Vocabulary Normalization

The source uses terms that do not exactly match this repo. Normalize them before design:

| Source term | Project term |
|---|---|
| `CandidateEnvelope` | `JudgeCase` / current submit request plus generation bundle facts |
| `ObservedEvidence` | `JudgeEvidence` / current report evidence projection |
| `Verdict` | advisory report outcome; never auto-accept |
| `repair_adapter` | support-only or future producer of a new candidate after owner gate |
| `knowledge_reference` | `knowledge_note` |
| `benchmark_contract_reference` | `knowledge_note` plus possible `manifest_seed` |
| `automation roadmap` | candidate design queue, not implementation approval |

Allowed intake shapes remain the ones in `EXTERNAL_ASSET_MAPPING_MATRIX.md`.

## 5. Supply-Chain And Sandbox Lessons

External assets need an asset record before implementation:

```text
asset_id:
source_url:
intake_shape:
project_artifact:
pinned_version_or_commit:
license_spdx:
runtime_language:
requires_network:
requires_docker:
writes_workspace:
secrets_or_payload_risk:
expected_evidence:
red_lines:
```

Minimum sandbox expectations for future external commands:

```text
temporary workspace
source read-only, candidate output writable
network off unless explicitly approved
timeout, CPU, memory, process, and disk limits
argv-list invocation, not shell-string composition
environment allowlist
stdout/stderr digest and redaction
before/after file diff
artifact hash and tool version
workspace cleanup
```

These are design requirements. They are not implemented by this digest.

## 6. Project-Specific Priority Correction

The source's P0/P1 lists are not this repo's P0/P1 lists.

Current project priority is:

```text
1. keep S7 report-only API evidence and manifest boundaries honest;
2. decide manifest id carry-through before execution;
3. harden SOPs and context recovery;
4. audit external assets with asset records;
5. only then consider one owner-approved executor or producer adapter.
```

This correction prevents external reuse enthusiasm from displacing the judge-first thesis.

## 7. Where This Feeds

Use this digest when working on:

- `docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md`;
- `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`;
- `docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md`;
- future external README audits;
- future manifest/governance design.

Do not add it to the Layer 1 default read set.
