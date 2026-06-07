# Phase 2 验收报告（最小生成器）

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/00_foundation/07_SOURCE_NOTES.md`、`/docs/20_phase2/09_PHASE2_BACKLOG.md`。
> 验收日期：2026-06-06。
> 结论：**Phase 2 通过。最小生成器闭环成立——目标→有界上下文→LLM 生成→写独立测试→真实执行→覆盖率对比→报告，全部用真实 Maven 验证，且成功与失败两类结果均被如实记录。**
> 本报告不实现新功能，仅记录验收证据。

---

## 0. 验收结论速览

| 维度 | 结论 |
|---|---|
| 单元/集成测试 | ✅ 101 passed, 4 skipped（4 个为 Maven 门控 e2e） |
| Phase 2 真实 e2e（`samples/calc`） | ✅ 2 passed in ~16s（成功用例 + 编译失败用例） |
| 生成测试可编译可执行 | ✅ `CalcAiGeneratedTest` 编译通过、运行 2/2 绿 |
| 目标覆盖率较基线提升 | ✅ `Calc` 分支覆盖 0.5 → 1.0（`target_branch_delta = +0.5`） |
| 覆盖率不下降 | ✅ `coverage_dropped = false`（整体分支 +0.5） |
| 未修改生产代码 / 既有测试 | ✅ `Calc.java`、`CalcTest.java` 校验零改动 |
| 失败被如实记录（不隐藏） | ✅ 编译失败用例 `compiled=false`、`gen_outcome=COMPILE_FAILURE`，仍 `GEN_DONE` |
| 无 accept/reject 门禁 | ✅ 结论恒为 `NEED_HUMAN_REVIEW` |
| 无 Fixer / 无自动入仓 | ✅ 确认 |

---

## 1. 运行命令（本机）

环境：Windows 11，Python 3.12.10（venv），Maven 3.9.9，JDK 17（Microsoft）。

```powershell
# 单元/集成（无需 Maven）
.\.venv\Scripts\python.exe -m pytest -q            # 101 passed, 4 skipped

# Phase 2 真实 e2e（需 Maven）
$env:TESTAGENT_MAVEN_CMD = "C:\Users\lenovo\AppData\Local\Programs\Maven\apache-maven-3.9.9\bin\mvn.cmd"
$env:TESTAGENT_E2E = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_phase2_e2e.py -v   # 2 passed
```

---

## 2. 端到端证据

### 2.1 成功用例 `test_phase2_success`

目标 `com.example.Calc#max`。基线 `CalcTest` 仅测 `max(7,3)`（命中 `a>b` 真分支），假分支未覆盖。
离线 fixture 客户端确定性返回一个覆盖两个分支的真实测试，经"写文件→真实 `mvn test`→JaCoCo"后：

| 指标 | 基线(before) | 生成后(after) | delta |
|---|---|---|---|
| `Calc` 行覆盖 | 1.0 | 1.0 | 0.0 |
| `Calc` 分支覆盖 | **0.5**（1/2） | **1.0**（2/2） | **+0.5** |
| 整体分支覆盖 | — | — | **+0.5** |

- `gen_outcome = PASS`，`gen_counts = {total:2, passed:2, failed:0}`。
- `coverage_dropped = false`，`target_improved = true`。
- `production_code_touched = false`，`trusted = false`，`conclusion = NEED_HUMAN_REVIEW`。
- `Calc.java`/`CalcTest.java` 校验未被改动；新增文件仅 `src/test/java/com/example/CalcAiGeneratedTest.java`。

### 2.2 编译失败用例 `test_phase2_compile_failure_surfaced`

离线 fixture 客户端故意返回引用不存在方法 `Calc.multiply(...)` 的测试：

- 流水线**完整跑完**（`status = GEN_DONE`），未崩溃、未吞错。
- 报告如实呈现：`gen_outcome = COMPILE_FAILURE`，`compiled = false`，`executed = false`，`passed = false`。
- 结论 `NEED_HUMAN_REVIEW`；生产代码/既有测试零改动。
- 对应 `docs/07` A4：**展示失败，不只演示成功**。

---

## 3. 任务验收对照（T01–T11）

| 任务 | 验收 | 证据 |
|---|---|---|
| T01 目标选择 | ✅ | `resolve_target` 定位/校验；目标经 T10 持久化到 `Job.target` |
| T02 有界上下文 | ✅ | `build_snapshot` 按 docs/07 P4 收集；缺失显式 `ContextError` |
| T03 LLM 隔离 | ✅ | `app/llm/` 单一入口；默认 fake 离线；密钥仅 env，不入库不日志 |
| T04 Prompt | ✅ | 确定性、JUnit5+Mockito、边界/异常、禁臆造 |
| T05 生成编排 | ✅ | JSON 契约；身份字段确定性填充；`trusted=False` |
| T06 写独立文件 | ✅ | 仅 `src/test/java` 新增、拒覆盖、规范类名 |
| T07 执行生成测试 | ✅ | 复用 Phase 1 runner；隔离解析生成测试自身报告分类 |
| T08 覆盖率对比 | ✅ | 按类聚合 JaCoCo；`CoverageDelta` 整体+目标 delta + 不降/提升标记 |
| T09 生成报告 | ✅ | 事实段 + patch 预览 + 恒 `NEED_HUMAN_REVIEW`；`GET /jobs/{id}/generation` |
| T10 状态机+流水线 | ✅ | 7 个 Phase 2 状态 + `generate_pipeline`；失败短路 `GEN_FAILED`；`POST /jobs/{id}/generate` |
| T11 端到端 | ✅ | 本报告 §2，成功+失败两用例真实 Maven 通过 |

---

## 4. 红线确认（Phase 2）

| 红线 | 结论 |
|---|---|
| 不改生产代码 / 既有测试 | ✅ e2e 校验零改动；test_writer 边界守卫 |
| 不做 Fixer / 失败修复 | ✅ 编译失败用例仅记录不修复 |
| 不做 accept/reject 门禁 | ✅ 结论恒 `NEED_HUMAN_REVIEW` |
| 不提交密钥 / `.env` / 生成仓库内容 | ✅ key 仅 env+Bearer 头；`.env`/`.claude`/`var` 已 gitignore |
| 不臆造依赖 / 不复杂 RAG | ✅ 有界上下文 + 显式失败 |
| 不因"看起来正确"跳过执行 | ✅ 全部经真实 `mvn test` 判定 |
| 不自动入仓 / PR / 合并 | ✅ 无相关代码路径 |

---

## 5. Phase 2 完成定义（DoD）核对

1. ✅ T01–T11 全部通过各自验收。
2. ✅ 对一个目标类/方法：有界上下文 → LLM 生成 → 写独立测试 → 真实执行 → 覆盖率对比 → 出报告。
3. ✅ 生成测试可编译可执行；目标覆盖率较 Phase 1 基线可量化变化（分支 0.5→1.0）。
4. ✅ 全程零生产代码修改、零既有测试改动、零自动入仓、零 Fixer、零质量门禁。
5. ✅ 不确定结论默认 `NEED_HUMAN_REVIEW`。

---

## 6. 已知边界与后续

- **离线 fake 客户端**产出的是占位空测试（含 import，可编译、可运行、但不覆盖目标）；真实覆盖提升用例由 e2e 的确定性 fixture 客户端验证。接入真实模型只需配置 `TESTAGENT_LLM_PROVIDER/MODEL/API_KEY`。
- **生成构件结构校验仍偏轻**（`docs/10` §4.2）：非法 Java 会留到 `mvn` 编译阶段暴露（被判 `COMPILE_FAILURE`，不会误判 PASS）。可在 Phase 3 起步时左移。
- **T07 跑全量套件**取舍见 `docs/10` §4.3，单模块样例无碍。
- 下一阶段：**Phase 3 失败分类 + 有限 Fixer（≤3 轮）**，前置已满足（Phase 2 验收通过）。MVP（Charter §9）尚需 Phase 3 的"至少 1 轮修复"与 Phase 4 的"是否建议采纳"。

> 满足 DoD，进入 Phase 3。新阶段开工前先读 `docs/00` 与 `docs/07`。
