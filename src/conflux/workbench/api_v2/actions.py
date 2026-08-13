"""C3 编排接线：动作 → 既有 Job/读取复用；写操作先过 ApprovalRequest 门禁。

- research_query：复用既有 JobManager（P3 job kind），提交即返回 run_id + events_url。
- run_radar（雷达/入库）：写操作 —— 先创建 ApprovalRecord，未经确认零执行；
  确认后才调用既有的 run_project_research_radar 入队。
- project_audit / cycle_summary：只读，复用 P3 /api/v1/projects/* 的构建函数。
- memory_query：A 阶段（P4.0）落地前返回澄清式提示，不幻觉执行。
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

from .schemas import ApprovalRecord, ChatMessageResponse, IntentResult

_WRITE_EXECUTORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
_APPROVALS: dict[str, ApprovalRecord] = {}
_APPROVAL_LOCK = threading.Lock()


def _memory_repo() -> Any:
    """每次请求打开独立的 user_memory 仓库连接（bootstrap 幂等）。"""

    from conflux.adapters.sqlite_store import SQLiteDatabase
    from conflux.core.runtime_home import database_path
    from conflux.memory import UserMemoryRepository

    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    return UserMemoryRepository(db)


def register_executor(operation: str, executor: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """注册写操作执行器（测试可替换）；approve 时按 operation 分发。"""

    _WRITE_EXECUTORS[operation] = executor


def create_approval(
    operation: str,
    diff: dict[str, Any],
    *,
    risk: str = "low",
) -> ApprovalRecord:
    approval = ApprovalRecord(
        approval_id=f"approval-{uuid.uuid4().hex[:12]}",
        operation=operation,
        diff=diff,
        risk=risk,  # type: ignore[arg-type]
        status="pending",
        created_at=time.time(),
    )
    with _APPROVAL_LOCK:
        _APPROVALS[approval.approval_id] = approval
    return approval


def list_pending_approvals() -> list[ApprovalRecord]:
    with _APPROVAL_LOCK:
        return [item for item in _APPROVALS.values() if item.status == "pending"]


def decide_approval(approval_id: str, decision: str) -> dict[str, Any]:
    """确认门：rejected 直接关闭；approved 才执行注册的写操作。"""

    with _APPROVAL_LOCK:
        approval = _APPROVALS.get(approval_id)
    if approval is None:
        return {"ok": False, "error": f"审批不存在：{approval_id}"}
    if approval.status != "pending":
        return {"ok": False, "error": f"审批已处理：{approval.status}"}
    if decision not in {"approved", "rejected"}:
        return {"ok": False, "error": "decision 必须为 approved 或 rejected"}
    if decision == "rejected":
        approval.status = "rejected"
        return {"ok": True, "approval_id": approval_id, "status": "rejected", "executed": False}
    executor = _WRITE_EXECUTORS.get(approval.operation)
    if executor is None:
        return {"ok": False, "error": f"未注册执行器：{approval.operation}"}
    result = executor(dict(approval.diff))
    if result.get("ok") is False:
        return {"ok": False, "approval_id": approval_id, "status": "pending", **result}
    approval.status = "approved"
    return {"ok": True, "approval_id": approval_id, "status": "approved", "executed": True, **result}


def _default_write_executors() -> None:
    """惰性注册默认执行器（避免模块导入时拉起重型 server 依赖）。"""

    if _WRITE_EXECUTORS:
        return

    def radar(diff: dict[str, Any]) -> dict[str, Any]:
        from conflux.workbench.server import run_project_research_radar

        return run_project_research_radar(diff)

    _WRITE_EXECUTORS["research.radar"] = radar


def execute_intent(intent: IntentResult, request: Any) -> ChatMessageResponse:
    """按意图动作执行；写操作返回待确认，读取直接返回结果摘要。"""

    _default_write_executors()
    message = str(getattr(request, "message", "") or "").strip()
    project_id = str(getattr(request, "project_id", "") or "").strip()
    depth = str(getattr(request, "depth", "") or "").strip() or "standard"

    if intent.action == "clarify":
        return ChatMessageResponse(
            reply=intent.clarify_question or "我不确定你想做什么。",
            action="clarify",
        )

    if intent.action == "research_query":
        from conflux.workbench.jobs import get_job_manager

        submitted = get_job_manager().submit(
            message,
            {"depth": depth, "project_id": project_id},
        )
        return ChatMessageResponse(
            reply=(
                f"已提交调研任务：{submitted['run_id']}（深度 {depth}）。"
                "我将在证据链完整后给出带引用的结论。"
            ),
            action="research_query",
            run_id=submitted["run_id"],
            events_url=submitted["events_url"],
        )

    if intent.action == "run_radar":
        if not project_id:
            return ChatMessageResponse(
                reply="请先告诉我项目 ID（已登记项目），我再运行论文雷达。",
                action="clarify",
                clarify_question="",
            )
        approval = create_approval(
            "research.radar",
            {"project_id": project_id, "work_item_id": "", "gap_source": "chat"},
            risk="medium",
        )
        return ChatMessageResponse(
            reply=(
                f"论文雷达会扫描并可能把候选论文写入项目 {project_id}，"
                f"需要你确认后才执行（审批号 {approval.approval_id}）。"
            ),
            action="run_radar",
            requires_approval=True,
            approval_id=approval.approval_id,
        )

    if intent.action == "project_audit":
        from conflux.workbench.server import build_p3_audit, build_p3_projects

        if project_id:
            payload = build_p3_audit(project_id)
        else:
            payload = build_p3_projects()
        return ChatMessageResponse(
            reply=_summarize_audit(payload, project_id),
            action="project_audit",
            payload=payload,
        )

    if intent.action == "cycle_summary":
        from conflux.workbench.server import build_p3_audit

        if not project_id:
            return ChatMessageResponse(
                reply="请告诉我项目 ID，我汇总该项目本周期已确认的进展与风险。",
                action="clarify",
            )
        payload = build_p3_audit(project_id)
        return ChatMessageResponse(
            reply=_summarize_cycle(payload),
            action="cycle_summary",
            payload=payload,
        )

    if intent.action == "memory_query":
        from conflux.memory import UserMemoryRepository

        repo = _memory_repo()
        try:
            entries = repo.recall(message, kinds=("preference", "feedback", "reference"), limit=5)
        finally:
            repo.db.close()
        if not entries:
            return ChatMessageResponse(
                reply="还没有相关的用户记忆条目；你可以让我「以后都……」或在工作台记忆页登记偏好。",
                action="memory_query",
                payload={"entries": []},
            )
        lines = [
            f"- [{entry['kind']}] {entry['description']}"
            for entry in entries
        ]
        return ChatMessageResponse(
            reply="相关记忆条目：\n" + "\n".join(lines),
            action="memory_query",
            payload={"entries": entries},
        )

    return ChatMessageResponse(reply="暂不支持该动作。", action="clarify")


def _summarize_audit(payload: dict[str, Any], project_id: str) -> str:
    if project_id:
        if payload.get("ok") is False:
            return f"审计读取失败：{payload.get('error')}"
        return f"项目 {project_id} 的审计快照已读取（详见 payload）。"
    projects = payload.get("projects") or []
    return f"当前登记了 {len(projects)} 个项目，可以指定项目 ID 查看审计明细。"


def _summarize_cycle(payload: dict[str, Any]) -> str:
    if payload.get("ok") is False:
        return f"周期汇总读取失败：{payload.get('error')}"
    cycle = payload.get("cycle_summary") or payload.get("confirmed_summary") or {}
    if not cycle:
        return "本周期尚未确认摘要；可先运行项目审计并确认后生成周期汇总。"
    return (
        f"本周期已确认摘要：真实进展 {cycle.get('real_progress', 0)} 项、"
        f"失败工作项 {cycle.get('failed_experiments', 0)} 项、常驻风险 {cycle.get('risks', 0)} 项。"
    )
