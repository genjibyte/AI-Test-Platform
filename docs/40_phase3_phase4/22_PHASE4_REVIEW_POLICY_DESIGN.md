# Phase 4 — Review Policy

> Date: 2026-06-06。性质：**策略定义与实现记录**；2026-06-07 已落地最小实现，见 §9。
> 上级：`docs/00`、`docs/07`、`docs/19`、`docs/20`、`docs/21`。
> 边界（用户指令）：**进入 Phase 4 review policy；不要扩 Phase 3 oracle fixer。**

---

## 0. 目标与定位

Phase 2.6 用真实数据确认（`docs/21`，`var/benchmark/v2-pro-quality-final`）：pro 模型下**编译已解决（100%）、结构质量已解决（0 FAIL），剩余唯一瓶颈是 oracle/API 行为正确性**（2/3 `TEST_FAILURE`）。

Phase 4 不解决 oracle 正确性（那需要规格/人判），而是把现有事实**组织成可供人快速判定的"评审建议 + 评审摘要"**，并把"什么能/不能采纳"的**策略显式化**。一句话：

> Phase 4 = 在确定性质量门之上加一层**面向 reviewer 的、建议性的、永不自动采纳**的决策与摘要层。

---

## 1. 红线（每条都来自 docs/00/07 与本项目结论）

1. ❌ **永不自动采纳**：最终 `conclusion` 恒为 `NEED_HUMAN_REVIEW`，`trusted` 恒 `False`。Phase 4 产出的是**建议（recommendation）**，不是判决。
2. ❌ **不自动修 oracle**：不把 `expected` 改成 `actual`、不删断言到只剩 smoke、不扩 Phase 3 进 oracle 修复（`docs/07` A5）。
3. ❌ **`TEST_FAILURE` 默认 review-only、不可采纳**：编译+运行但断言失败，必须人判"是测试错还是发现 bug"。
4. ❌ **不让 LLM/门当验证者**（`docs/07` A2）：recommendation 是**确定性规则**，不调用模型。
5. ❌ 不改生产代码/pom/既有测试；不动覆盖率策略（仍按 `docs/14` 关 JaCoCo，覆盖率为 advisory 输入）。
6. ✅ `risk_flags` 保持 advisory（`docs/21`）；门禁 `PASS` ≠ 采纳。

---

## 2. 评审建议（review recommendation）—— 确定性、建议性

新增一个**建议**字段（与 `conclusion` 解耦；`conclusion` 永远 `NEED_HUMAN_REVIEW`）：

`review_recommendation ∈ { REJECT_CANDIDATE, NEEDS_REVISION, REVIEW_CANDIDATE, STRONG_REVIEW_CANDIDATE }`

**确定性规则（输入全部已存在于 generation report）**：

| 条件（按优先级自上而下） | recommendation | 理由 |
|---|---|---|
| `production_code_touched` 为真 | `REJECT_CANDIDATE` | 越过红线（应不可能，作守卫） |
| 质量门 `status == FAIL`（含 not_executed / 弱断言 only / 同义反复 / 不稳定 / 反射 / 覆盖率下降） | `REJECT_CANDIDATE` | 有结构性阻断缺陷，不值得人 review |
| `gen_outcome == TEST_FAILURE` | `NEEDS_REVISION` | 编译+运行但断言失败：交人判 oracle vs bug，**默认不可采纳** |
| 质量门 `status == REVIEW`（有 warning，如 weak_assertion_heavy / no_obvious_target_reference） | `REVIEW_CANDIDATE` | 可 review，但有需关注的弱点 |
| 质量门 `status == PASS` 且 `passed == True` | `STRONG_REVIEW_CANDIDATE` | 编译+通过+无结构缺陷+oracle 有据；**最强候选，但仍需人审** |

> 注意：`STRONG_REVIEW_CANDIDATE` ≠ accept。它是"优先 review、最可能可用"的排序信号。`advisories`（如 `model_declared_risk`）**不降级** recommendation，但**附在摘要里**给 reviewer。

不确定/缺数据时一律向**更保守**靠（缺 `passed` → 不得 STRONG）。

---

## 3. 面向 reviewer 的评审摘要（review summary）

把分散事实拼成一个**可直接行动**的结构（全部来自现有数据，零新计算来源）：

```text
review_summary = {
  recommendation,                 # §2
  conclusion: "NEED_HUMAN_REVIEW",# 恒定
  target,                         # class#method
  outcome,                        # gen_outcome (PASS/TEST_FAILURE/...)
  quality: { status, blockers[], warnings[], advisories[] },  # 来自 quality_gate
  failures: [                     # 仅"生成测试自身"的失败（按 classname 过滤 suite_result.failed_cases）
    { test_name, type,            # failure(assert) | error(exception)
      expected, actual,           # 从 message "expected: <X> but was: <Y>" 解析；解析不出则置 null + 保留 raw
      raw_message }
  ],
  grounding: { behavior_sources[], omitted_uncertain_cases[], risk_flags[], dependency_assumptions[] },
  patch_preview: { file_path, is_new_file, content },
  invariants: { trusted: false, production_code_touched: false }
}
```

**expected/actual 解析**（确定性、最小）：对 JUnit5 `AssertionFailedError` 的 `message`（形如 `expected: <foo BAR> but was: <foo bAR>`）用正则提取 `expected`/`actual`；对 `error`（异常，如 `UnsupportedOperationException`）置 `expected=null`、`actual=<异常类型/消息>`，并保留 `raw_message`。**解析失败不报错**，回退到 `raw_message`。

> 这正好命中 `docs/21` 的两个真实失败：Option 的 `addValue → UnsupportedOperationException`（error 类）、CSVRecord 的异常类型猜错（error 类），以及 WordUtils 那类 `expected/actual` 不符（failure 类）。

---

## 4. 在哪里呈现

- **生成报告**：`assemble_generation_report` 增 `review_recommendation` 与 `review_summary` 两个字段（**纯增量**，不改既有键、不改 `conclusion`）。
- **benchmark**：`BenchCaseResult` 增 `review_recommendation`；`aggregate()` 增 `recommendation_distribution`（各档计数）。`report_md` 增一列。
- **不新增 API、UI**（Charter §10 的前端留后；先把 API 产出做对）。

---

## 5. 最小实现方案（供下一步实现，本文不实现）

| 文件 | 改动 | 不做 |
|---|---|---|
| 新增 `app/review/review_policy.py` | `recommend(facts) -> str`（§2 规则）+ `build_review_summary(generation, suite_result, fqcn) -> dict`（§3，含 expected/actual 解析） | 不调模型、不改测试源码 |
| 改 `app/report/generation_report.py` | 调 `review_policy`，加 `review_recommendation` + `review_summary` 两个键 | 不改 `conclusion`/`trusted`/既有键 |
| 改 `app/benchmark/{models,runner,report_md}.py` | `BenchCaseResult.review_recommendation` + 聚合分布 + 报告列 | 不改判卷/生成逻辑 |
| 新增 `tests/test_review_policy.py` | 覆盖 §2 每条规则 + §3 expected/actual 解析（含 error/exception 分支）+ 保守回退 | — |
| 改 `tests/test_generation_report.py`、`tests/test_benchmark.py` | 断言新字段存在、`conclusion` 不变 | — |

**风险**：低。纯增量字段 + 确定性规则；唯一易错点是 expected/actual 正则的鲁棒性（用"解析不出就回退 raw"兜底）。规则参数（如 STRONG 的条件）后续可调，不影响红线。

---

## 6. 验证计划（零模型成本优先）

1. 单元测试覆盖规则与解析（离线）。
2. 用**既有** `bench.db`（`v2-pro-quality-final`、`v2-pro-repair`）**重评**，产出 recommendation 分布与 review_summary，核对：
   - Option/CSVRecord → `NEEDS_REVISION`，且 summary 正确抽出 `UnsupportedOperationException`/异常类型；
   - WordUtils(pro-quality-final) → `STRONG_REVIEW_CANDIDATE`。
   （复现方式同 `docs/20` §6，零成本。）
3. **不跑新模型**，除非你确认要更大样本。

---

## 7. Phase 4 边界（明确不做）

- 不做"自动采纳/拒收"的最终判决（只给建议；人是最终门）。
- 不做 oracle 自动修复 / 不扩 Phase 3。
- 不做覆盖率门禁恢复（覆盖率仅作 advisory 输入；待 compile/quality 稳定且选无 JaCoCo 冲突仓库后另议）。
- 不做前端/CI 集成（Charter §8）。
- 不做多模型自动对照/共识（重型，留后）。

---

## 8. 开放问题（实现前可拍板，不阻塞设计）

1. recommendation 档名用 `REJECT_CANDIDATE/NEEDS_REVISION/REVIEW_CANDIDATE/STRONG_REVIEW_CANDIDATE` 还是更短的 `REJECT/REVISE/REVIEW/STRONG`？（建议前者，语义更显"建议非判决"）
2. `advisories`（model_declared_risk）是否在 `STRONG` 档里降一级为 `REVIEW`？**建议否**（保持 advisory 不降级，`docs/21` 一致），只在 summary 显示。
3. 覆盖率 available 时，`coverage_dropped` 已是质量门 FAIL 项；`target_improved` 是否进 recommendation？**建议否**（覆盖率本期关闭，先不纳入），仅记录。

---

> 结论：Phase 4 第一步是**把策略和摘要定清楚**（本文）。它在现有确定性事实上加一层**建议性、永不自动采纳**的 reviewer 决策层，直接命中 `docs/21` 暴露的 oracle 失败，且不触碰 Phase 3 oracle 修复红线。

---

## 9. 实现状态（已落地，2026-06-07）

按 §5 最小方案实现，**零新模型调用、零生产逻辑改动、纯增量字段**：

- 新增 `app/review/review_policy.py`：`recommend(...)`（§2 规则）+ `build_review_summary(...)`（§3，含 expected/actual 解析）。
- `app/report/generation_report.py`：增 `review_recommendation` + `review_summary` 两键，**未改** `conclusion`/`trusted`/既有键。
- `app/benchmark/{models,runner,report_md}.py`：`BenchCaseResult.review_recommendation` + 聚合 `recommendation_distribution` + 报告列。
- 新增 `tests/test_review_policy.py`（规则 6 条 + 摘要解析 failure/error 两分支 + 不变量）。
- **无需改** `surefire_parser`/`FailedCase`：真实 message 已含所需信息（failure 的 `expected:<>but was:<>`；error 的异常详情）。

**测试**：全量 `158 passed, 4 skipped`。

**真实数据验证（零成本，重评 `var/benchmark/v2-pro-quality-final/bench.db`）**：
| case | outcome | quality | recommendation | summary 抽取 |
|---|---|---|---|---|
| WordUtils | PASS | PASS | `STRONG_REVIEW_CANDIDATE` | — |
| CSVRecord | TEST_FAILURE | REVIEW | `NEEDS_REVISION` | `expected=IllegalArgumentException actual=ArrayIndexOutOfBoundsException` |
| Option | TEST_FAILURE | REVIEW | `NEEDS_REVISION` | `actual='The addValue method is not intended for client use...'` |

`recommendation_distribution = {NEEDS_REVISION: 2, STRONG_REVIEW_CANDIDATE: 1}`；三例 `conclusion` 均 `NEED_HUMAN_REVIEW`、`trusted=False`（不变量保持）。

> 落地效果（对齐大厂痛点）：reviewer 现在每个生成测试都能直接看到**为什么失败**（异常类型猜错 / 内部 API 误用）与**建议处置**，而平台**不自动采纳、不自动改 oracle**——判卷优先、人是最终门。
