# 沉淀层设计（Precipitation / Accumulation Layer）- live contract

> 日期：2026-06-08。状态：P1/P2 已落地，`app/ledger/` 提供 judged-record 存储、
> badcase 聚合和只读查询；后续 `docs/50` 增加 retrieval。本文现在是 live contract +
> 历史设计记录，不批准新模型调用、新表扩张、自动采纳、自动修复或 verdict 变化。
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

> 结论：判卷事实的**原始沉淀已存在**。早期缺口是把这些事实**跨 run、跨作者**
> 统一成账本 + 失败签名聚合 + 比较视图；这个 P1/P2 缺口已由 `app/ledger/`
> 和相关测试覆盖。后续只允许在不改 verdict 的前提下补 compact carry 或只读视图。

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
    - `COMPILE_FAILURE` → 编译错误类（`cannot_find_symbol` / `overload_ambiguous` / `incompatible_types`，复用当前 failure taxonomy 的粗分类）；
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

## 7. 最小落地切片（每片小、可独立交付、可停；状态截至 2026-07-21）

| 片 | 内容 | 代码量 |
|---|---|---|
| **P0** | 定 `JudgedRecord` schema + 签名规则（**本文**） | 纯文档 |
| **P1** | `app/ledger/`：一张表 + `append(record)` + `from_bench_case_result(r, provenance)` 适配器；benchmark 跑完 append。**零判卷逻辑改动** | 小 |
| **P2** | badcase 聚合 + §5 的几个只读查询 | 小 |
| **P3** | author-agnostic 提交入口（doc 40 §6.2 `submit_candidate`）已由 docs/53 落地；**直接 append 账本**仍未自动化 | 小 |

顺序与 doc 40 §6 对齐。每片先有测试、离线可验。

---

## 8. 红线 / 不做（anti-drift；Charter §8 + doc 40 §5）

- 不做 KG、不做复杂 RAG、不做规则引擎 / 自动修复规则生成（Charter §8.10-11）。
- 不自动采纳、不自动改 oracle；badcase 仅记录 + 检索。
- 不把"生成量 / 生成质量"当账本 KPI；账本度量**判卷结果**，按作者中立比较。
- 不引新存储技术：复用 SQLite + pydantic。
- 不跑模型、不引新存储技术；已落地 ledger 仍保持只读聚合 / append-only 语义。

---

## 9. 待你拍板

1. 账本用**独立 durable 库**（`var/ledger.db`）还是扩展 `bench.db`？（建议**独立库**，跨 run 更清晰。）
2. ~~P1（表 + append）/ P2（badcase 聚合 + 查询）~~ **P1 + P2 已落地**（见 §10）。`submit_candidate` 入口已由 docs/53 落地；是否增加“外部提交自动 append 到 ledger”仍需单独设计。
3. badcase 签名粒度：**先粗**（`failure_type` + 目标）还是直接细（含 expected/actual 类名）？（建议**先粗**，避免过拟合，复发数据足够后再细化。）

---

## 10. 实现状态（P1 + P2 已落地，2026-06-08）

按 §7 **P1** 实现，**零判卷逻辑改动、离线、复用 SQLite + pydantic**：

- 新增 `app/ledger/`：
  - `models.py`：`Provenance` / `JudgedRecord` / `fingerprint_source`（sha256 of 归一化 source）。
  - `store.py`：`LedgerStore`（`append` + `by_target` / `by_author` / `by_fingerprint` / `count` / `all`；整条记录存 `record_json` + 索引列；`INSERT OR IGNORE` 幂等）。
  - `ingest.py`：`record_from_bench_case(result, provenance, test_source?)` 适配器 + `record_report(store, report, ...)`。
- `app/benchmark/runner.py`：跑完后 `_precipitate(report, workdir)` **best-effort** append（`$TESTAGENT_LEDGER_DB` 或 `<workdir>/../ledger.db`，即 `var/benchmark/ledger.db`，跨 run 共享）；**ledger 失败绝不影响 benchmark**。
- **P2（analytics）**：新增 `app/ledger/analytics.py`——`badcase_signature`（粗粒度 `failure_type@target`，PASS 返回 `None`）、`aggregate_badcases`（按签名分组排名：count / first·last_seen / authors / targets / examples）、`author_profile`（compile/pass 率 + recommendation 分布 + top badcase）、`compare_authors_on_target`（跨作者同 target 对照——"谁判得更好，而非谁生成得多"）、`ledger_summary`。**纯函数、读侧、确定性；不判卷、不生成规则**。结构审理结论：P1 内核（models/store）benchmark-free，coarse 签名由现成字段派生，**P2 零 P1/schema 改动**。
- 测试：`tests/test_ledger.py` 共 **10**（P1 5 + P2 5：签名、聚合排序、author 画像、跨作者对照、digest）；`tests/test_benchmark.py` 增 ledger 接线断言。全量 **225 passed, 4 skipped**。
- **未做（设计在案）**：`submit_candidate` 自动 append 到 ledger；真实 `test_source` 指纹自动接线（benchmark 记录暂 `None`，适配器已支持并测试，待提交/ingest 桥接）；细粒度 badcase 签名（expected/actual 类名，§4，无需改 schema）。

> 红线保持：判卷内核未改、账本独立库、不判卷 / 不采纳 / 不改 oracle / 不引新存储技术。

---

> 一句话：沉淀层不是新系统，而是**把已经在 `BenchCaseResult`/`bench.db` 里的判卷事实，升格为跨运行、跨作者、可查询、能识别复发失败的账本**——核心是判卷的"记忆"与"比较"，仍然 design-first、复用优先、不堆功能。
