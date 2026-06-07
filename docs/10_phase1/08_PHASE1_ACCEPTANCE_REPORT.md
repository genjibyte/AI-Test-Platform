# Phase 1 验收报告（判卷场）

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/10_phase1/05_PHASE1_BACKLOG.md`、`/docs/00_foundation/07_SOURCE_NOTES.md`。
> 验收日期：2026-06-05。
> 结论：**Phase 1 通过。判卷场闭环成立，且真实 Maven 判卷核心已用真实工程验证。**
> 本报告不实现任何新功能，仅记录验收证据。

---

## 0. 验收结论速览

| 维度 | 结论 |
|---|---|
| 单元/集成测试 | ✅ 37 passed, 2 skipped |
| 真实 `mvn test` | ✅ BUILD SUCCESS（`samples/calc`）|
| Surefire 真实解析 | ✅ total=2, passed=2 |
| JaCoCo 真实解析 | ✅ line_rate=1.0, branch_rate=0.5 |
| 无 LLM/模型/API 调用 | ✅ 确认 |
| 无 Generator/Fixer Agent | ✅ 确认 |
| 未修改被测生产代码 | ✅ 确认 |

---

## 1. 运行所有测试的精确命令

环境：Windows 10，Python 3.10.11（venv），Maven 3.9.16，JDK 17（Temurin）。

### 1.1 单元 / 集成测试（无需 Maven）

```bash
# bash（仓库根目录）
./.venv/Scripts/python.exe -m pytest -v
```

### 1.2 端到端真实判卷（需要 Maven）

```powershell
# PowerShell（仓库根目录）
$env:TESTAGENT_MAVEN_CMD = "C:\Users\wczheng\Downloads\apache-maven-3.9.16\bin\mvn.cmd"
$env:TESTAGENT_E2E = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e -v
```

### 1.3 完整含 git 导入的流水线 e2e（仅干净主机）

```powershell
$env:TESTAGENT_E2E = "1"; $env:TESTAGENT_E2E_GIT = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e -v
```

---

## 2. 完整 pytest 摘要

```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\AIwork\ai-test-platform-claude
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0
collected 39 items

tests\e2e\test_phase1_e2e.py ss                                          [  5%]
tests\test_executor.py ...                                               [ 12%]
tests\test_git_importer.py ..                                            [ 17%]
tests\test_health.py .                                                   [ 20%]
tests\test_jacoco.py ....                                                [ 30%]
tests\test_job_repo.py ......                                            [ 46%]
tests\test_maven_detector.py ...                                         [ 53%]
tests\test_maven_runner.py .......                                       [ 71%]
tests\test_pipeline.py ..                                                [ 76%]
tests\test_report.py ....                                                [ 87%]
tests\test_surefire_parser.py ...                                        [ 94%]
tests\test_workspace.py ..                                               [100%]

================== 37 passed, 2 skipped, 1 warning in 11.61s ==================
```

> 2 skipped = `tests/e2e`（需 `TESTAGENT_E2E=1` 才运行）。在快速套件中默认跳过。
> 1 warning = starlette TestClient/httpx 的 deprecation（仅测试期，无害）。

---

## 3. E2E 命令与输出摘要

命令（见 1.2）。输出：

```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0
collected 2 items

tests\e2e\test_phase1_e2e.py .s                                          [100%]

======================== 1 passed, 1 skipped in 8.31s =========================
```

- `test_real_build_and_parse` → **PASSED**：对 `samples/calc` 跑真实 `mvn test`+JaCoCo 并解析真实报告。
- `test_full_pipeline_git` → **skipped**：含 git 克隆的完整流水线，需 `TESTAGENT_E2E_GIT=1` 且非文件篡改主机（本机 DLP 会加密 git 落盘文件，详见 `docs/06`）。

---

## 4. 证据：`samples/calc` 跑了真实 `mvn test`

真实运行后在 `samples/calc/target/` 产生的产物（由 `java.exe` 写入，明文）：

```text
samples\calc\target\site\jacoco\jacoco.xml
samples\calc\target\surefire-reports\TEST-com.example.CalcTest.xml
samples\calc\target\jacoco.exec
```

`jacoco.exec` 与 `surefire-reports` 只能由真实 `mvn test` 执行生成 —— 证明执行真实发生，而非伪造。
（`target/` 已在 `.gitignore`，不入库。）

---

## 5. 证据：Surefire XML 被解析

真实 Surefire XML 头（真实 surefire 3.0 schema）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuite xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:noNamespaceSchemaLocation="https://maven.apache.org/surefire/maven-surefire-plugin/xsd/surefire-test-report-3.0.xsd"
  version="3.0" name="com.example.CalcTest" time="0.084"
  tests="2" errors="0" skipped="0" failures="0">
```

平台解析器输出：

```json
SUREFIRE: {"has_reports": true, "suites": 1, "total": 2, "passed": 2,
           "failed": 0, "errors": 0, "skipped": 0, "failed_cases": []}
```

`tests="2"` ↔ 解析 `total=2, passed=2`，一致。

---

## 6. 证据：JaCoCo XML 被解析

真实 `jacoco.xml` 的 report 级总计 counter：

```xml
<counter type="LINE"   missed="0" covered="3"/>
<counter type="BRANCH" missed="1" covered="1"/>
<counter type="METHOD" missed="0" covered="3"/>
```

平台解析器输出：

```json
COVERAGE: {"has_report": true, "line_covered": 3, "line_missed": 0,
           "branch_covered": 1, "branch_missed": 1,
           "method_covered": 3, "method_missed": 0,
           "line_rate": 1.0, "branch_rate": 0.5, "method_rate": 1.0}
```

解析器只取 `<report>` 直接子 counter（总计），数值与真实报告一致。

---

## 7. 覆盖率结果：line_rate 与 branch_rate

| 指标 | 值 | 含义 |
|---|---|---|
| `line_rate` | **1.0** | 3/3 行覆盖 |
| `branch_rate` | **0.5** | `max()` 三元分支仅走到一侧（1/2）|
| `method_rate` | 1.0 | 3/3 方法覆盖 |

`branch_rate=0.5` 证明覆盖率是真实度量而非占位——若为伪造极可能是 1.0。

---

## 8. 确认：不存在任何 LLM / 模型 / API 调用

对 `app/` 全量检索 `openai|anthropic|claude|llm|gpt|langchain|completion|api_key|bearer|prompt` 等关键词，仅命中**注释**（声明"NO LLM"），无任何调用代码：

```text
app\__init__.py:3:Phase 1 scope: 判卷场 (the judging arena). NO LLM, NO test generation,
app\main.py:3:Phase 1 scope: 判卷场 (the judging arena). NO LLM, NO test generation,
app\pipeline\judge_pipeline.py:12:No LLM, no generation, no fixer — Phase 1 is read-only judging.
```

对 `app/` 检索出站网络客户端 `import httpx|import requests|import urllib|aiohttp|socket.|http(s)://`：

```text
No matches found
```

依赖清单 `requirements.txt` 中无任何 LLM SDK；`httpx` 仅为测试依赖（FastAPI TestClient 用），不在 `app/` 中被引用。
唯一的网络行为是 `git clone`（git 子进程）与 Maven 依赖下载（maven 子进程）——属判卷基座，非模型调用。

---

## 9. 确认：不存在 Generator Agent 或 Fixer Agent

- `app/` 中无任何 Generator/Fixer 相关类、模块或调用（检索仅命中 `judge_pipeline.py` 注释 "no generation, no fixer"）。
- 流水线 `app/pipeline/judge_pipeline.py` 固定为：`import -> detect -> mvn test+coverage -> parse`，无生成/修复阶段。
- 模块目录中无 `generator/`、`fixer/`；状态机 `JobStatus` 仅 `CREATED/IMPORTING/BUILDING/PARSING/DONE/FAILED`，无 Generate/Fix 状态。

---

## 10. 确认：未修改被测生产代码

机制保证（代码层面）：

1. 导入只读：`git_importer` 仅 `git clone` 到隔离工作区，从不写回 origin。
2. 执行只读：`mvn test` 在隔离工作区内运行；JaCoCo 经**命令行 plugin 目标注入**（`org.jacoco:...:prepare-agent/report`），**从不修改 pom 或源码**。
3. 平台只向 `workspace/<job>/logs/` 写日志，从不向被测仓库 `src/` 写入。

事实证据：本次真实 e2e 后，`samples/calc` 的源码与 pom **无改动**（`git status` 仅显示 `/docs/00_foundation/07_SOURCE_NOTES.md` 未跟踪；`samples/calc` 下仅新增 `target/`，且 `target/` 已被 gitignore，非源码）。

---

## 11. 当前限制

1. **本机远程开源仓库不可靠**：宿主机 Trend Micro DLP 代理会异步加密 `git.exe`/`python.exe` 落盘文件（替换为 `%TSD-Header` 桩），导致 git 克隆出的源码无法编译。详见 `docs/06`。真实 OSS 端到端需在无此代理的主机用 `scripts/run_judge.py` 运行。
2. **Maven 未入 PATH**：经 `TESTAGENT_MAVEN_CMD` 注入，平台已支持；但需手动配置。
3. **多模块仅识别不强制执行**：Phase 1 对多模块项目只识别，执行以根模块为主。
4. **任务执行为同步单进程**：无并发/队列（符合 Charter 禁止项）。
5. **报告止于事实**：不输出采纳建议/质量门禁（属后续 Phase 4）。
6. **schema 无自动迁移**：列变更需重建本地 `var/` 开发库（dev-only，已 gitignore）。
7. **e2e 黄金样例为本地 fixture**：`samples/calc`；远程开源样例验证待干净主机补充。

---

## 12. Phase 2 进入检查单

> 满足以下全部项方可进入 Phase 2（最小 Generator）。当前状态如下。

| # | 检查项 | 状态 |
|---|---|---|
| 1 | Phase 1 判卷闭环跑通（import→detect→test→parse→report）| ✅ |
| 2 | 真实 `mvn test` 可执行并判定结果 | ✅ |
| 3 | Surefire 真实解析正确 | ✅ |
| 4 | JaCoCo 真实解析正确（含 line/branch）| ✅ |
| 5 | 任务状态与执行日志可持久化、可查询 | ✅ |
| 6 | 报告接口对外提供结构化结果 | ✅ |
| 7 | 全程零 LLM、零生成、零 Fixer、零生产代码修改 | ✅ |
| 8 | 单元/集成测试全绿 | ✅（37 passed）|
| 9 | 远程开源仓库真实端到端（干净主机）| ⏳ 待干净主机用 `scripts/run_judge.py` 补充 |
| 10 | Phase 2 范围与红线已在 `docs/07` 第 5 节锚定 | ✅ |

Phase 2 起允许：目标类/方法选择、有界上下文收集、独立 `*AiGeneratedTest.java` 生成、执行生成测试、覆盖率对比。
仍禁止：修改生产代码、修改既有测试、自动合并、复杂 RAG。

> **本报告不启动 Phase 2。** 进入 Phase 2 需显式指令。

---

## 附录 A：项目结构（tree, 深度 4）

```text
ai-test-platform/
├── app/
│   ├── api/            health.py  jobs.py  report.py
│   ├── build/          maven_runner.py
│   ├── common/         response.py
│   ├── coverage/       jacoco_parser.py  jacoco_runner.py
│   ├── detect/         maven_detector.py
│   ├── importer/       git_importer.py
│   ├── models/         job.py  exec_record.py  maven_project.py  test_result.py  coverage.py
│   ├── pipeline/       judge_pipeline.py
│   ├── report/         surefire_parser.py  report_assembler.py
│   ├── runtime/        workspace.py  executor.py
│   ├── storage/        db.py  job_repo.py  schema.sql
│   ├── config.py
│   └── main.py
├── docs/
│   ├── 00_PROJECT_CHARTER.md
│   ├── 01_PROJECT_PLAN.md
│   ├── 04_ENV_AND_STACK_DECISION.md
│   ├── 05_PHASE1_BACKLOG.md
│   ├── 06_PHASE1_GOLDEN_SAMPLE.md
│   ├── 07_SOURCE_NOTES.md
│   └── 08_PHASE1_ACCEPTANCE_REPORT.md
├── samples/
│   └── calc/           pom.xml  src/main/...  src/test/...  README.md
├── scripts/            run_judge.py
├── tests/
│   ├── e2e/            test_phase1_e2e.py
│   └── test_*.py       (executor, git_importer, health, jacoco, job_repo,
│                        maven_detector, maven_runner, pipeline, report,
│                        surefire_parser, workspace)
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

## 附录 B：git status

```text
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	/docs/00_foundation/07_SOURCE_NOTES.md

nothing added to commit but untracked files present
```

> 仅 `/docs/00_foundation/07_SOURCE_NOTES.md` 未跟踪（工程知识文件，本次新增）。
> 无任何 `app/` 或 `samples/` 源码改动 → 印证第 10 节。

## 附录 C：git log --format=fuller -1

```text
commit 0d486d532e234c47609d0aacf5bfb964e416118a
Author:     genjibyte <wenchaozheng2@gmail.com>
AuthorDate: Fri Jun 5 22:04:44 2026 +0800
Commit:     genjibyte <wenchaozheng2@gmail.com>
CommitDate: Fri Jun 5 22:04:44 2026 +0800

    feat(T11): real-Maven end-to-end + judge script + golden sample doc
    ...
```

> 作者与提交者均为 genjibyte，无 Claude 署名。
