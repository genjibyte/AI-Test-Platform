# External Project And Benchmark Registry

> Date: 2026-07-21
> Status: compact registry. This file preserves the project/benchmark candidate set after raw
> knowledge-pack pruning. It is not architecture, not an implementation backlog, and not approval
> to clone, install, download, execute, or vendor any external asset.

## 0. Why This Exists

The raw knowledge packs were too large and mixed current facts with stale plans, but deleting them
also made the external project and benchmark candidates harder to find. This registry keeps the
asset names, intake shapes, and next actions in one small place.

Use it with:

```text
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
docs/knowledge/EXTERNAL_REPO_README_AUDIT.md
docs/50_benchmark/23_BENCHMARK_MANIFEST.md
docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md
```

Every external asset still needs an intake shape, a phase gate, and, when required, a focused
README audit before design or implementation.

## 1. Current In-Repo Benchmark Assets

| Asset | Role | Status | Guardrail |
|---|---|---|---|
| `benchmarks/smoke.json` | Harness smoke check | Live local smoke manifest | Not model-quality evidence. |
| `benchmarks/manifest.v1.json` | Frozen Java/Maven unit benchmark | Live, 10 pinned Apache Commons cases | Do not edit in place; make a new version for changed pins. |
| `benchmarks/manifest.v2.json` | v1 pins plus business tags and invariant descriptors | Live advisory enrichment | Same code-under-test as v1; metadata changes no verdict. |
| `benchmarks/spec.example.json` | Example spec | Support only | Not a formal benchmark claim. |
| `var/benchmark/*/bench.db` | Historical benchmark artifacts | Read-only evidence | Historical rows without `run_kind` remain heuristic/unknown-labeled; never backfill. |

The benchmark files were not pruned. The previous prune removed old notes, not the current
benchmark manifests or benchmark runner code.

## 2. First External Audit Queue

These are the first assets to audit when external benchmark or adapter work resumes. Stop after
this list unless the owner explicitly widens the intake.

| Asset | Intake shape | Project artifact it may affect | Next action |
|---|---|---|---|
| SWE-bench | `readme_audit` + `knowledge_note` + future `manifest_seed` | Future `EvalTask`/report-evidence vocabulary | README audit only; no dataset import. |
| Claw-SWE-Bench | `readme_audit` + `knowledge_note` | Future adapter/workspace contract vocabulary | README audit only. |
| OpenHands Benchmarks | `readme_audit` + `knowledge_note` | Evaluation pipeline organization | README audit only. |
| Inspect AI | `readme_audit` + `knowledge_note` | Task/solver/scorer vocabulary | README/docs audit only; no dependency. |
| TestExplora | `readme_audit` + future `manifest_seed` | Repository-level generated-test evaluation design | README audit; possible tiny seed later. |
| TestBench | `readme_audit` + future `manifest_seed` | Java class-level benchmark design | README audit; possible tiny seed later. |
| Defects4J | `readme_audit` + future `dataset_slice` | Real-bug fail-to-pass calibration | No ingestion until owner-approved pilot. |
| GitBug-Java | `readme_audit` + future `dataset_slice` | Java real-bug candidate pool | README audit only. |
| Spring PetClinic REST | `readme_audit` + future `sut_target` | API/interface smoke SUT candidate | README audit only; no service orchestration. |
| Schemathesis | `readme_audit` + future `executor_adapter` | Future `api_schema_candidate` executor design | README audit only; no install. |
| Newman | `readme_audit` + future `executor_adapter` | Future `api_collection_candidate` executor design | README audit only; no install. |
| WireMock | `readme_audit` + `isolation_support` | API/integration dependency isolation | README audit only; no dependency. |
| Testcontainers | `readme_audit` + `isolation_support` | API/integration service isolation | README audit only; no Docker path. |

## 3. Deferred External Assets

These names are retained so they are not rediscovered repeatedly, but they are not next actions.

| Area | Assets | Current handling |
|---|---|---|
| Java test-generation producers | EvoSuite, Randoop, ChatUniTest, TestSpark, TackleTest, Diffblue Cover | `producer_adapter` candidates only; output enters `submit_candidate`, never platform identity. |
| Java/Python generation benchmarks | TestGenEval, TestEval, ULT, ProjectTest, TDD-Bench-Java, JavaBench, SBFT Java track, Pynguin, CoverUp | `knowledge_note` or future `manifest_seed`; defer until benchmark-governance design. |
| Real-bug datasets | Bugs.jar, Bears, BugSwarm | Future `dataset_slice`; no bulk import. |
| API/integration research | RESTestBench, APITestGenie, SAINT, AutoRestTest, RESTSpecIT, QuickREST, KAT | `knowledge_note`; use for API evidence/Asset Gate design, not executor work. |
| API execution tools | RESTler, EvoMaster, RESTest, RestTestGen, RestCT, Karate, Dredd, Pact, Prism, OpenAPI Generator | `support_only`, `executor_adapter`, or `isolation_support`; no install before approved adapter design. |
| SWE-agent ecosystems | SWE-Gym, SWE-smith, mini-SWE-agent, Harness-Bench, BenchFlow indexes | `support_only` or `discovery_index`; do not turn the product into an agent platform. |

## 4. Minimal Manifest-Seed Block

When an external benchmark candidate moves from registry to design, record only this first:

```text
asset_id:
intake_shape:
project_artifact:
source_url:
pinned_version_or_commit:
license_spdx:
task_count_requested:
candidate_kind:
expected_evidence:
requires_network:
requires_docker:
requires_model_or_api_key:
red_lines:
next_action:
```

This block is metadata, not approval. A real dataset slice or executor still needs a separate
owner-approved design and no-verdict-drift tests.

## 5. Anti-Drift Rule

External benchmark work is useful only when it strengthens one of:

```text
Candidate input shape
Provenance and run_kind hygiene
Badcase/RCA precipitation
Asset sufficiency and test-level routing
Reproducible report evidence
```

If an asset mainly improves the built-in generator's pass rate, makes a prompt race, or pulls the
platform toward a generic agent/eval/RAG system, keep it as `support_only` or `reject_mainline`.
