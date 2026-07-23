# 09 - S8 API Smoke Denominator Policy

> Date: 2026-07-20
> Status: S8 report-only denominator policy V1 and S8B red-line summary V1 are live. No executor,
> service orchestration, dependency, benchmark schema change, ledger schema change, digest
> severity change, headline metric, external SUT import, or verdict change is implied.

## 0. Purpose

S7D1/S7D2 can now carry compact API smoke manifest facts from `submit_candidate` into:

```text
review_summary["api_smoke_manifest"]
```

S8 defines the next small boundary: a report-only policy block that says whether a manifest-bound
`junit_api_candidate` row has enough local facts to be a future API-smoke denominator row.

It does not count the row in benchmark or ledger.

S8B adds a reviewer-facing red-line summary over the same report facts:

```text
review_summary["api_smoke_redlines"]
```

It highlights whether compact API evidence, manifest alignment, redaction, local execution
boundary, denominator readiness, and authority invariants are present/satisfied. It is still
report-only and does not feed digest severity, recommendation, conclusion, benchmark/ledger
analytics, or trust.

S8C adds optional Markdown presentation through:

```text
render_api_smoke_redlines_markdown(review_summary)
```

It renders nothing when the red-line summary is absent and remains presentation-only: no endpoint,
executor, benchmark/ledger wiring, digest signal, or verdict/trust authority.

## 1. Decision

S8 V1 adds a report-only block:

```text
review_summary["api_smoke_denominator"] = {
  "advisory": true,
  "report_only": true,
  "policy_version": "api_smoke_denominator.v1",
  "scope": "separate_api_smoke_denominator",
  "smoke_id": "...",
  "candidate_kind": "junit_api_candidate",
  "run_kind": "external | real | fake | dryrun | smoke | null",
  "eligible_for_api_smoke_denominator": true | false,
  "benchmark_counting_enabled": false,
  "unit_headline_eligible": false,
  "not_eligible_reasons": [...],
  "requirements": {
    "manifest_present": true,
    "manifest_status_allowed": true | false,
    "candidate_kind_matches": true | false,
    "target_matches_generation": true | false,
    "api_evidence_present": true | false,
    "api_evidence_candidate_kind_matches": true | false | null,
    "runner_tool_matches": true | false | null,
    "redaction_contract_satisfied": true | false | null,
    "maven_judge_evidence_present": true | false,
    "conclusion_needs_review": true | false,
    "trusted_false": true | false
  }
}
```

Rules:

- Attach this block only when `review_summary["api_smoke_manifest"]` exists.
- Set `eligible_for_api_smoke_denominator=true` only when every requirement is satisfied.
- Keep `benchmark_counting_enabled=false` in S8 V1.
- Keep `unit_headline_eligible=false` always; API smoke rows must never mix into current unit-test
  real headlines.
- Do not feed digest severity.
- Do not add `BenchCaseResult` fields.
- Do not add `aggregate(...)` keys.
- Do not write ledger fields or signatures.

## 2. Eligibility

Eligible means:

```text
manifest.status in {"approved", "active"}
manifest.candidate_kind == "junit_api_candidate"
manifest target is already aligned by S7D
caller supplied compact api_evidence
api_evidence.candidate_kind matches manifest
api_evidence.execution.runner_tool == "maven_surefire_jacoco"
api_evidence redaction says request/response bodies and secrets were not persisted
existing Maven/Surefire judge produced a gen_outcome fact
report conclusion remains NEED_HUMAN_REVIEW
report trusted remains False
```

Non-eligible examples:

```text
manifest.status = designed
  -> not_eligible_reasons includes manifest_status_not_approved_or_active

manifest carried without supplied api_evidence
  -> not_eligible_reasons includes api_evidence_absent

execution has no gen_outcome
  -> not_eligible_reasons includes maven_judge_evidence_absent
```

Eligibility is not correctness. It means the row has the minimum local evidence shape for a future
separate API-smoke denominator.

## 3. Relationship To S7D Alignment

S7D currently writes:

```text
review_summary["api_smoke_manifest"]["alignment"]["denominator_ready"]
```

S8 V1 sets that value from `eligible_for_api_smoke_denominator`.

Important distinction:

```text
denominator_ready = row satisfies S8 report-only eligibility requirements
benchmark_counting_enabled = false in S8 V1
```

So a row can be denominator-ready for review while still not counted by any benchmark or ledger
view.

## 4. Benchmark Boundary

S8 V1 must not change:

```text
BenchCaseResult
aggregate(...)
asset_gate_breakdown(...)
validation_line_summary(...)
render_markdown(...)
ledger ingest
ledger analytics
SQLite schemas or indexes
```

S9A implements the pure helper designed in
`docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md`; S9B conditional markdown
rendering is live and renders only when API smoke source rows exist. S10A compact ledger JSON
carry and S10B pure ledger projection helper are live in
`docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md`; S10C presentation is live as a
conditional renderer over the named projection. This line must keep:

```text
unit-test real headline != API smoke headline
external submit rows != real-model unit headline
raw API smoke view != headline API smoke view
```

## 5. Tests Required

```text
tests/test_api_smoke_denominator.py
  eligible approved/active manifest with aligned evidence becomes denominator-ready
  designed/retired manifest is not eligible
  missing supplied api_evidence is not eligible
  missing Maven/Surefire gen_outcome is not eligible
  report block is absent for ordinary unit candidates
  digest does not read api_smoke_denominator
  conclusion remains NEED_HUMAN_REVIEW
  trusted remains False

tests/test_api_smoke_redlines.py
  ordinary unit reports have no API smoke red-line summary
  clean manifest/evidence/denominator facts satisfy red lines
  missing supplied api_evidence is surfaced once
  unsafe-looking supplied summary facts are flagged without granting authority

tests/test_api_smoke_redlines_report.py
  absent summaries render empty
  existing summaries render boundary facts and flags for humans
  public app.report import remains available
```

No test may start a service, Docker container, external API executor, or real model.

## 6. External Asset Mapping

External Asset Mapping:

```text
assets consulted: none for S8 V1
intake shape chosen: none
project artifact affected: review_summary["api_smoke_denominator"]
expected evidence: manifest/evidence/execution eligibility facts
red lines: no external asset execution, no SUT import, no executor, no dependency
```

## 7. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  future separate API smoke denominator discipline
- automated evidence:
  manifest status, smoke_id, candidate_kind, target alignment, compact api_evidence alignment,
  Maven/Surefire gen_outcome presence, conclusion/trust invariants
- human labels required:
  no for denominator eligibility facts; yes for usable-test rate, defect discovery, diagnosis
  time, human handling time, and misjudgment rate
- denominator:
  report-only eligibility plus separate S9 benchmark projection/display; not counted in ledger in
  S8/S9 V1
- headline eligibility:
  false for current unit-test real headline; future API smoke headline requires a later design
- red lines:
  no executor, no dependency, no benchmark/ledger schema change, no digest severity, no
  auto-accept, no trusted=True
```

## 8. Definition Of Done

S8 V1 is sufficient if the next maintainer can answer:

- where denominator eligibility appears in the report;
- where red-line summary facts appear in the report;
- how to render the red-line summary for a human handoff;
- why eligibility is not correctness;
- why red-line flags are review prompts, not digest or verdict signals;
- why benchmark counting remains disabled;
- why unit-test real headlines stay unchanged;
- which missing facts make a row non-eligible;
- why digest, benchmark, ledger, conclusion, recommendation, and trust do not drift.
