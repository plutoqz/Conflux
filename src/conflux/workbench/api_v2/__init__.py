"""P4.2 C 对话入口 — FastAPI v2 层（/api/chat/* + /docs）。"""

from .app import app, create_app, serve_api_v2  # noqa: F401
from .schemas import (  # noqa: F401
    ApprovalDecisionRequest,
    ApprovalRecord,
    ChatMessageRequest,
    ChatMessageResponse,
    IntentResult,
)

__all__ = [
    "app",
    "create_app",
    "serve_api_v2",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "IntentResult",
    "ApprovalRecord",
    "ApprovalDecisionRequest",
]
