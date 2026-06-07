# Phase Next — 方向审计与下一阶段设计（技术负责人视角）

> 日期：2026-06-07。性质：**方向审计 + 设计**，不写代码、不跑模型、不安装工具、不重构、不新增大功能。
> 上级约束：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/00_foundation/07_SOURCE_NOTES.md`。
> 关联：`docs/20`、`docs/21`、`docs/22`、`docs/23`（本会话新建的 frozen benchmark manifest）。
> **编号说明**：用户要求文件名为 `docs/23_PHASE_NEXT_DESIGN.md`，但本会话已先建 `/docs/50_benchmark/23_BENCHMARK_MANIFEST.md`（Step 2 工件，已被代码/JSON 引用）。为遵守“不覆盖已有文档”且不在本轮改代码，本文落到 `docs/24`。若需互换编号，请告知。
> **方法纪律**：每个判断给出（本项目事实证据 ‖ 外部高可信来源链接）。外部来源限学术论文、官方文档、厂商工程博客；不引用营销软文。来源汇总见 §5。

---

## 0. 结论速览（TL;DR）

1. **当前设计方向正确，继续，不重构。** “判卷优先 / 把 AI 输出当不可信代码 / 结构性确定性质量门 / 永不自动采纳 / 人是最终门”这套姿态，与 EvoSuite（自动 oracle 仍需开发者检查）、IntelliTest（人选哪些生成测试入 regression suite）、GitHub Copilot（生成测试后仍需 review）、Meta SapFix（修复经工程师审批才落地）的公开实践**一致**。见 §2 问题 4/5 与 §5。
2. **下一步最高性价比 = Context v3（方法契约接地）**，直接命中 `docs/21` 两个真实失败（猜错异常/内部 API），且纯增量、可离线验证。
3. **benchmark 先固化再小扩**：`docs/23` 的 `manifest.v1`（10 case / 4 repo / SHA 固化）已是“小扩”落地；不必现在冲 20。
4. **Phase 3 repair 做、但收窄**：仅 compile/API 机械错，永不碰 oracle，修复后仍 `NEED_HUMAN_REVIEW`；排在 Context v3 之后。
5. **coverage 稍后在“无 JaCoCo 冲突”子集以 advisory 恢复**，不作门禁；mutation/PIT 只参考。
6. **质量门不要去“判语义”**——这是自动化生成器的原理性边界（EvoSuite 实证），不是待补的功能缺口。

---

## 1. 证据基线

### 1.1 本项目硬事实（内部）

| 事实 | 证据 |
|---|---|
| 最优配置（v2 prompt + 编译修复 + `deepseek-v4-pro`）：编译 100%、生成测试通过 33%、质量门 0 FAIL、`conclusion` 恒 `NEED_HUMAN_REVIEW` | `docs/21` §2；`var/benchmark/v2-pro-quality-final/report.json` |
| 两个 `TEST_FAILURE` 都是 oracle/API 行为错：`Option.addValue`→`UnsupportedOperationException`（误以为是客户端 API）；`CSVRecord.get(int)` 越界→`ArrayIndexOutOfBoundsException`、`get(String)` 无 header→`IllegalStateException`（猜错异常类型） | `docs/21` §3 |
| 根因（代码层）：`_methods_block` 只渲染 `return_type name(params)`，**已解析的 `throws` 没被渲染**；whole-class target 不提供方法体；Javadoc 在 `_mask` 阶段被抹除 | `app/generate/prompt_builder.py:90-98` vs `app/context/java_parser.py:169-184`；`app/models/java_source.py:34-41` |
| 质量门是结构性、确定性的，**明确不证明 oracle 正确** | `docs/20` §5；`app/quality/test_quality_gate.py` |
| 覆盖率本期全程关闭（`-Djacoco.skip`），因 F2 JaCoCo 双 agent 冲突 | `docs/21` §2；`docs/20` §7；`docs/14`（F2） |
| 样本仅 3 case，作者自陈“不能下通过率强结论” | `docs/20` §7 |
| 已落地 frozen manifest（10 case、SHA 固化、commit 入 mirror key）+ review policy（recommendation 分布、expected/actual 抽取） | `docs/23`；`docs/22`；`benchmarks/manifest.v1.json` |

### 1.2 外部高可信来源（映射到六问题）

| 来源 | 类型 | 对应问题 |
|---|---|---|
| ProjectTest / MultiFileTest（arXiv 2502.06556） | 学术 benchmark | 1、5、6 |
| Meta Sapienz / SapFix（Engineering at Meta + 论文） | 厂商工程 + 学术 | 5 |
| Microsoft IntelliTest（Microsoft Learn 官方文档） | 官方文档 | 4 |
| GitHub Copilot 测试文档（GitHub Docs） | 官方文档 | 2、4 |
| EvoSuite（官网论文 + GitHub） | 工具 + 学术 | 4、（baseline） |
| PIT mutation testing（pitest.org） | 官方文档 | 3、4 |
| Randoop（randoop.github.io + OOPSLA’07） | 官方文档 + 学术 | 4、（baseline） |
| JUnit5 / JaCoCo / Maven Surefire（官方） | 官方文档 | 2、3、6 |

---

## 2. 六个问题的解决方案

> 每个问题统一给出：**事实证据 / 外部依据 / 最小方案 / 验收 / 风险 / 明确不做**。

### 问题 1：样本太小

- **事实证据**：`v2-pro-quality-final` 仅 3 case，33% 通过率来自 1/3，统计无意义；作者已在 `docs/20` §7 标注“样本量…不能下通过率强结论”。
- **外部依据**：ProjectTest / MultiFileTest 用每语言 **20 个项目**作为项目级基准，且前沿模型仍出现 executability/cascade 错（[arXiv 2502.06556](https://arxiv.org/abs/2502.06556)）；`docs/07` §4.5（TestExplora）强调评测须“真实仓库 + 可执行 + fail‑to‑pass”；Meta Sapienz 在大规模移动应用上做系统级测试（[Engineering at Meta](https://engineering.fb.com/2018/05/02/developer-tools/sapienz-intelligent-automated-software-testing-at-scale/)）。→ 行业基线是“十几~几十个可执行项目”，不是 3。
- **最小方案**：以 `docs/23` 的 `manifest.v1`（10 case / 4 repo，SHA 固化）为“保守小扩”落地；按 bucket 平衡（异常语义×5 / 纯函数×3 / API 契约×2）让失败分布有信息量。**不盲目追 20**。
- **验收**：≥8 个可执行 case 稳定跑通；失败可按 bucket 聚类；3 个 frozen case 与 v2 baseline commit 一致、零重跑可比。
- **风险**：扩样本=更多全量 baseline 构建成本——本会话离线 dry‑run 实测 **commons‑lang3 的全量测试 suite 是明显瓶颈**；模型成本随 case 数线性增长。
- **明确不做**：不追 SWE‑bench 规模；不引入需大改 harness 的多语言/复杂多模块样本；不靠堆样本掩盖 oracle 问题。

### 问题 2：上下文不足，模型猜错 oracle/API

- **事实证据**：v2‑pro 两个失败都是“猜异常/内部 API”（`docs/21` §3）。代码根因：`throws` 已被 `java_parser` 解析却未进 prompt；whole‑class target 无方法体、Javadoc 被抹（见 §1.1）。
- **外部依据**：GitHub Copilot 官方建议——提供明确测试要求、覆盖边界/异常场景；若目标代码尚无测试，可打开已有测试文件作为上下文，并且对生成代码“always review”后补齐遗漏场景（[GitHub Docs – Writing tests](https://docs.github.com/en/copilot/tutorials/write-tests)、[Generating unit tests](https://docs.github.com/en/copilot/tutorials/copilot-cookbook/testing-code/generate-unit-tests)）；JUnit5 的 `assertThrows(expectedType, executable)` 在类型不符/未抛时失败，是“按声明类型断言异常”的正确手段（[JUnit5 User Guide](https://docs.junit.org/current/user-guide/)）。→ 把“契约/意图”喂进去能降猜测，但仍须人审。
- **最小方案**：**Context v3 = 方法契约接地**（纯增量）：①渲染已解析的 `throws`；②从原始源码抽每方法 Javadoc 的 `@throws/@return`（有界、超长回退）；③从方法体抽 `throw new XxxException`；④system 规则改为“断言异常用契约声明的精确类型（throws/@throws/body throw）+ `assertThrows`；无据则不断言具体异常类型 → 跳过并记 `omitted_uncertain_cases`”。改动面：`java_parser` + `JavaMethod`(+`javadoc`/`body_throws`) + `prompt_builder` 渲染，不动主流程。
- **验收**：3 frozen case 上 v3 vs v2：CSVRecord/Option 的异常从“猜错”转为“用文档类型”或“被主动跳过”；纯函数 case（WordUtils）不退化；全量测试仍绿。
- **风险**：Javadoc 抽取是启发式（无完整 Java 语法）→ 必须有界 + 回退；context 变长→token 成本升；模型仍可能无视契约（故保留人审）。
- **明确不做**：不喂全仓库/全方法体（违反 `docs/07` P4 bounded context）；不让模型自由“补” API；不自动把 `expected` 改 `actual`（`docs/07` A5）。

### 问题 3：覆盖率被降级

- **事实证据**：本期 coverage 全程 `-Djacoco.skip` 关闭（`docs/20` §7、`docs/21` §2），根因是 F2 JaCoCo 双 agent 冲突（`docs/14`）；导致北极星指标“目标覆盖提升”（`docs/00` §6.5）当前未验证。
- **外部依据**：`docs/07` P3——覆盖率必要但不充分；PIT 官方说明传统覆盖率只度量哪些代码被执行，不能检查测试是否能发现被执行代码中的 fault，mutation score 是更强的测试有效性信号（[pitest.org](https://pitest.org/)）；JaCoCo 是基于 Java agent 的覆盖库，双 agent 冲突是其机制使然（[jacoco.org](https://www.jacoco.org/jacoco/)）。
- **最小方案**：在“**不自带 JaCoCo**”的仓库子集恢复覆盖率，作为 **advisory 价值指标**（让 `target_line_delta/target_improved` 回归），冲突仓库继续 skip 并如实标 `coverage_unavailable`（runner 已有 `cov_available` 逻辑）。mutation 只“参考”，本期不集成。
- **验收**：≥3 个 JaCoCo‑free case 报出 before/after 覆盖率且 `coverage_dropped=false`；覆盖率仅作 advisory 输入，不改 `conclusion`。
- **风险**：筛“无 JaCoCo 冲突且可构建”的子集有成本；覆盖率升 ≠ 有效（PIT 论点），不得据此放松人审。
- **明确不做**：不恢复覆盖率**门禁**；不为覆盖率引入 mutation（重，参考即可）；不在冲突仓库强开 JaCoCo。

### 问题 4：质量门不能判断语义正确

- **事实证据**：质量门是结构性确定性检查（弱断言/同义反复/不稳定/反射/越界/覆盖下降），自陈“**不证明 oracle 正确**”（`docs/20` §5、`app/quality/test_quality_gate.py`）；Option 的失败被判 `REVIEW` 非 `FAIL`（编译+运行但断言错），仍须人判“测试错 vs 发现 bug”（`docs/21` §4）。
- **外部依据**：EvoSuite 论文明确把 test oracle problem 列为传统白盒生成的主要问题，并说明生成断言是在捕获当前行为，仍需要开发者检查语义一致性（[evosuite.org 论文](https://www.evosuite.org/wp-content/papercite-data/pdf/esecfse11.pdf)、[GitHub](https://github.com/EvoSuite/evosuite)）；IntelliTest 由人选择哪些生成测试保存为 regression suite（[Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/test/generate-unit-tests-for-your-code-with-intellitest)）；GitHub Copilot 官方要求 review 生成代码并补齐遗漏测试（[GitHub Docs](https://docs.github.com/en/copilot/tutorials/write-tests)）；SapFix 的修复**经工程师审批才落地**（[Engineering at Meta](https://engineering.fb.com/2018/09/13/developer-tools/finding-and-fixing-software-bugs-automatically-with-sapfix-and-sapienz/)）。
- **最小方案**：**不让门去判语义**。维持判卷优先：门做结构把关，review policy（`docs/22`）把 expected/actual + grounding + risk 组织给人；`conclusion` 恒 `NEED_HUMAN_REVIEW`。可选增强：当 v3 使模型用 `assertThrows` 且异常类型来自契约时，review summary 标注“异常类型有文档支撑”——给 reviewer 信号，仍不自动采纳。
- **验收**：所有 `TEST_FAILURE` 恒 review‑only；门不产出“语义正确”判定；review summary 能定位每个失败的 expected vs actual（`docs/22` 已验证）。
- **风险**：把“门 PASS”误读为“可采纳”是最大风险 → 文档/UI 须持续强调 **PASS≠accept**（`docs/22` 红线）。
- **明确不做**：不引入 LLM 当验证者（`docs/07` A2）；不做自动语义判定/自动采纳；不用 mutation 当 oracle 真值（mutation 测“测试强度”，非 oracle 对错）。

### 问题 5：Phase 3 修复闭环需要收窄

- **事实证据**：已有 bounded compile‑failure repair（最多 N 轮，commit `7187965` P3‑min）；`docs/07` P5/A5 明令“**不靠弱化 oracle 修复**”；v2‑pro 已 100% 编译，`docs/21` §5 直言“broadening Phase 3 repair is not the best next move”。
- **外部依据**：ProjectTest 做了 manual/self error‑fixing 消融，error‑fixing 对 compilation/cascade 错有帮助（[arXiv 2502.06556](https://arxiv.org/abs/2502.06556)）；SapFix 自动修复但**人审批后落地**（[Engineering at Meta](https://engineering.fb.com/2018/09/13/developer-tools/finding-and-fixing-software-bugs-automatically-with-sapfix-and-sapienz/)、[SapFix 论文 PDF](https://web.eecs.umich.edu/~weimerw/2025-481F/readings/SapFix-Automated-End-to-End-Repair-at-Scale-v2.pdf)）。→ 修复值得做，但限“机械错”且永远人审。
- **最小方案**：repair 收窄为 **compile / API‑misuse only**（缺 import、错签名/重载、误用内部 API）；每次修复后过 quality gate + review policy，修复后仍 `NEED_HUMAN_REVIEW`；`TEST_FAILURE`/oracle 永不进 repair。
- **验收**：repair 只作用于 compile/API 类失败；oracle 类 **0 改写**；修复轨迹有 diff、可追溯失败类型、≤3 轮（`docs/00` §7.13、`docs/07` P5）；修复后 `conclusion` 不变。
- **风险**：API‑misuse 与 oracle‑wrong 边界模糊（如 `addValue` 误用既是 API 误用又表现为异常）→ 保守处理：不确定即归人审、不修。
- **明确不做**：不修 oracle/断言；不删断言到只剩 smoke（A5）；不扩到语义级修复；不无限重试。

### 问题 6：缺 benchmark 体系

- **事实证据**：此前 `spec.example.json` 克隆 HEAD→漂移、不可复现；旧 report 早于质量门、无质量字段（`docs/20` §1）；样本 3、无 frozen、无 provenance。现已落地 `manifest.v1`（10 case、SHA 固化、commit 入 mirror key）+ `recommendation_distribution` 聚合（`docs/23`、`docs/22`）。
- **外部依据**：`docs/07` §4.5（TestExplora）——repo‑level + 可执行 + fail‑to‑pass 优于“看起来对”；ProjectTest——固定项目集 + error‑fixing 消融 + 报告 compile/cascade 错（[arXiv 2502.06556](https://arxiv.org/abs/2502.06556)）；`docs/07` §8 已给最小 benchmark 模板（`commit_hash/baseline_*/failure_type/validator_result`）；`docs/07` A4——**必须展示失败分布，而非只展示成功**。
- **最小方案**：以 `manifest.v1` 为基线 benchmark；每 case 记 provenance（`repo@commit`、bucket、frozen?）；支持消融对照（v2 vs v3、repair on/off）；report 出 `recommendation_distribution + top_failure_types + per-case expected/actual`；frozen 3 与 `v2-pro-quality-final` 零成本可比。
- **验收**：benchmark 一键复现（SHA 固化）；输出含失败分布与 per‑case 根因；v2/v3 可对照；不只报成功。
- **风险**：全量 baseline 构建成本（lang3 瓶颈，dry‑run 实测）；模型非确定 → 需多次或谨慎结论（`docs/20` §7）。
- **明确不做**：不追大基准规模；不把 benchmark 变成“只展示成功的 demo”（A4）；不在 benchmark 里自动采纳。

---

## 3. 下一阶段路线（三选一，可叠加）

### A. 2 周保守路线（低风险、零/极小模型成本）
1. 提交 `manifest.v1` + 质量门 + review policy 稳定点（已具备）。
2. 实现 **Context v3**（纯增量、离线单测）。
3. 跑 **一次** v3 pro（仅 3 frozen case）对照 `v2-pro-quality-final`——**需你确认成本**。
4. 不碰 repair / coverage。
- **产出**：v3 vs v2 对照 + 文档；验证“契约接地是否降低猜错率”。
- **适用**：想用最小代价确认 Context v3 价值。

### B. 100 天标准路线（建设“可信闭环 + 可复现 benchmark”）
A 之上叠加：
1. benchmark 稳定跑 8–12 case（已 10），多模型对照（flash/pro 及可选 +1）。
2. 覆盖率在 JaCoCo‑free 子集以 **advisory** 恢复。
3. **收窄版 Phase 3 repair**（compile/API，永不 oracle，修复后仍人审）。
4. 失败分布沉淀 badcase 规则（`docs/07` §4.6 Airbnb 失败聚类思路）。
- **产出**：可复现 benchmark 体系 + 可信失败画像 + 窄修复闭环。
- **适用**：把项目做成“可对外讲清楚的质量系统”。

### C. 企业 PoC 激进路线（探索大厂落地形态）
B 之上叠加：
1. 接 PR/CI：仅产出**建议 patch**，**不入仓**（`docs/00` §4.4 预留、§8 Roadmap‑only）。
2. PIT mutation 作为**可选**价值指标；EvoSuite/Randoop 作为**对照 baseline**（见 §4）。
3. 多仓/多模块；人审反馈回流成规则/badcase 训练数据（`docs/07` §4.4 TiCoder）。
- **铁律不变**：`conclusion` 恒 `NEED_HUMAN_REVIEW`；不自动入仓。
- **适用**：要做企业 PoC demo；**明确超出 charter Phase 1 范围**，需先改 `docs/00` 再做。

---

## 4. 最终建议（逐条回答）

| 问题 | 建议 | 依据 |
|---|---|---|
| 是否继续当前设计 | **继续，不重构**。判卷优先 + 永不自动采纳 + 结构门 + 人审，与 EvoSuite/IntelliTest/Copilot/SapFix 公开实践一致 | §2 问题 4/5；§5 |
| 是否先扩 benchmark | **先固化 + 小扩（已到 10），再 Context v3，再用 benchmark 量化 v3**；不必先冲 20 | 问题 1/6；ProjectTest 规模仅作上限参考 |
| 是否做 Context v3 | **做，且是最高性价比下一步**（直击 `docs/21` 两个真实失败，纯增量、可离线验证） | 问题 2；`docs/21` §3 |
| Phase 3 repair 到底做不做 | **做，但收窄**到 compile/API、永不 oracle、修复后仍人审；优先级排在 Context v3 之后 | 问题 5；`docs/21` §5 |
| coverage 什么时候恢复 | **Context v3 + benchmark 稳定后**，于 JaCoCo‑free 子集作为 **advisory** 恢复（不作门禁） | 问题 3；`docs/07` P3 |
| 哪些工具**只参考不集成** | Meta Sapienz/SapFix（重型系统级，借“自动测试 + 人审修复”理念）；EvoSuite/Randoop（借 oracle 哲学，不入生成流）；PIT（借“覆盖不足、mutation 更强”，PoC 才考虑）；IntelliTest（借“人保存 regression suite”交互） | §5 各源 |
| 哪些工具可作**可选 baseline** | **EvoSuite / Randoop** 作传统自动生成对照（同 target 跑，比“AI vs 搜索/随机”的可 review 性与 oracle 质量）；**JaCoCo**（覆盖率，子集恢复）；**JUnit5 + Surefire**（执行/报告，已在用）；**PIT**（测试强度，PoC 可选度量） | §5 各源 |

> 一句话：**Context v3 → 用 frozen benchmark 量化 → 收窄 repair → advisory 覆盖率**，全程不动“永不自动采纳、判卷优先、人是最终门”的红线。

---

## 5. 来源（高可信，去营销）

**学术 / 基准**
- ProjectTest / MultiFileTest: A Project‑level / Multi‑File‑Level LLM Unit Test Generation Benchmark — [arXiv 2502.06556](https://arxiv.org/abs/2502.06556) ‖ 代码 [github.com/YiboWANG214/ProjectTest](https://github.com/YiboWANG214/ProjectTest)
- Randoop: Feedback‑Directed Random Testing for Java（OOPSLA’07）— [PDF](https://homes.cs.washington.edu/~mernst/pubs/pacheco-randoop-oopsla2007.pdf) ‖ 官方 [randoop.github.io/randoop](https://randoop.github.io/randoop/)
- EvoSuite: Automatic Test Suite Generation（ESEC/FSE’11）— [PDF](https://www.evosuite.org/wp-content/papercite-data/pdf/esecfse11.pdf) ‖ 官网 [evosuite.org](https://www.evosuite.org/) ‖ [GitHub](https://github.com/EvoSuite/evosuite)

**厂商工程实践**
- Meta Sapienz — [Engineering at Meta（2018‑05‑02）](https://engineering.fb.com/2018/05/02/developer-tools/sapienz-intelligent-automated-software-testing-at-scale/)
- Meta SapFix + Sapienz — [Engineering at Meta（2018‑09‑13）](https://engineering.fb.com/2018/09/13/developer-tools/finding-and-fixing-software-bugs-automatically-with-sapfix-and-sapienz/) ‖ SapFix 论文 [PDF](https://web.eecs.umich.edu/~weimerw/2025-481F/readings/SapFix-Automated-End-to-End-Repair-at-Scale-v2.pdf)

**官方文档**
- Microsoft IntelliTest — [Generate unit tests with IntelliTest](https://learn.microsoft.com/en-us/visualstudio/test/generate-unit-tests-for-your-code-with-intellitest) ‖ [IntelliTest manual](https://learn.microsoft.com/en-us/visualstudio/test/intellitest-manual/)
- GitHub Copilot — [Writing tests](https://docs.github.com/en/copilot/tutorials/write-tests) ‖ [Generating unit tests](https://docs.github.com/en/copilot/tutorials/copilot-cookbook/testing-code/generate-unit-tests)
- PIT mutation testing — [pitest.org](https://pitest.org/)
- JaCoCo — [jacoco.org/jacoco](https://www.jacoco.org/jacoco/)
- JUnit 5 — [User Guide](https://docs.junit.org/current/user-guide/)（`assertThrows`）
- Maven Surefire — [maven.apache.org/surefire](https://maven.apache.org/surefire/maven-surefire-plugin/)

**项目内部证据**
- `docs/00`、`docs/07`、`docs/14`、`docs/20`、`docs/21`、`docs/22`、`docs/23`
- `app/quality/test_quality_gate.py`、`app/generate/prompt_builder.py`、`app/context/java_parser.py`、`app/models/java_source.py`、`app/benchmark/`、`app/review/review_policy.py`
- `var/benchmark/v2-pro-quality-final/`（report.json / bench.db）

---

> 复核要点：本文不改任何生产逻辑、不跑模型、不集成工具；所有判断均挂接（内部事实 ‖ 外部来源）。落地顺序与红线见 §0 与 §4。
