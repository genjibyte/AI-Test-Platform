# Phase 3 修复闭环 —— 开源工具 / Skill / 知识库选型调研

> 上级文档：`/docs/00_foundation/00_PROJECT_CHARTER.md`、`/docs/00_foundation/07_SOURCE_NOTES.md`、`/docs/20_phase2/09_PHASE2_BACKLOG.md`、`/docs/20_phase2/11_PHASE2_ACCEPTANCE_REPORT.md`。
> 日期：2026-06-06。
> 性质：**纯调研文档**。不安装任何依赖、不改任何代码、不写实现。仅给出"引入/不引入"建议。
> 范围：Phase 3 = 失败分类 + 有限 Fixer（**≤3 轮**）+ patch 历史 + badcase 落库（`docs/07` §5 Phase 3）。

---

## 0. 评估前提（决定取舍的硬约束）

1. **技术形态**：Python 编排后端 + Java/Maven/JUnit5/Mockito 被测目标。任何"Java 侧工具"都要从 Python 跨进程调用，集成成本天然偏高。
2. **红线**（继承 `docs/00` §8、`docs/07` P5/A5）：
   - ❌ 不改被测**生产代码**（排除一切 APR 自动程序修复工具）。
   - ❌ 不改/删**既有测试**；修复只能动**本次生成的那一个**测试文件。
   - ❌ 不靠**弱化断言**修复（限制"盲翻断言/替换期望值"类确定性模板）。
   - ❌ 不做复杂 RAG / 知识图谱 / 重型 Agent 框架（`docs/00` §8、`docs/09` §0.2）。
   - ❌ 不做 mutation testing（`docs/00` §8）。
   - 🔒 ≤3 轮修复；密钥不入库不写日志；不自动入仓。
3. **现状可复用资产**：`app/build`（mvn 执行 + `BuildOutcome` 分类）、`app/report/surefire_parser`（栈解析）、`app/context/class_index`（项目内类的 FQN 索引）、`app/context/java_parser`（**正则**轻量解析，非 AST）、`app/llm`（隔离的 LLM 客户端）、`app/storage`（SQLite）。
4. **痛点**（`docs/00` §5.2）：import 幻觉、不懂构造/泛型/类型、错误 Mock、边界/异常不足、缺执行验证、失败无系统化修复与沉淀。

> 结论先行：**Phase 3 的痛点 90% 落在"读懂编译器/栈错误 → 定点小修 → 再执行"这条确定性回路上，而这条回路用现有资产即可搭建，几乎不需要新引入第三方工具。** 详见 §4、§6。

---

## 1. 可直接使用的确定性工具

> 判据：确定性（同输入同输出）、可离线、与红线不冲突、能直接接入现有 Python 编排。

### 1.1 Maven 编译器 / Surefire 结构化诊断（**已在仓内，强烈复用**）
- **是什么**：`mvn test-compile`（仅编译，比全量 `test` 快）产出 `[ERROR] <file>:[line,col] <message>`；Surefire 产出失败栈。是失败分类的"事实来源"。
- **收益**：失败分类的骨架；零新依赖；确定性；`test-compile` 反馈快。直接支撑 TestART 式 8 类错误识别（见 §2.1）。
- **风险**：编译器措辞随 JDK/locale 变化（本项目已强制 `-Dproject.build.sourceEncoding=UTF-8` 缓解 GBK 乱码）；需维护正则鲁棒性。低。
- **集成成本**：**低**。复用 `app/build` + 新增纯 Python 分类器模块即可。

### 1.2 项目类索引 `class_index`（**已在仓内，复用**）
- **是什么**：现有的"项目内类 → FQN/文件"索引。对应 TestART 模板 T1 的"项目内符号"子集。
- **收益**：直接修复最高频的"缺 import / 符号未找到（项目内类型）"；已存在、确定性。
- **风险**：不覆盖 JDK / 第三方符号（无 classpath 索引）；但 JUnit5/Mockito 的 import 是**固定已知集合**，可用静态映射表补上。
- **集成成本**：**低**。

### 1.3 Python 标准库 `difflib`（**stdlib，复用**）
- **是什么**：生成 patch / 每轮 diff 的统一 diff 文本。
- **收益**：patch 历史与 badcase 的 diff 全部 stdlib 解决；零依赖、确定性。
- **风险**：无。
- **集成成本**：**低**。

### 1.4 py-tree-sitter + tree-sitter-java（**可选增强，暂不引入**）
- **是什么**：Python 绑定的增量解析器，对生成测试文件产出 CST，精确定位 import/标识符/断言节点做定点编辑。比 JavaParser 快约 36×（[symflower](https://symflower.com/en/company/blog/2023/parsing-code-with-tree-sitter/)）。
- **收益**：比正则鲁棒的结构化编辑；为"插入 import / 定点改写"提供可靠锚点；只解析单个测试文件，范围天然受控。
- **风险**：引入**原生依赖**（需 wheel/构建）、grammar 版本要 pin；CST **无语义/类型解析**，单靠它无法判定"该 import 哪个 FQN"，仍需 `class_index`；当前痛点用正则已能覆盖，收益边际。
- **集成成本**：**中**。新依赖 + 节点查询代码。
- **建议**：列为**触发式增强**——当正则修复在真实仓库上证明不够鲁棒时再引入。

### 1.5 javalang（纯 Python Java 解析，**可选，暂不引入**）
- **是什么**：纯 Python 的 Java AST 解析库。
- **收益**：无原生构建；易取 import/方法节点。
- **风险**：维护较弱，对新语法（record/sealed/var）可能解析失败；无类型解析。
- **集成成本**：**低-中**。
- **建议**：相对 1.4 更轻但更脆，二选一时优先 tree-sitter；当前都不引入。

### 1.6 OpenRewrite（rewrite-maven-plugin：`RemoveUnusedImports` / `OrderImports`，**暂不引入**）
- **是什么**：Moderne 的确定性重构引擎，自带 import 卫生 recipe，且支持 `mvn rewrite:dryRun` 不改 build 跑（[OpenRewrite Docs](https://docs.openrewrite.org/)、[Remove unused imports](https://docs.openrewrite.org/recipes/java/removeunusedimports)）。
- **收益**：成熟、确定性的 import 整理；可干掉"未用 import"类编译告警/错误。
- **风险**：**重**（拉插件 + recipe 工件 + JVM 启动）；recipe 默认**仓库级**作用，若不严格限定到那一个生成文件，**有触碰生产代码/既有测试的红线风险**；对"幻觉类"缺失 import，`AddImport` 仍需你给出 FQN（它不会凭空发明），语义解析需完整 classpath 类型归因——为单文件修复属牛刀杀鸡。
- **集成成本**：**高**（插件配置 + 文件级范围限定 + 边界守卫）。
- **建议**：**不引入**。其能力用 1.1+1.2 的轻量组合即可覆盖 Phase 3 所需子集。

### 1.7 google-java-format / Spotless（**不引入**）
- 仅格式化，不修编译/运行错误，对修复闭环价值边际。**不引入**。

---

## 2. 只适合参考设计的开源项目 / 论文 / 博客 / 知识库

> 判据：拿来**抄设计**，不作为运行期依赖。

### 2.1 TestART（arXiv 2408.03095，**首要蓝本**）
- **价值**：给出可直接对标的**失败分类 + 修复模板**：
  - 编译类：cannot find symbol / 方法调用错误 / 访问越权 / 语法错误 / 抽象类实例化。
  - 运行类：assertNull↔assertNotNull、assertTrue↔assertFalse、assertEquals 值不符、未捕获异常、测试失败。
  - 5 个确定性模板：T1 查包补 import（索引 JDK+依赖定位 FQN）、T2 翻转断言、T3 用实际执行值替换期望、T4 try-catch 包裹、T5 补 catch；模板失败后**一次性 LLM 兜底**；**≤4 轮**；用 JUnit+覆盖率+栈日志反馈。
- **对本项目的启示**：先确定性模板、后 LLM 兜底、轮次受限——与 Phase 3 设计高度一致。**但 T2/T3（翻转断言/替换期望）触碰"弱化 oracle"红线，须谨慎或交给 LLM 带理由修，而非盲改。**
- **引入方式**：**仅参考**，不依赖其代码。

### 2.2 YATE: The Role of Test Repair in LLM-Based Unit Test Generation（arXiv 2507.18316）
- **价值**：系统论证"修复"在 LLM 测试生成中的作用与边界，指导轮次/收益取舍。**仅参考**。

### 2.3 CoverUp（arXiv 2403.16218）
- **价值**：把"未覆盖代码"作为反馈喂给 LLM。更偏 Phase 2/4，但其**反馈构造**思路可用于 Fixer 的上下文组织。**仅参考**。

### 2.4 Meta TestGen-LLM
- **价值**：assured 生成——**凡不编译/不通过/不提升覆盖的测试一律丢弃**。直接印证本项目"判卷先于采纳 + Phase 4 门禁"的过滤哲学。**仅参考**。

### 2.5 Self-Refining LLM Unit Testers（Medium, 2025-12）
- **价值**：实践向的"错误引导式迭代修复"写法，可作 Fixer 提示词与回路工程的参照。**仅参考**。

### 2.6 已纳入 `docs/07` 的来源（Uber AutoCover / Airbnb 迁移 / 快手 / 微软 TiCoder·TestExplora）
- **价值**：Airbnb 的"分步 + 每步验证 + 重试 + 失败聚类"、Uber 的 Preparer→Generator→Executor→Validator→Fixer 专业化分工，是 Phase 3 编排的上位设计。**仅参考**（已是项目知识库）。

### 2.7 EvoSuite / Randoop / Diffblue Cover（**仅参考，不依赖**）
- **价值**：确定性/搜索式（EvoSuite、Randoop）与商用反射式（Diffblue）Java 测试生成，提供失败分类、回归 oracle、修复回路的对照设计。
- **不依赖原因**：范式不同、JVM 重、许可/闭源（Diffblue 商用），与"LLM 生成器"定位竞争。

### 2.8 OpenRewrite 文档（作为**能力参照**）
- 即便不引入，其 recipe 列表也能告诉你"哪些 Java 改写可被确定性化"，用于规划本项目自研的定点小修边界。**仅参考**。

---

## 3. 不建议引入的"过重 / 过于滞后 / 触红线"候选

| 候选 | 不引入原因 |
|---|---|
| **APR 自动程序修复**（GenProg / Astor / Nopol / Arja） | 修复对象是**生产代码**，直接违反红线 ❌；学术、JVM 重、维护滞后。 |
| **Mutation testing**（PIT/PITest） | `docs/00` §8 明确不做；且非修复工具，是质量度量。 |
| **重型 Agent 框架**（LangChain / DSPy / SWE-agent / OpenHands / Aider / AutoGen） | 过度工程，违反"LLM 隔离在单模块、不引复杂框架"；版本动荡、黑箱重；Fixer 用现有 `app/llm` 足矣。 |
| **RAG / 向量库 / 知识图谱**（LlamaIndex / Chroma / KG） | `docs/09` §0.2 红线禁复杂 RAG/KG；Phase 3 badcase 用 SQLite 足够，过早泛化。 |
| **EvoSuite 作为运行期依赖** | 范式冲突、LGPL、JVM agent，与 LLM 生成器重叠。 |
| **Diffblue Cover 作为依赖** | 商用/闭源，不可控。 |
| **JavaParser + SymbolSolver（Java 侧）** | 需从 Python 跨进程跑 Java 符号解析服务，重；tree-sitter / class_index 更轻。 |

---

## 4. 对本项目 Phase 3 的"最小最能解决痛点"引入方案

> 目标：用**最少新依赖**覆盖最高频失败。核心结论是 —— **本期不引入任何第三方运行期工具**，全部用现有资产 + stdlib 搭建确定性回路；第三方工具列为"触发式增强"。

### 4.1 推荐落地组合（全部复用现有资产）
1. **失败分类器（新增纯 Python 模块）**：对 `mvn test-compile`/Surefire 输出做结构化解析，映射到对标 TestART 的失败类目：
   `MISSING_IMPORT/CANNOT_FIND_SYMBOL`、`METHOD_NOT_FOUND`、`CONSTRUCTOR_MISMATCH`、`TYPE_MISMATCH`、`MOCKITO_STUB_ERROR`、`ASSERTION_FAILURE`、`UNCAUGHT_EXCEPTION`、`TEST_DATA`、`UNKNOWN`。依赖：仅 `app/build`+`app/report`。
2. **确定性微修（仅限最安全子集，作用域=本次生成测试文件）**：
   - 缺 import 且为**项目内类型** → 用 `class_index` 解析 FQN 补全；
   - JUnit5/Mockito 等**固定 import** → 静态映射表补全。
   - ⚠️ **不做**盲目翻转断言 / 替换期望值（红线 A5）——断言类失败一律交 LLM 带理由修。
3. **LLM Fixer（复用 `app/llm` 隔离层）**：输入 = {失败类目 + 编译/栈摘要 + 当前测试 + 上一轮 diff}，输出新测试；**≤3 轮**；每轮经现有 runner 真执行；成功或 3 轮失败即止。
4. **patch 历史 + badcase（复用 `app/storage`）**：新增列/表存每轮 diff（`difflib`）、失败类目、轮次、最终结果；不引向量库。

### 4.2 触发式增强（**本期不引入**，写明触发条件）
- **py-tree-sitter**：当正则定点修在真实开源仓库上**反复误伤/漏改**时引入，换取鲁棒结构化编辑。
- **classpath 符号索引**：当"JDK/第三方符号缺失"成为高频失败时，构建依赖 jar 的类索引（可由 `mvn dependency:build-classpath` 派生），补全 T1 在项目外符号的能力。
- **OpenRewrite**：仅当需要**仓库级** import 卫生且能严格限定文件范围时——Phase 3 不需要。

---

## 5. 候选项汇总评分（收益 / 风险 / 集成成本 / 结论）

| 候选 | 类别 | 收益 | 风险 | 集成成本 | 结论 |
|---|---|---|---|---|---|
| Maven 编译器/Surefire 诊断 | 1 | 高（分类骨架） | 低 | 低 | ✅ 本期引入（复用） |
| `class_index`（项目内 FQN） | 1 | 高（修高频 import） | 低（不覆盖外部符号） | 低 | ✅ 本期引入（复用） |
| `difflib`（patch/diff） | 1 | 中（patch 历史） | 无 | 低 | ✅ 本期引入（stdlib） |
| py-tree-sitter + java grammar | 1 | 中（鲁棒编辑） | 中（原生依赖/无语义） | 中 | ⏸ 触发式，暂不引入 |
| javalang | 1 | 中 | 中（新语法脆） | 低-中 | ⏸ 暂不引入（劣于 tree-sitter） |
| OpenRewrite import recipes | 1 | 中 | 高（范围溢出触红线） | 高 | ❌ 不引入 |
| google-java-format/Spotless | 1 | 低 | 低 | 低 | ❌ 不引入（价值边际） |
| TestART（论文） | 2 | 高（分类+模板蓝本） | —（仅参考） | — | 📖 参考 |
| YATE / CoverUp / TestGen-LLM | 2 | 中-高（修复/反馈/过滤设计） | — | — | 📖 参考 |
| Self-Refining（博客）/ docs07 来源 | 2 | 中（回路工程） | — | — | 📖 参考 |
| EvoSuite / Randoop / Diffblue | 2 | 中（对照设计） | 范式/许可 | 高 | 📖 参考，不依赖 |
| APR（GenProg/Astor/Nopol/Arja） | 3 | — | 改生产码红线 | 高 | ❌ 不引入 |
| Mutation testing（PIT） | 3 | — | 越界 §8 | 中 | ❌ 不引入 |
| Agent 框架（LangChain/SWE-agent…） | 3 | — | 过度工程/动荡 | 高 | ❌ 不引入 |
| RAG/向量库/KG | 3 | — | 越红线/过早 | 中-高 | ❌ 不引入 |

---

## 6. 结论

### 6.1 Phase 3 当前**应引入**（全部为现有资产/stdlib，零新第三方运行期依赖）
1. **复用 Maven `test-compile` + Surefire 诊断**作为失败分类事实来源。
2. **复用 `class_index` + 静态 import 映射**做最安全子集的确定性补 import。
3. **复用 `app/llm` 隔离层**做 LLM Fixer，**≤3 轮**、每轮真执行。
4. **复用 `app/storage` + `difflib`**做 patch 历史与 badcase 落库。
5. **以 TestART 为首要设计蓝本**（失败类目 + "先确定性后 LLM 兜底 + 轮次受限"），辅以 YATE / TestGen-LLM / CoverUp / docs07 来源。

### 6.2 Phase 3 当前**不应引入**
- OpenRewrite、google-java-format/Spotless（价值边际/范围溢出风险）。
- py-tree-sitter、javalang、classpath 符号索引（列为**触发式增强**，满足明确触发条件再议）。
- 一切 APR、mutation testing、重型 Agent 框架、RAG/向量库/知识图谱（越红线或过度工程）。

> 一句话：**Phase 3 不靠"引入新工具"取胜，而靠"把编译器/栈的确定性反馈 → 定点小修 → 受限 LLM 兜底 → 真执行验证 → 落库沉淀"这条回路用现有积木搭扎实。** 第三方工具均设为可延后的增强项，避免在闭环未稳前过早增加依赖与红线风险。

---

## 来源（Sources）

- [TestART: Improving LLM-based Unit Testing via Co-evolution of Automated Generation and Repair Iteration (arXiv 2408.03095)](https://arxiv.org/html/2408.03095v6)
- [YATE: The Role of Test Repair in LLM-Based Unit Test Generation (arXiv 2507.18316)](https://arxiv.org/html/2507.18316v1)
- [CoverUp: Coverage-Guided LLM-Based Test Generation (arXiv 2403.16218)](https://arxiv.org/html/2403.16218v3)
- [Self-Refining LLM Unit Testers: Iterative Generation and Repair via Error-Guided Feedback (Medium, 2025-12)](https://medium.com/@floralan212/self-refining-llm-unit-testers-iterative-generation-and-repair-via-error-guided-feedback-7c4afd7f5f55)
- [OpenRewrite Docs](https://docs.openrewrite.org/) · [Remove unused imports](https://docs.openrewrite.org/recipes/java/removeunusedimports) · [Order imports](https://docs.openrewrite.org/recipes/java/orderimports) · [rewrite-maven-plugin](https://docs.openrewrite.org/reference/rewrite-maven-plugin)
- [py-tree-sitter](https://github.com/tree-sitter/py-tree-sitter) · [tree-sitter-java grammar](https://github.com/tree-sitter/tree-sitter-java) · [Parsing code with Tree-sitter (symflower, 36× vs JavaParser)](https://symflower.com/en/company/blog/2023/parsing-code-with-tree-sitter/)
