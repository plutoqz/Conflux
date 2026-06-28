"""LangGraph 状态图 — Phase 1 单层 ReAct 循环

Graph 结构：
  __start__ → agent_node → [conditional: loop | finalize] → __end__

State 定义：
  - query: 用户原始问题
  - messages: 完整的对话历史 (System → User → AI → Tool → ...)
  - final_answer: 最终回答文本
  - iteration_count: 当前循环轮次
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .agent import ResearchAgent, FINAL_MARKER
from .config import get


# ── State ──────────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    messages: list[BaseMessage]
    final_answer: str
    iteration_count: int


# ── Nodes ──────────────────────────────────────────────────

def agent_node(state: AgentState, *, agent: ResearchAgent) -> AgentState:
    """Agent 节点：Think → Act → Observe

    每次调用：
    1. 调用 LLM（绑定工具）获取 AIMessage
    2. 如果有 tool_calls，执行工具并追加 ToolMessage
    3. 如果给出最终答案，标记完成
    """
    messages = state["messages"]
    iteration = state.get("iteration_count", 0)

    # Step 1: Think + Act — 调用 LLM
    ai_message = agent.call_model(messages)
    new_messages = [ai_message]

    # Step 2: Observe — 如果 LLM 请求了工具调用，执行工具
    if ai_message.tool_calls:
        tool_messages = agent.execute_tools(ai_message)
        new_messages.extend(tool_messages)

    # Step 3: 检查是否有最终答案
    final_answer = ""
    if agent.has_final_answer(ai_message):
        content = ai_message.content
        if isinstance(content, str) and FINAL_MARKER in content:
            final_answer = content.split(FINAL_MARKER, 1)[1].strip()
        else:
            final_answer = content

    return {
        "query": state["query"],
        "messages": messages + new_messages,
        "final_answer": final_answer,
        "iteration_count": iteration + 1,
    }


def should_continue(state: AgentState, *, agent: ResearchAgent) -> str:
    """路由：继续循环 or 结束"""
    if state.get("final_answer"):
        return "finalize"

    if state.get("iteration_count", 0) >= agent.max_iterations:
        return "finalize"

    return "loop"


def finalize_node(state: AgentState, *, agent: ResearchAgent) -> AgentState:
    """Finalize 节点：如果循环耗尽仍无 final_answer，强制生成"""
    if state.get("final_answer"):
        return state

    # 最后一轮：用纯文本模型（无工具）基于已有上下文生成回答
    messages = state["messages"] + [
        HumanMessage(content="请基于以上检索结果，给出最终回答。使用 ```final 标记。")
    ]
    ai_message = agent.call_model(messages, use_tools=False)
    content = ai_message.content
    if isinstance(content, str):
        if FINAL_MARKER in content:
            content = content.split(FINAL_MARKER, 1)[1].strip()

    return {
        **state,
        "final_answer": content,
        "messages": state["messages"] + [ai_message],
    }


# ── Graph Construction ─────────────────────────────────────

def create_graph(agent: ResearchAgent) -> StateGraph:
    """构建 Phase 1 单层 ReAct 状态图"""
    graph = StateGraph(AgentState)

    # 注入 agent 实例到所有节点
    graph.add_node("agent", lambda s: agent_node(s, agent=agent))
    graph.add_node("finalize", lambda s: finalize_node(s, agent=agent))

    graph.set_entry_point("agent")

    # agent → [loop 回自己 | finalize]
    graph.add_conditional_edges(
        "agent",
        lambda s: should_continue(s, agent=agent),
        {
            "loop": "agent",
            "finalize": "finalize",
        },
    )

    graph.add_edge("finalize", END)

    return graph.compile()
