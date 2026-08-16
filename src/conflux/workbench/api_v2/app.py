"""P4.2 C 对话入口 — FastAPI v2 层（/api/chat/*）。

老端点（stdlib ThreadingHTTPServer）冻结不动；本层经 uvicorn 与老服务同进程
共存（默认独立端口），OpenAPI 文档在 /docs。
"""

from __future__ import annotations

import re
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
    """Stream the executed action response without invoking a second model."""

    del message
    text = str(response.reply or "")
    if not text:
        return
    for start in range(0, len(text), 24):
        yield text[start:start + 24]


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
                        run_id = response.run_id or ""
                        events = manager.events(run_id, after_id=0)
                        job = manager.get(run_id) or {}
                        status = str(job.get("status") or "")
                        terminal = {
                            "completed", "completed_with_warnings", "completed_diagnostic",
                            "failed", "cancelled", "timed_out",
                        }
                        if status in terminal:
                            last_id = max((int(item.get("id") or 0) for item in events), default=0)
                            events.append({
                                "id": last_id + 1,
                                "run_id": run_id,
                                "stage": "job",
                                "status": status,
                            })
                        return events
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
        if re.fullmatch(r"[A-Za-z0-9_-]+", name) is None:
            return {"ok": False, "error": "name 仅允许字母、数字、下划线和连字符"}
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

    # ── P4.5 E2 文献笔记与写作闭环 ─────────────────────────────

    @app.get("/api/v1/notes")
    def notes_list(status: str | None = None) -> dict[str, Any]:
        from conflux.paper_notes import open_notes_repo

        repo, db = open_notes_repo()
        try:
            entries = repo.list(status=status)
            return {"ok": True, "count": len(entries), "notes": entries}
        finally:
            db.close()

    @app.post("/api/v1/notes")
    def notes_add(payload: dict[str, Any]) -> dict[str, Any]:
        from conflux.paper_notes import NoteCapacityError, open_notes_repo

        repo, db = open_notes_repo()
        try:
            entry = repo.add(
                paper_key=str(payload.get("paper_key") or ""),
                title=str(payload.get("title") or ""),
                note_text=str(payload.get("note_text") or ""),
                fields=dict(payload.get("fields") or {}),
                source_refs=[dict(item) for item in (payload.get("source_refs") or [])],
                status=str(payload.get("status") or "active"),
            )
            return {"ok": True, "note": entry}
        except (ValueError, NoteCapacityError) as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            db.close()

    @app.post("/api/v1/notes/audit")
    def notes_audit(payload: dict[str, Any]) -> dict[str, Any]:
        """E2.2 一致性审计：笔记字段 vs 原文片段（确定性，零 LLM）。"""
        from conflux.paper_notes import audit_note_consistency

        note = dict(payload.get("note") or {})
        source = str(payload.get("source") or "")
        result = audit_note_consistency(note, source)
        return {"ok": True, **result}

    @app.get("/api/v1/notes/bibtex")
    def notes_bibtex(paper_key: str = "") -> dict[str, Any]:
        """E2.1 BibTeX 导出：从论文元数据确定性生成。"""
        if not paper_key:
            return {"ok": False, "error": "paper_key 必填"}
        from conflux.adapters.sqlite_store import PaperStore, SQLiteDatabase
        from conflux.core.runtime_home import database_path
        from conflux.paper_notes import paper_to_bibtex

        db = SQLiteDatabase(database_path()).connect()
        db.bootstrap_schema()
        try:
            paper = PaperStore(db).get(paper_key)
        finally:
            db.close()
        if paper is None:
            return {"ok": False, "error": f"论文不存在：{paper_key}"}
        return {"ok": True, "paper_key": paper_key, "bibtex": paper_to_bibtex(paper)}

    @app.post("/api/v1/notes/related-work")
    def notes_related_work(payload: dict[str, Any]) -> dict[str, Any]:
        """Generate a traceable draft from selected notes."""

        from conflux.paper_notes import generate_related_work, open_notes_repo

        selected_ids = {str(value) for value in (payload.get("note_ids") or []) if value}
        repo, db = open_notes_repo()
        try:
            notes = repo.list(status="active")
        finally:
            db.close()
        if selected_ids:
            notes = [note for note in notes if str(note.get("note_id") or "") in selected_ids]
        if not notes:
            return {"ok": False, "error": "没有可用于 related work 的 active 笔记"}
        draft, problems = generate_related_work(notes)
        return {
            "ok": not problems,
            "draft": draft,
            "problems": problems,
            "note_ids": [str(note.get("note_id") or "") for note in notes],
        }

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
