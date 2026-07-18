# M0 基线报告

> 文档状态：已完成
>
> 日期：2026-07-18
>
> 上位方案：[docs/execution_plan_v1.md](execution_plan_v1.md)

## 1. 概述

本报告记录 Conflux 在 **M0（基线与实施准备）** 阶段的核心行为与性能基线，用于后续 M1-M5 对比验证。

所有基线指标均来自离线评测：不依赖真实 API Key 或外部网络，可以在新机器或临时工作区复现。

## 2. 测试基线

### 2.1 单元测试

| 指标 | 值 |
|---|---|
| 测试文件数 | 13 |
| 测试用例数 | 149 |
| 通过率 | 100%（149/149） |
| 执行时间（冷） | ~52s |
| 执行时间（温） | ~36s |
| 执行命令 | `python -m pytest -q` |

测试文件清单：

- `test_acceptance.py` — 报告验收与 FactCheck
- `test_agent.py` — 研究 Agent 与子 Agent
- `test_paper_ingestion.py` — 论文摄入流
- `test_paper_promotion.py` — 论文入库
- `test_paper_radar.py` — 论文雷达/发现
- `test_phase2.py` — Phase 2 多源调研
- `test_progress_audit.py` — 进度审计
- `test_project_registry.py` — 项目注册与监控
- `test_quality_gates.py` — 质量门禁
- `test_real_query_regressions.py` — 真实查询回归
- `test_research_profile.py` — 研究画像
- `test_roadmap_features.py` — 路线图功能
- `test_workbench.py` — 工作台

### 2.2 已知状态

- 所有 149 个测试通过，无已知不稳定测试或 flaky 用例。
- `test_real_query_regressions.py` 在无 API Key 时自动 skip，不影响离线结果。

## 3. 检索评测基线

### 3.1 整体指标

| 指标 | 值 |
|---|---|
| recall@5 | **0.5882** |
| hit_rate | **0.7667** |
| source_coverage | 0.5882 |
| irrelevant_hit_rate | **0.30** |
| 评测用例数 | 30 |
| RAG 预期命中数 | 17 |
| RAG 预期命中中失败数 | **7（41.2%）** |
| 执行命令 | `python scripts/eval_retrieval.py --offline` |

### 3.2 失败模式分析

7 个 RAG 预期命中但词法检索失败的用例：

| Case ID | Query | 失败原因 |
|---|---|---|
| gd_002 | 什么是后量子密码学？ | 无词法文档命中 |
| gd_005 | 中国和欧盟的AI监管有什么不同？ | 无词法文档命中 |
| gd_012 | 后量子密码迁移为什么需要提前规划？ | 无词法文档命中 |
| gd_014 | 中国生成式AI监管为什么强调内容安全？（变体） | 无词法文档命中 |
| gd_018 | 量子计算对区块链安全有什么影响？ | 无词法文档命中 |
| gd_019 | AI监管中的风险分级方法有什么优点？ | 无词法文档命中 |
| gd_021 | 中国生成式AI监管为什么强调内容安全？ | 无词法文档命中 |

共同特征：查询使用了语义化、概括性表述（如"有什么优点""为什么需要提前规划"），现有词法匹配（关键词 + 术语重合）无法找到对应文档。**这正是 LLM 语义评审需要解决的差距。**

### 3.3 当前检索方式

- RAG：BM25 + Chroma 混合检索（`HybridRetriever`），基于词项匹配和向量相似度
- 评分：确定性分数（`matched_terms` 计数归一化），无 LLM 参与
- 评测用离线语料中文档类别有限（量子密码、AI 监管、NIST 标准、ArcGIS 教程等）

### 3.4 当前评分方式的限制

1. **纯词法/向量匹配**：无法理解查询意图和文档语义关系。「后量子密码迁移为什么需要提前规划？」虽然可以匹配到 "post-quantum" 或 "migration"，但如果文档使用 "transition"、"roadmap" 等表述，词法匹配就会失败。
2. **未区分研究价值**：`esri--arcgis-pro-layers.md` 匹配到 "RAG" 和 "Web" 两个词项后获得高分，但完全不相关。
3. **无 LLM 语义评审**：当前论文发现（`scorer.py`）同样使用确定性关键词/字段/会议匹配，不评估论文方法、证据质量和研究价值。
4. **结果无结构化评审字段**：当前产出仅有分数和匹配词，无 `relevance`、`research_value`、`evidence_quality`、`confidence` 等字段。

## 4. 报告评测基线

### 4.1 整体指标

| 指标 | 值 |
|---|---|
| source_status_coverage | **1.0** |
| acceptance_pass_rate | **1.0** |
| factcheck_pass_rate | **1.0** |
| failed_source_leakage | **0** |
| prompt_injection_leakage | **0** |
| avg_latency_ms | 10 |
| estimated_cost | 0.0 |
| 评测用例数 | 3 |
| 执行命令 | `python scripts/eval_reports.py --offline` |

### 4.2 离线评测说明

当前报告评测使用 **预先录制的模型响应**（离线 FakeModel），不产生真实 API 成本。三个评测场景：

1. **source_failure** — Web 失败时，失败来源不泄漏到 Evidence Graph 和报告
2. **prompt_injection** — 检索到的 Prompt Injection 文本不被作为系统指令执行
3. **disagreement** — RAG 和 Web 存在冲突时，仲裁和综合正确处理

### 4.3 已知限制

- 离线评测覆盖 3 个场景，但未覆盖真实模型运行时的不确定性、幻觉、Schema 违规等
- FactCheck 当前为单次核查，无自动修订再核查循环（已记录为待改造项）
- 评测成本为零（离线），不能反映真实 LLM 评审的成本和延迟
- 无论文雷达/发现路径的报告评测覆盖

## 5. 当前功能入口点

### 5.1 CLI 入口

| 入口 | 命令 | 功能 |
|---|---|---|
| 研究查询 | `python -m conflux "<query>"` | Phase 2 多源调研（RAG + Web + Model） |
| 文档索引 | `python -m conflux --index <dir>` | 构建本地 RAG 索引 |
| 论文发现 | `python -m conflux.paper_ingestion inbox` | 根据画像发现论文 |
| 论文入库 | `python -m conflux.paper_ingestion promote` | 人工确认后入库论文 |
| 论文 CLI | `python -m conflux.papers` | 兼容入口（→ paper_ingestion.cli） |
| 进度快照 | `python -m conflux.progress snapshot` | 建立项目基线 |
| 进度审计 | `python -m conflux.progress audit` | 比较 Git/文件/测试变化 |
| 研究画像 | `python -m conflux.research_profile` | 画像管理 |
| 工作台 | `python -m conflux.workbench` | 本地 Web 界面 |

### 5.2 核心模块位置

| 模块 | 路径 | 职责 |
|---|---|---|
| CLI | `src/conflux/__main__.py` | 研究查询、索引 CLI |
| Graph V2 | `src/conflux/graph_v2.py` | LangGraph 多 Agent 工作流 |
| Evidence | `src/conflux/evidence.py` | 声明级证据、Evidence Graph、共识投票 |
| Source Status | `src/conflux/source_status.py` | 五态来源协议、来源排除规则 |
| Report | `src/conflux/report.py` | Markdown/HTML 报告生成 |
| Trace | `src/conflux/trace.py` | Trace JSONL + Run Summary |
| Checkpoint | `src/conflux/checkpointing.py` | 内存 Checkpointer |
| Paper Ingestion | `src/conflux/paper_ingestion/` | 论文发现、筛选、入库 |
| Progress Audit | `src/conflux/progress_audit/` | Git 检查、测试检查、审计报告 |
| Project Registry | `src/conflux/project_registry/` | 项目注册、监控、计划分析 |
| Research Profile | `src/conflux/research_profile/` | 研究画像加载与校验 |
| Workbench | `src/conflux/workbench/` | 本地 Web 工作台（Python stdlib `ThreadingHTTPServer` + SSE） |

## 6. M0 历史架构问题（来自 architecture.md §3.3 确认）

本节记录的是 M0 建立时的历史问题，用于解释后续阶段为什么需要改造；它不等同于当前实现状态。

以下问题已在 M0 基线中确认，M1-M4 逐步解决：

1. **固定来源枚举**：`SourceName` 和图状态固定为 RAG/Web/Model，新增来源需修改核心状态、节点、Trace 和报告。
2. **文本 marker 中转**：`SourceResult` 在工具和图之间通过文本 marker 序列化/反解析。
3. **无统一协议**：查询、论文、项目和审计共享目录与配置，但无统一的 Run/Step/Event/Artifact/Approval 协议。
4. **工作台专用 API**：不同能力维护专用 API，用户扩展无法声明输入输出和运行生命周期。
5. **内存任务调度**：后台任务保存在内存，通过全局环境变量覆盖和执行锁运行。
6. **进程内 Checkpoint**：历史会话依赖扫描报告目录，Checkpoint 仅为内存 MemorySaver。
7. **FactCheck 未闭环**：无自动修订再核查循环；Deep Research 未按风险和证据缺口动态触发。
8. **数据分散**：YAML、JSON、JSONL、`.env.workbench`、报告目录、Chroma 各存各的，无统一初始化和迁移版本。
9. **确定性评分为主**：论文和搜索结果主要依赖确定性相关性分数，无 LLM 语义评审。

## 7. 测试夹具约定

M0 创建了 `tests/fixtures/architecture/` 目录，子目录约定：

| 目录 | 用途 | 目标阶段 |
|---|---|---|
| `plugin_manifests/` | 有效/无效 Manifest 夹具 | M1 |
| `workflows/` | YAML 工作流夹具 | M2 |
| `migrations/` | Schema 迁移夹具（旧 → 新） | M3 |
| `source_snapshots/` | 来源版本变化夹具 | M4 |
| `llm_recordings/` | LLM 录制响应 | M5 |

夹具原则：
- 不写入 `reports/`、`data/chroma_db/` 或用户项目路径
- 使用 pytest `tmp_path` 或 checked-in fixture 文件
- 不依赖真实 API Key 或外部网络
- LLM 夹具使用 FakeModel 或录制响应

## 8. 当前成本与执行模型

| 操作 | 是否需要 API Key | 是否有离线回退 |
|---|---|---|
| 单元测试（全部） | 否 | 始终离线 |
| 离线检索评测 | 否 | FakeModel |
| 离线报告评测 | 否 | FakeModel |
| RAG 索引构建 | 需要 EMBEDDING Key | Chroma 嵌入需真实 API |
| 真实研究查询 | 需要 REASONING + EMBEDDING Key | 无 |
| 论文发现（ArXiv） | 否（ArXiv API 免费） | — |
| 论文分析（语义） | 需要 REASONING Key | 无 |
| 项目计划分析 | 需要 REASONING Key | 无 |
| 进度审计 | 否（仅 Git/文件检查） | — |
| 真实 API 评测 | 需要全部 Key | `--real` 显式开启 |

## 9. 可复现性声明

以下基线可以在任意干净环境复现（需 Python 3.11+，`pip install -e ".[dev]"`）：

```powershell
# 单元测试基线
python -m pytest -q

# 离线检索评测
python scripts/eval_retrieval.py --offline

# 离线报告评测
python scripts/eval_reports.py --offline
```

以上三条命令不需要任何 API Key、`.env` 或外部网络。RAG 索引构建和真实查询需要 API Key，不在离线基线范围内。

## 10. M0 验收确认

对照 `execution_plan_v1.md` §4.3：

| 验收标准 | 状态 |
|---|---|
| 基线结果可以在新机器或临时工作区重复生成 | ✅ 离线命令无需 API Key |
| 基线报告明确列出当前 RAG/Web 确定性评分的限制 | ✅ §3.4 + §6.9 |
| 当前功能行为没有因 M0 改变 | ✅ 无代码、依赖或配置变更 |
| 后续阶段可以引用同一份基线，不依赖个人未提交文件 | ✅ 本报告可提交到仓库 |

M0 已完成并作为不可覆盖的历史对照；M1、M2 已在此基线之上完成，M3 及以后尚未启动。

## 11. M1-M2 后续验证快照

2026-07-18 在同一工作区完成 M1、M2 及本轮修复后的验证：

| 指标 | 当前值 | 与 M0 的关系 |
|---|---:|---|
| 全量测试 | 230/230 通过 | 新增协议、能力和回归测试；不覆盖 M0 的 149 用例记录 |
| 离线 recall@5 | 0.5882 | 与 M0 相同，语义召回改进尚未计入离线词法基准 |
| 离线报告验收率 | 1.0 | 与 M0 相同 |
| 失败来源泄漏 | 0 | 与 M0 相同 |
| Prompt Injection 泄漏 | 0 | 与 M0 相同 |

M0 指标保持固定，不能用新增测试数量或一次真实 API 结果直接替换。后续阶段应继续运行 §9 的三条命令，并把真实 API 的质量、延迟、成本和降级情况单独记录为验证快照。

## 12. P0 验收后验证快照

2026-07-18 完成 P0 研究质量与可用性修复。以下数据是当前实现快照，不覆盖 M0 历史基线：

| 指标 | 当前值 | 与 M0 的关系 |
|---|---:|---|
| 全量测试 | 243/243 通过 | 包含 P0 专项夹具；M0 的 149 用例记录保持不变 |
| P0 专项夹具 | 13/13 通过 | 覆盖评审容错、Web 降级、双语召回、全文状态、索引 upsert 和 Trace |
| 离线 recall@5 | 0.5882 | 未低于 M0；离线语料仍主要衡量确定性召回 |
| 离线报告验收率 | 1.0 | 与 M0 相同 |
| failed_source_leakage | 0 | 与 M0 相同 |
| prompt_injection_leakage | 0 | 与 M0 相同 |

P0 新增能力还需要真实 API/真实英文论文全文样本评估语义质量、跨语言召回增益、延迟、Token 和降级成本；这些指标不能用离线 FakeModel 结果替代。
