# Phase 2 中期验收、审计与后续规划

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/00_foundation/07_SOURCE_NOTES.md`、`/docs/20_phase2/09_PHASE2_BACKLOG.md`。
> 报告日期：2026-06-06（换机后在新机器上重建环境并复核）。
> 性质：**中期审计 + 规划，不是 Phase 2 终验**。Phase 2 终验报告待 T11 完成后另出（`docs/1X_PHASE2_ACCEPTANCE_REPORT.md`）。
> 本文不实现新功能，只记录"已设计/已实现的事实"、"红线合规结论"、"差距"与"后续计划"。

---

## 0. 结论速览

| 维度 | 结论 |
|---|---|
| Phase 2 任务进度 | T01–T07 已实现，T08–T11 未开始（7/11） |
| 单元/集成测试 | ✅ 78 passed, 2 skipped（80 个用例，2 个为 Maven 门控 e2e） |
| 真实 `mvn test` 判卷（Phase 1 e2e） | ✅ `samples/calc` BUILD SUCCESS（约 22s） |
| T07 真实 Maven 冒烟（本次新增） | ✅ 生成测试 `PASS` 2/2，after line/branch=1.0 |
| 红线合规（生产码/既有测试/密钥/门禁/Fixer） | ✅ 全部满足，详见 §3 |
| 发现的差距 | 3 项（均非红线违规，见 §4），建议并入 T10 处理 |

> 一句话：**判卷场（Phase 1）稳固；最小生成器（Phase 2）已打通"目标→上下文→LLM→写文件→执行"前半链，差"覆盖率对比→报告→流水线编排→端到端"后半链。**

---

## 1. 已设计与实现（T01–T07 逐项核对）

每项对照 `docs/09` 的验收标准给出"实现位置 + 结论 + 证据"。

### P2-T01 目标类/方法选择 — ✅（含 1 处偏离，见 §4.1）
- 实现：`app/targeting/target_selector.py` `resolve_target()`；API `app/api/context.py`（`GET /jobs/{id}/classes`、`/classes/{fqn}`、`POST /jobs/{id}/context`）。
- 结论：合法目标可定位到 `src/main/java` 源文件；类不存在/方法不存在均显式报错（`Target.exists/method_exists/reason`，[target_selector.py:24-62](../app/targeting/target_selector.py)）。
- 偏离：backlog 要求 `POST /jobs/{id}/target` 且"目标持久化到 Job"；当前以无状态的 `/context` 取代，**目标未写回 Job**（详见 §4.1）。

### P2-T02 有界上下文收集 — ✅
- 实现：`app/context/context_collector.py` `build_snapshot()`，产出 `ContextSnapshot`。
- 结论：严格按 `docs/07` P4 顺序收集（目标方法源码、字段、构造函数、import、邻近测试、Maven 依赖摘要），**不喂整库**；缺必需上下文抛 `ContextError` 显式失败（[context_collector.py:48-53](../app/context/context_collector.py)）。无向量检索/RAG。

### P2-T03 LLM 客户端与配置（隔离） — ✅
- 实现：`app/llm/client.py`（`LLMClient` 抽象 + `get_client` 工厂）、`fake_client.py`（确定性离线假实现）、`openai_client.py`（OpenAI/DeepSeek 兼容真实实现）；配置 `app/config.py`。
- 结论：默认 `fake`，无网络/无密钥即可运行；真实 provider 经 `TESTAGENT_LLM_*` 环境变量装配；**密钥仅存私有字段、仅用于 Authorization 头、不入库不写日志**（[openai_client.py:35,44](../app/llm/openai_client.py)，[config.py:37](../app/config.py)），`.env` 已在 `.gitignore`。未知 provider 显式 `NotImplementedError`，杜绝误连真实模型。

### P2-T04 Prompt 构建 — ✅
- 实现：`app/generate/prompt_builder.py` `build_prompt()`。
- 结论：确定性渲染（无时间戳/随机，可快照测试）；显式要求 JUnit5+Mockito、happy + 边界/异常、有意义断言、**不得臆造构造函数/依赖/返回值/import**（[prompt_builder.py:22-29](../app/generate/prompt_builder.py)）；带邻近测试风格段。

### P2-T05 生成编排 — ✅（设计与 backlog 不同，非缺陷，见 §4.2）
- 实现：`app/generate/generation.py` `dry_generate()` + `app/llm/schema.py`（`parse_payload`/`assemble_result`）。
- 结论：走通 context→prompt→client→parse→assemble；**身份字段（类/方法/文件名/`trusted`）由平台确定性填充，模型只控创作字段**，对抗性输出无法篡改目标身份（[schema.py:41-57,86-105](../app/llm/schema.py)）；构件默认 `trusted=False`（`docs/07` P2）。
- 偏离：backlog 设想 `generator.py` + markdown 代码块抽取 + "基本结构校验"；实际采用 **JSON payload 契约**（更稳），但 `test_source` 仅做 schema 字符串校验，未校验是否为可解析 Java 类（详见 §4.2）。

### P2-T06 写入独立测试文件 — ✅
- 实现：`app/generate/test_writer.py` `write_generated_test()`。
- 结论：仅在目标类同模块的 `src/test/java` 下新增 `<Target>AiGeneratedTest.java`；**强制规范类名**避免与既有测试同名碰撞、**拒绝覆盖既有文件**、**只写 src/test 不写 src/main**（[test_writer.py:82-94](../app/generate/test_writer.py)）；`production_code_touched=False`。

### P2-T07 执行生成测试 — ✅（本次新增）
- 实现：`app/generate/gen_executor.py` `execute_generated_test()`。
- 结论：复用 Phase 1 的 JaCoCo runner 跑**全量 suite（含生成测试）**，得到供 T08 对比的 after 覆盖率；再**仅解析生成测试自身的 `TEST-<fqcn>.xml`** 隔离其结果，分类 `PASS / TEST_FAILURE / COMPILE_FAILURE / NO_TESTS / BUILD_ERROR / NO_MAVEN`，**不受同套件中其它无关失败干扰**（[gen_executor.py:_classify](../app/generate/gen_executor.py)）。无修复/重试/改 pom。
- 证据：9 个 Maven-free 单测（含"无关套件失败时生成测试仍判 PASS"的隔离用例）+ 1 次真实 Maven 冒烟（PASS 2/2、after 覆盖率 1.0）。

---

## 2. 尚未开始（T08–T11）

| 任务 | 目标 | 主要新增文件（规划） | 状态 |
|---|---|---|---|
| T08 覆盖率对比 | baseline vs after 的行/分支 delta + 目标类聚合 | `app/models/coverage_delta.py`、`app/coverage/coverage_compare.py` | ⬜ |
| T09 生成结果报告 | 生成/编译/执行/覆盖率 delta/patch 预览 + `NEED_HUMAN_REVIEW` | 改 `app/report/report_assembler.py`、新增 `app/api/generation.py` | ⬜ |
| T10 状态机+生成流水线 | `TARGET_SELECT→CONTEXT→GENERATE→GEN_EXECUTE→COMPARE→GEN_DONE/GEN_FAILED`，串起 T01–T09 | 改 `app/models/job.py`、新增 `app/pipeline/generate_pipeline.py`、改 `app/api/jobs.py` | ⬜ |
| T11 端到端验证 | `samples/calc` 全链路 + 终验报告 | `tests/e2e/test_phase2_e2e.py`、`docs/1X_PHASE2_ACCEPTANCE_REPORT.md` | ⬜ |

---

## 3. 红线合规审计

对照 `docs/00` 第 8 节、`docs/07` 第 6/7 节与 `docs/09` §0.2 逐条核验：

| 红线 | 结论 | 证据 |
|---|---|---|
| ❌ 不改生产代码（src/main） | ✅ | test_writer 守卫"必须在 src/test/java 内"，否则 `TestWriteError` |
| ❌ 不改/删既有测试 | ✅ | 规范类名避免同名碰撞 + 拒绝覆盖既有文件 |
| ❌ 不做 Fixer/失败修复 | ✅ | gen_executor 无重试/修复路径，仅记录事实 |
| ❌ 不做 accept/reject 门禁 | ✅ | 全仓无 verdict 产出；结论留待 Phase 4 |
| ❌ 不提交密钥/.env | ✅ | key 仅私有字段 + Bearer 头，不日志不入库；`.env`、`.claude/` 已 gitignore |
| ❌ 不臆造依赖/构造函数 | ✅ | prompt 显式禁止；上下文有界；缺失即显式失败 |
| ❌ 不因"看起来正确"跳过执行 | ✅ | T07 真实 `mvn test`，按 surefire 事实分类 |
| ❌ 不用弱断言冒充有效测试 | ✅(标记) | prompt 要求有意义断言；`trusted=False` 默认；弱断言检测属 Phase 4 |
| ❌ 不自动入仓/PR/合并 | ✅ | 无任何 git push/PR 代码路径 |
| ❌ 不复杂 RAG/知识图谱 | ✅ | 上下文为确定性轻量解析，无向量检索 |
| 离线可运行（无网/无密钥） | ✅ | 默认 fake client，单测全程离线 |

**结论：Phase 2 当前实现无红线违规。**

---

## 4. 审计发现的差距与建议（均非红线违规）

### 4.1 目标未持久化到 Job（T01 验收第 6 条未满足）
- 现象：`/jobs/{id}/context` 为无状态接口，每次调用重建 `ContextSnapshot`，`Target` 不写回 Job。
- 影响：流水线串联与报告复现需要"当前目标"的稳定来源。
- 建议：**并入 T10**——在 `Job` 增 `target` 字段，落库后由生成流水线读取，避免重复造一套 `/target` 接口。

### 4.2 生成构件结构校验偏轻（T05）
- 现象：`parse_payload` 仅校验 JSON schema，`test_source` 只要是字符串即通过；未校验其是否为"可解析的 Java 类且含 `@Test`"。
- 影响：空壳/非法 Java 文本会被写盘，留到 `mvn` 编译阶段才暴露（仍会被 T07 判 `COMPILE_FAILURE`，不会误判 PASS，故非安全问题，仅效率/信号问题）。
- 建议：**T11 前补一个最小结构校验**（含 `class` 关键字 + 至少一个 `@Test`），非法即显式失败，向左移错。

### 4.3 T07 跑全量套件的性能取舍
- 现象：为拿到 after 整体覆盖率，T07 跑全量 `mvn test`（含 JaCoCo）。
- 影响：大仓库每次生成都会重跑既有全量测试，慢。
- 取舍：当前以单模块样例为主，无碍；记为后续优化点（可选 `-Dtest=<生成测试>` 单跑 + 覆盖率合并），**不在 Phase 2 内强行优化**。

### 4.4 文档小瑕疵
- `generation.py` docstring 标注 `P2-T03`，实际承担 T05 seam；T10 收口时一并校正注释编号。

---

## 5. 后续设计规划

### 5.1 Phase 2 收尾（近期，建议顺序）

**T08 覆盖率对比** → **T09 报告** → **T10 流水线编排** → **T11 端到端 + 终验**。
设计要点：

- **T08**：`CoverageDelta` 模型记录 `line/branch` 的 before/after/delta、`coverage_not_dropped: bool`、目标类聚合增量。需让 `jacoco_parser` 能按类聚合（当前 `parse_jacoco` 多为汇总，需补"按 `com.example.Calc` 提取 counter"）。判据来自 `docs/00` 北极星：覆盖率不下降 + 目标提升可量化；**不把"覆盖率提升"等同"有效"**。
- **T09**：报告新增"生成段"——是否生成/编译/执行、覆盖率 delta、新增测试 diff（patch 预览）、是否改生产代码（应为否）、结论恒为 `NEED_HUMAN_REVIEW`；新增 `GET /jobs/{id}/generation`。**不输出 accept/reject**。
- **T10**：`Job` 增 Phase 2 状态（`TARGET_SELECT/CONTEXT/GENERATE/GEN_EXECUTE/COMPARE/GEN_DONE/GEN_FAILED`）与字段（`target`、`generation`、`coverage_delta`），同步 `schema.sql`/`job_repo`；`generate_pipeline.py` 串起 T01–T09，任一步失败短路 `GEN_FAILED` 并留日志；与 Phase 1 判卷解耦但复用其 baseline。顺手补齐 §4.1。
- **T11**：`tests/e2e/test_phase2_e2e.py`（门控 `TESTAGENT_E2E`，用假客户端产出固定测试，或真实模型可选）；跑通 `Calc.max` 全链路；产出 `/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md`（含成功**与**失败用例，禁止只演示成功）。

**Phase 2 完成定义（DoD，复述自 `docs/09` §3）**：T01–T11 全过；对一个目标类/方法能"有界上下文→LLM 生成→写独立测试→真实执行→覆盖率对比→出报告"；生成测试可编译可执行、目标覆盖率较 baseline 可量化变化；全程零生产码改动、零既有测试改动、零自动入仓、零 Fixer、零门禁；不确定默认 `NEED_HUMAN_REVIEW`。

### 5.2 Phase 3+ 路线（来自 `docs/07` §5，仅方向不展开实现）

| 阶段 | 范围 | 关键红线 |
|---|---|---|
| **Phase 3 修复闭环** | 失败分类（缺 import/符号未找到/构造不匹配/类型不匹配/Mockito stub/断言失败/测试数据构造）+ 有限 Fixer，**≤3 轮**，patch 历史，badcase 落库 | 只改生成测试文件、保留生产码、可追溯失败类型、**不靠弱化断言修复** |
| **Phase 4 质量门禁** | 断言质量检查、生产码改动检查、覆盖率对比、弱断言检测，产出 `ACCEPT/REJECT/NEED_HUMAN_REVIEW` | 不确定默认 `NEED_HUMAN_REVIEW`；LLM **不得**充当验证者 |
| **Phase 5 基准评测** | ≥3 个公开 Java Maven 仓库、每仓 ≥5 目标方法、Fail-to-Pass 证据、聚合指标（见 `docs/07` §8） | 不做 success-only demo |
| **产品形态（Charter §10）** | Web 平台：项目列表/详情、任务创建、Agent 轨迹、Patch 预览、质量报告页 | 判卷场 API 先于前端美化（反模式 A1） |

> 进入 Phase 3 的前置：Phase 2 终验通过（T11 + 终验报告）。每个新阶段开工前先读 `docs/00` 与 `docs/07`，不得跨阶段提前实现。

---

## 6. 复现证据（本机）

环境：Windows 11，Python 3.12.10（venv），Maven 3.9.9，JDK 17（Microsoft）。

```powershell
# 单元/集成（无需 Maven）
.\.venv\Scripts\python.exe -m pytest -q          # 78 passed, 2 skipped

# Phase 1 真实判卷 e2e（需 Maven）
$env:TESTAGENT_MAVEN_CMD = "C:\Users\lenovo\AppData\Local\Programs\Maven\apache-maven-3.9.9\bin\mvn.cmd"
$env:TESTAGENT_E2E = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e -v # 1 passed, 1 skipped
```

新机器工具链与路径见会话记忆 `new-machine-toolchain`。本审计未改动任何生产逻辑，仅新增 T07 模块/测试与本文件。
