# TestAgent Lab — AI 单测生成判卷场

面向开源 Java Maven 项目的 AI 单元测试生成、执行判卷、失败修复与质量治理系统。

> **当前阶段：Phase 1 — 判卷场。** 只做导入/识别/执行/解析/报告，**不接入 LLM、不生成测试、不做 Fixer、不做复杂前端**。
> 详见 [`docs/05_PHASE1_BACKLOG.md`](docs/05_PHASE1_BACKLOG.md)。

## 文档

| 文档 | 作用 |
|---|---|
| [`docs/00_PROJECT_CHARTER.md`](docs/00_PROJECT_CHARTER.md) | 最高约束文件 |
| [`docs/01_PROJECT_PLAN.md`](docs/01_PROJECT_PLAN.md) | 里程碑规划 |
| [`docs/04_ENV_AND_STACK_DECISION.md`](docs/04_ENV_AND_STACK_DECISION.md) | 技术栈决策 + 环境前置 |
| [`docs/05_PHASE1_BACKLOG.md`](docs/05_PHASE1_BACKLOG.md) | Phase 1 任务拆解 |

## 技术栈

Python 3.10+ / FastAPI / SQLite。详见环境决策文档。

## 环境前置（实跑 Phase 1 判卷前必须）

- **Maven**：通过 `mvnw` wrapper / PATH / 或配置 `TESTAGENT_MAVEN_CMD` 指向 `mvn(.cmd)`。
- **JDK**：JaCoCo/JUnit5 需可用 JDK（本机 JDK 17 已验证）。

```powershell
# 若 mvn 不在 PATH，指定可执行文件
$env:TESTAGENT_MAVEN_CMD = "C:\path\to\apache-maven\bin\mvn.cmd"
```

> 仅运行下方骨架（health 接口）不需要 Maven/JDK。
> 注意：若宿主机有会加密落盘文件的 DLP/安全代理，git 克隆出的源码可能被篡改，
> 导致远程仓库无法构建。详见 `docs/06_PHASE1_GOLDEN_SAMPLE.md`。

## 快速开始

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health

# 运行单元/集成测试（快速，无需 Maven）
pytest

# 端到端真实判卷（需要 Maven）
$env:TESTAGENT_MAVEN_CMD = "C:\path\to\mvn.cmd"; $env:TESTAGENT_E2E = "1"
pytest tests/e2e -v

# 对任意开源 Maven 仓库做真实端到端（干净主机）
python -m scripts.run_judge https://github.com/<org>/<repo>.git main
```

## 目录结构

```
app/
├── main.py        # 入口 (P1-T01)
├── config.py      # 配置：workspace / data 目录 (P1-T01)
├── api/           # 路由：health (T01)，jobs/report (T04/T09/T10)
├── common/        # 统一响应体
├── models/        # 领域模型 (T02/T03/T05/T07/T08)
├── storage/       # 持久化 SQLite (T02)
├── runtime/       # 隔离工作区 + 执行器 (T03)
├── importer/      # Git 导入 (T04)
├── detect/        # Maven 识别 (T05)
├── build/         # mvn test 执行 (T06)
├── coverage/      # JaCoCo (T08)
├── report/        # Surefire 解析 + 报告接口 (T07/T10)
└── pipeline/      # 判卷流水线编排 (T09)
```

各模块当前为骨架占位，按 backlog 任务顺序逐步实现。
