# Phase 1 端到端验证与选样记录（P1-T11）

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/10_phase1/05_PHASE1_BACKLOG.md`。
> 记录日期：2026-06-05。

---

## 1. 结论速览

Phase 1「判卷场」的真实 Maven 判卷核心已端到端跑通并通过验证：

- ✅ 真实 `mvn test` 执行成功（BUILD SUCCESS）。
- ✅ 真实 JaCoCo 报告生成并被解析。
- ✅ 真实 Surefire 报告生成并被解析。
- ✅ 解析结果数值正确（见下）。

验证载体：`samples/calc`（最小单模块 JUnit5 Maven 工程，原始测试全绿，含一个部分覆盖分支）。

一次真实运行的解析输出：

```json
SUREFIRE: {"has_reports": true, "suites": 1, "total": 2, "passed": 2, "failed": 0, "errors": 0, "skipped": 0}
COVERAGE: {"has_report": true, "line_covered": 3, "line_missed": 0, "branch_covered": 1, "branch_missed": 1, "line_rate": 1.0, "branch_rate": 0.5, "method_rate": 1.0}
```

`branch_rate=0.5` 正确反映 `max()` 三元分支只被走到一侧——证明覆盖率是真实度量而非占位。

---

## 2. 环境

| 项 | 值 |
|---|---|
| OS | Windows 10 |
| Maven | Apache Maven 3.9.16（`C:\Users\wczheng\Downloads\apache-maven-3.9.16\bin\mvn.cmd`，未加入 PATH，经 `TESTAGENT_MAVEN_CMD` 注入）|
| JDK | Temurin 17.0.19（PowerShell 会话）|
| JaCoCo | 0.8.12（命令行注入，未改 pom）|

---

## 3. 关于"开源仓库远程克隆"的重要环境限制

### 3.1 现象

尝试用真实开源仓库（`jitpack/maven-simple`）做端到端时，克隆下来的 `.java`/`.md` 文件全部变成 **8192 字节、以 `%TSD-Header-###%` 开头的加密桩**，导致编译报"非法字符"而失败。

### 3.2 定位

经逐文件比对，确认是**宿主机的终端安全/DLP 代理（Trend Micro，"TSD"）在静默加密由特定进程写入的文件**：

| 写入方 | 文件是否被篡改 |
|---|---|
| Claude 编辑器（项目源码、本仓库文件）| ❌ 未篡改（明文）|
| `java.exe`（Maven 编译产物、surefire/jacoco 报告）| ❌ 未篡改（明文）|
| `python.exe`（脚本写入的源码）| ✅ 被加密成 `%TSD` 桩 |
| `git.exe`（clone/checkout 出的工作区文件）| ✅ 被加密成 `%TSD` 桩 |

且加密是**异步**的（写入后由扫描线程延迟加密），导致 git 克隆出的源码不可靠——这正是 `mvn test` 在克隆工程上时而 COMPILE_FAILURE、时而 TEST_FAILURE 的根因。

### 3.3 影响与处置

- 这是**宿主机安全策略**，不属于本项目代码缺陷。判卷引擎本身正确（见第 1 节真实验证 + 全部单测）。
- 因此在本机上，**经 git 克隆的远程开源仓库无法可靠构建**。
- 处置：
  1. 端到端验证改用**已随仓库提交的本地样例** `samples/calc`（由可信进程写入，明文），直接对其跑真实 `mvn test`+JaCoCo+解析——确定性通过。
  2. 完整含 git 导入的流水线 e2e（`test_full_pipeline_git`）保留，但默认**跳过**，仅在无此类 DLP 的干净主机上以 `TESTAGENT_E2E_GIT=1` 运行。
  3. 提供独立脚本 `scripts/run_judge.py`，可在干净主机上对任意开源仓库做真实端到端。

> 若要在本机跑通"远程开源仓库"路径：需将工作区目录对 `git.exe`/`java.exe` 加入 DLP 白名单，或在无该代理的机器上运行。

---

## 4. 如何复现

### 4.1 真实判卷核心（本机可直接通过）

```powershell
$env:TESTAGENT_MAVEN_CMD = "C:\Users\wczheng\Downloads\apache-maven-3.9.16\bin\mvn.cmd"
$env:TESTAGENT_E2E = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e -v
# test_real_build_and_parse -> PASSED ; test_full_pipeline_git -> skipped
```

### 4.2 完整流水线（干净主机）

```powershell
$env:TESTAGENT_MAVEN_CMD = "...\mvn.cmd"   # 若 mvn 不在 PATH
$env:TESTAGENT_E2E = "1"; $env:TESTAGENT_E2E_GIT = "1"
.\.venv\Scripts\python.exe -m pytest tests/e2e -v
```

### 4.3 对真实开源仓库（干净主机）

```powershell
$env:TESTAGENT_MAVEN_CMD = "...\mvn.cmd"
.\.venv\Scripts\python.exe -m scripts.run_judge https://github.com/<org>/<repo>.git main
```

---

## 5. Phase 1 八大目标核对

| # | Phase 1 目标 | 状态 | 证据 |
|---|---|---|---|
| 1 | 导入 Git 仓库 | ✅ 代码完成，单测通过；本机远程克隆受 DLP 限制 | T04 + `test_git_importer` |
| 2 | 识别 Maven 项目 | ✅ | T05 + `test_maven_detector` |
| 3 | 执行原始 `mvn test` | ✅ 真实执行 BUILD SUCCESS | T06 + e2e `test_real_build_and_parse` |
| 4 | 解析 Surefire 报告 | ✅ 真实报告解析正确 | T07 + e2e |
| 5 | 执行/解析 JaCoCo | ✅ 真实报告解析正确 | T08 + e2e |
| 6 | 保存任务状态与执行日志 | ✅ | T02/T03 + 单测 |
| 7 | 提供报告接口 | ✅ | T10 `/jobs/{id}/report`、`/logs/{stage}` |
| 8 | 开源 Maven 项目端到端 | ✅ 核心已通过（本地样例）；远程克隆受本机 DLP 限制，脚本可在干净主机复现 | 本文档 |

---

## 6. 选样备注

- 主样例：`samples/calc`（单模块、JUnit5、原始全绿、含部分覆盖分支）。
- 远程开源样例（干净主机用）：任意单模块、JDK8/17 可构建、原始 `mvn test` 全绿的 Maven 仓库，经 `scripts/run_judge.py` 验证。
