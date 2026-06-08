# 沉淀层设计（Precipitation / Accumulation Layer）

> 日期：2026-06-08。性质：**设计（design-first）**。**不写代码、不跑模型、不建表、不新增功能**——本文只定模型与切片。
> 上级：`docs/00`（Charter §5.2-9、§7.16-17）、`docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md`（§4 把"沉淀"列为核心前沿）。
> 红线：复用优先、最小新增；不做 KG / 复杂 RAG / 规则引擎（Charter §8）；不自动采纳、不自动改 oracle。
> 触发：用户"继续"——落地 doc 40 §6.4 / §9-3 提出的、design-first 的沉淀层。

---

## 0. 一句话

沉淀层 = 一个**来源无关、跨运行、可查询**的判卷结果账本（ledger）+ **失败签名库（badcase）** + **跨作者比较视图**；**复用**已有 `BenchCaseResult` 事实与 `classify_failure` taxonomy，最小新增。它度量的是"**判卷结果**"，不是"生成了多少 / 生成得多好"。

---

## 1. 已有什么（复用清单，避免重建）

| 资产 | 已含内容 | 证据 |
|---|---|---|
| `BenchCaseResult` | 全部判卷事实：baseline、gen_outcome、compiled/executed/passed、coverage delta、failure_type、quality（status/blockers/warnings）、review_recommendation、review_summary、conclusion、model、repair_rounds、runtime | `app/benchmark/models.py:66` |
| `classify_failure` + `FAILURE_TYPES` | 11 桶失败 taxonomy（log-aware，含 JaCoCo/policy-plugin 反遮蔽） | `app/benchmark/models.py:19,119` |
| `aggregate(cases)` | 跨 case 指标：`top_failure_types`、`recommendation_distribution`、compile/pass/coverage 率 | `app/benchmark/models.py:152` |
| `bench.db` `jobs.generation_json` | 每个 job 持久化完整 bundle（含 `test_source`、execution、`review_summary`） | `app/storage/db.py`、`app/storage/job_repo.py` |

> 结论：判卷事实的**原始沉淀已存在**。`badcase`/`ledger`/`provenance` 在代码中**零实现**（仅文档计划，`docs/13` §2.3）。缺的是把这些事实**跨 run、跨作者**统一成账本 + 失败签名聚合 + 比较视图。

---

## 2. 缺口（为什么现状还不算"沉淀"）

1. **按 run 分库**：每次 benchmark 写各自 `var/benchmark/<run>/bench.db`，无统一跨 run 查询。
2. **无 author 维度**：只有 `model`（= 本平台生成器模型），无法按"人 / agentA / agentB / 生成器"归并（doc 40 的 author-agnostic 主张落不到数据上）。
3. **无 badcase 签名库**：有 per-case `failure_type`，但无"同一失败模式跨 run/作者复发 N 次"的聚合 + 归因 + 检索。
4. **无跨作者比较一等视图**：现在靠人工比对多个 report。
5. **无候选指纹**：无 `test_source` hash，识别不出"这条之前见过 / 同一候选再次提交"。

---

## 3. 最小数据模型：来源无关的判卷记录

```text
JudgedRecord = {
  record_id, created_at,
  target:     { repo_url, ref/commit, target_class, target_method? },
  provenance: { author_type: human | platform_generator | external_agent,
                author_id, model?, prompt_version?, run_id? },
  test_fingerprint,            # sha256(normalized test_source) -- 去重/复现
  judging:    <BenchCaseResult 判卷事实子集：gen_outcome, compiled, executed, passed,
               coverage deltas, failure_type, quality(status/blockers/warnings),
               preflight.status, review_recommendation + reasons, conclusion>,
  badcase_signatures: [ <见 §4> ],
}
```

- 存储：**一张 SQLite 表 + 一个 durable 库**（如 `var/ledger.db`），benchmark / 单次生成 / 人工提交都向**同一账本 append**。复用现有 `sqlite + pydantic`（`app/storage/db.py` 模式），不引新技术。
- `judging` 直接由现成 `BenchCaseResult` 投影——**零新判卷计算**。

---

## 4. Badcase 签名库（失败经验沉淀）

- **签名 = 确定性、去标识的 key**，全部从已有事实派生（**零新模型**）：
  - 主桶：`failure_type`（`FAILURE_TYPES`）。
  - 细化：
    - `TEST_FAILURE` → 取 `review_summary.failures` 的 `{type(failure|error), 归一化的 expected/actual 类名 或 异常类型}`；
    - `COMPILE_FAILURE` → 编译错误类（`cannot_find_symbol` / `overload_ambiguous` / `incompatible_types`，复用 `docs/38` 归类）；
    - `preflight` → blocker code。
  - 例：`TEST_FAILURE/error/exception=ArrayIndexOutOfBoundsException @ CSVRecord#getInt`、`COMPILE_FAILURE/overload_ambiguous @ BooleanUtils#toBoolean`。
- **Badcase 记录**：`{signature, count, first_seen, last_seen, examples[record_id], authors_affected[], targets_affected[]}`。
- **价值**：跨 run/作者的**复发频率 + 归因**；reviewer 一眼看到"这是第 N 次同类失败、哪些作者都栽在这"。对齐 Charter §5.2-9、§7.16-17。
- **红线**：badcase 只**记录 + 检索**；**不自动生成修复规则、不自动改 oracle**。规则化（rule KB）留后、人审。

---

## 5. 查询 / 视图（沉淀层真正的产品价值，全部来自已存事实）

- **按 target**：某 target 下所有候选（跨作者）的判卷结果并排比较（compile/pass/coverage/quality/recommendation）。
- **按 author**：某作者（人 / agentX / 生成器vY）的可用率画像 + 其复发 badcase。
- **跨作者比较**：同一 `target × rubric`，human vs agentA vs 生成器——**谁的判卷结果更好，而非谁生成得多**。
- **Badcase 排行**：跨账本 top 复发失败签名 + 归因。
- **去重 / 复现**：按 `test_fingerprint` 识别重复候选与历史结论。

---

## 6. 与现有 benchmark 的关系（复用，不替换）

- benchmark **不消失**：它是**一个 producer + batch runner**，跑完把 `BenchReport.cases` append 进账本（带 `provenance.author_type=platform_generator` + `run_id`）。
- `aggregate()` 复用并加一个 **author 维度切片**。
- 即：**沉淀层 = 把 benchmark 的 per-run 聚合，提升为 cross-run / cross-author 的持久账本 + badcase 库 + 比较视图**。绝大部分逻辑复用。

---

## 7. 最小落地切片（每片小、可独立交付、可停；**本文不实现**）

| 片 | 内容 | 代码量 |
|---|---|---|
| **P0** | 定 `JudgedRecord` schema + 签名规则（**本文**） | 纯文档 |
| **P1** | `app/ledger/`：一张表 + `append(record)` + `from_bench_case_result(r, provenance)` 适配器；benchmark 跑完 append。**零判卷逻辑改动** | 小 |
| **P2** | badcase 聚合 + §5 的几个只读查询 | 小 |
| **P3** | author-agnostic 提交入口（doc 40 §6.2 `submit_candidate`）直接 append 账本——人/外部 agent 测试也进沉淀 | 小 |

顺序与 doc 40 §6 对齐。每片先有测试、离线可验。

---

## 8. 红线 / 不做（anti-drift；Charter §8 + doc 40 §5）

- 不做 KG、不做复杂 RAG、不做规则引擎 / 自动修复规则生成（Charter §8.10-11）。
- 不自动采纳、不自动改 oracle；badcase 仅记录 + 检索。
- 不把"生成量 / 生成质量"当账本 KPI；账本度量**判卷结果**，按作者中立比较。
- 不引新存储技术：复用 SQLite + pydantic。
- 本文 **design-only**：不写代码、不跑模型、不建表。

---

## 9. 待你拍板

1. 账本用**独立 durable 库**（`var/ledger.db`）还是扩展 `bench.db`？（建议**独立库**，跨 run 更清晰。）
2. 是否按 §7 的 **P1** 先落"一张表 + append 适配器"（最小、可停、零判卷改动）？
3. badcase 签名粒度：**先粗**（`failure_type` + 目标）还是直接细（含 expected/actual 类名）？（建议**先粗**，避免过拟合，复发数据足够后再细化。）

> 一句话：沉淀层不是新系统，而是**把已经在 `BenchCaseResult`/`bench.db` 里的判卷事实，升格为跨运行、跨作者、可查询、能识别复发失败的账本**——核心是判卷的"记忆"与"比较"，仍然 design-first、复用优先、不堆功能。
