# Prompt/Context v2 —— 针对真实失败的最小落地

> 角色：Prompt/Context v2 负责人。日期：2026-06-06。
> 上级：`docs/00`、`docs/07`、`docs/13`、`docs/15`、`docs/16`。
> 性质：设计 + 最小实现 + 测试。**不进 Phase 3、不写自动修复、不改生产码/pom/既有测试、不跑真实模型（除非你确认）。**

---

## 1. 当前状态

- v2 已最小实现并通过测试：**127 passed, 4 skipped**（新增 14 项）。
- 设计**直接对准** Phase 2.5 实测的 5 类失败（`docs/15`/`docs/16`），不是泛泛“更长 prompt”。
- 未跑真实模型；是否重跑 3-case 见 §7（已给命令/成本/预期，等你确认）。

## 2. 调研资料摘要（每条注明对 v2 的启发；区分事实/参考；标注不确定）

| 资料 | 类型 | 对 v2 的启发 |
|---|---|---|
| Mockito 5 inline mock-maker（[InfoQ](https://www.infoq.com/news/2023/01/mockito-5/)、[Baeldung](https://www.baeldung.com/mockito-core-vs-mockito-inline)） | **可直接用的事实** | Mockito ≥5.0.0 默认 inline maker 才能 mock final 类；<5.0.0 不能。故 bucket 4 规则是**条件式**：除非邻测证明可行，否则不 mock final/value 类（**不确定**：我们未解析目标仓 Mockito 版本，安全默认=不 mock、构造真实对象） |
| LLM oracle 幻觉（[arXiv 2410.21136](https://arxiv.org/pdf/2410.21136)、[2601.05542](https://arxiv.org/html/2601.05542v1)） | 可直接用的事实 | 即使明确指示，LLM 仍频繁产出语义错的 oracle → 必须允许**跳过**而非硬猜 |
| ChatTester/TestChain 的 derive-then-assert（同上检索） | **参考设计思想** | 先按方法源码逐步推导期望值、再写断言，可降低逻辑幻觉 → v2 oracle 规则采用 |
| 多智能体共识（CANDOR，[arXiv 2506.02943](https://arxiv.org/pdf/2506.02943)） | 参考（不采纳） | 多模型投票治 oracle，但属重型多 agent，违反本项目红线，仅备查 |
| TestART 模板修复（`docs/12`，[arXiv 2408.03095](https://arxiv.org/html/2408.03095v6)） | 参考设计思想 | 失败分类法与“先确定性后 LLM”——属 Phase 3，本期只在 prompt 侧前移预防 |
| JUnit5 Assertions / Surefire / JaCoCo / Apache Commons 源码 | 可直接用的事实 | `assertNotSame`/`assertThrows` 属 `org.junit.jupiter.api.Assertions` 静态导入；方法内 enum 在 Java<16 非法 → v2 硬规则 |

> 不堆链接：以上每条都落到具体规则；未直接引用 EvoSuite/Randoop/Diffblue/Copilot/TestSpark 的实现，仅作为“判卷优先 + 回归 oracle 风险”的背景参考（EvoSuite 的“断言当前行为”正是我们**禁止**自动做的事，作为反例）。

## 3. Prompt/Context v2 设计

### 3.1 system prompt v2（角色 + 硬规则，确定性、与上下文无关）
落在 `app/generate/prompt_builder.py:SYSTEM_PROMPT`。要点（每条对应一个失败桶）：
- **[API grounding]** 只用上下文出现的类型/方法/构造器/常量；不臆造方法/重载/字段；缺则跳过并记 `omitted_uncertain_cases`；嵌套类写 `Owner.Nested`。
- **[Imports]** `test_source` 必须是**自包含可编译**文件：package + 所有 import，**每个用到的 JUnit 断言都要静态导入**（示例 `assertNotSame`）。
- **[Build/language]** 禁止方法体内声明 enum/class/interface（要就做测试类的 private static 嵌套类型）；不 mock final/value 类，且**邻测没 mock 就不准 mock**（点明 Mockito 需 inline maker，不得假设）；禁网络/绝对路径/时间/随机。
- **[Oracle grounding]** 每个期望值必须从**证据**（目标方法源码或邻测样例）推导；推不出就跳过，不猜；禁同义反复断言；断行为而非实现细节。
- **[Test strategy]** 少而高置信；一测一行为；避免大 `@BeforeEach`；禁 `assertNotNull` 充数。

### 3.2 user prompt / context template v2
落在 `build_user_prompt(context)`。结构（context block）：
```
Target class / Target method / Package
Imports available on the target class
Fields / Constructors / Public-Protected methods (use ONLY these)
Nested types (reference as Owner.Nested)      <-- v2 新增
Target method source (derive oracles from this)
Neighbor test (style + mock reference, 含 bounded 源码片段)   <-- v2 增强
Maven dependencies
<OUTPUT_CONTRACT v2>
```
`build_prompt = build_system_prompt + "\n\n" + build_user_prompt`（向后兼容单字符串，`dry_generate` 不变）。

### 3.3 metadata schema（`app/llm/schema.py`，全部可选、默认空 → 向后兼容）
| 字段 | 作用 |
|---|---|
| `used_apis` | 用到的目标 API；每个必须在上下文出现（**自检**，压 API 幻觉） |
| `behavior_sources` | 每个非平凡 oracle 的证据来源（压 oracle 幻觉） |
| `omitted_uncertain_cases` | 主动跳过、未猜的 case（给模型“跳过”的出口） |
| `dependency_assumptions` | 假设的 JUnit/Mockito 事实（暴露风险假设） |
| `risk_flags` | 自报风险动作（如仍 mock 了某类）→ 报告呈现给人审 |

### 3.4 与 Prompt v1 的差异表
| 维度 | v1 | v2 |
|---|---|---|
| 结构 | 单段 prompt | system（规则）+ user（上下文）拆分 |
| API 约束 | “不要臆造 import/构造/返回类型” | “只用上下文 API，缺则跳过”，+ `used_apis` 自检 |
| 嵌套类 | 无 | 解析并列出 `Owner.Nested` + 硬规则 |
| 导入 | 仅列目标类 import | 要求 test 自包含 + 每个断言静态导入（举例 `assertNotSame`） |
| 语言级 | 无 | 禁方法内类型声明 |
| Mock | “JUnit5 + Mockito only” | 条件式：邻测没 mock 就不 mock；点明 final/inline maker |
| Oracle | “meaningful assertions” | derive-then-assert + 推不出就跳过 + 禁同义反复 |
| 邻测 | 仅方法名列表 | + bounded 源码片段（风格/мock 模仿） |
| 输出 | imports/test_source/scenarios/mocks/notes | + 5 个 grounding 元数据字段 |

### 3.5 v2 如何具体避免当前 5 类失败
| 失败（证据） | v2 对策 |
|---|---|
| import 缺失 `assertNotSame`/`Stream`（flash Option / pro CSVRecord，`docs/16` §2.1/2.2） | “自包含 + 每个断言静态导入”规则 + `imports` 必列全 + `used_apis` 自检 |
| 嵌套类未限定 `Builder`（flash Option，`docs/16` §2.1） | 解析 `nested_classes` → 上下文列 `Option.Builder` + “写成 Owner.Nested”规则 |
| 方法内 local enum（flash CSVRecord，`docs/16` §2.2） | “禁止方法体内声明类型”硬规则（不需解析 source level 即可消除） |
| mock final `DeprecatedAttributes`（pro Option，`docs/16` §2.1） | 条件式 mock 规则 + 邻测片段（无 mock 即禁）+ `risk_flags` 暴露 |
| oracle 猜错 `abbreviate/wrap/...`（flash/pro WordUtils，`docs/16` §2.3） | derive-then-assert + 证据不足跳过（`omitted_uncertain_cases`）+ 禁同义反复 |

## 4. 实际修改文件（最小集，每个改动小）

| 文件 | 改动 | 目的/桶 |
|---|---|---|
| `app/models/java_source.py` | 加 `nested_classes: List[str]` | 桶 2 数据 |
| `app/context/java_parser.py` | 提取嵌套类型名（并修正“嵌套类头被误判为 field”的旧 bug） | 桶 2 |
| `app/models/context_snapshot.py` | `NeighborTestSummary.source_excerpt` | 桶 4 + 风格模仿 |
| `app/context/context_collector.py` | 填 bounded 邻测片段：import 摘要 + 第一个 `@Test` 附近源码 | 桶 4 + 模仿 |
| `app/generate/prompt_builder.py` | **v2 重写**：system/user 拆分、嵌套块、邻测片段、build/oracle 规则、v2 契约 | 全部 5 桶 |
| `app/llm/schema.py` | `LLMTestPayload`/`TestGenerationResult` 加 5 个可选 metadata + `assemble_result` 透传 | 自检/人审 |
| `app/report/generation_report.py` | 报告新增 `grounding`（used_apis/omitted/risk_flags/deps_assumptions） | 判卷优先/人审 |

**不改**：`generation.py`、`llm/client.py`、`openai_client.py`（client 接口不动，v2 system 内容随单字符串 prompt 进 user 消息——最小、稳定；真正的 system-message 化列为后续）；`generate_pipeline.py`、`test_writer.py`、`gen_executor.py`、`benchmark/*`、`models/job.py`、pom、生产代码、既有测试。

**风险**：
- system 规则随 user 消息发送（非独立 system role）——影响小于理想，但零 client 改动、最稳。
- 邻测片段不再取文件头固定截断，而是保留 import 摘要并拼入第一个 `@Test` 附近源码；真实 Apache 仓库抽样均包含 `@Test`/断言。calc prompt 3818 字符，距 `<4000` 测试上限仅 182 余量（偏紧，记录在案）。
- 嵌套类提取是启发式（regex），复杂泛型/注解嵌套可能漏，但默认空、不致命。

## 5. 测试命令与结果

```powershell
# 受影响子集
.\.venv\Scripts\python.exe -m pytest tests/test_prompt_builder.py tests/test_java_parser.py `
  tests/test_generation.py tests/test_llm_layer.py tests/test_context_collector.py `
  tests/test_generation_report.py -q       # 50 passed
# 全量
.\.venv\Scripts\python.exe -m pytest -q     # 127 passed, 4 skipped
```
新增测试把每条 v2 规则钉到对应失败桶（`tests/test_prompt_builder.py`）、验证嵌套提取与不再误判为 field（`tests/test_java_parser.py`）、验证 metadata 可选向后兼容且透传（`tests/test_llm_layer.py`）。

## 6. 验收标准自检

| 标准 | 结论 |
|---|---|
| 直接针对真实失败 | ✓ §3.5 五桶逐一映射 |
| 不只是更长 prompt | ✓ 结构化 + 解析新增（嵌套/邻测片段）+ 自检 metadata，非堆字 |
| 降低 6 类风险 | ✓ API 幻觉/import/嵌套/local enum/mock final/oracle 均有规则或数据 |
| 保留“判卷优先，不让 LLM 当验证者” | ✓ 未改判卷；metadata 是模型**自报**供人审，不作通过依据；`trusted=False` 不变 |
| 符合 docs/00/07/13/16 | ✓ 最小、不进 Phase 3、不弱化断言、不自动改 expected |
| 结论有证据 | ✓ 引用 benchmark report/log、官方文档、本仓文件 |

## 7. 是否现在重跑 3-case benchmark？

**建议重跑**——这是验证 v2 是否抬高 compile 率的唯一办法，且最便宜。**但按你的规则，先给命令/成本/预期，等你确认，我不擅自跑。**

精确命令（沿用 `docs/14` 策略；`.env` 已配 deepseek + 跳过策略插件/JaCoCo）：
```powershell
$env:TESTAGENT_MAVEN_CMD="C:\Users\lenovo\AppData\Local\Programs\Maven\apache-maven-3.9.9\bin\mvn.cmd"
$env:TESTAGENT_MVN_EXTRA_ARGS="-Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dlicense.skip=true -Denforcer.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dpmd.skip=true -Djacoco.skip=true"
# flash 对照（便宜）：.env 设 TESTAGENT_LLM_MODEL=deepseek-v4-flash
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/v2-flash
# pro 对照：.env 设 TESTAGENT_LLM_MODEL=deepseek-v4-pro
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/v2-pro
```
- **成本范围**：每档 3 个真实模型调用（whole-class，输出可能仍偏大），约等于上一轮（分钱级）；时长每档约 3–6 分钟（pro 更慢）。两档共约 6 次调用。
- **预期**（诚实）：
  - compile 率应上升：Option（import/嵌套）、CSVRecord（local enum/Stream）是 v2 直接打的点；flash 33%、pro 67% 有望提高。
  - WordUtils 这类 **oracle 失败大概率仍在**：prompt 能让模型多“跳过”（`omitted_uncertain_cases` 增多、断错变少），但不能根治；`gen_test_pass_rate` 可能仍低。
  - 可能出现新形态：模型为守规则而**跳过更多** → 个别 case 变 `NO_TESTS`（这是预期内的诚实退化，比硬猜更好）。
- **对照方法**：与 `var/benchmark/deepseek/`、`var/benchmark/deepseek-pro-final/` 同 spec 比 `compile_pass_rate`、`top_failure_types`、`omitted_uncertain_cases`。

## 8. 下一步：进 Phase 3 还是继续 prompt/context？

**先不进 Phase 3。** 顺序应为：**v2 重跑量化 → 看 compile 率与残余失败桶 → 再决定**。
- 若 v2 把 compile 率显著抬高且残余主要是 oracle：Phase 3 的价值进一步下降（oracle 不该自动修），应转向 **Phase 4 最小质量门禁**（弱断言/同义反复/oracle mismatch → reject/review）。
- 若 compile 失败仍顽固（import/符号/语法类残留）：才进 **Phase 3 最小编译修复器**（只修编译、≤3 轮、只改生成测试，按 `docs/16` §5）。
- 与 `docs/16` §9 边界一致：先 prompt/context（已做）+ 重跑；compile 仍失败再进 Phase 3 最小编译修复，不做全能 fixer、不自动改 oracle。

> 结论：v2 已落地并测试通过，针对 5 类真实失败、最小影响、Phase 2 主流程稳定。**等你确认是否按 §7 重跑**；在拿到 v2 的真实 compile 率前，不建议进 Phase 3。
