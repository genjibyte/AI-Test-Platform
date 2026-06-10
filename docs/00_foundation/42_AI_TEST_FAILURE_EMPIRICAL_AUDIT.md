# AI 单测失败模式实证审计 + 价值重定位（围绕 7 个问题）

> 日期：2026-06-08。性质：**实证审计 + 研究综合**（不写代码、不改逻辑、不跑模型）。
> 证据：项目 `var/benchmark/*/bench.db` **真实 n=80 次生成**（离线用 `assemble_generation_report` 复算）+ 外部同行评审文献 + 诚实空白。
> 上级：`docs/00`、`docs/40`（判卷内核=产品）、`docs/41`（沉淀层）。

---

## 0. 重定位（接受用户判断）

真正的突破点**不是"做出完整平台"**，而是把这套**判卷 / 度量仪器**用于回答："AI 写的测试为什么 / 如何失败、哪些能工程自动拦、哪些必须人审、上下文 / 模型 / 覆盖率各自的真实效用。"

> **平台 = 仪器；产品 = 这些可沉淀、可比较的实证答案。** 这把 `docs/40`（判卷内核=产品）再 sharpen 一层：卖点是**结论**，不是软件齐全度。

---

## 1. 数据基线（硬事实，本审计依赖）

`bench.db` 全量 **80 次真实生成**（跨 v2/v3/v3.1/v3.2.x、flash/pro/deepseek）：

| gen_outcome | 数 | 占比 |
|---|---:|---:|
| PASS（编译+通过执行） | 28 | 35% |
| TEST_FAILURE（跑了但断言失败） | 23 | 29% |
| COMPILE_FAILURE | 23 | 29% |
| BUILD_ERROR / NO_TESTS | 6 | 7.5% |

| 质量门（全 80） | 数 | 占比 |
|---|---:|---:|
| FAIL | 41 | 51% |
| REVIEW | 23 | 29% |
| PASS | 16 | **20%** |

**关键交叉**：28 个"编译+通过"里只有 **16 (57%) 过质量门，12 (43%) 被判 FAIL**（绿但无价值）。审查推荐：REJECT 41 / NEEDS_REVISION 22 / REVIEW_CANDIDATE 17 / **STRONG 0**（风险感知降级后，无一条达"强候选"）。

> 诚实标注：n=80 跨**异构配置**、多为**单样本**，数字是**方向性**，非统计显著。

---

## 2. 逐题解答

### Q1 AI 为什么生成编译不过的测试？（29%）
- **项目**：`docs/38` 把 23 个 COMPILE_FAILURE 归类——`cannot_find_symbol`×8（缺 import / 幻觉 API）、`overload_ambiguous`×8、`incompatible_types`×2（泛型）、`no_suitable_method`×1。**全是符号/类型/重载层"看似合理"的错，不是语法错。**
- **机理**：生成是 token 似然，不做符号解析 / 类型检查——不知道精确签名、重载集、泛型边界、可见性、Java 版本（`List.of`）。
- **文献**：SF110 上 LLM 可编译率仅 **2.7–12.7%**（Codex 最低 2.7%）[Schäfer]。我们靶向单方法 + 有界上下文把可编译率拉到 **~71%**，远高于 whole-class baseline——**上下文确实有效，但仍 29% 挂**。
- **落地**：大多数**可工程自动拦/修**（见 Q6）。

### Q2 AI 为什么生成"能跑但没价值"的测试？
- **项目**：**12/28 (43%) 编译+通过的测试被质量门判 FAIL**（无断言 / 弱断言 / 同义反复 / 无目标引用）。"绿" ≠ "有价值"。
- **机理（文献）**：LLM 有**确认偏置**，生成**镜像实现行为的回归 oracle**而非对照规格的 spec oracle [2410.21136, 2601.05542]——断言"代码现在干了什么"自然能过，但**屏蔽 bug 而非发现 bug**。
- **落地**：结构性无价值（无断言 / 同义反复 / 只断言 mock）**可自动拦**（质量门 FAIL）；"断言的是不是正确的东西"**必须人审**。

### Q3 AI 为什么容易写弱断言？
- **机理 = oracle problem**：写强断言需知道**预期行为（规格）**，而 LLM 只看得到**实现**，于是退化为断言可观察输出。文献：弱/错断言在某些 benchmark 占 **>85% 的失败**；算术 / 循环场景断言正确率显著下降 [digrazia ASE2025；TOSEM 3699598]。
- **项目**：质量门的 `weak_assertion_heavy` / `tautology` / `no_obvious_target_reference`（`docs/19`）正是这类形态。
- **落地**：弱断言的**结构形态可自动拦**；**语义强度必须人审**（静态指标与动态有效性**无显著相关** → 只能靠人或 mutation）。

### Q4 给更多上下文后，错误类型减少了吗？（最有价值、也最诚实）
- **项目直接数据**：v2→v3（方法契约 grounding）降了**特定** compile 错误；但整体**非单调**：
  - `v3-pro-10case` {TF4, CF3, P2}；`v3_1-pro-10case` {TF4, CF2, P3, NT1}；`v3_2_3-pro-10case` {**CF5**, TF3, P2}。
  - v3.2.3 10-case **回归**到 compile 50% / pass 20%（v3.1 曾 80%）；BooleanUtils 在 v3.2.2 后**仍** `toBoolean(null)` 回归。
- **结论**：上下文对**特定错误类**（重载、异常语义）有**定向**效果，但**整体不单调**，且被 **n=10 单样本的非确定性淹没**；**prompt 合规本身不确定**。
- **落地**：**不能再靠"加 prompt 规则刷分"当主线**（`docs/40` §5 反漂移）；要用**多样本 + 账本（`docs/41`）量化每类错误的真实下降**，而非单跑凭感觉。

### Q5 Claude / Codex / DeepSeek / 自己 generator 失败模式差异？
- **诚实空白**：项目只系统跑过 **deepseek（flash/pro）+ 少量 openai**；**Claude / Codex 零基准**。现有只能说 flash→pro：pro 编译更稳，失败**从"编不过"前移到"oracle 错"**（TEST_FAILURE 占比升高）。
- **文献**：SF110 跨模型可编译率差异巨大（StarCoder 12.7% vs Codex 2.7%）→ 模型差异主要在**可编译率 + happy-path 倾向**。
- **落地**：这正是**已建的账本 cross-author 视图（`docs/41` P2 `compare_authors_on_target`）要回答的问题**——结构已就绪，**缺多模型 run**。**这是最该做的实验，而不是再调自己的 prompt。**

### Q6 哪些失败可工程自动拦，哪些必须人审？（核心可落地结论）

| 失败类 | 处置 | 机制 / 证据 |
|---|---|---|
| 缺 import / `List.of` / 方法局部枚举 | 自动**修**（确定性、oracle-safe） | compile-repair，`docs/38` |
| 重载消歧 / 未列方法 arity / 幻觉目标调用 | 自动**拦**（pre-Maven） | preflight，`docs/32,36` |
| 无断言 / 同义反复 / 弱断言形态 / 改生产码 | 自动**拦**（质量门 FAIL） | quality gate，`docs/19` |
| 泛型 `incompatible_types` / `no_suitable_method` | 编译器即真值，可提示；修复需谨慎 | `docs/38` |
| **TEST_FAILURE：是 bug 还是测试错？** | **必须人审** | 红线：不自动改 oracle |
| **断言语义强度（断言对了吗）** | **必须人审** | oracle problem，Q3 |

> 原则：**语法 / 结构 / 符号层 = 可自动；语义 / oracle / 规格层 = 必须人。** 这条线项目已用代码画出（preflight + 质量门 = 自动；review policy 恒 `NEED_HUMAN_REVIEW` = 人审）。

### Q7 coverage 提升和测试价值差距多大？
- **文献硬结论**：Inozemtseva & Holmes，ICSE 2014（ACM Distinguished Paper）——覆盖率与有效性**仅 low-moderate 相关（控制套件大小后）**，**不应作质量目标**；静态 oracle 指标与动态有效性**无显著相关** → 真正衡量需 mutation。
- **项目**：**仅 20% 过质量门**，但只看 `target_improved`（覆盖提升）数字会高得多——**覆盖率高估价值**。项目据此已**把 coverage 降为 advisory、关掉覆盖率门**（`docs/14`、`docs/00` §5.2-8）。
- **诚实空白**：项目**没做 mutation**（Charter §8 禁），**无法给出"差距"的绝对值**，只能用"质量门通过率 vs 覆盖提升率"的落差作代理 + 文献定性结论。
- **落地**：**不要恢复 coverage 门当价值指标**；价值的可操作代理 = 质量门 + 人审推荐 + 账本"过门率 / badcase 复发率"。

---

## 3. 面向落地的总结（这才是产品）

一句话画像（本项目仪器产出的实证）：**AI 测试 ~71% 编译 / 35% 通过执行 / 仅 20% 过质量门；绿测里 43% 无价值；失败分"语法层（可自动）"与"oracle 层（必人审）"两类；覆盖率系统性高估价值。**

**接下来该做的实验（非功能堆叠）**：
1. **多模型 × 同 manifest** 跑，喂账本 cross-author —— Q5 的唯一解法（结构已就绪）。
2. **多样本（每 case ≥5 次）** 量化"上下文 vX 对每类错误的真实下降" —— Q4 去噪。
3. （可选、越界）小规模 **mutation 子集**校准"覆盖率-价值差距"绝对值（需先松绑 Charter §8）。

**不该做**：再加 Context vX prompt 规则刷分；恢复 coverage 门；扩 oracle 自动修。

---

## 4. 诚实边界 / 不确定

- n=80 跨异构配置、非受控；数字方向性，非显著。
- Claude / Codex **零数据**。
- 无 mutation → coverage-价值差距只能**定性**。
- prompt 合规**非确定性** → 单跑结论不可靠。

---

## 来源（外部、同行评审、无营销）

- Inozemtseva & Holmes, *Coverage is not strongly correlated with test suite effectiveness*, ICSE 2014（ACM Distinguished Paper）— https://dl.acm.org/doi/10.1145/2568225.2568271
- Schäfer et al., *An Empirical Evaluation of Using LLMs for Automated Unit Test Generation*, arXiv:2302.06527（IEEE TSE）— https://arxiv.org/abs/2302.06527
- *On the Evaluation of LLMs in Unit Test Generation*, arXiv:2406.18181（ASE 2024）— https://arxiv.org/html/2406.18181v1
- *Using LLMs to Generate JUnit Tests: An Empirical Study*, arXiv:2305.00418 — https://arxiv.org/pdf/2305.00418
- *Do LLMs generate test oracles that capture the actual or the expected program behaviour?*, arXiv:2410.21136 — https://arxiv.org/html/2410.21136v1
- *Understanding LLM-Driven Test Oracle Generation*, arXiv:2601.05542 — https://arxiv.org/pdf/2601.05542
- Di Grazia et al., *Do LLMs Generate Useful Test Oracles?*, ASE 2025 — https://www.lucadigrazia.com/papers/ase2025.pdf
- *Exploring Automated Assertion Generation via LLMs*, ACM TOSEM — https://dl.acm.org/doi/10.1145/3699598
- *Test Oracle Automation in the Era of LLMs*, ACM TOSEM — https://dl.acm.org/doi/10.1145/3715107
