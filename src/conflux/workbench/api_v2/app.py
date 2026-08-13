"""P4.2 C 对话入口 — FastAPI v2 层（/api/chat/*）。

老端点（stdlib ThreadingHTTPServer）冻结不动；本层经 uvicorn 与老服务同进程
共存（默认独立端口），OpenAPI 文档在 /docs。
"""

from __future__ import annotations

import threading
from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from . import actions
from .intent import classify_intent
from .schemas import (
    ApprovalDecisionRequest,
    ChatMessageRequest,
    ChatMessageResponse,
)
from .streaming import multiplex, sse_frames

_classifier: Any = None
_classifier_lock = threading.Lock()


def _get_classifier() -> Any:
    """惰性构建 flash 意图分类模型；配置缺失时返回 None（规则表兜底）。"""

    global _classifier
    with _classifier_lock:
        if _classifier is None:
            try:
                from conflux.model_factory import create_chat_model

                _classifier = create_chat_model("flash", max_tokens=256, max_retries=0)
            except Exception:
                _classifier = False  # 标记不可用，避免反复重建
        return _classifier if _classifier is not False else None


def _reply_tokens(message: str, response: ChatMessageResponse) -> Iterator[str]:
    """回复 token 源：有模型时走模型流，否则按字符切片（确定性兜底）。"""

    model = _get_classifier()
    if model is not None:
        try:
            for chunk in model.stream([
                {
                    "role": "system",
                    "content": "You are Conflux's chat assistant. Reply concisely in the user's language.",
                },
                {"role": "user", "content": message},
            ]):
                text = str(getattr(chunk, "content", chunk) or "")
                if text:
                    yield text
            return
        except Exception:
            pass
    yield response.reply


def _chat_response(request: ChatMessageRequest) -> ChatMessageResponse:
    intent = classify_intent(request.message, llm=_get_classifier())
    return actions.execute_intent(intent, request)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Conflux Chat API v2",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    @app.get("/api/chat/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "service": "conflux-chat-v2"}

    @app.post("/api/chat/intent")
    def intent(request: ChatMessageRequest) -> dict[str, Any]:
        result = classify_intent(request.message, llm=_get_classifier())
        return result.model_dump()

    @app.post("/api/chat/messages")
    def messages(request: ChatMessageRequest) -> dict[str, Any]:
        return _chat_response(request).model_dump()

    @app.post("/api/chat/messages/stream")
    def messages_stream(request: ChatMessageRequest) -> StreamingResponse:
        def frames() -> Iterator[str]:
            intent_result = classify_intent(request.message, llm=_get_classifier())
            yield f"event: intent\ndata: {intent_result.model_dump_json()}\n\n"
            response = actions.execute_intent(intent_result, request)
            event_source = None
            if intent_result.action == "research_query" and response.run_id:
                from conflux.workbench.jobs import get_job_manager

                manager = get_job_manager()

                def poll() -> list[dict[str, Any]]:
                    try:
                        return manager.events(response.run_id or "", after_id=0)
                    except Exception:
                        return []

                event_source = poll
            yield from sse_frames(
                multiplex(
                    _reply_tokens(request.message, response),
                    event_source=event_source,
                    run_id=response.run_id or "",
                )
            )

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/chat/approvals")
    def approvals() -> dict[str, Any]:
        return {"ok": True, "pending": [item.model_dump() for item in actions.list_pending_approvals()]}

    @app.post("/api/chat/approvals/{approval_id}")
    def approve(approval_id: str, decision: ApprovalDecisionRequest) -> dict[str, Any]:
        return actions.decide_approval(approval_id, decision.decision)

    # ── P4.0 A 用户记忆与技能库（v2 进程承载 /api/v1/*，老 stdlib 服务零改动） ──

    @app.get("/api/v1/memory")
    def memory_list(kind: str | None = None, status: str | None = None) -> dict[str, Any]:
        from conflux.memory import UserMemoryRepository

        repo = actions._memory_repo()
        try:
            entries = repo.list(kind=kind or None, status=status or None)
            return {"ok": True, "entries": entries, "capacity": 500, "count": len(entries)}
        finally:
            repo.db.close()

    @app.post("/api/v1/memory")
    def memory_add(payload: dict[str, Any]) -> dict[str, Any]:
        from conflux.memory import MemoryCapacityError, UserMemoryRepository

        repo = actions._memory_repo()
        try:
            memory_id = repo.add(
                kind=str(payload.get("kind") or ""),
                content=payload.get("content") or {},
                description=str(payload.get("description") or ""),
                source_event_id=str(payload.get("source_event_id") or ""),
                source_run_id=str(payload.get("source_run_id") or ""),
                project_id=str(payload.get("project_id") or ""),
                confidence=float(payload.get("confidence") or 1.0),
                status=str(payload.get("status") or "active"),
            )
            return {"ok": True, "id": memory_id, **repo.get(memory_id)}
        except (ValueError, MemoryCapacityError) as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            repo.db.close()

    @app.post("/api/v1/memory/{memory_id}/confirm")
    def memory_confirm(memory_id: str) -> dict[str, Any]:
        return _memory_transition(memory_id, "confirm")

    @app.post("/api/v1/memory/{memory_id}/reject")
    def memory_reject(memory_id: str) -> dict[str, Any]:
        return _memory_transition(memory_id, "reject")

    @app.get("/api/v1/skills")
    def skills_list() -> dict[str, Any]:
        from conflux.skills import SkillLibrary

        skills, problems = SkillLibrary().load()
        return {
            "ok": True,
            "skills": [skill.to_dict() for skill in skills],
            "problems": problems,
        }

    @app.post("/api/v1/skills")
    def skills_add(payload: dict[str, Any]) -> dict[str, Any]:
        from pathlib import Path

        from conflux.skills import DEFAULT_SKILLS_DIR, SkillLibrary

        library = SkillLibrary()
        skills, _ = library.load()
        name = str(payload.get("name") or "").strip()
        if not name or not str(payload.get("description") or "").strip():
            return {"ok": False, "error": "name 与 description 必填"}
        if any(skill.name == name for skill in skills):
            return {"ok": False, "error": f"技能已存在：{name}"}
        skill_path = Path(DEFAULT_SKILLS_DIR) / f"{name}.yaml"
        try:
            import yaml

            skill_path.write_text(
                yaml.safe_dump({key: value for key, value in payload.items() if value not in (None, "")}, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        _, problems = SkillLibrary().load()
        return {"ok": True, "name": name, "path": str(skill_path), "problems": problems}

    return app


def _memory_transition(memory_id: str, decision: str) -> dict[str, Any]:
    from conflux.workbench.api_v2 import actions as actions_module

    repo = actions_module._memory_repo()
    try:
        entry = repo.confirm(memory_id) if decision == "confirm" else repo.reject(memory_id)
        if entry is None:
            return {"ok": False, "error": f"记忆不存在或非 pending：{memory_id}"}
        return {"ok": True, **entry}
    finally:
        repo.db.close()


app = create_app()


def serve_api_v2(*, host: str = "127.0.0.1", port: int = 9765) -> threading.Thread:
    """与老 ThreadingHTTPServer 同进程共存：uvicorn 跑在守护线程，独立端口。"""

    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="conflux-chat-v2")
    thread.start()
    return thread
