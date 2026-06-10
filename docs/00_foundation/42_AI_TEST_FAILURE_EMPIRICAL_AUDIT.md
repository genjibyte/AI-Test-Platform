# AI 单测失败模式实证审计 + 价值重定位（围绕 7 个问题）

> 日期：2026-06-08。性质：**实证审计 + 研究综合**（不写代码、不改逻辑、不跑模型）。
> 证据：项目 `var/benchmark/*/bench.db` 提取 n=80，**剔除 13 个 fake-client 占位样本后真实 n=67**（离线用 `assemble_generation_report` 复算）+ 外部同行评审文献 + 诚实空白。**复现与更正见 §A（2026-06-08 复现审计）。**
> 上级：`docs/00`、`docs/40`（判卷内核=产品）、`docs/41`（沉淀层）。

---

## 0. 重定位（接受用户判断）

真正的突破点**不是"做出完整平台"**，而是把这套**判卷 / 度量仪器**用于回答："AI 写的测试为什么 / 如何失败、哪些能工程自动拦、哪些必须人审、上下文 / 模型 / 覆盖率各自的真实效用。"

> **平台 = 仪器；产品 = 这些可沉淀、可比较的实证答案。** 这把 `docs/40`（判卷内核=产品）再 sharpen 一层：卖点是**结论**，不是软件齐全度。

---

## 1. 数据基线（硬事实，本审计依赖）

> **复现更正（2026-06-08，详见 §A）**：原始提取 n=80，但其中 **13 个是 fake-client 占位样本**（`dryrun1/2/3` + `manifest-dryrun`×10，源码含 `FAKE CLIENT PLACEHOLDER`，非真实模型输出）。**真实模型生成 n=67**，下表与全文已改用。**口径**：`gen_outcome`（编译/通过）是运行时历史事实；`quality_gate` 与 `recommendation` 是用**当前**判卷代码对历史源码**重算**（含风险感知降级），非当时输出。

真实模型生成 **n=67**（跨 v2/v3/v3.1/v3.2.x、flash/pro/deepseek）：

| gen_outcome | 数 | 占比 |
|---|---:|---:|
| TEST_FAILURE（跑了但断言失败） | 23 | 34% |
| COMPILE_FAILURE | 23 | 34% |
| PASS（编译+通过执行） | 17 | 25% |
| BUILD_ERROR / NO_TESTS | 4 | 6% |

| 质量门（重算，n=67） | 数 | 占比 |
|---|---:|---:|
| FAIL | 28 | 42% |
| REVIEW | 23 | 34% |
| PASS | 16 | **24%** |

**关键交叉（更正）**：17 个"编译+通过"里 **16 (94%) 过质量门，仅 1 REVIEW、0 FAIL**——**真实绿测被结构质量门判"无价值"= 0%**。（原 docs/42 的"43% 绿但无价值"系 fake-client 占位样本造成的**伪结论，已撤回**——见 Q2、§A。）审查推荐（重算）：REJECT 28 / NEEDS_REVISION 22 / REVIEW_CANDIDATE 17 / **STRONG 0**。

> 诚实标注：n=67 跨**异构配置**、多为**单样本**，数字是**方向性**，非统计显著。

---

## 2. 逐题解答

### Q1 AI 为什么生成编译不过的测试？（29%）
- **项目**：`docs/38` 把 23 个 COMPILE_FAILURE 归类——`cannot_find_symbol`×8（缺 import / 幻觉 API）、`overload_ambiguous`×8、`incompatible_types`×2（泛型）、`no_suitable_method`×1。**全是符号/类型/重载层"看似合理"的错，不是语法错。**
- **机理**：生成是 token 似然，不做符号解析 / 类型检查——不知道精确签名、重载集、泛型边界、可见性、Java 版本（`List.of`）。
- **文献**：SF110 上 LLM 可编译率仅 **2.7–12.7%**（Codex 最低 2.7%）[Schäfer]。我们靶向单方法 + 有界上下文把可编译率拉到 **~61%**（平台 `compiled` 口径＝`{PASS,TEST_FAILURE,NO_TESTS}/67`；若仅把 `COMPILE_FAILURE` 记为未编译则 66%），仍**远高于** whole-class baseline——上下文有效，但仍 **~34% `COMPILE_FAILURE`**。
- **落地**：大多数**可工程自动拦/修**（见 Q6）。

### Q2 AI 为什么生成"能跑但没价值"的测试？
- **项目（更正，撤回原结论）**：原 docs/42 称"12/28 (43%) 绿测被判 FAIL"——**这是 fake-client 占位样本（`no_assertions`）造成的伪结论，撤回**。真实样本里 **17 个编译+通过的测试，16 过质量门、0 被判 FAIL**（§A）。**项目数据不支持"AI 绿测大量无价值"。** 但注意：结构质量门只测断言**形态**，不测**语义 oracle 强度**——后者是人审红线、项目**未度量**，故"绿测语义上有没有价值"仍是开放问题（靠下方文献机理，不靠本项目数据）。
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
- **项目**：**仅 24% 过质量门**（真实 n=67），但只看 `target_improved`（覆盖提升）数字会高得多——**覆盖率高估价值**（方向性，非 mutation 量化）。项目据此已**把 coverage 降为 advisory、关掉覆盖率门**（`docs/14`、`docs/00` §5.2-8）。
- **诚实空白**：项目**没做 mutation**（Charter §8 禁），**无法给出"差距"的绝对值**，只能用"质量门通过率 vs 覆盖提升率"的落差作代理 + 文献定性结论。
- **落地**：**不要恢复 coverage 门当价值指标**；价值的可操作代理 = 质量门 + 人审推荐 + 账本"过门率 / badcase 复发率"。

---

## 3. 面向落地的总结（这才是产品）

一句话画像（**更正后，真实 n=67**）：**AI 测试 ~61% 编译 / 25% 通过执行 / 24% 过结构质量门；真实绿测被结构质量门判"无价值"= 0%（原"43%"系 fake 样本伪结论，已撤回）；语义 oracle 强度本项目未度量；失败分"语法层（可自动）"与"oracle 层（必人审）"两类；覆盖率系统性高估价值。**

**接下来该做的实验（非功能堆叠）**：
1. **多模型 × 同 manifest** 跑，喂账本 cross-author —— Q5 的唯一解法（结构已就绪）。
2. **多样本（每 case ≥5 次）** 量化"上下文 vX 对每类错误的真实下降" —— Q4 去噪。
3. （可选、越界）小规模 **mutation 子集**校准"覆盖率-价值差距"绝对值（需先松绑 Charter §8）。

**不该做**：再加 Context vX prompt 规则刷分；恢复 coverage 门；扩 oracle 自动修。

---

## 4. 诚实边界 / 不确定

- 原始 n=80 含 **13 个 fake-client 占位样本**；真实 n=67（§A）。跨异构配置、非受控；数字方向性，非显著。
- Claude / Codex **零数据**。
- 无 mutation → coverage-价值差距只能**定性**。
- prompt 合规**非确定性** → 单跑结论不可靠。

---

## A. 复现附录（reproducibility audit，2026-06-08）

### A.1 数据来源
- 库：`var/benchmark/*/bench.db`（28 个，glob）。表：`jobs`。列：`generation_json`（每 job 持久化的生成 bundle）。
- 取样：对每行 `generation_json` 做 `assemble_generation_report(json.loads(...))`，保留 `gen_outcome is not None` 的行（真正进入过生成阶段的 job）→ **n=80**。
- **污染**：13 行源码含 `FAKE CLIENT PLACEHOLDER`（`dryrun1/2/3` 各 1 + `manifest-dryrun` 10），非真实模型输出 → **真实 n=67**。

### A.2 最小复现命令
仓库根目录存为 `verify.py`，用项目 venv 运行：`& "E:\AI-Test-Platform\.venv\Scripts\python.exe" verify.py`

```python
import glob, json, sqlite3
from collections import Counter, defaultdict
from app.report.generation_report import assemble_generation_report  # 须在仓库根运行

rows = []
for db in sorted(glob.glob("var/benchmark/*/bench.db")):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    for r in c.execute("SELECT generation_json FROM jobs"):
        if not r["generation_json"]:
            continue
        gen = json.loads(r["generation_json"])
        rep = assemble_generation_report(gen)
        if rep.get("gen_outcome") is None:
            continue
        src = (gen.get("write") or {}).get("content") or (gen.get("result") or {}).get("test_source") or ""
        rows.append((rep["gen_outcome"], (rep.get("quality_gate") or {}).get("status"),
                     rep.get("review_recommendation"), "FAKE CLIENT PLACEHOLDER" in src))
real = [r for r in rows if not r[3]]
print("n_all", len(rows), "n_fake", sum(r[3] for r in rows), "n_real", len(real))
print("outcome", Counter(r[0] for r in real))
print("quality", Counter(r[1] for r in real))
ct = defaultdict(Counter)
for r in real: ct[r[0]][r[1]] += 1
print("PASS x quality", dict(ct["PASS"]))
```

### A.3 口径（定义）
| 指标 | 定义 | 来源 |
|---|---|---|
| `gen_outcome` | 存的 `execution.gen_outcome`（PASS/TEST_FAILURE/COMPILE_FAILURE/...） | **历史事实**（非重算） |
| compiled | `gen_outcome ∈ {PASS,TEST_FAILURE,NO_TESTS}`（平台 `_COMPILED`）；"loose"＝非 `COMPILE_FAILURE` | 派生 |
| passed | `gen_outcome == PASS` | 派生 |
| quality-gate | `evaluate_test_quality(...)` 的 status（PASS/REVIEW/FAIL） | **当前代码重算**历史源码 |
| recommendation | `recommend_with_reasons(...)`（含风险感知降级） | **当前代码重算**（非当时输出） |

> 关键：除 `gen_outcome` 外，**quality 与 recommendation 都是用当前判卷代码对历史源码重算**——STRONG=0 等是"今天标准回看历史"，不是当时标签。

### A.4 复现结果（raw vs real）
| | n | PASS | TEST_FAILURE | COMPILE_FAILURE | 其它 | compiled(strict) | passed | qPASS |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| raw（含 fake） | 80 | 28 | 23 | 23 | 6 | 66% | 35% | 20% |
| **real（去 fake）** | **67** | **17** | 23 | 23 | 4 | **61%** | **25%** | **24%** |

PASS×quality 交叉（real）：`{PASS:16, REVIEW:1, FAIL:0}` → 绿测结构无价值率 **0/17**。
raw 的 `{PASS:16, REVIEW:1, FAIL:11}` 中那 11 个 FAIL **全是 fake 占位样本**。

### A.5 代表性 badcase（真实样本）
1. **COMPILE_FAILURE** — `deepseek-pro-final` / `CSVRecord`：符号 / import 类（`cannot_find_symbol`，归类见 `docs/38`）。
2. **COMPILE_FAILURE** — `deepseek-pro-rerun` / `Option`：源码含 `import org.apache.commons.cli.Option.Builder`（内部类引用，符号类）。
3. **TEST_FAILURE（mock 误用）** — `deepseek-pro-final` / `Option`：`Cannot mock/spy ... final class DeprecatedAttributes`（Mockito 不能 mock final 类；`review_summary` 原文）。
4. **TEST_FAILURE（oracle 错）** — `deepseek-pro-final` / `WordUtils`：`expected=false actual=true`（断言与行为不符——是 bug 还是测试错？**必须人审**；`review_summary` 原文）。
5. **反例**：原"绿但无价值"的两个 example（`dryrun3`、`manifest-dryrun`）经查均 `FAKE CLIENT PLACEHOLDER` → 真实样本中该类 **= 0**。

### A.6 需降级 / 撤回的表述
| 原表述 | 处置 | 更正 |
|---|---|---|
| "绿测里 43% 无价值"（12/28） | **撤回** | 真实 0/17；原数系 fake 占位样本 |
| "~71% 编译" | **降级 / 明确口径** | strict 61% / loose 66%（real） |
| "35% 通过执行" | 更正 | 25%（real） |
| "仅 20% 过质量门" | 更正 | 24%（real） |
| "STRONG 0" | 加口径 | 成立，但属**当前** recommendation 重算 |
| n=80 "真实生成" | 更正 | 含 13 fake；真实 67 |

未受影响（仍可复现）：Q1 的 COMPILE_FAILURE 归类（`docs/38`）、Q4 的 v3.1 80% / v3.2.3 50%·20%（per-run not-CF 口径，real）、Q6 拦截边界、Q7 文献定性结论。

### A.7 外部引用定位
外部文献仅作**机理 / 对照支撑**，未替代项目数据：Q1（SF110 对照我们的 61%）、Q2·Q3（regression-oracle 机理；项目只证形态、不证语义）、Q7（Inozemtseva 定性；项目不做 mutation）。Q5 明确"项目零数据"，未用文献伪造项目结论。**结论：引用未越位。**

### A.8 一致性与 push 建议
- 计数（outcome / quality / recommendation）**完全可复现**；raw↔real 的差异根因＝fake 口径与分母。
- **建议先不 push**：本次更正后再 push 整条 `docs/40–42` 链，避免把含已撤回结论（43% 等）的旧版推上去。

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
