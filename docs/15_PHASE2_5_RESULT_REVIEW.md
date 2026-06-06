# Phase 2.5 结果复盘与下一阶段设计决策

> 上级文档：`docs/00`、`docs/07`、`docs/13`、`docs/14`。
> 日期：2026-06-06。性质：复盘 + 决策，**不写代码、不调用模型、不提交**。
> 证据源：`var/benchmark/smoke/`、`var/benchmark/deepseek/`（report + 各 case 的生成测试与 Maven 日志，均在 `var/`，gitignore，可本地复现）。
> 模型：`deepseek-v4-flash`（注：非用户口头提的 `deepseek-v4-pro`；见 §10 不确定项）。

---

## 0. 一句话结论

**真实模型 × 真实仓库的最小验证已达成；结果是 0/3 测试开箱可用（2 编译失败、1 编译过但 16/34 断言错）。这用真实数据证明了项目痛点真实存在，并指出下一步最高性价比是先做 prompt/context 优化（治编译失败），而非立刻上 Phase 3 fixer。**

---

## 1. 真实模型是否跑通？（Q1）

**是。** 端到端跑通：鉴权 → 真实生成 → schema 校验 → 写盘 → 真实 `mvn` 判卷 → 分类。
- 证据：`var/benchmark/deepseek/report.md` 头部 `provider: openai  model: deepseek-v4-flash`；`setup_failures: 0  clone_failures: 0  repo_build_failures: 0`（无 harness/网络/构建层失败）。
- smoke 先行验证一致：`var/benchmark/smoke/report.md` 同样 judged ✓、schema ✓、产出报告。
- 无 `LLM_CONFIG_FAILED` / `LLMOutputError`：模型返回均通过 `LLMTestPayload` 契约（否则会落 `PIPELINE_FAILED`，实际未出现）。

## 2. 每个 case 的结果（Q2）

来源：`var/benchmark/deepseek/report.md` 每行 + 各 ws 的 `logs/mvn-test-jacoco.log` 与生成测试文件。

| case | judged | compiled | passed | failure | 真实根因（带证据） | ms |
|---|---|---|---|---|---|---|
| commons-cli `Option` | ✓ | ✗ | ✗ | COMPILE_FAILURE | `OptionAiGeneratedTest.java:[90]` 用 `Builder` 未限定（应 `Option.Builder`）；`:[196]` `assertNotSame(Option,Option)` 未静态导入 | 56735 |
| commons-csv `CSVRecord` | ✓ | ✗ | ✗ | COMPILE_FAILURE | `CSVRecordAiGeneratedTest.java:[99],[109]` `枚举类型不能为本地类型`（方法内声明 local enum，项目 Java 源级别不允许） | 72719 |
| commons-text `WordUtils` | ✓ | ✓ | ✗ | TEST_FAILURE | 编译并运行 **34 个测试、16 失败**（`TEST-...WordUtilsAiGeneratedTest.xml`），全为**期望值猜错**：`uncapitalize` 期望 `foo BAR` 实得 `foo bAR`；`abbreviate` 期望 `abc...` 实得 `abcdef...`；`wrap` 期望换行实得未换行；`containsAllWords` 期望 true 实得 false | 231437 |

> 旁注：WordUtils 日志里出现 `sun.nio.ch.Net.connect0` 网络栈，来自 **commons-text 自身**的 StringLookup/DNS 测试，**非**生成测试（生成测试 16 个失败全是 `AssertionFailedError`，0 error）。不影响本 case 归因。

## 3. 失败类型分布（Q3）

来源：`var/benchmark/deepseek/report.md` 聚合段。
- `compile_pass_rate: 33%`（1/3 编译过）、`gen_test_pass_rate: 0%`（0/3 完全通过）。
- `top_failure_types: {COMPILE_FAILURE: 2, TEST_FAILURE: 1}`。
- `coverage_measured: 0/3`（按 Phase 2.5 策略跳过 JaCoCo，覆盖率轴本期不测，见 `docs/14` §8）。
- 对照 smoke（1 case，亦 COMPILE_FAILURE）：Option 在 smoke 与 3-case 两次跑出**不同**编译错误（smoke：`setObjectType`/`setType(Object)` 幻觉方法；3-case：`Builder`/`assertNotSame`）——说明模型**非确定性**，具体错点会变，但"编译不过"这一类稳定复现。

**归到 `docs/12` TestART 失败学**：cannot-find-symbol（Option）、语法/语言级（CSVRecord local enum）、assertEquals 值不符（WordUtils ×16）。

## 4. 失败来自哪里？（Q4）

逐项归因（model / prompt / context / 目标选择 / 仓库构建 / harness）：

| 失败 | 归因 | 依据 |
|---|---|---|
| Option：`Builder` 未限定 + `assertNotSame` 未导入 | **prompt+context+model** | 模型未限定嵌套类、漏导入断言方法；当前 prompt 虽禁臆造 import，但未强约束"嵌套类用外类限定/列全所需静态导入" |
| CSVRecord：local enum | **model**（次：context） | 方法内 enum 是模型代码坏味；若 context 告知项目 Java 源级别可能规避，但根本是模型生成了非法结构 |
| WordUtils：16 个期望值错 | **model** | 模型不知道 `WordUtils` 真实语义，凭空猜 oracle；无执行反馈纠正（这正是"判卷场"要抓的：看似正确实则错） |
| —（无） | **harness** | `setup/clone/repo_build_failures=0`；3 仓均 judged=True；分类正确 |
| —（无） | **目标选择** | 3 个目标类全部解析成功（无 `PIPELINE_FAILED`） |
| —（无） | **仓库构建策略** | skip 策略插件 + jacoco.skip 生效，3 仓基线判卷通过 |

**结论**：失败**全部来自模型/prompt/context 侧，没有一例来自 harness、构建策略或目标选择**。这说明 Phase 2.5 的工程底座是可信的，问题集中在"喂给模型的约束/上下文"与"模型本身能力"。

## 5. 痛点是否真实存在？（Q5）

**真实，且被实证。** `docs/00` §5.2 列的 AI 生成单测新痛点，本次逐条命中：
- "看起来正确但编译不过" → 2/3 COMPILE_FAILURE；
- "import 幻觉 / 不理解构造、类型" → Option 嵌套类未限定、漏导入；
- "happy path、缺执行验证" → WordUtils 16 个 oracle 猜错，只有真实执行才暴露；
- "覆盖率提升不等于有效" → 本次连编译/通过都过不了，遑论覆盖率。

且印证 `docs/07` P1/A2："判卷先于生成""不让 LLM 当验证者"——确定性判卷正确地判定了 AI 产物**不可直接采纳**（0/3 通过，全部 `NEED_HUMAN_REVIEW`）。

## 6. 是否满足"真实模型 × 真实仓库"最小验证目标？（Q6）

**满足。** 目标（`docs/13` 路线 A / §6.3 任务 1-3）要求：真实模型 + 真实仓库 + Phase 2 全链路 + 记录 compile/exec/失败类型。本次：
- 真实模型 `deepseek-v4-flash` ×真实 3 仓（commons-cli/csv/text）；
- 全链路：判卷→上下文→生成→写盘→执行→分类→报告；
- 产出可量化失败分布（§3）与逐 case 归因（§2/§4），**成功与失败都记录**（`docs/07` A4）。
- 唯一缩水项：覆盖率轴本期按策略不测（`coverage_unavailable`），属已知取舍非缺陷。

## 7. 下一步最有实际价值的是什么？（Q7）

按"性价比 = 收益/成本"排序，**以真实失败分布为依据**：

1. **首选：prompt/context 优化（治编译失败）。** 
   - 依据：2/3 失败卡在**编译**（第一道门），且根因是可由约束/上下文消除的类别——嵌套类限定、补全静态导入、"只用上下文出现过的方法"、声明项目 Java 源级别（治 local enum）。
   - 成本低（不动架构），可用现有 benchmark **重跑量化**是否把 compile_pass_rate 从 33% 抬高。
2. **其次：Phase 3 fixer（治残余编译错）。**
   - 依据：即便优化 prompt，仍会有 cannot-find-symbol 残留；定点 fixer（补 import / 限定符号）对 Option 类失败收益明确（`docs/12` TestART T1）。
   - 但 **oracle 失败（WordUtils 16 个）是硬骨头**：靠"把 expected 改成实际返回值"修复 = 弱化断言，违反 `docs/07` A5/P5，会造出"测了个寂寞"的同义反复测试。故 fixer 应**只修编译/符号类，不自动改断言**。
3. **再次：扩 benchmark（提升统计可信度）。**
   - 依据：当前 n=1/仓，且模型非确定性（§3），3 个数据点不足以给稳定 rate。扩到 5-8 仓/多目标能让 compile/pass 率有意义。
4. **最后：恢复 coverage 策略。**
   - 依据：覆盖率是 Phase 2 既有能力，但在"连编译都过不了"时优先级最低；待 compile_pass_rate 起来后再恢复（无自带 jacoco 的仓库，或弹性 runner）。

> 即：**先 prompt/context（最便宜、打编译这道主门）→ 再 Phase 3 fixer（只治符号/编译，不碰 oracle）→ 扩 benchmark 量化 → 最后补 coverage。** 不建议跳过 prompt 直接堆 fixer。

## 8. 三条后续路线（Q8）

### A. 保守（最小可讲项目，~1-2 周）
- 做：prompt/context 优化 1-2 轮 + 把 benchmark 扩到 5-8 case，重跑量化 compile_pass_rate 变化；产出"判卷场 + 最小生成器在真实仓库的实证报告"（含失败分布与归因）。**不做 Phase 3。**
- 叙事：判卷先于生成；真实数据证明 AI 单测开箱 0/3 可用、主因编译与 oracle 幻觉；prompt 约束可量化改善编译率。
- 风险：低。最坏是优化收效有限——**本身也是诚实结论**。

### B. 标准（高质量，~100 天）
- 做：A + Phase 3 fixer（**仅** import/符号/语法类，≤3 轮，patch/badcase，数据驱动自 benchmark）+ Phase 4 最小质量门禁（**弱断言/同义反复 oracle 检测** → ACCEPT/REJECT/REVIEW，正好接住 WordUtils 这类）+ 恢复 coverage（jacoco-free 仓或弹性 runner）+ 5-8 仓 benchmark。
- 价值：达成 `docs/00` §9 完整 MVP，且每层有真实数据支撑。
- 风险：中。守住"不靠弱化断言修复"红线是关键。

### C. 激进（企业 PoC，高风险）
- 做：B + 多模型对比（flash vs pro vs 其它）+ TestART 规模 benchmark + 容器沙箱执行 + 多模块/Spring + 成本/延迟压测。
- 风险：高。范围爆炸、单人难维、触 Charter §8 砍掉的企业特性。**不建议个人走 C。**

## 9. 明确不要做（Q9）

- ❌ 不要用"expected 改成实际返回值"自动修 oracle 失败（`docs/07` A5）——制造同义反复测试。WordUtils 的 16 个失败**标记交人审/Phase 4 门禁**，不自动改。
- ❌ 不要在 n=1 小样本上下强结论或对外宣称"通过率/成功率"——先扩 benchmark。
- ❌ 不要现在大改 runner 去补覆盖率（`docs/14` §8 决策）——compile 未解决前覆盖率优先级最低。
- ❌ 不要跳过 prompt/context 直接堆 Phase 3 fixer——最便宜的杠杆还没用。
- ❌ 不要扩到多模块 / Gradle / 多语言 / IDE / 自动入仓（Charter §8）。
- ❌ 不要把"模型非确定性导致的具体错点"当成可一劳永逸修复的固定 bug。

## 10. 不确定项 / 样本局限

| 项 | 说明 | 如何验证 |
|---|---|---|
| 模型档位 | 用的是 `deepseek-v4-flash`（更弱/便宜），非 `pro`；编译失败率可能被模型档位放大 | 同 spec 切 `pro` 重跑一次对比 compile_pass_rate（便宜实验） |
| 样本量 | n=1/仓，3 仓；模型非确定性，错点会变 | 扩到 5-8 仓、每仓多目标、每目标多次 |
| 覆盖率轴 | 本期 `coverage_unavailable`，未验证"目标覆盖提升" | 用无自带 jacoco 的仓库或弹性 runner 恢复 |
| 目标粒度 | 均为 whole-class，生成大文件（WordUtils 34 测试），放大 oracle 错面 | 试方法级目标，缩小面、省 token |

---

> 复盘结论：**Phase 2.5 达成最小验证，痛点被真实数据证实，底座（harness/构建/目标）零问题，失败集中在模型/prompt/context。下一步先做 prompt/context 优化并重跑量化，再考虑只治编译的 Phase 3 fixer；oracle 失败交质量门禁而非自动弱化。** 完成本复盘，暂停等待 review。
