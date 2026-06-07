# Context v3.2.2 BooleanUtils Review

> Date: 2026-06-07. Scope: one live `deepseek-v4-pro` BooleanUtils validation
> after the v3.2.2 bare-null overload prompt guardrail. No Phase 3 repair, no
> oracle auto-fix, no preflight extension, no coverage restoration.

## 1. Purpose

`v3.2.2` added a prompt-only rule for a recurring compile bucket:

- `BooleanUtils.toBoolean(null)` ambiguous between `toBoolean(Boolean)` and
  `toBoolean(String)`;
- `BooleanUtils.toBooleanObject(null)` ambiguous between
  `toBooleanObject(Integer)` and `toBooleanObject(String)`;
- `NumberUtils.toDouble(null, ...)` ambiguous between reference-type overloads.

The rule says: when same-arity overloads differ by reference parameter type,
cast `null` to the evidenced type or skip the case.

This review checks whether that rule is enough to proceed to the full 10-case
pro benchmark.

## 2. Run

Report:

- `var/benchmark/v3_2_2-pro-booleanutils/report.json`
- `var/benchmark/v3_2_2-pro-booleanutils/bench.db`

Configuration:

- model: `deepseek-v4-pro`
- target: `org.apache.commons.lang3.BooleanUtils`
- commit: `598dfc163b8b410fb3bb8794521206ec8dcec82a`
- repo source: existing local pinned mirror
- repair: disabled
- coverage: unavailable / JaCoCo skipped
- preflight: enabled

Aggregate:

| metric | value |
|---|---:|
| buildable repos | 1 |
| generation attempted | 1 |
| preflight status | `PASS` |
| target-class calls checked | 145 |
| generated outcome | `COMPILE_FAILURE` |
| quality gate | `FAIL` |
| review recommendation | `REJECT_CANDIDATE` |
| conclusion | `NEED_HUMAN_REVIEW` |

## 3. What Improved

The previous live run failed on bare-null reference overloads:

```java
BooleanUtils.toBoolean(null);
BooleanUtils.toBooleanObject(null);
```

The v3.2.2 run no longer emitted those forms. The generated source used casts
for single-argument reference overloads:

```java
BooleanUtils.toBoolean((Boolean) null);
BooleanUtils.toBoolean((String) null);
BooleanUtils.toBooleanObject((Integer) null);
BooleanUtils.toBooleanObject((String) null);
```

The model also explicitly skipped several uncertain null cases in
`omitted_uncertain_cases`, including:

- `toBoolean(String, String, String) with null trueString/falseString`;
- `toBoolean(Integer, Integer, Integer) with null parameters`.

So the v3.2.2 rule changed model behavior in the intended direction.

## 4. New Compile Failure

Maven failed on a different same-arity overload ambiguity:

```text
BooleanUtilsAiGeneratedTest.java:[104,72] reference to toBoolean is ambiguous
  both toBoolean(int,int,int) and toBoolean(Integer,Integer,Integer) match
```

Generated source:

```java
assertThrows(
    IllegalArgumentException.class,
    () -> BooleanUtils.toBoolean(Integer.valueOf(3), 1, 2)
);
```

Root cause:

- the target has same-arity primitive and boxed overloads;
- the generated call mixes a boxed argument (`Integer.valueOf(3)`) with primitive
  literals (`1`, `2`);
- Java can match both overloads through boxing/unboxing conversion, so the call
  is ambiguous.

This is not the old bare-null bucket. It is a broader overload type-consistency
bucket:

> For same-arity primitive/boxed overload families, a call must use one coherent
> argument type family. Do not mix boxed and primitive arguments.

## 5. Preflight Finding

Preflight returned `PASS`:

```json
{
  "checked": true,
  "status": "PASS",
  "blocking_issues": [],
  "metrics": {
    "target_class_calls": 145
  }
}
```

This is expected under the current preflight contract. The gate checks direct
target-class method existence, arity, and the known primitive/boxed varargs
case. It does not type-check non-varargs overload resolution.

There is still no over-reject evidence.

## 6. Judgment

Do **not** proceed to the formal 10-case pro benchmark yet.

Reason:

- v3.2.2 fixed the previous bare-null symptom;
- but BooleanUtils still exposes a recurring overload-resolution family;
- a 10-case run would likely spend pro calls discovering the same Java overload
  class of failures in a noisier setting.

Also do **not** start Phase 3 repair. This is still a generation-time compile
avoidance problem, not an oracle-repair problem.

## 7. Recommended Next Step

Add one more prompt-only guardrail, `v3.2.3`, then rerun the same single-case
BooleanUtils validation.

Suggested rule:

> For same-name, same-arity primitive/boxed overload families, never mix boxed
> and primitive arguments in one call. Use all primitive literals for primitive
> overloads, or all boxed values for boxed overloads. If the intended overload is
> not evidenced, skip into `omitted_uncertain_cases`.

Example safe forms:

```java
BooleanUtils.toBoolean(3, 1, 2); // all primitive
BooleanUtils.toBoolean(Integer.valueOf(3), Integer.valueOf(1), Integer.valueOf(2)); // all boxed
```

Unsafe form:

```java
BooleanUtils.toBoolean(Integer.valueOf(3), 1, 2); // ambiguous
```

Boundary:

- prompt/test only;
- no pipeline changes;
- no repair;
- no preflight extension yet;
- no expected-to-actual rewrite;
- no 10-case run before the single-case result is known.
