# Conflux — 三源知识多智能体调研系统 · 项目深度解析

> **用途**：面试准备 · 项目深挖材料  
> **项目定位**：结合本地知识库 (RAG) + 互联网权威信息检索 (Web) + 模型世界知识 (Model) 的多智能体调研系统，用于话题调研、问题解答、信息获取、知识体系搭建。  
> **设计目标**：展示工程化成熟度 —— 架构设计、证据网络、不确定性管理、评估体系、成本追踪、流程可视化、降级方案。  
> **技术栈**：Python 3.11+ / LangGraph / LangChain / ChromaDB / BM25 / DuckDuckGo / YAML / pytest  
> **代码规模**：~25 个源文件，~15 个测试文件，~1000 行架构设计文档

---

## 目录

1. [总体架构](#1-总体架构)
2. [LangGraph 状态图设计](#2-langgraph-状态图设计)
3. [三源知识仲裁系统](#3-三源知识仲裁系统)
4. [证据网络 (Evidence Graph)](#4-证据网络-evidence-graph)
5. [Loop Engineering — 五层嵌套循环](#5-loop-engineering--五层嵌套循环)
6. [来源状态协议 (Source Status Protocol)](#6-来源状态协议-source-status-protocol)
7. [RAG 子系统](#7-rag-子系统)
8. [Web 检索与模型知识工具](#8-web-检索与模型知识工具)
9. [FactCheck 事实核查](#9-factcheck-事实核查)
10. [配置系统](#10-配置系统)
11. [模型工厂 (Model Factory)](#11-模型工厂-model-factory)
12. [成本追踪 (Cost Ledger)](#12-成本追踪-cost-ledger)
13. [断路器模式 (Circuit Breaker)](#13-断路器模式-circuit-breaker)
14. [质量评分与验收门](#14-质量评分与验收门)
15. [Trace 结构化追踪](#15-trace-结构化追踪)
16. [评估体系 (Evaluation)](#16-评估体系-evaluation)
17. [Prompt 管理策略](#17-prompt-管理策略)
18. [安全护栏设计](#18-安全护栏设计)
19. [降级方案与延迟 SLO](#19-降级方案与延迟-slo)
20. [报告生成](#20-报告生成)
21. [CLI 入口与开发流程](#21-cli-入口与开发流程)
22. [测试策略](#22-测试策略)
23. [设计模式总结](#23-设计模式总结)
24. [面试常见追问](#24-面试常见追问)

---

## 1. 总体架构

### 1.1 宏观三层

```
┌──────────────────────────────────────────────────────────┐
│  第三层：Meta-Cognition Layer（元认知层）                   │
│  负责全局调度、不确定性溯源、报告合成、人的最终决策点          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │ Orchestrator │  │ EvidenceGraph │  │ ReportComposer │ │
│  └──────────────┘  └───────────────┘  └────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  第二层：Agent Loop Layer（多智能体循环层）                  │
│  每个 Agent 有独立的 ReAct + Reflexion 内环                │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────────┐ │
│  │RAG Agent │ │Web Agent │ │Model Agent│ │FactCheck    │ │
│  └──────────┘ └──────────┘ └───────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────┤
│  第一层：Tool & Retrieval Layer（工具与检索层）             │
│  ChromaDB + BM25 + DuckDuckGo/SerpAPI + LLM              │
└──────────────────────────────────────────────────────────┘
```

- **元认知层**：`graph_v2.py` 中的 evidence_merge → synthesize → factcheck → deeper_research 构成了最上层的全局调度。它不直接调用工具，而是消费下层 Agent 的产出做仲裁、合成、验证和深挖。
- **Agent 层**：三个并行的单工具子 Agent（RAG/Web/Model）+ FactCheck Agent，每个都是 ReAct + Reflexion 的独立循环。
- **工具层**：`tools/rag.py`、`tools/web.py`、`tools/model.py` 是 LangChain `@tool` 装饰器包装的函数，返回嵌入了 `CONFLUX_SOURCE_RESULT_JSON` 标记的结构化文本。

### 1.2 三源知识分层模型

| 知识源 | 代号 | 优势 | 劣势 | 典型延迟 |
|--------|------|------|------|---------|
| 本地知识库 (RAG) | **L** | 可控、可审计、领域深度 | 范围有限、可能过时 | <1s |
| 互联网检索 (Web) | **W** | 实时、广度大 | 权威性参差、噪音多 | 3-8s |
| 模型世界知识 (Model) | **M** | 零延迟、推理整合强 | 幻觉风险、知识截止、无溯源 | <0.5s |

**设计理念**：三源互补 —— RAG 提供确定性事实，Web 提供时效性补充，Model 填补知识空白并做推理整合。三者的缺点也互相制约：RAG 和 Web 的可追溯性可以检查 Model 的幻觉；Model 和 Web 的广度可以弥补 RAG 的范围局限。

### 1.3 核心数据流

```
用户输入 query
  → dispatch (初始化 run_id/thread_id/计时)
  → [fan-out 并行] rag_agent | web_agent | model_agent
      每个子 Agent: 先调专属工具(SourceResult) → LLM 合成 → Reflexion 自反思
  → evidence_merge (解析 SourceResult → 构建 EvidenceGraph → 仲裁器运行五级冲突协议)
  → synthesize (基于 merge + arbitration + evidence 生成 Markdown 报告)
  → factcheck (确定性检查 + LLM 核查 → 修正报告，标记 passed/needs_review)
  → deeper_research (L4: 从报告中提取子问题 → 生成深化补充 → 追加到 final_answer)
  → 输出 .md + .html + .trace.jsonl + .summary.json
```

---

## 2. LangGraph 状态图设计

### 2.1 为什么用 LangGraph 而不是 while 循环？

| 特性 | while 循环 | LangGraph |
|------|-----------|-----------|
| **可观测性** | 需自行埋点 | 每个 Node 自动记录状态 |
| **可中断/恢复** | 复杂状态管理 | Checkpointer 原生支持断点续跑 |
| **可并行** | 手动管理 | `Send()` API 原生 fan-out |
| **流程可视** | 无 | LangSmith 自动追踪 |
| **状态隔离** | 全局变量污染风险 | 每个 Node 接收不可变 state 快照 |

### 2.2 MultiAgentState（`graph_v2.py:34-61`）

```python
class MultiAgentState(TypedDict):
    query: str                          # 用户问题
    rag_result: str                     # RAG Agent 输出
    web_result: str                     # Web Agent 输出
    model_result: str                   # Model Agent 输出
    _merged: str                        # 三方结果合并文本
    _arbitration: str                   # 仲裁器输出
    _evidence_json: str                 # 证据网络 JSON
    _source_statuses: dict              # 来源状态（RAG/Web/Model 各自 success/failed/fallback）
    _verified_answer: str               # FactCheck 验证结果
    _factcheck_status: str              # passed / needs_review
    _factcheck_report: str              # FactCheck 详细报告
    _deep_research: str                 # L4 深化研究补充
    _run_summary: dict                  # 运行摘要（计时/SLO/阶段列表）
    _quality_report: dict               # 质量评分
    _pipeline_stage: str                # 当前阶段
    _run_id: str                        # 运行 ID
    _thread_id: str                     # 线程 ID（用于 checkpoint 恢复）
    _checkpoint_backend: str            # checkpoint 后端类型
    _resumed: bool                      # 是否从 checkpoint 恢复
    _review_status: str                 # awaiting_user_review / accepted
    final_answer: str                   # 最终报告
```

设计要点：
- 21 个字段覆盖了从输入到输出的全过程，每个字段对应一个 Pipeline 阶段。
- `_` 前缀字段是内部中间产物，`final_answer` 是面向用户的最终输出。
- `_run_summary` 贯穿全流程，在每个阶段被 `_append_stage()` 更新，记录耗时和 SLO 状态。

### 2.3 图的拓扑结构（`graph_v2.py:799-844`）

```
__start__
    │
    ▼
dispatch ──[fan-out]──▶ rag_agent ──┐
            Send()  ▶  web_agent ──┤
                      model_agent ─┘
                           │
                           ▼
                    evidence_merge
                           │
                           ▼
                      synthesize
                           │
                           ▼
                       factcheck
                        ╱    ╲
               [L4 enabled]   [done]
                    │            │
                    ▼            ▼
            deeper_research    END
                    │
                    ▼
                   END
```

**关键实现细节**：

1. **Fan-out 并行派发**（`graph_v2.py:619-625`）：
```python
def fanout(state: MultiAgentState) -> list[Send]:
    return [
        Send("rag_agent", state),
        Send("web_agent", state),
        Send("model_agent", state),
    ]
```
LangGraph 的 `Send()` API 将同一个 state 副本并行发送给三个子 Agent，它们各自独立运行 ReAct 循环。三个 Agent 都完成后，在 `evidence_merge` 节点汇聚。

2. **Agent 节点通过 closure 注入**（`graph_v2.py:811-813`）：
```python
graph.add_node("rag_agent", lambda s: rag_agent_node(s, agent=rag_agent))
```
因为 LangGraph 节点签名固定为 `(state) -> dict`，使用 lambda 将 `ResearchAgent` 实例注入。

3. **条件边**（`graph_v2.py:838-841`）：
```python
graph.add_conditional_edges("factcheck", factcheck_router, {
    "deeper_research": "deeper_research",
    "end": END,
})
```
根据配置和 FactCheck 结果决定是否进入 L4 深挖。

---

## 3. 三源知识仲裁系统

### 3.1 五级冲突升级协议（`graph_v2.py:321-439`）

这是处理三源信息冲突的核心机制，从自动到人工逐级升级：

| 级别 | 名称 | 逻辑 | 置信度 |
|------|------|------|--------|
| **L0** | 一致性锚定 | 三源 success 一致 → 直接采纳 | > 0.9 |
| **L1** | 双向仲裁 | 两源一致 vs 一源分歧，多数原则 | 0.7-0.9 |
| **L2** | 权威加权投票 | 每个 success 源按权威分加权：RAG=0.7, Web=0.5, Model=0.4 | 加权计算 |
| **L3** | 溯源深挖建议 | 加权后仍存争议 → 建议回溯原始 Agent 输出交叉验证 | 标记 contested |
| **L4** | 人工升级标记 | 不可自动裁决 → `[HUMAN_ESCALATION_NEEDED]` | 待人工 |

**权威分权重设计理由**：
- **RAG 0.7**：本地知识库可控、可审计，文档经过人工筛选，可信度最高。
- **Web 0.5**：互联网信息权威性参差，但可追溯 URL。
- **Model 0.4**：模型知识无溯源，有幻觉风险，但仍可用于推理和填补空白。

**关键安全规则**：只有 `status == "success"` 的来源才能参与共识投票，`failed` / `fallback` 来源被排除在外。这是通过 `SourceResult.is_valid_evidence` 属性强制实施的。

### 3.2 仲裁器 Prompt 结构（`graph_v2.py:346-439`）

仲裁器使用 cheap 模型（低成本），输入包括：
- 用户原始问题
- 三源状态表（`source_status_markdown`）
- 证据网络摘要 JSON
- 三源合并后的原始文本

输出格式严格结构化：五个 Level 段落，每个段落列出具体声明及其置信度，最后输出整体评估。

---

## 4. 证据网络 (Evidence Graph)

### 4.1 数据结构（`evidence.py`）

```python
@dataclass
class EvidenceNode:
    id: str                              # 唯一标识
    claim: str                           # 声明内容（截断到 240 字符）
    source: Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]
    source_detail: str                   # 具体来源（文档ID/URL）
    authority_score: float               # 来源权威分
    evidence_refs: list[str]             # 参考文献引用
    confidence: float                    # 声明自身置信度
    limitations: list[str]               # 已知限制
    timestamp: str                       # ISO 时间戳
    supporting: list[str]                # 支持此声明的其他节点 ID
    contradicting: list[str]             # 与此声明矛盾的节点 ID
    derived_from: list[str]              # 上游推理节点
    uncertainty: float                   # 不确定性总分
    uncertainty_breakdown: dict          # 五维不确定性分解
    verified: bool                       # 是否已被 FactCheck 验证
```

**五维不确定性分解**（对应架构文档 §2.3）：
```python
uncertainty_breakdown = {
    "aleatoric": 0.1,       # 数据固有噪音（多高质量源间的小差异）
    "epistemic": 0.15,      # 知识不足（该主题缺少权威源覆盖）
    "source_quality": 0.05, # 源质量导致
    "temporal": 0.2,        # 时效性衰减（信息可能过时）
    "consensus_gap": 0.3,   # 源之间未达成共识
}
```

报告中呈现为："本结论置信度 78%。主要不确定性来自：信息可能已过时，且不同权威源之间存在分歧。"

### 4.2 EvidenceGraph 核心方法（`evidence.py:61-158`）

| 方法 | 功能 | 复杂度 |
|------|------|--------|
| `add_node()` | 添加声明节点，自动从 SOURCE_AUTHORITY 获取默认权威分 | O(1) |
| `add_support()` | 建立支持关系（双向连接） | O(1) |
| `add_contradiction()` | 建立矛盾关系（双向连接） | O(1) |
| `find_contradictions()` | 遍历所有节点检测矛盾对 | O(n²) 最坏 |
| `find_single_source()` | 找出无任何关联的孤立声明 | O(n) |
| `consensus_summary()` | 生成统计摘要（总数/共识/争议/单源/源分布/平均权威） | O(n) |
| `propagate_uncertainty()` | 低权威节点的不确定性向其支持的所有下游节点传播 | O(n²) |
| `link_surface_relations()` | 基于 claim 文本相似度（>55%）和情感极性自动发现支持/矛盾关系 | O(n²) |

### 4.3 两层图的职责边界

这是架构设计中的一个关键决策：

- **EvidenceGraph（临时内存图）**：每次查询时构建，存储本次查询的所有声明及其关系。查询结束后序列化到报告的附录 A 中（JSON 格式），用于审计和可追溯性。这是 **运行时证据网络**。
- **Neo4j 持久图（规划中）**：离线构建的文档级知识图谱，存储实体、关系、社区摘要。用于 Graph RAG 的结构化检索（实体关系查询、多跳推理）。这是 **离线知识图谱**。

当前实现聚焦于 EvidenceGraph，Neo4j 集成是 Phase 3 规划。

### 4.4 声明提取（`evidence.py:219-244`）

`extract_claims_from_text()` 对 Agent 输出的自然语言文本做粗粒度声明提取：
- 按段落和列表项分割
- 过滤标题行和分隔线
- 清洗 Markdown 格式标记
- 过滤短于 8 字符或为 "none"/"n/a" 的无效文本

### 4.5 构建 EvidenceGraph 的入口（`evidence.py:180-216`）

`build_evidence_graph_from_results()` 是 Phase 2 的入口函数：
1. 遍历三源 `SourceResult`
2. **只有 `result.is_valid_evidence == True`**（即 `status ∈ {success, low_relevance}` 且内容非空）的来源才进入节点构建
3. 优先使用 Agent 在工具层提取的结构化 `AgentClaim` 列表
4. 如果没有 `AgentClaim`，回退到文本级 `extract_claims_from_text()`
5. 最后执行 `link_surface_relations()`（自动发现关系）+ `propagate_uncertainty()`（不确定性传播）

---

## 5. Loop Engineering — 五层嵌套循环

### 5.1 五层结构

从外到内：

```
L5: Goal Loop（目标循环）
    用户设定总目标 → Orchestrator 分解子问题 → 逐个解决 → 合成报告
    → 用户反馈 → 修正/深化 → 继续...
    止条件：用户确认满意 或 连续2轮无实质改进
    硬上限：3 轮

L4: Research Loop（调研循环）
    针对单个子问题：搜索 → 阅读 → 提取声明 → 交叉验证 → 发现新子问题
    止条件：信息饱和（本轮新事实 < 上轮 20% AND 新来源 < 上轮 30%）
    硬上限：3 轮

L3: Agent Loop（Agent 内循环）
    ReAct: Thought → Action → Observation → ...
    关键改造：加入 Reflexion 反思步骤
    Thought → Action → Observation → Self-Critique → Refine → ...
    止条件：Agent 自评完成 或 达到迭代上限
    硬上限：3 轮

L2: Verification Loop（验证循环）
    Maker-Checker 模式：synthesize (Maker) → factcheck (Checker)
    → 通过 / 驳回 / 要求修正...
    硬上限：2 轮；不通过 → 标记为 uncertain

L1: Retrieval Loop（检索细粒度循环）
    初检 → CRAG 评估检索质量 → 若不足则改写 Query → 再检索
    止条件：检索质量达标 或 改写2次无改善 → 降级到 Web Search
    硬上限：2 轮
```

### 5.2 当前实现状态

- **L1**（Retrieval Loop）：部分实现。`tools/rag.py` 和 `tools/web.py` 中通过 4 因子/5 因子确定性相关性评分实现检索质量门控，将低质量结果标记为 `low_relevance` 或 `no_evidence`。但 CRAG 风格的检索质量评估器 + Query 改写 + 降级到 Web 的闭环尚未实现（Phase 3 规划）。
- **L2**（Verification Loop）：完整实现。`synthesize`（Maker）产出报告 → `factcheck`（Checker）做确定性检查 + LLM 核查 → 修正或通过。当前配置 `max_verify_iterations=1`。
- **L3**（Agent Loop）：完整实现。`_run_agent()` 内部先执行专属工具（`_run_exclusive_tool`）获取 SourceResult → LLM 合成 → Reflexion 自反思（`_reflect_and_refine()`）。最多 3 轮。
- **L4**（Research Loop）：已实现。`deeper_research_node()` 从首轮报告中通过 LLM 提取子问题（`discover_sub_questions()`），生成深化补充并追加到 `final_answer`。`max_deep_questions=2`。
- **L5**（Goal Loop）：`process_user_feedback()` 函数已实现，但尚未集成到主 Graph 中（Phase 3 规划）。

### 5.3 组合爆炸分析

最坏情况：3×3×3×2×2 = 108 次 LLM 调用。但实际中：
- L3 Agent Loop 通常第 1 轮就完成（工具已返回足够信息）
- L2 验证通常第 1 轮通过
- L4 深度研究通常提取不到子问题时跳过

预期单次查询 < 25 次 LLM 调用。通过 `budget.max_llm_calls=20` 做硬约束。

---

## 6. 来源状态协议 (Source Status Protocol)

这是 Conflux 最核心的工程创新之一 —— 一个贯穿全流程的结构化数据契约。

### 6.1 核心数据结构（`source_status.py`）

```python
MARKER = "CONFLUX_SOURCE_RESULT_JSON"  # 机器可读标记

@dataclass
class AgentClaim:
    claim: str                    # 声明文本
    source: SourceName            # RAG/Web/Model/FactCheck/Synthesize
    evidence_refs: list[str]      # 证据引用（如 [RAG:file#chunk-001]）
    confidence: float             # 声明级置信度
    limitations: list[str]        # 已知限制

@dataclass
class SourceResult:
    source: SourceName            # 来源名称
    status: SourceStatus          # success / low_relevance / no_evidence / failed / fallback
    content: str                  # 人类可读内容
    detail: str                   # 来源详情（如 "Local Chroma hybrid retrieval"）
    error: str                    # 错误说明
    claims: list[AgentClaim]      # 结构化声明列表
    metadata: dict                # 扩展元数据
```

### 6.2 嵌入与解析

**写入**（`SourceResult.to_tool_text()`）：
```python
def to_tool_text(self) -> str:
    payload = json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
    body = self.content.strip() or self.error.strip() or "无内容。"
    return f"{MARKER}: {payload}\n\n{body}"
```
每个工具的输出是 `CONFLUX_SOURCE_RESULT_JSON: {"source":"RAG","status":"success",...}\n\n实际内容`。

**读取**（`parse_source_results()`）：
```python
def parse_source_results(text: str) -> list[SourceResult]:
    pattern = rf"{re.escape(MARKER)}:\s*(\{{.*?\}})(?=\n|$)"
    for match in re.finditer(pattern, text, flags=re.DOTALL):
        payload = json.loads(match.group(1))
        results.append(SourceResult.from_dict(payload))
    return results
```

**清洗**（`strip_source_markers()`）：从面向用户的文本中移除机器可读标记。

### 6.3 关键规则

**两级证据分类**：

```python
EVIDENCE_STATUSES = {"success", "low_relevance"}
NON_EVIDENCE_STATUSES = {"no_evidence", "failed", "fallback"}
```

**`is_valid_evidence` 属性**：
```python
@property
def is_valid_evidence(self) -> bool:
    return self.status in EVIDENCE_STATUSES and bool(self.content.strip())
```

这是整个系统的安全闸门 —— `success` 和 `low_relevance` 来源可以进入 EvidenceGraph 作为证据节点并参与仲裁投票，但 `low_relevance` 作为弱相关证据会降权处理。

- **`success`**：工具成功执行，相关性评分 ≥ 0.55（RAG）或 ≥ 0.55 且 ≥ 2 条结果（Web），作为高置信证据参与投票。
- **`low_relevance`**：工具成功执行但相关性较弱（RAG: 0.25-0.55，Web: 不满足 success 条件但 ≥ 0.35），可作为弱相关上下文参与低权重投票。
- **`no_evidence`**：工具执行了但所有结果被相关性/质量过滤掉，不可作为证据。
- **`failed`**：工具执行失败（异常/无结果/API 不可用），不可作为证据。
- **`fallback`**：Agent 在没有成功工具结果时自行生成的内容（模型推断），不可作为事实证据。

`no_evidence`、`failed` 和 `fallback` 来源：
- 在报告中仍然显示（透明度）
- 但明确标注不可作为事实支持
- 被确定性 FactCheck 自动检测是否被误用
- 仲裁器中明确排除在共识投票之外

**辅助判断函数**：
- `status_is_evidence(status)`：返回 status 是否属于 EVIDENCE_STATUSES
- `status_is_non_evidence(status)`：返回 status 是否属于 NON_EVIDENCE_STATUSES
- `is_low_relevance` 属性：便捷判断 `status == "low_relevance"`

### 6.4 五种状态的语义

| 状态 | 含义 | 触发条件 | 能否作为证据 |
|------|------|---------|-------------|
| `success` | 工具成功执行，结果相关性高 | RAG: score≥0.55; Web: score≥0.55 且 ≥2 条 | ✅ 高置信证据 |
| `low_relevance` | 工具执行成功但相关性较弱 | RAG: 0.25≤score<0.55; Web: score≥0.35 但不满足 success | ⚠️ 弱相关证据，降权 |
| `no_evidence` | 工具执行了但所有结果被过滤 | 检索返回结果但全部低于最低相关性阈值 | ❌ 不可作为证据 |
| `failed` | 工具执行失败或结果不可用 | 异常/无结果/API 不可用 | ❌ 不可作为证据 |
| `fallback` | Agent 自行补写（无工具支持） | 模型在没有成功工具结果时生成的内容 | ❌ 不可作为证据 |

---

## 7. RAG 子系统

### 7.1 多粒度分块（`rag/chunker.py`）

```
文档 → L1 父块 (1024 tokens) ──→ 用于上下文窗口扩展
     → L2 子块 (256 tokens)  ──→ 用于精确检索和索引
```

子块通过 `parent_id` 反向引用父块，支持检索到子块后扩展上下文窗口到父块（在报告附录 C 中可见完整的 chunk citation 表格）。

技术细节：
- 使用 `tiktoken` 的 `cl100k_base` 编码做 token 计数（匹配 OpenAI text-embedding-3 系列）
- 每个 chunk 的 metadata 包含：`chunk_type`(parent/child)、`chunk_id`、`parent_id`、`char_start`、`char_end`
- chunk_id 格式：`filename#p{parent_idx}#c{child_idx}`

### 7.2 混合检索器（`rag/retriever.py`）

```python
class HybridRetriever:
    def search(self, query: str) -> list[Document]:
        # 1. Dense: ChromaDB 向量相似度搜索 (top_k=10)
        # 2. Sparse: BM25 词法匹配 (top_k=10)
        # 3. RRF (Reciprocal Rank Fusion): dense_weight=0.7 + bm25_weight=0.3
        # 4. 返回 final_k=5 个文档
```

**RRF 融合公式**：
```
RRF_score(doc) = dense_weight × 1/(dense_rank + 60) + bm25_weight × 1/(bm25_rank + 60)
```

设计考虑：
- `dense_weight=0.7` 优先语义匹配，`bm25_weight=0.3` 保证关键词精确匹配也能被检索到
- 权重可通过 `config.yaml` 的 `retrieval.dense_weight` / `retrieval.bm25_weight` 调整
- BM25 索引惰性加载（`_ensure_bm25()`），首次检索时才从 ChromaDB 拉取所有文档构建
- 使用 `jieba` 分词处理中文

### 7.3 RAG 工具的相关性评分与分级门控（`tools/rag.py`）

RAG 工具不依赖 LLM，而是通过确定性的多因子加权评分对每个检索结果评估相关性，并据此决定来源状态。

**四因子加权评分**（`_score_docs()`）：

| 因子 | 权重 | 计算方式 | 设计意图 |
|------|------|---------|---------|
| `dense_hint` | 0.35 | 从 ChromaDB metadata 提取已有分数（relevance_score/score/dense_score/bm25_score/rrf_score），归一化到 [0,1]；无分数时默认 0.5 | 利用向量检索的语义相关性信号 |
| `lexical_overlap` | 0.30 | 查询重要词项在文档中的命中比例（`overlap_score()`） | 保证关键词精确匹配 |
| `entity_match` | 0.20 | 查询技术实体（NIST/FIPS/ArcGIS/GIS/PQC 等）在文档中的命中比例 | 技术术语高信号加权 |
| `topic_match` | 0.15 | 查询词项/实体与文档来源文件名的主题重叠度 | 来源文件级相关性 |

额外加成：当 `entity > 0` 且 `lexical > 0` 时 +0.08，鼓励技术与关键词双重匹配的结果。

**三级阈值决策**：

| 分数区间 | 状态 | 置信度 | 含义 |
|---------|------|--------|------|
| `score ≥ 0.55` | `success` | 0.78 | 高置信证据，可参与共识投票 |
| `0.25 ≤ score < 0.55` | `low_relevance` | 0.50 | 弱相关上下文，只能作为低权重证据 |
| `score < 0.25` | `no_evidence` | — | 全部丢弃，不进入下游 |

**多子查询检索**（`_search_with_plan()`）：
- 通过 `plan_queries(query, target="rag")` 生成最多 4 个子查询
- 每个子查询独立执行混合检索
- 按 `chunk_id` 去重合并
- 确保不同角度的子查询能覆盖更广的知识面

**声明提取**（`_claim_from_chunk()`）：
- 对每个通过阈值的 chunk，按句号/换行切分
- 取首个 ≥ 12 字符的有效句子作为 `AgentClaim`
- claim 截断到 220 字符

**结构化元数据输出**：
每个 RAG 结果携带完整的 `score_breakdown`（四因子分值）、`citations`（chunk 级引用表），最终进入报告附录 C。

### 7.4 RAG 引用格式

RAG 结果中的每个 chunk 被格式化为 `[RAG:filename#chunk-pN-cM]`，在报告附录 C 中以表格形式完整列出：
```
| Ref | Source | Chunk | Parent | Char Range | Excerpt |
```

### 7.5 查询规划器（`query_planner.py`）

查询规划器是 RAG 和 Web 工具共享的确定性（零 LLM 调用）查询预处理模块，负责将用户原始问题转化为多角度子查询并提取信号词。

**核心数据结构**：

```python
@dataclass(frozen=True)
class QueryPlan:
    original_query: str       # 原始问题
    subqueries: list[str]     # 子查询列表（最多 4 个）
    entities: list[str]       # 识别到的技术实体
    terms: list[str]          # 提取的重要词项
```

**子查询生成策略**（`plan_queries()`）：
1. 原始查询直接作为第一个子查询
2. 将技术实体 + 概念扩展合并为第二个子查询（前 12 个词）
3. Web 目标时，为高优先级域名生成 `site:` 定向查询（如 `site:nist.gov PQC FIPS 203`）
4. RAG 目标时，生成纯词项查询作为补充
5. 去重、截断到 `max_subqueries`（默认 4）

**领域权威域名单**（`DOMAIN_PRIORITY`）：
```python
DOMAIN_PRIORITY = {
    "nist.gov": 1.0, "csrc.nist.gov": 1.0,
    "esri.com": 0.95, "developers.arcgis.com": 0.95,
    "opengeospatial.org": 0.9, "ogc.org": 0.9,
    "arxiv.org": 0.85, "doi.org": 0.8,
    "springer.com": 0.75, "ieee.org": 0.75, "acm.org": 0.75,
    "usgs.gov": 0.8, "openstreetmap.org": 0.8,
    ...
}
```
这个权重表同时用于：(1) Web 搜索的 `site:` 定向；(2) 搜索结果的相关性评分中的 `domain_authority` 因子。

**概念扩展**（`CONCEPT_EXPANSIONS`）：
```python
CONCEPT_EXPANSIONS = {
    "ArcGIS": ["ArcGIS", "Esri", "ArcGIS Enterprise", "ArcGIS Pro"],
    "后量子": ["post-quantum cryptography", "PQC", "NIST", "FIPS 203"],
    "知识图谱": ["knowledge graph", "semantic mapping", "GeoSPARQL", "ontology"],
    ...
}
```
当查询中包含触发词时，自动展开为相关概念词，提高检索召回率。触发词和扩展词的匹配不区分大小写。

**停用词过滤**（`STOPWORDS`）：
包含中英文通用停用词（"the"/"and"/"研究"/"说明"/"如何"等）以及领域通用词（"system"/"design"/"risk"/"工程"/"落地"），在词项提取（`important_terms()`）时过滤，避免这些高频低信号词稀释相关性评分。

**低质域名黑名单**（`LOW_QUALITY_DOMAINS`）：
```python
LOW_QUALITY_DOMAINS = {
    "instagram.com", "facebook.com", "x.com", "twitter.com",
    "pinterest.com", "slideshare.net", "scribd.com",
    "quora.com", "medium.com",
}
```
在 Web 检索的 `_filter_web_results()` 中，命中黑名单的域名 `domain_quality=0.0` 并额外施加 spam penalty（-0.55）。子域名（如 `www.medium.com`）也通过后缀匹配被覆盖。

**技术实体识别**（`extract_entities()`）：
从查询中提取高信号技术实体（如 "NIST"/"FIPS"/"ArcGIS"/"GeoSPARQL"/"PQC"/"ML-KEM" 等），用于 entity_match 评分和子查询生成。同时支持大写缩写模式匹配（如 `\b[A-Z][A-Z0-9+.\-]{1,}\b`）。

**辅助工具函数**：
- `overlap_score(terms, text)`：词项命中比例
- `entity_score(entities, text)`：技术实体命中比例
- `important_terms(text)`：中英文混合词项提取（支持 jieba 分词）
- `_priority_domains_for_query(query)`：根据查询主题自动选择定向域名

---

## 8. Web 检索与模型知识工具

### 8.1 Web 检索（`tools/web.py`）

支持双 provider：
- **DuckDuckGo**（默认，免费）：通过 `ddgs` 库调用，无 API key 要求
- **SerpAPI**（付费，需 `SERPAPI_API_KEY`）：通过 `aiohttp` 异步调用 Google Search API

Web 工具也使用 `plan_queries(query, target="web")` 进行查询规划，生成含 `site:` 定向的子查询。

**五因子相关性过滤**（`_filter_web_results()`）：

| 因子 | 权重 | 计算方式 | 设计意图 |
|------|------|---------|---------|
| `entity_match` | 0.35 | 技术实体命中比例 | 技术查询的高信号匹配 |
| `lexical_overlap` | 0.25 | 查询词项命中比例 | 关键词精确匹配 |
| `domain_authority` | 0.25 | 基于 `DOMAIN_PRIORITY` 表查分；gov/edu/org 默认 0.55；其他 0.35；黑名单 0.0 | 来源权威性加权 |
| `snippet_specificity` | 0.15 | 长度 ≥80(+0.25)、技术关键词(+0.25)、年份(+0.1)、标题含冒号/破折号(+0.1) | 片段信息密度 |
| `spam_penalty` | 减法 | 黑名单域名 -0.55；含 "login"/"sign up"/"instagram" 等 -0.25；snippet <30 字符 -0.15 | 低质/垃圾结果惩罚 |

**阈值决策**：
- `score ≥ 0.35` → 保留；`score ≥ 0.55` 且 ≥ 2 条 → `status=success`(confidence=0.72)
- 不满足 success 但 ≥ 0.35 → `status=low_relevance`(confidence=0.45)
- `score < 0.35` → 全部过滤
- 所有结果被过滤 → `status=no_evidence`

**多子查询检索**（`_search_with_plan()`）：
- 每个子查询独立执行搜索（per_query = max(2, max_results)）
- 按 URL 去重合并
- 总结果数达到 max_results × 2 时提前截断

**失败处理**：
- 库未安装 → status=failed
- 所有结果都标记为 failed → status=failed
- 部分失败结果被过滤，只保留有效结果
- 所有有效结果被质量过滤 → status=no_evidence

### 8.2 模型知识工具（`tools/model.py`）

通过全局变量注入 LLM 实例（`set_model()`），调用时标注 `[model knowledge / inference]`。

关键设计：
- `confidence=0.55`：模型知识的默认置信度低于 RAG(0.78) 和 Web(0.72)，体现了对模型幻觉的保守态度
- `evidence_refs=["[Model:world-knowledge]"]`：明确标识为模型推断而非检索证据
- `limitations=["model knowledge / inference; not external retrieved evidence"]`

---

## 9. FactCheck 事实核查

### 9.1 两阶段核查（`graph_v2.py:443-594`）

**阶段一：确定性检查**（`_deterministic_factcheck()`）—— 不消耗 LLM 调用

检查项：
1. **非证据来源滥用检测**：扫描报告文本，查找 `[RAG]`/`[Web]`/`[Model]` 引用，交叉对比 `source_statuses`，检测 `no_evidence`/`failed`/`fallback` 来源是否被当作事实证据引用。`low_relevance` 来源允许引用但需标注低置信。
2. **证据节点存在性**：检查 EvidenceGraph 中是否有来自 `success` 或 `low_relevance` 来源的节点。
3. **模型唯一来源容忍**：当证据图无节点、只有 Model 为 success、且报告中包含"模型推断"标记时，允许通过（`_model_only_allowed` 逻辑）。
4. **不确定性标注**：如果存在非证据来源或有效证据来源少于 2 个，检查报告是否包含"不确定"关键词。
5. **low_relevance 来源统计**：单独统计 `low_relevance` 来源数量，在 FactCheck 报告中显式列出。

**阶段二：LLM 核查**（`_llm_factcheck()`）—— 消耗 1 次 cheap 模型调用

输入：报告 + 确定性检查结果 + 证据图 JSON + 来源状态（含 low_relevance 标记）

输出：
- 已验证的声明（可追溯到 success/low_relevance 来源）
- 无法验证的声明
- 非证据来源是否被误用
- 需要修正的声明及正确版本
- 整体结论：passed / needs_review / partial

### 9.2 判定逻辑（`graph_v2.py:509-524`）

```python
deterministic_passed = not deterministic_findings["issues"]
if deterministic_passed and "验证通过" in fc_text and "无法验证" not in fc_text and "需修正" not in fc_text:
    status = "passed"
else:
    status = "needs_review"
    revised_report = _revise_report_after_factcheck(report, deterministic_findings)
```

两阶段都通过才标记为 `passed`，否则进入 `needs_review` 并自动修正。

### 9.3 自动修正（`_revise_report_after_factcheck()`）

对报告中出现的 no_evidence/failed/fallback 来源引用做确定性替换：
- `[RAG]` → `[RAG:excluded]`
- `来源：RAG` → `来源：RAG:excluded`
- `source:RAG` → `source:RAG:excluded`

修正后追加 `## Verification Revision Log` 说明。

---

## 10. 配置系统

### 10.1 三层优先级（`config.py`）

```
环境变量 CONFLUX_* > 本地 .env > config.yaml
```

环境变量覆盖使用双下划线路径语法：
```bash
CONFLUX_MODELS__REASONING__API_KEY=sk-xxx  → config["models"]["reasoning"]["api_key"]
CONFLUX_RETRIEVAL__DENSE_WEIGHT=0.8        → config["retrieval"]["dense_weight"]
```

### 10.2 加载流程

1. `_load_local_env()`：从项目根或当前目录加载 `.env` 文件（不覆盖已设置的环境变量）
2. `_load_raw()`：根据 `CONFLUX_CONFIG` 环境变量或默认路径查找 `config.yaml`
3. `_env_override()`：遍历所有 `CONFLUX_*` 环境变量，递归合并到配置字典
4. 结果缓存在模块级 `_config` 变量中（惰性加载，只加载一次）

### 10.3 配置结构（`config.yaml`）

| 模块 | 关键配置项 | 默认值 |
|------|-----------|--------|
| `models.reasoning` | provider, model, base_url, temperature | deepseek-v4-flash, 0.3 |
| `models.cheap` | 同上 | deepseek-v4-flash, 0.0 |
| `embedding` | provider, model | text-embedding-3-small |
| `web_search` | provider, max_results | duckduckgo, 5 |
| `vector_store` | provider, persist_dir | chromadb, ./data/chroma_db |
| `retrieval` | top_k, final_k, dense_weight, bm25_weight, parent_chunk_size, child_chunk_size | 10, 5, 0.7, 0.3, 1024, 256 |
| `agent` | max_iterations, confidence_threshold | 3, 0.7 |
| `research` | enable_l4, max_deep_questions, max_verify_iterations, max_rewrite_attempts | true, 2, 1, 1 |
| `slo` | survey_p95_ms | 45000 |
| `budget` | max_llm_calls, max_elapsed_ms | 20, 90000 |

---

## 11. 模型工厂 (Model Factory)

### 11.1 设计（`model_factory.py`）

使用 **策略模式** + **工厂函数**：所有 Provider 对上层透明，Agent 只依赖 `BaseChatModel` 接口。

支持的 Provider：

| Provider | 配置值 | 底层库 | 说明 |
|----------|--------|--------|------|
| OpenAI | `openai` | langchain-openai | 原生 OpenAI API |
| OpenAI Compatible | `openai_compatible` | langchain-openai | 自定义 base_url（如 DeepSeek API、代理） |
| Anthropic | `anthropic` | langchain-anthropic | Claude 系列 |
| Groq | `groq` | langchain-groq | Groq 推理 API |
| DeepSeek | `deepseek` | langchain-openai | 自动设置 base_url |
| Ollama | `ollama` | langchain-ollama | 本地模型（可选扩展） |

### 11.2 分级模型策略

```
reasoning preset → Agent Think 步骤（temperature=0.3, max_tokens=4096）
cheap preset     → 意图分类、仲裁、FactCheck、评估（temperature=0.0, max_tokens=1024）
```

这是成本优化策略的核心：复杂推理用 reasoning 模型，简单分类/仲裁用 cheap 模型。

### 11.3 凭证验证

`validate_runtime_credentials()` 在运行前检查所有必需的 API key 是否已配置，给出明确的缺失项列表。设计为 fail-fast —— 避免跑到一半才发现 API key 没配。

---

## 12. 成本追踪 (Cost Ledger)

### 12.1 数据模型（`cost.py`）

```python
@dataclass
class LLMCall:
    model: str          # 模型名
    stage: str          # 阶段（intent/rag_agent/web_agent/model_agent/arbitrate/synthesize/factcheck/reflexion）
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    timestamp: float

@dataclass
class CostLedger:
    calls: list[LLMCall]
    def record(model, stage, tokens_in, tokens_out, latency_ms)  # 记录单次调用
    def total_cost() -> float                                    # 总成本
    def total_tokens() -> tuple[int, int]                        # 总 token
    def breakdown_by_stage() -> dict[str, float]                  # 按阶段汇总
    def summary() -> dict                                        # 可打印摘要
```

### 12.2 定价表

内置了 Claude Sonnet 4、Claude Haiku 3.5、GPT-4o、GPT-4o-mini、DeepSeek V3/V4-flash 的定价（$/1M tokens），支持 `default` 回退定价。

### 12.3 成本优化策略

| 策略 | 实现状态 | 预估节省 |
|------|---------|---------|
| 分级模型 | 已实现：reasoning vs cheap 双 preset | ~30% |
| 提前终止 | 已实现：ReAct 达到 FINAL_MARKER 即停止 | ~25% |
| Prompt Caching | Phase 3 规划 | ~40% |
| 检索缓存 | Phase 3 规划 | ~20% |
| 结果缓存 | Phase 3 规划 | ~15% |

---

## 13. 断路器模式 (Circuit Breaker)

### 13.1 实现（`circuit_breaker.py`）

标准三态断路器：

```
CLOSED ──[连续失败 ≥ threshold]──▶ OPEN
  ▲                                  │
  │                                  ▼
  └────[成功]──── HALF_OPEN ◀──[冷却时间到]
```

关键参数：
- `failure_threshold=3`：连续失败 3 次后熔断
- `recovery_timeout=30s`：断路后冷却 30 秒

### 13.2 核心方法

```python
class CircuitBreaker:
    def call(self, fn, fallback_fn=None, *args, **kwargs):
        # OPEN 状态且未冷却 → 直接执行 fallback_fn
        # 否则执行 fn()，成功则重置，失败则累加计数
    async def acall(self, fn, fallback_fn=None, *args, **kwargs):
        # 异步版本，语义相同
```

全局注册表 `_breakers` 按服务名管理所有断路器实例。

### 13.3 应用场景

每个外部服务应有独立断路器：
- DuckDuckGo API → `get_breaker("duckduckgo")`
- SerpAPI → `get_breaker("serpapi")`
- ChromaDB → `get_breaker("chromadb")`
- 各 LLM Provider → 各自独立

当前断路器代码已完整实现，但尚未深度集成到工具调用中（工具层目前使用 try/except + SourceResult failed 状态做错误处理）。

---

## 14. 质量评分与验收门

### 14.1 质量评分（`quality.py`）

`evaluate_run_quality()` 在每次运行结束时自动执行（在 `deeper_research_node` 中触发），对 6 个维度评 1-5 分：

| 维度 | 评分标准 | 满分条件 |
|------|---------|---------|
| **运行过程** | 必需阶段是否全部执行，SLO 状态 | dispatch + merge + synthesize + factcheck 全部完成 |
| **报告质量** | 是否包含关键术语（最终结论/信息来源/不确定/证据/建议） | 5/5 术语命中 |
| **来源可靠性** | success 来源数量和 failed 来源数量 | ≥2 个 success 来源且无 failed |
| **FactCheck有效性** | 是否通过验证，是否包含追溯检查 | passed + "success 来源" 在验证文本中 |
| **证据图结构** | 是否有节点、来源状态、源分布统计 | nodes + source_counts + source_statuses 全部存在 |
| **L4深化质量** | 深化内容是否标注证据支持/模型推断 | "证据支持" + "模型推断" 或 "进一步检索" |

总体通过条件：`overall ≥ 4.0` AND `FactCheck有效性 ≥ 4` AND `证据图结构 ≥ 4`。

### 14.2 验收门（`acceptance.py`）

`validate_report_pair()` 对输出的 .md + .html 报告对做 13 项自动化验收检查：

1. Markdown 文件存在
2. HTML 文件存在且为完整 HTML 文档
3. 6 个必需小节全部存在（最终报告/信息来源状态/FactCheck/证据摘要/运行摘要/质量评分）
4. 最终报告包含 4 个关键术语（最终结论/信息来源/不确定/证据）
5. 来源状态覆盖 RAG/Web/Model
6. 来源状态值合法（success / low_relevance / no_evidence / failed / fallback）
7. 证据 JSON 可解析
8. 证据图包含三源状态
9. 证据图有有效声明节点
10. no_evidence/failed/fallback 来源没有被当作证据节点
11. RAG 为 evidence 状态时有 chunk 级引用（`[RAG:file#chunk-xxx]`）
12. FactCheck 有确定性追溯检查（含 success/low_relevance 来源摘要）
13. 质量评分有达标结论

验收结果以 JSON 格式输出（含 `passed`/`checks`/`issues`/`evidence_summary` 字段），可供 CI 消费。

---

## 15. Trace 结构化追踪

### 15.1 TraceEvent（`trace.py`）

```python
@dataclass
class TraceEvent:
    stage: str           # 阶段名（rag_agent/web_agent/model_agent/evidence_merge/arbitration/synthesize/factcheck/deep_research）
    status: str          # completed / failed / fallback
    elapsed_ms: float    # 距开始时间的毫秒数
    source: str | None   # 知识源（RAG/Web/Model/FactCheck）
    summary: str         # 输出摘要（前 180 字符）
    run_id: str          # 运行 ID
    thread_id: str       # 线程 ID（用于 checkpoint 关联）
    metadata: dict       # 扩展元数据（state_key, size）
    timestamp: float     # Unix 时间戳
```

### 15.2 事件生成

`event_from_state_key()` 在 Graph stream 过程中被调用：当检测到某个 state key 首次出现时（如 `rag_result` 非空），生成对应事件并自动推断状态（检查文本中是否包含 "failed"/"error"/"fallback" 关键词）。

### 15.3 输出产物

每次查询生成两个追踪文件：
- `{run_id}.trace.jsonl`：逐行 JSON，每行一个 TraceEvent
- `{run_id}.summary.json`：结构化运行摘要（耗时、阶段、SLO、来源状态、FactCheck 结论、质量评分）

---

## 16. 评估体系 (Evaluation)

### 16.1 LLM-as-Judge（`eval.py`）

使用独立 cheap 模型对系统回答做 5 维评分：

| 维度 | 评分标准 | 权重 |
|------|---------|------|
| **忠实度** (faithfulness) | 每个声明是否有检索证据支持 | 1-5 |
| **完整性** (completeness) | 是否回答用户问题的所有方面 | 1-5 |
| **权威性** (authority) | 引用来源的权威程度 | 1-5 |
| **平衡性** (balance) | 争议话题是否呈现多视角 | 1-5 |
| **诚实性** (honesty) | 是否明确标注不确定性和信息缺失 | 1-5 |

### 16.2 Golden Dataset

- 文件：`data/golden_dataset.yaml`
- 规模：30-50 条精心标注的问答对（Phase 1 目标）
- 标注内容：`id`、`query`、`expected_sources`（期望引用的权威源）
- 包含类型：事实查询 / 综述 / 对比 / 学术
- 包含特殊 case：故意模糊的问题（测试不确定性表态）、时间敏感问题（测试时效性处理）、争议话题（测试平衡性）

### 16.3 离线评估脚本

`scripts/` 目录下的评估脚本：

| 脚本 | 功能 | 指标 |
|------|------|------|
| `eval_retrieval.py` | 词法检索 baseline 评估（基于 Golden Dataset） | recall@k, hit rate, source coverage, irrelevant hit rate |
| `eval_reports.py` | 三种场景（source_failure/prompt_injection/disagreement）× 验收器 | acceptance pass rate, failed-source leakage, prompt-injection leakage |
| `eval_ablation.py` | 消融研究：4 配置（Single Agent / Multi no Arb / Multi + Arb / Full）× 4 场景 × FakeModel | 量化各组件（多 Agent 并行、仲裁器、FactCheck+L4）的边际贡献 |
| `eval_end_to_end.py` | 真实 API smoke test（需 `--real` 触发） | 端到端成功率 |

CI pipeline 中集成离线评估步骤。

---

## 17. Prompt 管理策略

### 17.1 版本化存储（`prompts/`）

```
prompts/
├── agents/
│   ├── rag_agent.system.yaml      # RAG Agent system prompt
│   ├── web_agent.system.yaml      # Web Agent system prompt
│   ├── model_agent.system.yaml    # Model Agent system prompt
│   └── factcheck_agent.system.yaml
├── evaluation/
│   └── judge.system.yaml          # LLM-as-Judge 评分 prompt
├── routing/
│   └── intent_classifier.yaml     # 意图分类 prompt
└── generation/
    └── report_composer.yaml       # 报告合成 prompt
```

每个 YAML 包含版本元数据：
```yaml
version: "1.0.0"
model: "reasoning"
temperature: 0.3
max_tokens: 2048
system: |
  你是 Conflux 的本地知识库检索 Agent...
metadata:
  author: "conflux"
  last_modified: "2026-06-28"
  change_log: "初始化 Phase 2 RAG Agent prompt"
```

### 17.2 加载机制（`prompts.py`）

- `load_prompt()`：加载 YAML 文件，返回完整 dict
- `load_system_prompt()`：加载 `system` 字段；文件缺失或字段为空时回退到硬编码的默认 prompt
- LRU 缓存：`@lru_cache(maxsize=32)` 避免重复读取磁盘

### 17.3 子 Agent Prompt（`agent.py:64-82`）

每个子 Agent 有两种 prompt 来源：
1. 优先从 `prompts/agents/{name}_agent.system.yaml` 加载
2. 文件不存在时使用硬编码默认 prompt（`SUB_AGENT_PROMPTS`）

---

## 18. 安全护栏设计

### 18.1 输入安全（架构设计阶段）

- Prompt Injection 检测：轻量分类器或关键词模式匹配检测越狱尝试
- 敏感话题识别：意图分类阶段同时检测自残、暴力、违法内容
- 输入长度限制：单次查询不超过 4096 tokens

### 18.2 高危领域处理

| 领域 | 触发条件 | 处置 |
|------|---------|------|
| 医疗 | 查询含诊断、治疗、用药 | 报告头部插入医疗免责声明 |
| 法律 | 查询含诉讼、合同、权利 | 报告头部插入法律免责声明 |
| 金融 | 查询含投资、理财、股票建议 | 报告头部插入金融免责声明 |
| 紧急事件 | 查询含正在发生的灾害、事故 | 提示通过官方渠道获取 |

### 18.3 输出安全（已实现）

**API Key 脱敏**（`report.py:_sanitize_report_text()`）：
```python
re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]", text)       # OpenAI key
re.sub(r"sk-proj-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]", text)   # OpenAI project key
re.sub(r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]", text)             # AWS key
re.sub(r"AIza[0-9A-Za-z_-]{35}", "[REDACTED_GOOGLE_KEY]", text)     # Google key
```

**Prompt Injection 脱敏**：
```python
re.sub(r"(?i)ignore previous instructions[^.\n]*", "[REDACTED_PROMPT_INJECTION]", text)
re.sub(r"(?i)web source confirmed this\s*:", "[REDACTED_PROMPT_INJECTION_CLAIM]:", text)
```
第二条规则防止模型在报告中嵌入虚假的"web source confirmed this:"式声明来伪装外部验证。

**声明追溯**：报告中每个事实声明必须能从 Evidence Graph 追溯到至少一个具体来源节点。

---

## 19. 降级方案与延迟 SLO

### 19.1 五层降级

| Level | 名称 | 触发条件 | 行为 |
|-------|------|---------|------|
| L0 | 全功能 | 正常 | 所有 Agent + 完整验证 |
| L1 | 降速保质量 | 成本敏感 | 减少循环轮次，关闭学术 API |
| L2 | 单源降级 | API 不可用 | 仅用 RAG + Model，跳过 Web |
| L3 | 极简模式 | 高并发/低成本 | 仅意图分类 + 单轮 RAG + 简单回答 |
| L4 | 纯模型 | 全部基础设施不可用 | 仅模型知识，标注无法检索外部信息 |

### 19.2 延迟 SLO

| 模式 | P50 | P95 | 超时策略 |
|------|-----|-----|---------|
| 简单事实查询 | < 3s | < 8s | 跳过 FactCheck，直接返回单源结果 |
| 综述调研 | < 15s | < 45s | 返回部分子问题结果 + 未完成标记 |
| 学术深度调研 | < 30s | < 90s | 流式输出中间结果 |

当前默认 SLO：`survey_p95_ms=45000`（45 秒），在 `_append_stage()` 中自动检查 `elapsed_ms <= p95_ms` 并标记 `slo_status: pass/breached`。

---

## 20. 报告生成

### 20.1 Markdown 报告结构（`report.py`）

```
# Conflux 调研报告
- 查询：xxx
- Generated at: 2026-06-30T12:00:00
- Run id: abc123def456
- Thread id: abc123def456

## 最终报告
[FactCheck 验证后的最终报告正文]

## 信息来源状态
| 来源 | 状态 | 详情 | 错误/说明 |
| RAG | success | Local Chroma hybrid retrieval | ... |
| Web | low_relevance | duckduckgo | weak web snippet evidence |
| Model | success | LLM world knowledge | ... |

Rule: `success` sources support factual evidence; `low_relevance` sources are weak contextual evidence; `no_evidence` / `failed` / `fallback` sources are excluded.

## FactCheck 验证
### 确定性追溯检查
- success 来源：RAG, Web
- low_relevance 来源：Model
- no_evidence/failed/fallback 来源：无
- 证据节点数：15
- 问题：未发现结构性追溯问题。

## 三源仲裁（如有）
[五级冲突协议输出]

## 证据摘要
- 证据节点总数：15
- Consensus/uncontested nodes: 12
- Contested nodes: 1
- ...

## 附录 A：证据图 JSON
```json
{...}
```

## Appendix C: RAG Chunk Citations（如有）
| Ref | Source | Chunk | Parent | Char Range | Excerpt |

## 运行摘要
- 模式：phase2
- 耗时：12345 ms
- SLO P95：45000 ms
- SLO 状态：pass

## 质量评分
- 总分：4.5 / 5
- 是否达标：是
- 运行过程：5 / 5
- ...

## 附录 B：原始三源输出
[三方 Agent 的原始输出文本]
```

### 20.2 HTML 生成（`report.py:92-161`）

使用 `markdown` 库将 Markdown 渲染为 HTML5，嵌入专业的 CSS 样式：
- 响应式设计（max-width: 980px，移动端适配）
- 清晰的排版层次（h1/h2/h3 间距，表格样式）
- 代码块样式（`fenced_code` 扩展）
- 引用块灰色边框

### 20.3 文件名生成

格式：`{YYYYMMDD-HHMMSS}-{slugified_query}.md/.html`

例如：`20260630-120000-how-should-rag-web-model-arbitration-work.md`

---

## 21. CLI 入口与开发流程

### 21.1 命令行接口（`__main__.py`）

```
# 索引文档
python -m conflux --index data/documents/

# Phase 2 查询
python -m conflux "How should RAG/Web/Model arbitration work?" --mode phase2 --stream-events

# 从 checkpoint 恢复
python -m conflux "question" --resume <thread-id> --checkpoint-backend memory

# 验收报告
python -m conflux.acceptance report.md report.html
```

### 21.2 查询流程（`query_command()`）

1. 加载配置 + 验证凭证
2. 创建 reasoning 和 cheap 两个模型
3. 创建 HybridRetriever → RAG Tool
4. 创建三个子 Agent（RAG/Web/Model）
5. 构建 Multi-Agent Graph（带 checkpointer）
6. `graph.stream(initial_state)` 逐步产出事件
7. 写报告产物（.md + .html + .trace.jsonl + .summary.json）

---

## 22. 测试策略

### 22.1 测试文件（5 个）

| 文件 | 测试内容 |
|------|---------|
| `test_agent.py` | 导入、配置加载、分块、Graph 编译、Golden Dataset 大小、Prompt 文件存在性、子 Agent prompt 加载、凭证缺失检查 |
| `test_phase2.py` | 多 Agent 全流程（FakeModel）、报告导出、BM25 检索排序、RAG 相关性分级（success vs low_relevance vs no_evidence）、证据图结构、非证据来源排除、final_answer 包含 FactCheck |
| `test_acceptance.py` | 验收通过/拒绝（完整报告 vs. 非证据源污染）、low_relevance 容忍 |
| `test_roadmap_features.py` | Checkpointer 后端、Trace JSONL 往返、RAG 引用格式、证据图 claim 驱动、离线 eval 脚本、Prompt injection/API key 脱敏 |
| `test_real_query_regressions.py` | 真实查询回归：中文复杂 GIS 查询保持 low_relevance/success 分类、垃圾 Web 结果 → no_evidence、短拒绝 → model-only fallback 报告替换 |

### 22.2 CI Pipeline（`.github/workflows/ci.yml`）

```
pytest → import check → secret scan → offline retrieval eval → offline report eval
```

### 22.3 FakeModel 策略

测试中使用 FakeModel（一个预编程响应的 mock LLM）避免真实 API 调用，使 CI 可以不依赖外部 API 运行。

---

## 23. 设计模式总结

| 模式 | 位置 | 说明 |
|------|------|------|
| **Fan-out/Fan-in** | `graph_v2.py:619-625` | LangGraph `Send()` API 并行派发三 Agent |
| **ReAct + Reflexion** | `agent.py` + `graph_v2.py:183-205` | Think→Act→Observe + Self-Critique→Refine |
| **Maker-Checker** | `graph_v2.py:443-534` | synthesize (Maker) → factcheck (Checker) |
| **Circuit Breaker** | `circuit_breaker.py` | 每个外部服务独立熔断 (closed/open/half_open) |
| **Strategy (Model Factory)** | `model_factory.py` | 多 provider 透明切换 |
| **TypedDict State** | `graph_v2.py:34-61` | LangGraph 状态类型安全（21 字段） |
| **Builder (Graph)** | `graph_v2.py:799-844` | `create_multi_agent_graph()` 组装节点和边 |
| **Decorator (Tool)** | `tools/*.py` | `@tool` 装饰器注册 LangChain 工具 |
| **Source Status Protocol** | `source_status.py` | 五态结构化来源状态负载（success/low_relevance/no_evidence/failed/fallback），嵌入工具输出 |
| **Evidence Graph** | `evidence.py` | 声明级证据网络，支持矛盾检测和不确定性传播 |
| **Five-Level Arbitration** | `graph_v2.py:321-439` | L0 一致性锚定 → L4 人工升级 |
| **Query Planner** | `query_planner.py` | 确定性查询规划（零 LLM 调用）：子查询扩展、概念扩展、权威域名定向、低质域名过滤 |
| **Deterministic Relevance Scoring** | `tools/rag.py` + `tools/web.py` | 4 因子（RAG）/ 5 因子（Web）确定性相关性评分，无需 LLM 即可分级门控 |
| **Prompt Versioning** | `prompts/` + `prompts.py` | YAML 文件 + 版本元数据 + LRU 缓存加载 |
| **Visitor (Streaming)** | `__main__.py:253-283` | `graph.stream()` + 事件分发到 TraceEvent |

---

## 24. 面试常见追问

### Q1：为什么选择 LangGraph 而不是自己写 Agent 循环？

**答**：LangGraph 提供了三个核心能力是手写循环难以实现的：(1) **Checkpoint** — 原生支持断点续跑，状态可序列化和恢复；(2) **Fan-out** — `Send()` API 让并行派发变得声明式，不需要手动管理线程池；(3) **可观测性** — 每个 Node 的输入输出自动被 LangSmith 追踪，适合调试和生产监控。此外，LangGraph 的图结构天然对应了我们的 Pipeline 设计（dispatch → fan-out → merge → synthesize → factcheck），代码和架构文档一一对应。

### Q2：EvidenceGraph 和 Neo4j 图的关系是什么？

**答**：这是两层不同职责的图。EvidenceGraph 是每次查询运行时在内存中构建的临时图，追踪本次查询的所有声明、来源和矛盾关系，查询结束后序列化到报告附录中。Neo4j 持久图（Phase 3 规划）是离线构建的文档级知识图谱，用于 Graph RAG 的结构化检索。两者不直接交互 —— EvidenceGraph 的数据来自工具层的 SourceResult，不需要 Neo4j。这个设计的目的是保持职责清晰：一个管"本次查询的证据追溯"，一个管"整个知识库的结构化索引"。

### Q3：如何处理三源信息冲突？

**答**：通过五级冲突升级协议。L0 是三源一致直接采纳；L1 是两源一致多数原则；L2 是权威加权投票（RAG=0.7, Web=0.5, Model=0.4）；L3 是对仍存争议的声明建议回溯原始 Agent 输出做交叉验证；L4 是标记 `[HUMAN_ESCALATION_NEEDED]` 等待人工裁决。核心安全规则是只有 `status ∈ {success, low_relevance}` 的来源才能参与共识投票（low_relevance 降权），no_evidence/failed/fallback 来源被排除。仲裁器 prompt 中明确要求区分"多源 success 真实共识"、"low_relevance 弱相关支持"、"单源声明"、"工具失败后的推断"和"互相冲突的声明"。

### Q4：如何防止模型幻觉污染报告？

**答**：多层防护：(1) Model Agent 的 `confidence=0.55`，低于 RAG(0.78) 和 Web(0.72)；(2) Model 的声明被标注为 `[Model:world-knowledge]`，与检索证据明确区分；(3) FactCheck 确定性检查会检测报告中是否将 no_evidence/failed/fallback 来源用作事实证据，low_relevance 来源允许但需标注低置信；(4) EvidenceGraph 构建时 `is_valid_evidence` 属性排除 no_evidence/failed/fallback 来源；(5) 报告 sanitization 脱敏 prompt injection 文本（包括 "web source confirmed this:" 伪装声明模式）；(6) 不确定性分解在报告中明确标注。

### Q5：Source Status Protocol 的设计动机？

**答**：在多 Agent 系统中，下游节点需要知道上游工具的执行结果是否可靠。如果 Agent 的 Web 搜索失败了但它仍然生成了内容，下游必须区分"这是基于成功搜索的结果"还是"这是 Agent 在没有工具结果时的推断"。在 ToolMessage 中嵌入机器可读的 JSON 标记，让下游可以无需 LLM 调用就能确定性地区分五种状态（success/low_relevance/no_evidence/failed/fallback），从而避免 no_evidence/failed/fallback 来源被当作事实证据参与投票。此外，`low_relevance`（弱相关证据）作为中间状态，允许系统在证据不足时仍保留部分上下文，但明确降权——这是一个工程权衡：完全丢弃弱相关结果可能丢失有用信息，但将其等同于 success 又是危险的。五态模型在"宁缺毋滥"和"信息最大化"之间找到了平衡点。

### Q6：为什么 RAG 的 dense_weight 设为 0.7 而不是 0.5？

**答**：因为 ChromaDB 使用的是 `text-embedding-3-small` 做语义向量检索，它能捕获同义词和语义相近的概念（如"机器学习"和"深度学习"）。BM25 是纯词法匹配，会漏掉这些。在大部分场景下，语义匹配比词法匹配更重要。但 BM25 对专有名词和精确术语的匹配是不可替代的（如"GPT-4"），所以保留 0.3 的权重作为补充。

### Q7：系统如何做性能优化？

**答**：(1) 三 Agent 并行 fan-out 而非串行，将三个 I/O 密集型任务并行化；(2) 分级模型策略（reasoning vs cheap），简单任务用便宜模型；(3) BM25 惰性加载，首次查询才构建索引；(4) ReAct 循环有硬上限（3 轮），防止无限循环；(5) budget 配置限定了最大 LLM 调用次数和最大耗时；(6) 断路器模式防止级联故障。

### Q8：如何保证报告的可信度？

**答**：从五个层面：(1) **可追溯性** — 每个声明都能从 EvidenceGraph 追溯到具体来源节点；(2) **FactCheck 验证** — 两阶段核查（确定性+LLM），确定性检查涵盖 non_evidence 来源滥用、证据节点存在性、low_relevance 来源统计、模型唯一来源容忍、不确定性标注；(3) **来源状态透明** — 报告中明确标注每个来源的五态（success/low_relevance/no_evidence/failed/fallback），并附 Rule 说明；(4) **不确定性分解** — 五维不确定性，不是单一分数；(5) **验收门** — 13 项自动化检查在 CI 中运行，确保每次变更不破坏质量标准。

### Q9：如果说服力不够，你会怎么改进？

**答**：(1) 引入 Authority API（如 NewsGuard/MBFC）对 Web 来源做权威性评分，而不是固定 0.5；(2) 集成 Semantic Scholar API 增加学术来源；(3) 实现 Graph RAG（Neo4j 持久图）做多跳推理；(4) 增加 A/B 测试框架对比不同 prompt 版本的效果；(5) 将 L5 Goal Loop（用户反馈闭环）集成到主 Graph 中，让用户反馈直接驱动再调研；(6) 扩展 Golden Dataset 到 150+ 条并增加更多边缘 case。

---

> **最后更新**: 2026-07-02  
> **项目状态**: Phase 2 多智能体 + Loop Engineering + 五态来源协议 + 确定性查询规划已实现；Phase 3 工程化成熟度进行中（CRAG 检索闭环、Neo4j Graph RAG、L5 Goal Loop 集成、Cross-encoder Reranker 等规划中）
