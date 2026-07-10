"""Model-knowledge tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from ..source_status import AgentClaim, SourceResult


_model: BaseChatModel | None = None


def set_model(model: BaseChatModel) -> None:
    """Inject the model used by the ask_model tool."""

    global _model
    _model = model


@tool
def ask_model(query: str) -> str:
    """Answer from model knowledge only, clearly marked as inference."""

    if _model is None:
        return SourceResult(
            source="Model",
            status="failed",
            detail="LLM world knowledge",
            error="The model-knowledge tool was not initialized. Call set_model() first.",
            content="The model-knowledge tool was not initialized.",
        ).to_tool_text()

    messages = [
        SystemMessage(content=(
            "You answer from model knowledge only. Be concise, name uncertainty, "
            "and never present this answer as retrieved RAG or Web evidence."
        )),
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
            content="Model-knowledge call failed.",
        ).to_tool_text()

    if isinstance(content, list):
        content = str(content[0]) if content else ""
    content = str(content)
    body = f"[model knowledge / inference]\n{content}"
    claim_text = _claim_from_model_content(content)
    return SourceResult(
        source="Model",
        status="success",
        detail="LLM world knowledge",
        content=body,
        claims=[
            AgentClaim(
                claim=claim_text,
                source="Model",
                evidence_refs=["[Model:world-knowledge]"],
                confidence=0.55,
                limitations=["model knowledge / inference; not external retrieved evidence"],
            )
        ] if claim_text else [],
        metadata={"evidence_type": "model knowledge / inference"},
    ).to_tool_text()


def _claim_from_model_content(content: str, max_length: int = 220) -> str:
    text = " ".join(content.strip().split())
    return text[:max_length]
