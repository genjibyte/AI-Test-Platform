# Knowledge Base - Agent Memory

These files are external lessons and reference material. They are not current architecture and
not proof that a feature exists.

For current state, do not start here. Read:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
```

Then return here only when the active task needs an external lesson, repo intake, benchmark
source, or skill/SOP pattern.

## Files

| File | Use |
|---|---|
| `EXTERNAL_ASSET_MAPPING_MATRIX.md` | Required mapping matrix for external assets. Every asset must map to an intake shape before design or implementation. |
| `AGENT_HARNESS_EVALUATION_KB.md` | Agent/Harness evaluation lessons from the new PDFs, reconciled with this repo's judge-first boundary. |
| `EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md` | External tools, benchmarks, and test-asset landscape mapped to the four pillars. |
| `EXTERNAL_AGENT_AND_TESTGEN_KB.md` | External agent/test-generation lessons and anti-drift reminders. Historical status may be stale. |
| `BENCHMARK_SOURCES_AND_STRATEGY.md` | Benchmark source options and strategy notes. |
| `INTERNET_TECH_BUSINESS_KB.md` | Business-domain invariants useful for human review and benchmark manifests. |

## Knowledge Architecture

Role in the project three-layer read mechanism:

```text
Layer 1: this index + EXTERNAL_ASSET_MAPPING_MATRIX.md
Layer 2: only the named knowledge/design file required by the active design
Layer 3: external repo README audits, benchmark reports, ledger records, or source evidence
```

Knowledge docs should be read as patterns, warnings, and design vocabulary. They should not be
treated as implementation truth or an automatic backlog.

Design knowledge gate:

```text
Every design must read docs/knowledge/README.md and
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md before using external assets.
If an external asset is mentioned, the design must name its intake shape.
```

When importing a new external lesson, classify it first:

```text
adopt      -> strengthens candidate judging, evidence, comparison, RCA, or asset sufficiency
downgrade  -> useful producer-side support, demo aid, or research note
reject     -> prompt race, generic RAG/platform, auto-accept, auto-merge, or broad web/backend drift
```

For Skill-style knowledge, use the same filter. A Skill should encode a bounded judge workflow:
trigger, inputs, steps, evidence, red lines, output, and fallback. It should not smuggle in a new
product surface.

## Caveat

Some knowledge docs mention planned or historical paths such as `CLAUDE.md`, `docs/TASKS.md`,
`docs/HANDOFF.md`, `docs/RUN_POLICY.md`, `docs/QUALITY_GATE.md`, `artifacts/runs/`, or `skills/`.
Do not treat those mentions as current repo facts.

Built capabilities must be verified from code and active docs. Current live areas include:

- `run_kind` hygiene
- quality gate and review policy
- gated mutation subsystem
- invariant review
- mock smell
- badcase ledger and retrieval
- producer-agnostic `submit_candidate`
- Asset Gate S1-S4A, including report-only Test-Level Router; not a live executor
- Agent/Harness external evaluation lessons are knowledge only; the project does not become a
  prompt-based evaluator or multi-agent workflow platform.

External asset lists should first pass through `EXTERNAL_ASSET_MAPPING_MATRIX.md`. Do not clone,
vendor, copy, or install tools from an external list before the asset has an intake shape, a small
README audit when needed, and an owner-approved design deciding its role.

## Current North-Star

TestAgent Lab is an execution-based judge for test candidates from any producer.

Every new design should strengthen Candidate, Provenance, Badcase, or Asset Gate. If a change only
improves the built-in generator's compile/pass rate, downgrade it unless it fixes a false-trust or
oracle-safety issue.

Historical benchmark DB rows without `run_kind` remain read-only and heuristic-labeled.
