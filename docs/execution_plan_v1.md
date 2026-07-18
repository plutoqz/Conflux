# Conflux 执行方案 v1

> 文档状态：已批准；M0-M2 与 P0 已完成验收，M3+ 暂缓
>
> 版本：1.0
>
> 日期：2026-07-18
>
> 上位蓝图：[docs/architecture.md](architecture.md)
>
> 状态：M0 基线、M1 扩展协议、M2 第一方能力/工作流和 P0 研究质量修复已完成验收。当前尚未启动 M3 数据库、持久运行或初始化迁移。

## 1. 使用方式

`architecture.md` 负责长期方向，本文件负责第一轮实施。实施时不要求一次完成 M1-M6；每个阶段开始前确认当期范围，完成后根据真实问题更新状态。

本方案的成功标准不是新增模块数量，而是：

- 用户可以定义和运行自己的能力，同时不直接依赖核心私有状态。
- 现有研究查询、论文、项目和审计能力可以逐步迁移，不发生大范围停摆。
- 论文和搜索结果的语义判断真正由 LLM 完成，失败时不会被确定性分数伪装成已评审。
- 任务、证据、产物和审批可以追溯、恢复和迁移。
- 测试、安全和抽象成本与真实风险相称，不阻碍日常开发。

## 2. 全局实现规则

### 2.1 代码和数据边界

第一轮在当前单仓库中建立边界，不立即拆分多个 Python 包或服务：

```text
src/conflux/
  core/       # 运行上下文、协议、事件、策略和存储端口
  sdk/        # Plugin、Capability、Workflow、Evaluator、Renderer
  builtin/    # 第一方能力，按协议接入
  adapters/   # 模型、RAG、Web、SQLite、Chroma、CLI、HTTP
  workbench/  # UI 和 HTTP 适配，只调用 Application API
```

当前模块可以分阶段迁移。迁移前保留兼容适配器，迁移完成后标记移除版本，禁止永久保留两条主要路径。

### 2.2 数据协议

核心边界使用稳定、JSON 可序列化的协议：

- `RunContext`：工作区、模型、预算、取消、权限和运行标识。
- `StepResult`：状态、输出、证据引用、产物引用、指标和错误。
- `ArtifactRef`：产物 ID、类型、哈希、位置、来源 Run/Step。
- `ApprovalRequest`：待确认操作、差异、风险、输入哈希和审批结果。
- `TraceEvent`：开始、完成、失败、重试、降级、审批和恢复。

插件不能接收完整 LangGraph 状态，不能写入核心全局变量，不能直接修改工作台对象。

### 2.3 LLM 评审规则

确定性逻辑只做召回、去重、格式校验、负面条件和硬性安全门禁。LLM 负责：

- 搜索结果和论文的语义相关性。
- 研究价值、方法/数据集复用价值和证据质量。
- 候选排序、边界候选是否需要深评。
- 冲突解释、报告综合和开放式研究计划。

LLM 评审必须输出 `relevance`、`research_value`、`evidence_quality`、`reasoning`、`confidence`、`needs_deeper_review`。模型失败、超时或 Schema 无法修复时输出 `unreviewed`，不能自动入库或提升为高置信证据。

### 2.4 变更控制

每个阶段均建立：

- 范围和非目标。
- 受影响模块和数据格式。
- 新增依赖及其移除条件。
- 快速测试、阶段测试和真实 API 测试分层。
- 回滚开关或恢复步骤。

以下情况必须暂停并更新架构决策：插件需要核心私有状态、出现 YAML/数据库双写、需要预先建设多租户/微服务、单个示例要求核心加入领域分支、或连续两次修复都扩大核心协议。

## 3. 阶段总览

| 阶段 | 目标 | 主要产物 | 默认状态 |
|---|---|---|---|
| M0 | 基线、夹具和决策记录 | 基线报告、问题登记格式 | 已完成 |
| M1 | 扩展协议最小闭环 | SDK、Registry、契约测试 | 已完成 |
| M2 | 第一方能力和 YAML 工作流 | 动态结果、工作流编译、LLM 评审 | 已完成 |
| P0 | 研究质量与可用性修复 | 评审容错、Web 降级、跨语言 RAG、回答先行 | 已完成验收 |
| M3 | 持久运行和初始化迁移 | SQLite Run Store、Job、Event、Approval | P0 验收后启动 |
| M4 | Evidence Ledger 和验证闭环 | 来源版本、声明关系、影响分析 | 待启动 |
| M5 | LLM 评审评测和示例扩展 | 标注集、消融报告、互补扩展 | 待启动 |
| M6 | 可选服务化 | Postgres、Worker、隔离插件 | 条件触发 |

依赖顺序：M0 -> M1 -> M2 -> P0 -> M3 -> M4 -> M5；M6 不得提前启动。P0 是 M3 的启动闸门，不扩展为新的架构阶段，也不引入数据库。

## 4. M0：基线与实施准备

### 4.1 目标

- 记录当前行为和性能基线。
- 准备不污染源码运行目录的测试夹具。
- 建立轻量 ADR/问题记录，不增加重审批流程。

### 4.2 实现方法

- 在临时目录运行 `python -m pytest -q`、离线检索评测和离线报告评测。
- 记录当前测试数量、检索指标、报告验收率、失败来源泄漏、平均/分位延迟和已知失败样本。
- 建立 `tests/fixtures/architecture/` 目录约定，保存插件、工作流、迁移、来源变化和 LLM 录制响应夹具。
- 测试不得写入现有 `reports/`、`data/chroma_db/` 或用户项目路径。
- 记录查询、论文 inbox、论文 promote、项目计划、进度审计和工作台任务的当前入口。

### 4.3 验收标准

- 基线结果可以在新机器或临时工作区重复生成。
- 基线报告明确列出当前 RAG/Web 确定性评分的限制。
- 当前功能行为没有因 M0 改变。
- 后续阶段可以引用同一份基线，不依赖个人未提交文件。

### 4.4 失败处理

如果基线本身不稳定，先修复夹具或登记缺陷，不进入 M1。不得将不稳定行为包装成重构后的回归或收益。

## 5. M1：扩展协议最小闭环

### 5.1 目标

让一个能力可以被发现、校验、执行、追踪和测试，同时不修改核心固定来源列表和工作台专用路由。

### 5.2 建议代码边界

```text
src/conflux/core/contracts.py
src/conflux/core/registry.py
src/conflux/core/policy.py
src/conflux/sdk/manifest.py
src/conflux/sdk/plugin.py
src/conflux/sdk/testing.py
src/conflux/adapters/plugin_loader.py
```

### 5.3 实现方法

- SDK 边界使用 Pydantic v2，直接声明依赖；核心内部可继续使用现有 dataclass/TypedDict。
- 定义 `PluginManifest`、`CapabilitySpec`、`WorkflowDefinition`、`StepResult`、`PluginContext`。
- Manifest 包含 ID、版本、入口、能力、权限、配置、Schema、超时、副作用和 SDK 兼容范围。
- Registry 从内置插件和用户显式指定目录加载 Manifest，不扫描未知 Python 文件。
- 通过 entry point 或明确路径加载插件；只加载通过版本、Schema、权限和入口校验的插件。
- `PluginContext` 仅提供日志、配置、模型、存储、证据登记和 Artifact 服务。
- 第一阶段插件标记为可信进程内代码；权限用于校验和审计，不宣称提供沙箱。

### 5.4 CLI

```text
conflux plugin list
conflux plugin validate <path>
conflux plugin inspect <plugin-id>
conflux workflow validate <path>
```

### 5.5 测试范围

契约测试覆盖：Manifest 缺失字段、版本不兼容、未知能力、Schema 错误、权限不足、插件异常封装、禁用插件、事件记录和 Secret 脱敏。

不为简单代理函数建立重复的多层测试；重点覆盖协议分支和安全边界。

### 5.6 验收标准

- 至少一个第一方能力通过 Registry 注册并独立执行。
- 新增能力不需要修改 `MultiAgentState`、固定来源枚举或工作台专用 API。
- 输入输出可以导出和校验 JSON Schema。
- 异常统一转换为 `StepResult`，不泄露 Secret，不直接修改共享状态。
- 协议分支契约测试覆盖 100%。
- 现有测试、离线评测和工作台测试不回归。

### 5.7 回滚

新 Registry 默认只在显式开关下启用，保留当前内置调用路径。协议失败时删除实验性加载器不影响现有查询和工作台。

## 6. M2：第一方能力迁移与 YAML 工作流

### 6.1 目标

将核心能力通过同一 SDK 接入，并让技术用户使用 YAML 组合已安装能力，不引入可视化编排。

### 6.2 动态结果协议

将固定的 `rag_result`、`web_result`、`model_result` 逐步迁移为带 reducer 的动态 `source_results` 集合。过渡期保留旧字段适配器，但新报告、Trace 和仲裁只读取统一集合。

`SourceResult.source` 改为 namespaced ID，例如 `builtin.rag` 或 `plugin.example.search`。来源展示名、证据类型和权限从 Registry 元数据读取。

### 6.3 第一方迁移顺序

1. RAG Connector：确定性召回/硬过滤，LLM 语义评审。
2. Web Connector：结果规范化，LLM 相关性/证据质量评审。
3. Model Analyst：直接读取结构化 `StepResult`，移除图内文本 marker 中转。
4. Paper Workflow：批量 LLM 评审、边界候选深评和人工入库确认。
5. Project/Audit Workflow：计划分析、证据核验和审计作为统一步骤。

### 6.4 YAML 工作流

YAML 只描述已安装能力和连接，不执行任意 Python：

```yaml
api_version: conflux.dev/v1alpha1
kind: Workflow
id: research.query
version: 0.1.0
inputs:
  query: {type: string, required: true}
steps:
  - id: retrieve
    uses: builtin.rag.search
    mode: deterministic
  - id: semantic_review
    uses: builtin.research.evidence_review
    mode: agentic
  - id: approve
    uses: builtin.human.approval
    mode: human
```

编译前检查能力存在性、Schema 连通性、循环停止条件、预算、权限和副作用。编译后生成版本化工作流和文本图预览。

### 6.5 LLM 评审实现

- 批量阅读研究画像、查询、标题、摘要或搜索片段。
- 输出 `relevance`、`research_value`、`evidence_quality`、`reasoning`、`confidence`、`needs_deeper_review`。
- 缓存键包含候选内容哈希、画像版本、Prompt 版本和模型版本。
- 普通候选使用批量和轻量模型；边界、高价值或冲突候选再做深评。
- 模型失败、超时或 Schema 修复失败时标记 `unreviewed`，不能自动入库。

### 6.6 验收标准

- 一个外部来源和一个本地查询工作流可以完成 YAML 校验、编译和 Dry Run。
- 新增来源不修改核心固定来源枚举、报告模板和 Trace 映射。
- 论文评审可以追溯候选哈希、画像、Prompt、模型、理由和不确定性。
- LLM 不可用时界面显示 `unreviewed` 原因和下一步。
- 旧 CLI/工作台至少有一个兼容适配路径。
- 失败来源泄漏保持 0，报告验收率不低于 M0 基线。
- 无可视化编排页面。

### 6.7 回滚

新工作流通过显式配置启用，默认保留旧路径。动态结果适配器必须记录删除版本，不允许长期双路径作为默认实现。

## P0：研究质量与可用性修复（最高优先级）

### P0.1 目标

在进入 M3 持久运行和数据迁移前，先解决当前影响基本可用性的正确性问题：论文语义评审失败导致整批跳过、Web 搜索单一 provider 失败、中文问题召回英文论文不足、研究回答被可信度说明淹没，以及 RAG 证据质量和全文状态不清晰。

P0 是 M2 的后置修复闸门。它不改变 `architecture.md` 的长期边界，不引入 SQLite、服务化、微服务或可视化编排。

### P0.2 全局原则

- LLM 评审失败时保留候选和确定性排序，但不得把确定性分数伪装成语义评审结果。
- `unreviewed` 不等于 `skip`；未评审候选可以展示、重试和人工处理，但不能自动提升为高置信证据或无审批入库。
- 主答案先回答问题，再附证据、可信度和缺口；FactCheck、仲裁和原始日志作为可展开审计信息。
- 来源可信度按证据项的相关性、权威性、时效性、引用完整性和多源一致性判断，不按 RAG/Web/Model 通道绝对化。
- 确定性逻辑负责召回、去重、格式校验、硬性过滤和安全门禁；LLM 负责语义相关性、研究价值、证据质量和候选重排。
- 所有降级、重试、临时结果和失败原因必须可见、可追溯、可再次执行。

### P0.3 工作包 A：论文语义评审容错

受影响边界：`builtin.paper.review`、`builtin.research.evidence_review`、论文 inbox、Workbench 评审状态。

实现要求：

- 将大批次拆分为 3-5 篇的小批次，批次之间独立成功或失败。
- 单篇或单批次异常不得影响其他候选。
- 初评成功、深评失败时保留初评结果；仅将深评失败候选标记为 `unreviewed` 或 `needs_deeper_review`。
- 对超时、认证失败、JSON 截断、数量不匹配、Schema 错误和二次修复失败使用结构化错误码。
- 评审失败最多自动重试一次，使用有限退避并记录重试原因。
- 评审结果至少区分 `deterministic_score`、`semantic_score`、`review_status` 和 `candidate_status`。
- 评审失败时保留确定性候选排序和原始结果，但不得将其写成已完成的 LLM 相关性判断。
- 评审完成后重新写出 inbox JSON/Markdown；失败原因、模型、Prompt、候选哈希和下一步操作必须写入产物。
- Workbench 不再只显示“配置模型后重试”，必须展示可操作的失败原因。

验收标准：

- 10 篇论文中任意 1 批失败时，其余批次仍保留评审结果。
- 初评成功而深评超时时，初评结果不丢失。
- LLM 不可用时论文不会被整批设为 `skip`，而是显示 `unreviewed/provisional`。
- 未评审论文不会自动变为高置信证据或无审批进入知识库。
- 评审失败原因可在 CLI、Workbench 和 inbox 产物中定位。

### P0.4 工作包 B：Web provider 多级降级

实现统一 `SearchProvider` 适配边界，支持配置化 provider 链：

```text
主 provider
  -> DuckDuckGo / 备用通用搜索 API
  -> Bing 或 Google 的授权 API / SerpAPI
  -> Semantic Scholar / OpenAlex / Crossref / arXiv
  -> LLM 统一语义评审与去重
```

降级触发条件包括请求失败、超时、限流、有效 URL 过少、去重后候选过少、低质量域名占比过高或 LLM 评审后有效候选不足。不得直接抓取 Google/Bing 搜索页面作为默认实现；需要使用授权 API 或聚合服务。

学术查询判断扩展“局限性、评估、风险、模型、算法、机制、研究现状、失败模式”等中英文意图词，但不对所有开放问题强制触发学术 API。边界问题可以通过轻量模型判断是否需要学术搜索。

验收标准：

- 主 provider 失败时能自动进入备用 provider，并在 Trace 中记录切换原因。
- provider 结果可以按 URL、DOI、论文 ID 去重并合并。
- 备用结果不会绕过统一的 LLM 语义评审和证据状态协议。
- 无备用凭证时仍能明确显示可用的学术 API、失败来源和下一步，而不是静默失败。

### P0.5 工作包 C：跨语言 RAG 和论文全文质量

实现一个独立的 `QueryRewriteProvider`，将原始查询、术语扩展和可选 LLM 中英改写分开，避免底层检索器直接依赖模型。

检索链路要求：

- 中文原始查询、英文翻译查询和领域扩展查询并行召回。
- Chroma 的真实查询距离必须转换为明确的 Dense 相似度并传递给后续排序。
- 禁止使用论文发现阶段的 `relevance_score` 作为当前查询的 Dense 分数。
- BM25 使用语言感知分词；跨语言场景降低词法分数对最终判断的影响。
- 候选先扩大召回，再由 LLM 做语义重排；确定性阈值不得直接淘汰所有跨语言候选。
- 论文查询支持 `limitations`、`challenges`、`failure modes`、`future work`、`research gaps` 等章节词扩展。

论文入库要求区分：

```text
full_text_requested
full_text_downloaded
full_text_extracted
full_text_indexed
```

论文全文应尽量保留 `abstract`、`method`、`results`、`limitations`、`discussion`、`future_work` 等章节元数据。内容更新使用内容哈希和版本化 upsert，不能因为相同 `chunk_id` 永久跳过更新。

验收标准：

- 中文问题能够稳定召回英文相关论文，且不因词法分数为零直接丢弃。
- Dense、BM25、融合分数和最终 LLM 评审结果可以分别追溯。
- 论文没有下载或提取全文时，界面和产物明确显示原因。
- 针对“局限性/失败模式/未来工作”的查询能够优先命中对应章节或明确说明知识库缺口。
- 重复入库和内容更新不会产生旧摘要永久遮蔽新全文的问题。

### P0.6 工作包 D：回答先行与可信度后置

重构报告综合和 Model-only fallback 行为。主报告默认结构为：

```markdown
## 核心回答
## 分析
## 证据支撑
## 可信度评估
## 需要进一步核验
```

实现要求：

- 在现有条件下先给出尽可能完整的回答、分类、原因和工程分析。
- Model-only 场景允许输出临时分析，但必须逐条标记为模型推断。
- `low_relevance` 只能降低相关结论的可信度，不应自动把整个回答变成拒答。
- 可信度按声明或证据项评估，不能只给一个笼统的全局低分。
- FactCheck、三源仲裁、原始来源状态和运行日志进入附录或可展开区域。
- 报告必须区分“没有证据”“证据弱”“Model 推断”和“工具失败”。

验收标准：

- 用户打开报告首先看到问题答案，而不是失败原因或免责声明。
- RAG/Web 不足但 Model 有内容时，仍能得到结构化临时回答。
- 低可信度说明位于答案之后，且不会遮蔽核心结论。
- 关键结论可以定位到来源、证据类型和模型推断状态。
- 现有失败来源泄漏、Prompt Injection 泄漏和 FactCheck 安全约束不回归。

### P0.7 工作包 E：状态、诊断和分层验证

- UI 显示论文评审批次、当前 provider、RAG 召回数量、LLM 重排状态和失败原因。
- 运行结果区区分“候选召回”“语义评审”“答案生成”“可信度核验”和“降级重试”。
- 日常测试使用 FakeModel、录制响应和临时 Chroma 夹具。
- 阶段测试覆盖批次失败、模型超时、Schema 错误、Web provider 失败、跨语言查询、全文缺失和索引更新。
- 真实 API 测试单独记录质量、延迟、Token、成本、限流和降级情况。

### P0.8 P0 总验收

P0 完成后必须同时满足：

1. 论文语义评审单批次失败不会导致整批论文跳过。
2. Web 主 provider 失败时可自动降级到备用来源。
3. 中文问题可以召回英文知识库中的相关论文。
4. 研究查询主答案先呈现内容，可信度与缺口后置。
5. LLM 语义判断、确定性候选排序和人工复核状态不再混淆。
6. 所有失败和降级路径均有可操作提示、结构化 Trace 和回归测试。
7. P0 全量测试、离线检索评测和离线报告评测不低于 M0/M2 当前基线。

P0 未完成或验收不通过时，不进入 M3 的 SQLite Run Store、持久 Job、初始化或迁移实现。

### P0.9 P0 验收记录（2026-07-18）

P0 已完成实现和验收，未引入 SQLite、持久 Job、初始化或迁移。验收证据如下：

| 验收项 | 结果 |
|---|---|
| 全量测试 | 243/243 通过，36.43s |
| P0 专项夹具 | 13/13 通过，覆盖批次隔离、深评保留、provider 降级、双语召回、Dense 分数、全文状态、upsert 和 Trace 诊断 |
| 离线检索评测 | recall@5 0.5882；hit_rate 0.7667；irrelevant_hit_rate 0.30，未低于 M0 基线 |
| 离线报告评测 | acceptance_pass_rate 1.0；factcheck_pass_rate 1.0 |
| 安全回归 | failed_source_leakage 0；prompt_injection_leakage 0 |
| 工具链检查 | `pip check`、`compileall`、`node --check`、`git diff --check` 通过（仅既有换行符提示） |

已确认的可用行为：论文评审批次失败不再导致整批 `skip`；深评失败保留初评；Web 支持 DuckDuckGo -> Bing/Google/SerpAPI 的授权 API 降级并记录 Trace；中文查询生成双语/术语扩展并传递真实 Dense 分数；全文状态和章节元数据可追溯；研究报告先给核心回答，再呈现证据、可信度和待核验项；Workbench 结果区显示节点、召回数量、provider 和评审错误。

P0 通过后，下一阶段仅可按 M3 范围评估本地 SQLite Run Store、持久 Job 和初始化迁移，不能把 P0 的临时 Trace 或文件产物直接视为持久化实现。

## 7. M3：持久运行时与初始化迁移

### 7.1 目标

任务、事件、审批和 Checkpoint 在进程重启后可恢复，运行数据与源码目录解耦，同时保持本地单机体验。

### 7.2 本地目录

```text
CONFLUX_HOME/
  conflux.db
  objects/
  indexes/
  exports/
  logs/
  config/
```

新增 `CONFLUX_HOME` 解析，Windows 默认 `%LOCALAPPDATA%/Conflux`。现有源码目录中的数据可以通过导入迁移，但不自动删除。

### 7.3 SQLite 表和 Repository

第一版建议表：

- `schema_migrations`
- `workspaces`
- `runs`
- `run_steps`
- `run_events`
- `approvals`
- `artifacts`
- `workflow_versions`
- `plugin_versions`
- `index_versions`

新增 `RunStore`、`EventStore`、`ApprovalStore`、`ArtifactStore`、`JobQueue` 和 `CheckpointAdapter`。项目/画像在本地模式继续由 YAML Repository 管理，SQLite 只保存路径、哈希和运行关联，不做双向同步。

### 7.4 运行时改造

- 通过 `RunContext` 注入配置，不再修改进程环境变量。
- 移除 Workbench 对全局函数的 monkey patch。
- 使用 SQLite 租约队列记录状态、取消、重试、幂等键和心跳。
- SSE 从 EventStore 读取，不依赖进程内 `_EventLog`。
- Artifact 使用内容哈希和来源 Run/Step 关联。
- Checkpoint 接入 SQLite；若 LangGraph 版本不兼容，先实现可恢复快照并记录限制。

### 7.5 初始化、迁移和诊断

```text
conflux init [--home <path>] [--mode local]
conflux migrate [--dry-run]
conflux doctor
conflux import-legacy [--source <path>] [--dry-run]
```

要求：迁移前备份、事务化版本、来源哈希幂等、Secret 不落数据库、Chroma 作为可重建派生索引。

### 7.6 验收标准

- `init` 幂等且不覆盖用户文件。
- 进程终止后重启可以查询 Run、事件和最后可恢复步骤。
- 历史会话不再依赖扫描整个报告目录。
- 重复幂等键不会重复执行有副作用步骤。
- `migrate --dry-run` 显示版本和对象变化。
- `doctor` 识别权限、数据库、模型、Embedding 和索引版本问题。
- Legacy 导入保留路径、哈希、来源和用户确认状态。
- 本地模式不需要 Postgres、Redis 或对象存储。

### 7.7 回滚

保留旧 YAML、报告和 Chroma。新运行时通过开关启用；迁移失败恢复备份并回到旧 CLI 路径。验证导入前禁止删除旧数据。

## 8. M4：Evidence Ledger 与验证闭环

### 8.1 目标

将当前单次运行的 Evidence Graph 提升为可版本化、可追踪、可影响分析的证据账本。

### 8.2 数据实体

- `SourceSnapshot`：来源身份、内容哈希、抓取时间和版本。
- `EvidenceItem`：声明、引用区间、证据类型、限制和来源 Snapshot。
- `Claim`：报告或项目结论、状态、置信度和生成 Run。
- `EvidenceRelation`：支持、矛盾、派生、替代和影响关系。
- `Transformation`：检索、LLM 评审、仲裁、综合和修订的输入输出哈希。

模型置信度不等于事实真值；历史 Evidence 不被新运行覆盖，只产生新版本或关系。

### 8.3 验证和深化

- FactCheck 输出结构化问题列表。
- 有结构性问题时回到 Synthesizer 修订一次，再运行轻量核查。
- 超过 `max_verify_iterations` 或仍有关键未验证声明时进入 `needs_review`。
- Deep Research 只在证据覆盖不足、冲突、高风险或用户选择时触发。
- 子问题独立记录检索、LLM 评审、仲裁和证据，不拼成不可分辨的一次查询。

### 8.4 影响分析

来源变化时找到受影响的 Claim、Report、ProjectPlan 和 ProgressAudit，创建待确认复核 Run；不自动改写历史报告或项目计划。

### 8.5 验收标准

- 每个报告关键声明可定位到 Evidence ID、Source Snapshot 和生成步骤。
- 来源失效或替换后可以列出受影响声明和产物。
- 失败来源泄漏可被修订路径移除或降级，保留前后版本。
- 未验证、冲突和被替代状态可在报告和工作台区分。
- 离线冲突、来源失败、Prompt Injection 和证据变化夹具通过。

## 9. M5：LLM 评审评测与示例扩展

### 9.1 目标

验证 LLM 语义评审比旧确定性评分更适合研究场景，并验证 SDK 对不同扩展类型的支持。成功不以扩展数量衡量。

### 9.2 评测方法

- 建立小规模人工标注集：查询、候选论文/搜索结果、相关性、研究价值和证据质量。
- 计算 `precision@k`、`recall@k`、`NDCG@k`、边界候选一致性和理由完整性。
- 对比旧确定性评分、LLM 批量评审、LLM 深评和混合策略。
- 记录模型、Prompt、画像、候选哈希、缓存、Token、延迟和成本。
- 对工作流、插件和模型做最小消融矩阵。

### 9.3 示例扩展选择

在 M1/M2 协议稳定后另行选定，至少覆盖一个数据源扩展和一个工作流或评测扩展。选择依据是真实使用价值、数据合法可得性、维护成本、协议边界覆盖和不增加领域核心分支。当前不固定具体名单。

### 9.4 验收标准

- LLM 评审结构化输出成功率 100%；失败样本必须为 `unreviewed`。
- 人工标注集上主要指标相对 M0 不下降；下降时必须记录适用场景和调整方案。
- 高价值、无关和边界样本都有可解释输出。
- 至少两个互补扩展通过 SDK 契约测试，其中至少一个不是纯数据源连接器。
- 默认使用离线 FakeModel 或录制响应；真实 API 评测必须显式开启。
- 评测同时报告质量、成本和延迟，不以报告长度或 Agent 数量判定成功。

## 10. M6：条件触发的服务化

### 10.1 启动条件

只有出现以下任一真实需求才评估：两个以上独立工作区并发、SQLite 队列成为可观测瓶颈、需要跨机器访问/远程 Worker/集中备份，或可信进程内插件无法满足实际隔离要求。

### 10.2 实现方法

- Postgres 替换 Run/Approval/Repository，保留迁移和 Repository 接口。
- 本地对象目录替换 S3 兼容存储，ArtifactRef 语义不变。
- Worker 使用持久队列、租约、幂等键和心跳。
- 第三方插件使用子进程或远程运行时，声明网络、文件和 Secret 权限。
- 增加工作区级访问控制和审计，不把多租户权限提前下放到本地模式。

### 10.3 验收标准

- 同一 WorkflowDefinition 和插件在本地与 Worker 模式产生兼容 StepResult。
- Worker 崩溃或网络重试不会重复提交有副作用操作。
- 工作区之间不能读取对方 Run、Artifact、Evidence 或 Secret。
- 服务化失败时可以导出工作区并恢复到单机模式。

## 11. 分层测试和安全

### 11.1 日常快速验证

每次修改默认执行：受影响模块单测、插件/工作流契约测试、核心离线查询/报告验收、静态导入检查、Secret 扫描和 `git diff --check`。

不默认执行真实网络、真实模型、长时间压力和全量迁移演练。

### 11.2 阶段验证

- 协议变化：完整契约矩阵和兼容测试。
- 存储变化：迁移、备份、恢复、幂等和进程重启。
- LLM 评审变化：人工标注集、录制响应、成本和延迟。
- 外部连接器变化：限流、超时、失败隔离和凭证脱敏。
- 权限/写入变化：路径边界、审批绕过、恶意输入和副作用重试。

### 11.3 安全最小基线

- Secret 不进入 Prompt、日志、Artifact 或普通数据库字段。
- 插件访问遵循声明权限；第一版进程内权限以校验和审计为主。
- 用户路径解析并限制在允许工作区边界。
- 文档、网页和检索内容始终是不可信数据。
- 计划写入、知识入库和文件覆盖需要明确审批。
- 每项安全检查必须对应真实威胁和回归用例。

## 12. 问题发现、回滚与复盘

### 12.1 问题分类

- 正确性：证据、引用、状态或结果错误。
- 边界：职责泄漏、插件依赖私有状态或数据双写。
- 性能：LLM、索引、队列或 UI 超出基线。
- 安全：Secret、路径、不可信内容或副作用失控。
- 体验：配置、调试、审批或开发复杂度明显上升。

### 12.2 处理流程

1. 用最小夹具复现并记录影响。
2. 判断是当前阶段修复还是架构决策变化。
3. 优先修复正确性和安全问题，必要时暂停新增功能。
4. 用最小改动修正，补充一条防回归测试或评测样本。
5. 更新验收、兼容说明和本文档偏差记录。
6. 连续两次修复都需要扩大核心边界时暂停并重新审查抽象。

### 12.3 回滚原则

- 协议变化通过版本号和适配器过渡，兼容层必须有删除版本。
- 存储迁移采用备份、事务和单向导入，保留原始文件。
- 新工作流先用显式开关启用，稳定一个版本后再考虑默认路径。
- 自动写入失败保留待审批状态，不因回滚丢失用户决策或证据。

## 13. 启动前验收

执行方案在启动 M1 前需要确认：

1. 是否同意 M1 -> M2 -> P0 -> M3 -> M4 -> M5 的顺序，M6 只条件触发。
2. 是否接受 Pydantic v2 只作为 SDK 边界依赖，核心内部保留现有轻量类型。
3. 是否接受 LLM 评审失败使用 `unreviewed`，不回退为确定性评分自动入库。
4. 是否接受 M3 使用本地 SQLite，不提前引入 Postgres/Redis。
5. 是否接受 M4 先做 Evidence Ledger 最小闭环，再做跨来源影响分析。
6. 是否接受 M5 使用人工标注集和消融评测判断 LLM 评审收益。
7. 是否接受每阶段保留显式回滚、问题分类和轻量架构复盘。

M1/M2/P0 已完成验收。M3 已满足启动闸门，但本轮只执行到 P0，未开始 SQLite、持久 Job、初始化或迁移；后续仍不得同时展开 M3-M6。每完成一个阶段，更新本文档状态、验收结果和下一阶段范围。

P0 启动前确认（已完成）：

8. 是否接受 `unreviewed` 保留候选但不等同于语义通过，确定性分数仅作为临时排序信号。
9. 是否接受 Web provider 通过授权 API 或聚合服务降级，不默认抓取 Google/Bing 搜索页面。
10. 是否接受研究查询采用“先回答、后评估可信度、最后列出缺口”的用户输出顺序。
11. 是否接受中英双语查询改写、LLM 候选重排和章节级论文索引作为 P0 的必要范围。
