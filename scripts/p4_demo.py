#!/usr/bin/env python
"""P4.2 C 对话入口零成本演示剧本（无外部 API）。

剧本：种子论文 → 雷达（确认门）→ 入库 → 调研查询（SSE 流式）→ 周期周报。
全部经 FastAPI v2 真实路由（TestClient）+ 确定性 fake 模型/任务管理器，
展示意图路由、写操作门禁、token/进度流式多路复用与 OpenAPI 契约。

用法：python scripts/p4_demo.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

SEED_PAPERS = [
    {"title": "EvidenceLedger: auditable RAG verification for research reports", "arxiv_id": "seed-0001"},
    {"title": "Multi-model review panels reduce false verification in RAG pipelines", "arxiv_id": "seed-0002"},
    {"title": "Provenance replay for reproducible literature surveys", "arxiv_id": "seed-0003"},
]

DEMO_KNOWLEDGE: list[dict] = []


def _fake_manager():
    submitted: list[dict] = []

    class Manager:
        def submit(self, query, payload, *, run_id=None):
            submitted.append({"query": query, "payload": payload})
            return {
                "run_id": "demo-run-1",
                "status": "pending",
                "events_url": "/api/query/jobs/demo-run-1/events",
                "status_url": "/api/query/jobs/demo-run-1",
                "timeout_seconds": 300,
                "deadline_at": time.time() + 300,
                "commit_reserve_seconds": 20,
            }

        def events(self, run_id, *, after_id=0, limit=200):
            return [
                {"id": 1, "run_id": run_id, "status": "running", "stage": "retrieval"},
                {"id": 2, "run_id": run_id, "status": "running", "stage": "verification"},
                {"id": 3, "run_id": run_id, "status": "completed", "stage": "finalize"},
            ]

    manager = Manager()
    manager.submitted = submitted  # type: ignore[attr-defined]
    return manager


def _fake_radar_executor(store: list[dict]):
    def radar(diff: dict) -> dict:
        project_id = diff.get("project_id")
        for paper in SEED_PAPERS:
            store.append({**paper, "project_id": project_id, "ingested_via": "radar"})
        return {"ok": True, "job_id": "demo-radar-1", "ingested": len(SEED_PAPERS)}

    return radar


def _cycle_fixture() -> dict:
    return {
        "ok": True,
        "cycle_summary": {
            "real_progress": 2,
            "failed_experiments": 0,
            "risks": 1,
            "next_cycle_candidates": 2,
        },
    }


def header(text: str) -> None:
    print(f"\n=== {text} ===", flush=True)


def main() -> int:
    import importlib

    app_module = importlib.import_module("conflux.workbench.api_v2.app")
    manager = _fake_manager()
    store: list[dict] = []

    with (
        patch.object(app_module, "_get_classifier", lambda: None),
        patch("conflux.workbench.jobs.get_job_manager", lambda: manager),
        patch("conflux.workbench.server.build_p3_audit", lambda project_id: _cycle_fixture()),
    ):
        client = TestClient(app_module.create_app())

        header("1. 意图路由（规则表 → 动作白名单）")
        for line, expect in (
            ("跑一次论文雷达", "run_radar"),
            ("帮我调研证据链可追溯性", "research_query"),
            ("本周进展周报", "cycle_summary"),
        ):
            result = client.post("/api/chat/intent", json={"message": line}).json()
            print(f"  「{line}」→ {result['action']}（source={result['source']}）")
            assert result["action"] == expect, result

        header("2. 写操作门禁：雷达未经确认零执行")
        body = client.post(
            "/api/chat/messages",
            json={"message": "跑一次论文雷达", "project_id": "demo-project"},
        ).json()
        print(f"  回复：{body['reply']}")
        assert body["requires_approval"] is True
        assert store == []  # 零执行
        print(f"  知识库当前条目数：{len(store)}（确认前不落库）")

        header("3. 用户确认 → 种子论文入库")
        with patch(
            "conflux.workbench.api_v2.actions._WRITE_EXECUTORS",
            {"research.radar": _fake_radar_executor(store)},
        ):
            decided = client.post(
                f"/api/chat/approvals/{body['approval_id']}", json={"decision": "approved"}
            ).json()
        print(f"  审批结果：{json.dumps(decided, ensure_ascii=False)}")
        print(f"  入库论文：{', '.join(p['title'] for p in store)}")
        assert len(store) == len(SEED_PAPERS)

        header("4. 调研查询：复用既有 Job + SSE 流式（token/进度互不阻塞）")
        with client.stream(
            "POST",
            "/api/chat/messages/stream",
            json={"message": "帮我调研证据链可追溯性", "depth": "standard"},
        ) as response:
            frames = list(response.iter_text())
        events = [
            line for line in "".join(frames).splitlines()
            if line.startswith("event:")
        ]
        print("  SSE 事件序列：", " → ".join(events))
        assert "event: intent" in events
        assert "event: progress" in events
        assert "event: done" in events

        header("5. 周期周报（只读，复用 P3 审计）")
        body = client.post(
            "/api/chat/messages",
            json={"message": "本周进展周报", "project_id": "demo-project"},
        ).json()
        print(f"  回复：{body['reply']}")

        header("6. 白名单兜底：未命中规则且无模型 → 澄清（无幻觉执行）")
        body = client.post("/api/chat/messages", json={"message": "今天天气如何"}).json()
        print(f"  回复：{body['reply'][:80]}...")
        assert body["action"] == "clarify"

        header("7. OpenAPI 契约")
        paths = client.get("/openapi.json").json()["paths"]
        chat_paths = sorted(path for path in paths if path.startswith("/api/chat"))
        print("  /api/chat/* 路由：", ", ".join(chat_paths))
    print("\n剧本完成：零外部 API 调用，全确定性 fixture。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
