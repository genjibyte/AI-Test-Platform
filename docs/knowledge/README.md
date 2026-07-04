# Knowledge Base - Agent Memory

These files are external lessons and reference material. They are not current architecture and
not proof that a feature exists.

For current state, read:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
```

## Files

| File | Use |
|---|---|
| `EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md` | External tools, benchmarks, and test-asset landscape mapped to the four pillars. |
| `EXTERNAL_AGENT_AND_TESTGEN_KB.md` | External agent/test-generation lessons and anti-drift reminders. Historical status may be stale. |
| `BENCHMARK_SOURCES_AND_STRATEGY.md` | Benchmark source options and strategy notes. |
| `INTERNET_TECH_BUSINESS_KB.md` | Business-domain invariants useful for human review and benchmark manifests. |

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
- Asset Gate S1-S3D
- Test-Level Router S4A is report-only live, not a live executor

## Current North-Star

TestAgent Lab is an execution-based judge for test candidates from any producer.

Every new design should strengthen Candidate, Provenance, Badcase, or Asset Gate. If a change only
improves the built-in generator's compile/pass rate, downgrade it unless it fixes a false-trust or
oracle-safety issue.

Historical benchmark DB rows without `run_kind` remain read-only and heuristic-labeled.
