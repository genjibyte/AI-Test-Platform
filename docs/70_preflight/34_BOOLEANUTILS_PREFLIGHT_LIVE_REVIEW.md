# BooleanUtils Preflight Live Review

> Date: 2026-06-07. Scope: one live `deepseek-v4-pro` BooleanUtils validation.
> No Phase 3 repair, no oracle auto-fix, no coverage restoration, no pipeline
> change.

## 1. Purpose

This run follows `/docs/70_preflight/33_PREFLIGHT_OFFLINE_REPLAY_AUDIT.md`:

1. run exactly one live `BooleanUtils` pro case with the preflight gate enabled;
2. verify whether preflight either rejects a repeated API-list violation or
   cleanly allows Maven to judge the generated test;
3. do not start the 10-case benchmark until this single-case behavior is known.

## 2. Inputs

Target:

- repo: Apache Commons Lang
- target class: `org.apache.commons.lang3.BooleanUtils`
- commit: `598dfc163b8b410fb3bb8794521206ec8dcec82a`
- model: `deepseek-v4-pro`
- repair: disabled
- Maven extra args: policy/style/audit plugins skipped; JaCoCo skipped

Network note:

- first attempt used `https://github.com/apache/commons-lang.git`;
- it failed before model/generation with `REPO_CLONE_FAILED` because GitHub port
  443 was unreachable;
- the live validation was rerun from the existing local pinned mirror at the
  same commit.

Report files:

- `var/benchmark/v3_2_1-pro-booleanutils-preflight-live/report.json`
- `var/benchmark/v3_2_1-pro-booleanutils-preflight-live-localmirror/report.json`

Only the local-mirror run is the meaningful live validation.

## 3. Result

Live local-mirror run:

| metric | value |
|---|---:|
| buildable repos | 1 |
| generation attempted | 1 |
| model | `deepseek-v4-pro` |
| preflight status | `PASS` |
| target-class calls checked | 85 |
| generated outcome | `COMPILE_FAILURE` |
| quality gate | `FAIL` |
| review recommendation | `REJECT_CANDIDATE` |
| conclusion | `NEED_HUMAN_REVIEW` |

Preflight detail:

```json
{
  "checked": true,
  "status": "PASS",
  "blocking_issues": [],
  "metrics": {
    "target_class_calls": 85
  }
}
```

Interpretation:

- the model did **not** repeat the previously observed unlisted
  `toBooleanObject(int,int,int)` hallucination;
- the model did **not** emit individual-value primitive/boxed varargs calls such
  as `BooleanUtils.and(true, true)`;
- therefore preflight correctly deferred to Maven instead of blocking.

This validates the non-reject path of the gate.

## 4. Maven Failure Root Cause

Maven then failed compilation with two ambiguous `null` overload calls:

```text
BooleanUtilsAiGeneratedTest.java:[211,33] reference to toBoolean is ambiguous
  both toBoolean(Boolean) and toBoolean(String) match

BooleanUtilsAiGeneratedTest.java:[231,32] reference to toBooleanObject is ambiguous
  both toBooleanObject(Integer) and toBooleanObject(String) match
```

Generated source excerpts:

```java
assertFalse(BooleanUtils.toBoolean(null));
assertNull(BooleanUtils.toBooleanObject(null));
```

This is not the API-list failure that preflight currently targets. It is a
Java overload-resolution failure caused by an untyped `null` literal.

## 5. Relation To Offline Replay

This live failure matches a boundary already observed in
`/docs/70_preflight/33_PREFLIGHT_OFFLINE_REPLAY_AUDIT.md`:

- offline replay found a `NumberUtils.toDouble(null, ...)` Maven compile
  failure that preflight passed;
- the reason was also `null` overload ambiguity;
- the current live run reproduces the same failure shape on `BooleanUtils`.

So this is a real recurring bucket:

> untyped null literal passed to overloaded target methods with same arity and
> multiple nullable reference parameter types.

## 6. Finding

The preflight gate behaved correctly under its current contract:

- no over-reject occurred;
- Maven ran normally after preflight `PASS`;
- the remaining compile failure is outside the current narrow API-list/varargs
  gate.

This run does **not** justify Phase 3 repair or oracle repair.

It does suggest a possible next minimal deterministic/prompt boundary:

- prompt/context rule: when calling overloaded methods with nullable reference
  parameters, cast `null` to the intended type or skip the case;
- deterministic preflight extension, later and optional: detect untyped `null`
  calls against overloaded same-arity target methods and flag as a compile-risk.

Do not implement that extension before the 10-case run unless the next review
decides the null-overload bucket is common enough to justify it.

## 7. Recommendation

Proceed to the full 10-case pro quality benchmark only after GitHub/network
access is stable or the manifest is explicitly rewritten to use existing local
mirrors for this machine.

For the 10-case run, keep the same boundaries:

- no Phase 3 repair;
- no oracle auto-fix;
- no coverage restoration;
- preflight enabled;
- repair disabled;
- review conclusion remains `NEED_HUMAN_REVIEW`.

Expected analysis focus after the 10-case run:

1. how often preflight rejects deterministic API-list failures;
2. how often Maven still catches boundary-outside compile failures;
3. whether `null` overload ambiguity deserves a narrow v3.2.2 prompt/preflight
   rule;
4. whether the gate shows any over-reject evidence.
