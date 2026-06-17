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
| [`EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md`](EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md) | External ecosystem & test-asset survey (2026-06-17): tools/products/benchmarks/SUTs (PIT, Schemathesis, EvoMaster, Testcontainers, WireMock, Defects4J, TestExplora…) mapped to the four pillars. **Has a reconciliation header — several "Slices" are already built.** Reference/roadmap, not proof of implementation. |

## Status caveat (read before citing)

These docs reference some paths that are **PLANNED, not implemented** — e.g.
`AGENTS.md`, `docs/TASKS.md`, `docs/HANDOFF.md`, `docs/RUN_POLICY.md`,
`docs/QUALITY_GATE.md`, `docs/benchmark/*`, `docs/FAILURE_LEDGER.md`, `artifacts/runs/`,
`skills/`. Do **not** cite a knowledge doc as evidence a feature exists.
**Now built (no longer "planned"):** the **`run_kind`** field (docs/43), the gated
**`app/mutation/`** subsystem (docs/46), the producer-agnostic **`submit_candidate`** entry
(docs/53), and the badcase **retrieval** layer (`app/ledger/retrieval.py`, docs/50).

**What exists today:** quality gate = `app/quality/` + `docs/30_phase2_5_quality/19_MINIMAL_TEST_QUALITY_GATE.md`;
review policy = `app/review/`; reporting = `app/report/`; ledger = `app/ledger/`
(P1+P2); benchmark audit = `scripts/audit_bench.py` (heuristic fake/real split only);
agent guide = `CLAUDE.md`; test-safety guard = `tests/conftest.py`.

## Design north-star (binding — read with `CLAUDE.md`)

The product is an **execution-based judge for test-generating agents**, not a generator.
Every new design must strengthen one of the four pillars — **Candidate / Provenance /
Badcase / Asset Gate** — for *candidates of any origin*, and pass the anti-drift filter
("does this only make our own generator greener? then downgrade"). Build order: unit-test
judge kernel *(done)* → the four-pillar abstraction → *then* gated interface/API testing.
The authoritative statement is `CLAUDE.md` ("Design north-star") +
`docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` §10.

> **Status (2026-06-17):** `run_kind` (docs/43), the value-judgment signal layer
> (docs/45/46/48/49/51/52), badcase retrieval (docs/50), and the producer-agnostic
> `submit_candidate` entry (docs/53 S1+S2) have all **landed** — Candidate/Provenance/Badcase
> are live. **Next on-thesis step: the Asset Sufficiency Gate + Test-Level Router** (docs/40
> §10.3), then a gated API-test level. Feature work is no longer paused; each new level/phase
> is owner-gated + design-first.

Historical `bench.db` rows have no `run_kind`, so their fake/real split stays heuristic
and labeled (`scripts/audit_bench.py` prints that LIMITATION); historical data is read-only.
