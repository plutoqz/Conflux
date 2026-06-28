"""模型知识工具 — 封装纯 LLM 世界知识为 Tool，供 Agent 主动调用"""

from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..source_status import SourceResult


# 模块级缓存，由工厂函数注入
_model: BaseChatModel | None = None


def set_model(model: BaseChatModel) -> None:
    """注入用于 ask_model 的 LLM 实例"""
    global _model
    _model = model


@tool
def ask_model(query: str) -> str:
    """直接使用模型自身的世界知识回答问题，不进行任何检索。
    适用于：需要常识推理、概念解释、历史知识、理论分析等模型训练数据中已包含的信息。
    注意：模型知识有截止日期，对实时信息（新闻、最新研究）不应使用此工具。
    """
    if _model is None:
        return SourceResult(
            source="Model",
            status="failed",
            detail="LLM world knowledge",
            error="模型知识工具未初始化。请先调用 set_model() 注入 LLM 实例。",
            content="模型知识工具未初始化。",
        ).to_tool_text()

    messages = [
        SystemMessage(content="你是一个知识渊博的助手。请简洁、准确地回答用户的问题。如果问题涉及你知识范围之外或需要实时数据的内容，请明确说明。"),
        HumanMessage(content=query),
    ]
    try:
        response = _model.invoke(messages)
        content = response.content
    except Exception as exc:
        return SourceResult(
            source="Model",
            status="failed",
            detail="LLM world knowledge",
            error=f"{type(exc).__name__}: {exc}",
            content="模型知识调用失败。",
        ).to_tool_text()
    if isinstance(content, list):
        content = str(content[0]) if content else ""
    body = f"[基于模型世界知识]\n{content}"
    return SourceResult(
        source="Model",
        status="success",
        detail="LLM world knowledge",
        content=body,
    ).to_tool_text()
