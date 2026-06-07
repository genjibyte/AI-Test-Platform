# Phase 2.5 —— 真实模型 × 真实开源仓库 最小验证（mini-benchmark）

> 上级文档：`docs/00`、`docs/07`、`docs/11`、`docs/13`。
> 目的：在开 Phase 3 之前，先回答 `docs/13` 提出的核心未知——**AI 在真实开源代码上能否生成可编译、可执行、能提升覆盖率的测试**。
> 性质：实现 + 验证文档。**不新增任何判卷/生成逻辑**，只编排现有两条流水线并按 `docs/07 §8` 记录事实。

---

## 1. 它解决的问题（对应 docs/13 §四/§六）

`docs/13` 审计结论：整个项目的"真实验证"此前只建立在 `samples/calc`（6 行 toy）+ 一个确定性 fixture 客户端上；真实模型、真实仓库、规模化证据**均不存在**。Phase 2.5 就是补这一块——**路线 A（保守路线）**：用最少代价，在真实仓库上把 Phase 2 闭环用真实模型跑一遍，产出成功**与**失败都记录的 mini-benchmark。

---

## 2. 架构（全部复用现有能力）

```
app/benchmark/
├── models.py      # BenchCase / BenchCaseResult / BenchReport + aggregate + classify_failure + load_spec
├── runner.py      # run_case（judge→generate）/ run_benchmark（循环+聚合）+ 仓库镜像缓存
└── report_md.py   # 渲染 docs/07 §8 风格 Markdown
scripts/run_benchmark.py   # CLI：读 spec → 跑 → 写 report.json + report.md
benchmarks/spec.example.json  # 真实仓库目标清单
```

- **判卷**复用 `app/pipeline/judge_pipeline.run_pipeline`；**生成**复用 `app/pipeline/generate_pipeline.run_generation`；**报告事实**复用 `app/report/generation_report`。Phase 2.5 只做编排与聚合。
- **LLM 客户端可配置**：默认离线 fake（无 key 即可在真实仓库上验证 harness）；配置 `TESTAGENT_LLM_*` 后切真实模型。报告记录实际 `provider/model`，对"是否真跑了真实模型"诚实可查。

### 2.1 关键设计决策（带理由）
1. **每个 case 独立重判卷**（fresh job/workspace）→ 每个目标拿到**干净基线**、互不污染。代价：同一仓库多个目标会各重跑一次 `mvn test`（见 §6 局限）。
2. **仓库镜像缓存**：每个 `(url,branch)` 只 `git clone --depth 1` **一次**到本地，后续 case 从本地镜像导入，避免重复打网络。
3. **工作区隔离**：通过标准设置 `TESTAGENT_WORKSPACE_ROOT` 把所有 job 落到 `--out/ws/<job_id>/`，复用现有隔离机制，不改 Workspace。
4. **比率分母 = 生成已尝试的 case**（即仓库判卷成功的）：不可构建仓库不稀释 compile/pass 率，但单列在 `top_failure_types` 与 `buildable_repos`。
5. **Phase 3/4 指标留空**：`average_repair_rounds`、`accept_rate` 显式为 `null`——尚未实现，不臆造。

---

## 3. 如何运行

### 3.1 离线在真实仓库上验证 harness（无需 key）
```powershell
$env:TESTAGENT_MAVEN_CMD = "C:\Users\lenovo\AppData\Local\Programs\Maven\apache-maven-3.9.9\bin\mvn.cmd"
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/dryrun
```
离线 fake 客户端产出的是**占位空测试**（含 JUnit5 import，可编译可运行，但不覆盖目标）。因此期望：`compiled=true`、`passed=true`、`target_improved=false`、覆盖率 delta≈0。**这一步只证明"在真实仓库上整条链跑得通"，不证明 AI 有用。**

### 3.2 真实模型：先 smoke（1 case）再正式（full spec）
**强制顺序**：先用 `benchmarks/smoke.json`（1 case）验证 key/模型名/JSON schema/延迟/成本，通过后再跑 `benchmarks/spec.example.json`（3 repos）。配置经 `.env`（见 `.env.example`，已 gitignore）。

```powershell
# 0) 把 .env.example 复制成 .env 并填入真实 key（含 deepseek-v4-pro 与 -Djacoco.skip=true 等）
Copy-Item .env.example .env   # 然后编辑 .env

# 1) SMOKE —— 1 个 case，确认真实模型链路
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks/smoke.json --out var/benchmark/smoke

# 2) 通过后再跑正式 3-repo mini-benchmark
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/deepseek
```
> 🔑 **提醒**：正式跑需要配置 API key（DeepSeek，`deepseek-v4-pro`）。key 经 `.env`/环境变量注入，**不写入仓库、不进对话、不入日志**（`app/llm/openai_client.py` 只放进 Authorization 头）。`var/` 与 `.env` 均已 gitignore。
>
> 覆盖率：默认 `.env` 含 `-Djacoco.skip=true`，因此这些 Apache 仓库会标 `coverage_unavailable`（见 §7/§8 覆盖率策略）——本期聚焦 compile/exec/pass。

---

## 4. 验收证据

### 4.1 Harness 离线单测
- `tests/test_benchmark.py`：6 passed（spec 解析、失败分桶、聚合比率、Markdown 渲染）。
- 全量套件：107 passed, 4 skipped。

### 4.2 真实仓库 dry-run（fake 客户端）—— 含一个真实发现

**第一次 dry-run（`apache/commons-cli`，未跳过策略插件）**：harness 完整跑通（exit 0，产出 report），但暴露真实仓库障碍——
- **判卷成功**：`repo_judged=true`，commons-cli 真实 `mvn test`+JaCoCo 跑通，基线覆盖率采集成功。
- **生成执行 `BUILD_ERROR`**：`gen_outcome=BUILD_ERROR`、`compiled=false`。根因**不是测试问题**，而是 **Apache RAT（license-header 审计插件）** 在 `mvn test` 阶段因生成文件缺许可证头而 fail：
  ```
  [ERROR] apache-rat-plugin:0.18:check  Files with unapproved licenses:
    /src/test/java/org/apache/commons/cli/OptionAiGeneratedTest.java
  ```
  基线判卷成功是因为原始文件都有头；只有新增的生成文件触发 RAT。

**修复（最小、opt-in）**：新增 benchmark 专用设置 `TESTAGENT_MVN_EXTRA_ARGS`（[config.py](../app/config.py)），仅由 Phase 2.5 harness 显式传给自己的 judge/generate 调用；普通 API、`scripts.run_judge` 与 Phase 2 e2e 不读取它。benchmark 用它跳过策略/风格/审计类插件（RAT/checkstyle/enforcer/license/spotbugs/…），以保留 compile/exec 信号。

> 这是 Phase 2.5 的首个真实价值：**成熟 OSS（尤其 Apache 系）在 `mvn test` 阶段普遍挂 license/style 门禁插件，会拦截缺头的生成测试**——呼应 `docs/13` §3.3 的"构建脆性"障碍。真实模型生成的测试若不带许可证头，会撞同样的墙。

**第二次 dry-run（跳过策略插件后）**：又暴露第二个真实障碍——
- `compiled=true`（100%），但 `gen_outcome=NO_TESTS`、整套件 `Tests run: 0` + BUILD FAILURE。
- 根因：**JaCoCo 双 agent 冲突**。commons-cli 的 pom **自带 jacoco**，我们又在命令行注入 `jacoco:prepare-agent`，导致 `java.lang.LinkageError: duplicate class definition for java.lang.$JaCoCo`，测试 JVM 在跑任何用例前就崩了：
  ```
  java.lang.LinkageError: ... duplicate class definition for java.lang.$JaCoCo
  *** java.lang.instrument ASSERTION FAILED ***
  ```
- **验证**：对同一工作区加 `-Djacoco.skip=true` 重跑，生成测试干净通过：`Tests run: 1, Failures: 0 ... BUILD SUCCESS`。

> 第二个真实发现：**我们"命令行注入 JaCoCo agent"的覆盖率策略，与自带 JaCoCo 的仓库冲突**。跳过 JaCoCo 可恢复 compile+exec 信号，但会**丢失覆盖率轴**——这是正式 benchmark 需要拍板的取舍（见文末决策）。

### 4.2.1 两个真实发现小结（Phase 2.5 的首批价值）
| # | 发现 | 影响 | 现状 |
|---|---|---|---|
| F1 | Apache RAT 等 license/style 门禁插件在 `mvn test` 阶段拦截缺头的生成测试 | 生成执行 `BUILD_ERROR` | 已修：`TESTAGENT_MVN_EXTRA_ARGS` 跳过策略插件 |
| F2 | 命令行注入的 JaCoCo agent 与仓库自带 JaCoCo 冲突（duplicate `java.lang.$JaCoCo`） | 测试 JVM 崩溃，整套件 0 测试 | `-Djacoco.skip=true` 可恢复 compile+exec，但失覆盖率 |

### 4.3 真实模型 smoke（DeepSeek，1 case）—— 已跑，含真实发现

配置（来自用户 `.env`）：`provider=openai`、`base_url=https://api.deepseek.com`、`model=deepseek-v4-flash`（注意：用户口头说的是 `deepseek-v4-pro`，实配为 `flash`）。

**验证结论（smoke 目的全部达成）**：
- ✅ key/鉴权可用；模型 `deepseek-v4-flash` 可达；返回**通过 `LLMTestPayload` schema**（成功解析→写盘→编译）。
- ⏱️ 延迟 ~85s（含 2 次 mvn）；输出**很大**（~55 个测试方法）。
- ⚠️ 成本：harness 暂未捕获 token usage（`LLMResponse` 无 usage 字段），需从 DeepSeek 控制台读，或后续给 client 加 usage 捕获。

**真实发现 F3 —— 符号幻觉导致 `COMPILE_FAILURE`**（commons-cli `Option`）：
- DeepSeek 生成了相当全面、大体正确的测试（Builder/构造/访问器/设值/values/clone/序列化…）。
- 但编译失败于 2 处 `找不到符号`（cannot find symbol）：
  - `opt.setObjectType(Integer.class)` —— **方法不存在**（模型自己还留了疑问注释）；
  - `opt.setType((Object) Integer.class)` —— `setType(Object)` 重载不存在。
- 即 ~53/55 个测试看似可用，**2 个幻觉方法调用拖垮整文件**。这正是 `docs/12` TestART 的头号失败类目（cannot find symbol），也是 `docs/13` #1 未知的**真实数据点**：真实代码上 AI 测试**开箱不编译**，主因符号幻觉。
- **对 Phase 3 的直接含义**：一个定点 Fixer（删/修幻觉符号）极可能把此 `COMPILE_FAILURE` 变成一大批通过的测试——为"继续 Phase 3 修复闭环"提供了数据支撑（而非凭空）。

> smoke **验证通过**（key/模型/schema/延迟均 OK），可进入正式 3-repo 跑；但需先拍板：(a) 模型用 `flash` 还是 `pro`；(b) 是否先加 token usage 捕获以量化成本。正式聚合指标见 §4.4（待跑）。

### 4.4 正式 3-repo mini-benchmark
`<待回填：spec.example.json 跑后的 compile_pass_rate / gen_test_pass_rate / top_failure_types / 每仓 runtime>`

---

## 5. 这一步能下/不能下的结论
- **能下**：harness 在真实仓库上是否跑得通（4.2）；真实模型在真实仓库上的 compile/pass/coverage 实证（4.3，待跑）。
- **不能下**（仍 unknown，须 4.3 跑完才知）：真实模型生成测试的真实 compile 通过率、覆盖率提升率、主要失败类型分布。这些数据将**驱动 Phase 3 失败分类的优先级**（而非凭 TestART 论文猜，呼应 `docs/13` §6.3 任务 4）。

---

## 6. 已知局限（诚实记录）
1. **每 case 重跑全量 `mvn test`**：同仓多目标成本线性增长；mini 规模可接受，规模化需"判卷一次 + 按目标复制工作区"优化（留待后续）。
2. **JUnit5 假设**：生成测试用 `org.junit.jupiter`；若目标仓库测试类路径只有 JUnit4，占位/生成测试会 `COMPILE_FAILURE`——这是**真实发现**，会如实进 `top_failure_types`。
3. **单模块优先**：多模块仓库的目标定位/覆盖率聚合未特殊处理（与 Charter §7.7 一致）。
4. **真实仓库构建脆性**：strict 插件（enforcer/checkstyle/animal-sniffer）可能让 `mvn test` 失败 → 记 `REPO_NOT_BUILDABLE`；这是数据点，不是 harness bug。
5. **成本/耗时未压测**：真实模型 token/时延将在 4.3 记录。

---

---

## 7. 失败分类（Phase 2.5 taxonomy）

实现在 [app/benchmark/models.py](../app/benchmark/models.py) `FAILURE_TYPES` + `classify_failure()`。每个 case 落**一个** failure bucket（`None` 即干净 PASS）；**覆盖率是独立状态**（`coverage_status`），不混进失败桶。分类器**先读构建日志**，因为 JaCoCo 崩溃 / 策略插件失败会伪装成 `NO_TESTS` / `BUILD_ERROR`。

| bucket | 含义 | 主要判据 |
|---|---|---|
| `REPO_NOT_BUILDABLE` | 仓库自身判卷就没过（import/build/compile） | `repo_judged=false` |
| `PIPELINE_FAILED` | 生成流水线短路（目标/上下文/写文件错误） | `generation_status=GEN_FAILED` |
| `POLICY_PLUGIN_FAILURE` | RAT/checkstyle/enforcer/license/pmd/spotbugs 让 `mvn test` 失败（F1） | 日志含 `Failed to execute goal ...-plugin` |
| `JACOCO_CONFLICT` | JaCoCo 双 agent 崩溃（F2，`duplicate java.lang.$JaCoCo`） | 日志含 `java.lang.$JaCoCo` / `jacoco.agent.rt` |
| `COMPILE_FAILURE` | 生成测试编译失败 | gen_outcome=COMPILE_FAILURE |
| `NO_TESTS` | 编译并运行但无用例 | gen_outcome=NO_TESTS（且无上面崩溃签名） |
| `TEST_FAILURE` | 运行但断言/异常失败 | gen_outcome=TEST_FAILURE |
| （None） | 干净 PASS | gen_outcome=PASS |
| + `BUILD_ERROR`/`NO_MAVEN` | 其它未归类 / 环境无 maven | 兜底 |

**覆盖率状态（与失败桶正交）**：`coverage_status ∈ {available, unavailable}`。`COVERAGE_UNAVAILABLE` 表示**没测到覆盖率**（JaCoCo 被跳过或无报告），即使测试 PASS 也可能 unavailable；此时 `target_*_delta`/`coverage_dropped`/`target_improved` 置 `None`（不伪造 0）。

聚合报告额外单列 `setup_failures`、`clone_failures`、`repo_build_failures`：
- `setup_failures`：例如 LLM key/model/provider 配置错误，尚未进入仓库判卷。
- `clone_failures`：Git clone / 分支 / 网络失败，尚未进入 Maven 判卷。
- `repo_build_failures`：仓库已导入但原始判卷失败。

因此 `buildable_repos` / `generation_attempted` 只表示**已经判卷成功并进入生成链路**的 case，不把 LLM 配置错误误读成仓库不可构建。

## 8. 覆盖率策略（Phase 2.5）

- **本期以 compile/exec/pass 为主**：默认 `.env` 含 `-Djacoco.skip=true`，规避 F2 双 agent 崩溃，让测试真正跑起来。
- **覆盖率冲突/跳过 → 标 `coverage_unavailable`**，聚合里单列 `coverage_measured` 与 `coverage_improved_rate`（仅对 available 的 case 计）。
- **不马上大改 runner**：不在本期做"自带 jacoco 就用它、否则注入"的弹性覆盖率（留作后续，或改用无自带 JaCoCo 的仓库）。

## 9. 仓库选择（2-3 个，小型/单模块/JUnit5/Maven）

| repo | 校验 | 目标（whole-class） | 备注 |
|---|---|---|---|
| `apache/commons-cli` | 已实跑（JUnit5、单模块） | `org.apache.commons.cli.Option` | dry-run 已验证可判卷 |
| `apache/commons-csv` | pom 校验：单模块 + junit-jupiter | `org.apache.commons.csv.CSVRecord` | RAT/checkstyle/jacoco → 由 skip 处理 |
| `apache/commons-text` | pom 校验：单模块 + junit-jupiter | `org.apache.commons.text.WordUtils` | 同上 |

- 选 Apache Commons 同族：单模块、JUnit5、结构已知，**避免一上来被多模块/复杂构建淹没**。
- 不确定：`CSVRecord`/`WordUtils` 类与方法的精确存在性仅凭经验，**首跑时由 harness 兜底**（不存在 → `PIPELINE_FAILED`，如实记录）。验证：smoke/首跑后看 report。
- whole-class 目标（不指定 method）规避签名臆测；后续可收窄到方法级以省 token。

## 10. DeepSeek smoke 流程（正式前必做）

1. 配 `.env`（provider=deepseek、model=deepseek-v4-pro、key、`-Djacoco.skip=true` 等）。
2. 跑 `benchmarks/smoke.json`（1 case）。**通过判据**：
   - 真实模型可达、鉴权成功（无 `LLMRequestError`）；
   - 返回通过 `LLMTestPayload` schema 校验（无 `LLMOutputError`）；
   - `model` 字段回填为真实模型名；
   - 记录**延迟**（report 的 `runtime_ms`，含 mvn）与**成本**（在 DeepSeek 控制台看本次 token；注：当前 `LLMResponse` 未捕获 usage，token 成本暂从控制台读，后续可加）。
3. smoke 通过 → 再跑 `spec.example.json`（3 repos）。

## 11. WIP 文件分类（commit vs 残留）

| 类别 | 文件 |
|---|---|
| **harness 必要（提交）** | `app/benchmark/**`、`scripts/run_benchmark.py`、`benchmarks/spec.example.json`、`benchmarks/smoke.json`、`tests/test_benchmark.py`、`.env.example`；改动 `app/config.py`、`app/build/maven_runner.py`、`app/coverage/jacoco_runner.py`；`docs/12`/`13`/`14` |
| **实验残留（不提交）** | `benchmarks/_dryrun1.json`（已删）、`var/benchmark/**`（已 gitignore，含克隆仓库/报告/日志，11M，可随时清） |

---

> 状态：harness 已实现 + 离线单测全绿（benchmark 9 项；全量 110 passed/4 skipped）；真实仓库 dry-run 跑通并暴露 F1/F2 两个真实发现；失败分类、覆盖率策略、仓库选择、smoke 流程已定。**正式 mini-benchmark 待：(1) 你的 `deepseek-v4-pro` key 进入 `.env`/User 作用域（当前我的 shell 看不到）；(2) 先过 `benchmarks/smoke.json` 1-case smoke。**
