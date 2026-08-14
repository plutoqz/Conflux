"""P4.2 C 对话入口 — FastAPI v2 请求/响应模型（Pydantic v2）。

老端点（stdlib ThreadingHTTPServer）冻结不动；新功能只进本 v2 层。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChatAction = Literal[
    "research_query",
    "run_radar",
    "project_audit",
    "cycle_summary",
    "memory_query",
    "experiment",
    "mentor_report",
    "clarify",
]


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None
    project_id: str | None = None
    depth: Literal["quick", "standard", "deep"] | None = None


class IntentResult(BaseModel):
    """C2 意图路由结果：确定性规则优先，LLM 分类兜底且非白名单即拒绝。"""

    action: ChatAction
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["rules", "llm", "fallback"] = "fallback"
    clarify_question: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    reply: str
    action: ChatAction | None = None
    run_id: str | None = None
    events_url: str | None = None
    requires_approval: bool = False
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalRecord(BaseModel):
    """C3 写操作门禁：入库/雷达/实验登记须先经用户确认才执行。"""

    approval_id: str
    operation: str
    diff: dict[str, Any] = Field(default_factory=dict)
    risk: Literal["low", "medium", "high"] = "low"
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: float = 0.0


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
