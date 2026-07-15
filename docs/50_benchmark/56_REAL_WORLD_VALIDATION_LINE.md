# 56 - Real-World Validation Line

> Date: 2026-07-11  
> Status: active design reference. V1 automated evidence projection is live; no schema change,
> ledger change, UI change, model run, external dataset import, human-label workflow, or API
> executor is implied.

## 0. Purpose

This project needs a real landing validation line early, before the implementation grows around
easy but weak metrics.

The strongest final claim should not be:

```text
the platform generated many tests
```

It should be:

```text
the platform measures which test candidates are executable, reviewable, defect-revealing,
human-usable, and non-misleading under reproducible evidence.
```

These metrics are design targets for benchmark, ledger, report, and future human-review workflows.
They are not all live today.

## 1. Evidence Rule

Every metric must declare:

- denominator;
- numerator;
- evidence source;
- whether human labels are required;
- whether it is live, future-instrumented, or future-calibrated;
- whether it may appear in headline reporting.

Do not compute a metric from vibes, model self-report, producer identity, coverage alone, or
green execution alone.

Default headline rules:

- automated judge metrics may be shown once evidence is collected and `run_kind` hygiene is
  respected;
- human-outcome metrics require explicit human labels;
- defect metrics require real-bug or seeded-defect manifests;
- misjudgment metrics require a stable human/golden reference;
- fake/dryrun/smoke/external/historical unknown rows must not pollute real-model headlines.

## 2. Metric Set

| Metric | Meaning | Evidence source | Current status | Headline rule |
|---|---|---|---|---|
| First Compile Pass Rate | Candidate compiles on first judged execution. | `generation.execution.gen_outcome` before repair; compiled if `PASS`, `TEST_FAILURE`, or `NO_TESTS`. | Partly live for current runs; must preserve first-run evidence if repair is enabled. | Allowed for real-only automated headline. |
| First Test Pass Rate | Candidate executes and its own tests pass on first judged execution. | `gen_outcome == "PASS"` before repair. | Partly live for current runs; must not include repaired final outcome as first-pass. | Allowed for real-only automated headline, with caveat that green is not value. |
| Usable Test Rate | Human ultimately keeps the candidate, with or without edits. | Human review disposition: `kept`, `kept_with_edits`, `rejected`, `deferred`. | Not live; requires review ledger fields. | Headline only after human labels exist. |
| Weak Assertion Detection Rate | Platform catches fake-green / weak-oracle candidates. | Quality Gate, oracle-strength, mutation when gated, plus human/golden weak labels. | Structural detection live; true detection rate needs labeled set. | Do not headline recall/precision until labels exist. |
| Defect Discovery Rate | Candidate exposes a real or injected defect. | Confirmed real-bug manifest, seeded-defect manifest, mutation/golden verifier, or human-confirmed bug. | Not live as a trustworthy metric. | Headline only on pinned real-bug/seeded-defect benchmark slice. |
| Human Edit Count | Number of human edit rounds needed from candidate to usable test. | Human review workflow or PR/edit annotation. | Not live. | Headline only after review workflow instrumentation. |
| Human Handling Time | Human review + fix time. | Human timestamps, not model/job runtime. | Not live. | Headline only after timestamped human workflow exists. |
| Diagnosis Time | Time from failure evidence to identified root cause. | Failure surfaced timestamp + human/root-cause recorded timestamp. | Not live. | Headline only after RCA workflow exists. |
| Misjudgment Rate | Platform guidance misleads or misses important human findings. | Human/golden labels compared with platform recommendation, digest flags, and quality signals. | Not live. | Headline only after calibrated labeled set exists. |

## 3. Precise Definitions

### 3.1 First Compile Pass Rate

```text
denominator = candidates with first execution evidence
numerator   = first_run.gen_outcome in {PASS, TEST_FAILURE, NO_TESTS}
```

Rules:

- compile repair must not be counted as first compile pass;
- preflight reject should be counted separately, not hidden;
- Maven/Surefire remains the verifier;
- current historical rows may be computed only if first-run evidence is unambiguous.

### 3.2 First Test Pass Rate

```text
denominator = candidates with first execution evidence
numerator   = first_run.gen_outcome == PASS
```

Rules:

- test pass is not test value;
- include `run_kind` split;
- keep `TEST_FAILURE` distinct because it may be a true defect or a bad oracle and requires human
  review.

### 3.3 Usable Test Rate

```text
denominator = human-reviewed candidates
numerator   = human_disposition in {kept, kept_with_edits}
```

Required future fields:

```text
human_disposition: kept | kept_with_edits | rejected | deferred
human_disposition_reason:
reviewer_id_hash?:
review_completed_at:
```

Rules:

- platform must never fill this field automatically;
- `STRONG_REVIEW_CANDIDATE` is not "usable";
- a candidate can be usable only after human review or golden verifier confirmation.

### 3.4 Weak Assertion Detection Rate

Two levels:

```text
structural_weak_signal_rate =
  candidates with weak assertion / no assertion / tautology / weak oracle signals
  divided by judged candidates

audited_weak_detection_rate =
  human-or-golden weak candidates caught by platform
  divided by all human-or-golden weak candidates
```

Live signal examples:

```text
quality_gate.blocking_issues:
  no_assertions
  weak_assertions_only
  tautological_assertion
quality_gate.warnings:
  weak_assertion_heavy
review_summary.oracle_strength_estimate
review_summary.mutation_survivors when mutation is gated on
```

Rules:

- structural signal rate is not recall;
- recall/precision require a labeled weak-test set;
- false positives must feed Misjudgment Rate.

### 3.5 Defect Discovery Rate

```text
denominator = candidates on pinned defect-bearing tasks
numerator   = candidates that reveal the target defect under verifier or human confirmation
```

Allowed evidence:

- pinned real-bug benchmark slice such as future Defects4J/GitBug manifest seed;
- seeded defect/mutation task with known expected failure;
- human-confirmed true product defect, linked to root-cause evidence.

Rejected evidence:

- `TEST_FAILURE` alone;
- coverage increase;
- schema conformance;
- model claim that a bug was found.

### 3.6 Human Edit Count

```text
denominator = human-reviewed candidates that reach a final disposition
metric      = number of human edit rounds before final disposition
```

Future minimum fields:

```text
manual_revision_count:
manual_revision_kind: assertion | import | mock | fixture | data | target | style | other
```

Rules:

- machine compile repair is not a human edit;
- count review/fix rounds, not individual keystrokes;
- allow `0` for kept-as-is.

### 3.7 Human Handling Time

```text
handling_time = review_completed_at - review_started_at
```

Rules:

- this is human time, not job runtime;
- paused/deferred review should be either excluded or separately labeled;
- do not infer from Git commit timestamps unless the review workflow defines it.

### 3.8 Diagnosis Time

```text
diagnosis_time = root_cause_recorded_at - failure_first_surfaced_at
```

Future RCA fields:

```text
failure_first_surfaced_at:
root_cause_recorded_at:
root_cause: compile_symbol | mock_misuse | fixture_missing | weak_oracle | product_bug | ...
root_cause_confidence: human_confirmed | verifier_confirmed | uncertain
```

Rules:

- root cause must be human-declared or verifier-confirmed;
- platform may suggest but must not fabricate RCA;
- report digest should help reduce this time, but cannot claim success without timestamps.

### 3.9 Misjudgment Rate

Misjudgment has two directions:

```text
false_positive_guidance =
  platform flags/recommendations that human/golden reference says were misleading

false_negative_guidance =
  important human/golden findings missed by platform
```

Recommended future labels:

```text
platform_signal:
human_verdict:
misjudgment_kind: false_positive | false_negative | severity_mismatch | unclear
misled_human: true | false | unknown
```

Rules:

- this is the key trustworthiness metric for the judge itself;
- do not compute it without a stable human/golden reference;
- report it separately from candidate quality metrics.

## 4. Implementation Order

Do not implement all metrics at once.

Recommended sequence:

```text
V1 automated evidence line:
  First Compile Pass Rate
  First Test Pass Rate
  structural weak-signal rate
  run_kind-filtered reporting

V2 human review line:
  human_disposition
  usable test rate
  human edit count
  human handling time

V3 RCA and defect line:
  root_cause fields
  diagnosis time
  pinned defect / seeded defect manifest
  defect discovery rate

V4 judge calibration line:
  misjudgment labels
  precision/recall for weak assertion and platform guidance
```

This order preserves the current judge-first product while making the final validation story more
convincing.

### 4.1 V1 Automated Evidence Line - Live

Implemented on 2026-07-12:

```text
app/benchmark/validation_line.py
  validation_line_summary(...)

app/benchmark/report_md.py
  Real-world validation line - RAW (all run_kinds)
  Real-world validation line - HEADLINE (real only)

tests/test_validation_line.py
tests/test_benchmark.py
```

Live V1 metrics:

- first compile pass rate;
- first test pass rate;
- structural weak-signal rate;
- preflight reject count;
- first-run ambiguity count for rows where repair rounds make first-run evidence unsafe to claim;
- explicit unavailable markers for human/golden metrics.

V1 did not change:

- `aggregate(...)` keys;
- benchmark or ledger schemas;
- SQLite indexes;
- recommendations, conclusions, trust, or digest severity;
- human/golden metrics, which still require labels or verifiers.

## 5. Mapping To Current Project

Current live or near-live:

- compile and pass facts from `assemble_generation_report(...)` / `JudgeEvidence`;
- quality-gate weak assertion signals;
- oracle-strength structural estimate;
- gated mutation evidence when explicitly enabled;
- run_kind-filtered benchmark/ledger aggregates.

Needs future design:

- human review disposition;
- human edit rounds;
- human review timestamps;
- RCA timestamps and root-cause labels;
- pinned defect benchmark manifest;
- misjudgment labels and calibration reports.

Human review disposition, edit rounds, review timestamps, RCA labels, and misjudgment labels are
specified in `docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`.

Do not add new SQLite indexes, benchmark schema, or ledger fields until a bounded implementation
slice is approved.

## 6. External Asset Mapping

External assets may support the validation line only through the mapping matrix:

| Asset type | Intake shape | Metric support | Red line |
|---|---|---|---|
| Defects4J / GitBug-Java | `readme_audit` + future `manifest_seed` / `dataset_slice` | Defect Discovery Rate | no bulk import; pin 3-5 seeds only after design |
| TestExplora / TestBench | `readme_audit` + `knowledge_note` | benchmark design vocabulary, possible manifest seed | no direct leaderboard copying |
| EvoSuite / Randoop / external agents | `producer_adapter` | compare producers via same judge | producer identity is never quality proof |
| Schemathesis / Newman | `executor_adapter` | future API smoke compile/pass/evidence equivalent | no install/run before S7 approval |
| Inspect AI / SWE-bench style harnesses | `knowledge_note` | task/scorer/verifier governance patterns | no generic harness platform |

## 7. Definition Of Done For Future Designs

Any future design that changes benchmark, report, ledger, review workflow, or API candidate work
must state which of the validation-line metrics it strengthens and how the metric will be
measured.

Required block:

```text
Real-World Validation Impact:
- metrics strengthened:
- automated evidence:
- human labels required:
- denominator:
- headline eligibility:
- red lines:
```

If a design cannot fill this block, it should not claim landing-value improvement.
