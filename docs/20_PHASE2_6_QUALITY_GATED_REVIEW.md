# Phase 2.6 — Quality-Gated Real-Repo Mini-Benchmark（验证，不堆功能）

> 日期：2026-06-06。性质：**验证**，非新功能。
> 上级：`docs/00`、`docs/07`、`docs/16`、`docs/17`、`docs/18`、`docs/19`。
> 问题：现在生成的测试，在真实仓库里，除了“能编译、能跑”，**是否能成为值得人 review 的测试资产**？

---

## 0. 一句话结论

**基本能。** 在最好配置（v2 prompt + 编译修复 + `deepseek-v4-pro`）下，真实仓库生成的测试**编译 100%、运行通过 67%、且每个可执行测试都过了确定性质量门（0 个 FAIL、3 个 REVIEW、0 个 PASS）**：没有弱断言堆砌、没有同义反复、没有不稳定/反射、没有触碰生产码；oracle 有证据支撑、不确定的 case 被**主动跳过**而非硬猜、风险被模型**自报**。它们是**值得人 review 的候选资产**，但**没有一个可自动采纳**——这正是 `docs/07` P6 期望的保守姿态。

> 关键转变：Phase 2.5 的 WordUtils 是“猜 16 个错”，v2+repair 的 WordUtils 是“跳过 13 个不确定、通过 7 个”。质量提升来自**少而有据**，不是更全。

---

## 1. 方法（零模型成本）

质量门（`app/quality/test_quality_gate.py`）与 benchmark 接线（`app/benchmark/{models,runner}.py`）**已实现且通过测试**（`docs/19`；本次全量 **145 passed, 4 skipped**），runner 的 `_completed_result` 已填 `quality_gate_status/blockers/warnings`（`app/benchmark/runner.py:162-164`）。但既有 v2 跑批早于质量门，其 `report.json` 不含质量字段。

因此本次**不跑新模型**，而是对既有跑批的 `bench.db`（持久化了完整 generation bundle：测试源码 + grounding 元数据 + 执行事实）**重新过质量门**（`assemble_generation_report` 现含 gate），得到忠实的质量化视图。复现命令见 §6。

证据目录：`var/benchmark/v2-pro-repair/`（`deepseek-v4-pro`）、`var/benchmark/v2-flash-repair/`（`deepseek-v4-flash`）。

## 2. 聚合结果（官方口径 `aggregate()`）

| 跑批 | compile_pass | gen_test_pass | quality PASS / REVIEW / FAIL |
|---|---:|---:|---|
| `v2-pro-repair` | **100%** | 67% | 0 / **3** / 0 |
| `v2-flash-repair` | 67% | 33% | 0 / 2 / **1** |

- pro+repair：3 个全部 **REVIEW**（review-worthy，无阻断缺陷），0 FAIL。
- flash+repair：2 REVIEW + 1 **FAIL**（CSVRecord 编译失败 → `not_executed` 阻断）。
- 两者 `quality_gate_pass_rate=0`：诚实模型几乎触发不到 PASS（见 §5 设计观察），符合 Phase 2 “永不自动采纳”。

## 3. Per-case 质量明细（证据：各 `bench.db` 重评）

### v2-pro-repair（最佳）
| 目标 | 结果 | 质量门 | tests/assertions/weak/taut | 关键信号 |
|---|---|---|---|---|
| `WordUtils` | PASS 7/7 | REVIEW | 7 / 7 / 1 / **0** | 跳过 13 个无证据 case；risk_flags 诚实标注 abbreviate oracle 仅据有限样例 |
| `CSVRecord` | PASS 23/23 | REVIEW | 23 / 43 / 2 / **0** | 跳过 10 个；risk_flags 标注 toString 格式可能异 |
| `Option` | TEST_FAILURE 11/15(2F,2E) | REVIEW | 15 / 76 / 5 / **0** | risk_flags 标注“假设的选项名校验规则”等，正是该让人 review 的点 |

### v2-flash-repair
| 目标 | 结果 | 质量门 | 关键信号 |
|---|---|---|---|
| `Option` | PASS 11/11 | REVIEW | risk_flags：“无 mock，全真实实例” |
| `WordUtils` | TEST_FAILURE 6/9 | REVIEW | 6 弱断言/28，仍无同义反复 |
| `CSVRecord` | COMPILE_FAILURE | **FAIL** | risk_flag 自曝“在测试类内用了自定义 enum（以为允许）”——flash 仍踩 local-enum，pro 未踩 |

> 全 6 个 case **同义反复断言数=0**；弱断言占比低（pro：1/7、2/43、5/76）。断言是**有意义**的，不是 `assertNotNull` 充数。

## 4. 回答：是否“值得人 review 的资产”？

按三条可度量轴，**是**：
1. **断言强度**（`app/quality/test_quality_gate.py` 检测）：0 同义反复、弱断言少数、无“仅弱断言”阻断。
2. **oracle 有据 + 跳过不确定**：pro 三例 `behavior_sources` 均非空（5/6/16）、`omitted_uncertain_cases` 均非空（13/10/9）——v2 的 oracle grounding 真在起作用，把“硬猜”换成“跳过”。
3. **风险自报**：`risk_flags` 诚实指出弱 oracle/假设，**直接告诉 reviewer 该看哪里**——提升可 review 性。

同时**正确地不自动采纳**：质量门给 REVIEW（不是 PASS、不是 FAIL），`conclusion` 恒 `NEED_HUMAN_REVIEW`，`trusted=False`，零生产码改动——`docs/07` P2/P6 落地。

**反面**：`Option`(pro) 仍 TEST_FAILURE（4/15 失败）、flash 仍出 1 个编译 FAIL。即“能 review”≠“都能采纳”；弱模型质量明显更差。

## 5. 设计观察（供 Phase 4，不在本期改）

- **诚实模型几乎到不了 PASS**：只要模型如实填 `risk_flags`，质量门就加 `model_declared_risk` 警告 → 降为 REVIEW。当前 `quality_gate_pass_rate=0` 主要源于此，而非测试差。这是保守取舍（任何自报风险都让人看），但意味着 PASS 通道对诚实模型近乎关闭。Phase 4 需决定：`risk_flags` 是“信息项”还是“降级项”。
- **质量门是结构性、确定性的**：它证明“无明显坏味/不稳定/弱断言/越界”，**不证明 oracle 正确**（`docs/07` P3/A2：不让 LLM/门当验证者）。Option 的 4 个失败仍需人判断是测试错还是发现 bug。

## 6. 复现（零成本）

```powershell
.\.venv\Scripts\python.exe -c @"
from app.storage.db import get_connection
from app.storage.job_repo import JobRepo
from app.report.generation_report import assemble_generation_report
from app.benchmark.models import BenchCaseResult, aggregate
for run in ('v2-pro-repair','v2-flash-repair'):
    repo=JobRepo(conn=get_connection(rf'var/benchmark/{run}/bench.db')); rows=[]
    for j in repo.list():
        g=j.generation or {}; r=assemble_generation_report(g); q=r.get('quality_gate') or {}
        rows.append(BenchCaseResult(name='x',repo_url='x',target_class='x',repo_judged=True,
          compiled=r.get('compiled'),passed=r.get('passed'),gen_outcome=r.get('gen_outcome'),
          conclusion=r.get('conclusion'),quality_gate_status=q.get('status')))
    print(run, aggregate(rows)['quality_gate_pass_rate'], aggregate(rows)['quality_gate_reviews'], aggregate(rows)['quality_gate_failures'])
"@
```

## 7. 不确定项 / 局限（诚实）

| 项 | 说明 |
|---|---|
| 样本量 | 每跑批仅 3 case；模型非确定，不能下通过率强结论 |
| 模型族 | 仅 DeepSeek flash/pro；未对照其它模型 |
| 覆盖率轴 | 本期仍关闭（`-Djacoco.skip`），未验证“目标覆盖提升” |
| 门的边界 | 结构性确定性检查，不证明 oracle 正确性；REVIEW≠正确 |
| grounding 依赖 | 质量门部分信号依赖模型自报 `risk_flags/behavior_sources`，模型可少报以“显得干净” |

## 8. 建议

1. **本期验证目标已达成**，**无需**为此跑新模型（既有 bundle 足够忠实）。若要一份带质量字段的 `report.md` 工件或更大样本，再按 `docs/17` §7 命令重跑（需你确认成本）。
2. **方向：转向 review/质量策略（Phase 4 雏形），而非更广的 Phase 3 修复器。** 数据显示编译已基本解决（pro 100%），剩余是 oracle/test-failure，不该自动修。最有价值的是：把 `risk_flags / omitted_uncertain_cases / behavior_sources / quality_gate` 组织成**面向 reviewer 的产出**，并由 Phase 4 决定 `risk_flags` 是否降级。
3. **扩样本**（5-8 仓）以让质量分布有统计意义——这是比加功能更该做的事，契合本期“验证而非堆功能”。

> 结论：在最佳配置下，生成测试已是**值得人 review 的候选资产**（有据、少坏味、自报风险、零越界），但**正确地不可自动采纳**。下一步应深化 review/质量策略与扩样本，而非堆更多生成/修复功能。
