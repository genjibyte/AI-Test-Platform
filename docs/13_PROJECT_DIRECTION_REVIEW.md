# TestAgent Lab —— 技术负责人方向审计

> 角色：技术负责人（非执行开发）。性质：方向审计，不写代码、不改文件。
> 日期：2026-06-06。
> 阅读范围：`docs/00`、`docs/07`、`docs/11`、`docs/12`、`app/`、`tests/`、`samples/`、`git log`。
> 证据规则：每个判断标注代码文件 / 测试 / 文档 / commit；不确定处写明"不确定"与验证方法；不写营销话术。

> **文档勘误（先记）**：审计任务清单第 4 项指向 `docs/12_PHASE3_TOOL_SKILL_KB_AUDIT.md`，仓库中**不存在**该文件；实际文件为 `docs/12_PHASE3_TOOLING_RESEARCH.md`（本次已阅）。

---

## 0. 事实基线（本审计依赖的硬事实）

| 事实 | 证据 |
|---|---|
| Phase 1（判卷场）T01–T11 全部落库 | `git log`：commit `1a75695`..`0d486d5` |
| Phase 2（最小生成器）T01–T11 全部落库 | `git log`：commit `96f10c0`..`fbbecaa` |
| 单元/集成：105 个测试函数，22 个测试文件 | `grep 'def test_' tests`（105），`ls tests` |
| 真实 Maven e2e 仅 2 例且全部针对 toy | `tests/e2e/test_phase2_e2e.py`（2 passed），`tests/e2e/test_phase1_e2e.py` |
| **唯一样例是 6 行的 toy** | `samples/calc/src/main/java/com/example/Calc.java`：`add`/`max` 两方法共 6 行 |
| 应用代码约 3113 行 Python | `find app -name '*.py' \| xargs wc -l` |
| 真实 LLM 仅有手动脚本、未进测试套件 | `scripts/llm_live_check.py`（仅对 `calc#max` 校验 schema 稳定性，门控于 env key） |
| 任意 OSS 仓库判卷能力存在但无 committed 证据 | `scripts/run_judge.py`（可跑任意 repo），但仓内无真实仓库运行记录 |

> 一句话基线：**两条确定性闭环（判卷 / 最小生成）都已实现并在一个 toy 上用真实 Maven 验证；真实模型、真实仓库、规模化证据均尚不存在。**

---

## 一、项目到底解决什么痛点？

### 1.1 目标用户
Charter §4 定义四类：开发工程师、测试开发/质量效能、研发负责人、CI/CD（仅架构预留，明确不集成）。证据：`docs/00` §4。
- **真实第一用户 = 开发 + 测开/质量效能**（白盒研发效能场景），证据：`docs/00` §3.1–3.3。

### 1.2 真实痛点
项目**北极星不是"生成测试"，而是"判定 AI 生成测试是否工程可用"**。证据：`docs/00` §3.6、§6（"AI 生成的测试是否经过真实工程判卷，并形成可审查结果"）、`docs/07` P1（"Build the judge before the generator"）。
- 落点：降低单测成本 + 提升目标覆盖 + **测试资产可信治理**（可编译/可执行/可度量/可审查），而非纯生成。证据：`docs/00` §5.2 列了 10 条 AI 生成单测新痛点（import 幻觉、不懂构造/泛型、错误 mock、缺执行验证、无系统化修复等）。

### 1.3 当前代码是否真覆盖该痛点？
| 能力 | 状态 | 证据 |
|---|---|---|
| 导入→构建→执行→Surefire→JaCoCo→报告（判卷闭环） | ✅ 实现，toy 验证 | `app/pipeline/judge_pipeline.py`；`tests/e2e/test_phase1_e2e.py` 通过；`docs/08` |
| 目标→有界上下文→LLM→写独立测试→执行→覆盖率对比→报告 | ✅ 实现，toy + fixture 客户端验证 | `app/pipeline/generate_pipeline.py`；`tests/e2e/test_phase2_e2e.py`（2 passed）；`docs/11` §2 |
| 生成物"不可信"标记 + 平台确定性身份字段 | ✅ 实现 | `app/llm/schema.py:41-57`（`trusted=False`） |
| 写文件边界守卫（只 src/test、拒覆盖、不碰生产码） | ✅ 实现 | `app/generate/test_writer.py:82-94` |
| 覆盖率不降/目标提升判定 | ✅ 实现 | `app/coverage/coverage_compare.py`（`coverage_dropped`/`target_improved`） |
| 结论恒 `NEED_HUMAN_REVIEW`、失败不隐藏 | ✅ 实现 | `app/report/generation_report.py`（`CONCLUSION`） |
| **真实模型生成出可用测试** | ❌ 未验证 | e2e 用 `_FixtureClient`（`tests/e2e/test_phase2_e2e.py`），非真实模型 |
| **真实仓库上整条闭环成立** | ❌ 未验证 | 仅 `samples/calc`；`docs/09` §4 把 clean-host OSS e2e 列为待补 |

**结论（一）**：痛点在**结构上被覆盖**（判卷优先的闭环真实存在），但**实证仅限一个 toy + 一个确定性假客户端**。"AI 能否在真实代码上生成工程可用测试"这一核心命题**当前未被任何证据支持**。这是本项目最大的"看起来已完成、实则未验证"的缺口。

---

## 二、与普通 AI 生成测试 demo 的区别

### 2.1 普通 demo 做什么
prompt → LLM → 输出测试文本（可能跑一次）。无隔离执行、无判卷、无覆盖率对比、无状态机/持久化、无不可信标记、无失败分类、无边界守卫。

### 2.2 本项目多出的工程闭环（逐条带证据）
1. 隔离工作区 + 子进程执行 + 日志：`app/runtime/workspace.py`、`app/runtime/executor.py`（commit `93088c7`）。
2. 确定性判卷（mvn test + Surefire + JaCoCo 解析）：`app/build/maven_runner.py`、`app/report/surefire_parser.py`、`app/coverage/jacoco_parser.py`（`9adf640`）。
3. 状态机 + SQLite 持久化（Phase 1 + Phase 2 共 13 状态）：`app/models/job.py`、`app/storage/job_repo.py`（`a82aea6`、`a341ac1`）。
4. LLM 隔离层（fake/openai/deepseek，离线默认）：`app/llm/client.py`（`30021a7`、`b8f41f0`）。
5. 生成物不可信 + 身份字段防篡改：`app/llm/schema.py:41-57`。
6. 写文件边界守卫：`app/generate/test_writer.py:82-94`。
7. 覆盖率 before/after delta：`app/coverage/coverage_compare.py`（`d694028`）。
8. 报告恒人审、失败如实呈现：`app/report/generation_report.py`（`0a4f7bf`）。

### 2.3 已实现 vs 仅文档设想
- **已实现且有测试**：上述 2.2 全部；105 测试函数；2 条真实 Maven e2e。
- **仅文档设想（无代码）**：
  - Phase 3 失败分类 + 有限 Fixer：`docs/07` §5、`docs/12` §4（计划，无实现）。
  - Phase 4 质量门禁 accept/reject + 弱断言检测：`docs/07` §5。
  - Phase 5 benchmark（≥3 仓库×≥5 方法）：`docs/07` §5/§8。
  - Web 前端 6 个页面：`docs/00` §10（无任何前端代码）。
  - badcase 知识库 / 规则库：`docs/00` §7.16-17。
  - 真实模型闭环、真实仓库验证：见 §0、§1.3。

**结论（二）**：与 demo 的差异是**真实且结构性的**（判卷优先 + 不可信治理 + 确定性度量），不是包装。但差异目前体现在"**架构与离线测试**"层面，尚未体现在"**真实模型 × 真实仓库的产出**"层面。

---

## 三、企业落地可能？

### 3.1 接近真实企业需求的部分
- **判卷优先架构**：与 Uber AutoCover（Preparer→Generator→Executor→Validator→Fixer）一致，证据：`docs/07` §4.2。企业 AI 测试系统的真实要件就是"先有确定性判卷底座"。
- **不可信标记 + 强制人审门 + 不改生产码 + patch 可审查**：`schema.py`、`test_writer.py`、`generation_report.py`。这些正是企业合规/安全的硬约束。

### 3.2 距离企业落地还很远的部分
- **构建/语言面**：仅单模块 Maven + JUnit5 + Mockito；企业大量是多模块、Gradle、Spring DI、复杂泛型/构造/mock。证据：`docs/00` §7-8（主动限定/砍掉）。
- **无真实仓库 benchmark、无真实 LLM 闭环证据**：§0、§1.3。
- **执行安全**：在隔离**目录**里跑任意 OSS 的 `mvn`，但**非容器/网络沙箱**——等于在宿主执行不可信第三方构建脚本，存在 RCE/供应链面。证据：`app/runtime/executor.py`（子进程，无容器化）；`docs/06` 也仅讨论 DLP 篡改、未讨论沙箱。**这是落地硬障碍。**
- **无 CI/IDE 集成**：Charter §8 明确不做。

### 3.3 最大落地障碍排序（我的判断，逐条标注证据/不确定）
1. **上下文充分性**（真实 repo 的 DI/泛型/构造/重载是否能喂够，决定生成能否编译）——**最关键**。当前仅 toy 验证。**不确定**，验证方法：在 2-3 个真实小仓库上跑 Phase 2 统计 compile 通过率。
2. **执行安全（沙箱）**——企业不可能在裸宿主跑不可信构建。证据：无容器化代码。
3. **断言质量/oracle**（覆盖率≠有效）——`docs/07` P3；当前无断言质量检测（属 Phase 4，未实现）。
4. **构建系统多样性**（Gradle/多模块）——Charter §8 限定。
5. **成本**（LLM 调用 × 修复轮次 × 仓库规模）——**不确定**，无任何成本数据；验证：路线 A 跑真实模型记录 token/耗时。
- 注：IDE/CI 集成、覆盖率采集本身**不是**主要障碍（覆盖率已可靠实现，证据 `tests/test_coverage_compare.py` 6 passed + e2e 实测 0.5→1.0）。

### 3.4 个人项目成熟度上限
我的判断：**可信的最小闭环 + 小型真实仓库 mini-benchmark（约等于 TRL 4，实验室验证）**。不可能到企业生产（TRL 7+）。
证据/理由：单人维护、无沙箱、无 CI/IDE 集成、Charter §8 主动砍掉企业特性。**这不是缺点**——项目定位本就是"判卷场/最小可靠闭环"（`docs/00` §3.5），不是终局平台。

---

## 四、Phase 3 是否应该继续？

### 4.1 继续做 Fixer 是否最优方向？
**部分是、但时机不对。** Fixer 是 Charter §9 item 11 的 MVP 必需项，但当前**最大未知不是"修不修"，而是"真实仓库上生成能否编译/有意义"**——而这点**零证据**（§1.3）。在未验证的地基上加 Fixer，是在猜测的失败分布上做优化。证据：`docs/12` §4 的失败分类优先级目前是"凭 TestART 论文猜"，而非来自本项目真实数据。

### 4.2 是否应先补 benchmark / 多仓库验证？
**应优先做"最小真实验证"。** 不必一上来做完整 Phase 5 benchmark，但至少需要：真实模型 + 2-3 个真实小型 Maven 仓库 + 几个目标方法的 Phase 2 实跑。证据：`samples/` 只有 toy；`docs/09` §4 已自列 clean-host OSS e2e 待补；`docs/07` §5 Phase 5 要 ≥3 repos。

### 4.3 是否应收缩范围？
**应收缩为"验证里程碑"**：把"真实 LLM × 真实小仓库 × Phase 2 闭环"作为下一步唯一目标，而非展开 Phase 3/4。理由：闭环可信度 > 修复成功率。

### 4.4 是否存在比 Phase 3 更重要的工作？
**有，且更重要**：(a) 真实 LLM 端到端验证（现仅 fixture）；(b) 小型真实仓库 mini-benchmark；(c) 执行沙箱安全评估。这三件决定项目**可信度**；Fixer 只决定**成功率**。可信度未立时，成功率无意义。

**结论（四）**：**不立即推进 Phase 3**。先插入真实验证里程碑，用真实失败数据反推 Phase 3 的设计与优先级。

---

## 五、三条路线

### A. 保守路线（2 周内稳定完成，面试可讲）
- 内容：**不做 Phase 3**。接真实模型（openai/deepseek）跑通 1-2 个真实小型单模块 Maven 仓库的 Phase 2，对 3-5 个目标方法记录 before/after 覆盖率 + 失败类型（**成功与失败都展示**），产出一份 mini-benchmark 报告（对齐 `docs/07` §8 模板）。
- 复用：`scripts/run_judge.py`、`scripts/llm_live_check.py`、现有 generate_pipeline。
- 收益：把"架构强但只在 toy 上验证"升级为"在真实仓库有实证"，面试叙事闭环（判卷场 + 最小生成器 + 真实数据）。
- 风险：低。最坏情况是发现真实仓库生成大量编译失败——**但这本身就是有价值的诚实结论**（`docs/07` A4）。

### B. 标准路线（100 天，高质量项目）
- 内容：A +
  1. Phase 3 有限 Fixer：确定性补 import（复用 `class_index`）+ LLM 兜底 ≤3 轮 + patch/badcase（SQLite + `difflib`），失败分类**由 A 的真实数据驱动**（`docs/12` §4）。
  2. Phase 4 最小质量门禁：弱断言检测 + 生产码改动检测 → ACCEPT/REJECT/NEED_HUMAN_REVIEW（`docs/07` P6）。
  3. 5-8 个仓库 benchmark + 聚合指标（`docs/07` §8）。
  4. 最小只读 Web 报告页（先 API 后前端，`docs/07` A1）。
- 收益：达成 Charter §9 完整 MVP，且每层有真实数据支撑。
- 风险：中。关键是不让范围漂移到企业特性。

### C. 激进路线（接近企业 PoC，高风险）
- 内容：B + 多模块/Spring 支持 + **容器沙箱执行** + 真实 LLM 成本/稳定性压测 + CI 集成（PR 自动补测）。
- 收益：触及真实企业形态。
- 风险：**高**。范围爆炸、单人难维、直接触碰 Charter §8 主动砍掉的企业特性（Gradle/多模块/CI）。**不推荐个人项目走 C。**

---

## 六、最终建议

### 6.1 是否继续当前方向？
**是。** judge-first 方向正确且差异化真实（证据：架构与 Uber/Meta 实践一致 `docs/07` §4.2、§4.5；确定性判卷已实现并通过测试）。方向不需要改。

### 6.2 是否继续 Phase 3？
**暂缓，不立即开 Phase 3。** 先做路线 A 的"真实 LLM × 真实小仓库"验证里程碑，用真实失败分布驱动 Phase 3 设计。理由见 §四。

### 6.3 下一阶段 5 个任务（按依赖排序）
1. **真实 LLM smoke**：配置真实 provider，对 `samples/calc#max` 跑 `scripts/llm_live_check.py`（schema 稳定性）+ 一次真实 `generate_pipeline`，落一份证据文档。验证现仅 fixture 的真实模型路径。
2. **真实仓库判卷验证**：选 2-3 个小型真实开源单模块 Maven 仓库，用 `scripts/run_judge.py` 跑 Phase 1，确认 build/test/coverage 真实可解析（补 `docs/09` §4 待办）。
3. **真实仓库 mini-benchmark**：对其中 1-2 仓的 3-5 个目标方法跑 Phase 2 真实生成，记录 compile/exec/coverage-delta/失败类型（成功+失败都记，`docs/07` §8 模板）。
4. **数据驱动的 Phase 3 设计修订**：用任务 3 的真实失败分布，重排 `docs/12` §4 的失败分类与确定性微修优先级（而非凭论文猜）。
5. **执行安全边界评估**：文档化"子进程跑任意 OSS 构建"的风险面与最小沙箱方案（容器/网络隔离），**先定边界，不一定实现**。

### 6.4 明确不做
- 不在真实输入验证前堆 Phase 3/4 复杂度（§四）。
- 不做 Gradle / 多语言 / IDE 插件 / 自动入仓 / mutation testing / 复杂 RAG / 知识图谱 / 重型 Agent 框架（`docs/00` §8、`docs/12` §3）。
- 不做多模块强制执行（`docs/00` §7.7 仅作增强项）。
- 不先做 Web 前端美化（`docs/07` A1）。
- 不在断言修复中弱化 oracle（`docs/07` A5）。

---

## 七、不确定项清单（须验证后才能下定论）

| 不确定项 | 当前证据缺口 | 验证方法 |
|---|---|---|
| 真实模型对本项目 prompt 的 schema 稳定性与生成质量 | 仅 `scripts/llm_live_check.py`，未进 CI、未留结果 | 配 key 跑 `python -m scripts.llm_live_check 5`，记录 N/N 与 has_assertion |
| 真实仓库 Phase 1 判卷成功率 | 无 committed 真实仓库运行 | `python -m scripts.run_judge <repo> <branch>` ×3 仓 |
| 真实仓库生成测试的 compile 通过率 | 仅 toy + fixture | 路线 A 任务 3 统计 |
| LLM 闭环成本/耗时 | 无任何数据 | 路线 A 记录 token/时延 |
| 执行安全实际严重度 | 未评估 | 任务 5 威胁建模 |
| 上下文收集在真实 DI/泛型/重载下是否够用 | 仅 toy 验证 `build_snapshot` | 路线 A 任务 3 观察编译失败归因 |

---

> 审计结论一句话：**方向正确、底座扎实、但"AI 在真实代码上是否管用"零证据。下一步不是 Phase 3，而是用真实模型 + 真实小仓库把这个核心命题先证伪或证实。** 完成本文档后暂停，等待 review。
