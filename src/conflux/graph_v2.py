"""LangGraph 状态图 v2 — Phase 2 三 Agent 并行派发 (fan-out)

Graph 结构：
  __start__ → dispatch → [Send: rag | web | model] → evidence_merge → synthesize → __end__

每个子 Agent 是独立的 ReAct 循环（内嵌于 SubGraph），并行执行。
"""

import json
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
    SourceResult,
    fallback_result,
    parse_source_results,
    source_status_markdown,
    strip_source_markers,
)
from .quality import evaluate_run_quality


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
    _deep_research: str
    _run_summary: dict
    _quality_report: dict
    _pipeline_stage: str
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
            "如果工具状态是 failed/fallback，必须明确说明不可作为真实来源。\n\n"
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
        if cleaned and result.status == "success":
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
    return {
        "_pipeline_stage": "dispatch",
        "_run_summary": {
            "mode": "phase2",
            "started_at": started_at,
            "elapsed_ms": 0,
            "stages": ["dispatch"],
            "slo_p95_ms": int(get("slo", "survey_p95_ms", default=45000)),
            "slo_status": "running",
        },
    }


def rag_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """RAG 子 Agent：仅用 search_rag"""
    result = _run_agent(state["query"], agent)
    return {"rag_result": result}


def web_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """Web 子 Agent：仅用 search_web"""
    result = _run_agent(state["query"], agent)
    return {"web_result": result}


def model_agent_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """Model 子 Agent：仅用 ask_model"""
    result = _run_agent(state["query"], agent)
    return {"model_result": result}


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
    _dedup_graph(graph)
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


def _dedup_graph(graph: EvidenceGraph) -> None:
    """简单去重：合并前 30 个字符相同的节点"""
    seen: dict[str, str] = {}
    to_remove = []
    for nid, node in list(graph.nodes.items()):
        key = node.claim[:30].strip().lower()
        if key in seen:
            # 合并到已存在的节点
            existing_id = seen[key]
            existing = graph.nodes[existing_id]
            existing.supporting.extend(node.supporting)
            existing.derived_from.extend(node.derived_from)
            # 取较高的权威分
            existing.authority_score = max(existing.authority_score, node.authority_score)
            to_remove.append(nid)
        else:
            seen[key] = nid
    for nid in to_remove:
        del graph.nodes[nid]


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

    权威分权重：
    - RAG (本地知识库): 0.7 — 可控可审计
    - Web: 0.5 — 权威性参差
    - Model: 0.4 — 无溯源、有幻觉风险
    """
    evidence_hint = ""
    if evidence_summary:
        evidence_hint = f"\n证据网络摘要：{evidence_summary}\n"
    status_hint = source_status_markdown(source_statuses or {})

    prompt = f"""你是信息仲裁器，遵循五级冲突升级协议。权威分权重：RAG=0.7, Web=0.5, Model=0.4。
只有状态为 success 的来源可以参与共识投票。failed / fallback 来源必须排除在投票外，只能作为失败说明或模型推断风险提示。
你必须明确区分：
- 多源真实共识：至少两个 success 来源支持；
- 单源声明：只有一个 success 来源支持；
- 工具失败后的推断：来源状态是 failed/fallback 或没有结构化工具成功结果；
- 互相冲突的声明：证据图或来源文本出现相反结论。

用户问题：{query}
来源状态：
{status_hint}
{evidence_hint}
以下是三个信息源的结果：

{merged}

请按以下结构输出（中文，精简）：

## Level 0 — 共识声明（高置信度 > 0.9）
列出多源 success 真实共识。不要把 failed/fallback 来源计入共识。

## Level 1 — 多数声明（中置信度 0.7-0.9）
列出两个 success 来源支持、一源未覆盖或失败的声明。标注缺失/失败来源。

## Level 2 — 权威加权投票
对于存在分歧的声明，按权威分加权计算：
- 声明 A (RAG 0.7 + Web 0.5) vs 声明 B (Model 0.4) → 采纳声明 A
只对 success 来源加权，failed/fallback 不能投票。

## Level 3 — 溯源深挖建议
对于加权后仍存争议的声明，标注「建议回溯原始 Agent 输出交叉验证」。

## Level 4 — 人工升级标记
对于无法自动裁决的关键分歧，标注 [HUMAN_ESCALATION_NEEDED] 并说明原因。

## 单源声明
列出只有一个 success 来源支持的关键声明，并降低置信度。

## 工具失败/推断
列出 failed/fallback 来源及其影响。明确说明这些内容不得当作真实来源。

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
- 不得把 failed/fallback 来源当作真实来源；
- 模型世界知识只能作为 Model 来源，不能替代 Web/RAG 证据；
- 每个关键事实声明后标注来源类型，例如 [RAG]、[Web]、[Model]；
- 对单源声明和工具失败后的推断明确降低置信度；
- 主报告保持简洁，证据图、原始三源输出由系统附录提供，不要大段复制。"""),
        HumanMessage(content=f"""用户问题：{state['query']}

来源状态：
{source_status_markdown(source_statuses)}

以下是三个信息源的结果：

{merged}{arb_section}

请输出以下小节：
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
    return {
        "final_answer": str(response.content),
        "_run_summary": _append_stage(state, "synthesize"),
        "_pipeline_stage": "synthesized",
    }


def factcheck_node(state: MultiAgentState, *, agent: ResearchAgent) -> dict:
    """FactCheck 验证节点（L2 验证循环 — Maker-Checker 模式）

    读取 synthesize 的报告，逐条检查关键声明是否能追溯到原始 Agent 输出。
    如果发现无证据支持的声明，标记问题并生成修正版报告。
    """
    report = state.get("final_answer", "")
    merged = state.get("_merged", "")
    evidence_json = state.get("_evidence_json", "")
    source_statuses = state.get("_source_statuses") or {}
    if not report or not merged:
        return {
            "_verified_answer": report,
            "_factcheck_status": "skipped",
            "_factcheck_report": "FactCheck 跳过：缺少报告或来源。",
            "_run_summary": _append_stage(state, "factcheck_skipped"),
        }

    deterministic_findings = _deterministic_factcheck(report, source_statuses, evidence_json)

    prompt = f"""你是事实核查员（Fact-Checker）。请检查以下调研报告中的关键声明。

对于报告中每个重要的事实断言，检查它是否能在原始信息源中找到支持证据。
只有状态为 success 的来源可作为有效证据；failed/fallback 不可作为事实支持。

来源状态：
{source_status_markdown(source_statuses)}

确定性预检查：
{json.dumps(deterministic_findings, ensure_ascii=False, indent=2)}

证据图：
{evidence_json[:3000]}

原始信息源：
{merged[:4000]}

调研报告：
{report[:3000]}

请输出（精简）：
1. 已验证的声明（可追溯到 success 来源）— 列出 3-5 个
2. 无法验证的声明（找不到 success 来源支持）— 如有则列出
3. 失败/降级来源是否被误用 — 如有则列出
4. 需要修正的声明 — 如有事实错误则指出正确版本
5. 整体验证结论：通过 / 需修正 / 部分通过

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
        final_answer = report
    else:
        status = "needs_review"
        final_answer = (
            f"{report.rstrip()}\n\n"
            "## FactCheck 验证结果\n"
            f"{_factcheck_findings_markdown(deterministic_findings)}\n\n"
            f"{fc_text.strip()}\n"
        )
    factcheck_report = f"{_factcheck_findings_markdown(deterministic_findings)}\n\n{fc_text.strip()}"

    return {
        "_verified_answer": factcheck_report,
        "_factcheck_status": status,
        "_factcheck_report": factcheck_report,
        "final_answer": final_answer,
        "_run_summary": _append_stage(state, "factcheck"),
        "_pipeline_stage": "factchecked",
    }


def _deterministic_factcheck(report: str, source_statuses: dict, evidence_json: str) -> dict:
    """Cheap deterministic checks before LLM FactCheck."""

    success_sources = {
        source
        for source, payload in (source_statuses or {}).items()
        if payload.get("status") == "success"
    }
    failed_sources = {
        source
        for source, payload in (source_statuses or {}).items()
        if payload.get("status") in {"failed", "fallback"}
    }
    cited_sources = {
        source
        for source in ("RAG", "Web", "Model")
        if f"[{source}]" in report or f"来源：{source}" in report or f"来源:{source}" in report
    }
    issues = []
    invalid_mentions = sorted((cited_sources & failed_sources) - success_sources)
    if invalid_mentions:
        issues.append(
            f"报告把 failed/fallback 来源 {', '.join(invalid_mentions)} 用作事实证据引用。"
        )

    try:
        evidence_payload = json.loads(evidence_json) if evidence_json else {}
    except json.JSONDecodeError:
        evidence_payload = {}
    nodes = evidence_payload.get("nodes") or []
    if not nodes:
        issues.append("证据图没有任何来自 success 来源的声明节点，关键事实无法追溯。")

    if "不确定" not in report and (failed_sources or len(success_sources) < 2):
        issues.append("存在失败/单源条件，但报告没有明确不确定性说明。")

    return {
        "success_sources": sorted(success_sources),
        "failed_or_fallback_sources": sorted(failed_sources),
        "evidence_node_count": len(nodes),
        "issues": issues,
    }


def _factcheck_findings_markdown(findings: dict) -> str:
    lines = [
        "### 确定性追溯检查",
        f"- success 来源：{', '.join(findings.get('success_sources') or []) or '无'}",
        f"- failed/fallback 来源：{', '.join(findings.get('failed_or_fallback_sources') or []) or '无'}",
        f"- 证据节点数：{findings.get('evidence_node_count', 0)}",
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
    """并行派发到三个子 Agent"""
    return [
        Send("rag_agent", state),
        Send("web_agent", state),
        Send("model_agent", state),
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


def deeper_research_node(state: MultiAgentState, *, model: BaseChatModel) -> dict:
    """L4 Research Loop：基于首轮报告提取子问题，并生成一次深化摘要。"""
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

    prompt = f"""你是 Conflux 的深化调研节点。请基于已有三源结果和最终报告，对下列子问题给出补充分析。

原始问题：{state['query']}

需要深化的子问题：
{chr(10).join(f"- {q}" for q in questions)}

三源原始输出：
{state.get('_merged', '')[:4000]}

来源状态：
{source_status_markdown(state.get('_source_statuses') or {})}

已有报告：
{report[:3000]}

要求：
- 只基于提供材料和明确的模型推理补充；
- 只有 success 来源可作为事实证据；
- 对 failed/fallback 来源只能说明失败影响，不能用于支持结论；
- 每条深化结论标注“证据支持”或“模型推断”；
- 标注哪些内容仍需进一步检索；
- 输出 Markdown 小节。"""

    messages = [
        SystemMessage(content="你是调研深化节点，输出简洁的 Markdown 补充分析。"),
        HumanMessage(content=prompt),
    ]
    response = model.invoke(messages)
    deep = str(response.content).strip()
    final_answer = f"{report.rstrip()}\n\n## 深化研究补充\n{deep}\n"
    run_summary = _append_stage(state, "deep_research")
    next_state = {
        **state,
        "_deep_research": deep,
        "final_answer": final_answer,
        "_run_summary": run_summary,
        "_pipeline_stage": "deep_researched",
    }
    return {
        "_deep_research": deep,
        "final_answer": final_answer,
        "_quality_report": evaluate_run_quality(next_state),
        "_run_summary": run_summary,
        "_pipeline_stage": "deep_researched",
    }


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
    graph.add_node("deeper_research", lambda s: deeper_research_node(s, model=arbitrator_model or synthesizer_model))

    graph.set_entry_point("dispatch")

    # dispatch → fan-out to three agents
    graph.add_conditional_edges("dispatch", fanout, path_map=["rag_agent", "web_agent", "model_agent"])

    # 每个 agent → evidence_merge
    graph.add_edge("rag_agent", "evidence_merge")
    graph.add_edge("web_agent", "evidence_merge")
    graph.add_edge("model_agent", "evidence_merge")

    # merge → synthesize → factcheck → end
    graph.add_edge("evidence_merge", "synthesize")
    graph.add_edge("synthesize", "factcheck")
    graph.add_conditional_edges("factcheck", factcheck_router, {
        "deeper_research": "deeper_research",
        "end": END,
    })
    graph.add_edge("deeper_research", END)

    return graph.compile()
