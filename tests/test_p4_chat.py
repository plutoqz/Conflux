"""P4.2 C 对话入口最小集测试（对照实施计划 C2–C4、C8 验收表）。

覆盖：意图路由规则优先与白名单兜底（C2）、写操作门禁零执行与确认后执行（C3）、
token/进度 SSE 多路复用与互不阻塞（C4）、OpenAPI 契约（C1）、老端点零变化
（C1 回归另由既有 workbench 测试套件承担）。
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.workbench.api_v2 import actions  # noqa: E402
from conflux.workbench.api_v2.intent import classify_intent  # noqa: E402
from conflux.workbench.api_v2.schemas import ChatMessageRequest, IntentResult  # noqa: E402
from conflux.workbench.api_v2.streaming import multiplex, sse_frames  # noqa: E402


class _FakeLLM:
    """fake 分类模型：返回指定 action 的 JSON。"""

    def __init__(self, action: str):
        self.action = action
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return SimpleNamespace(content=json.dumps(
            {"action": self.action, "confidence": 0.9}
        ))


def _request(message: str, project_id: str = "") -> ChatMessageRequest:
    return ChatMessageRequest(message=message, project_id=project_id or None)


def _intent(action: str) -> IntentResult:
    return IntentResult(action=action, confidence=1.0, source="rules")  # type: ignore[arg-type]


# ============================================================
# C2 意图路由
# ============================================================

class TestIntentRouting:
    def test_rules_hit_deterministically(self):
        assert classify_intent("帮我调研一下多智能体评审").action == "research_query"
        assert classify_intent("跑一次论文雷达").action == "run_radar"
        assert classify_intent("项目审计").action == "project_audit"
        assert classify_intent("本周进展周报").action == "cycle_summary"
        assert classify_intent("我有什么偏好记忆").action == "memory_query"

    def test_llm_non_whitelist_action_is_clarify(self):
        result = classify_intent("随便聊聊", llm=_FakeLLM("delete_all_projects"))
        assert result.action == "clarify"
        assert result.source == "fallback"

    def test_llm_whitelist_action_accepted(self):
        result = classify_intent("随便聊聊", llm=_FakeLLM("cycle_summary"))
        assert result.action == "cycle_summary"
        assert result.source == "llm"

    def test_llm_failure_falls_back_to_clarify(self):
        class _Boom:
            def invoke(self, messages):
                raise RuntimeError("no api")

        result = classify_intent("随便聊聊", llm=_Boom())
        assert result.action == "clarify"
        assert result.clarify_question


# ============================================================
# C3 写操作门禁（零执行 → 确认后才执行）
# ============================================================

class TestApprovalGate:
    def test_write_action_requires_approval_and_zero_execution(self, monkeypatch):
        calls: list[dict] = []

        def fake_radar(diff):
            calls.append(diff)
            return {"ok": True, "job_id": "job-1"}

        monkeypatch.setitem(actions._WRITE_EXECUTORS, "research.radar", fake_radar)
        response = actions.execute_intent(
            _intent("run_radar"), _request("跑一次论文雷达", project_id="p1")
        )
        assert response.requires_approval is True
        assert response.approval_id
        assert calls == []  # 未经确认零执行

    def test_approve_executes_registered_operation(self, monkeypatch):
        calls: list[dict] = []

        def fake_radar(diff):
            calls.append(diff)
            return {"ok": True, "job_id": "job-1"}

        monkeypatch.setitem(actions._WRITE_EXECUTORS, "research.radar", fake_radar)
        approval = actions.create_approval("research.radar", {"project_id": "p1"})
        result = actions.decide_approval(approval.approval_id, "approved")
        assert result["ok"] is True and result["executed"] is True
        assert calls == [{"project_id": "p1"}]

    def test_reject_never_executes(self, monkeypatch):
        calls: list[dict] = []

        def fake_radar(diff):
            calls.append(diff)
            return {"ok": True}

        monkeypatch.setitem(actions._WRITE_EXECUTORS, "research.radar", fake_radar)
        approval = actions.create_approval("research.radar", {"project_id": "p1"})
        result = actions.decide_approval(approval.approval_id, "rejected")
        assert result["executed"] is False
        assert calls == []

    def test_failed_executor_keeps_approval_pending(self, monkeypatch):
        monkeypatch.setitem(
            actions._WRITE_EXECUTORS,
            "research.radar",
            lambda diff: {"ok": False, "error": "project missing"},
        )
        approval = actions.create_approval("research.radar", {"project_id": "nope"})
        result = actions.decide_approval(approval.approval_id, "approved")
        assert result["ok"] is False
        assert approval.status == "pending"

    def test_unknown_approval_rejected(self):
        assert actions.decide_approval("approval-missing", "approved")["ok"] is False

    def test_memory_query_returns_real_entries_or_empty(self, monkeypatch):
        # P4 阶段三落地后 memory_query 走真实仓库；空库 → 提示无条目，不幻觉执行。
        import sqlite3

        import conflux.memory as memory_mod
        from conflux.memory import UserMemoryRepository

        class _DB:
            def __init__(self):
                self.connection = sqlite3.connect(":memory:")
                self.connection.row_factory = sqlite3.Row
                for statement in memory_mod.USER_MEMORY_STATEMENTS:
                    self.connection.execute(statement)
                self.connection.commit()

            def close(self):
                self.connection.close()

        db = _DB()
        monkeypatch.setattr(actions, "_memory_repo", lambda: UserMemoryRepository(db))
        response = actions.execute_intent(_intent("memory_query"), _request("我有什么偏好记忆"))
        assert response.action == "memory_query"
        assert "记忆" in response.reply
        assert response.payload == {"entries": []}
        db.close()


# ============================================================
# C4 流式（token 与进度互不阻塞）
# ============================================================

class TestStreaming:
    def test_multiplex_interleaves_token_and_progress(self):
        events = [
            {"id": 1, "status": "running"},
            {"id": 2, "status": "completed"},
        ]
        items = list(multiplex(["你", "好"], event_source=lambda: events, run_id="run-1"))
        kinds = [kind for kind, _ in items]
        assert kinds[0] == "token"
        assert "progress" in kinds
        assert kinds[-1] == "done"

    def test_progress_polling_does_not_block_tokens(self):
        seen: list[str] = []

        def slow_poll():
            seen.append("poll")
            time.sleep(0.05)
            return [{"id": 1, "status": "completed"}]

        items = list(multiplex(["t1", "t2"], event_source=slow_poll, run_id="run-1"))
        tokens = [payload for kind, payload in items if kind == "token"]
        assert tokens == ["t1", "t2"]
        assert "poll" in seen

    def test_sse_frames_are_well_formed(self):
        frames = list(sse_frames([("token", "你好"), ("progress", {"id": 1}), ("done", None)]))
        assert frames[0] == "event: token\ndata: 你好\n\n"
        assert frames[1].startswith("event: progress\ndata: ")
        assert frames[2] == "event: done\ndata: {}\n\n"


# ============================================================
# C1/C8 API 契约（TestClient）
# ============================================================

class _FakeManager:
    def __init__(self):
        self.submitted: list[dict] = []

    def submit(self, query, payload, *, run_id=None):
        self.submitted.append({"query": query, "payload": payload})
        return {
            "run_id": "run-1",
            "status": "pending",
            "events_url": "/api/query/jobs/run-1/events",
            "status_url": "/api/query/jobs/run-1",
            "timeout_seconds": 300,
            "deadline_at": time.time() + 300,
            "commit_reserve_seconds": 20,
        }

    def events(self, run_id, *, after_id=0, limit=200):
        return [{"id": 1, "run_id": run_id, "status": "completed"}]


class TestChatApi:
    def _client(self, monkeypatch):
        import importlib

        from fastapi.testclient import TestClient

        app_module = importlib.import_module("conflux.workbench.api_v2.app")

        monkeypatch.setattr(app_module, "_get_classifier", lambda: None)
        fake_manager = _FakeManager()
        monkeypatch.setattr(
            "conflux.workbench.jobs.get_job_manager",
            lambda: fake_manager,
        )
        client = TestClient(app_module.create_app())
        client._fake_manager = fake_manager  # type: ignore[attr-defined]
        return client

    def test_health(self, monkeypatch):
        client = self._client(monkeypatch)
        assert client.get("/api/chat/health").json()["ok"] is True

    def test_openapi_covers_chat_routes(self, monkeypatch):
        client = self._client(monkeypatch)
        paths = client.get("/openapi.json").json()["paths"]
        for route in ("/api/chat/messages", "/api/chat/messages/stream",
                      "/api/chat/intent", "/api/chat/approvals/{approval_id}"):
            assert route in paths, route

    def test_clarify_when_unclassifiable(self, monkeypatch):
        client = self._client(monkeypatch)
        body = client.post("/api/chat/messages", json={"message": "今天天气如何"}).json()
        assert body["action"] == "clarify"

    def test_research_query_submits_existing_job_kind(self, monkeypatch):
        client = self._client(monkeypatch)
        body = client.post(
            "/api/chat/messages",
            json={"message": "帮我调研多智能体评审的证据链", "depth": "standard"},
        ).json()
        assert body["action"] == "research_query"
        assert body["run_id"] == "run-1"
        assert body["events_url"] == "/api/query/jobs/run-1/events"
        submitted = client._fake_manager.submitted  # type: ignore[attr-defined]
        assert submitted[0]["payload"]["depth"] == "standard"

    def test_radar_write_requires_approval_via_api(self, monkeypatch):
        client = self._client(monkeypatch)
        body = client.post(
            "/api/chat/messages",
            json={"message": "跑一次论文雷达", "project_id": "p1"},
        ).json()
        assert body["requires_approval"] is True
        approval_id = body["approval_id"]
        pending = client.get("/api/chat/approvals").json()
        assert any(item["approval_id"] == approval_id for item in pending["pending"])
        # 未经确认：执行器未注册（默认惰性注册雷达），确认会被拒——验证门禁存在
        decided = client.post(
            f"/api/chat/approvals/{approval_id}", json={"decision": "rejected"}
        ).json()
        assert decided["ok"] is True and decided["executed"] is False

    def test_stream_endpoint_emits_intent_and_done(self, monkeypatch):
        client = self._client(monkeypatch)
        with client.stream(
            "POST",
            "/api/chat/messages/stream",
            json={"message": "帮我调研证据链"},
        ) as response:
            body = "".join(response.iter_text())
        assert "event: intent" in body
        assert "event: done" in body
