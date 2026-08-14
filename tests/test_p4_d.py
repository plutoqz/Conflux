"""P4.3 D 实验追踪与导师周报测试（对照 D 设计 D1–D4 验收表）。

覆盖：D1 通用 schema（登记/幂等/状态/字段往返）、D2 数字可追溯
（检验器拒绝不可回溯数字与哈希）、D3 全链路闭环（实验→审计→周报数据块）、
D4 模型不可编造（故意缺失实验数据时周报不得出现未登记数字）、
三路采集（CLI 路径统一走 experiment_register；results*.json 扫描）、
对话登记确认门（写操作零执行）。
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import conflux.experiments as experiments_mod  # noqa: E402
from conflux.experiments import ExperimentRepository  # noqa: E402
from conflux.experiments import auto_scan_result_files  # noqa: E402
from conflux.mentor_report import (  # noqa: E402
    build_mentor_report,
    export_mentor_report_markdown,
    generate_mentor_report,
    validate_report_text,
)


class _DB:
    """内存 SQLite（row_factory=Row），schema 走 0010 migration 语句。"""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        for statement in experiments_mod.EXPERIMENT_STATEMENTS:
            self.connection.execute(statement)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


@pytest.fixture()
def repo():
    db = _DB()
    yield ExperimentRepository(db)
    db.close()


class TestRepository:
    def test_register_round_trip(self, repo):
        entry = repo.register(
            project_id="fusionagent001",
            name="对照实验 A",
            hypothesis="温度越低收敛越快",
            params={"lr": 1e-3},
            metrics={"acc": 0.912, "loss": "0.21"},
            status="done",
            commit_hash="a" * 40,
            source_ref="cli:exp-a",
        )
        assert entry["id"].startswith("exp-")
        assert entry["name"] == "对照实验 A"
        assert entry["status"] == "done"
        assert entry["metrics"]["acc"] == 0.912

    def test_register_idempotent_by_source_ref(self, repo):
        first = repo.register(project_id="p1", name="n1", source_ref="scan:x.json")
        second = repo.register(project_id="p1", name="n1", source_ref="scan:x.json")
        assert first["id"] == second["id"]
        assert repo.count("p1") == 1

    def test_status_bounds(self, repo):
        with pytest.raises(ValueError):
            repo.register(project_id="p1", name="bad", status="invalid")

    def test_list_period_includes_finish_window(self, repo):
        # created before period start, finished inside the period → included.
        repo.register(project_id="p1", name="early", source_ref="s-early")
        early = repo.list("p1")[0]
        repo.db.connection.execute(
            "UPDATE experiments SET created_at = ?, updated_at = ? WHERE id = ?",
            (10.0, 30.0, early["id"]),
        )
        repo.db.connection.commit()
        # in-period entry: created_at must be inside (20, 40].
        repo.register(project_id="p1", name="in-period", source_ref="s-in")
        in_entry = repo.list("p1", status=None)[0]
        repo.db.connection.execute(
            "UPDATE experiments SET created_at = ? WHERE id = ?",
            (25.0, in_entry["id"]),
        )
        repo.db.connection.commit()
        rows = repo.list_period("p1", start=20, end=40)
        names = {row["name"] for row in rows}
        assert "early" in names  # finished (updated_at) inside the window
        assert "in-period" in names
        names_out = {row["name"] for row in repo.list_period("p1", start=60, end=80)}
        assert "early" not in names_out

    def test_update_status_and_attach_metric(self, repo):
        entry = repo.register(project_id="p1", name="n", source_ref="s1")
        updated = repo.update_status(entry["id"], "failed")
        assert updated["status"] == "failed"
        with_metrics = repo.attach_metric(entry["id"], "f1", 0.5)
        assert with_metrics["metrics"]["f1"] == 0.5

    def test_unique_name_and_source_ref(self, repo):
        repo.register(project_id="p1", name="a", source_ref="x")
        repo.register(project_id="p1", name="a", source_ref="y")
        assert repo.count("p1") == 2


# ============================================================
# D1 采集路 2：results*.json 扫描（auto_scan_result_files）
# ============================================================


class _StubProject:
    id = "fusionagent001"
    path = ""
    result_dirs = ["results"]


def _scan_register(repo):
    """把 auto_scan_result_files 的登记入口替换为内存 repo 的 register。"""

    def register(project_id, name, hypothesis="", params=None, metrics=None,
                 status="draft", commit_hash="", source_ref=""):
        return repo.register(
            project_id=project_id,
            name=name,
            hypothesis=hypothesis,
            params=params,
            metrics=metrics,
            status=status,
            commit_hash=commit_hash,
            source_ref=source_ref,
        )

    return register


class TestScan:
    def test_scan_creates_experiment(self, tmp_path, repo, monkeypatch):
        results = tmp_path / "results"
        results.mkdir()
        (results / "results_r1.json").write_text(
            json.dumps({
                "name": "sweep-lr",
                "metrics": {"acc": 0.91, "loss": 0.201},
                "commit": "c" * 40,
                "status": "done",
            }),
            encoding="utf-8",
        )
        project = _StubProject()
        project.path = str(tmp_path)
        monkeypatch.setattr(experiments_mod, "experiment_register", _scan_register(repo))
        ids = auto_scan_result_files(project)
        assert len(ids) == 1
        rows = repo.list("fusionagent001")
        assert rows[0]["name"] == "sweep-lr"
        assert rows[0]["source_ref"] == "scan:results_r1.json"
        assert rows[0]["metrics"]["acc"] == 0.91

    def test_scan_ignores_malformed(self, tmp_path, repo, monkeypatch):
        results = tmp_path / "results"
        results.mkdir()
        (results / "results_bad.json").write_text('{"foo": 1}', encoding="utf-8")
        (results / "notes.txt").write_text("hello", encoding="utf-8")
        project = _StubProject()
        project.path = str(tmp_path)
        monkeypatch.setattr(experiments_mod, "experiment_register", _scan_register(repo))
        assert auto_scan_result_files(project) == []
        assert repo.count("fusionagent001") == 0


# ============================================================
# D2/D4 周报数字可追溯：校验器
# ============================================================


def test_validate_accepts_backed_numbers():
    data = {
        "data_block": "实验 A acc=0.912 loss=0.21\n提交 a1234b5678cdef00 完成",
        "experiments": [{"id": "exp-x", "metrics": {"acc": 0.912}}],
        "claims": [],
    }
    ok_report = "本周完成实验 A（acc=0.912，loss=0.21），提交 a1234b5678cdef00。"
    assert validate_report_text(ok_report, data) == []


def test_validate_rejects_fabricated_number():
    data = {
        "data_block": "实验 A acc=0.912",
        "experiments": [],
        "claims": [],
    }
    forged = "本周完成 87 项实验，提升 42%。"
    problems = validate_report_text(forged, data)
    assert any("87" in problem for problem in problems)
    assert any("42" in problem for problem in problems)


def test_validate_rejects_fabricated_hash():
    data = {
        "data_block": "提交 a1111111111111111111111111111111111111111",
        "experiments": [],
        "claims": [],
    }
    forged = "参考提交 b2222222222222222222222222222222222222222 的结论。"
    problems = validate_report_text(forged, data)
    assert any("b222" in p for p in problems)


# ============================================================
# D3/D4 全链路：实验 → 审计 → 周报数据块（确定性，无模型）
# ============================================================


class _MiniAudit:
    """周期审计数据的最小替身（避免 server/快照依赖）。"""

    ok = True
    project_id = "p1"
    baseline = {"revision": 0, "created_at": 0.0}
    current = {"revision": 1, "created_at": 100.0}
    period = "2026-08-01 至 2026-08-14"
    real_progress = []
    risks = []
    failed_experiments = []
    next_cycle_candidates = []


def test_build_mentor_report_uses_experiment_numbers(tmp_path, repo):
    repo.register(
        project_id="p1",
        name="基线回归",
        metrics={"acc": 0.912},
        status="done",
        commit_hash="d" * 40,
        source_ref="x1",
    )

    # 构造最小 intelligence：它的 db 就是内存库；build_cycle_audit 走不到（被替换）。
    class _Intel:
        db = repo.db

        class cycles:
            @staticmethod
            def latest_confirmed(project_id):
                return None

    class _Project:
        id = "p1"

    # 用最薄替身替换 audit 数据源，验证周报数据块携带 exp 引用。
    from conflux import mentor_report as mentor_mod

    original = mentor_mod.build_cycle_audit

    def fake_audit(intelligence, project, **kwargs):
        result = dict(_MiniAudit.__dict__)
        result["baseline"] = {"revision": 0, "created_at": 0.0}
        result["current"] = {"revision": 1, "created_at": time.time()}
        result["period"] = "2026-08-01 至 2026-08-14"
        result["real_progress"] = []
        result["risks"] = []
        result["failed_experiments"] = []
        result["next_cycle_candidates"] = []
        return result

    mentor_mod.build_cycle_audit = fake_audit
    try:
        data = build_mentor_report(_Intel(), _Project())
        block = data["data_block"]
        assert "acc=0.912" in block
        assert "<exp:" in block
        assert ("d" * 40) in block
    finally:
        mentor_mod.build_cycle_audit = original


def test_deterministic_fallback_contains_data_clearing():
    """D4 兜底：确定性回退报告必须原样携带数据清单（数字可追溯）。"""
    db = _DB()
    repo = ExperimentRepository(db)
    try:
        repo.register(
            project_id="p1",
            name="回退实验",
            metrics={"acc": 0.77},
            status="done",
            commit_hash="e" * 40,
            source_ref="fb1",
        )
        data = {
            "period": "2026-08-01 至 2026-08-14",
            "claims": [],
            "experiments": repo.list("p1"),
            "risks": [],
            "failed_experiments": [],
            "candidates": [],
            "data_block": "实验 回退实验 acc=0.77 <exp:exp-xxx>",
            "prompt": "",
        }
        report, problems = generate_mentor_report(data)
        assert problems == []
        assert "acc=0.77" in report
        assert "回退实验" in report
    finally:
        db.close()


# ============================================================
# D 导出：Markdown 幂等
# ============================================================


def test_export_mentor_report_markdown(tmp_path):
    artifacts = export_mentor_report_markdown(
        {"period": "2026-08-01 至 2026-08-14"},
        "# 导师周报草稿\n\n数据清单：``0.912``",
        out_dir=tmp_path,
    )
    md = Path(artifacts["markdown_path"])
    assert md.exists()
    assert "导师周报" in md.read_text(encoding="utf-8")
    assert Path(artifacts["json_path"]).exists()

# ============================================================
# 对话登记路（D 采集路 3）：experiment 动作走确认门；mentor_report 只读
# ============================================================

class TestChatActions:
    def test_experiment_action_requires_approval(self, monkeypatch):
        from conflux.workbench.api_v2 import actions
        from conflux.workbench.api_v2.schemas import ChatMessageRequest, IntentResult

        calls: list[dict] = []

        def fake_register(diff):
            calls.append(diff)
            return {"ok": True, "experiment": {"id": "exp-1"}}

        monkeypatch.setitem(actions._WRITE_EXECUTORS, "experiment.register", fake_register)
        intent = IntentResult(action="experiment", confidence=1.0, source="rules",
                              params={"name": "消融A"})
        response = actions.execute_intent(
            intent,
            ChatMessageRequest(message="登记实验 消融A", project_id="p1"),
        )
        assert response.requires_approval is True
        assert response.approval_id
        assert calls == []  # 未经确认零执行

        # 确认后执行
        result = actions.decide_approval(response.approval_id, "approved")
        assert result["executed"] is True
        assert calls[0]["project_id"] == "p1"
        assert calls[0]["name"] == "消融A"

    def test_mentor_report_read_only_without_project_clarifies(self, monkeypatch):
        from conflux.workbench.api_v2 import actions
        from conflux.workbench.api_v2.schemas import ChatMessageRequest, IntentResult

        intent = IntentResult(action="mentor_report", confidence=1.0, source="rules")
        response = actions.execute_intent(
            intent, ChatMessageRequest(message="生成周报")
        )
        assert response.action == "clarify"

    def test_experiment_without_project_clarifies(self, monkeypatch):
        from conflux.workbench.api_v2 import actions
        from conflux.workbench.api_v2.schemas import ChatMessageRequest, IntentResult

        intent = IntentResult(action="experiment", confidence=1.0, source="rules",
                              params={"name": "消融A"})
        response = actions.execute_intent(
            intent, ChatMessageRequest(message="登记实验")
        )
        assert response.action == "clarify"
