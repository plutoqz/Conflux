"""LangGraph 状态图 v2 — Phase 2 三 Agent 并行派发 (fan-out)

Graph 结构：
  __start__ → dispatch → [Send: rag | web | model] → evidence_merge → synthesize → __end__

每个子 Agent 是独立的 ReAct 循环（内嵌于 SubGraph），并行执行。
"""

import json
import re
import time
from typing import TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Send
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from .agent import ResearchAgent, FINAL_MARKER
from .config import get
from .evidence import EvidenceGraph, build_evidence_graph_from_results
from .source_status import (
    EXTERNAL_EVIDENCE_CLASSES,
    AgentClaim,
    SourceResult,
    fallback_result,
    parse_source_results,
    status_is_evidence,
    status_is_non_evidence,
    source_status_markdown,
    strip_source_markers,
)
from .quality import evaluate_run_quality
from .trace import new_run_id


# ── State ──────────────────────────────────────────────────

class MultiAgentState(TypedDict):
    query: str
    # 三个子 Agent 各自的输出
    rag_result: str
    web_result: str
    model_result: str
    # 内部合并结果
    _merged: str
    # 仲裁摘要
    _arbitration: str
    # 证据网络摘要（JSON 字符串）
    _evidence_json: str
    _source_statuses: dict
    # FactCheck 验证后的修正报告
    _verified_answer: str
    _factcheck_status: str
    _factcheck_report: str
    _factcheck_findings: dict
    _deep_research: str
    _deep_queries: list[str]
    _deep_arbitration: str
    _deep_factcheck_report: str
    _deep_evidence_json: str
    _deep_source_statuses: dict
    _run_summary: dict
    _quality_report: dict
    _pipeline_stage: str
    _run_id: str
    _thread_id: str
    _checkpoint_backend: str
    _resumed: bool
    _review_status: str
    # 合成阶段
    final_answer: str


# ── Sub-Agent Runner ───────────────────────────────────────

def _run_agent(query: str, agent: ResearchAgent, reflexion: bool = True) -> str:
    """在单次调用中运行一个子 Agent 的完整 ReAct 循环，返回其最终回答

    Args:
        query: 用户问题
        agent: ResearchAgent 实例
        reflexion: 是否启用 Reflexion 自反思（Phase 2）
    """
    messages = agent.build_messages(query)
    tool_payloads: list[str] = []

    direct_tool_result = _run_exclusive_tool(agent, query)
    if direct_tool_result is not None:
        tool_payloads.append(direct_tool_result)
        messages.append(HumanMessage(content=(
            "已执行该子 Agent 的专属工具。请只基于以下工具结果生成简洁结论；"
            "如果工具状态是 no_evidence/failed/fallback，必须明确说明不可作为真实来源；"
            "如果工具状态是 low_relevance，必须标注为弱相关证据。\n\n"
            f"{direct_tool_result}"
        )))
        final_msg = agent.call_model(messages, use_tools=False)
        answer = str(final_msg.content)
        if FINAL_MARKER in answer:
            answer = answer.split(FINAL_MARKER, 1)[1].strip()
        if reflexion:
            answer = _reflect_and_refine(query, answer, agent, messages + [final_msg])
        return f"{answer}\n\n{direct_tool_result}"

    for _ in range(agent.max_iterations):
        ai_msg = agent.call_model(messages)

        if ai_msg.tool_calls:
            tool_msgs = agent.execute_tools(ai_msg)
            tool_payloads.extend(str(msg.content) for msg in tool_msgs)
            messages.append(ai_msg)
            messages.extend(tool_msgs)
            continue

        # 没有 tool_calls → 可能是最终回答
        if agent.has_final_answer(ai_msg):
            content = ai_msg.content
            if isinstance(content, str):
                if FINAL_MARKER in content:
                    answer = content.split(FINAL_MARKER, 1)[1].strip()
                else:
                    answer = content

                if reflexion:
                    # Reflexion: 自我批判 → 修正
                    answer = _reflect_and_refine(query, answer, agent, messages)
                if tool_payloads:
                    return f"{answer}\n\n" + "\n\n".join(tool_payloads[-3:])
                return answer

        messages.append(ai_msg)

    # 超过 max_iterations，强制生成最终回答
    messages.append(HumanMessage(content="请基于以上结果，给出简洁的最终回答。"))
    final_msg = agent.call_model(messages, use_tools=False)
    answer = str(final_msg.content)
    if tool_payloads:
        return f"{answer}\n\n" + "\n\n".join(tool_payloads[-3:])
    return answer


def _run_exclusive_tool(agent: ResearchAgent, query: str) -> str | None:
    """Run a single-tool sub-agent's tool before model synthesis.

    Phase 2 sub-agents each own exactly one retrieval/model tool. Executing it
    first makes source status deterministic and avoids treating model-only text
    as retrieval evidence when tool calling is skipped.
    """

    if len(agent.tools_by_name) != 1:
        return None
    tool = next(iter(agent.tools_by_name.values()))
    try:
        return str(tool.invoke({"query": query}))
    except Exception as exc:
        source = {
            "search_rag": "RAG",
            "search_web": "Web",
            "ask_model": "Model",
        }.get(tool.name, "Model")
        return SourceResult(
            source=source,
            status="failed",
            detail=tool.name,
            error=f"{type(exc).__name__}: {exc}",
            content=f"{tool.name} 执行失败。",
        ).to_tool_text()


def _source_result_from_agent_text(source: str, text: str) -> SourceResult:
    """Parse the last tool payload for a source; agent-only text becomes fallback."""

    parsed = [result for result in parse_source_results(text) if result.source == source]
    if parsed:
        result = parsed[-1]
        cleaned = strip_source_markers(text)
        if cleaned and result.is_valid_evidence:
            result.content = cleaned
        return result
    return fallback_result(
        source,
        "未检测到该 Agent 的结构化工具成功结果；仅可作为模型补写或失败后的推断。",
        strip_source_markers(text),
    )


def _format_source_section(title: str, result: SourceResult) -> str:
    status_line = f"状态：{result.status}"
    detail_line = f"详情：{result.detail}" if result.detail else "详情：未提供"
    error_line = f"错误/降级说明：{result.error}" if result.error else "错误/降级说明：无"
    content = strip_source_markers(result.content).strip() or "无可用内容。"
    return f"## {title}\n{status_line}\n{detail_line}\n{error_line}\n\n{content}\n"


def _reflect_and_refine(query: str, answer: str, agent: ResearchAgent, history: list) -> str:
    """Reflexion 自反思：让 Agent 批判自己的回答 → 修正 → 返回改进版"""
    critique_prompt = f"""请严格审查你刚才的回答。

用户问题：{query}

你的回答：
{answer[:2000]}

请回答以下问题：
1. 回答中有哪些可能的不足或遗漏？
2. 是否有未被证据充分支持的主张？
3. 置信度评估是否合理？

然后用改进后的版本重写回答。保持 ```final 标记格式。"""

    critique_msg = HumanMessage(content=critique_prompt)
    response = agent.call_model(history + [critique_msg], use_tools=False)
    content = str(response.content) if response.content else answer

    if FINAL_MARKER in content:
        return content.split(FINAL_MARKER, 1)[1].strip()
    return content[:2000]  # 防止过长


# ── Nodes ──────────────────────────────────────────────────

def dispatch_node(state: MultiAgentState) -> dict:
    """dispatch 节点：返回 query，由 Send 分发"""
    started_at = time.time()
    run_id = state.get("_run_id") or new_run_id()
    thread_id = state.get("_thread_id") or run_id
    checkpoint_backend = state.get("_checkpoint_backend") or "none"
    resumed = bool(state.get("_resumed"))
    return {
        "_pipeline_stage": "dispatch",
        "_run_id": run_id,
        "_thread_id": thread_id,
        "_checkpoint_backend": checkpoint_backend,
        "_resumed": resumed,
        "_run_summary": {
            "mode": "phase2",
            "run_id": run_id,
            "thread_id": thread_id,
            "checkpoint_backend": checkpoint_backend,
            "resumed": resumed,
            "started_at": started_at,
            "elapsed_ms": 0,
            "stages": ["dispatch"],
            "l4_enabled": bool(get("research", "enable_l4", default=True)),
            "slo_p95_ms": int(get("slo", "survey_p95_ms", default=45000)),
            "slo_status": "running",
        },
    }


def rag_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """RAG retrieval is already structured; do not summarize it twice."""
    result = _run_exclusive_tool(agent, state["query"])
    if result is None:
        result = fallback_result("RAG", "RAG Agent 未配置唯一检索工具。").to_tool_text()
    return {"rag_result": result}


def web_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """Web retrieval is already structured; do not summarize it twice."""
    result = _run_exclusive_tool(agent, state["query"])
    if result is None:
        result = fallback_result("Web", "Web Agent 未配置唯一检索工具。").to_tool_text()
    return {"web_result": result}


def model_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """Run one post-retrieval Model Analyst call over structured external evidence."""

    external_results = {
        "RAG": _source_result_from_agent_text("RAG", state.get("rag_result", "")),
        "Web": _source_result_from_agent_text("Web", state.get("web_result", "")),
    }
    external_graph = build_evidence_graph_from_results(external_results)
    evidence_table = _analyst_evidence_table(external_graph)
    gaps = _evidence_gaps(external_results, external_graph)
    prompt = f"""你是检索后的研究分析员，不是新的事实来源。请只做解释、比较、提出假设和识别证据缺口。

用户问题：{state['query']}

结构化外部证据：
{json.dumps(evidence_table, ensure_ascii=False, indent=2)}

当前未覆盖问题：
{chr(10).join(f'- {gap}' for gap in gaps)}

请输出简洁 Markdown：
1. 证据支持的比较与解释，必须引用证据 ID；
2. 明确标注的“模型推断”，不得声称是外部事实；
3. 证据冲突和局限；
4. 2-4 条下一轮检索词。
"""
    response = agent.raw_model.invoke([
        SystemMessage(content="你是研究分析员。外部事实只能来自给定证据，自己的内容一律标记为模型推断。"),
        HumanMessage(content=prompt),
    ])
    analysis = str(response.content).strip()
    claims = _model_analysis_claims(analysis)
    result = SourceResult(
        source="Model",
        status="success" if analysis else "fallback",
        detail="post-retrieval model analyst",
        content=analysis or "模型分析未返回内容。",
        evidence_class="model_inference",
        claims=claims,
        metadata={"evidence_ids": [item["id"] for item in evidence_table], "identified_gaps": gaps},
    )
    return {
        "model_result": result.to_tool_text(),
        "_run_summary": _append_stage(state, "model_analysis"),
        "_pipeline_stage": "model_analyzed",
    }


def _analyst_evidence_table(graph: EvidenceGraph) -> list[dict]:
    return [
        {
            "id": node.id,
            "claim": node.claim,
            "quote": node.verbatim_quote,
            "source": node.source,
            "paper_id": node.paper_id,
            "section": node.paper_section,
            "evidence_class": node.evidence_class,
            "relevance": node.relevance,
            "limitations": node.limitations,
        }
        for node in graph.nodes.values()
        if node.source in {"RAG", "Web"}
    ]


def _evidence_gaps(results: dict[str, SourceResult], graph: EvidenceGraph) -> list[str]:
    gaps = []
    for source, result in results.items():
        if result.status != "success":
            gaps.append(f"{source} 当前状态为 {result.status}，需要更精确的检索。")
    if not graph.nodes:
        gaps.append("没有可验证的外部声明。")
    if graph.consensus_summary().get("true_consensus_count", 0) == 0:
        gaps.append("尚无由两个独立外部来源支持的同一声明。")
    return gaps or ["检查时间敏感性、样本范围和方法局限。"]


def _model_analysis_claims(text: str) -> list[AgentClaim]:
    claims = []
    for raw in text.splitlines():
        cleaned = re.sub(r"^[-*\d.)\s]+", "", raw).strip()
        if len(cleaned) < 20:
            continue
        claims.append(AgentClaim(
            claim=cleaned[:240],
            source="Model",
            verbatim_quote=cleaned[:500],
            paper_section="analysis",
            relevance=0.0,
            research_type="model_analysis",
            confidence=0.45,
            limitations=["model inference; cannot support external factual claims"],
            evidence_class="model_inference",
        ))
        if len(claims) >= 6:
            break
    return claims


def evidence_merge(state: MultiAgentState, *, arbitrator_model=None) -> dict:
    """合并三个 Agent 的结果，运行仲裁 + 构建证据网络

    1. 格式化三方结果
    2. 构建 EvidenceGraph（声明提取 + 去重 + 矛盾检测）
    3. 用 cheap 模型生成仲裁摘要
    """
    source_results = {
        "RAG": _source_result_from_agent_text("RAG", state.get("rag_result", "")),
        "Web": _source_result_from_agent_text("Web", state.get("web_result", "")),
        "Model": _source_result_from_agent_text("Model", state.get("model_result", "")),
    }

    merged = "\n\n---\n\n".join([
        _format_source_section("本地知识库 (RAG) 结果", source_results["RAG"]),
        _format_source_section("互联网搜索 (Web) 结果", source_results["Web"]),
        _format_source_section("模型世界知识 (Model) 结果", source_results["Model"]),
    ])

    graph = build_evidence_graph_from_results(source_results)
    evidence_json = graph.to_json()
    source_statuses = {source: result.to_dict() for source, result in source_results.items()}

    arbitration = ""
    if arbitrator_model and merged:
        arbitration = _run_arbitration(
            state["query"],
            merged,
            arbitrator_model,
            evidence_json,
            source_statuses,
        )

    return {
        "_merged": merged,
        "_arbitration": arbitration,
        "_evidence_json": evidence_json,
        "_source_statuses": source_statuses,
        "_run_summary": _append_stage(state, "evidence_merge"),
        "_pipeline_stage": "evidence_merged",
    }




def _run_arbitration(
    query: str,
    merged: str,
    model,
    evidence_summary: str = "",
    source_statuses: dict | None = None,
) -> str:
    """仲裁器（对应架构文档 §2.1 五级冲突升级协议）

    Level 0: 一致性锚定 → 三源一致的声明标记高置信度
    Level 1: 双向仲裁 → 两源一致 vs 一源分歧，多数原则
    Level 2: 权威加权 → 为声明计算加权分数 authority_weighted_score
    Level 3: 溯源深挖 → 对冲突声明标注需要回溯原始 Agent 输出
    Level 4: 人工升级 → 不可自动裁决标记 [HUMAN_ESCALATION_NEEDED]

    权威分来自每条 EvidenceItem 的证据类型、相关度和来源状态，不能按 RAG/Web 通道固定赋值。
    """
    evidence_hint = ""
    if evidence_summary:
        evidence_hint = f"\n证据网络摘要：{evidence_summary}\n"
    status_hint = source_status_markdown(source_statuses or {})

    prompt = f"""你是信息仲裁器，遵循五级冲突升级协议。必须使用证据节点中的 authority_score，禁止按 RAG/Web/Model 通道固定赋权。
状态为 success 的来源可以正常参与共识投票；low_relevance 可作为弱相关证据参与低权重投票；no_evidence / failed / fallback 必须排除在投票外，只能作为检索缺口、失败说明或模型推断风险提示。
你必须明确区分：
- 多源真实共识：至少两个 success 来源支持；
- 弱相关支持：low_relevance 来源只提供上下文，不得提升为高置信共识；
- 单源声明：只有一个 success 或 low_relevance 来源支持；
- 工具失败/无证据后的推断：来源状态是 no_evidence/failed/fallback 或没有结构化工具成功结果；
- 互相冲突的声明：证据图或来源文本出现相反结论。

用户问题：{query}
来源状态：
{status_hint}
{evidence_hint}
以下是三个信息源的结果：

{merged}

请按以下结构输出（中文，精简）：

## Level 0 — 共识声明（高置信度 > 0.9）
列出多源 success 真实共识。不要把 low_relevance、no_evidence、failed、fallback 来源计入高置信共识。

## Level 1 — 多数声明（中置信度 0.7-0.9）
列出两个 success 来源支持、一源未覆盖、弱相关、无证据或失败的声明。标注缺失/弱相关/无证据来源。

## Level 2 — 权威加权投票
对于存在分歧的声明，按证据节点实际 authority_score 加权；同行评审、权威文件、预印本和社区内容必须区分。
success 正常加权；low_relevance 降权；model_inference、no_evidence/failed/fallback 不能作为外部事实投票。

## Level 3 — 溯源深挖建议
对于加权后仍存争议的声明，标注「建议回溯原始 Agent 输出交叉验证」。

## Level 4 — 人工升级标记
对于无法自动裁决的关键分歧，标注 [HUMAN_ESCALATION_NEEDED] 并说明原因。

## 单源声明
列出只有一个 success 或 low_relevance 来源支持的关键声明，并降低置信度。

## 工具失败/无证据/推断
列出 no_evidence/failed/fallback 来源及其影响。明确说明这些内容不得当作真实来源。

## 整体仲裁概要
共识度评估（高/中/低）+ 对最终报告的建议。"""

    messages = [
        SystemMessage(content="你是一个信息仲裁分析器。请精简、结构化地按五级协议输出。"),
        HumanMessage(content=prompt),
    ]
    response = model.invoke(messages)
    return str(response.content)


def synthesize_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """综合节点：LLM 综合三方结果 + 仲裁摘要，生成最终报告"""
    merged = state.get("_merged", "")
    arbitration = state.get("_arbitration", "")
    source_statuses = state.get("_source_statuses") or {}
    if not merged:
        return {"final_answer": "错误：未能从任何信息源获取结果。"}

    arb_section = ""
    if arbitration:
        arb_section = f"\n\n## 仲裁分析（供参考）\n{arbitration}"

    messages = [
        SystemMessage(content="""你是 Conflux 的调研报告综合编辑。你必须输出简洁 Markdown 主报告。
硬性要求：
- 不得把 no_evidence/failed/fallback 来源当作真实来源；
- low_relevance 只能作为弱相关上下文，必须标注低置信；
- 模型世界知识只能作为 Model 来源，不能替代 Web/RAG 证据；
- 每个外部事实声明后必须使用工具提供的精确引用，例如 [RAG:paper#chunk-001] 或 [Web:https://...]；
- [RAG:low_relevance]、[Web:no_evidence] 等状态说明不是引用，必须写入“信息来源”小节而非事实声明后；
- 模型分析只能标注 [Model]，并明确写“模型推断”；
- 分层输出：多源 success 为高置信；单源 success 为中低置信；low_relevance 为低置信；仅 Model 可用时允许回答但必须标注“模型推断，缺少外部证据支持”；三源均无内容时才拒答；
- 对单源声明、弱相关证据和工具无证据/失败后的推断明确降低置信度；
- 主报告保持简洁（目标1200–2500字），证据图、原始三源输出由系统附录提供，不要大段复制。"""),
        HumanMessage(content=f"""用户问题：{state['query']}

来源状态：
{source_status_markdown(source_statuses)}

以下是三个信息源的结果：

{merged}{arb_section}

请输出以下小节（总字数控制在1200–2500字）：
## 最终结论
用 3-6 条给出核心结论，逐条标注来源和置信度。

## 信息来源
简述 RAG/Web/Model 的状态、可用证据和失败/降级情况。

## 不确定性
说明单源声明、时间敏感信息、工具失败、模型推断带来的不确定性。

## 证据摘要
简述哪些结论来自多源共识、哪些是单源声明、哪些存在冲突。

## 工程落地建议
给出面向多智能体调研系统或用户问题的可执行建议。
"""),
    ]

    response = agent.raw_model.invoke(messages)
    final_answer = _ensure_model_fallback_report(
        state["query"],
        str(response.content),
        source_statuses,
        merged,
    )
    return {
        "final_answer": final_answer,
        "_run_summary": _append_stage(state, "synthesize"),
        "_pipeline_stage": "synthesized",
    }


def _ensure_model_fallback_report(
    query: str,
    candidate: str,
    source_statuses: dict,
    merged: str,
) -> str:
    """Replace short refusals with a low-confidence Model-only report when available."""

    report = candidate.strip()
    model_payload = source_statuses.get("Model") or {}
    model_status = str(model_payload.get("status") or "")
    model_content = strip_source_markers(str(model_payload.get("content") or ""))
    external_evidence = [
        source
        for source in ("RAG", "Web")
        if status_is_evidence(str((source_statuses.get(source) or {}).get("status") or ""))
    ]
    model_available = model_status == "success" and len(model_content.strip()) >= 80
    if external_evidence or not model_available or not _looks_like_short_refusal(report):
        return report

    return f"""## 最终结论
- 当前 RAG/Web 没有提供可用外部证据；以下内容仅基于 Model 来源的模型推断，置信度较低。[Model]
- 针对“{query}”，可先给出概念性脉络或工程判断，但不应把它表述为已被本地知识库或 Web 验证的结论。[Model]

## 信息来源
- RAG/Web：未形成可引用外部证据，状态见来源表。
- Model：有可用推断内容，但属于模型世界知识，不是检索证据。

## 不确定性
- 该回答缺少 RAG/Web 证据支撑，事实细节、时间线、引用来源和具体案例都需要后续检索验证。
- 若问题涉及标准、产品版本、论文结论或政策日期，应优先补充权威 Web 或本地文档证据。

## 证据摘要
- 多源共识：暂无。
- 单源内容：仅 Model 给出低置信推断。
- 检索缺口：RAG/Web 未返回足够相关证据，不能参与事实投票。

## 工程落地建议
- 将本轮输出作为“待验证草案”，下一轮优先使用 query planner 的英文/中文子查询补充 RAG/Web 证据。
- 对关键事实建立最小引用清单；没有引用的内容继续保持 Model-only 低置信标注。

### Model 推断草案
{model_content.strip()[:2200]}
"""


def _looks_like_short_refusal(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) >= 260:
        return False
    refusal_markers = [
        "无法给到",
        "无法提供",
        "没有相关内容",
        "未能获取",
        "无法回答",
        "不能回答",
        "no relevant",
        "cannot provide",
        "i cannot",
    ]
    lowered = stripped.lower()
    return any(marker in lowered or marker in stripped for marker in refusal_markers)


def factcheck_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """FactCheck 验证节点（L2 验证循环 — Maker-Checker 模式）

    读取 synthesize 的报告，逐条检查关键声明是否能追溯到原始 Agent 输出。
    如果发现无证据支持的声明，标记问题并生成修正版报告。
    """
    report = state.get("final_answer", "")
    evidence_json = state.get("_evidence_json", "")
    source_statuses = state.get("_source_statuses") or {}
    if not report:
        return {
            "_verified_answer": report,
            "_factcheck_status": "skipped",
            "_factcheck_report": "FactCheck 跳过：缺少报告或来源。",
            "_factcheck_findings": {"issues": ["缺少待核查报告。"], "verified_claim_ratio": 0.0},
            "_run_summary": _append_stage(state, "factcheck_skipped"),
        }

    deterministic_findings = _deterministic_factcheck(report, source_statuses, evidence_json)
    evidence_items = _factcheck_evidence_items(evidence_json)

    prompt = f"""你是事实核查员（Fact-Checker）。请检查以下调研报告中的关键声明。

对于报告中每个重要的事实断言，检查它是否能在原始信息源中找到支持证据。
success 来源可作为有效证据；low_relevance 只能作为弱相关证据；no_evidence/failed/fallback 不可作为事实支持。
当 RAG/Web 无证据但 Model success 时，允许报告给出明确标注的低置信“模型推断”，但不得写成外部证据已验证。

来源状态：
{source_status_markdown(source_statuses)}

确定性预检查：
{json.dumps(deterministic_findings, ensure_ascii=False, indent=2)}

结构化证据声明（逐条核验，不使用原始文本截断）：
{json.dumps(evidence_items, ensure_ascii=False, indent=2)}

调研报告：
{report}

请输出（精简）：
1. 已验证的声明（可追溯到 success 来源）— 列出 3-5 个
2. 弱证据声明（仅 low_relevance 支持）— 如有则列出
3. 模型推断声明（仅 Model 支持且已标注低置信）— 如有则列出
4. 无法验证的声明（找不到 success/low_relevance 来源支持，且未标注模型推断）— 如有则列出
5. 无证据/失败/降级来源是否被误用 — 如有则列出
6. 需要修正的声明 — 如有事实错误则指出正确版本
7. 整体验证结论：通过 / 需修正 / 部分通过

如果报告质量良好，写「验证通过：所有关键声明均有信息源支持」即可。"""

    messages = [
        SystemMessage(content="你是一个严格的事实核查员。只基于提供的原始信息源判断，不要引入外部知识。"),
        HumanMessage(content=prompt),
    ]
    fc_result = agent.raw_model.invoke(messages)
    fc_text = str(fc_result.content)
    deterministic_passed = not deterministic_findings["issues"]
    if deterministic_passed and "验证通过" in fc_text and "无法验证" not in fc_text and "需修正" not in fc_text:
        status = "passed"
    else:
        status = "needs_review"
    factcheck_report = f"{_factcheck_findings_markdown(deterministic_findings)}\n\n{fc_text.strip()}"
    next_state = {
        **state,
        "_verified_answer": factcheck_report,
        "_factcheck_status": status,
        "_factcheck_report": factcheck_report,
        "_factcheck_findings": deterministic_findings,
        "_review_status": "awaiting_user_review" if status == "needs_review" else "accepted",
        "_run_summary": _append_stage(state, "factcheck"),
        "_pipeline_stage": "factchecked",
    }
    return {
        "_verified_answer": factcheck_report,
        "_factcheck_status": status,
        "_factcheck_report": factcheck_report,
        "_factcheck_findings": deterministic_findings,
        "_review_status": next_state["_review_status"],
        "_quality_report": evaluate_run_quality(next_state),
        "_run_summary": next_state["_run_summary"],
        "_pipeline_stage": "factchecked",
    }


def _revise_report_after_factcheck(report: str, findings: dict) -> str:
    """Deterministically remove excluded source citations from report text."""

    revised = report
    for source in findings.get("non_evidence_sources") or []:
        revised = revised.replace(f"[{source}]", f"[{source}:excluded]")
        revised = revised.replace(f"来源：{source}", f"来源：{source}:excluded")
        revised = revised.replace(f"source:{source}", f"source:{source}:excluded")
    if revised != report:
        revised += (
            "\n\n## Verification Revision Log\n"
            "No-evidence/failed/fallback source citations were excluded from factual support before final delivery.\n"
        )
    return revised


def _deterministic_factcheck(report: str, source_statuses: dict, evidence_json: str) -> dict:
    """Match each key report claim against structured, source-backed evidence."""

    success_sources = {
        source
        for source, payload in (source_statuses or {}).items()
        if payload.get("status") == "success"
    }
    low_relevance_sources = {
        source
        for source, payload in (source_statuses or {}).items()
        if payload.get("status") == "low_relevance"
    }
    evidence_sources = success_sources | low_relevance_sources
    non_evidence_sources = {
        source
        for source, payload in (source_statuses or {}).items()
        if status_is_non_evidence(str(payload.get("status") or ""))
    }
    cited_sources = {
        source
        for source in ("RAG", "Web", "Model")
        if f"[{source}]" in report or f"来源：{source}" in report or f"来源:{source}" in report
    }
    issues = []
    invalid_mentions = sorted((cited_sources & non_evidence_sources) - evidence_sources)
    if invalid_mentions:
        issues.append(
            f"报告把 no_evidence/failed/fallback 来源 {', '.join(invalid_mentions)} 用作事实证据引用。"
        )

    evidence_items = _factcheck_evidence_items(evidence_json)
    nodes = [item for item in evidence_items if item.get("claim")]
    model_only_allowed = (
        not nodes
        and "Model" in success_sources
        and not (success_sources - {"Model"})
        and ("模型推断" in report or "Model" in report)
    )
    if not nodes and not model_only_allowed:
        issues.append("证据图没有任何来自 success/low_relevance 来源的声明节点，关键事实无法追溯。")

    report_claims = _extract_key_report_claims(report)
    claim_checks = []
    for claim in report_claims:
        cited = _cited_sources(claim)
        candidates = [item for item in nodes if not cited or item.get("source") in cited]
        ranked = sorted(
            ((item, _claim_text_overlap(claim, str(item.get("claim") or ""))) for item in candidates),
            key=lambda pair: pair[1],
            reverse=True,
        )
        best, overlap = ranked[0] if ranked else ({}, 0.0)
        source = str(best.get("source") or "")
        source_status = str((source_statuses.get(source) or {}).get("status") or "")
        evidence_class = str(best.get("evidence_class") or "")
        if overlap >= 0.12 and source_status == "success" and evidence_class in EXTERNAL_EVIDENCE_CLASSES:
            verification = "verified"
        elif overlap >= 0.12 and source_status == "low_relevance":
            verification = "weak_evidence"
        elif overlap >= 0.12 and evidence_class == "model_inference" and "Model" in cited:
            verification = "model_inference"
        else:
            verification = "unverified"
        claim_checks.append({
            "claim": claim,
            "cited_sources": sorted(cited),
            "matched_evidence_id": best.get("id", ""),
            "matched_source": source,
            "overlap": round(overlap, 3),
            "verification": verification,
        })

    verified_count = sum(item["verification"] == "verified" for item in claim_checks)
    verified_ratio = verified_count / len(claim_checks) if claim_checks else 0.0
    unverified = [item for item in claim_checks if item["verification"] == "unverified"]
    if unverified:
        issues.append(f"{len(unverified)} 条关键声明未匹配到可核验的结构化证据。")
    if claim_checks and verified_ratio <= 0.5:
        issues.append(f"关键声明外部证据覆盖率仅为 {verified_ratio:.0%}，未超过 50%。")

    if "不确定" not in report and (non_evidence_sources or len(evidence_sources) < 2):
        issues.append("存在失败/单源条件，但报告没有明确不确定性说明。")

    return {
        "success_sources": sorted(success_sources),
        "low_relevance_sources": sorted(low_relevance_sources),
        "non_evidence_sources": sorted(non_evidence_sources),
        "evidence_node_count": len(nodes),
        "report_claim_count": len(report_claims),
        "verified_claim_count": verified_count,
        "verified_claim_ratio": round(verified_ratio, 3),
        "claim_checks": claim_checks,
        "issues": issues,
    }


def _factcheck_evidence_items(evidence_json: str) -> list[dict]:
    try:
        payload = json.loads(evidence_json) if evidence_json else {}
    except json.JSONDecodeError:
        return []
    items = []
    for node in payload.get("nodes") or []:
        items.append({
            key: node.get(key)
            for key in (
                "id",
                "claim",
                "source",
                "evidence_class",
                "paper_id",
                "paper_section",
                "verbatim_quote",
                "evidence_refs",
                "confidence",
                "limitations",
            )
        })
    return items


def _extract_key_report_claims(report: str) -> list[str]:
    claims = []
    in_conclusion = False
    for raw in report.splitlines():
        line = raw.strip()
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            in_conclusion = "最终结论" in heading.group(1) or "核心结论" in heading.group(1)
            continue
        if in_conclusion and re.match(r"^(?:[-*]|\d+[.)])\s+", line):
            claims.append(re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line))
    if claims:
        return claims[:12]
    return [
        line.strip()
        for line in report.splitlines()
        if len(line.strip()) >= 30 and not line.lstrip().startswith("#")
    ][:12]


def _cited_sources(claim: str) -> set[str]:
    return set(re.findall(r"\[(RAG|Web|Model)(?::[^\]]+)?\]", claim))


def _claim_text_overlap(left: str, right: str) -> float:
    def tokens(text: str) -> set[str]:
        cleaned = re.sub(r"\[(RAG|Web|Model)(?::[^\]]+)?\]", "", text, flags=re.IGNORECASE)
        english = set(re.findall(r"[a-z][a-z0-9_-]{2,}", cleaned.lower()))
        chinese = re.sub(r"[^\u4e00-\u9fff]", "", cleaned)
        bigrams = {chinese[index:index + 2] for index in range(max(0, len(chinese) - 1))}
        return english | bigrams

    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _factcheck_findings_markdown(findings: dict) -> str:
    lines = [
        "### 确定性追溯检查",
        f"- success 来源：{', '.join(findings.get('success_sources') or []) or '无'}",
        f"- low_relevance 来源：{', '.join(findings.get('low_relevance_sources') or []) or '无'}",
        f"- no_evidence/failed/fallback 来源：{', '.join(findings.get('non_evidence_sources') or []) or '无'}",
        f"- 证据节点数：{findings.get('evidence_node_count', 0)}",
        f"- 关键声明核验覆盖率：{float(findings.get('verified_claim_ratio', 0.0)):.0%}",
    ]
    issues = findings.get("issues") or []
    if issues:
        lines.append("- 问题：" + "；".join(issues))
    else:
        lines.append("- 问题：未发现结构性追溯问题。")
    return "\n".join(lines)


def factcheck_router(state: MultiAgentState) -> str:
    """路由：可选进入 L4 深挖循环。"""
    if get("research", "enable_l4", default=True):
        return "deeper_research"
    return "end"


def fanout(state: MultiAgentState) -> list[Send]:
    """并行执行两个外部检索源；Model 必须等待检索完成。"""
    return [
        Send("rag_agent", state),
        Send("web_agent", state),
    ]


# ── L4 Research Loop ───────────────────────────────────────

def discover_sub_questions(report: str, model) -> list[str]:
    """L4 Research Loop：从报告中提取需要进一步研究的子问题"""
    if not report or len(report.strip()) < 20:
        return []

    prompt = f"""从以下调研报告中，提取2-3个值得进一步深入研究的具体子问题。

报告：
{report[:2000]}

只输出子问题，每行一个，不要编号。如果没有值得深挖的问题，输出「无」。"""

    messages = [
        SystemMessage(content="你是调研分析师。简洁输出子问题。"),
        HumanMessage(content=prompt),
    ]
    response = model.invoke(messages)
    content = str(response.content)

    questions = []
    for line in content.split("\n"):
        line = line.strip().lstrip("- ").strip()
        if line and len(line) > 10 and line != "无":
            questions.append(line)
    return questions[:3]


# ── L5 Goal Loop ──────────────────────────────────────────

def process_user_feedback(
    query: str,
    report: str,
    feedback: str,
    model: BaseChatModel,
) -> str:
    """L5 Goal Loop：用户反馈驱动的再调研

    用户对报告不满意 → 提取反馈中的修正点 → 生成改进版报告。
    对应架构文档 L5 — 用户反馈 → 修正/深化 → 继续。
    """
    if not feedback.strip():
        return report

    prompt = f"""用户对以下调研报告提出了反馈。请根据反馈修正报告。

原始问题：{query}

原报告：
{report[:3000]}

用户反馈：
{feedback}

请输出改进后的完整报告（保持原格式）。"""

    messages = [
        SystemMessage(content="你是调研报告编辑。根据用户反馈修正报告，保持客观准确。"),
        HumanMessage(content=prompt),
    ]
    response = model.invoke(messages)
    return str(response.content)


def deeper_research_node(
    state: MultiAgentState,
    *,
    model: BaseChatModel,
    rag_agent: ResearchAgent | None = None,
    web_agent: ResearchAgent | None = None,
    arbitrator_model=None,
) -> dict:
    """L4 loop: discover gaps, retrieve new evidence, re-arbitrate, and verify."""
    max_questions = int(get("research", "max_deep_questions", default=2))
    report = state.get("final_answer", "")
    if not report or max_questions <= 0:
        next_state = {
            **state,
            "_deep_research": "",
            "_run_summary": _append_stage(state, "deep_research_skipped"),
            "_pipeline_stage": "deep_research_skipped",
        }
        return {
            "_deep_research": "",
            "_quality_report": evaluate_run_quality(next_state),
            "_run_summary": next_state["_run_summary"],
            "_pipeline_stage": "deep_research_skipped",
        }

    questions = discover_sub_questions(report, model)[:max_questions]
    if not questions:
        next_state = {
            **state,
            "_deep_research": "",
            "_run_summary": _append_stage(state, "deep_research_skipped"),
            "_pipeline_stage": "deep_research_skipped",
        }
        return {
            "_deep_research": "",
            "_quality_report": evaluate_run_quality(next_state),
            "_run_summary": next_state["_run_summary"],
            "_pipeline_stage": "deep_research_skipped",
        }

    deep_queries = [f"{state['query']} {question}" for question in questions]
    combined_deep_query = f"{state['query']} {' '.join(questions)}"
    fresh_results: dict[str, SourceResult] = {}
    for source, source_agent in (("RAG", rag_agent), ("Web", web_agent)):
        payloads = []
        if source_agent is not None:
            payload = _run_exclusive_tool(source_agent, combined_deep_query)
            if payload:
                payloads.extend(
                    result for result in parse_source_results(payload) if result.source == source
                )
        existing_payload = (state.get("_source_statuses") or {}).get(source)
        if existing_payload:
            payloads.insert(0, SourceResult.from_dict(existing_payload))
        fresh_results[source] = _combine_source_results(source, payloads)

    model_payload = (state.get("_source_statuses") or {}).get("Model")
    fresh_results["Model"] = (
        SourceResult.from_dict(model_payload)
        if model_payload
        else fallback_result("Model", "深化研究不新增 Model 外部证据。")
    )
    deep_graph = build_evidence_graph_from_results(fresh_results)
    deep_evidence_json = deep_graph.to_json()
    deep_statuses = {source: result.to_dict() for source, result in fresh_results.items()}
    deep_merged = "\n\n---\n\n".join(
        _format_source_section(f"深化 {source}", result)
        for source, result in fresh_results.items()
    )
    deep_arbitration = ""
    if arbitrator_model:
        deep_arbitration = _run_arbitration(
            state["query"],
            deep_merged,
            arbitrator_model,
            deep_evidence_json,
            deep_statuses,
        )

    prompt = f"""你是 Conflux 的深化调研节点。请基于本轮新检索证据，对子问题给出补充分析。

原始问题：{state['query']}

需要深化的子问题：
{chr(10).join(f"- {q}" for q in questions)}

本轮结构化证据：
{json.dumps(_analyst_evidence_table(deep_graph), ensure_ascii=False, indent=2)}

来源状态：
{source_status_markdown(deep_statuses)}

本轮仲裁：
{deep_arbitration}

已有报告：
{report}

要求：
- 只基于提供材料和明确的模型推理补充；
- success 来源可作为事实证据；low_relevance 只能作为弱相关上下文；
- 对 no_evidence/failed/fallback 来源只能说明检索缺口或失败影响，不能用于支持结论；
- 每条深化结论标注“证据支持”或“模型推断”；
- 标注哪些内容仍需进一步检索；
- 输出 Markdown 小节。"""

    messages = [
        SystemMessage(content="你是调研深化节点，输出简洁的 Markdown 补充分析。"),
        HumanMessage(content=prompt),
    ]
    response = model.invoke(messages)
    deep = str(response.content).strip()
    deep_findings = _deterministic_factcheck(deep, deep_statuses, deep_evidence_json)
    deep_factcheck = _factcheck_findings_markdown(deep_findings)
    next_state = {
        **state,
        "_deep_research": deep,
        "_deep_queries": deep_queries,
        "_deep_arbitration": deep_arbitration,
        "_deep_factcheck_report": deep_factcheck,
        "_deep_evidence_json": deep_evidence_json,
        "_deep_source_statuses": deep_statuses,
        "_run_summary": _append_stage(state, "deep_research"),
        "_pipeline_stage": "deep_researched",
    }
    return {
        "_deep_research": deep,
        "_deep_queries": deep_queries,
        "_deep_arbitration": deep_arbitration,
        "_deep_factcheck_report": deep_factcheck,
        "_deep_evidence_json": deep_evidence_json,
        "_deep_source_statuses": deep_statuses,
        "_quality_report": evaluate_run_quality(next_state),
        "_run_summary": next_state["_run_summary"],
        "_pipeline_stage": "deep_researched",
    }


def _combine_source_results(source: str, results: list[SourceResult]) -> SourceResult:
    if not results:
        return fallback_result(source, "深化研究没有获得结构化结果。")
    valid = [result for result in results if result.is_valid_evidence]
    if not valid:
        return results[-1]
    claims = []
    seen = set()
    for result in valid:
        for claim in result.claims:
            key = (claim.paper_id.casefold(), re.sub(r"\s+", " ", claim.claim).casefold())
            if key not in seen:
                seen.add(key)
                claims.append(claim)
    status = "success" if any(result.status == "success" for result in valid) else "low_relevance"
    evidence_class = max(
        (result.evidence_class for result in valid),
        key=lambda value: {
            "peer_reviewed": 5,
            "authoritative_document": 4,
            "preprint": 3,
            "community_content": 2,
            "model_inference": 1,
        }.get(value, 0),
    )
    return SourceResult(
        source=source,
        status=status,
        detail="deep research retrieval",
        content="\n\n".join(result.content for result in valid if result.content),
        claims=claims,
        evidence_class=evidence_class,
        metadata={"round_count": len(results), "deep_research": True},
    )


def _append_stage(state: MultiAgentState, stage: str) -> dict:
    """更新运行摘要，记录阶段、耗时和 SLO。"""
    summary = dict(state.get("_run_summary") or {})
    started_at = float(summary.get("started_at") or time.time())
    stages = list(summary.get("stages") or [])
    stages.append(stage)
    elapsed_ms = round((time.time() - started_at) * 1000, 2)
    p95_ms = int(get("slo", "survey_p95_ms", default=45000))
    summary.update({
        "mode": summary.get("mode", "phase2"),
        "run_id": state.get("_run_id") or summary.get("run_id"),
        "thread_id": state.get("_thread_id") or summary.get("thread_id"),
        "checkpoint_backend": state.get("_checkpoint_backend") or summary.get("checkpoint_backend", "none"),
        "resumed": bool(state.get("_resumed") or summary.get("resumed")),
        "started_at": started_at,
        "elapsed_ms": elapsed_ms,
        "stages": stages,
        "slo_p95_ms": p95_ms,
        "slo_status": "pass" if elapsed_ms <= p95_ms else "breached",
    })
    return summary


# ── Graph Construction ─────────────────────────────────────

def create_multi_agent_graph(
    rag_agent: ResearchAgent,
    web_agent: ResearchAgent,
    model_agent: ResearchAgent,
    synthesizer_model,  # raw BaseChatModel，用于 synthesize
    arbitrator_model=None,  # raw BaseChatModel，用于仲裁（默认=cheap）
    checkpointer=None,
) -> StateGraph:
    """构建三 Agent 并行派发状态图"""
    graph = StateGraph(MultiAgentState)

    graph.add_node("dispatch", dispatch_node)
    graph.add_node("rag_agent", lambda s: rag_agent_node(s, agent=rag_agent))
    graph.add_node("web_agent", lambda s: web_agent_node(s, agent=web_agent))
    graph.add_node("model_agent", lambda s: model_agent_node(s, agent=model_agent))
    graph.add_node("evidence_merge", lambda s: evidence_merge(s, arbitrator_model=arbitrator_model))

    # 用一个轻量 agent wrapper 传给 synthesize
    syn_agent = ResearchAgent(synthesizer_model, [])
    graph.add_node("synthesize", lambda s: synthesize_node(s, agent=syn_agent))

    # FactCheck 验证节点（L2 验证循环）
    fc_agent = ResearchAgent(arbitrator_model or synthesizer_model, [])
    graph.add_node("factcheck", lambda s: factcheck_node(s, agent=fc_agent))
    graph.add_node(
        "deeper_research",
        lambda s: deeper_research_node(
            s,
            model=arbitrator_model or synthesizer_model,
            rag_agent=rag_agent,
            web_agent=web_agent,
            arbitrator_model=arbitrator_model,
        ),
    )

    graph.set_entry_point("dispatch")

    # dispatch → external retrieval fan-out → post-retrieval Model Analyst
    graph.add_conditional_edges("dispatch", fanout, path_map=["rag_agent", "web_agent"])

    graph.add_edge("rag_agent", "model_agent")
    graph.add_edge("web_agent", "model_agent")
    graph.add_edge("model_agent", "evidence_merge")

    # merge → synthesize → factcheck → end
    graph.add_edge("evidence_merge", "synthesize")
    graph.add_edge("synthesize", "factcheck")
    graph.add_conditional_edges("factcheck", factcheck_router, {
        "deeper_research": "deeper_research",
        "end": END,
    })
    graph.add_edge("deeper_research", END)

    return graph.compile(checkpointer=checkpointer)
