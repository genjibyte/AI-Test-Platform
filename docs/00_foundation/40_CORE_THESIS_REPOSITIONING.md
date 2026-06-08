# 核心理念再审计与重定位：判卷场，而非生成器

> 日期：2026-06-08。角色：技术负责人（方向审计）。性质：**理念审计 + 最小重定位设计**。
> 边界：不写代码、不改生产逻辑、不跑模型、**不新增功能**、**不覆盖既有文档**（本文 sharpen + 交叉引用 Charter，不回写 Charter）。
> 证据规则：每个判断标注代码/文档/commit。
> 触发：用户指令——平台核心优势是**管理 / 判卷 / 审计比较 / 沉淀（人或 agent 写的单测结果）**，不是"生成单测"本身；把"生成"从主卖点降为链路中的一个普通环节；避免偏离与堆功能。

---

## 0. 一句话结论

1. 这**不是改方向**，而是**回到 Charter 的北极星**：`docs/00` §3.6（"最大价值不是生成测试，而是判定 AI 生成测试是否工程可用"）、§6、`docs/07` P1（"Build the judge before the generator"）。近期投入**漂移**到"把我们自己的生成器调得更好"。
2. 真正的**扩展**：判卷对象从"本平台 AI 生成的测试"扩为"**任意来源的候选测试**（人 / 本平台生成器 / 外部 agent）"。
3. 关键事实（好消息）：**判卷内核已基本与"生成"解耦**（§3 证据），所以重定位 ≈ **解耦 + 一个统一入口 + 改名/重述 + 重排优先级**，**几乎不需要新功能**。

---

## 1. 漂移审计：我们偏到哪了

| 投入 | 文档/证据 | 属于 |
|---|---|---|
| Context v3 → v3.1 → v3.2 → v3.2.1/.2/.3 | `docs/25-31,35,37` | 生成侧（让产物更好） |
| preflight 重载消歧 | `docs/32,33,34,36` | 生成侧（拦我们生成器的坏调用） |
| compile-repair 加固 | `docs/38,39` | 生成侧（修我们生成器的编译失败） |

- 近十余篇文档/多次提交集中在**生成侧**：核心动机是"让本平台生成器的产物编译更好、pass 更高、修复更安全"。
- 对照之下，"管理 / 判卷 / 比较 / 沉淀"这层（**真正的核心**）相对少投入；且**至今没有"提交一个已存在 / 外部测试来判卷"的入口**——只能"先生成、再判卷"。
- 澄清：生成侧工作并非无价值（preflight/repair 的 oracle-safety 本就是**判卷红线**的一部分）。问题是**权重失衡**——把"生成质量"当主线，违反 Charter §3.6。

---

## 2. 现状其实已接近北极星（内核已解耦——证据）

| 判卷能力 | 函数（签名要点） | 是否依赖"生成" | 证据 |
|---|---|---|---|
| 执行判卷 | `execute_generated_test(repo_dir, workspace, generated_class, …)` —— 只需 FQCN + 路径，跑磁盘上**任意**测试 | **否** | `app/generate/gen_executor.py:122` |
| 质量门 | `evaluate_test_quality(source, *, execution, coverage_delta, …)` —— 吃原始 `source` 字符串 + 执行事实 | **否** | `app/quality/test_quality_gate.py:220` |
| 覆盖率对比 | `compare(before, after, …)` —— 纯覆盖率 | 否 | `app/coverage/coverage_compare.py` |
| preflight | `evaluate_generated_test_preflight(source, snapshot)` —— 吃 source + 目标上下文 | 否（依赖目标上下文，非生成器） | `app/quality/generated_test_preflight.py` |
| 审查建议/摘要 | `recommend_with_reasons(...)` / `build_review_summary(generation=…)` —— 吃 execution/quality 事实（grounding 可选） | 基本否（仅**命名**为 generation） | `app/review/review_policy.py` |

**真正与"生成"耦合的，只有三处：**
1. **入口**：只有 `run_generation`（先生成后判），没有 author-agnostic 的"提交测试来判卷"。
2. **命名**：`generation` bundle、`gen_outcome`、`TestGenerationResult`、`write_generated_test(result)`。
3. **比较**：benchmark 只驱动**本平台生成器**，按 model/version 对照（`app/benchmark/runner.py`），无"按作者对照"。

> 结论：**判卷内核就是产品；生成器是一个可插拔的 producer。** 平台约 80% 的代码已站在正确一侧——重定位是把剩下 20% 的**入口/命名/比较**对齐，而非重建。

---

## 3. 核心抽象（最小，不堆功能）：来源无关的"候选测试"

定义一个**来源无关的候选提交（Candidate / Submission）**作为平台一等公民：

```text
Candidate = {
  target:      { repo, ref, target_class, target_method? },
  test_source: <Java 测试源码>,                 # 人 / agent / 本平台生成器 都只是一段源码
  provenance:  { author_type: human | platform_generator | external_agent,
                 author_id:  "alice" | "deepseek-v3" | "copilot" | "evosuite" | ...,
                 model? / prompt_version? / notes? },
  grounding?:  <可选；仅生成器/agent 自报，advisory>
}
```

统一判卷链路（**已存在**，只需把入口做成 author-agnostic）：

```text
Candidate
  -> 复用 Phase 1 judged repo
  -> 写入隔离 src/test（人/agent 的测试就是一个文件）
  -> preflight（source + 上下文）
  -> execute（mvn test + Surefire + JaCoCo）
  -> coverage compare
  -> quality gate
  -> review recommendation + summary（含 oracle / 永不自动采纳 等不变量）
  -> 记录 / 沉淀（bench.db + 报告）
```

**生成器降级为一个 producer**：`run_generation` 产出一个 `provenance.author_type = platform_generator` 的 Candidate，然后走**同一条**判卷链路；人 / 外部 agent 走**同一条**链路，只是 producer 不同。判卷内核**完全不变**。

---

## 4. 四大核心：现状与缺口（管理 / 判卷 / 比较 / 沉淀）

| 核心 | 现状（已有） | 缺口（真正该补的核心，而非生成侧） |
|---|---|---|
| **管理 Manage** | 项目/任务/状态机/持久化：`app/models/job.py`、`app/storage/job_repo.py`、`judge_pipeline.py` | 以 **Candidate 为一等公民**的列表/检索（按 target / 按 author / 按结论） |
| **判卷 Judge** | 执行+质量门+preflight+审查，已基本解耦（§2） | **author-agnostic 入口**（`submit_candidate` / `judge_existing_test`） |
| **比较 Compare** | benchmark/aggregate 已能对照（按 model/version）：`app/benchmark/` | **按作者对照**（human vs agentA vs agentB vs 本平台）在同一 target/rubric 上——把现有 aggregate 加一个 provenance 维度，**非新系统** |
| **沉淀 Precipitate** | bench.db + 报告 = 原始沉淀；失败分类已有 | **badcase 库 / 失败归因 / 跨运行·跨作者可复用判定经验**——Charter §7.16-17 **仅文档、未实现**（`docs/13` §2.3） |

> 真正值得投入的核心前沿是**沉淀层**（失败归因 + badcase 库 + 跨作者比较），**不是再调 prompt**。

---

## 5. 反漂移护栏（防止再堆功能）

**单一判据（每个新需求都先过这关）：**

> 这个功能是让**判卷 / 管理 / 比较 / 沉淀对任意来源的测试更强**，还是只是让**我们自己的生成器产物更好看**？后者一律降级 / 封顶。

落实：

- **生成侧进入维护模式**：Context vX prompt 调优、新 repair bucket、新 preflight 规则——**仅当它修复判卷红线**（oracle-safety、误判/误杀）才做；纯粹提升生成 compile/pass 率的微调**不再作为主线**。
- **北极星指标改述（sharpen Charter §6）**：从"AI 生成测试是否经判卷"扩为——
  > **任意来源的候选测试，是否经过同一套确定性判卷，并形成可比较、可沉淀的可审查结果。**
- **重申不做**（Charter §8 + 本次）：不把"生成器质量"当 KPI；不为提升 pass 率引入更激进 repair / 触碰 oracle；不堆多语言/Gradle/IDE/CI/企业特性。

---

## 6. 最小重定位路线（**设计，不实现**；每步都小、复用优先）

1. **命名/概念解耦（纯文档，零代码，现在即可）**：文档与 API 叙述统一用 Candidate/Submission + provenance，明确"生成器 = 一个 producer"。
2. **author-agnostic 入口（小代码，未来按需）**：新增 `submit_candidate(judged_job, test_source, provenance)`，**复用**现有 execute → compare → quality → review；`run_generation` 改为"生成 Candidate 后调用统一判卷"。**判卷内核不动。**
3. **按作者比较（小改 aggregate/report，未来按需）**：benchmark 增 provenance 维度，支持同 target 多作者对照。
4. **沉淀层（核心前沿，另行先设计后实现）**：失败归因 + badcase 库（SQLite + `difflib`，Charter §7.16-17）。

> 第 1 步是纯叙述、现在就能做；第 2-4 步都**小**且**先设计后实现**。**本文不实现任何代码。**

---

## 7. 对当前未决项的影响（重排，不新增）

- **compile-repair enablement（`docs/39`）**：保持 gated off。它属生成侧，**不再是主线**；oracle-safety 加固已是判卷红线的收尾。除非判卷需要，否则不启用。
- **coverage 子集恢复（roadmap #11）**：覆盖率是**判卷的 advisory 度量**，属核心层；可在重定位后作为"判卷度量"补回，**优先级高于再调生成**。
- **Context vX**：进入维护模式（§5）。

---

## 8. 红线 / 不做（重申）

- **已小幅回写 Charter**（2026-06-08，获用户"允许小幅度修改"授权）：sharpen `docs/00` §0 / §2 / §3.6 / §6 / §11 为 author-agnostic 口径（**保留原意、仅澄清 + broaden、未重写、未删原句**）。其余 Charter 结构不动；§1 暂保留原措辞。
- 本次仅审计 + 设计：不写代码、不改生产逻辑、不跑模型、不加功能。
- 判卷红线不变：**永不自动采纳**、不自动改 oracle、不改生产代码、结论恒 `NEED_HUMAN_REVIEW`、`trusted=False`。

---

## 9. 待你拍板

1. 认可"**生成器 = producer、判卷内核 = 产品**"的重定位与 §5 北极星改述？
2. ~~是否允许回写 Charter？~~ **已授权并完成**（2026-06-08 小幅 sharpen `docs/00` §0/§2/§3.6/§6/§11，保留原意）。如需进一步调整措辞或扩展到 §1，请指出。
3. **沉淀层**（badcase / 失败归因 / 跨作者比较）是否作为下一个**功能**投入方向？（设计已起草：`docs/50_benchmark/41_PRECIPITATION_LAYER_DESIGN.md`，仍先设计后实现，待你批准 P1 切片。）

> 一句话：方向没错，错在**重心**。把"判卷/管理/比较/沉淀任意来源测试"重新摆到正中央，生成器退回到"链路中的一个 producer"；而这条路**主要靠解耦与重述，不靠堆功能**。
