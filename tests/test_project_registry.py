import json
import subprocess
from pathlib import Path

import yaml


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def test_registry_round_trip_preserves_plan_and_schedule_fields(tmp_path):
    from conflux.project_registry import Milestone, ProjectDefinition, ProjectPlan, ProjectRegistry, RefreshPolicy

    project_root = tmp_path / "research"
    project_root.mkdir()
    registry = ProjectRegistry(tmp_path / "projects", base_dir=tmp_path)
    project = ProjectDefinition(
        id="research-one",
        name="Research One",
        path=str(project_root),
        plan=ProjectPlan(
            overall_goal="验证知识图谱与大模型结合方法",
            milestones=[Milestone(id="m1", title="完成基线实验", status="in_progress")],
            next_actions=["复现实验"],
        ),
        refresh=RefreshPolicy(
            mode="manual",
            schedule_enabled=False,
            interval_minutes=60,
            timezone="Asia/Shanghai",
        ),
    )

    saved_path = registry.save(project)
    loaded = registry.get("research-one")

    assert loaded is not None
    assert loaded.path == str(project_root.resolve())
    assert loaded.plan.overall_goal == "验证知识图谱与大模型结合方法"
    assert loaded.plan.milestones[0].status == "in_progress"
    assert loaded.refresh.interval_minutes == 60
    assert yaml.safe_load(saved_path.read_text(encoding="utf-8"))["path"] == "research"


def test_non_git_research_directory_is_not_an_audit_error(tmp_path):
    from conflux.progress_audit import audit_project

    root = tmp_path / "research"
    (root / "experiments").mkdir(parents=True)
    (root / "experiments" / "metrics.csv").write_text("score\n0.91\n", encoding="utf-8")

    report = audit_project(root, project_id="research-only")

    assert report.snapshot is not None
    assert report.snapshot.git_available is False
    assert report.snapshot.errors == []
    assert not any("Git" in risk for risk in report.risks)
    assert report.snapshot.result_files[0].path == "experiments/metrics.csv"


def test_plan_document_discovery_prefers_project_charter_case_insensitively(tmp_path):
    from conflux.project_registry import ProjectDefinition, discover_plan_documents

    root = tmp_path / "research"
    root.mkdir()
    (root / "project.MD").write_text("# 项目纲领\n\n总体目标：完成可复现实验。\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# 智能体说明\n", encoding="utf-8")
    (root / "README.md").write_text("# 说明\n", encoding="utf-8")
    project = ProjectDefinition(id="charter", name="Charter", path=str(root))

    context = discover_plan_documents(project)

    assert context["charter"]["path"] == "project.MD"
    assert context["charter"]["kind"] == "project.MD"
    assert context["documents"][0]["kind"] == "charter"
    assert context["documents"][0]["content"].startswith("# 项目纲领")


def test_plan_document_discovery_finds_architecture_charter_in_configured_docs(tmp_path):
    from conflux.project_registry import ProjectDefinition, discover_plan_documents

    root = tmp_path / "research"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "architecture.md").write_text("# 研究项目蓝图\n", encoding="utf-8")
    project = ProjectDefinition(id="blueprint", name="Blueprint", path=str(root), document_dirs=["docs"])

    context = discover_plan_documents(project)

    assert context["charter"]["status"] == "available"
    assert context["charter"]["path"] == "docs/architecture.md"


def test_plan_analysis_filters_noise_and_gates_completed_evidence():
    from conflux.project_registry import normalize_plan_analysis

    context = {
        "charter": {"status": "available", "path": "PROJECT.md"},
        "documents": [{
            "path": "PROJECT.md",
            "line_count": 40,
            "sha256": "doc-hash",
            "content": "# 项目",
        }],
        "warnings": [],
    }
    evidence = [
        {"ref": "code:src/models.py", "kind": "code", "label": "代码"},
        {"ref": "artifact:results/metrics.csv", "kind": "artifact", "label": "实验结果"},
    ]
    payload = {
        "overall_goal": {
            "summary": "建立知识图谱与大模型结合的可复现研究流程",
            "source_refs": [{"path": "PROJECT.md", "line_start": 2, "line_end": 4}],
        },
        "items": [
            {
                "type": "milestone",
                "title": "添加 `src/models.py`",
                "summary": "实现一个文件",
                "source_refs": [{"path": "PROJECT.md", "line_start": 5}],
            },
            {
                "type": "milestone",
                "title": "完成知识图谱增强生成基线评估",
                "summary": "在统一数据集上比较可复现基线。",
                "declared_status": "completed",
                "actual_status": "completed",
                "source_refs": [{"path": "PROJECT.md", "line_start": 8}],
                "evidence_refs": ["code:src/models.py"],
                "confidence": 0.8,
            },
            {
                "type": "next_action",
                "title": "完成消融实验并记录关键指标",
                "summary": "验证知识图谱证据对回答质量的影响。",
                "actual_status": "completed",
                "source_refs": [{"path": "PROJECT.md", "line_start": 12}],
                "evidence_refs": ["artifact:results/metrics.csv"],
                "confidence": 0.9,
            },
        ],
    }

    analysis = normalize_plan_analysis(payload, context=context, evidence=evidence, model="test-model")

    assert [item["title"] for item in analysis["items"]] == [
        "完成知识图谱增强生成基线评估",
        "完成消融实验并记录关键指标",
    ]
    assert analysis["items"][0]["actual_status"] == "needs_review"
    assert analysis["items"][1]["actual_status"] == "completed"
    assert any("已过滤" in warning for warning in analysis["analysis"]["warnings"])
    assert any("降级" in warning for warning in analysis["analysis"]["warnings"])


def test_remote_monitoring_does_not_update_tracking_refs(tmp_path):
    from conflux.progress_audit.git_inspector import inspect_git

    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(remote, "init", "--bare")
    local = tmp_path / "local"
    local.mkdir()
    _git(local, "init")
    _git(local, "config", "user.name", "Monitor Test")
    _git(local, "config", "user.email", "monitor@example.com")
    (local / "README.md").write_text("# Local\n", encoding="utf-8")
    _git(local, "add", "README.md")
    _git(local, "commit", "-m", "Initial")
    _git(local, "branch", "-M", "main")
    _git(local, "remote", "add", "origin", str(remote))
    _git(local, "push", "-u", "origin", "main")
    _git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", str(remote), str(other)],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    _git(other, "config", "user.name", "Remote Test")
    _git(other, "config", "user.email", "remote@example.com")
    (other / "remote.txt").write_text("remote\n", encoding="utf-8")
    _git(other, "add", "remote.txt")
    _git(other, "commit", "-m", "Remote change")
    _git(other, "push", "origin", "main")

    tracking_before = _git(local, "rev-parse", "refs/remotes/origin/main")
    inspection = inspect_git(local, check_remote=True)
    tracking_after = _git(local, "rev-parse", "refs/remotes/origin/main")

    assert inspection.remote_checked is True
    assert inspection.remote_head != inspection.head
    assert inspection.remote_tracking_stale is True
    assert inspection.ahead is None and inspection.behind is None
    assert any("未执行 git fetch" in warning for warning in inspection.warnings)
    assert tracking_after == tracking_before


def test_plan_extraction_returns_pending_candidates_without_writing_config(tmp_path):
    from conflux.project_registry import ProjectDefinition, ProjectPlan, extract_plan_suggestions

    root = tmp_path / "research"
    docs = root / "docs"
    docs.mkdir(parents=True)
    plan_path = docs / "PLAN.md"
    plan_path.write_text(
        "# 研究目标\n\n- 构建知识图谱增强的大模型问答方法\n\n"
        "## 阶段计划\n\n- 完成消融实验\n\n## 下一步\n\n- 整理实验数据\n",
        encoding="utf-8",
    )
    project = ProjectDefinition(
        id="kg-llm",
        name="KG + LLM",
        path=str(root),
        plan=ProjectPlan(source_documents=["docs/PLAN.md"]),
    )
    before = plan_path.read_text(encoding="utf-8")

    suggestions = extract_plan_suggestions(project)

    assert {item["type"] for item in suggestions} >= {"overall_goal", "milestone", "next_action"}
    assert all(item["status"] == "pending_confirmation" for item in suggestions)
    assert all(item["source_path"] == "docs/PLAN.md" for item in suggestions)
    assert plan_path.read_text(encoding="utf-8") == before


def test_plan_extraction_excludes_non_goals_and_reads_inline_goal(tmp_path):
    from conflux.project_registry import ProjectDefinition, extract_plan_suggestions

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text(
        "## Direction\n\nGoal: 建立可复现的知识图谱增强生成基线。\n\n"
        "## Non-Goals\n\n- 自动撰写整篇论文\n",
        encoding="utf-8",
    )
    project = ProjectDefinition(id="inline-goal", name="Inline goal", path=str(root))

    suggestions = extract_plan_suggestions(project)

    assert [item["title"] for item in suggestions] == ["建立可复现的知识图谱增强生成基线。"]
    assert suggestions[0]["type"] == "overall_goal"


def test_project_monitor_counts_readable_reports_not_runtime_noise(tmp_path):
    from conflux.project_registry import ProjectDefinition, monitor_project

    root = tmp_path / "research"
    reports = root / "reports"
    (reports / "test_run").mkdir(parents=True)
    (reports / "final.md").write_text("# Final\n", encoding="utf-8")
    (reports / "weekly_summary.json").write_text("{}", encoding="utf-8")
    (reports / "workbench-server.log").write_text("runtime", encoding="utf-8")
    (reports / "test_run" / "fixture.md").write_text("# Fixture\n", encoding="utf-8")
    project = ProjectDefinition(id="reports", name="Reports", path=str(root))

    overview = monitor_project(project, audit_root=tmp_path / "audit")

    assert overview["reports"]["count"] == 1
    assert {item["path"] for item in overview["reports"]["recent_files"]} == {
        "reports/final.md",
    }
