# Knowledge Base — agent memory

Durable, project-scoped knowledge for future agents (Claude Code / Codex / reviewer /
human). These are **lessons, strategy, and reference**, not architecture and not proof
of implementation.

## Contents

| File | Role |
|---|---|
| [`EXTERNAL_AGENT_AND_TESTGEN_KB.md`](EXTERNAL_AGENT_AND_TESTGEN_KB.md) | External industrial/research lessons (Meta TestGen-LLM/ACH/Sapienz, harness engineering, benchmark hygiene, test-smell quality) + the immediate project rules they imply (judge-not-generate, `run_kind`, headline-metrics). |
| [`BENCHMARK_SOURCES_AND_STRATEGY.md`](BENCHMARK_SOURCES_AND_STRATEGY.md) | Layered benchmark strategy (smoke → real Java/Maven → real-bug fail-to-pass → issue/agent), source-by-source assessment (Defects4J, GitBug-Java, ProjectTest, AgoneTest, Methods2Test, EvoSuite/Randoop/PIT…), the required manifest schema, and the first-10 cases. |
| [`INTERNET_TECH_BUSINESS_KB.md`](INTERNET_TECH_BUSINESS_KB.md) | Business-domain → testable-invariant map (payments, search, ads, e-commerce, identity, reliability…), used as a **filter**: a generated test is strong only if it protects a meaningful business invariant. |

## Status caveat (read before citing)

These docs reference many paths that are **PLANNED, not implemented** — e.g.
`AGENTS.md`, `docs/TASKS.md`, `docs/HANDOFF.md`, `docs/RUN_POLICY.md`,
`docs/QUALITY_GATE.md`, `docs/benchmark/*`, `docs/FAILURE_LEDGER.md`, `artifacts/runs/`,
`app/mutation/`, `skills/`, and the **`run_kind`** field. Do **not** cite a knowledge
doc as evidence a feature exists.

**What exists today:** quality gate = `app/quality/` + `docs/30_phase2_5_quality/19_MINIMAL_TEST_QUALITY_GATE.md`;
review policy = `app/review/`; reporting = `app/report/`; ledger = `app/ledger/`
(P1+P2); benchmark audit = `scripts/audit_bench.py` (heuristic fake/real split only);
agent guide = `CLAUDE.md`; test-safety guard = `tests/conftest.py`.

## Convergent priority (all three docs agree)

> **`run_kind` is the critical next step.** Sequence:
> `benchmark hygiene → run_kind → schema-based audit → Layer 1 Java/Maven pilot → Defects4J 3-bug pilot`.

Until `run_kind` exists, every fake/real metric split is heuristic and must be labeled
incomplete (`scripts/audit_bench.py` already prints that LIMITATION). Feature work
stays paused per `CLAUDE.md`; design/planning is allowed.
