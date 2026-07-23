# 60 - API Smoke Ledger Projection Design

> Date: 2026-07-21
> Status: S10A compact ledger carry, S10B pure ledger projection helper, and S10C presentation are live. S10A adds
> optional `JudgedRecord` JSON fields and copies valid S8 denominator facts through
> `record_from_bench_case(...)`; S10B adds `api_smoke_ledger_projection(...)` as a named pure
> helper; S10C adds `render_api_smoke_ledger_markdown(...)` as a conditional Markdown renderer.
> No SQLite column/index, existing ledger analytics change, retrieval change, badcase
> signature change, executor, dependency, external SUT import, digest severity, verdict change,
> `trusted=True`, or auto-accept is implied.
>
> Upstream: `docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md`,
> `docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md`,
> `docs/50_benchmark/43_RUN_KIND_DESIGN.md`, and
> `docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md`.

## 0. Purpose

S8 emits report-only API smoke denominator facts under:

```text
review_summary["api_smoke_denominator"]
```

S9A/S9B make those facts visible in benchmark projection and markdown without changing aggregate
headlines.

S10 defines the ledger-side precipitation path for the same compact facts. The purpose is to
let future maintainers answer:

- which judged records carried API smoke denominator facts;
- which records were denominator-ready under S8;
- which `run_kind`, `smoke_id`, candidate kind, and failed requirements explain the shape;
- how those records relate to existing badcases without changing badcase signatures.

It does not prove API correctness, test usefulness, defect discovery, or acceptance.

## 1. Core Decision

S10 must mirror the Asset Gate ledger pattern:

```text
BenchCaseResult.review_summary
  -> record_from_bench_case(...)
  -> compact JudgedRecord JSON fields
  -> optional pure descriptive summary
```

The first implementation slice, S10A, is compact carry only. It does not add SQLite indexed
columns. The existing `LedgerStore` already stores full `JudgedRecord` JSON, so optional fields
round-trip through `record_json` without changing the durable table shape.

The second implementation slice, S10B, adds a pure summary helper over `list[JudgedRecord]`.
It does not feed existing `ledger_summary(...)`, `aggregate_badcases(...)`, retrieval scoring,
badcase signatures, digest, or verdicts.

The third implementation slice, S10C, renders the named S10B projection for human readers. It
does not attach to existing ledger analytics, change retrieval, or create a new score.

## 2. Source Authority

The only sanctioned source for S10 carry is the S8 block:

```text
BenchCaseResult.review_summary["api_smoke_denominator"]
```

The source block must be accepted only when:

```text
policy_version == "api_smoke_denominator.v1"
scope == "separate_api_smoke_denominator"
```

Do not infer API smoke facts from:

```text
candidate_kind alone
test class names
producer_id
run_kind
passing Maven/Surefire execution
asset_sufficiency
test_level_router
api_evidence without the S8 denominator block
```

Run-kind authority remains top-level:

```text
BenchCaseResult.run_kind -> JudgedRecord.run_kind
```

The copied denominator `run_kind` is provenance context only and must not promote an unknown
top-level `run_kind` into a headline view.

## 3. Compact Carry Shape

S10A adds only these optional compact fields to `JudgedRecord`:

```text
api_smoke_policy_version: str | None = None
api_smoke_scope: str | None = None
api_smoke_smoke_id: str | None = None
api_smoke_candidate_kind: str | None = None
api_smoke_denominator_eligible: bool | None = None
api_smoke_not_eligible_reasons: list[str] = []
api_smoke_requirement_failures: list[str] = []
api_smoke_benchmark_counting_enabled: bool | None = None
api_smoke_unit_headline_eligible: bool | None = None
```

These fields are facts about denominator readiness, not quality scores.

Do not carry:

```text
raw request bodies
raw response bodies
headers with secrets
cookies
tokens
payload samples
OpenAPI schema dumps
service URLs beyond already-redacted report facts
database snapshots
full manifest JSON
full api_evidence JSON
```

If a future maintainer needs one more field, the bar is: compact, already emitted by the report,
redacted, useful for denominator/replay explanation, and covered by no-verdict-drift tests.

## 4. Carry Semantics

`record_from_bench_case(...)` should copy facts without recomputing policy:

```text
denominator = result.review_summary["api_smoke_denominator"]
api_smoke_denominator_eligible = denominator["eligible_for_api_smoke_denominator"]
api_smoke_not_eligible_reasons = denominator["not_eligible_reasons"]
api_smoke_requirement_failures = names where denominator["requirements"][name] is not True
```

Missing, malformed, wrong-policy, or wrong-scope blocks must produce default values:

```text
api_smoke_policy_version = None
api_smoke_denominator_eligible = None
api_smoke_not_eligible_reasons = []
api_smoke_requirement_failures = []
```

Do not backfill historical ledger rows. They remain absent/unknown for this projection.

## 5. Ledger Views

S10B adds a named pure helper:

```text
api_smoke_ledger_projection(records, *, view="raw" | "headline") -> dict
```

RAW view:

```text
included records =
  records with api_smoke_policy_version == "api_smoke_denominator.v1"
  and api_smoke_scope == "separate_api_smoke_denominator"
run_kind filter = none
```

API smoke HEADLINE view:

```text
included records =
  RAW source records
  and api_smoke_denominator_eligible is True
  and JudgedRecord.run_kind in {"real", "external"}
```

Why `external` is included: public `submit_candidate` rows are external by design, and API smoke
candidate evaluation is producer-agnostic. This is separate from existing real-model unit-test
headlines.

Do not modify:

```text
ledger_summary(...)
aggregate_badcases(...)
author_profile(...)
compare_authors_on_target(...)
business_summary(...)
oracle_strength_summary(...)
asset_gate_summary(...)
badcase_signature(...)
find_similar(...)
```

Those existing helpers retain their current meanings unless a later owner-approved design says
otherwise.

## 6. Relationship To Badcase Memory

API smoke ledger carry is a denominator/evidence projection. It is not a new failure taxonomy.

Badcase signature remains:

```text
<failure_type>@<target_class>#<target_method|*>
```

Do not add `smoke_id`, endpoint, HTTP status, schema status, or eligibility status into
`badcase_signature(...)` in S10. Those may be useful later, but they require real smoke execution
evidence and an API failure taxonomy.

Retrieval may eventually display compact API smoke facts as context, but it must not rank by them
in S10. A previous API smoke record is precedent only after a human can see the underlying judged
evidence.

## 7. Metrics Boundary

Allowed automated ledger counts:

```text
api_smoke_source_records
eligible_source_records
ineligible_source_records
by_run_kind
by_candidate_kind
by_smoke_id
not_eligible_reason_counts
requirement_failure_counts
gen_outcome_distribution
quality_gate_distribution
review_recommendation_distribution
need_human_review_records
unit_headline_eligible_records
```

Not allowed:

```text
usable_test_rate
defect_discovery_rate
human_handling_time
diagnosis_time
misjudgment_rate
accept_rate
API correctness score
auto-accept
auto-adoption
```

Green execution, denominator eligibility, and producer identity are not value proof.

## 8. Implementation Slices

Recommended bounded order:

```text
S10A compact ledger carry - live
  optional JudgedRecord JSON fields only
  copy from BenchCaseResult.review_summary["api_smoke_denominator"]
  no SQLite columns or indexes
  no analytics helper yet

S10B pure ledger projection helper - live
  api_smoke_ledger_projection(records, view="raw"|"headline")
  separate from ledger_summary and aggregate_badcases
  top-level JudgedRecord.run_kind is headline authority

S10C presentation - live
  render_api_smoke_ledger_markdown(records)
  conditional Markdown only; empty for ledgers with no API smoke source records
```

S10C still does not approve existing analytics changes, retrieval, badcase-signature changes,
executor, or schema/index work.

## 9. Tests

S10A carry tests (live in `tests/test_ledger.py`):

```text
record_from_bench_case copies compact API smoke fields from a valid S8 block
record_from_bench_case defaults fields when no S8 block exists
wrong policy_version/scope is ignored
requirement failures are derived from requirements where value is not True
badcase_signature(...) is unchanged
LedgerStore round-trips fields through record_json
SQLite table/index set is unchanged
conclusion remains NEED_HUMAN_REVIEW
no trusted=True path is introduced
```

S10B projection tests (live in `tests/test_api_smoke_ledger_projection.py`):

```text
RAW includes all source records
HEADLINE includes eligible real/external only
HEADLINE excludes fake, dryrun, smoke, unknown/null, and ineligible records
top-level JudgedRecord.run_kind is authoritative
existing ledger_summary(...) and aggregate_badcases(...) keys/values stay unchanged
external rows remain excluded from existing real-only ledger analytics
no accept_rate or usable-test language appears
```

S10C presentation tests (live in `tests/test_api_smoke_ledger_projection.py`):

```text
unit-only ledgers render no API smoke Markdown
RAW and separate HEADLINE sections render from the S10B projection
HEADLINE excludes fake and ineligible rows
ledger_summary(...) and aggregate_badcases(...) remain unchanged
no accept_rate or usable-test language appears
```

No test may start a service, Docker container, external API executor, real model, or networked SUT.

## 10. External Asset Mapping

External Asset Mapping:

```text
assets consulted: none for S10A-S10C
intake shape chosen: none
project artifact affected: app/ledger/models.py, app/ledger/ingest.py,
  app/ledger/api_smoke_projection.py, app/ledger/api_smoke_report.py, tests/test_ledger.py,
  tests/test_api_smoke_ledger_projection.py
expected evidence: local S8 denominator facts already emitted by the judge
red lines: no external asset execution, no SUT import, no dependency, no executor, no schema/index
```

## 11. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  cross-run memory for API smoke denominator readiness through compact ledger JSON carry and a
  named pure projection helper, with conditional human-readable presentation
- automated evidence:
  S8 denominator eligibility, run_kind, smoke_id, candidate_kind, requirement failures, existing
  Maven/Surefire judge outcome, quality gate status, advisory recommendation, conclusion invariant
- human labels required:
  yes for usable-test rate, defect discovery, diagnosis time, human handling time, and misjudgment
  rate; no for denominator eligibility facts
- denominator:
  RAW = all ledger records with valid API smoke carry; HEADLINE = eligible records with run_kind
  real/external
- headline eligibility:
  separate API smoke ledger headline only; never current unit-test real headline
- red lines:
  no executor, no dependency, no SQLite index, no badcase signature change, no digest severity,
  no auto-accept, no trusted=True, no claim that green API smoke equals engineering value
```

## 12. Definition Of Done

S10A/S10B/S10C are sufficient if the next maintainer can answer:

- why S10 is compact ledger carry, not a schema/index migration;
- why API smoke ledger RAW and HEADLINE are separate from existing ledger analytics;
- why `external` is valid in API smoke headline but excluded from existing unit-test real headline;
- why badcase signatures and retrieval scoring do not change;
- which fields can be carried without raw payloads or human labels;
- why presentation is conditional and separate from existing ledger analytics;
- which tests prove no verdict, digest, aggregate, signature, or SQLite drift occurred.
