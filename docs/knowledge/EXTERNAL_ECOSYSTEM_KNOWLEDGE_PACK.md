<!-- INGESTED 2026-06-17 into docs/knowledge/. This is an EXTERNAL research pack
(reference / roadmap), not proof of implementation. Read the reconciliation note
below before treating any "建议新增/Slice" as undone work — several pillars already
exist. The binding strategic reading lives in AGENTS.md plus the active docs:
docs/WORK_LOG.md, docs/README.md, docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md,
and docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md. -->

> **Reconciliation with current state (2026-07-06) — read first.** This pack predates
> some work it lists as "to do". Already built on `main` (do NOT re-build):
> - **Candidate / Submission entry (pack Slice A / §2.1)** → `submit_candidate` is live:
>   `app/api/submit_candidate.py` + `app/pipeline/submit_pipeline.py` (docs/53 S1). Any
>   producer's JUnit source is judged by the same kernel; `conclusion` stays
>   `NEED_HUMAN_REVIEW`. (Pack's richer Candidate JSON — `kind`, `grounding.business_oracle_source`
>   — is a future schema extension, not missing core.)
> - **Provenance (pack Slice B / §2.1)** → `producer_id` + `run_kind="external"` (docs/53 S2);
>   the charter invariant "external never enters the real headline" is test-pinned. (Full
>   side-by-side multi-author *compare report* is still future.)
> - **Badcase ledger (pack Slice C / §2.3)** → `app/ledger/` (P1/P2) + retrieval
>   `app/ledger/retrieval.py` (docs/50). (Pack's richer `failure_type` taxonomy +
>   `repair_hint`/`do_not_repeat_rule` are future enrichments.)
> - **PIT mutation (pack Slice E / §4.3)** → `app/mutation/` exists, **gated off** by default
>   (docs/46); survived-mutant classification = docs/49. Don't "add PIT"; it's there.
> - **Other judge signals already live:** quality gate (`app/quality/test_quality_gate.py`),
>   structural oracle-strength (docs/46), mock/external-dependency smells (docs/51),
>   invariant verification (docs/48), review digest (docs/52).
> - **Asset Gate + Test-Level Router (pack Slice D / §2.2)** → Asset Gate S1-S4A is live:
>   `review_summary["asset_sufficiency"]`, tiny `asset_facts`, digest flags, compact benchmark/
>   ledger carry, descriptive breakdowns, benchmark markdown, and report-only
>   `review_summary["test_level_router"]`. Do not rebuild it; audit/harden it.
>
> **Still not built:** interface/API candidate execution, new candidate kinds,
> Defects4J, multi-model experiments, LLM Judge scoring, complex RAG, large MCP/web backend,
> and any auto-adoption flow. All remain design-first, advisory, owner-gated, and report-first.
>
> ---

# AI-Test-Platform 外部生态与测试资产调研知识包（给 Coding Agent）

> 生成日期：2026-06-17  
> 适用仓库：https://github.com/genjibyte/AI-Test-Platform  
> 目的：为后续 Coding Agent 提供“可接入外部产品 / 库 / 文章 / 模块 / 开源测试资产 / badcase 数据源”的研究总结。  
> 执行原则：本文件是**知识包与路线建议**，不是一次性实现清单。Coding Agent 不应一次性接入所有工具；应按“核心判卷能力优先、外部工具轻接入”的路线逐步推进。

---

## 0. 当前项目理解

### 0.1 项目当前定位

TestAgent Lab 当前是一个面向 Java Maven 项目的 **AI 单测生成判卷场**。当前 README 描述为：Phase 2 已验收，已有“目标选择 → 有界上下文 → LLM 生成 → 写独立测试 → 真实执行 → 覆盖率对比 → 报告”，且结论恒为 `NEED_HUMAN_REVIEW`，不做自动入仓、不改生产代码、不做自动 accept/reject。

当前项目已具备的核心模块大致为：

```text
app/
├── api/          # health / jobs / report / context / generation 等接口
├── models/       # job / coverage / target / context / delta 等领域模型
├── storage/      # SQLite job 持久化
├── runtime/      # workspace 隔离
├── importer/     # Git 导入
├── detect/       # Maven 识别
├── build/        # mvn test 执行
├── coverage/     # JaCoCo 解析 + 覆盖率对比
├── report/       # Surefire 解析 + 生成报告
├── pipeline/     # 判卷流水线 + 生成流水线
├── targeting/    # 目标类/方法选择
├── context/      # 有界上下文收集
├── llm/          # fake / openai / deepseek 隔离层
└── generate/     # prompt / 生成编排 / 写文件 / 执行
```

### 0.2 当前最重要的重定位

仓库内部已有 `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md`，其核心结论是：

```text
生成器 = producer
判卷内核 = 产品
```

真正该扩展的不是“把自家生成器调得更好”，而是让平台可以判卷**任意来源的候选测试**：

```text
人写的测试
本平台生成器写的测试
Claude Code / Copilot / Codex 写的测试
Coze / Dify workflow 生产的测试场景或测试代码
EvoSuite / Randoop / Schemathesis 等传统工具生成的测试
```

统一进入：

```text
Candidate -> 隔离写入 -> preflight -> 真实执行 -> 覆盖率 / 断言 / mutation / asset gate -> review summary -> badcase ledger
```

### 0.3 现在最应该避免的漂移

不要把项目做成：

```text
大型 Coze/Dify workflow 套壳
大厂智能单测平台低配版
只追求 AI 生成通过率的 prompt 项目
一口气堆 API/UI/性能/安全/报表/K8s 全家桶
```

更合理的目标是：

```text
少资产场景下的 AI 测试候选物判卷平台：
先判断资产够不够，再决定生成哪层测试，再真实执行与判卷，最后沉淀 badcase。
```

---

## 1. 面向 Coding Agent 的总路线

### 1.1 北极星指标

每个新功能先问：

```text
这个功能是否增强“任意来源候选测试”的管理、判卷、比较、沉淀？
```

如果只是“让本平台自己的 LLM 生成器更容易 pass”，除非涉及 oracle safety / 判卷红线，否则降级。

### 1.2 推荐路线

```text
P0. Candidate / Submission 标准入口
P1. Provenance + 按作者比较 + badcase ledger
P2. Asset Sufficiency Gate + Test Level Router
P3. PIT mutation 轻量判卷增强
P4. API Test Harness（YAML/JSON 用例执行）
P5. Schemathesis / Newman / Testcontainers / WireMock 作为 API 生态接入
P6. Coze / Dify / Claude Code 作为外部 producer 轻接入
P7. UI / 性能 / 安全 / ReportPortal / Testkube 等后置扩展
```

### 1.3 不建议立即做的事

```text
不建议立即接入 Coze/Dify 做核心流程
不建议立即上 LangGraph 重写 pipeline
不建议立即做 IDE 插件
不建议立即做自动入仓 / PR 创建
不建议立即做多语言 / Gradle / Bazel
不建议立即做 K8s / Testkube
不建议立即做全量 mutation testing
```

---

## 2. 推荐新增核心抽象

### 2.1 Candidate / Submission

建议先定义来源无关的候选测试：

```json
{
  "target": {
    "job_id": "string",
    "target_class": "com.example.Calc",
    "target_method": "max",
    "test_level": "unit"
  },
  "candidate": {
    "kind": "junit_source",
    "content": "完整 JUnit 源码",
    "filename_hint": "CalcAiGeneratedTest.java"
  },
  "provenance": {
    "author_type": "human | platform_generator | external_agent | coze | dify | evosuite | randoop | schemathesis",
    "author_id": "string",
    "model": "optional",
    "prompt_version": "optional",
    "tool_version": "optional",
    "notes": "optional"
  },
  "grounding": {
    "business_oracle_source": "none | code | existing_test | prd | openapi | human | historical_bug",
    "assets_used": []
  }
}
```

### 2.2 Asset Sufficiency Report

每次候选测试判卷后，报告里应明确资产是否足够：

```json
{
  "asset_sufficiency": {
    "code_context": "sufficient | partial | missing",
    "existing_tests": "sufficient | partial | missing",
    "business_oracle": "sufficient | partial | missing",
    "test_data": "sufficient | partial | missing",
    "api_schema": "sufficient | partial | missing",
    "db_schema": "sufficient | partial | missing",
    "external_dependency_mock": "sufficient | partial | missing"
  },
  "test_level_recommendation": "unit | api | integration | ui | manual_oracle_first",
  "missing_assets": [],
  "risk_notes": []
}
```

### 2.3 Badcase Ledger

建议将失败沉淀为可检索记录：

```json
{
  "candidate_id": "...",
  "target_fingerprint": "...",
  "author_type": "external_agent",
  "failure_type": "COMPILE_FAILURE | TEST_FAILURE | WEAK_ASSERTION | MISSING_ORACLE | MISSING_FIXTURE | MOCK_HALLUCINATION | FLAKY | COVERAGE_NO_SIGNAL",
  "evidence": {
    "compiler_error": "...",
    "surefire_failure": "...",
    "quality_gate_findings": []
  },
  "repair_hint": "optional",
  "do_not_repeat_rule": "optional",
  "created_at": "..."
}
```

---

## 3. 工具 / 产品 / 开源库总览

### 3.1 当前最值得接入的前五个

| 优先级 | 工具 | 作用 | 推荐接入方式 |
|---|---|---|---|
| P0 | PIT / Pitest | mutation testing，判断 AI 测试是否只是覆盖代码但断言弱 | 目标类小范围 mutation gate |
| P0 | Candidate API | 不是外部工具，是项目核心抽象 | `POST /jobs/{id}/candidates` |
| P1 | Langfuse 或 Phoenix | LLM trace、prompt、model、token、latency、candidate 关联 | `app/llm/tracing.py` |
| P2 | Schemathesis | OpenAPI / GraphQL schema-based API 测试生成和执行 | API producer / executor |
| P2 | Testcontainers + WireMock | 提供真实 DB / Redis / MQ 容器与外部 HTTP mock | API / integration harness 环境层 |

---

## 4. 单测 / 白盒判卷生态

### 4.1 JaCoCo

- 类型：Java 覆盖率库
- 当前项目已使用或已兼容其报告概念。
- 用途：
  - 行覆盖、分支覆盖、方法覆盖
  - before/after coverage delta
  - 目标类覆盖率变化
- 注意：
  - 覆盖率不是 oracle，不代表测试有效。
  - 只能作为 advisory signal。

来源：
- https://www.eclemma.org/jacoco/
- https://github.com/jacoco/jacoco

### 4.2 Maven Surefire

- 类型：Maven 单测执行与测试报告生成插件
- 当前项目已解析 `target/surefire-reports/TEST-*.xml`。
- 用途：
  - 判断编译 / 执行 / 失败测试
  - 提供 JUnit XML 作为统一测试结果格式

来源：
- https://maven.apache.org/surefire/maven-surefire-plugin/
- https://maven.apache.org/surefire/maven-surefire-report-plugin/

### 4.3 PIT / Pitest

- 类型：Java mutation testing
- 推荐优先级：高
- 价值：
  - 解决“覆盖率高但断言弱”的问题
  - 对 AI 生成测试尤其重要，因为 AI 常生成“跑过即可”的测试
  - 可作为 `oracle_strength` 的一个强信号
- 接入建议：
  - 不要全仓库跑，太慢。
  - 只对目标类或目标包跑。
  - 只在候选测试 `PASS` 后可选运行。
  - 输出：
    - `mutation_score`
    - `killed_mutants`
    - `survived_mutants`
    - `no_coverage_mutants`
    - `mutation_timeout`
- 建议模块：
  - `app/mutation/pitest_runner.py`
  - `app/mutation/pitest_parser.py`
  - `app/quality/mutation_gate.py`

来源：
- https://pitest.org/
- https://github.com/hcoles/pitest

### 4.4 EvoSuite

- 类型：传统自动 JUnit 测试生成工具
- 价值：
  - 可作为非 LLM producer baseline
  - 适合比较“传统覆盖率导向工具 vs LLM 生成测试”
  - EvoSuite 会自动添加 regression assertions，这正好可以作为“复制当前实现”的讨论对象
- 接入建议：
  - 不是主线。
  - 后续作为 `provenance.author_type = evosuite` 的 Candidate producer。
  - 不要让 EvoSuite 产物自动入仓，只提交给平台判卷。

来源：
- https://github.com/EvoSuite/evosuite
- https://www.evosuite.org/

### 4.5 Randoop

- 类型：Java random / feedback-directed unit test generator
- 价值：
  - 作为传统工具 baseline
  - 适合证明“生成大量测试不等于业务 oracle 可信”
- 接入建议：
  - 可后置接入为 producer。
  - 重点比较：
    - 编译通过率
    - 覆盖率
    - mutation score
    - weak assertion / business oracle 缺失率

来源：
- https://randoop.github.io/randoop/
- https://github.com/randoop/randoop

### 4.6 JQF + Zest

- 类型：Java coverage-guided fuzzing / property-based testing
- 价值：
  - 可探索“属性测试 + AI 生成 property”的方向
  - 适合工具类、parser、compiler、序列化、格式转换等目标
- 接入建议：
  - 后置研究型模块，不进入近期主线。
  - 可作为“AI 生成 property，JQF 负责 fuzz”的 producer/executor 组合。

来源：
- https://github.com/rohanpadhye/jqf

### 4.7 Diffblue Cover / Diffblue Testing Agent

- 类型：商业 AI Java 单测生成产品
- 价值：
  - 可作为行业产品参考，不建议直接依赖。
  - 它强调“生成只是开始，验证是瓶颈”，和本项目“判卷内核 = 产品”一致。
- 接入建议：
  - 不接入代码。
  - 用作 README / 研究报告里的行业对标。

来源：
- https://www.diffblue.com/

---

## 5. API / 接口测试生态

### 5.1 Schemathesis

- 类型：OpenAPI / GraphQL property-based API testing
- 推荐优先级：高
- 价值：
  - 很适合“少资产场景”：只要有 OpenAPI schema，就能自动生成探索性接口测试。
  - 可生成大量边界、异常、schema mismatch 测试。
  - 适合作为 API candidate producer。
- 接入建议：
  - 先不要自己写复杂参数生成。
  - `api_schema -> schemathesis run -> parse results -> TestAgent report`
  - 记录：
    - 触发 5xx 的输入
    - schema violation
    - replay command
    - endpoint coverage
- 建议模块：
  - `app/api_test/schemathesis_runner.py`
  - `app/api_test/schemathesis_parser.py`
  - `app/models/api_candidate.py`

来源：
- https://github.com/schemathesis/schemathesis
- https://schemathesis.io/
- https://schemathesis.readthedocs.io/

### 5.2 EvoMaster

- 类型：REST / GraphQL / RPC API 自动测试生成与 fuzzing
- 价值：
  - 比 Schemathesis 更偏系统级 / 白盒 + 黑盒搜索。
  - 支持 JVM SUT，和 Java 项目契合。
  - 有学术 benchmark 生态 EMB。
- 接入建议：
  - 不作为近期 P0。
  - 中期可作为对比 producer：`author_type = evomaster`
  - 可以学习它的 benchmark 设计与 SUT 驱动方式。

来源：
- https://github.com/WebFuzzing/evomaster
- https://github.com/aster-test-generation/EMB

### 5.3 Newman / Postman Collection

- 类型：Postman Collection CLI runner
- 价值：
  - 企业常见接口测试资产格式。
  - 很多团队已有 Postman collection。
  - TestAgent 支持它会显得更落地。
- 接入建议：
  - 中期支持 `postman_collection.json` 作为 API Candidate。
  - 执行结果转成平台统一 report。
  - 不要把 Postman collection 当核心存储格式；它只是输入格式之一。
- 建议模块：
  - `app/api_test/newman_runner.py`
  - `app/api_test/postman_parser.py`

来源：
- https://github.com/postmanlabs/newman
- https://learning.postman.com/docs/reference/newman-cli/command-line-integration-with-newman/

### 5.4 Karate

- 类型：API testing / mock / performance / UI automation 一体化框架
- 价值：
  - Java 生态友好。
  - DSL 对 API 测试表达清晰。
  - 可同时覆盖 API、mock、性能、UI。
- 接入建议：
  - 不建议近期作为核心 API Harness，因为会引入 DSL 学习成本。
  - 可作为中后期 “导出 Karate feature” 或 “执行 Karate candidate” 的适配器。

来源：
- https://github.com/karatelabs/karate
- https://docs.karatelabs.io/extensions/examples-and-demos

### 5.5 Testcontainers

- 类型：用 Docker 启动真实数据库、消息队列、浏览器等依赖
- 推荐优先级：中高
- 价值：
  - 解决接口测试最大痛点之一：没有稳定测试数据和环境。
  - 比 H2 / fake DB 更接近生产依赖。
- 接入建议：
  - 在 API Harness 后接入。
  - 先支持 MySQL / PostgreSQL / Redis 三类。
  - 不要一开始要求所有目标项目都容器化。
- 建议模块：
  - `app/env/docker_env.py`
  - `app/env/testcontainers_plan.py`
  - `app/assets/fixture_manifest.py`

来源：
- https://testcontainers.com/
- https://testcontainers.com/guides/introducing-testcontainers/
- https://java.testcontainers.org/modules/databases/

### 5.6 WireMock

- 类型：HTTP API mock / service virtualization
- 推荐优先级：中高
- 价值：
  - 解决短信、支付、地图、第三方服务等外部依赖问题。
  - 能制造边界和异常响应。
- 接入建议：
  - 作为 `external_dependency_mock` 资产的一种。
  - Asset Gate 发现外部依赖时，提示需要 mock。
  - 后续可以让 AI 生成 WireMock stubs，但必须人审。
- 建议模块：
  - `app/mock/wiremock_runner.py`
  - `app/mock/stub_manifest.py`

来源：
- https://wiremock.org/
- https://github.com/wiremock/wiremock

### 5.7 MockServer

- 类型：HTTP/HTTPS mock server
- 价值：
  - 和 WireMock 类似。
  - 当前版本还支持 LLM / AI API mocking，可用于模拟 OpenAI / Anthropic / Gemini 等接口。
- 接入建议：
  - 二选一即可；不建议 WireMock 和 MockServer 同时进入近期主线。
  - 如果你要 mock LLM API，MockServer 有额外价值。
- 来源：
  - https://www.mock-server.com/
  - https://github.com/mock-server/mockserver-monorepo

### 5.8 Pact

- 类型：consumer-driven contract testing
- 价值：
  - 微服务契约测试，避免昂贵且脆弱的 E2E。
  - 对接口资产化很有价值。
- 接入建议：
  - 后置。
  - 等 API Harness 稳定后，再考虑 Pact contract 作为 `api_contract_asset` 输入。
- 来源：
  - https://github.com/pact-foundation

---

## 6. UI / GUI 测试生态

### 6.1 Playwright

- 类型：Web E2E automation
- 推荐优先级：后置中高
- 价值：
  - Web UI 自动化主流工具。
  - 支持 Python / Java / Node / .NET。
  - 官方也强调可用于 testing、scripting、AI agent workflows。
- 接入建议：
  - 不进近期主线。
  - 等 API Harness 稳定后，可新增 `UiCandidate`：
    - `script_type = playwright_python`
    - 执行截图、trace、video、DOM snapshot
    - 结果进入统一判卷。
- 来源：
  - https://playwright.dev/
  - https://github.com/microsoft/playwright

### 6.2 Selenium

- 类型：经典浏览器自动化
- 价值：
  - 行业覆盖广。
  - 适合作为兼容知识，但新项目优先 Playwright。
- 接入建议：
  - 不作为近期接入目标。
- 来源：
  - https://www.selenium.dev/

### 6.3 Appium

- 类型：移动端 / 桌面 / IoT UI 自动化
- 价值：
  - 若后续扩展移动端 UI 自动化，可作为执行适配器。
- 接入建议：
  - 与你当前 Java Maven 单测/API 平台距离较远，后置。
- 来源：
  - https://appium.io/
  - https://github.com/appium/appium

### 6.4 AUITestAgent / KuiTest / Meituan UI Agent 思路

- 类型：自然语言驱动 GUI 测试 / 多模态 UI 验证
- 价值：
  - 作为研究参考。
  - 核心思想不是脚本生成，而是“交互轨迹 + Oracle 验证 + 人类预期”。
- 接入建议：
  - 不直接接入。
  - 后续做 UI Agent 时，可借鉴：
    - 需求拆解
    - GUI 信息抽取
    - 交互后验证
    - 轨迹归因
    - 执行失败是 agent 问题还是系统缺陷的问题
- 来源：
  - https://github.com/bz-lab/AUITestAgent
  - https://arxiv.org/abs/2407.09018

---

## 7. 性能 / 安全 / 静态分析生态

### 7.1 Locust

- 类型：Python load testing
- 价值：
  - 和项目 Python 栈契合。
  - 接口测试稳定后，可从 API case 生成简单 Locust load scenario。
- 接入建议：
  - 后置。
  - 只做“小流量性能烟测”，不要做完整压测平台。
- 来源：
  - https://github.com/locustio/locust
  - https://locust.io/

### 7.2 k6

- 类型：现代 load testing
- 价值：
  - 工业常用，生态好。
  - JavaScript 脚本，和 API 场景可转换。
- 接入建议：
  - 和 Locust 二选一。
  - 如果项目主栈 Python，优先 Locust；如果考虑企业展示，k6 也有价值。
- 来源：
  - https://github.com/grafana/k6
  - https://grafana.com/oss/k6/

### 7.3 OWASP ZAP

- 类型：Web/API 安全扫描自动化
- 价值：
  - 可作为 `SecurityCandidate` 后置扩展。
  - 对 API / Web 安全 smoke test 有用。
- 接入建议：
  - 后置，不进入当前主线。
  - 可支持 ZAP Automation Framework YAML plan 作为候选输入。
- 来源：
  - https://www.zaproxy.org/docs/automate/automation-framework/
  - https://www.zaproxy.org/docs/desktop/addons/automation-framework/

### 7.4 Semgrep

- 类型：静态分析 / SAST / bug pattern
- 价值：
  - 可扫描 AI 生成测试中的坏味道或生产代码风险。
  - 可构建少量自定义规则：例如禁止测试触碰外部网络、禁止 Thread.sleep 过长、禁止随机无种子。
- 接入建议：
  - 只作为质量门的辅助，不作为真实正确性判定。
- 来源：
  - https://github.com/semgrep/semgrep
  - https://github.com/semgrep/semgrep-rules

---

## 8. LLMOps / Agent 生态

### 8.1 Langfuse

- 类型：LLM observability / prompt / trace / eval
- 推荐优先级：中高
- 价值：
  - 记录每个 candidate 的 prompt、model、latency、token、cost。
  - 支持后续按模型 / prompt 版本对比。
  - 对 debug AI 生成失败非常有用。
- 接入建议：
  - 不改变判卷逻辑。
  - 只在 `app/llm/` 外包一层 tracing。
  - 记录 `job_id`、`candidate_id`、`provenance`。
- 来源：
  - https://github.com/langfuse/langfuse
  - https://langfuse.com/docs

### 8.2 Arize Phoenix

- 类型：AI observability & evaluation
- 价值：
  - tracing、eval、datasets、experiments。
  - 可替代或对比 Langfuse。
- 接入建议：
  - Langfuse / Phoenix 二选一即可。
  - 不建议同时接。
- 来源：
  - https://github.com/arize-ai/phoenix
  - https://arize.com/phoenix/

### 8.3 DeepEval

- 类型：LLM app evaluation framework
- 价值：
  - 可评估“测试场景生成”这类自然语言输出。
  - 类似 pytest，但用于 LLM apps。
- 接入建议：
  - 后续做 RAG / 场景生成时使用。
  - 不替代 Maven/JUnit/API 真实执行判卷。
- 来源：
  - https://github.com/confident-ai/deepeval
  - https://deepeval.com/

### 8.4 Ragas

- 类型：RAG evaluation
- 价值：
  - 如果后续做业务知识 RAG，可评估 retrieval / groundedness / faithfulness。
- 接入建议：
  - 后置。
  - 仅评估“知识召回是否支撑场景生成”，不用于直接判断测试是否通过。
- 来源：
  - https://docs.ragas.io/en/stable/
  - https://github.com/vibrantlabsai/ragas

### 8.5 Coze Studio

- 类型：AI Agent 开发平台 / 可视化编排
- 价值：
  - 可作为外部 producer：
    - 输入 PRD / 业务规则 / 历史 bug
    - 输出测试场景 / candidate JSON
  - 演示价值高。
- 接入建议：
  - 不作为平台底座。
  - 最后做轻接入：Coze webhook / 手动复制 JSON 到 Candidate API。
- 来源：
  - https://github.com/coze-dev/coze-studio
  - https://www.coze.com/

### 8.6 Dify

- 类型：LLM app development / workflow / RAG / agent
- 价值：
  - 可管理 PRD、接口文档、历史 bug，生成结构化测试场景。
  - 可做“资产收集前台”。
- 接入建议：
  - 不作为核心判卷系统。
  - 后期作为 external producer。
- 来源：
  - https://github.com/langgenius/dify
  - https://dify.ai/

### 8.7 LangGraph

- 类型：stateful agent orchestration
- 价值：
  - 如果后续出现复杂多 agent 流程，可用它编排。
- 接入建议：
  - 现在不迁移。
  - 当前 Python pipeline 足够。
  - 等模块稳定后再考虑：
    - AssetProfiler
    - TestLevelRouter
    - Generator
    - Executor
    - Judge
    - Memory
- 来源：
  - https://github.com/langchain-ai/langgraph
  - https://docs.langchain.com/oss/python/langgraph/overview

### 8.8 Claude Code / Copilot / Codex

- 类型：外部 agentic coding producer
- 价值：
  - 让平台能够评测真实 coding agent 生成的测试。
  - 适合演示“平台不是自家生成器自嗨，而是外部 agent 的裁判”。
- 接入建议：
  - 不需要 API 深集成。
  - 只要允许它们生成测试文件，再通过 Candidate API 提交。
  - `provenance.author_type = external_agent`
  - `author_id = claude_code | copilot | codex`
- 参考：
  - Claude Code 官方文档 / GitHub 生态
  - GitHub Copilot 测试生成文档

---

## 9. 报告 / 平台化 / CI 生态

### 9.1 Allure Report

- 类型：测试报告展示
- 价值：
  - 将平台 JSON 报告转换为更好看的 HTML。
  - 适合 demo。
- 接入建议：
  - 不替代当前 report JSON。
  - 后置导出：
    - `allure-results/`
    - `allure-report/`
- 来源：
  - https://allurereport.org/
  - https://allurereport.org/docs/

### 9.2 ReportPortal

- 类型：开源测试自动化 dashboard
- 价值：
  - 测试结果趋势、失败聚类、协作面板。
  - 适合企业级展示。
- 接入建议：
  - 后置，作为结果 sink。
  - 不作为项目核心存储。
- 来源：
  - https://github.com/reportportal
  - https://reportportal.io/

### 9.3 Testkube

- 类型：Kubernetes-native test orchestration
- 价值：
  - 如果后续要多环境/K8s 运行测试，可参考。
- 接入建议：
  - 当前不要做。
  - 项目未到 K8s 编排阶段。
- 来源：
  - https://github.com/kubeshop/testkube

### 9.4 GitHub Actions Test Reporters

- 类型：CI 测试报告展示
- 价值：
  - 可以展示 JUnit XML 到 PR check。
- 接入建议：
  - 后置。
  - 如果项目要推 GitHub demo，可把平台自身测试结果展示到 Actions。
- 来源：
  - https://github.com/marketplace/actions/junit-report-action
  - https://github.com/marketplace/actions/test-reporter

### 9.5 OpenTelemetry

- 类型：通用可观测性标准
- 价值：
  - 若后续 API 测试要看链路日志、trace、服务调用，可以作为标准格式。
- 接入建议：
  - 暂不实现。
  - 后续可以把 API 测试执行和 LLM 调用都抽象成 spans。
- 来源：
  - https://opentelemetry.io/
  - https://opentelemetry.io/docs/concepts/signals/traces/

---

## 10. 开源测试资产 / Benchmark / Badcase 数据源

### 10.1 Defects4J

- 类型：Java reproducible bugs benchmark
- 价值：
  - 真实 Java bug + triggering tests
  - 可用于评估生成测试是否能暴露 bug
- 注意：
  - 环境约束强，JDK 版本敏感。
  - 不适合直接作为新手 e2e 全量跑。
- 建议用法：
  - 先抽 3~5 个简单 bug 做样本。
  - 研究：
    - AI 生成是否能触发 fail-to-pass
    - 需要哪些 assets
    - weak oracle 发生在哪
- 来源：
  - https://github.com/rjust/defects4j

### 10.2 Bugs.jar

- 类型：大型 Java real bugs dataset
- 价值：
  - 包含 bug report、developer patch、test result。
  - 可作为 badcase / bug reproduction 研究资产。
- 建议用法：
  - 只做文档级研究或少量抽样。
- 来源：
  - https://github.com/bugs-dot-jar/bugs-dot-jar

### 10.3 Bears Benchmark

- 类型：Java bug benchmark from CI builds
- 价值：
  - 从 Travis CI build pairs 里收集 bug / patch。
  - 适合研究“CI 失败 → 修复”的数据。
- 注意：
  - 部分依赖可能过期，不保证全量易复现。
- 来源：
  - https://github.com/bears-bugs/bears-benchmark

### 10.4 GitBug-Java

- 类型：较新的 reproducible Java bugs benchmark
- 价值：
  - 近期 Java bug，减少老 benchmark 污染风险。
- 建议用法：
  - 作为后续研究数据源。
- 来源：
  - https://github.com/gitbugactions/gitbug-java

### 10.5 QuixBugs

- 类型：小型算法 bug benchmark，Java + Python
- 价值：
  - 简单、可控、适合早期 smoke benchmark。
  - 但偏算法题，不代表真实业务系统。
- 建议用法：
  - 用于快速验证 Candidate API、JUnit 判卷、mutation gate。
- 来源：
  - https://github.com/jkoppel/QuixBugs

### 10.6 TestExplora

- 类型：Microsoft repository-level test generation benchmark
- 价值：
  - 目标是评估 LLM 主动发现潜在缺陷的能力。
  - 数据来自真实 GitHub PR，任务要求生成测试触发 buggy/fixed fail-to-pass。
  - 很贴合“测试生成评测平台”方向。
- 建议用法：
  - 作为设计参考，不一定直接跑全量。
  - 学习：
    - task schema
    - repo-level harness
    - trajectory logging
    - whitebox/graybox/blackbox test type
- 来源：
  - https://github.com/microsoft/TestExplora
  - https://huggingface.co/datasets/microsoft/TestExplora

### 10.7 SWE-bench / SWE-bench Verified

- 类型：真实 GitHub issue 修复 benchmark
- 价值：
  - 更偏“修代码”，不是“生成测试”。
  - 但它的 harness / task packaging / reproducible execution 很值得学习。
- 建议用法：
  - 学习 benchmark 工程结构。
  - 不作为当前测试生成主数据源。
- 来源：
  - https://github.com/swe-bench/SWE-bench
  - https://www.swebench.com/
  - https://www.swebench.com/verified.html

### 10.8 CodeXGLUE

- 类型：代码理解 / defect detection / code repair 等 benchmark 集合
- 价值：
  - 可作为“代码缺陷分类 / defect detection”参考。
- 建议用法：
  - 不直接接入主线。
- 来源：
  - https://microsoft.github.io/CodeXGLUE/
  - https://github.com/microsoft/codexglue

### 10.9 EMB / EvoMaster Benchmark

- 类型：Web/Enterprise API benchmark
- 价值：
  - 适合后续 API Test Harness / Schemathesis / EvoMaster 对比。
- 建议用法：
  - 中期选择小型 SUT 作为 API harness e2e。
- 来源：
  - https://github.com/aster-test-generation/EMB
  - https://github.com/WebFuzzing/Dataset

### 10.10 APIs.guru OpenAPI Directory

- 类型：OpenAPI schema 目录
- 价值：
  - 可用于收集公开 OpenAPI schema。
  - 适合 Schemathesis schema fuzzing 的外部样本。
- 注意：
  - 很多 schema 没有可控测试环境，不能直接真实执行。
- 来源：
  - https://github.com/APIs-guru/openapi-directory

---

## 11. 开源业务系统 / 可作为 SUT 的项目

### 11.1 Spring PetClinic

- 类型：Spring 官方示例应用
- 价值：
  - 简单、文档多、适合早期稳定 e2e。
  - 包含 Spring Boot / MVC / Data JPA 等常见结构。
- 建议用法：
  - 单测 / API harness early sample。
- 来源：
  - https://github.com/spring-projects/spring-petclinic
  - https://spring-petclinic.github.io/

### 11.2 mall-swarm

- 类型：Spring Cloud Alibaba 微服务商城
- 价值：
  - 更贴近电商业务、微服务、网关、注册中心、配置中心、监控等。
  - 适合作为中后期业务复杂度样本。
- 注意：
  - 环境重，启动成本高。
  - 不适合当前第一阶段。
- 来源：
  - https://github.com/macrozheng/mall-swarm
  - https://cloud.macrozheng.com/

### 11.3 yudao-cloud / ruoyi-vue-pro

- 类型：Spring Cloud / Spring Boot 后台管理系统
- 价值：
  - 模块丰富：RBAC、租户、流程、支付、商城、CRM、ERP、AI、IoT 等。
  - 适合研究权限、数据权限、后台管理类测试资产。
- 注意：
  - 大而复杂，适合中后期。
- 来源：
  - https://github.com/YunaiV/yudao-cloud
  - https://doc.iocoder.cn/intro/

### 11.4 OWASP Juice Shop

- 类型：故意脆弱 Web 应用
- 价值：
  - 安全测试 / UI / API / ZAP demo。
- 注意：
  - Node.js 项目，不适合当前 Java Maven 单测主线。
- 来源：
  - https://owasp.org/www-project-juice-shop/
  - https://github.com/juice-shop/juice-shop

---

## 12. 文章 / 工业实践 / 研究方向

### 12.1 快手智能单测：采纳率从 3% 到 80%

核心可借鉴点：

```text
AI 单测问题不只是语法错误。
真正困难包括：
- 代码调用信息缺失
- import / mock 幻觉
- 场景覆盖不足
- 复杂对象构造
- 与 IDE / 流水线割裂
- 缺少知识和规则
```

对本项目的意义：

```text
不要盲目追求“一次生成”。
要重视 context、execution feedback、knowledge/rules、badcase。
但个人项目不要复刻大厂私域中间件 / IDE 插件 / 自动入仓。
```

### 12.2 Uber AutoCover

核心可借鉴点：

```text
Preparer -> Generator -> Executor -> Validator -> Fixer
build-system integration
scenario-guided generation
AST-aware splicing
quality gates
mutation testing
persistent memory
```

对本项目的意义：

```text
最值得模仿的是工作流拆分、质量门、持久记忆。
不值得个人阶段模仿的是大规模 monorepo / Headless MR / IDE background precompute。
```

### 12.3 天猫 / 货拉拉 / 美团 AI 测试实践

共同结论：

```text
AI 测试落地不是模型问题，而是：
输入治理
知识组织
测试数据
场景建模
执行验证
人审反馈
资产沉淀
```

对本项目的意义：

```text
“少资产场景下的资产充分性判断”是差异化方向。
```

### 12.4 TestExplora / PR-aware Test Generation / MocklessTester

研究趋势：

```text
从 isolated function test generation 转向 repo-level / PR-aware / proactive bug discovery
从 coverage-only 转向 fail-to-pass / documentation intent / mutation score
从 direct prompting 转向 agentic exploration + execution harness
```

对本项目的意义：

```text
项目应建立小 benchmark：
- 同一目标，多 producer 生成 candidate
- 对比 pass / compile / coverage / mutation / oracle / asset gaps
```

---

## 13. 推荐实现切片

### Slice A：Candidate API（最高优先级）

目标：

```text
让平台能判卷任意来源的 JUnit 测试源码。
```

建议新增：

```text
app/models/candidate.py
app/storage/candidate_repo.py
app/api/candidates.py
app/pipeline/candidate_pipeline.py
```

API 草案：

```text
POST /jobs/{job_id}/candidates
GET  /jobs/{job_id}/candidates
GET  /jobs/{job_id}/candidates/{candidate_id}
GET  /jobs/{job_id}/candidates/{candidate_id}/report
```

验收：

```text
手动提交一段 JUnit 测试源码
平台写入隔离 test 文件
复用 Maven/JUnit/JaCoCo/Surefire/quality/report
报告里记录 provenance
结论仍 NEED_HUMAN_REVIEW
```

### Slice B：Provenance Compare

目标：

```text
同一 target 多个 author 的候选测试可以横向比较。
```

报告维度：

```text
author_type
compiled
executed
passed
coverage_delta
mutation_score
weak_assertion_findings
asset_missing_count
failure_type
review_summary
```

### Slice C：Badcase Ledger

目标：

```text
失败不再只是日志，而是结构化经验。
```

先做 SQLite 即可：

```text
badcase_records(
  id,
  target_fingerprint,
  author_type,
  failure_type,
  evidence_json,
  repair_hint,
  created_at
)
```

### Slice D：Asset Sufficiency Gate

目标：

```text
判断测试可信度缺的不是代码，而是业务 oracle / 测试数据 / mock / schema。
```

第一版用规则即可，不用 RAG：

```text
- 只有 assertNotNull / assertTrue(true) -> weak_assertion
- 断言完全复制当前实现输出但无外部依据 -> oracle_from_code_only
- 方法依赖 repository/client/mq/time/random -> likely_needs_fixture_or_mock
- Controller/Service 状态流转复杂 -> recommend_api_or_integration
```

### Slice E：PIT 轻量接入

目标：

```text
对 PASS candidate 进一步判断断言强度。
```

限制：

```text
只跑目标类
默认关闭
超时控制
失败不影响主判卷，只作为 advisory
```

### Slice F：API Harness MVP

目标：

```text
支持 YAML API candidate 执行。
```

最小 YAML：

```yaml
name: create_order_success
method: POST
base_url: ${BASE_URL}
path: /api/orders
headers:
  Authorization: Bearer ${TOKEN}
body:
  skuId: 1001
  count: 1
assertions:
  status_code: 200
  json:
    $.code: 0
```

后续扩展 DB assertion：

```yaml
db_assertions:
  - datasource: mysql_main
    sql: "select status from orders where id = ?"
    params: ["${response.$.data.orderId}"]
    expect: "CREATED"
```

---

## 14. 不同外部工具在本项目里的正确角色

```text
Claude Code / Copilot / Codex
=> external_agent producer，不是判卷器

Coze / Dify
=> 测试场景 / 业务规则 / 候选 JSON producer，不是平台底座

EvoSuite / Randoop / Schemathesis / EvoMaster
=> non-LLM or tool-based producer，用来做 baseline

JaCoCo / Surefire / PIT / JSONPath / DB assertion
=> deterministic judge signals

Langfuse / Phoenix
=> LLM trace / prompt / cost observability

Allure / ReportPortal
=> report sink / dashboard

Testcontainers / WireMock
=> environment asset provider

Defects4J / TestExplora / EMB / GitBug-Java
=> benchmark / badcase asset source
```

---

## 15. 推荐优先级清单

### 必做

```text
Candidate API
Provenance
Badcase Ledger
Asset Sufficiency Gate
PIT advisory mutation gate
API Harness MVP
```

### 可做

```text
Schemathesis adapter
Newman adapter
Langfuse trace
Testcontainers env plan
WireMock mock plan
Allure exporter
```

### 后置

```text
Coze/Dify producer demo
Claude Code producer demo
EvoSuite/Randoop producer baseline
ReportPortal sink
Playwright UI candidate
Locust/k6 perf candidate
ZAP security candidate
Testkube K8s orchestration
```

### 暂不做

```text
自动入仓
自动 accept/reject
复杂 IDE 插件
大规模并发生成
全量 mutation
多语言仓库支持
Bazel/Gradle 适配
完整企业级权限系统
```

---

## 16. 推荐写给后续 Coding Agent 的短 Prompt

```text
You are working on TestAgent Lab. The project is not another test generator.
The core product is an author-agnostic test candidate judge.

Do not add broad integrations unless explicitly requested.
First read:
- README.md
- docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md
- docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md

Current strategic goal:
Implement the smallest Candidate/Submission abstraction so that tests from humans, platform generator, Claude Code, Coze/Dify, EvoSuite, Randoop, or any external producer can be judged by the same deterministic pipeline.

Hard boundaries:
- Never modify production code.
- Never auto-accept or auto-reject.
- Conclusion remains NEED_HUMAN_REVIEW.
- External producer claims are advisory only.
- All verdicts must be grounded in execution evidence, coverage/mutation/quality signals, and asset sufficiency analysis.

Do not integrate Coze/Dify/LangGraph/Testkube now.
Design interfaces so they can later submit Candidate JSON.
```

---

## 17. Sources

### Project-specific

- TestAgent Lab README: https://raw.githubusercontent.com/genjibyte/AI-Test-Platform/main/README.md
- Core thesis repositioning: https://raw.githubusercontent.com/genjibyte/AI-Test-Platform/main/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md
- Phase 2 acceptance report: https://raw.githubusercontent.com/genjibyte/AI-Test-Platform/main/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md

### Unit / white-box

- JaCoCo: https://www.eclemma.org/jacoco/
- Maven Surefire Plugin: https://maven.apache.org/surefire/maven-surefire-plugin/
- Maven Surefire Report Plugin: https://maven.apache.org/surefire/maven-surefire-report-plugin/
- PIT / Pitest: https://pitest.org/
- EvoSuite: https://github.com/EvoSuite/evosuite
- Randoop: https://randoop.github.io/randoop/
- JQF: https://github.com/rohanpadhye/jqf
- Diffblue: https://www.diffblue.com/

### API / integration

- Schemathesis: https://github.com/schemathesis/schemathesis
- EvoMaster: https://github.com/WebFuzzing/evomaster
- Newman: https://github.com/postmanlabs/newman
- Karate: https://github.com/karatelabs/karate
- Testcontainers: https://testcontainers.com/
- WireMock: https://wiremock.org/
- MockServer: https://www.mock-server.com/
- Pact Foundation: https://github.com/pact-foundation

### UI / GUI

- Playwright: https://playwright.dev/
- Selenium: https://www.selenium.dev/
- Appium: https://appium.io/
- AUITestAgent: https://github.com/bz-lab/AUITestAgent

### LLMOps / agents

- Langfuse: https://github.com/langfuse/langfuse
- Phoenix: https://github.com/arize-ai/phoenix
- DeepEval: https://github.com/confident-ai/deepeval
- Ragas: https://docs.ragas.io/en/stable/
- Coze Studio: https://github.com/coze-dev/coze-studio
- Dify: https://github.com/langgenius/dify
- LangGraph: https://github.com/langchain-ai/langgraph

### Reporting / orchestration

- Allure Report: https://allurereport.org/
- ReportPortal: https://github.com/reportportal
- Testkube: https://github.com/kubeshop/testkube
- GitHub JUnit Report Action: https://github.com/marketplace/actions/junit-report-action
- OpenTelemetry: https://opentelemetry.io/

### Benchmark / assets / badcases

- Defects4J: https://github.com/rjust/defects4j
- Bugs.jar: https://github.com/bugs-dot-jar/bugs-dot-jar
- Bears Benchmark: https://github.com/bears-bugs/bears-benchmark
- GitBug-Java: https://github.com/gitbugactions/gitbug-java
- QuixBugs: https://github.com/jkoppel/QuixBugs
- TestExplora: https://github.com/microsoft/TestExplora
- TestExplora dataset: https://huggingface.co/datasets/microsoft/TestExplora
- SWE-bench: https://github.com/swe-bench/SWE-bench
- CodeXGLUE: https://microsoft.github.io/CodeXGLUE/
- EMB: https://github.com/aster-test-generation/EMB
- APIs.guru OpenAPI Directory: https://github.com/APIs-guru/openapi-directory

### Open-source SUT candidates

- Spring PetClinic: https://github.com/spring-projects/spring-petclinic
- mall-swarm: https://github.com/macrozheng/mall-swarm
- yudao-cloud: https://github.com/YunaiV/yudao-cloud
- OWASP Juice Shop: https://github.com/juice-shop/juice-shop
