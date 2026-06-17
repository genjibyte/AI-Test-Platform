# TestAgent Lab Docs Index

> Layered archive for project documents. File names keep their original numeric
> order; folders provide the working layer.
>
> **Start here:** [`WORK_LOG.md`](/docs/WORK_LOG.md) — single context snapshot + latest audit
> (read it + `CLAUDE.md` to resume). The **binding design direction** is `CLAUDE.md`
> ("Design north-star") + [`40 §10`](/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md):
> an execution-based judge for test-generating agents; four pillars **Candidate / Provenance /
> Badcase / Asset Gate**; unit kernel done → Asset Gate next → gated API testing. External
> ecosystem survey: [`knowledge pack`](/docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md).
> The **value-judgment signal layer** (advisory, never auto-accepts) is docs **43** (run_kind),
> **45** (business-invariant tags), **46** (oracle-strength + mutation), **48** (invariant
> verification), **49** (survived-mutant classification), **50** (badcase retrieval), **51**
> (mock smells), **52** (review digest capstone), **53** (submit_candidate); forward roadmap **47**.

## 00 Foundation

- [00 Project Charter](/docs/00_foundation/00_PROJECT_CHARTER.md)
- [01 Project Plan](/docs/00_foundation/01_PROJECT_PLAN.md)
- [04 Env And Stack Decision](/docs/00_foundation/04_ENV_AND_STACK_DECISION.md)
- [07 Source Notes](/docs/00_foundation/07_SOURCE_NOTES.md)
- [13 Project Direction Review](/docs/00_foundation/13_PROJECT_DIRECTION_REVIEW.md)
- [24 Phase Next Design](/docs/00_foundation/24_PHASE_NEXT_DESIGN.md)
- [40 Core Thesis Repositioning](/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md)
- [42 AI Test Failure Empirical Audit](/docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md)
- [44 Decisions And Failures](/docs/00_foundation/44_DECISIONS_AND_FAILURES.md)
- [47 Six AI Problems Roadmap](/docs/00_foundation/47_SIX_AI_PROBLEMS_ROADMAP.md)

## 10 Phase 1

- [05 Phase 1 Backlog](/docs/10_phase1/05_PHASE1_BACKLOG.md)
- [06 Phase 1 Golden Sample](/docs/10_phase1/06_PHASE1_GOLDEN_SAMPLE.md)
- [08 Phase 1 Acceptance Report](/docs/10_phase1/08_PHASE1_ACCEPTANCE_REPORT.md)

## 20 Phase 2

- [09 Phase 2 Backlog](/docs/20_phase2/09_PHASE2_BACKLOG.md)
- [10 Phase 2 Midphase Audit](/docs/20_phase2/10_PHASE2_MIDPHASE_AUDIT.md)
- [11 Phase 2 Acceptance Report](/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md)

## 30 Phase 2.5 / 2.6 Quality

- [14 Phase 2.5 Benchmark](/docs/30_phase2_5_quality/14_PHASE2_5_BENCHMARK.md)
- [15 Phase 2.5 Result Review](/docs/30_phase2_5_quality/15_PHASE2_5_RESULT_REVIEW.md)
- [16 Model Comparison Review](/docs/30_phase2_5_quality/16_MODEL_COMPARISON_REVIEW.md)
- [17 Prompt Context V2](/docs/30_phase2_5_quality/17_PROMPT_CONTEXT_V2.md)
- [18 Phase 2.5 V2.1 And Repair Review](/docs/30_phase2_5_quality/18_PHASE2_5_V2_1_AND_REPAIR_REVIEW.md)
- [19 Minimal Test Quality Gate](/docs/30_phase2_5_quality/19_MINIMAL_TEST_QUALITY_GATE.md)
- [20 Phase 2.6 Quality Gated Review](/docs/30_phase2_5_quality/20_PHASE2_6_QUALITY_GATED_REVIEW.md)
- [21 Phase 2.6 Pro Quality Benchmark](/docs/30_phase2_5_quality/21_PHASE2_6_PRO_QUALITY_BENCHMARK.md)

## 40 Phase 3 / 4

- [12 Phase 3 Tooling Research](/docs/40_phase3_phase4/12_PHASE3_TOOLING_RESEARCH.md)
- [22 Phase 4 Review Policy Design](/docs/40_phase3_phase4/22_PHASE4_REVIEW_POLICY_DESIGN.md)
- [38 Compile Repair Replay Audit](/docs/40_phase3_phase4/38_COMPILE_REPAIR_REPLAY_AUDIT.md)
- [39 Compile Repair Enablement Plan](/docs/40_phase3_phase4/39_COMPILE_REPAIR_ENABLEMENT_PLAN.md)

## 50 Benchmark

- [23 Benchmark Manifest](/docs/50_benchmark/23_BENCHMARK_MANIFEST.md)
- [41 Precipitation Layer Design](/docs/50_benchmark/41_PRECIPITATION_LAYER_DESIGN.md)
- [43 run_kind Design](/docs/50_benchmark/43_RUN_KIND_DESIGN.md)
- [45 Business-Invariant Tagging Design](/docs/50_benchmark/45_BUSINESS_INVARIANT_TAGGING_DESIGN.md)
- [46 Oracle-Strength + Mutation Signal Design](/docs/50_benchmark/46_ORACLE_STRENGTH_SIGNAL_DESIGN.md)
- [48 Business-Invariant Verification Design](/docs/50_benchmark/48_BUSINESS_INVARIANT_VERIFICATION_DESIGN.md)
- [49 Survived-Mutant Classification Design](/docs/50_benchmark/49_SURVIVED_MUTANT_CLASSIFICATION_DESIGN.md)
- [50 Badcase Retrieval Design (#6)](/docs/50_benchmark/50_BADCASE_RETRIEVAL_DESIGN.md)
- [51 Mock / External-Dependency Smell Design (#4 judge-side)](/docs/50_benchmark/51_MOCK_SMELL_DESIGN.md)
- [52 Review Digest Design (#5 consolidation capstone)](/docs/50_benchmark/52_REVIEW_DIGEST_DESIGN.md)
- [53 submit_candidate Design (judge any producer)](/docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md)

## 60 Context V3 (generation-side, maintenance mode)

- [Context v3 → v3.2.3 Evolution Digest](/docs/60_context_v3/CONTEXT_V3_EVOLUTION_DIGEST.md)
  — consolidates the 9 per-run logs (25–37); originals in git history.

## 70 Preflight

- [Preflight Evolution Digest](/docs/70_preflight/PREFLIGHT_EVOLUTION_DIGEST.md)
  — consolidates the 4 preflight docs (32/33/34/36); originals in git history. The gate
  is live code (`app/quality/generated_test_preflight.py`).

## Knowledge (agent memory)

- [Knowledge Index](/docs/knowledge/README.md)
- [External Agent & Test Generation KB](/docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md)
- [Benchmark Sources & Strategy](/docs/knowledge/BENCHMARK_SOURCES_AND_STRATEGY.md)
- [Internet & Tech Business KB (test-value invariants)](/docs/knowledge/INTERNET_TECH_BUSINESS_KB.md)
- [External Ecosystem & Test-Asset Knowledge Pack (2026-06-17)](/docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md)
