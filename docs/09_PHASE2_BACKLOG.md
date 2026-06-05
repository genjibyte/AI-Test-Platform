# Phase 2 Backlog —— 最小生成器（Minimal Generator）

> 上级文档：`docs/00_PROJECT_CHARTER.md`、`docs/05_PHASE1_BACKLOG.md`、`docs/07_SOURCE_NOTES.md`。
> 冲突时以 Charter 为准；范围以 `docs/07` 第 5 节 Phase 2 定义为准。
> 本文档只规划 **Phase 2**，**不写代码**，**不启动实现**。

---

## 0. Phase 2 范围与红线

### 0.1 Phase 2 只做这些

1. 目标类 / 方法选择。
2. 有界、相关的上下文收集（`docs/07` P4 顺序）。
3. 首次引入 LLM 调用（仅用于生成测试）。
4. 生成 JUnit5 + Mockito 测试。
5. 写入**独立**测试文件 `<Target>AiGeneratedTest.java`。
6. 执行生成的测试（复用 Phase 1 判卷执行器）。
7. 覆盖率对比（相对 Phase 1 基线）。
8. 生成结果报告（止于事实 + `NEED_HUMAN_REVIEW` 默认）。
9. 在 `samples/calc` 上端到端验证。

### 0.2 Phase 2 全局红线（每个任务继承）

Phase 2 **允许**首次 LLM 调用，但**不允许**：

- ❌ Fixer / 失败修复（属 Phase 3）。
- ❌ 质量门禁 accept/reject 判定（属 Phase 4；Phase 2 只能产出事实 + `NEED_HUMAN_REVIEW`）。
- ❌ 修改被测**生产代码**。
- ❌ 修改或删除**既有测试**。
- ❌ 自动提交 / PR / 合并入仓。
- ❌ 复杂 RAG / 知识图谱 / 运行时知识库。
- ❌ Gradle、多语言、多模块强制执行、UI/接口自动化。
- ❌ 因"看起来正确"而跳过真实执行（`docs/07` 规则 9）。
- ❌ 用弱断言（仅 `assertNotNull`）或断言实现细节冒充有效测试（`docs/07` P2，标记而非接受）。
- ❌ 提交 secrets / token / `.env` / 生成的仓库内容（`docs/07` 规则 12）。

> Phase 2 对应 `docs/07` 4.1 闭环的前半：`Generate -> Execute`（`Diagnose/Repair` 留 Phase 3）。

### 0.3 待决策项（实现前必须拍板）

Phase 2 引入唯一的新外部依赖：**LLM 提供方**。本 backlog 不锁定具体模型，但约束：

1. LLM 客户端必须**隔离在单一模块**（`app/llm/`），其余代码只依赖其接口。
2. 配置经环境变量（如 `TESTAGENT_LLM_PROVIDER` / `TESTAGENT_LLM_MODEL` / `TESTAGENT_LLM_API_KEY`），**不硬编码、不提交密钥**。
3. 需可在无网络/无密钥时以"假客户端"运行（便于测试与离线开发）。
4. 提供方/模型选定后记入《Phase 2 LLM 决策》文档，再开始编码。

> 与 Phase 1 的"技术栈假设"一致：任务的目标/输入/输出/验收与具体模型无关。

---

## 1. 任务依赖关系

```text
P2-T01 目标选择
  -> P2-T02 有界上下文收集
        -> P2-T03 LLM 客户端与配置（隔离）
              -> P2-T04 Prompt / 场景规划构建
                    -> P2-T05 生成编排（调用 LLM -> 测试构件）
                          -> P2-T06 写入独立测试文件
                                -> P2-T07 执行生成测试（复用 Phase 1）
                                      -> P2-T08 覆盖率对比
                                            -> P2-T09 生成结果报告
P2-T10 Job 状态机与生成流水线编排（贯穿 T01–T09）
P2-T11 samples/calc 端到端验证
```

共 **11 个任务**。T10 为编排骨架，可在 T01 后先立状态/流水线占位，随各任务填充。

---

## 2. 任务清单

---

### P2-T01　目标类 / 方法选择

1. **任务目标**：让用户对某个已判卷成功的 Job 指定目标类与（可选）目标方法，并校验其在导入仓库中真实存在。
2. **输入**：Job id；目标类全限定名；可选目标方法签名。
3. **输出**：校验后的目标描述（类路径、方法、所在源文件、是否存在）。
4. **涉及模块**：`app/targeting/`（新增）。
5. **需要新增或修改的文件**：
   - 新增 `app/models/target.py`（目标描述结构）
   - 新增 `app/targeting/target_selector.py`（在 repo 中定位/校验目标）
   - 修改 `app/api/jobs.py`（`POST /jobs/{id}/target` 设定目标）
6. **验收标准**：合法目标可定位到源文件；不存在的类/方法明确报错；目标持久化到 Job。
7. **运行命令**：
   ```bash
   curl -X POST localhost:8000/jobs/<id>/target -d '{"class":"com.example.Calc","method":"max"}'
   ```
8. **不允许做的事**：❌ 不做全仓库批量目标；❌ 不在此步收集上下文；❌ 不调用 LLM。

---

### P2-T02　有界上下文收集

1. **任务目标**：按 `docs/07` P4 的优先级，收集**有界、相关**的生成上下文，不喂整库。
2. **输入**：校验后的目标（来自 T01）。
3. **输出**：结构化上下文：目标方法源码、目标类字段/构造函数、直接方法签名与 import、邻近既有测试、项目测试约定、Maven 依赖摘要。
4. **涉及模块**：`app/context/`（新增）。
5. **需要新增或修改的文件**：
   - 新增 `app/models/gen_context.py`
   - 新增 `app/context/context_collector.py`（Java 源码轻量解析，提取签名/字段/构造函数/import）
6. **验收标准**：能产出含上述各部分的有界上下文；**缺必需上下文时显式失败**（`docs/07` P4），不臆造。
7. **运行命令**：
   ```bash
   curl localhost:8000/jobs/<id>/context
   ```
8. **不允许做的事**：❌ 不喂整仓库；❌ 不做向量检索/复杂 RAG；❌ 不让模型臆造依赖/构造函数。

---

### P2-T03　LLM 客户端与配置（隔离）

1. **任务目标**：提供**隔离、可配置、可离线**的 LLM 客户端抽象，作为 Phase 2 唯一外部依赖入口。
2. **输入**：环境变量配置（provider / model / api key / base url）。
3. **输出**：统一 `generate(prompt) -> text` 接口；真实客户端 + 假客户端（离线/测试）两种实现。
4. **涉及模块**：`app/llm/`（新增）。
5. **需要新增或修改的文件**：
   - 新增 `app/llm/client.py`（接口 + 工厂）
   - 新增 `app/llm/fake_client.py`（确定性假实现，用于测试/离线）
   - 修改 `app/config.py`（新增 LLM 配置项，默认不启用）
6. **验收标准**：无密钥/离线时用假客户端可运行；真实客户端经环境变量装配；**密钥不入库、不写日志**。
7. **运行命令**：
   ```bash
   pytest tests/test_llm_client.py -q   # 走假客户端
   ```
8. **不允许做的事**：❌ 不硬编码密钥/模型；❌ 不在 `app/` 其它模块直接发起网络调用；❌ 不提交 `.env`。

---

### P2-T04　Prompt / 场景规划构建

1. **任务目标**：从有界上下文构建生成 Prompt，显式要求 JUnit5 + Mockito、边界与异常场景（`docs/07` 4.3）。
2. **输入**：有界上下文（T02）。
3. **输出**：结构化 Prompt（含目标、约束、邻近测试风格、期望场景列表）。
4. **涉及模块**：`app/generate/`（新增）。
5. **需要新增或修改的文件**：
   - 新增 `app/generate/prompt_builder.py`
   - 新增 `app/models/scenario_plan.py`（最小场景集合）
6. **验收标准**：Prompt 含目标方法、依赖签名、邻近测试风格约束、明确的边界/异常要求；可快照测试。
7. **运行命令**：
   ```bash
   pytest tests/test_prompt_builder.py -q
   ```
8. **不允许做的事**：❌ 不把整库塞进 Prompt；❌ 不要求模型改生产代码；❌ 此步不调用 LLM。

---

### P2-T05　生成编排（调用 LLM → 测试构件）

1. **任务目标**：调用 LLM 客户端生成测试，解析为测试文件构件，并**标记为不可信**（`docs/07` P2）。
2. **输入**：Prompt（T04）、LLM 客户端（T03）。
3. **输出**：生成的测试源码构件（类名、文件名建议、原始文本、untrusted 标记）。
4. **涉及模块**：`app/generate/`。
5. **需要新增或修改的文件**：
   - 新增 `app/generate/generator.py`（调用 + 抽取代码块 + 基本结构校验）
   - 新增 `app/models/generated_test.py`
6. **验收标准**：能从 LLM 响应抽取出 Java 测试类文本；非法/空响应明确失败；构件默认 untrusted。
7. **运行命令**：
   ```bash
   pytest tests/test_generator.py -q   # 假客户端返回固定测试
   ```
8. **不允许做的事**：❌ 不让模型充当验证者（`docs/07` A2）；❌ 不在此步判定通过；❌ 不做修复。

---

### P2-T06　写入独立测试文件

1. **任务目标**：把生成构件写入**独立**测试文件 `<Target>AiGeneratedTest.java`，绝不触碰生产代码与既有测试。
2. **输入**：生成构件（T05）、工作区。
3. **输出**：工作区测试源码树中的新文件；写入边界校验结果。
4. **涉及模块**：`app/generate/`、`app/runtime/`。
5. **需要新增或修改的文件**：
   - 新增 `app/generate/test_writer.py`（计算目标路径 + 写入 + 边界守卫）
6. **验收标准**：仅新增一个测试文件；不覆盖既有文件；写入前后**生产代码与既有测试零改动**（可校验）。
7. **运行命令**：
   ```bash
   pytest tests/test_test_writer.py -q
   ```
8. **不允许做的事**：❌ 不改 `src/main`；❌ 不改/删既有 `*Test.java`；❌ 不改 pom。

---

### P2-T07　执行生成测试

1. **任务目标**：复用 Phase 1 执行器，对含新生成测试的工程跑 `mvn test`，捕获编译/执行结果。
2. **输入**：写入生成测试后的工作区（T06）。
3. **输出**：编译状态、执行状态、失败日志（复用 ExecRecord + BuildOutcome）。
4. **涉及模块**：复用 `app/build/`、`app/coverage/`、`app/report/`（surefire 解析）。
5. **需要新增或修改的文件**：
   - 新增 `app/generate/gen_executor.py`（编排一次含生成测试的判卷执行，复用现有 runner）
6. **验收标准**：能区分生成测试"编译失败/执行失败/通过"；结果与日志持久化；不修复（仅记录）。
7. **运行命令**：
   ```bash
   pytest tests/test_gen_executor.py -q   # 用本地样例 + 已知测试
   ```
8. **不允许做的事**：❌ 不做失败重试/修复；❌ 不为通过而弱化断言；❌ 不改 pom。

---

### P2-T08　覆盖率对比

1. **任务目标**：对比加入生成测试前（Phase 1 基线）后的覆盖率，给出整体与目标类/方法的增量。
2. **输入**：基线覆盖率（Phase 1 Job）、生成测试执行后的覆盖率（T07）。
3. **输出**：覆盖率 delta（行/分支整体 + 目标类聚合），是否不下降、目标是否提升。
4. **涉及模块**：`app/coverage/`。
5. **需要新增或修改的文件**：
   - 新增 `app/models/coverage_delta.py`
   - 新增 `app/coverage/coverage_compare.py`
6. **验收标准**：能正确计算 before/after delta；覆盖率下降能被标记；目标类提升可量化。
7. **运行命令**：
   ```bash
   pytest tests/test_coverage_compare.py -q
   ```
8. **不允许做的事**：❌ 不把"覆盖率提升"等同"测试有效"（`docs/07` P3）；❌ 不做 mutation testing。

---

### P2-T09　生成结果报告

1. **任务目标**：扩展报告，输出生成状态、编译/执行状态、覆盖率 delta、patch 预览与不可信标记；结论默认 `NEED_HUMAN_REVIEW`。
2. **输入**：T05–T08 结果。
3. **输出**：生成报告 JSON：是否编译、是否执行、覆盖率变化、新增测试 diff、是否改动生产代码（应为否）、`NEED_HUMAN_REVIEW`。
4. **涉及模块**：`app/report/`。
5. **需要新增或修改的文件**：
   - 修改 `app/report/report_assembler.py`（增加生成段）
   - 新增 `app/api/generation.py`（`GET /jobs/{id}/generation`、patch 预览）
6. **验收标准**：报告含生成全量事实与 diff；**不输出 accept/reject**（Phase 4）；不确定默认 `NEED_HUMAN_REVIEW`。
7. **运行命令**：
   ```bash
   curl localhost:8000/jobs/<id>/generation
   ```
8. **不允许做的事**：❌ 不做 accept/reject 门禁；❌ 不隐藏失败（`docs/07` A4）；❌ 不伪造结果。

---

### P2-T10　Job 状态机扩展与生成流水线编排

1. **任务目标**：扩展状态机并编排 Phase 2 生成流水线，串起 T01–T09，与 Phase 1 判卷解耦但复用其基线。
2. **输入**：已判卷成功的 Job + 目标。
3. **输出**：生成流水线：`TARGET_SELECT -> CONTEXT -> GENERATE -> GEN_EXECUTE -> COMPARE -> GEN_DONE/GEN_FAILED`。
4. **涉及模块**：`app/pipeline/`、`app/models/job.py`、`app/storage/`。
5. **需要新增或修改的文件**：
   - 修改 `app/models/job.py`（新增 Phase 2 状态与字段；schema/repo 同步）
   - 新增 `app/pipeline/generate_pipeline.py`
   - 修改 `app/api/jobs.py`（触发生成流水线）
6. **验收标准**：单次调用从目标到覆盖率对比跑通；任一步失败短路为 `GEN_FAILED` 并保留日志；各步状态可查。
7. **运行命令**：
   ```bash
   curl -X POST localhost:8000/jobs/<id>/generate
   ```
8. **不允许做的事**：❌ 不在流水线加入 Fixer/门禁；❌ 不并发多任务；❌ 不自动入仓。

---

### P2-T11　samples/calc 端到端验证

1. **任务目标**：在 `samples/calc` 上完整跑通 Phase 2：选目标 `Calc.max` → 收集上下文 → 生成 → 写文件 → 执行 → 覆盖率对比 → 报告。
2. **输入**：`samples/calc`（Phase 1 已验证）；目标 `com.example.Calc#max`。
3. **输出**：一次完整生成运行记录；生成的 `CalcAiGeneratedTest.java`；覆盖率 delta（期望 `max` 分支覆盖提升）；`NEED_HUMAN_REVIEW` 报告。
4. **涉及模块**：全链路。
5. **需要新增或修改的文件**：
   - 新增 `tests/e2e/test_phase2_e2e.py`（门控 `TESTAGENT_E2E=1`，可用假客户端产出固定测试）
   - 新增 `docs/1X_PHASE2_ACCEPTANCE_REPORT.md`（验收时）
6. **验收标准**：生成测试可编译、可执行；目标分支覆盖率较基线提升；全程未改生产代码/既有测试。
7. **运行命令**：
   ```bash
   $env:TESTAGENT_E2E="1"; pytest tests/e2e/test_phase2_e2e.py -v
   ```
8. **不允许做的事**：❌ 不只展示成功（`docs/07` A4）；❌ 不为通过而挑数据；❌ 不改被测代码。

---

## 3. Phase 2 完成定义（DoD）

1. T01–T11 全部通过各自验收。
2. 能对一个目标类/方法：收集有界上下文 → LLM 生成 → 写独立测试 → 真实执行 → 覆盖率对比 → 出报告。
3. 生成测试可编译、可执行；目标覆盖率较 Phase 1 基线可量化变化。
4. 全程零生产代码修改、零既有测试改动、零自动入仓、零 Fixer、零质量门禁。
5. 不确定结论默认 `NEED_HUMAN_REVIEW`。

> 满足后进入 Phase 3（失败分类 + 有限 Fixer，≤3 轮），由后续 backlog 规划。

---

## 4. 与 Phase 1 的衔接

- 复用：工作区/执行器（T03）、mvn 执行（T06）、Surefire/JaCoCo 解析（T07/T08）、报告框架（T10）、Job/持久化（T02）。
- 新增模块：`app/targeting/`、`app/context/`、`app/llm/`、`app/generate/`。
- 前置：Phase 1 验收通过（见 `docs/08`）；`docs/08` 第 12 节检查单第 9 项（干净主机远程 OSS 端到端）建议在 Phase 2 期间补齐。

> 本文档为规划。**未开始 Phase 2 实现。** 进入实现需显式指令，并先完成 0.3 的 LLM 决策。
