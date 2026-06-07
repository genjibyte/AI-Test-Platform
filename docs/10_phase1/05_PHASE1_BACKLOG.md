# Phase 1 Backlog —— 判卷场（The Judging Arena）

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/00_foundation/01_PROJECT_PLAN.md`。
> 冲突时以 Charter 为准。
> 本文档只规划 **Phase 1**，**不写代码**。

---

## 0. Phase 1 范围与红线

### 0.1 Phase 1 只做这 8 件事

1. 导入 Git 仓库。
2. 识别 Maven 项目。
3. 执行原始 `mvn test`。
4. 解析 Surefire 报告。
5. 执行或解析 JaCoCo 覆盖率。
6. 保存任务状态和执行日志。
7. 提供报告接口。
8. 用一个开源 Maven 项目完成端到端验证。

### 0.2 Phase 1 全局红线（每个任务都继承）

Phase 1 **不允许**：

- ❌ 接入任何 LLM / 大模型。
- ❌ 做任何测试生成（Generate）。
- ❌ 做任何失败修复（Fixer / Fix Attempt）。
- ❌ 做复杂前端（最多一个用于自测的极简页面或直接用 API/curl；不引入前端框架、不做轨迹可视化）。
- ❌ 修改被测开源项目的**生产代码或测试代码**（判卷场只读地执行，不改原仓库内容）。
- ❌ 做 Gradle、多语言、多租户、并发调度等 Charter 第 8 节禁止项。

> Phase 1 对应规划文档里程碑 **M0 + M1 + M2 的非 AI 部分**：把「判卷场」本身做到可信，为后续 AI 阶段提供地基。

### 0.3 关于技术栈的暂定假设（重要）

技术栈尚未在《技术架构文档》中正式拍板。为了让 backlog 的「需要新增或修改的文件」可落地，本文档**暂定**后端为 **Python + FastAPI**，任务编排为单进程同步流水线，持久化用 **SQLite + 本地文件**。

- 这一假设**可在架构文档阶段被推翻**；若更换技术栈，仅需替换各任务中的文件路径，**任务目标 / 输入 / 输出 / 验收标准与技术栈无关**。
- 下方所有 `app/...` 路径均为暂定 Python 包结构占位。

---

## 1. 任务依赖关系

```text
P1-T01 后端骨架与运行约定
  -> P1-T02 任务状态模型与持久化
  -> P1-T03 隔离工作区与执行日志基础设施
        -> P1-T04 Git 仓库导入
              -> P1-T05 Maven 项目识别
                    -> P1-T06 mvn test 执行器
                          -> P1-T07 Surefire 报告解析
                          -> P1-T08 JaCoCo 覆盖率执行与解析
                                -> P1-T09 判卷流水线编排（串联 T04–T08）
                                      -> P1-T10 报告查询接口
                                            -> P1-T11 开源项目端到端验证
```

共 **11 个任务**，串行依赖为主，T07 与 T08 可在 T06 之后并行。

---

## 2. 任务清单

---

### P1-T01　后端骨架与运行约定

1. **任务目标**
   搭起一个可启动的后端服务骨架与统一运行约定，为后续所有任务提供承载（配置、健康检查、统一返回结构、日志格式）。

2. **输入**
   - 无业务输入。
   - 暂定技术栈决策（见 0.3）。

3. **输出**
   - 可启动的 HTTP 服务。
   - `GET /health` 返回服务状态。
   - 统一的配置加载（工作根目录、数据库路径等）。

4. **涉及模块**
   - 平台后端骨架（platform-core）。

5. **需要新增或修改的文件**
   - 新增 `app/main.py`（应用入口）
   - 新增 `app/config.py`（配置：工作区根目录、DB 路径）
   - 新增 `app/api/health.py`（健康检查路由）
   - 新增 `app/common/response.py`（统一返回结构）
   - 新增 `pyproject.toml` / `requirements.txt`
   - 新增 `README.md`（启动说明）

6. **验收标准**
   - 服务可本地启动且不报错。
   - `GET /health` 返回 200 且含服务版本/状态字段。
   - 工作区根目录可通过配置项指定，启动时自动创建。

7. **运行命令**
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   curl http://localhost:8000/health
   ```

8. **不允许做的事**
   - ❌ 不引入前端框架。
   - ❌ 不引入消息队列 / 分布式调度。
   - ❌ 不写任何业务逻辑（导入/执行/解析都不在本任务）。

---

### P1-T02　任务状态模型与持久化

1. **任务目标**
   定义「判卷任务（Job）」的数据模型与状态机，并提供持久化能力，使任务可被创建、查询、更新状态。

2. **输入**
   - P1-T01 的骨架与配置。

3. **输出**
   - Job 实体（id、git_url、branch、commit、状态、各阶段结果引用、时间戳）。
   - 状态机：`CREATED -> IMPORTING -> BUILDING -> PARSING -> DONE / FAILED`。
   - 持久化读写接口。

4. **涉及模块**
   - 任务模型（job-model）、持久化层（storage）。

5. **需要新增或修改的文件**
   - 新增 `app/models/job.py`（Job 实体与状态枚举）
   - 新增 `app/storage/db.py`（SQLite 连接与初始化）
   - 新增 `app/storage/job_repo.py`（增删查改）
   - 新增 `app/storage/schema.sql`（建表语句）

6. **验收标准**
   - 可创建 Job 并落库，重启服务后仍可读出。
   - 状态流转受状态机约束，非法流转被拒绝。
   - 每个 Job 有唯一 id 与创建/更新时间。

7. **运行命令**
   ```bash
   python -m app.storage.db --init        # 初始化数据库
   pytest tests/test_job_repo.py -q
   ```

8. **不允许做的事**
   - ❌ 不做用户/权限/多租户字段。
   - ❌ 不引入 ORM 之外的复杂迁移框架。
   - ❌ 状态机中不出现 Generate/Fix 等 AI 阶段。

---

### P1-T03　隔离工作区与执行日志基础设施

1. **任务目标**
   为每个 Job 提供独立、互不污染的工作目录，并提供统一的执行日志采集与持久化能力（stdout/stderr/退出码/耗时）。

2. **输入**
   - Job id（来自 P1-T02）。

3. **输出**
   - 每个 Job 一个独立工作区目录（如 `workspace/<job_id>/`）。
   - 统一的「执行记录」结构：命令、cwd、退出码、耗时、日志文件路径。
   - 日志落盘并可按 Job 检索。

4. **涉及模块**
   - 工作区管理（workspace）、执行与日志（runner-log）。

5. **需要新增或修改的文件**
   - 新增 `app/runtime/workspace.py`（创建/清理隔离目录）
   - 新增 `app/runtime/executor.py`（子进程执行 + 超时 + 日志捕获）
   - 新增 `app/models/exec_record.py`（执行记录结构）
   - 修改 `app/config.py`（增加 workspace 根目录配置）

6. **验收标准**
   - 两个 Job 的工作区完全隔离，互不读写对方目录。
   - 执行任意命令能正确捕获 stdout、stderr、退出码、耗时。
   - 日志写入文件且能通过 Job id 找回。
   - 命令支持超时，超时被标记为失败而非挂死。

7. **运行命令**
   ```bash
   pytest tests/test_workspace.py tests/test_executor.py -q
   ```

8. **不允许做的事**
   - ❌ 不在宿主机全局目录执行命令（必须在隔离工作区内）。
   - ❌ 不做并发/并行执行调度。
   - ❌ 不对被测项目内容做任何写入式修改（仅在其副本目录内构建产物由 Maven 自行生成）。

---

### P1-T04　Git 仓库导入

1. **任务目标**
   根据 Git 地址与分支，把开源仓库克隆到该 Job 的隔离工作区，并记录当前 commit 与导入状态。

2. **输入**
   - `git_url`、`branch`（可选，默认仓库默认分支）。
   - Job id。

3. **输出**
   - 工作区内的仓库副本。
   - 记录到 Job：实际 commit hash、导入状态（成功/失败）、导入耗时。

4. **涉及模块**
   - 仓库导入（repo-import），依赖 workspace（T03）、job-model（T02）。

5. **需要新增或修改的文件**
   - 新增 `app/importer/git_importer.py`（clone + 读取 commit）
   - 新增 `app/api/jobs.py`（`POST /jobs` 创建并触发导入）
   - 修改 `app/storage/job_repo.py`（写入 commit 与导入状态）

6. **验收标准**
   - 给定合法公开仓库与分支，能成功克隆到隔离工作区。
   - Job 中记录正确的 commit hash。
   - 仓库不存在/分支错误/网络失败时，Job 状态置为 FAILED 并保留错误信息，不崩溃。

7. **运行命令**
   ```bash
   curl -X POST http://localhost:8000/jobs \
     -H "Content-Type: application/json" \
     -d '{"git_url":"https://github.com/<org>/<repo>.git","branch":"main"}'
   ```

8. **不允许做的事**
   - ❌ 不做私有仓库凭据管理 / SSH key 体系（仅公开仓库 https）。
   - ❌ 不修改克隆下来的仓库内容。
   - ❌ 不做 Gradle 或非 Git 来源导入。

---

### P1-T05　Maven 项目识别

1. **任务目标**
   在已导入的仓库中识别 Maven 项目结构，提取构建判卷所需的关键信息（pom、模块结构、源码/测试路径）。

2. **输入**
   - 已导入仓库的工作区路径（来自 T04）。

3. **输出**
   - 是否为 Maven 项目的判定。
   - 单模块 / 多模块判定（多模块仅识别，不强制支持执行）。
   - 关键信息：`pom.xml` 路径、`src/main/java`、`src/test/java`、artifactId/groupId、Java 版本（若可读）。

4. **涉及模块**
   - 项目识别（project-detect）。

5. **需要新增或修改的文件**
   - 新增 `app/detect/maven_detector.py`（定位 pom、解析基础坐标与模块）
   - 新增 `app/models/maven_project.py`（识别结果结构）
   - 修改 `app/api/jobs.py`（`GET /jobs/{id}/project` 返回识别结果）

6. **验收标准**
   - 单模块 Maven 项目能正确识别 pom 与源码/测试路径。
   - 非 Maven 项目能明确返回「不支持」并将 Job 标记失败。
   - 多模块项目能识别出模块列表（即使 Phase 1 仅对根/单模块执行）。

7. **运行命令**
   ```bash
   curl http://localhost:8000/jobs/<job_id>/project
   ```

8. **不允许做的事**
   - ❌ 不解析全部 pom 依赖树/插件细节（仅取判卷必需字段）。
   - ❌ 不为多模块做复杂构建编排。
   - ❌ 不改写 pom.xml（识别为只读操作）。

---

### P1-T06　mvn test 执行器

1. **任务目标**
   在隔离工作区内对识别出的 Maven 项目执行**原始** `mvn test`，捕获构建结果与完整日志。

2. **输入**
   - Maven 项目识别结果（来自 T05）。
   - 工作区路径与执行器（来自 T03）。

3. **输出**
   - 构建退出码与构建状态（成功/失败/编译失败）。
   - 完整 Maven 日志（落盘，关联 Job）。
   - 构建耗时。

4. **涉及模块**
   - 构建执行（build-runner），依赖 executor（T03）。

5. **需要新增或修改的文件**
   - 新增 `app/build/maven_runner.py`（组装并执行 `mvn test`）
   - 修改 `app/models/job.py`（增加构建结果字段引用）
   - 修改 `app/api/jobs.py`（`POST /jobs/{id}/run` 触发执行，或并入流水线 T09）

6. **验收标准**
   - 对原始测试全绿的样板项目，执行后退出码为 0 且状态为成功。
   - 对编译失败/测试失败的项目，能区分「编译失败」与「测试失败」并记录。
   - 完整日志可通过 Job id 取回。
   - 执行在隔离工作区内完成，宿主机其他目录无副作用。

7. **运行命令**
   ```bash
   # 内部等价于在隔离工作区执行：
   mvn -B test
   curl -X POST http://localhost:8000/jobs/<job_id>/run
   ```

8. **不允许做的事**
   - ❌ 不向 `mvn test` 注入任何生成的测试（Phase 1 只跑原始测试）。
   - ❌ 不修改 pom 或测试源码以「让它通过」。
   - ❌ 不做失败重试式修复（Fixer 属后续阶段）。

---

### P1-T07　Surefire 报告解析

1. **任务目标**
   解析 Maven Surefire 生成的测试报告，产出结构化测试结果（用例总数、通过、失败、错误、跳过、失败用例明细）。

2. **输入**
   - `mvn test` 后工作区内的 `target/surefire-reports/*.xml`（来自 T06）。

3. **输出**
   - 结构化结果：total / passed / failed / errors / skipped。
   - 失败用例明细：类名、方法名、失败类型、错误摘要。

4. **涉及模块**
   - 结果解析（surefire-parser）。

5. **需要新增或修改的文件**
   - 新增 `app/report/surefire_parser.py`（解析 XML）
   - 新增 `app/models/test_result.py`（测试结果结构）
   - 修改 `app/storage/job_repo.py`（持久化测试结果引用）

6. **验收标准**
   - 能正确解析多份 surefire XML 并汇总。
   - 通过/失败/错误/跳过数量与 Maven 控制台一致。
   - 失败用例能给出类名+方法名+原因摘要。
   - 无报告目录时返回明确的「无结果」而非崩溃。

7. **运行命令**
   ```bash
   pytest tests/test_surefire_parser.py -q
   curl http://localhost:8000/jobs/<job_id>/report   # 含 surefire 部分
   ```

8. **不允许做的事**
   - ❌ 不对失败做归因分类（Failure Classify 属后续阶段）。
   - ❌ 不做断言质量评估（属后续阶段）。

---

### P1-T08　JaCoCo 覆盖率执行与解析

1. **任务目标**
   采集并解析原始项目的 JaCoCo 覆盖率作为**基线**，产出结构化覆盖率指标（行/分支/方法/类覆盖率）。

2. **输入**
   - 已识别的 Maven 项目（来自 T05）与已执行的测试（来自 T06）。

3. **输出**
   - 覆盖率报告（JaCoCo `jacoco.xml` 或 `jacoco.csv`）。
   - 结构化指标：整体行覆盖率、分支覆盖率、方法/类覆盖率；可按类聚合。

4. **涉及模块**
   - 覆盖率（coverage），依赖 build-runner（T06）。

5. **需要新增或修改的文件**
   - 新增 `app/coverage/jacoco_runner.py`（确保 JaCoCo 生效并执行）
   - 新增 `app/coverage/jacoco_parser.py`（解析 xml/csv）
   - 新增 `app/models/coverage.py`（覆盖率结构）

6. **验收标准**
   - 能产出并解析 JaCoCo 报告，得到整体行/分支覆盖率。
   - 覆盖率数值与 JaCoCo 自身 HTML/CSV 报告一致。
   - 对未配置 JaCoCo 的项目，能采用既定策略（注入 JaCoCo 仅用于度量，不改源码逻辑）或明确报告「无覆盖率」，二者择一并记录。
   - 覆盖率作为「基线」持久化到 Job。

7. **运行命令**
   ```bash
   # 内部等价于：
   mvn -B test    # 含 jacoco prepare-agent / report
   pytest tests/test_jacoco_parser.py -q
   curl http://localhost:8000/jobs/<job_id>/report   # 含 coverage 部分
   ```

8. **不允许做的事**
   - ❌ 不做覆盖率对比/增量（Coverage Compare 属后续 AI 阶段）。
   - ❌ 不修改被测项目的生产代码以提升覆盖率。
   - ❌ 不做 mutation testing。

---

### P1-T09　判卷流水线编排（串联 T04–T08）

1. **任务目标**
   把导入 → 识别 → 执行 → Surefire 解析 → JaCoCo 解析串成一条可一键触发的判卷流水线，并驱动 Job 状态机流转。

2. **输入**
   - `git_url`、`branch`。

3. **输出**
   - 一次完整判卷运行：各阶段状态、产物引用、整体结果。
   - Job 状态按 `IMPORTING -> BUILDING -> PARSING -> DONE/FAILED` 推进。

4. **涉及模块**
   - 流水线编排（pipeline），聚合 T04–T08。

5. **需要新增或修改的文件**
   - 新增 `app/pipeline/judge_pipeline.py`（按序调度各阶段）
   - 修改 `app/api/jobs.py`（`POST /jobs` 一键创建并跑完整流水线）
   - 修改 `app/models/job.py`（记录各阶段执行记录引用）

6. **验收标准**
   - 单次调用即可从 git_url 跑到 Surefire + JaCoCo 解析完成。
   - 任一阶段失败，流水线停止并将 Job 标为 FAILED，保留失败阶段与日志。
   - 各阶段耗时与状态可查询。

7. **运行命令**
   ```bash
   curl -X POST http://localhost:8000/jobs \
     -H "Content-Type: application/json" \
     -d '{"git_url":"https://github.com/<org>/<repo>.git","branch":"main"}'
   curl http://localhost:8000/jobs/<job_id>
   ```

8. **不允许做的事**
   - ❌ 不在流水线中加入 Generate/Fix/Validate 等 AI 阶段。
   - ❌ 不做并发多 Job 调度（顺序执行即可）。
   - ❌ 不做失败自动重试。

---

### P1-T10　报告查询接口

1. **任务目标**
   提供只读报告接口，聚合输出某个 Job 的判卷结果：构建状态、Surefire 结果、JaCoCo 覆盖率基线、各阶段日志入口。

2. **输入**
   - Job id。

3. **输出**
   - 报告 JSON：项目信息、构建结果、测试结果、覆盖率、各阶段状态与日志引用。
   - Job 列表接口（用于自测与端到端验证）。

4. **涉及模块**
   - 报告接口（report-api）。

5. **需要新增或修改的文件**
   - 新增 `app/api/report.py`（`GET /jobs/{id}/report`、`GET /jobs/{id}/logs/{stage}`）
   - 修改 `app/api/jobs.py`（`GET /jobs` 列表）
   - 新增 `app/report/report_assembler.py`（聚合各阶段结果）

6. **验收标准**
   - `GET /jobs/{id}/report` 返回结构化、完整、可机读的判卷报告。
   - 报告含：是否可构建、测试通过/失败统计、覆盖率基线、失败用例摘要、日志入口。
   - 对不存在的 Job 返回 404，对未完成的 Job 返回当前进度而非报错。

7. **运行命令**
   ```bash
   curl http://localhost:8000/jobs
   curl http://localhost:8000/jobs/<job_id>/report
   curl http://localhost:8000/jobs/<job_id>/logs/build
   ```

8. **不允许做的事**
   - ❌ 不做复杂前端可视化（仅 JSON 接口；如需页面，仅一个极简静态页直接渲染 JSON）。
   - ❌ 不做采纳建议/质量门禁判定（属后续 AI 阶段的质量报告）。
   - ❌ 不做导出 PDF/报表等附加形态。

---

### P1-T11　开源项目端到端验证

1. **任务目标**
   选定一个干净的开源 Java Maven 项目，跑通从导入到报告的完整判卷链路，证明判卷场可信、可重复，并归档为黄金样例。

2. **输入**
   - 1 个单模块、依赖干净、原始 `mvn test` 全绿、含可被度量目标类的开源 Maven 项目（git_url + branch）。

3. **输出**
   - 一次完整成功的判卷运行记录。
   - 《选样记录》：选用仓库、commit、JDK/Maven 版本、运行结果快照。
   - 端到端验证清单（逐条对照 Phase 1 八大目标）。

4. **涉及模块**
   - 全链路（pipeline + 所有上游任务）。

5. **需要新增或修改的文件**
   - 新增 `/docs/10_phase1/06_PHASE1_GOLDEN_SAMPLE.md`（选样记录与验证结论）
   - 新增 `tests/e2e/test_phase1_e2e.py`（端到端冒烟用例，可选）
   - 修改 `README.md`（补充端到端复现步骤）

6. **验收标准**
   - 同一仓库连续两次运行结果一致（可重复）。
   - 报告中正确体现：可构建、Surefire 结果、JaCoCo 基线覆盖率。
   - Phase 1 八大目标逐条勾选通过。
   - 全程未修改被测项目源码/测试代码。

7. **运行命令**
   ```bash
   # 一键跑完整链路（以选定的黄金样例为例）
   curl -X POST http://localhost:8000/jobs \
     -H "Content-Type: application/json" \
     -d '{"git_url":"<golden-sample-repo>.git","branch":"<branch>"}'
   curl http://localhost:8000/jobs/<job_id>/report
   pytest tests/e2e/test_phase1_e2e.py -q   # 若实现冒烟用例
   ```

8. **不允许做的事**
   - ❌ 不为「让样例通过」而挑选已被人工补测过的非代表性仓库（应反映真实存量状态）。
   - ❌ 不接入 LLM 做任何生成。
   - ❌ 不修改被测项目以美化结果。

---

## 3. Phase 1 完成定义（DoD）

Phase 1 视为完成，当且仅当：

1. T01–T11 全部通过各自验收标准。
2. 能用至少 1 个开源 Maven 项目端到端跑出：可构建结论 + Surefire 结构化结果 + JaCoCo 基线覆盖率。
3. 任务状态与执行日志可持久化、可查询、可重复。
4. 报告接口对外提供结构化判卷结果。
5. 全程零 LLM、零测试生成、零 Fixer、零复杂前端、零生产代码修改。

> 满足后即进入 Phase 2（目标选择 + 上下文收集 + AI 生成），由后续 backlog 规划。
