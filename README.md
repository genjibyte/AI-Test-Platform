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

- **Maven**：当前宿主机未安装。T06 起需要 `mvn`（建议优先用目标仓库的 `mvnw` wrapper）。
- **JDK**：当前仅 JDK 8，选黄金样例须挑 JDK 8 可构建的项目。

> 仅运行下方骨架（health 接口）不需要 Maven/JDK。

## 快速开始

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health

# 运行测试
pytest
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
