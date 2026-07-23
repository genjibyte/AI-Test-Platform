# 57 - Human Review And RCA Label Contract

> Date: 2026-07-12
> Status: S5C design with V1 pure validation slice live. No schema change, SQLite index, ledger
> migration, benchmark headline change, UI workflow, model call, LLM judge, historical backfill, or
> automatic RCA implementation is implied.

## 0. Purpose

This document defines the minimum human-review and RCA label contract needed after the V1
real-world validation line.

Current route:

```text
candidate -> deterministic judge evidence -> advisory signals -> review digest
  -> human label / RCA -> badcase memory -> reproducible report
```

V1 automated metrics are live in `app/benchmark/validation_line.py`. The next convincing landing
metrics require human or golden labels:

- usable test rate;
- human edit count;
- human handling time;
- diagnosis time;
- misjudgment rate;
- defect discovery rate when linked to a verifier or human-confirmed product bug.

S5C keeps this evidence-bound. The platform may suggest likely causes, but it must not fill
`root_cause`, `fix_note`, or human disposition automatically.

## 1. Current Anchor

Live ledger fields already exist:

```text
JudgedRecord.root_cause: Optional[str]
JudgedRecord.fix_note: Optional[str]
```

They are advisory, human/external-author declared, and default to `None`. Retrieval already
surfaces them as precedent. S5C stabilizes the language around these fields before adding any new
persistence fields.

Do not change `badcase_signature` in this design. It remains derived from observed failure facts.

## 2. Non-Goals

S5C must not:

- auto-classify RCA as fact;
- use an LLM judge to decide usability or root cause;
- treat `STRONG_REVIEW_CANDIDATE` as human usable;
- backfill historical records;
- add SQLite indexes or migrate the ledger in the first slice;
- change recommendation, digest severity, `conclusion`, or `trusted`;
- turn human labels into auto-accept or auto-warehouse behavior;
- expand into a task-management or review-platform product.

## 3. Label Shape

Use this shape as the future sidecar / API / CLI label contract:

```text
HumanReviewLabel = {
  "schema_version": "human_review_label.v1",
  "record_ref": "...",
  "candidate_ref": "...",
  "reviewer_ref": "hash-or-local-id",
  "review_started_at": "ISO-8601?",
  "review_completed_at": "ISO-8601?",
  "disposition": "kept | kept_with_edits | rejected | deferred",
  "disposition_reason": "short human note",
  "manual_revision_count": 0,
  "manual_revision_kinds": ["assertion | import | mock | fixture | data | target | style | other"],
  "root_cause": {
    "family": "compile | execution | oracle | mock | asset | environment | product | platform | unknown",
    "code": "stable_code",
    "confidence": "human_confirmed | verifier_confirmed | uncertain",
    "recorded_at": "ISO-8601?",
    "evidence_refs": ["report.quality.blockers:no_assertions", "log:mvn.log"],
    "note": "short human explanation"
  },
  "fix_note": {
    "action": "short human action",
    "changed_test": true,
    "changed_production": false
  },
  "misjudgment": {
    "kind": "none | false_positive | false_negative | severity_mismatch | unclear",
    "platform_signal": "quality_gate | review_digest | asset_gate | router | mutation | other",
    "human_verdict": "short human explanation",
    "misled_human": true | false | null
  }
}
```

Rules:

- Keep notes short and evidence-linked.
- Do not persist secrets, `.env`, raw payloads, or large source excerpts in label notes.
- `changed_production=true` is a red-line review fact; it still does not authorize auto-accept.
- Missing fields mean "not reviewed yet", not "clean".

## 4. Disposition Taxonomy

| Disposition | Meaning | Counts as usable? | Required evidence |
|---|---|---:|---|
| `kept` | Human kept the candidate as-is. | yes | final human review. |
| `kept_with_edits` | Human kept it after manual edits. | yes | `manual_revision_count > 0` and edit kind. |
| `rejected` | Human decided not to keep it. | no | disposition reason or root cause. |
| `deferred` | Human could not decide because assets/spec/env were insufficient. | no, excluded or separate | asset gap / missing evidence reason. |

Rules:

- `kept` and `kept_with_edits` are the only numerator for usable test rate.
- A platform recommendation is never a disposition.
- `deferred` should not be silently merged into `rejected`; it often means Asset Gate found a real
  missing-assets problem.

## 5. Root-Cause Taxonomy

Use a two-level taxonomy: a broad `family` plus a stable `code`.

### 5.1 Families

```text
compile
execution
oracle
mock
asset
environment
product
platform
unknown
```

### 5.2 Initial Codes

| Family | Code | Typical evidence |
|---|---|---|
| `compile` | `compile_missing_symbol_or_import` | Maven compiler cannot find class/method/import. |
| `compile` | `compile_api_signature_mismatch` | wrong overload, arity, constructor, visibility. |
| `compile` | `compile_type_or_generic_mismatch` | incompatible type, generic inference, raw/null ambiguity. |
| `execution` | `execution_test_runtime_error` | generated test errors at runtime, not assertion diff. |
| `execution` | `execution_no_tests_discovered` | compiled but Surefire found no generated tests. |
| `oracle` | `oracle_expected_behavior_wrong` | expected/actual mismatch, human says test oracle is wrong. |
| `oracle` | `oracle_weak_or_missing` | no assertion, weak assertion, tautology, weak-oracle survivor. |
| `oracle` | `oracle_spec_missing_or_ambiguous` | human cannot validate because business/spec oracle is absent. |
| `mock` | `mock_misuse_or_overmocking` | mocks target, final class, loose matcher, null stub, unrealistic stub. |
| `asset` | `asset_fixture_or_test_data_missing` | fixture/test data missing or invalid. |
| `asset` | `asset_schema_or_contract_missing` | API/schema/contract absent for candidate level. |
| `asset` | `asset_business_oracle_missing` | business oracle source absent. |
| `environment` | `environment_policy_plugin_failure` | RAT/checkstyle/enforcer/license blocks run. |
| `environment` | `environment_coverage_or_instrumentation` | JaCoCo/instrumentation/coverage conflict. |
| `environment` | `environment_service_or_dependency_unavailable` | service, DB, auth, fixture, or external dependency missing. |
| `product` | `product_bug_confirmed` | human/verifier confirms candidate exposed a product defect. |
| `product` | `product_bug_suspected` | possible product bug, not confirmed. |
| `platform` | `platform_judge_bug` | judge/parser/report bug misrepresented evidence. |
| `platform` | `platform_signal_misleading` | platform guidance misled review. |
| `unknown` | `unknown_insufficient_evidence` | not enough evidence to classify. |

Rules:

- `product_bug_confirmed` requires verifier or human confirmation; `TEST_FAILURE` alone is not
  enough.
- `platform_signal_misleading` should feed misjudgment labels.
- `unknown_insufficient_evidence` is valid and preferable to fabricated RCA.

## 6. Fix Note Taxonomy

`fix_note` remains human-declared. Recommended stable actions:

```text
add_import_or_symbol_reference
adjust_api_call_or_overload
fix_type_or_generic_use
rewrite_assertion_or_expected_value
add_behavior_or_business_oracle
add_fixture_or_test_data
replace_or_remove_mock
stabilize_time_random_io
configure_service_or_dependency
mark_product_bug
mark_not_actionable
```

`fix_note.action` should be short enough to group, while `fix_note.note` may carry a concise human
explanation in a future extended shape.

## 7. Metric Mapping

| Metric from docs/56 | Fields required | Headline eligibility |
|---|---|---|
| Usable Test Rate | `disposition` | after human labels exist. |
| Human Edit Count | `manual_revision_count`, `manual_revision_kinds` | after review workflow instrumentation. |
| Human Handling Time | `review_started_at`, `review_completed_at` | after timestamps exist. |
| Diagnosis Time | judge failure time + `root_cause.recorded_at` | after RCA timestamps exist. |
| Misjudgment Rate | `misjudgment.kind`, `platform_signal`, `human_verdict` | after calibrated labels exist. |
| Defect Discovery Rate | `root_cause.code=product_bug_confirmed` plus verifier/human evidence | only on pinned defect/seeded-defect slices. |

Automated V1 metrics do not need these labels and must stay separate.

## 8. First Implementation Slice

V1 live on 2026-07-15 as the smallest non-persistent slice:

```text
app/review/human_labels.py
  validate_human_review_label(label) -> normalized dict
  label_metric_projection(label) -> compact metric facts

tests/test_human_labels.py
  valid disposition/root-cause labels
  invalid auto-accept/trusted claims rejected
  product_bug_confirmed requires confidence/evidence
  kept_with_edits requires manual_revision_count > 0
```

The slice validates and projects labels only. It rejects authority fields such as `trusted`,
`conclusion`, and `auto_accept`; validates disposition, root-cause, fix-note, misjudgment,
timestamp, and manual-edit fields; and returns compact metric facts with
`conclusion=NEED_HUMAN_REVIEW`, `trusted=False`.

No database migration was made in the first slice.

The second slice can decide whether labels are stored as:

```text
sidecar JSON next to benchmark/report artifacts
or explicit new ledger fields
or a separate human_review_labels table
```

That decision should be made only after the label contract is tested.

S6F live on 2026-07-23 as a pure readiness summary, still without persistence:

```text
app/benchmark/validation_line.py
  human_label_metric_readiness(labels_or_projections) -> metric readiness summary
```

It answers whether the supplied labels are enough to compute usable-test rate, average edit count,
human handling time, diagnosis-time readiness, misjudgment rate, and defect-discovery label
presence. It does not write labels, add a table, backfill records, alter aggregate headlines, or
turn labels into verdict/trust authority.

## 9. Relationship To Existing Ledger

Existing `JudgedRecord.root_cause` and `fix_note` may be populated from the normalized label in a
future adapter, but the adapter must preserve the distinction:

```text
derived failure_type / badcase_signature = platform evidence
root_cause / fix_note / disposition       = human or verifier label
```

Retrieval may surface both, but retrieval must not turn a prior root cause into a current fact.

## 10. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  usable_test_rate, human_edit_count, human_handling_time, diagnosis_time,
  misjudgment_rate, defect_discovery_rate
- automated evidence:
  consumes existing judge/report/ledger evidence; adds no new automated verdict
- human labels required:
  yes
- denominator:
  human-reviewed candidates for disposition/effort/time;
  RCA-labeled failures for diagnosis time;
  calibrated human/golden labels for misjudgment;
  pinned defect tasks for defect discovery
- headline eligibility:
  only after label/verifier coverage is explicit and run_kind hygiene is preserved
- red lines:
  no auto-fill, no LLM judge authority, no historical backfill, no auto-accept,
  no schema/index change in the first implementation slice
```

## 11. Definition Of Done

S5C design is complete if future implementation can answer:

- what a human may label;
- what the platform may suggest but not assert;
- which stable root-cause codes exist;
- how `usable_test_rate`, edit count, handling time, diagnosis time, misjudgment rate, and defect
  discovery rate become measurable;
- why no current report/recommendation/conclusion/trusted behavior changes;
- how the first implementation can be pure validation before persistence.
