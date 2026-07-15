# API Candidate Judge Boundary

> Date: 2026-07-10  
> Status: S6 mainline-direction design entrypoint. Documentation only; no executor, dependency,
> schema discovery, or candidate-kind implementation is implied.

## 0. Why This Exists

The project should not stay unit-test-only. The mainline is:

```text
candidate -> isolated execution evidence -> advisory signals -> digest -> ledger -> report
```

Unit tests are the current kernel, not the product boundary. API/interface candidate evaluation is
a near-term mainline expansion when it reuses the same judge discipline.

This direction can expand beyond one fixed path. Interface tests, generated automation tests,
JUnit API tests, schema-based cases, collections, or human-authored cases may all be candidates if
they enter the same platform form:

```text
execute -> judge -> attribute -> precipitate badcase -> report
```

## 1. Three-Layer Read Set For This Design

Follow `docs/README.md` for the canonical three-layer read mechanism. API/interface design adds
these Layer 2 reads:

```text
docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md   # §10 only unless needed
docs/60_api_candidate/01_MINIMAL_JUDGE_CONTRACT.md   # minimal JudgeCase/Runner/Evidence/Report contract
docs/60_api_candidate/02_API_CANDIDATE_BOUNDARY_DESIGN.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md      # only for Spring PetClinic/Schemathesis/Newman intake
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md   # only when changing router/Asset Gate behavior
```

For S6B/S6C report-evidence or smoke-path design, also read
`docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md`.

Layer 3 remains proof-only: code/tests for touched modules, external repo README audits only when
the matrix says `readme_audit`, and benchmark/ledger evidence only when report or metric policy
changes. Do not load the whole knowledge base for this design.

## 2. Allowed Scope

S6 should define the minimum contract needed to bring API/interface and automated-test-generation
outputs into the evaluation mainline:

- `candidate_kind` names for API/interface candidates.
- Input shape for OpenAPI/schema, Postman collection, or JUnit API-test candidates.
- Deterministic evidence required in the report: request, response, status, assertion, schema,
  fixture, mock, service, and environment facts.
- How API evidence maps into the existing review, badcase, benchmark, and report surfaces.
- What must remain owner-gated before any executor runs.

## 3. Non-Goals

S6 must not:

- add an API/integration executor;
- install Schemathesis, Newman, RESTler, EvoMaster, Docker, or new dependencies;
- discover schemas, databases, services, credentials, or `.env`;
- create headline metrics for API rows;
- auto-accept, auto-reject, auto-merge, or mark `trusted=True`;
- become a general API automation framework.

## 4. First Contract Questions

The next concrete design should answer:

```text
candidate_kind:
input_artifact:
required_assets:
execution_boundary:
evidence_record:
api_report_fields:
quality_signals:
badcase_fields:
report_fields:
run_kind/headline_policy:
owner_gate:
tests_to_prove_no_drift:
```

Use `01_MINIMAL_JUDGE_CONTRACT.md` as the vocabulary guardrail. Do not expand S6 into a generic
plugin, runner, or workflow framework.

## 5. Earliest S7 Direction

After this boundary is approved, the smallest S7 path should be one smoke design only:

```text
Spring PetClinic REST as SUT
Schemathesis or Newman as one executor adapter candidate
no broad API platform
no automatic adoption of generated cases
```
