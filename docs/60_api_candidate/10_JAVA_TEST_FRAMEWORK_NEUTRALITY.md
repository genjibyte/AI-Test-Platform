# Java Test Framework Neutrality

> Date: 2026-07-23
> Status: S6D/S6D2 live V1 design note. Report-only Java framework facts plus optional
> `submit_candidate` declaration carry; no runner, dependency, candidate-kind migration,
> POM mutation, digest signal, verdict change, or trusted-status change.

## 0. Why

The current Java/Maven kernel grew from JUnit examples, and the API smoke path uses the historical
`junit_api_candidate` compatibility name. That should stay thin. Enterprise Java candidates may
arrive as TestNG as well as JUnit, and the judge should not make reviewers infer framework support
from old candidate names.

The built-in JUnit generator is not a framework strategy. It was an early failed exploration that
remains in the tree because deleting it would be noisy. Treat it as a removable producer feeding
the harness, not as the direction for Java framework support.

The near-term move is framework visibility, not framework migration:

```text
candidate source/declaration
  -> report-only java_test_framework facts
  -> human review context
  -> existing Maven/Surefire/JaCoCo evidence path remains unchanged
```

## 1. Live Contract

`app.report.java_test_framework.detect_java_test_framework(...)` returns compact facts under:

```text
review_summary["java_test_framework"]
```

Current frameworks:

| Framework | Meaning |
|---|---|
| `junit4` | Existing Maven/Surefire-compatible Java test framework. |
| `junit5` | Existing Maven/Surefire-compatible Java test framework. |
| `testng` | Recognized enterprise Java framework, report-only for now. |
| `mixed` | Declared/detected framework conflict or multiple frameworks; human review required. |
| `unknown` | No stable framework marker found. |

The facts include:

```text
framework
declared_framework
detected_frameworks
declared_matches_detected
runner_family = maven_surefire_jacoco
support_status
thin_junit_posture = true
testng_enterprise_path_visible
owner_gate_required_before
runtime/verdict/trust authority flags = false
```

S6D2 adds optional public submit carry:

```text
SubmitCandidateRequest.java_test_framework?: "junit4" | "junit5" | "testng" | "unknown"
  -> normalized bundle["java_test_framework"]
  -> report-only review_summary["java_test_framework"]
```

Aliases such as `test-ng` and `junit_5` may normalize to the canonical values. Unsupported
framework names are rejected at the submit boundary before job lookup.

## 2. Boundary

Allowed now:

- detect JUnit/TestNG markers in submitted/generated Java test source;
- accept an explicit `java_test_framework` declaration in the generation bundle or
  `submit_candidate` request;
- surface framework facts for review;
- keep `junit_unit_candidate` and `junit_api_candidate` as compatibility names for existing paths.

Not allowed without owner-gated design:

- rename existing candidate kinds;
- install TestNG or mutate `pom.xml`;
- add a framework-specific generator prompt race;
- switch the runner away from Maven/Surefire/JaCoCo;
- add digest severity, benchmark headline, ledger scoring, recommendation, conclusion, or
  `trusted=True` behavior from framework choice.

## 3. Next Possible Slices

1. Add benchmark/ledger compact carry only if reviewers need framework distribution evidence.
2. Design a future TestNG-specific candidate kind only after compatibility naming becomes a real
   blocker.

Each slice should reuse the existing judge path and prove no verdict/trust drift.
