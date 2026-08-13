"""C6 MCP server — stdio 暴露工作台工具（P4.2 对话生态的最小可用面）。

工具执行复用现有实现：search_rag/search_web 复用 tools/rag.py、tools/web.py
的 tool 管道；paper_radar 复用工作台雷达入队；project_audit/cycle_summary
复用 P3 只读构建函数（同 api_v2 层）。

明确后置（设计文档 §5-6 完整版）：MCP client、观测面板、OTel/Langfuse 导出。

用法：python -m conflux.mcp_server   （stdio；供 MCP client 拉起）
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("conflux")


def _rag_tool(profile: Any) -> Any:
    from conflux.rag import HybridRetriever, create_vector_store

    from conflux.tools.rag import create_rag_tool

    retriever = HybridRetriever(create_vector_store())
    return create_rag_tool(retriever, None, None, profile)


def _web_tool(profile: Any, run_id: str) -> Any:
    from conflux.tools.web import create_web_tool

    return create_web_tool(profile, run_id=run_id)


def _profile() -> Any:
    from conflux.research_modes import resolve_research_profile

    return resolve_research_profile("standard")


@mcp.tool()
def search_rag(query: str) -> str:
    """检索本地知识库（RAG），返回证据化结果文本。"""
    tool = _rag_tool(_profile())
    return str(tool.invoke(query) or "")


@mcp.tool()
def search_web(query: str) -> str:
    """联网检索（受 standard 档预算约束），返回证据化结果文本。"""
    from conflux.trace import new_run_id

    tool = _web_tool(_profile(), new_run_id())
    return str(tool.invoke(query) or "")


@mcp.tool()
def paper_radar(project_id: str) -> str:
    """为已登记项目入队一次论文雷达扫描（durable job）。"""
    from conflux.workbench.server import run_project_research_radar

    result = run_project_research_radar({"project_id": project_id})
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def project_audit(project_id: str) -> str:
    """读取项目审计快照（只读）。"""
    from conflux.workbench.server import build_p3_audit

    payload = build_p3_audit(project_id)
    return json.dumps(payload, ensure_ascii=False)[:6000]


@mcp.tool()
def cycle_summary(project_id: str) -> str:
    """读取项目已确认的周期汇总（只读）。"""
    from conflux.workbench.server import build_p3_audit

    payload = build_p3_audit(project_id)
    cycle = payload.get("cycle_summary") or payload.get("confirmed_summary") or {}
    return json.dumps(cycle, ensure_ascii=False) if cycle else "本周期尚未确认摘要。"


def main(argv: list[str] | None = None) -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
