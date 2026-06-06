# Phase 2.5 模型对照复盘与 Phase 3 最小设计

> 日期：2026-06-06  
> 性质：方向审计 + 下一步设计，不包含 Phase 3 实现。  
> 上级文档：`docs/00_PROJECT_CHARTER.md`、`docs/07_SOURCE_NOTES.md`、`docs/13_PROJECT_DIRECTION_REVIEW.md`、`docs/14_PHASE2_5_BENCHMARK.md`、`docs/15_PHASE2_5_RESULT_REVIEW.md`。  
> 证据目录：`var/benchmark/deepseek/`（`deepseek-v4-flash`）与 `var/benchmark/deepseek-pro-final/`（`deepseek-v4-pro`）。

---

## 0. 一句话结论

`deepseek-v4-pro` 相比 `deepseek-v4-flash` 确实提高了编译通过率：`33% -> 67%`。但两个模型在真实开源仓库上都是 `0/3` 生成测试最终通过，说明项目痛点仍然成立：**真实模型可以稳定产出 schema 合法、看起来完整、但不能直接采纳的测试资产**。

下一阶段不应该直接做“万能修复器”。最小、最有实际价值的路线是：

1. 先用 prompt/context 降低编译失败。
2. 再进入只修编译/符号/导入/语法问题的 Phase 3 fixer。
3. 对 oracle/test failure 只分类和打 `NEED_HUMAN_REVIEW`，不自动把 expected 改成实际值。

---

## 1. Step 1：flash 与 pro 对照结果

### 1.1 聚合指标

| 模型 | 报告 | total | buildable | compile_pass_rate | gen_test_pass_rate | failure 分布 | avg_runtime_ms |
|---|---|---:|---:|---:|---:|---|---:|
| `deepseek-v4-flash` | `var/benchmark/deepseek/report.md` | 3 | 3 | 33% | 0% | `COMPILE_FAILURE:2`, `TEST_FAILURE:1` | 120297 |
| `deepseek-v4-pro` | `var/benchmark/deepseek-pro-final/report.md` | 3 | 3 | 67% | 0% | `TEST_FAILURE:2`, `COMPILE_FAILURE:1` | 229963 |

证据：

- `var/benchmark/deepseek/report.md`：`provider=openai`、`model=deepseek-v4-flash`、`setup_failures=0`、`clone_failures=0`、`repo_build_failures=0`。
- `var/benchmark/deepseek-pro-final/report.md`：`provider=openai`、`model=deepseek-v4-pro`、`setup_failures=0`、`clone_failures=0`、`repo_build_failures=0`。
- 两次运行均为真实 Maven 判卷，覆盖率轴本轮按 `docs/14_PHASE2_5_BENCHMARK.md` 策略关闭，因此 `coverage_measured=0/3`。

### 1.2 Per-case 对照

| case | flash 结果 | pro 结果 | 结论 |
|---|---|---|---|
| commons-cli `Option` | `COMPILE_FAILURE` | `TEST_FAILURE` | pro 把编译门槛跨过去了，但测试运行时因错误使用 mock 失败。 |
| commons-csv `CSVRecord` | `COMPILE_FAILURE` | `COMPILE_FAILURE` | 两者仍卡在编译层，但具体错误不同，说明模型非确定，失败类别稳定。 |
| commons-text `WordUtils` | `TEST_FAILURE` | `TEST_FAILURE` | 两者都能编译，但 oracle/行为理解错误仍然存在。 |

---

## 2. Step 2：失败根因与下一步判断

### 2.1 commons-cli `Option`

flash：

- 结果：`COMPILE_FAILURE`。
- 证据：`var/benchmark/deepseek/ws/60c7626e3f6f4c75976c566d9c385a14/logs/mvn-test-jacoco.log`。
- 根因：
  - `OptionAiGeneratedTest.java:[90]` 找不到符号 `Builder`，应使用 `Option.Builder` 或正确导入/限定。
  - `OptionAiGeneratedTest.java:[196]` 找不到 `assertNotSame(Option, Option)`，缺少静态断言导入。
- 归因：prompt/context/model。不是 harness、构建或目标选择问题。

pro：

- 结果：`TEST_FAILURE`。
- 证据：
  - `var/benchmark/deepseek-pro-final/report.md`
  - `var/benchmark/deepseek-pro-final/ws/3e0796d9aa7c447c8b52532f2ae0a35f/logs/mvn-test-jacoco.log`
  - `var/benchmark/deepseek-pro-final/ws/3e0796d9aa7c447c8b52532f2ae0a35f/repo/src/test/java/org/apache/commons/cli/OptionAiGeneratedTest.java`
- 根因：
  - 编译通过。
  - 运行时 `46` 个 error，统一来自 `OptionAiGeneratedTest.setUp:27`。
  - 具体错误：Mockito 不能 mock `org.apache.commons.cli.DeprecatedAttributes`，因为它是 `final class`。
  - 生成测试在第 27 行执行 `deprecatedMock = mock(DeprecatedAttributes.class);`。
- 归因：模型误用了测试依赖/测试模式。它不是 oracle 猜错，而是运行时 setup 设计错误。

判断：

- pro 对编译能力有收益。
- 但 pro 更倾向生成大而复杂的测试文件，可能引入 mock、嵌套测试、setup 共享失败等新风险。
- Phase 3 可以修 flash 的 `Builder`/`assertNotSame` 类问题；不应该把 pro 的 Mockito final class 问题当成优先修复目标，除非后续样本显示它高频。

### 2.2 commons-csv `CSVRecord`

flash：

- 结果：`COMPILE_FAILURE`。
- 证据：`var/benchmark/deepseek/ws/52e4b041390f42d5a48f327b4961aceb/logs/mvn-test-jacoco.log`。
- 根因：
  - `CSVRecordAiGeneratedTest.java:[99]`、`:[109]`：`枚举类型不能为本地类型`。
  - 模型在方法内声明 local enum，当前项目 Java 源级别不允许。
- 归因：模型生成了不符合目标仓库 Java 约束的语法。

pro：

- 结果：`COMPILE_FAILURE`。
- 证据：
  - `var/benchmark/deepseek-pro-final/ws/cf30a0c353bd499caa07058bf0d82c32/logs/mvn-test-jacoco.log`
  - `var/benchmark/deepseek-pro-final/ws/cf30a0c353bd499caa07058bf0d82c32/repo/src/test/java/org/apache/commons/csv/CSVRecordAiGeneratedTest.java`
- 根因：
  - `CSVRecordAiGeneratedTest.java:[166]` 找不到符号 `Stream`。
  - 生成文件只导入了 `java.util.stream.Collectors`，没有导入 `java.util.stream.Stream`。
- 归因：导入缺失。属于 Phase 3 fixer 最适合处理的低风险编译错误。

判断：

- CSVRecord 的两次失败都支持一个结论：Phase 3 的第一版应该聚焦“编译闭环”，尤其是导入、限定名、source-level 语法约束。
- 这里不需要生产代码、不需要 mock 系统、不需要复杂知识库，最小闭环就能解决部分痛点。

### 2.3 commons-text `WordUtils`

flash：

- 结果：`TEST_FAILURE`。
- 证据：`var/benchmark/deepseek/ws/085852d5be8d457497c102b761e7920c/logs/mvn-test-jacoco.log`。
- 根因：
  - 生成测试编译通过。
  - `WordUtilsAiGeneratedTest` 跑了 `34` 个测试，`16` 个失败。
  - 失败集中在 oracle/行为理解：`uncapitalize`、`abbreviate`、`wrap`、`containsAllWords`、delimiter 判断等 expected 值错误。

pro：

- 结果：`TEST_FAILURE`。
- 证据：`var/benchmark/deepseek-pro-final/ws/ffd01fa330ca4ee2be2739f36f25a777/logs/mvn-test-jacoco.log`。
- 根因：
  - 生成测试编译通过。
  - `WordUtilsAiGeneratedTest` 跑了 `55` 个测试，`11` 个失败。
  - 失败仍集中在 oracle/行为理解：`abbreviate` 边界、`wrap` 换行、`containsAllWords` 空词数组、delimiter null 语义等。

判断：

- pro 的 WordUtils 失败数从 `16/34` 降到 `11/55`，但仍未通过。
- 这说明更强模型能改善一部分行为理解，但不能替代确定性判卷和质量门禁。
- 这类问题不能用自动修复器直接“把 expected 改成 actual”。那会违反 `docs/07_SOURCE_NOTES.md` 中“不让 LLM 当验证者”和“避免弱断言/同义反复测试”的设计原则。

---

## 3. 是否偏离大厂/前沿探索？

没有偏离，反而更接近大厂探索里更现实的一层：**AI 不是只生成测试，而是进入可度量、可判卷、可归因、可拒收的测试资产生产线**。

当前项目与普通 demo 的区别仍然成立：

- 普通 demo：给模型一个类，让它吐一段测试代码。
- 当前项目：真实仓库 checkout、基线判卷、上下文构造、schema 约束、写盘、Maven 执行、失败分类、报告沉淀。
- Phase 2.5 新增价值：证明这套链路在真实 Apache 仓库上能跑，并能把失败定位到模型/prompt/context，而不是 harness 或构建系统。

但也要诚实标注：

- 当前样本只有 `3` 个 case，不能声称模型通过率。
- 当前只覆盖 Maven/Java/JUnit 形态，不能声称多语言或企业级构建系统适配。
- 当前没有自动修复闭环，不能声称能稳定把失败测试变成可采纳资产。
- 当前覆盖率策略临时关闭，不能声称已经证明“提升覆盖率”。

---

## 4. 运行中暴露的 harness 准备问题

pro 首次对照运行暴露两个准备问题：

1. clone 阶段偶发失败：第一次 pro 输出目录出现 `REPO_CLONE_FAILED`，后续通过复用已有 mirror 缓存完成重跑。当前证据不足，不能断定是网络、GitHub 限流还是本地瞬时问题。验证方式：后续 benchmark 记录 `git clone` stderr，并保留 mirror 命中率。
2. `deepseek-v4-pro` 响应慢于 flash：第一次 pro 重跑在 `httpx.ReadTimeout` 处中断。已做最小防护：新增 `TESTAGENT_LLM_TIMEOUT_SECONDS`，并把 httpx 网络错误包装成 `LLMRequestError`，避免 benchmark 进程被裸异常打断。

相关代码变更范围：

- `app/config.py`
- `app/llm/client.py`
- `app/llm/openai_client.py`
- `tests/test_llm_layer.py`
- `.env.example`

验证：

- `.\.venv\Scripts\python.exe -m pytest tests\test_llm_layer.py tests\test_benchmark.py -q`：`21 passed`
- `.\.venv\Scripts\python.exe -m pytest`：`113 passed, 4 skipped`

这属于 Phase 2.5 benchmark 的最小稳定性修复，不是 Phase 3 功能，也不是架构重构。

---

## 5. Step 3：Phase 3 最小引入方案

### 5.1 Phase 3 的目标

Phase 3 不应该定义为“自动修好所有失败测试”。

Phase 3 最小目标应该是：

> 对真实仓库 benchmark 中的 `COMPILE_FAILURE` 做最多 3 轮、只修改生成测试文件的确定性/LLM 辅助修复，并记录每轮失败原因、补丁和最终结果。

验收指标：

- 输入是 Phase 2 生成的测试文件和 Maven compile log。
- 只允许修改 generated test，不允许改生产代码、不允许改 pom、不允许改已有测试。
- 修复后重新跑 Maven 判卷。
- 输出 repair trace：round、error bucket、patch summary、compiled/passed/outcome。
- 只把 `COMPILE_FAILURE -> compiled=true` 计为 Phase 3 主要收益。
- `TEST_FAILURE` 只分类，不自动修改 expected。

### 5.2 第一版只处理的失败桶

建议 Phase 3 第一版只处理以下桶：

| bucket | 示例 | 来源证据 | 是否引入 |
|---|---|---|---|
| missing import / static import | `assertNotSame` 未导入、`Stream` 未导入 | flash Option、pro CSVRecord | 应引入 |
| nested class qualification | `Builder` 应为 `Option.Builder` | flash Option | 应引入 |
| source-level syntax | 方法内 local enum | flash CSVRecord | 应引入，但只做简单迁移/重生，不做复杂 AST 重构 |
| nonexistent method / API hallucination | smoke 中 `setObjectType`、`setType(Object)` 这类方法幻觉 | `docs/14_PHASE2_5_BENCHMARK.md` smoke 记录 | 可分类，谨慎修复 |
| test dependency misuse | Mockito mock final class | pro Option | 先分类，不作为第一版主修复目标 |
| oracle mismatch | WordUtils expected 错 | flash/pro WordUtils | 不引入自动修复 |

### 5.3 最小流程

1. 读取上一轮 generated test 与 Maven compile log。
2. 从 log 中提取编译错误：
   - 文件、行列、错误类型、符号、方法名、类名。
3. 归类到 failure bucket。
4. 根据 bucket 生成最小补丁：
   - 缺 import：补 import 或 static import。
   - 嵌套类：补外部类限定名。
   - local enum：移出方法，变成测试类 private enum。
   - 方法幻觉：优先删除相关测试方法或要求模型重写该最小片段，不猜 API。
5. 重新执行 Maven。
6. 最多 3 轮，停止条件：
   - 编译通过。
   - 连续同类错误不收敛。
   - 修复需要改生产代码/pom/已有测试。
   - 进入 `TEST_FAILURE`。
7. 写入 report：
   - `repair_rounds`
   - `repair_buckets`
   - `repair_success`
   - `final_outcome`
   - `need_human_review`

### 5.4 明确红线

Phase 3 不做：

- 不自动把 expected 改成 actual。
- 不把失败断言删除到只剩 smoke test。
- 不自动扩大到 Spring、Gradle、多语言、IDE 插件。
- 不修改生产代码、pom、已有测试。
- 不把覆盖率提升作为 Phase 3 第一验收指标。
- 不引入重型外部 agent 框架。

---

## 6. 三条路线更新

### A. 保守路线：2 周内稳定可讲

做：

- 保留 Phase 2.5 结果。
- 补一个 prompt/context 版本，要求：
  - 列全静态断言导入。
  - 嵌套类使用外部类限定。
  - 不在方法内声明 enum。
  - 只使用上下文中出现过的 API。
  - 避免 mock final/internal classes。
- 重跑同一 3-case，并与本报告对照。

不做：

- 不进 Phase 3 fixer。
- 不追覆盖率。

价值：

- 面试/展示时可以讲清楚真实失败分布、模型对照、prompt 改进是否有效。

### B. 标准路线：100 天内形成高质量 MVP

做：

- A 路线。
- Phase 3 最小编译修复闭环。
- benchmark 扩到 5-8 个真实仓库/目标。
- Phase 4 最小质量门禁：弱断言、同义反复、oracle mismatch 进入 reject/review，不自动修断言。
- 恢复覆盖率策略，但只在 compile/pass 稳定后做。

价值：

- 接近 `docs/00_PROJECT_CHARTER.md` 中的完整 MVP：生成、判卷、修复、拒收、审计报告。

### C. 激进路线：企业 PoC

做：

- B 路线。
- 多模型对照、沙箱化执行、成本/延迟统计、CI 接入、更多构建系统。

风险：

- 范围明显扩大。
- 对单人项目不经济。
- 容易把主线从“测试资产治理”拉偏到“通用 agent 平台”。

当前不建议走 C。

---

## 7. 最终建议

是否继续当前方向：继续。Phase 2.5 的真实数据证明痛点存在，而且当前工程底座能稳定记录失败。

是否继续 Phase 3：可以继续，但必须收缩为“编译修复闭环”，不要做全能 fixer。

下一阶段 5 个任务：

1. 先做 prompt/context 小改并重跑同一 3-case，验证是否能把 compile pass 从 `33%/67%` 继续抬高。
2. 写 Phase 3 repair trace 数据结构和报告字段设计。
3. 实现 compile log bucket 分类，先不调用模型。
4. 实现 missing import / static import / nested class qualification 三类最小修复。
5. 在同一 benchmark 上重跑，比较 `COMPILE_FAILURE -> TEST_FAILURE/PASS` 的转化率。

明确不做：

- 不自动修 oracle。
- 不追求一次性 PASS。
- 不引入重型 agent 框架。
- 不扩展到多语言/Gradle/Spring。
- 不把覆盖率作为 Phase 3 的首要目标。

---

## 8. 不确定项与验证方式

| 不确定项 | 当前判断 | 验证方式 |
|---|---|---|
| pro 是否稳定优于 flash | 当前只看到 pro 编译通过率更高，但样本太小 | 同一 spec 多跑 2-3 次，或扩到 5-8 case |
| prompt/context 能提升多少 | 大概率能降低 import/限定名/语法错误，但不能解决 oracle | 改 prompt 后重跑同一 3-case |
| Phase 3 fixer 收益上限 | 对 missing import/限定名收益明确；对 API 幻觉不确定 | 先实现 bucket 分类，再按真实日志统计频次 |
| oracle 修复是否可自动化 | 当前不建议自动化 | 需要引入规格、已有测试语义、变异测试或人工 review 才能验证 |
| coverage 何时恢复 | 当前不是主瓶颈 | compile/pass 稳定后，用无 JaCoCo 冲突仓库恢复 |

---

## 9. 给下一轮 Claude/Codex 的执行边界

下一轮如果开始，不要直接开发完整 Phase 3。建议命令式边界如下：

> 先只做 prompt/context 优化和同一 3-case 重跑；如果编译失败仍存在，再进入 Phase 3 最小编译修复器设计。Phase 3 第一版只能修改 generated test，只修 compile failure，最多 3 轮，不修 oracle，不改生产代码/pom/已有测试，不引入新框架。

这条边界能最大程度贴合项目 MD：它解决真实痛点，有可度量价值，也与大厂探索中的“生成-判卷-修复-质量门禁”闭环一致；但它不会把项目过早推成不可控的通用 agent。
