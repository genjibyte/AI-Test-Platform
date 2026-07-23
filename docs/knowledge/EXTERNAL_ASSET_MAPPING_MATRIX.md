# External Asset Mapping Matrix

> Date: 2026-07-20
> Source: user-provided external asset lists, including
> `D:\AI_TEST_AGENT_OPEN_SOURCE_KNOWLEDGE_BASE_2026-07.md`.
> Status: design rule. This file maps assets to project intake shapes; it does not mean any asset
> is installed, cloned, copied, executed, or implemented.

## 0. Design Rule

Every future design that mentions an external asset must first map that asset to one intake shape.
Do not write "useful" without an access form.

Allowed intake shapes:

| Intake shape | Meaning | Allowed action |
|---|---|---|
| `knowledge_note` | The asset teaches a design idea, metric, warning, or vocabulary. | Read paper/README/docs and summarize into `docs/knowledge/` or a design doc. |
| `readme_audit` | The asset is a repo/framework worth understanding before decisions. | Shallow-read README/docs in scratch space; record facts in `EXTERNAL_REPO_README_AUDIT.md`. |
| `manifest_seed` | The asset can supply pinned benchmark/task metadata. | Store only URL, commit/tag, task id, risk bucket, expected evidence, and license notes. |
| `dataset_slice` | A tiny reproducible subset may be pulled later. | Owner-approved, pinned, minimal slice only; never bulk import. |
| `producer_adapter` | The asset produces candidate tests. | Treat output as candidate input to `submit_candidate` or future candidate adapter. |
| `executor_adapter` | The asset can execute a candidate kind. | Design runner command, evidence parser, isolation, and no-verdict-drift tests first. |
| `sut_target` | The asset is a system-under-test target. | Pin repo/commit and run requirements in a manifest; do not vendor source. |
| `isolation_support` | The asset supports mocks, containers, contracts, or service isolation. | Use only after Asset Gate/API design says which asset is required. |
| `provenance_support` | The asset records traces, prompt runs, or producer metadata. | Advisory provenance only; never a quality warrant or verdict source. |
| `discovery_index` | The asset is a list, forum, leaderboard, or search surface. | Periodic discovery only; it cannot create work by itself. |
| `support_only` | The asset is adjacent but not mainline now. | Keep as reference; revisit only when a design explicitly needs it. |
| `reject_mainline` | The asset direction would change the product. | Do not adopt as architecture; mention only as a boundary warning. |

Default rule: no vendoring external repos, no direct code copy, no new dependency, no external API
or model call, and no executor until an owner-approved design identifies the exact candidate kind,
evidence contract, isolation boundary, and tests.

External notes may use different labels. Normalize them before design:

| External/source label | Project handling |
|---|---|
| `repair_adapter` | Not an allowed current intake shape. Treat as `support_only` until an owner-approved repair-candidate design treats repair output as a new `producer_adapter` candidate. |
| `knowledge_reference` | Use `knowledge_note`. |
| `benchmark_contract_reference` | Use `knowledge_note` plus possible future `manifest_seed`. |
| `CandidateEnvelope` | Map to current submit request / future `JudgeCase` vocabulary. |
| `ObservedEvidence` | Map to `JudgeEvidence` / report evidence projection. |
| external P0/P1 roadmap | Treat as source priority only, not project implementation priority. |

## 0.1 Intake Workflow

Use this order for external assets:

```text
external asset
  -> intake shape from this matrix
  -> phase gate from EXTERNAL_ASSET_PHASE_PLAN.md
  -> small README/design audit when the shape requires it
  -> one of: knowledge note, manifest seed, dataset slice, adapter design, SUT target, or defer
```

The project remains:

```text
candidate -> deterministic evidence -> advisory signals -> digest -> ledger -> report
```

External assets are useful only when they improve one of:

- Candidate: better input format or producer-agnostic submission.
- Provenance: clearer origin, version, trace, and run_kind hygiene.
- Badcase: real failure memory, RCA, regression seeds.
- Asset Gate: better judgment of whether unit/API/integration/manual-oracle-first is appropriate.

## 0.2 README Audit Protocol

When reading external repositories, do not read everything and do not clone into the project tree.

Recommended workflow:

```text
1. Create a scratch directory outside tracked source, e.g. var/external_read/<asset>.
2. Shallow clone or fetch only README/docs:
   git clone --depth 1 --filter=blob:none <url> var/external_read/<asset>
3. Read README, docs overview, examples, CLI usage, data format, license.
4. Record only project-relevant facts in docs/knowledge/EXTERNAL_REPO_README_AUDIT.md.
5. Delete scratch clone if not needed.
```

Minimum fields to record:

```text
asset:
url:
intake_shape:
license:
language/runtime:
input format:
output/evidence format:
can run offline:
requires docker/network/model/API key:
fit for project:
risks:
next action:
```

## 0.2.1 Asset Record Block

Any external asset that moves beyond a casual knowledge mention must include this block in the
design or README audit:

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

This block is documentation metadata. It is not approval to clone, install, execute, vendor, or
ship the asset.

The pure validator for this block is:

```text
app/governance/external_assets.py::validate_external_asset_record
app/governance/external_assets.py::external_asset_intake_plan
app/governance/external_readme_audit.py::validate_external_repo_readme_audit
app/benchmark/manifest_governance.py::validate_golden_manifest_seed
app/benchmark/manifest_governance.py::golden_manifest_governance_plan
app/benchmark/manifest_governance_report.py::render_golden_manifest_governance_markdown
```

The first validates one metadata record and attaches phase policy. The second validates a batch,
rejects duplicate `asset_id` values, and summarizes current-stage blockers. The third validates a
focused README/license/runtime audit record. The Golden Set helpers validate metadata-only
`manifest_seed` records, summarize future owner gates, and render optional audit Markdown. All
still set runtime/download/install authority to false, and Golden Set helpers also keep benchmark
headline authority false.

## 0.3 First README Audit List

First focused audit should cover only these assets:

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

Stop after these. Do not let indexes recursively expand the scope.

## 1. Software Engineering Agent / Harness Evaluation

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| SWE-bench | `readme_audit` + `knowledge_note` + future `manifest_seed` | Borrow task instance / environment / verifier discipline for `EvalTask` and report evidence. | P0 README audit; no dataset import. |
| SWE-bench 官网/榜单 | `discovery_index` | Borrow lite/verified/full split and leaderboard caution language. | Summarize benchmark governance only. |
| SWE-bench Verified | `knowledge_note` + future `manifest_seed` | Pattern for small trusted calibration slices. | Use as Golden Set design analogy. |
| SWE-bench Lite | `knowledge_note` | Pattern for low-cost smoke subsets. | Use for smoke/full split vocabulary. |
| SWE-bench Verified Dataset | `manifest_seed` | External metadata reference only. | Do not download unless Golden Set design approves. |
| SWE-bench Live | `knowledge_note` | Decontamination / rolling task idea. | Summarize contamination risks. |
| Claw-SWE-Bench | `knowledge_note` | Adapter protocol and workspace contract reference. | Read design; do not implement adapter yet. |
| Claw-SWE-Bench GitHub | `readme_audit` | Concrete adapter repo to inspect. | P0 README audit. |
| Claw-SWE-Bench Dataset | `manifest_seed` | External task format reference. | Metadata only; no bulk import. |
| SWE-Gym | `support_only` | Training/evaluation environment ideas, too broad now. | Defer. |
| SWE-Gym Dataset | `support_only` | Large training-style dataset, not judge core. | Defer. |
| SWE-smith | `support_only` | Long-term task-construction idea. | Defer; no task generator. |
| SWE-smith 项目页 | `knowledge_note` | Read only for task-generation risks. | Optional summary later. |
| SWE-smith Dataset | `support_only` | Generated task data, not current benchmark. | Defer. |
| OpenHands Benchmarks | `readme_audit` + `knowledge_note` | Evaluation pipeline organization reference. | P0 README audit. |
| mini-SWE-agent | `support_only` | Agent producer example only. | Do not build agent platform. |
| Inspect AI | `readme_audit` + `knowledge_note` | Task/solver/scorer vocabulary for judge design. | P0 README/docs audit. |
| Inspect AI GitHub | `readme_audit` | Concrete framework repo to inspect. | README audit only; no runtime adoption. |
| Inspect Evals | `knowledge_note` | Eval packaging examples. | Use vocabulary, not dependency. |
| Harness-Bench | `knowledge_note` | Harness quality benchmark idea. | Summarize if harness design needs it. |
| BenchFlow Awesome Evals | `discovery_index` | Eval ecosystem discovery. | Track only. |

## 2. LLM Test-Generation Benchmarks

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| TestExplora | `readme_audit` + future `manifest_seed` | Repository-level generated-test evaluation closest to project thesis. | P0 README audit; possible tiny manifest seed later. |
| TestExplora arXiv | `knowledge_note` | F2P / hidden defect signal / repo-level task design. | Summarize metrics and risks. |
| TestExplora Microsoft Research | `knowledge_note` | Official positioning and benchmark framing. | Use in knowledge note only. |
| TestGenEval | `knowledge_note` + possible `manifest_seed` | Real-world unit-test generation benchmark. | P1; read after Golden Set design. |
| TestGenEval 项目页 | `discovery_index` | Task split / leaderboard reference. | Track only. |
| TestGenEval arXiv | `knowledge_note` | Compile/pass/coverage metric design warning. | Summarize if benchmark metrics change. |
| TestEval | `knowledge_note` | Coverage-targeted test-generation benchmark. | P1; avoid coverage-only drift. |
| TestEval Leaderboard | `discovery_index` | Model comparison reference. | Do not make provider platform. |
| TestEval arXiv | `knowledge_note` | Target-line/branch/path coverage task ideas. | Summary only. |
| ULT / UnLeakedTestBench | `knowledge_note` + possible `manifest_seed` | Decontaminated function-level benchmark idea. | P1; contamination design source. |
| ULT arXiv | `knowledge_note` | Accuracy/coverage/mutation metric warning. | Summary only. |
| TestBench | `readme_audit` + future `manifest_seed` | Java class-level test benchmark relevant to current kernel. | P0 README audit; possible tiny seed. |
| TestBench arXiv | `knowledge_note` | Java context construction and multi-dimensional evaluation. | Summarize for Java benchmark design. |
| ProjectTest | `knowledge_note` | Project-level testing benchmark idea. | P1 after manifest governance. |
| ProjectTest arXiv | `knowledge_note` | Project-level test-generation design. | Summary only. |
| TDD-Bench-Java / Reproduction Test Generation for Java SWE Issues | `knowledge_note` + possible `manifest_seed` | Java issue-to-reproduction-test framing. | P1; candidate kind/reference only. |
| JavaBench | `knowledge_note` | Java benchmark landscape reference. | Summary only. |
| SBFT Java Test Case Generation Track | `knowledge_note` | EvoSuite/Randoop comparison metric reference. | Use as producer baseline vocabulary. |

## 3. API / Integration Test Research And Benchmarks

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| RESTestBench | `knowledge_note` | API candidate judging metrics; requirement-based mutation idea. | Read when S6/S7 API evidence contract begins. |
| APITestGenie | `knowledge_note` | Requirement + OpenAPI + generated API integration tests. | Design source only; avoid RAG platform drift. |
| APITestGenie HTML | `knowledge_note` | Easier reading format for APITestGenie. | Read only if APITestGenie is selected. |
| SAINT | `knowledge_note` | Service-level integration test generation and dependency graph ideas. | Use for architecture-quality feedback concepts. |
| SAINT arXiv/SemanticScholar | `knowledge_note` | Backup citation/entry. | Read only if SAINT is selected. |
| AutoRestTest | `knowledge_note` | REST test-generation strategy. | Summary only. |
| AutoRestTest GitHub | `readme_audit` | Possible tool/design repo. | Audit only after S6 scope picks it. |
| RESTSpecIT / You Can REST Now | `knowledge_note` | API spec inference when docs are missing. | Use as Asset Gate warning; do not infer schemas automatically now. |
| QuickREST | `knowledge_note` | REST test strategy reference. | Summary only. |
| Empirical Comparison of REST API Test Generation Tools | `knowledge_note` | Tool comparison evidence. | Use to choose executor adapter later. |
| REST API Testing in DevOps | `knowledge_note` | Engineering workflow reference. | Summary only. |
| LLM-Based System Test Generation for REST APIs | `knowledge_note` | System-test generation ideas. | Design source only. |
| OAI Overlay for REST fuzzing | `knowledge_note` | OpenAPI augmentation/fuzzing idea. | Asset Gate/API schema risk note. |
| KAT / LLM + OpenAPI dependency graph | `knowledge_note` | Operation dependency graph idea. | Possible S8 integration signal. |

## 4. API Execution / Fuzzing / Contract Tools

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| Schemathesis | `readme_audit` + future `executor_adapter` | Candidate executor for `api_schema_candidate`. | P0 README audit; design adapter before install. |
| Schemathesis 文档 | `knowledge_note` | CLI/output/evidence shape. | Read during adapter design. |
| RESTler | `support_only` + future `executor_adapter` | Advanced stateful REST fuzzing executor. | S8+ after simple schema path works. |
| EvoMaster | `support_only` + future `executor_adapter` | Advanced API/system test generator/executor. | S8+; not first adapter. |
| RESTest | `support_only` + future `executor_adapter` | API test-generation executor candidate. | Defer. |
| RestTestGen | `support_only` + future `executor_adapter` | API generator/executor candidate. | Defer. |
| RestCT | `support_only` + future `executor_adapter` | Combinatorial REST testing candidate. | Defer. |
| Newman | `readme_audit` + future `executor_adapter` | Candidate executor for `api_collection_candidate`. | P0 README audit; design adapter before install. |
| Newman 文档 | `knowledge_note` | CLI JSON output and collection evidence shape. | Read during adapter design. |
| Karate | `support_only` + future `executor_adapter` | API test DSL executor candidate. | Defer until JUnit/schema/collection paths are evaluated. |
| Karate 官网 | `knowledge_note` | DSL capabilities reference. | Read only if Karate is selected. |
| Dredd | `support_only` + future `executor_adapter` | OpenAPI contract testing executor candidate. | Defer. |
| Dredd 文档 | `knowledge_note` | Contract-test evidence shape. | Read only if Dredd is selected. |
| Pact | `isolation_support` + future `executor_adapter` | Consumer-driven contract testing support. | Defer until contract candidate kind exists. |
| Pact Docs | `knowledge_note` | Contract test vocabulary. | Read only if contract tests are selected. |
| Prism | `isolation_support` | Mock server / OpenAPI simulation support. | Defer until API environment design. |
| Prism 官网 | `knowledge_note` | Mocking docs reference. | Read only if Prism is selected. |
| OpenAPI Generator | `producer_adapter` + support `executor_adapter` | Producer for API clients/stubs/tests; not judge core. | Treat generated output as candidate input only. |
| WireMock | `readme_audit` + `isolation_support` | Mock/external dependency isolation for API/integration candidates. | P0 README audit; no dependency until design. |
| Testcontainers | `readme_audit` + `isolation_support` | Containerized service/db dependency support. | P0 README audit; no Docker path until owner approval. |

## 5. Java Unit Test Generation And Quality Tools

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| EvoSuite | `producer_adapter` | External producer for JUnit candidates. | Design producer adapter; output enters `submit_candidate`. |
| Randoop | `producer_adapter` | External producer for JUnit candidates. | Design producer adapter; output enters `submit_candidate`. |
| ChatUniTest | `producer_adapter` + `readme_audit` | Java LLM test producer candidate; output only becomes submitted candidates. | Defer until producer comparison design; no generator race. |
| TestSpark | `knowledge_note` + possible `producer_adapter` | Java IDE/generator reference. | Defer; audit license/runtime before any adapter. |
| Pynguin | `support_only` + possible future `producer_adapter` | Python unit-test producer; useful for multi-language lessons, not current Java mainline. | Defer until multi-language candidate design exists. |
| CoverUp | `support_only` + possible future `producer_adapter` | Python coverage-oriented test producer. | Defer; avoid coverage-only drift. |
| Qodo Cover / Cover-Agent | `support_only` | External generator/repair reference with license/maintenance risk to audit. | Do not add dependency; no mainline adoption. |
| PIT / Pitest | `executor_adapter` already partly represented by gated mutation subsystem | Mutation evidence for weak oracle tests. | Keep gated; no product reroute around PIT. |
| JaCoCo | `executor_adapter` already live in judge kernel | Coverage delta evidence. | Keep core; improve parser robustness only. |
| TackleTest CLI | `producer_adapter` | Enterprise Java test producer baseline. | Read README before adapter; do not import now. |
| TackleTest Core | `producer_adapter` | Producer implementation reference. | README audit only if selected. |
| IBM TackleTest article | `knowledge_note` | Industrial producer lessons. | Summary only. |
| Auto Unit Test Case Generator | `producer_adapter` | Generic unit-test producer candidate. | Treat output as candidate only. |
| Diffblue Cover | `producer_adapter` | Commercial Java test producer. | External producer reference; no integration without approval. |
| GitHub Copilot tests docs | `producer_adapter` + `knowledge_note` | Human/IDE producer source. | Use provenance vocabulary only. |
| Amazon Q Developer test generation | `producer_adapter` + `knowledge_note` | IDE/cloud producer source. | Use provenance vocabulary only. |

## 6. Oracle / Assertion / Mutation Research

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| AugmenTest | `knowledge_note` | Oracle-generation evidence and risk reference. | Summarize for oracle-strength roadmap. |
| ChatAssert | `knowledge_note` | Assertion repair/generation warning. | Use for oracle-safety red lines. |
| TOGLL | `knowledge_note` | Correct/strong/diverse oracle metrics. | Summary only. |
| Understanding LLM-Driven Test Oracle Generation | `knowledge_note` | Oracle hallucination risk. | Add to oracle-strength references if needed. |
| STING | `knowledge_note` | Benchmark/test-suite augmentation warning. | P1; no auto augmentation. |
| UTBoost | `knowledge_note` + possible `readme_audit` | Shows benchmark tests may be too weak. | P1; summary first. |
| UTBoost GitHub | `readme_audit` | Concrete augmentation repo. | Audit only if selected. |
| MutGen | `knowledge_note` | Mutation-guided generation concept. | Summary only. |
| Meta ACH / Mutation-Guided LLM-based Test Generation | `knowledge_note` | Mutation-guided generation reference. | Summary only. |
| Meta TestGen-LLM | `knowledge_note` + `producer_adapter` concept | Human-in-loop generated test producer idea. | Do not copy workflow; output-as-candidate only. |
| GEM | `knowledge_note` | Mutation/oracle strength reference. | Summary only. |
| LLMorpheus | `knowledge_note` | LLM mutation testing research. | Defer. |
| PIT | `executor_adapter` already gated | Same as Pitest row; mutation evidence. | Keep gated. |

## 7. Bug / Badcase / Judge-Set Assets

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| Defects4J | `readme_audit` + future `dataset_slice` + `manifest_seed` | Java real-bug calibration and badcase seed source. | P0 README audit; 3-5 pinned seeds only after design. |
| GitBug-Java | `readme_audit` + future `dataset_slice` + `manifest_seed` | Recent Java bugs to reduce old-benchmark contamination. | P0 README audit; 3-5 pinned seeds only after design. |
| GitBug-Java arXiv | `knowledge_note` | Reproducibility and contamination notes. | Summary only. |
| BugSwarm | `support_only` + possible `manifest_seed` | CI fail/pass artifacts; heavier environment. | Defer. |
| BugSwarm publications | `knowledge_note` | CI artifact methodology. | Summary only. |
| Bears Benchmark | `support_only` + possible `manifest_seed` | Java bug dataset. | Defer after Defects4J/GitBug. |
| Bugs.jar | `support_only` + possible `manifest_seed` | Java bug dataset. | Defer. |
| QuixBugs | `support_only` + possible `manifest_seed` | Small bug tasks, often toy-like. | Defer; contamination caution. |
| Vul4J | `support_only` + possible `manifest_seed` | Security bug benchmark. | Defer; not current API/security goal. |
| FixEval | `support_only` | Repair/evaluation benchmark. | Defer. |
| BugRepo / BugHub | `discovery_index` + possible `manifest_seed` | Bug dataset discovery. | Track only. |
| Program Repair Benchmarks | `discovery_index` | Repair benchmark survey. | Track only. |
| From Bugs to Benchmarks | `knowledge_note` | Method for turning bugs into benchmarks. | Useful for Golden Set design. |
| From Bugs to Benchmarks arXiv | `knowledge_note` | Paper entry. | Summary only. |

## 8. API / Integration SUT And OpenAPI Assets

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| Spring PetClinic REST | `sut_target` + `readme_audit` + future `manifest_seed` | First small Java REST SUT for API smoke design. | P0 README audit; pin URL/commit later. |
| Spring PetClinic Microservices | `sut_target` support later | Microservice integration chain. | S8+ after REST MVP. |
| macrozheng/mall | `sut_target` support later | Business chain SUT: order/inventory/member. | Defer; one scenario only after MVP. |
| yudao-cloud | `sut_target` support later | Complex enterprise SUT. | Defer; too broad now. |
| EMB / EvoMaster Benchmark | `sut_target` + `manifest_seed` later | API benchmark SUT set for tool comparisons. | S8+; not first SUT. |
| EMB 备用组织 | `sut_target` backup | Backup source for EMB. | Track only. |
| OWASP crAPI | `sut_target` support later | Vulnerable API app for security-flavored API testing. | Defer; not current security platform. |
| APIs.guru OpenAPI Directory | `discovery_index` + possible `manifest_seed` | Source of public OpenAPI schemas. | Use only for small pinned schema smoke after S6. |
| APIs.guru 官网 | `discovery_index` | Directory docs and API. | Track only. |
| OpenAPI Initiative | `knowledge_note` | Schema/spec standard reference. | Read only for schema contract wording. |

## 9. LLM Observability / Prompt Eval / Trace Tools

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| Langfuse | `provenance_support` | Producer trace/version metadata only. | Downgrade; no verdict source. |
| Langfuse 官网 | `knowledge_note` | Trace/dataset/eval vocabulary. | Read only if provenance design needs it. |
| Phoenix | `provenance_support` | Producer trace/debug metadata only. | Downgrade; no verdict source. |
| Phoenix 官网 | `knowledge_note` | Observability vocabulary. | Read only if selected. |
| OpenTelemetry | `provenance_support` | Future trace/span vocabulary for producer or runner metadata. | Design only; no telemetry stack before provenance design. |
| promptfoo | `provenance_support` + `support_only` | Prompt/version eval support; not judge runtime. | Downgrade. |
| DeepEval | `support_only` | LLM-app evaluation; may help explanation quality only. | Defer; no LLM Judge verdict. |
| OpenAI Evals | `knowledge_note` | Eval packaging vocabulary. | Read only if eval-harness design needs it. |

## 9.1 Orchestration, Repair, Model, And Report-Sink Support

These assets appear in external reuse notes but are not mainline. They may be useful later only as
outer adapters or support surfaces after the judge/report contract is stable.

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| LangGraph | `support_only` | Optional outer orchestration vocabulary; must not contain judge semantics. | Do not rewrite pipeline into LangGraph. |
| PydanticAI | `support_only` | Possible typed worker pattern for future advisory agents. | No runtime adoption without owner gate. |
| mini-SWE-agent / SWE-agent | `support_only` + future `producer_adapter` concept | Future repairer may output a new candidate, never mutate old evidence. | Defer until repair-candidate contract. |
| OpenHands SDK | `support_only` + future `producer_adapter` concept | Coding-agent producer/repair reference. | Do not build agent platform. |
| AutoCodeRover | `support_only` | Repair-agent reference only. | Defer; no production-code repair path. |
| RepairAgent | `support_only` | Repair-agent reference only. | Defer; assertion/expected rewrite remains forbidden. |
| LiteLLM | `support_only` + `provenance_support` | Producer-side model gateway vocabulary. | No provider platform mainline. |
| vLLM / SGLang / Ollama / llama.cpp | `support_only` | Local inference references for producers only. | No serving stack in judge core. |
| reviewdog | `support_only` | Possible future report sink. | No PR comment publisher or auto-adoption path now. |
| PR-Agent | `support_only` | Code-review agent reference. | Do not turn project into code-review platform. |

## 10. Indexes, Forums, And Tracking Sources

| Asset | Intake shape | Project mapping | Next action |
|---|---|---|---|
| Awesome LLM Software Testing | `discovery_index` | Paper/resource discovery. | Track; do not generate backlog directly. |
| AwesomeLLM4UT | `discovery_index` | Unit-test generation discovery. | Track only. |
| Awesome Code LLM | `discovery_index` | Code-model benchmark discovery. | Track only. |
| Awesome Code Benchmark | `discovery_index` | Benchmark discovery. | Track only. |
| Awesome Repo-Level Code Generation | `discovery_index` | Repo-level generation discovery. | Track only. |
| Awesome Contract Testing | `discovery_index` | Contract-testing discovery. | Track only. |
| Defect Datasets Survey | `knowledge_note` | Dataset selection vocabulary. | Summary only. |
| arXiv cs.SE | `discovery_index` | Research tracking. | Search only when needed. |
| Papers with Code | `discovery_index` | Benchmark/model tracking. | Search only when needed. |
| Semantic Scholar | `discovery_index` | Paper lookup. | Search only when needed. |
| Hacker News SWE-bench 讨论 | `knowledge_note` | Community criticism of SWE-bench/test generation. | Optional summary; not evidence. |
| Reddit SWE-bench 讨论 | `knowledge_note` | Community criticism. | Optional summary; not evidence. |
| Reddit API 自动测试讨论 | `knowledge_note` | Practitioner pain points for API automation. | Optional summary; not evidence. |
| StackOverflow Java 自动单测讨论 | `knowledge_note` | Practitioner pain points for Java unit generation. | Optional summary; not evidence. |
| GitHub Topics: rest-api-testing | `discovery_index` | Repo discovery. | Track only. |
| GitHub Topics: combinatorial-testing | `discovery_index` | Repo discovery. | Track only. |

## 11. How To Use This Matrix In Future Designs

Every design should include a short "External Asset Mapping" block:

```text
External Asset Mapping:
- assets consulted:
- intake shape chosen:
- project artifact affected:
- evidence expected:
- red lines:
```

Examples:

```text
Schemathesis -> executor_adapter
  artifact: future api_schema_candidate runner design
  evidence: command, request/response summary, schema failures, reproducible logs
  red line: no install or executor before owner-approved S7 design

Defects4J -> dataset_slice + manifest_seed
  artifact: future benchmarks/manifest.s5-golden.draft.json
  evidence: pinned bug id, commit/version, command, expected failure/reproduction fact
  red line: no bulk import; no historical DB backfill

Langfuse -> provenance_support
  artifact: optional producer trace metadata
  evidence: producer/run/version ids only
  red line: never a quality proof or verdict source
```
