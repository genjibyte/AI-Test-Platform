# TestAgent Lab — AI 单测生成判卷场

面向开源 Java Maven 项目的 AI 单元测试生成、执行判卷、失败修复与质量治理系统。

> **当前阶段：Phase 2 已验收 — 最小生成器。** 在 Phase 1 判卷场之上，新增"目标选择 → 有界上下文 →
> LLM 生成 → 写独立测试 → 真实执行 → 覆盖率对比 → 报告"，结论恒为 `NEED_HUMAN_REVIEW`。
> **仍不做 Fixer（Phase 3）、不做质量门禁（Phase 4）、不自动入仓、不改生产代码。**
> Phase 1 见 [`docs/05`](/docs/10_phase1/05_PHASE1_BACKLOG.md)，Phase 2 见 [`docs/09`](/docs/20_phase2/09_PHASE2_BACKLOG.md) 与验收 [`docs/11`](/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md)。

## 文档

| 文档 | 作用 |
|---|---|
| [`/docs/README.md`](/docs/README.md) | 分层文档总索引 |
| [`/docs/00_foundation/00_PROJECT_CHARTER.md`](/docs/00_foundation/00_PROJECT_CHARTER.md) | 最高约束文件 |
| [`/docs/00_foundation/01_PROJECT_PLAN.md`](/docs/00_foundation/01_PROJECT_PLAN.md) | 里程碑规划 |
| [`/docs/00_foundation/04_ENV_AND_STACK_DECISION.md`](/docs/00_foundation/04_ENV_AND_STACK_DECISION.md) | 技术栈决策 + 环境前置 |
| [`/docs/10_phase1/05_PHASE1_BACKLOG.md`](/docs/10_phase1/05_PHASE1_BACKLOG.md) | Phase 1 任务拆解 |
| [`/docs/20_phase2/09_PHASE2_BACKLOG.md`](/docs/20_phase2/09_PHASE2_BACKLOG.md) | Phase 2 任务拆解 |
| [`/docs/20_phase2/10_PHASE2_MIDPHASE_AUDIT.md`](/docs/20_phase2/10_PHASE2_MIDPHASE_AUDIT.md) | Phase 2 中期审计 + 后续规划 |
| [`/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md`](/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md) | Phase 2 验收报告 |

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
> 导致远程仓库无法构建。详见 `/docs/10_phase1/06_PHASE1_GOLDEN_SAMPLE.md`。

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
├── config.py      # 配置：workspace / data / LLM (P1-T01, P2-T03)
├── api/           # 路由：health/jobs/report/context/generation
├── common/        # 统一响应体
├── models/        # 领域模型 (job/coverage/target/context/coverage_delta…)
├── storage/       # 持久化 SQLite (P1-T02, P2-T10 迁移)
├── runtime/       # 隔离工作区 + 执行器 (P1-T03)
├── importer/      # Git 导入 (P1-T04)
├── detect/        # Maven 识别 (P1-T05)
├── build/         # mvn test 执行 (P1-T06)
├── coverage/      # JaCoCo 解析 + 覆盖率对比 (P1-T08, P2-T08)
├── report/        # Surefire 解析 + 判卷/生成报告 (P1-T07/T10, P2-T09)
├── pipeline/      # 判卷流水线 + 生成流水线 (P1-T09, P2-T10)
├── targeting/     # 目标类/方法选择 (P2-T01)
├── context/       # 有界上下文收集 + Java 轻量解析 (P2-T02)
├── llm/           # LLM 隔离层：fake / openai / deepseek (P2-T03)
└── generate/      # prompt / 生成编排 / 写文件 / 执行 (P2-T04..T07)
```

Phase 1（判卷场）与 Phase 2（最小生成器）均已验收。生成流程示例：

```bash
# 1) 导入并判卷一个 Maven 仓库（得到基线覆盖率，Job 进入 DONE）
curl -X POST localhost:8000/jobs -d '{"git_url":"<repo>.git","branch":"main"}'

# 2) 对已判卷 Job 的某个目标类/方法生成测试（默认离线 fake 客户端）
curl -X POST localhost:8000/jobs/<id>/generate -d '{"target_class":"com.example.Calc","target_method":"max"}'

# 3) 查看生成报告（事实 + 覆盖率 delta + patch 预览 + NEED_HUMAN_REVIEW）
curl localhost:8000/jobs/<id>/generation

# 接入真实模型：设置 TESTAGENT_LLM_PROVIDER=openai|deepseek、TESTAGENT_LLM_MODEL、TESTAGENT_LLM_API_KEY
```
