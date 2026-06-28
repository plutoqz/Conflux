# 三源知识多智能体调研系统 — 架构设计文档

> **项目定位**：结合本地知识库 (RAG) + 互联网权威信息检索 (Web) + 模型世界知识 (Model) 的多智能体调研系统，用于话题调研、问题解答、信息获取、知识体系搭建。
>
> **技术栈**：LangGraph + Multi-Agent + Loop Engineering + RAG
>
> **设计目标**：工程化成熟度展示 — 架构设计、证据网络、不确定性管理、评估体系、成本追踪、流程可视化、降级方案。

---

## 目录

1. [总体架构](#1-总体架构)
2. [三源知识仲裁系统](#2-三源知识仲裁系统)
3. [Loop Engineering 设计](#3-loop-engineering-设计)
4. [LangGraph 状态图设计](#4-langgraph-状态图设计)
5. [RAG Chunking 与 Retrieval 策略](#5-rag-chunking-与-retrieval-策略)
6. [互联网检索权威性保证](#6-互联网检索权威性保证)
7. [评估体系](#7-评估体系)
8. [成本追踪](#8-成本追踪)
9. [流程可视化](#9-流程可视化)
10. [降级方案与延迟 SLO](#10-降级方案)
11. [工程化成熟度清单](#11-工程化成熟度清单)
12. [安全护栏设计](#12-安全护栏设计)
13. [Prompt 管理策略](#13-prompt-管理策略)
14. [实施路线图](#14-实施路线图修订版)
15. [参考文献](#参考文献)

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
│  │          │ │          │ │           │ │Agent        │ │
│  └──────────┘ └──────────┘ └───────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────┤
│  第一层：Tool & Retrieval Layer（工具与检索层）             │
│  Milvus/Qdrant + BM25 + Semantic Scholar + SerpAPI       │
│  + NewsGuard/MBFC Authority API + Browser MCP            │
└──────────────────────────────────────────────────────────┘
```

### 1.2 三源知识分层模型

| 知识源 | 代号 | 优势 | 劣势 | 典型延迟 |
|--------|------|------|------|---------|
| 本地知识库 (RAG) | **L** | 可控、可审计、领域深度 | 范围有限、可能过时 | <1s |
| 互联网检索 (Web) | **W** | 实时、广度大 | 权威性参差、噪音多 | 3-8s |
| 模型世界知识 (Model) | **M** | 零延迟、推理整合强 | 幻觉风险、知识截止、无溯源 | <0.5s |

---

## 2. 三源知识仲裁系统

### 2.1 五级冲突升级协议

```
Level 0: 一致性锚定 (Anchor on Consensus)
├── L ∩ W ∩ M 一致 → 高置信度，直接采纳，标记 confidence=0.95+
├── L ∩ W 一致，M 不同 → 采纳 L+W，标注 M 为"模型知识可能过时"
├── L ∩ M 一致，W 不同 → 检查 W 源权威性，若权威性低则采纳 L+M
└── W ∩ M 一致，L 不同 → 检查 L 时效性，可能触发知识库更新

Level 1: 双向仲裁 (Bilateral Arbitration)
├── 仅一个源有信息 → 标注为 single-source，降低置信度
└── 两个源一致 vs 第三个源 → 多数原则，但标记少数源差异

Level 2: 权威性加权 (Authority-Weighted Vote)
├── 为每个源计算权威分: score = f(时效性, 可溯源性, 来源声誉, 内容一致性)
└── 加权融合: final = Σ(score_i × claim_i) / Σ(score_i)

Level 3: 溯源深挖 (Deep Provenance Tracing)
├── 对冲突声明，每个 Agent 必须提供证据链
├── FactCheck Agent 介入，交叉验证每个声明
└── 结果标注为 "contested"，呈现多视角

Level 4: 人工升级 (Human Escalation)
├── 不可自动裁决的冲突 → 生成结构化争议摘要
├── 推送给用户，附带推荐和每个选项的证据链
└── 记录人的决策作为反馈信号
```

### 2.2 证据网络（Evidence Graph）

每个检索到的声明不是孤立的——它们构成一个有向证据图：

```python
class EvidenceNode:
    id: str
    claim: str                     # 声明内容
    source: Literal["L", "W", "M"]
    source_detail: str             # 具体来源（文档ID/URL/模型参数版本）
    authority_score: float         # 来源权威分
    timestamp: datetime            # 信息时间戳
    supporting: List[str]          # 支持此声明的其他节点 ID
    contradicting: List[str]       # 与此声明矛盾的节点 ID
    derived_from: List[str]        # 推理链条上游节点
    uncertainty: float             # 此节点自身的不确定性
```

**关键：两层图的职责边界**

- **Neo4j 持久图**：离线构建的文档级知识图谱，存储实体、关系、社区摘要。用于 Graph RAG 的结构化检索（实体关系查询、多跳推理），在 §5.3 索引管线中离线构建。
- **Evidence Graph（临时图）**：每次查询时在内存中构建的证据依赖图（`Dict[str, EvidenceNode]`），追踪本次查询的所有声明、来源、支持/反驳关系。查询结束后可序列化存储（用于审计和用户反馈学习），但不存入 Neo4j。

**证据网络的核心价值**：

- **可追溯**：报告中每个结论都可以展开为证据链
- **去重**：多个源说同一件事 → 自动合并为更高权重的聚合节点
- **矛盾检测**：图中存在 A → 支持 → C 且 B → 反驳 → C 时自动标记为 contested
- **传播更新**：某个源被降权后，所有 `derived_from` 它的节点自动降置信度

### 2.3 不确定性分解

每个结论附带不确定性分解（不是单一分数）：

```python
Uncertainty = {
    "aleatoric": 0.1,        # 数据固有噪音（多个高质量源之间的小差异）
    "epistemic": 0.15,       # 知识不足（该主题缺少权威源覆盖）
    "source_quality": 0.05,  # 源质量导致的不确定性
    "temporal": 0.2,         # 时效性衰减（信息可能过时）
    "consensus_gap": 0.3,    # 源之间未达成共识
}
```

报告中呈现为：**"本结论置信度 78%。主要不确定性来自：信息可能已过时（最近更新 2023年6月），且不同权威源之间存在分歧。建议关注以下两个视角…"**

---

## 3. Loop Engineering 设计

### 3.1 五层嵌套循环

从外到内的五层嵌套循环架构：

```
L5: Goal Loop（目标循环）
    用户设定总目标 → Orchestrator 分解子问题 → 逐个解决 → 合成报告
    → 用户反馈 → 修正/深化 → 继续...
    止条件：用户确认满意 或 连续2轮无实质改进
    硬上限：3 轮（由 l5_goal_iterations 计数器控制）

L4: Research Loop（调研循环）
    针对单个子问题：搜索 → 阅读 → 提取声明 → 交叉验证 → 发现新子问题
    → 回到搜索...
    止条件：信息饱和 或 达到最大搜索深度
    ⚠ 信息饱和的操作性定义：
       本轮新提取的原子事实数量 < 上一轮的 20%
       AND 本轮新增独立来源数量 < 上一轮的 30%
    硬上限：3 轮（由 l4_research_depth 计数器控制）

L3: Agent Loop（Agent 内循环）
    标准 ReAct: Thought → Action → Observation → ...
    关键改造：加入 Reflexion 反思步骤
    Thought → Action → Observation → Self-Critique → Refine → ...
    止条件：Agent 自评完成 或 达到迭代上限
    硬上限：3 轮（由 l3_agent_iterations 计数器控制）

L2: Verification Loop（验证循环）
    Maker-Checker 模式：生成 Agent 产出 → 验证 Agent 独立审查
    → 通过 / 驳回 / 要求修正...
    止条件：验证通过 或 达到最大修正次数
    硬上限：2 轮（由 l2_verify_iterations 计数器控制）；2轮后不通过 → 标记为 uncertain

L1: Retrieval Loop（检索细粒度循环）
    初检 → 评估检索质量(CRAG评估器) → 若不足则改写Query → 再检索
    → 混合检索融合 → 重排序...
    止条件：检索质量达标 或 改写2次无改善 → 降级到 Web Search
    硬上限：2 轮（由 l1_retrieval_iterations 计数器控制）

⚠ 组合爆炸风险：最坏 3×3×3×2×2 = 108 次 LLM 调用，实际 L4/L3/L2 通常第 1-2 轮收敛，
  预期单次查询 < 25 次调用。Phase 1 只实现 L1+L2+L3，详见 §14 实施路线图。
```

### 3.2 Loop Engineering 核心理念

> Loop Engineering 是把你从「提示 Agent 的人」变成「设计提示 Agent 的系统」的工程师。
> —— Addy Osmani (Google), 2026

六要素框架：

| 要素 | 描述 | 本项目映射 |
|------|------|-----------|
| **自动触发器** | Loop 的心跳，定时/事件触发 | 用户问题提交 → 自动启动调研流程 |
| **并行隔离** | 每个 Agent 独立上下文 | LangGraph SubGraph 隔离状态空间 |
| **技能文件** | 项目约定外部化 | Agent system prompt + tool definitions |
| **连接器** | MCP 协议连接外部工具 | SerpAPI, Semantic Scholar, NewsGuard 等 |
| **子 Agent** | Maker-Checker 分离 | RAG/Web/Model Agent 负责产出，FactCheck Agent 负责验证 |
| **持久记忆** | 跨会话状态 | PostgresSaver checkpoint + 知识库持久化 |

### 3.3 L3 Agent Loop 实现关键

```python
def research_agent_node(state: AgentState) -> AgentState:
    """
    ReAct + Reflexion + Tool-Calling 的融合循环
    通过 LangGraph 的 conditional edge 实现，而非 while True
    """
    # Step 1: Think — 模型推理当前状态，决定行动
    thought = model.invoke(THINK_PROMPT.format(state))

    # Step 2: Act — 调用工具
    if thought.action == "search_rag":
        result = rag_tool.search(thought.query)
    elif thought.action == "search_web":
        result = web_tool.search(thought.query, authority_filter=True)
    elif thought.action == "verify_claim":
        result = factcheck_tool.verify(thought.claim, thought.sources)
    elif thought.action == "finalize":
        # Step 3: Self-Critique（Reflexion 的关键步骤）
        critique = model.invoke(CRITIQUE_PROMPT.format(
            original_answer=state.draft_answer,
            evidence=state.collected_evidence
        ))
        if critique.score >= state.confidence_threshold:
            return state  # 通过，继续下一阶段
        else:
            state.remaining_questions = critique.gaps
            return state

    state.add_observation(result)
    return state


def should_continue_agent_loop(state):
    """条件边：决定是继续循环还是进入验证"""
    if state.iteration >= state.max_iterations:
        return "verify"  # 强制进入验证
    if state.agent_self_assessment == "done":
        return "verify"
    return "continue"
```

### 3.4 使用 LangGraph 替代 While 循环的原因

| 特性 | while 循环 | LangGraph |
|------|-----------|-----------|
| **可观测性** | 需自行埋点 | 每个 Node 自动记录状态 |
| **可中断** | 复杂状态管理 | Checkpointer 原生支持断点续跑 |
| **可并行** | 手动管理 | `Send()` API 原生 fan-out |
| **可恢复** | 重新开始 | PostgresSaver 从任意节点恢复 |
| **流程可视** | 无 | LangSmith 自动追踪 |

---

## 4. LangGraph 状态图设计

### 4.1 顶层状态定义

```python
from typing import TypedDict, List, Dict, Literal

class ResearchState(TypedDict):
    # 输入
    query: str
    intent: Literal["factoid", "survey", "comparative", "howto", "academic"]

    # 中间产物
    sub_questions: List[str]
    rag_results: List[Document]
    web_results: List[WebSource]
    model_knowledge: str

    # 证据网络
    evidence_graph: Dict[str, EvidenceNode]
    uncertainty_map: Dict[str, float]

    # 控制 — 每层独立计数器（对应五层嵌套循环）
    l5_goal_iterations: int        # Goal Loop 轮次 (max 3)
    l4_research_depth: int         # Research Loop 搜索深度 (max 3)
    l3_agent_iterations: int       # Agent Loop 轮次 (max 3)
    l2_verify_iterations: int      # Verification Loop 轮次 (max 2)
    l1_retrieval_iterations: int   # Retrieval Loop 轮次 (max 2)
    confidence_threshold: float

    # 延迟追踪
    started_at: float              # 查询开始时间戳
    latency_slo: str               # 当前查询的延迟 SLO 等级

    # 输出
    final_report: str
    cost_ledger: CostLedger
```

### 4.2 顶层图结构

```
                        ┌─────────────┐
                        │  __start__   │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │ classify_intent│  ← LLM 分类：事实查询/综述/对比/学术
                        └──────┬───────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌────────┐ ┌──────────┐
              │decompose│ │direct  │ │clarify   │  ← 复杂问题分解 vs 直接回答 vs 追问
              │_query   │ │_answer │ │_question │
              └────┬────┘ └───┬────┘ └────┬─────┘
                   │          │          │
                   └──────────┼──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  parallel_dispatch   │  ← Send API 并行派发 (fan-out)
                   └──────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐  ┌──────────┐   ┌──────────┐
        │RAG Agent │  │Web Agent │   │Model     │
        │(subgraph)│  │(subgraph)│   │Knowledge │
        └─────┬────┘  └─────┬────┘   │Agent     │
              │             │         └─────┬────┘
              └─────────────┼───────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  evidence_merge     │  ← 合并 + 冲突检测
                  └─────────┬──────────┘
                            │
                  ┌─────────▼──────────┐
                  │ conflict_router     │  ← 条件路由
                  │ (有冲突？)           │
                  └────┬──────────┬────┘
                       │ 无冲突    │ 有冲突
                       ▼           ▼
              ┌────────────┐ ┌──────────────┐
              │compose     │ │factcheck_agent│ ← 事实核查子图
              │_report     │ │(subgraph)     │
              └─────┬──────┘ └──────┬───────┘
                    │               │
                    └───────┬───────┘
                            │
                  ┌─────────▼──────────┐
                  │ quality_gate        │  ← LLM-as-Judge 评估
                  │ (置信度达标？)       │
                  └────┬──────────┬────┘
                       │ 达标      │ 不达标
                       ▼           ▼
              ┌────────────┐ ┌──────────────┐
              │present_to   │ │deeper_research│ ← 回到 L4 Research Loop
              │_user        │ │(conditional)  │
              └─────────────┘ └──────────────┘
```

**[fan-out 状态合并说明]** LangGraph 的 `Send()` API 将三个 Agent 并行派发到各自的 SubGraph。每个 Agent 写入 state 的不同字段（`rag_results`, `web_results`, `model_knowledge`），LangGraph 自动将这些字段浅合并回主状态。`evidence_merge` 节点读取这三个字段，构建统一的 Evidence Graph。

若 LangGraph 版本支持 `Command` API，可显式管理 fan-in 和 reducer 逻辑；否则依赖默认的浅合并行为（各 Agent 写入互不重叠的 key 即可保证正确性）。

### 4.3 Agent 子图（SubGraph）标准模板

每个 Agent（RAG / Web / Model / FactCheck）共享相同的内循环结构：

```
__start__ → prepare_tools → [think → act → observe → critique] → finalize → __end__
                              ↑                                  │
                              └──────── 循环（conditional） ─────┘
```

子图的 `finalize` 输出是**结构化证据包**而非最终答案：

```python
class AgentEvidencePacket:
    agent_type: str
    claims: List[EvidenceNode]
    search_trail: List[SearchStep]    # 完整的搜索轨迹
    self_assessment: SelfAssessment   # Agent 自评
    cost: float                       # 本次执行花费
```

### 4.4 状态设计工程考量

| 考量 | 策略 |
|------|------|
| **状态不可变** | 每个 Node 返回新状态字典，LangGraph 自动浅合并 |
| **大对象引用** | 文档 embedding 等大对象存 Redis，State 中仅存 key |
| **状态压缩** | Agent 循环超过 N 轮时，自动摘要中间状态，避免上下文膨胀 |
| **调试状态** | `_debug` 前缀字段存所有中间量，用于可视化但不影响主逻辑 |

### 4.5 LLM 选型策略

不同节点对模型能力、延迟、成本的要求不同，采用分级选型：

| 节点 | 推荐模型 | 备选模型 | 原因 |
|------|---------|---------|------|
| **意图分类** | GPT-4o-mini / Claude Haiku | Qwen-2.5-7B (本地) | 低成本、低延迟、分类任务简单 |
| **问题分解** | Claude Sonnet / GPT-4o | DeepSeek-V3 | 需要结构化拆解能力 |
| **Agent 推理 (Think)** | Claude Sonnet / GPT-4o | Qwen-3-235B | 需要强推理 + 工具调用 (function calling) |
| **报告合成** | Claude Sonnet / GPT-4o | DeepSeek-V3 | 长文本生成质量要求高 |
| **FactCheck Agent** | Claude Sonnet | GPT-4o | 需要精细对比分析和低幻觉率 |
| **评估 (LLM-as-Judge)** | GPT-4o | Claude Sonnet | 评分一致性要求高；GPT-4o 在 LLM-as-Judge 基准上表现略优 |
| **Reflexion 反思** | 同 Agent 推理模型 | — | 复用同一模型，避免额外上下文切换成本 |
| **上下文前缀生成** | Claude Haiku / GPT-4o-mini | Qwen-2.5-7B (本地) | 离线批处理、成本敏感、任务简单 |

**选型原则**：
- **简单任务用小模型**：分类、摘要、格式转换用 Haiku/4o-mini，成本降至 1/10–1/20
- **推理任务用强模型**：Agent Think 步骤和 FactCheck 对比分析需要 Sonnet/4o 级别
- **评估用独立模型**：LLM-as-Judge 不与被评估的生成 Agent 用同一模型，减少自我偏好偏差
- **API Provider 备选**：Phase 3 优先引入多个远程 API provider（OpenAI 兼容接口、OpenAI、Anthropic、Groq 等）作为可用性兜底；本地模型仅作为可选扩展，不是默认运行要求。

---

## 5. RAG Chunking 与 Retrieval 策略

### 5.1 分层分块策略

不采用单一 chunk size，而是**多粒度分块 + 自动合并**：

```
L0: 文档级（完整文档，用于 overview）
    存储在 DocStore，按文档元数据索引

L1: 父块（Parent Chunk, 1024 tokens）
    使用 Anthropic Contextual Retrieval:
    每个块嵌入前，用 LLM 生成 50-100 tokens 的上下文前缀
    例："这是关于《劳动法》第39条的解释，属于'劳动合同解除'章节，
         前面讨论了协商解除，后面讨论了经济补偿..."

L2: 子块（Child Chunk, 256 tokens）
    用于精确检索，检索到足够多子块时自动合并为父块

L3: 句子级（Sentence-level, 用于 Late Chunking）
    使用 Jina embeddings v3 的长上下文能力，
    先对整个文档做 token-level embedding，再按语义边界切分
```

> **Phase 规划**：Phase 1 只做 L1（父块 + Contextual Retrieval）+ L2（子块，自动合并到父块）。这是 Anthropic 验证过的方案——Contextual Retrieval 可将检索失败率降低 49%，工程成本可控。L3（Late Chunking）需要 Jina embeddings v3 或类似长上下文嵌入模型，Phase 2 按需引入。L0 文档级检索通过元数据过滤实现，不建独立索引层。

### 5.2 混合检索管线

```
Query 进入
  │
  ├──→ 查询改写（LLM 生成 3 个变体）
  │      ├── 原始查询
  │      ├── 关键词提取版（用于 BM25）
  │      └── 抽象语义版（用于 Dense）
  │
  ├──→ 并行检索
  │      ├── Dense (向量相似度, top-100)
  │      ├── Sparse (BM25, top-100)
  │      └── 元数据过滤 (自查询检索器 Self-Query Retriever)
  │
  ├──→ 融合 (RRF 倒数排名融合)
  │
  ├──→ CRAG 评估器（检索质量评估）
  │      ├── 高置信 → 直接使用
  │      ├── 中置信 → 分解-重组（提取关键信息，过滤噪音）
  │      └── 低置信 → 触发 Web Search 降级
  │
  ├──→ 重排序（Cohere Rerank v3 或本地 cross-encoder）
  │      从 top-100 → top-10
  │
  └──→ 上下文组装
         ┌─ 父块全文（通过子块自动合并找回）
         ├─ 上下文前缀（Anthropic 风格）
         └─ 源元数据（文档名、章节、更新时间、权威评分）
```

### 5.3 离线索引管线

```
原始文档
  │
  ├──→ 文档解析（Unstructured.io / LlamaParse）
  │      ├── PDF → Markdown
  │      ├── 保留表格、图片引用
  │      └── 章节结构提取
  │
  ├──→ 质量预筛
  │      ├── 重复/近似重复检测
  │      ├── AI生成内容检测
  │      └── 权威性预标注（.gov/.edu/已知权威源）
  │
  ├──→ 多粒度分块
  │      ├── L0: 完整文档 → 文档存储
  │      ├── L1: 父块(1024t) + 上下文前缀生成
  │      ├── L2: 子块(256t)
  │      └── L3: 句子级 (Late Chunking)
  │
  ├──→ 向量化 + 索引
  │      ├── Milvus 存 Dense 向量
  │      ├── Elasticsearch 存 Sparse 索引 + 元数据
  │      └── Neo4j 存知识图谱（用于 Graph RAG）
  │
  └──→ 更新策略
         ├── 增量更新（新增/修改文档）
         ├── 定期重索引（每周全量）
         └── 过期检测（超过 N 个月未更新的文档降权）
```

---

## 6. 互联网检索权威性保证

### 6.1 多层级权威评分体系

| 层级 | 信号 | 更新频率 | 用途 |
|------|------|---------|------|
| **Tier 0: 黑名单** | Iffy Index, CRED-1, Wikipedia Deprecated Sources | 周更 | 直接过滤 |
| **Tier 1: 预计算评分** | Domain Age, TLD, Moz DA, MBFC/NewsGuard Rating, Traffic Rank, Spam Score | 周更 | 预权重 |
| **Tier 2: 查询时评估** | SSL 有效性, About/Contact 页面, 作者资质, 发布时间, 语义匹配度 | 实时 | 动态调整 |
| **Tier 3: 学术专用** | Semantic Scholar 引用数, Peer Review 状态, 作者 h-index, 撤稿检测 | 条件触发 | 学术加权 |
| **Tier 4: 交叉验证** | 多源交叉验证, FactCheck Agent 定向核查, Wikipedia 引用回溯 | Agent 驱动 | 最终置信度 |

### 6.2 学术权威检索专用通道

对于学术类查询，不走通用搜索引擎，直接接入：

- **Semantic Scholar API**（2.14 亿论文，自带引用图）
- **PubMed E-Utilities**（生物医学，带 MeSH 标签和 RCT/Systematic Review 标记）
- **arXiv API**（预印本，跟踪后续是否被同行评审期刊接收）

学术源权威分计算：

```
authority = 0.3 × normalize(citation_count)
          + 0.2 × peer_review_status (1.0 if published in MEDLINE/Scopus journal)
          + 0.2 × author_h_index_norm
          + 0.15 × venue_prestige
          + 0.1 × recency_factor
          - 0.05 × retraction_flag
```

### 6.3 低质量源检测

| 检测维度 | 信号 | 来源 |
|---------|------|------|
| 内容农场 | 高广告比、工厂式发布模式、薄内容 | 自研爬虫分析 |
| SEO 垃圾 | Moz Spam Score ≥ 60% | Moz API |
| AI 生成内容 | 无人类署名 + 无编辑流程披露 + AI检测器标记 | GPTZero API + MBFC AI 政策 |
| 已知不可靠 | CRED-1 黑名单 / Iffy Index / Wikipedia Deprecated | 离线数据库 |
| 恶意/钓鱼 | Google Safe Browsing 标记 | Google API |

### 6.4 权威检索流水线

```python
async def authoritative_web_search(query: str, intent: str) -> List[RankedSource]:
    # Step 1: 多引擎检索
    raw_results = await asyncio.gather(
        serpapi.search(query),                       # Google
        semantic_scholar.search(query) if intent == "academic" else None,
        brave.search(query),                          # Brave Search (独立索引)
    )

    # Step 2: 去重 + 合并
    merged = deduplicate_and_merge(raw_results)

    # Step 3: 黑名单过滤
    filtered = [r for r in merged if r.domain not in BLACKLIST]

    # Step 4: 权威评分（分层触发，控制延迟）
    # Tier 1 预计算分数已在缓存中，零延迟
    # Tier 2 实时检查仅对 top-20（重排序后）执行
    # Tier 3 学术信号仅对 intent == "academic" 的查询触发
    top_for_scoring = filtered[:20]  # 仅对 top-20 做深度评估
    for r in top_for_scoring:
        r.authority = compute_authority(
            precomputed=authority_cache.get(r.domain),      # Tier 1: 缓存命中，零延迟
            realtime=await realtime_signals(r.url),          # Tier 2: 实时，仅 top-20
            academic=await academic_signals(r) if is_academic(r) and intent == "academic" else None,  # Tier 3: 仅学术查询
        )
    # 剩余结果仅用 Tier 1 预计算分数
    for r in filtered[20:]:
        r.authority = authority_cache.get(r.domain, 0.5)

    # Step 5: 按权威分排序 + diversity bonus（避免全是同一视角）
    ranked = rank_with_diversity(filtered)

    return ranked[:N]
```

### 6.5 权威数据源整合

| 数据源 | 类型 | 覆盖范围 | 接入方式 |
|--------|------|---------|---------|
| **CRED-1** | 开源域名可信度数据集 | 2,672 域名 | npm/MCP Server |
| **Iffy.news** | 不可靠源开放数据 | 1,300+ 域名 | JSON/CSV 下载 |
| **NewsGuard** | 人类审核新闻评级 | 10,000+ 新闻网站 | 商业 API |
| **Media Bias/Fact Check** | 媒体偏见与事实可靠性 | 10,000+ 媒体源 | API |
| **Wikipedia RSP** | 社群维护的源可靠性列表 | 数百个常用源 | 数据抓取 |
| **Moz Domain Authority** | SEO 权威预测分 | 10 亿+ 域名 | API ($20/月起) |
| **Semantic Scholar** | 学术引用图 | 2.14 亿论文 | 免费 API |
| **Google Safe Browsing** | 恶意/钓鱼域名 | — | 免费 API |

---

## 7. 评估体系

### 7.1 四层评估矩阵

| 层次 | 评估对象 | 指标 | 工具 | 频率 |
|------|---------|------|------|------|
| **检索** | RAG 检索质量 | Context Precision/Recall, NDCG | RAGAS + DeepEval | 每次查询 |
| **生成** | 答案质量 | Faithfulness, Answer Relevance, Completeness | RAGAS + LLM-as-Judge | 每次查询 |
| **系统** | Agent 行为 | Task Completion, Tool Correctness, Step Efficiency | DeepEval + 自研 | 每次会话 |
| **业务** | 用户价值 | 用户采纳率、反馈评分、修正率 | 用户反馈收集 | 每周汇总 |

### 7.2 LLM-as-Judge 评估 Prompt

```python
JUDGE_PROMPT = """你是一个严格的评估者。根据以下标准评分：

1. 忠实度 (1-5)：回答中的每个声明是否有检索到的证据支持？
2. 完整性 (1-5)：是否回答了用户问题的所有方面？
3. 权威性 (1-5)：引用的来源是否具有高权威性？
4. 平衡性 (1-5)：对于有争议的话题，是否呈现了多视角？
5. 诚实性 (1-5)：是否明确标注了不确定性和信息缺失？

对以下回答评分，给出每个维度的分数和改进建议。

用户问题：{query}
系统回答：{answer}
证据链：{evidence_chain}
"""
```

### 7.3 离线评估基准（Golden Dataset）

分阶段建设：

- **Phase 1 目标**：30-50 条精心标注的问答对
- **Phase 3 目标**：扩展至 150-200 条
- 每个答案标注 `expected_sources`（期望引用的权威源）
- 包含 deliberately ambiguous questions（测试不确定性表态）
- 包含 time-sensitive questions（测试时效性处理）
- 包含 controversial topics（测试平衡性）
- 数据来源：手工构造 + 从用户反馈中筛选高质量 case

---

## 8. 成本追踪

### 8.1 成本账本模型

```python
class CostLedger:
    """全链路成本追踪"""
    # LLM 调用成本
    llm_calls: List[LLMCall]  # {model, tokens_in, tokens_out, cost, purpose}

    # 检索成本
    retrieval_costs: List[RetrievalCost]  # {source, query, cost}

    # 嵌入成本
    embedding_costs: float  # tokens × embedding_price

    # 外部 API 成本
    api_costs: Dict[str, float]  # {api_name: total_cost}

    def per_query_summary(self) -> CostSummary:
        return CostSummary(
            total=self.total,
            breakdown_by_stage={
                "intent_classification": ...,
                "rag_retrieval": ...,
                "web_search": ...,
                "agent_loops": ...,
                "fact_check": ...,
                "report_generation": ...,
            },
            tokens_total=self.total_tokens,
            cache_hit_rate=self.cache_hit_rate,
        )
```

### 8.2 成本优化策略

| 策略 | 描述 | 预估节省 |
|------|------|---------|
| **Prompt Caching** | Anthropic prompt cache 将重复 system prompt 成本降低 90% | ~40% |
| **分级模型** | 简单分类用 GPT-4o-mini / Claude Haiku，复杂推理用大模型 | ~30% |
| **检索缓存** | 相同 query 的检索结果缓存 1 小时 | ~20% |
| **提前终止** | 早期检索达到高置信度时不启动深度 Agent 循环 | ~25% |
| **结果缓存** | 相同/相似问题（余弦相似度 > 0.95）直接返回缓存结果 | ~15% |

---

## 9. 流程可视化

### 9.1 三层可视化架构

```
┌─────────────────────────────────────────────────────────────┐
│  用户侧 (Streamlit/Gradio UI)                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  查询: "量子计算对密码学的威胁是什么？"                    │ │
│  │                                                         │ │
│  │  ⏳ 正在调研...                                          │ │
│  │  ├── ✅ 意图识别: academic (0.3s, $0.0002)               │ │
│  │  ├── ✅ 问题分解: 3个子问题 (0.8s, $0.001)                │ │
│  │  ├── 🔄 RAG检索中...                                    │ │
│  │  ├── 🔄 Web检索中...                                    │ │
│  │  └── ⏳ 证据合并中...                                    │ │
│  │                                                         │ │
│  │  进度: ████████░░ 67%                                    │ │
│  │  预估成本: $0.023 (已用 $0.015)                          │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  开发者侧 (LangSmith Dashboard)                              │
│  - 完整的状态图执行路径                                       │
│  - 每个 Node 的输入/输出快照                                  │
│  - Token 消耗瀑布图                                          │
│  - Agent 决策轨迹回放                                        │
├─────────────────────────────────────────────────────────────┤
│  架构师侧 (自研 Evidence Graph Viewer)                       │
│  - 交互式证据网络图                                           │
│  - 节点点击展开证据详情                                       │
│  - 矛盾节点红色高亮                                           │
│  - 不确定性热力图覆盖                                         │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 关键可视化元素

- **执行甘特图**：展示每个 Agent 的并行/串行执行时间
- **置信度雷达图**：每个结论的五维不确定性分解
- **证据桑基图**：从原始溯源到最终结论的信息流
- **成本瀑布图**：按阶段分解的成本构成

---

## 10. 降级方案

### 10.1 五层降级策略

```
Level 0: 全功能
  所有 Agent 可用，完整权威性检查，最高质量

Level 1: 降速保质量（成本敏感）
  减少 Agent 循环轮次，降低 max_iterations，关闭学术 API

Level 2: 单源降级（API 不可用）
  Web Search API 限流 → 仅用 RAG + Model Knowledge
  Semantic Scholar 不可用 → 降级为 Google Scholar scraping

Level 3: 极简模式（高并发/低成本）
  仅意图分类 + 单轮 RAG + 简单 LLM 回答，跳过所有 Agent 循环

Level 4: 纯模型降级（全部基础设施不可用）
  仅靠模型自身知识回答，明确标注"当前无法检索外部信息，
  以下回答仅基于模型训练数据，请独立验证"
```

### 10.2 断路器模式

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout  # 断路器打开后的冷却时间

    async def call(self, service_name: str, fn, fallback_fn):
        if self.is_open(service_name):
            return await fallback_fn()
        try:
            result = await asyncio.wait_for(fn(), timeout=30)
            self.reset(service_name)
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.open(service_name)
            return await fallback_fn()
```

### 10.3 重试策略

- 指数退避 (exponential backoff)：1s → 2s → 4s → 8s → max 30s
- 每个服务独立断路器
- 全局 30s 超时强制返回部分结果

### 10.4 延迟 SLO（Service Level Objective）

不同交互模式有不同的延迟容忍度，SLO 直接驱动降级触发：

| 交互模式 | P50 延迟目标 | P95 延迟目标 | 超时降级策略 |
|---------|------------|------------|------------|
| **简单事实查询** | < 3s | < 8s | 超时跳过 FactCheck，直接返回单源结果 |
| **综述调研** | < 15s | < 45s | 超时返回部分子问题结果 + 未完成标记 |
| **学术深度调研** | < 30s | < 90s | 流式输出中间结果，边调研边展示 |

延迟监控指标：

- `time_to_first_token`：用户看到首个输出的时间（流式场景）
- `time_to_complete`：完整报告生成时间
- `time_by_stage`：按节点分解的耗时分布（用于定位瓶颈）

降级触发条件：

- 若当前延迟超过 P95 目标的 80%，启动下一级降级（如跳过深度验证）
- 若超过 P95 目标的 120%，强制返回已有结果并标注 incomplete

---

## 11. 工程化成熟度清单

| 维度 | 具体实践 |
|------|---------|
| **可观测性** | LangSmith 全链路追踪 + 自研 Evidence Graph Dashboard + Prometheus 指标 |
| **容错性** | 五层降级 + 断路器 + 重试策略(指数退避) + 超时控制 + 延迟 SLO 驱动降级 |
| **成本控制** | 分级模型选路 + Prompt Cache + 结果缓存 + 提前终止 |
| **评估闭环** | RAGAS/DeepEval 在线评估 → LLM-as-Judge → 离线 Golden Dataset → CI 回归 |
| **数据飞轮** | 用户反馈 → 知识库更新 → 权威源白名单维护 → 低质源黑名单更新 |
| **安全护栏** | 详见 §12 安全护栏设计 |
| **Prompt 管理** | 详见 §13 Prompt 管理策略 |
| **延迟 SLO** | 详见 §10.4 延迟 SLO |
| **LLM 选型** | 详见 §4.5 LLM 选型策略 |
| **多模态扩展** | 架构预留：图片 OCR → 表格提取 → 图表数据提取 |
| **MCP 集成** | 通过 Model Context Protocol 标准化工具接口，方便扩展新数据源 |
| **CI/CD** | 评估指标回归检测 + Golden Dataset 自动测试 + 成本异常告警 |

---

## 12. 安全护栏设计

### 12.1 输入安全

- **Prompt Injection 检测**：用轻量分类器（GPT-4o-mini 或关键词模式匹配）检测越狱尝试和注入攻击
- **敏感话题识别**：意图分类阶段同时检测是否涉及自残、暴力、违法等内容
- **输入长度限制**：单次查询不超过 4096 tokens，防止资源耗尽

### 12.2 高危领域处理

| 领域 | 触发条件 | 处置 |
|------|---------|------|
| **医疗** | 查询含诊断、治疗、用药等关键词 | 报告头部插入免责声明：「⚠ 以下内容仅供参考，不构成医疗建议。请咨询执业医师。」 |
| **法律** | 查询含诉讼、合同、权利等关键词 | 报告头部插入免责声明：「⚠ 以下内容仅供参考，不构成法律意见。请咨询执业律师。」 |
| **金融** | 查询含投资、理财、股票建议等关键词 | 报告头部插入免责声明：「⚠ 以下内容仅供参考，不构成投资建议。投资有风险。」 |
| **紧急事件** | 查询含正在发生的灾害、事故等 | 提示用户通过官方渠道获取最新信息 |

### 12.3 输出安全

- **声明追溯**：报告中每个事实声明必须能从 Evidence Graph 追溯到至少一个具体来源节点
- **无法追溯的声明**：自动标记为「模型推断」，并附加不确定性说明
- **争议话题**：强制呈现至少两个视角，标注各方证据强度
- **敏感信息过滤**：输出侧检测并脱敏身份证号、手机号、地址等 PII

---

## 13. Prompt 管理策略

### 13.1 版本化存储

```
prompts/
├── agents/
│   ├── rag_agent.system.yaml       # RAG Agent 的 system prompt
│   ├── web_agent.system.yaml       # Web Agent 的 system prompt
│   └── factcheck_agent.system.yaml # FactCheck Agent 的 system prompt
├── evaluation/
│   └── judge.system.yaml           # LLM-as-Judge 评分 prompt
├── routing/
│   └── intent_classifier.yaml      # 意图分类 prompt
└── generation/
    └── report_composer.yaml        # 报告合成 prompt
```

每个 YAML 文件包含版本元数据：

```yaml
version: "1.2.0"
model: claude-sonnet-4-20250514
temperature: 0.3
max_tokens: 4096
system: |
  你是一个专注于本地知识库检索的研究 Agent...
metadata:
  author: "xxx"
  last_modified: "2026-06-28"
  change_log: "优化了检索结果的引用格式"
```

### 13.2 A/B 测试框架

- 关键 prompt（如 FactCheck system prompt、评估 judge prompt）支持多版本并存
- 每次查询随机分配版本，记录版本号到 trace
- 通过 LangSmith 对比不同版本的评估指标（忠实度、完整性）
- 统计显著后推广优胜版本

### 13.3 回归测试

- 每次 prompt 变更后，在 Golden Dataset 上跑完整评估
- 若任意指标下降 > 5%，阻止合并
- CI pipeline 中集成 `prompt-test` 步骤

---

## 14. 实施路线图（修订版）

### Phase 1: 核心闭环（MVP）

- 单 Agent（ReAct + RAG）+ 简单 Web Search + LLM 合成
- 基础仲裁逻辑（多数原则）
- LangGraph 单层图
- L1+L2+L3 循环（检索 + 验证 + Agent 内循环）
- 分块：仅 L1 父块 + L2 子块（Contextual Retrieval）
- Golden Dataset：30-50 条
- **目标**：跑通「问题 → 检索 → 回答」最短路径，单次查询 < 15s

### Phase 2: 多智能体 + Loop Engineering

- RAG Agent / Web Agent / Model Agent 三智能体并行
- FactCheck Agent 验证
- 证据网络 + 冲突升级协议
- Reflexion 自反思循环
- 权威评分体系
- L4 Research Loop 扩展
- 延迟 SLO 监控上线

### Phase 3: 工程化成熟

- 成本追踪 + 可视化 Dashboard
- 评估体系完善 + Golden Dataset 扩展至 150-200 条
- 降级方案 + 断路器
- 用户反馈闭环
- MCP 工具扩展
- 多 API Provider 备选上线（本地模型仅作为可选扩展）
- L5 Goal Loop（用户反馈驱动）
- 分块 L3 Late Chunking 按需引入

---

## 参考文献

- **ReAct**: Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR 2023
- **Reflexion**: Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning", NeurIPS 2023
- **Self-Refine**: Madaan et al., "Self-Refine: Iterative Refinement with Self-Feedback", NeurIPS 2023
- **CRITIC**: Gou et al., "CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing", ICLR 2024
- **ReWOO**: Xu et al., "ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models", 2023
- **LLMCompiler**: Kim et al., "An LLM Compiler for Parallel Function Calling", ICML 2024
- **CRAG**: Yan et al., "Corrective Retrieval Augmented Generation", arXiv 2401.15884
- **Self-RAG**: Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection", arXiv 2310.11511
- **Adaptive RAG**: Jeong et al., "Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models", NAACL 2024
- **Graph RAG**: Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization", arXiv 2404.16130
- **Anthropic Contextual Retrieval**: Anthropic Blog, Sep 2024
- **Jina Late Chunking**: Jina AI Blog, Aug 2024
- **Loop Engineering**: Addy Osmani, Jun 2026
- **CRED-1**: Loth et al., "An Open Multi-Signal Domain Credibility Dataset", ACM WebSci 2026
- **Authority Signals in AI Health Sources**: Jacques et al., arXiv 2601.17109

---

> **最后更新**: 2026-06-28
> **状态**: 架构设计阶段，待开发实施
