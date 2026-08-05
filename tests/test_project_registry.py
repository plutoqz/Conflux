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


def test_charter_draft_requires_confirmation_before_write(tmp_path, monkeypatch):
    from conflux.project_registry import ProjectDefinition, ProjectRegistry
    from conflux.workbench import server

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("# 研究项目\n\n研究知识图谱与大模型结合。\n", encoding="utf-8")
    registry = ProjectRegistry(tmp_path / "projects", base_dir=tmp_path)
    registry.save(ProjectDefinition(id="kg-llm", name="KG + LLM", path=str(root)))
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "_default_model_name", lambda preset: "test-model")
    monkeypatch.setattr(server, "_default_base_url", lambda preset: "https://example.invalid/v1")
    monkeypatch.setattr(server, "_default_api_key", lambda preset: "test-key")
    monkeypatch.setattr(server, "run_model_probe", lambda payload: {
        "ok": True,
        "model": "test-model",
        "content": "# KG + LLM 项目纲领\n\n## 项目定位与总体目标\n\n研究知识图谱与大模型结合。\n\n## 范围与非目标\n\n待确认。\n\n## 当前阶段\n\n待确认。\n\n## 里程碑与期望成果\n\n待确认。\n\n## 验收原则\n\n结果可复现。\n\n## 关键约束\n\n本地优先。\n\n## 证据与产物目录\n\n待确认。\n\n## 风险和已知问题\n\n待确认。\n\n## 后续方向\n\n待确认。",
    })

    generated = server.generate_project_charter({"project_id": "kg-llm"})

    assert generated["ok"] is True
    assert not (root / "PROJECT.md").exists()
    denied = server.apply_project_charter({
        "project_id": "kg-llm",
        "sha256": generated["draft"]["sha256"],
    })
    assert denied == {"ok": False, "error": "写入 PROJECT.md 前必须明确确认。"}

    applied = server.apply_project_charter({
        "project_id": "kg-llm",
        "confirmed": True,
        "sha256": generated["draft"]["sha256"],
        "content": generated["draft"]["content"],
    })

    assert applied["ok"] is True
    assert (root / "PROJECT.md").exists()
    saved = registry.get("kg-llm")
    assert saved is not None
    assert saved.document_files[0] == "PROJECT.md"
    assert saved.metadata["charter"]["approved_at"]


def test_llm_plan_analysis_is_preview_only_and_applies_confirmed_selection(tmp_path, monkeypatch):
    from conflux.project_registry import ProjectDefinition, ProjectPlan, ProjectRegistry
    from conflux.workbench import server

    root = tmp_path / "research"
    root.mkdir()
    docs = root / "docs"
    docs.mkdir()
    (docs / "historical.md").write_text("# 历史方案\n\n" + ("旧" * 200_000), encoding="utf-8")
    (root / "PROJECT.md").write_text(
        "# 项目纲领\n\n## 总体目标\n建立可复现的知识图谱增强生成研究流程。\n\n"
        "## 里程碑\n在统一数据集上完成基线比较并保存评估报告。\n",
        encoding="utf-8",
    )
    registry = ProjectRegistry(tmp_path / "projects", base_dir=tmp_path)
    registry.save(ProjectDefinition(
        id="kg-llm-plan",
        name="KG LLM Plan",
        path=str(root),
        document_dirs=["docs"],
        document_files=["PROJECT.md"],
        plan=ProjectPlan(source_documents=["PROJECT.md"]),
    ))
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "_default_model_name", lambda preset: "test-model")
    monkeypatch.setattr(server, "_default_base_url", lambda preset: "https://example.invalid/v1")
    monkeypatch.setattr(server, "_default_api_key", lambda preset: "test-key")
    calls = []

    def fake_probe(payload):
        calls.append(payload)
        return {
            "ok": True,
            "model": "test-model",
            "elapsed_ms": 1234,
            "usage": {"total_tokens": 4321},
            "content": json.dumps({
                "overall_goal": {
                    "summary": "建立可复现的知识图谱增强生成研究流程",
                    "source_refs": [{"path": "PROJECT.md", "line_start": 3, "line_end": 4}],
                },
                "items": [{
                    "type": "milestone",
                    "title": "完成统一数据集上的基线比较",
                    "summary": "比较主要基线并保存可复核评估报告。",
                    "acceptance_criteria": ["评估报告包含统一指标和实验配置"],
                    "criteria_origin": "suggested",
                    "declared_status": "planned",
                    "actual_status": "planned",
                    "source_refs": [{"path": "PROJECT.md", "line_start": 6, "line_end": 7}],
                    "evidence_refs": [],
                    "confidence": 0.84,
                    "rationale": "文档明确提出基线比较，但没有完成证据。",
                }],
                "warnings": [],
            }, ensure_ascii=False),
        }

    monkeypatch.setattr(server, "run_model_probe", fake_probe)

    preview = server.analyze_project_plan({"project_id": "kg-llm-plan"})

    assert preview["ok"] is True
    assert "PROJECT.md" in calls[0]["prompt"]
    assert "historical.md" not in calls[0]["prompt"]
    assert calls[0]["max_tokens"] == 12000
    assert calls[0]["timeout"] == 240
    assert preview["plan_context"]["warnings"] == []
    assert preview["analysis"]["analysis"]["elapsed_ms"] == 1234
    assert preview["analysis"]["analysis"]["usage"] == {"total_tokens": 4321}
    assert preview["analysis"]["analysis"]["document_count"] == 1
    unchanged = registry.get("kg-llm-plan")
    assert unchanged is not None
    assert unchanged.plan.overall_goal == ""
    assert unchanged.plan.milestones == []
    item_id = preview["analysis"]["items"][0]["id"]
    denied = server.apply_project_plan_analysis({
        "project_id": "kg-llm-plan",
        "generated_at": preview["analysis"]["analysis"]["generated_at"],
        "selection_ids": ["overall_goal", item_id],
    })
    assert denied == {"ok": False, "error": "写入计划前必须明确确认。"}

    applied = server.apply_project_plan_analysis({
        "project_id": "kg-llm-plan",
        "confirmed": True,
        "generated_at": preview["analysis"]["analysis"]["generated_at"],
        "selection_ids": ["overall_goal", item_id],
        "edits": {},
    })

    assert applied["ok"] is True
    saved = registry.get("kg-llm-plan")
    assert saved is not None
    assert saved.plan.overall_goal == "建立可复现的知识图谱增强生成研究流程"
    assert saved.plan.milestones[0].title == "完成统一数据集上的基线比较"
    assert saved.plan.milestones[0].deliverables == ["评估报告包含统一指标和实验配置"]


def test_plan_analysis_rate_limit_returns_actionable_reason(tmp_path, monkeypatch):
    from conflux.project_registry import ProjectDefinition, ProjectRegistry
    from conflux.workbench import server

    root = tmp_path / "research"
    root.mkdir()
    (root / "PROJECT.md").write_text("# 项目\n\n## 总体目标\n完成研究。\n", encoding="utf-8")
    ProjectRegistry(tmp_path / "projects", base_dir=tmp_path).save(
        ProjectDefinition(id="limited", name="Limited", path=str(root), document_files=["PROJECT.md"])
    )
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "_default_model_name", lambda preset: "test-model")
    monkeypatch.setattr(server, "_default_base_url", lambda preset: "https://example.invalid/v1")
    monkeypatch.setattr(server, "_default_api_key", lambda preset: "test-key")
    monkeypatch.setattr(server, "run_model_probe", lambda payload: {
        "ok": False,
        "status": 429,
        "error": '{"error":"rate_limit_exceeded"}',
    })

    result = server.analyze_project_plan({"project_id": "limited"})

    assert result["ok"] is False
    assert "请求过于频繁" in result["reason"]
    assert result["error"] == '{"error":"rate_limit_exceeded"}'


def test_plan_analysis_repairs_invalid_schema_once(tmp_path, monkeypatch):
    from conflux.project_registry import ProjectDefinition, ProjectRegistry
    from conflux.workbench import server

    root = tmp_path / "research"
    root.mkdir()
    (root / "PROJECT.md").write_text(
        "# 项目\n\n## 总体目标\n完成可复现研究。\n\n## 后续计划\n整理实验结果。\n",
        encoding="utf-8",
    )
    ProjectRegistry(tmp_path / "projects", base_dir=tmp_path).save(
        ProjectDefinition(id="repair", name="Repair", path=str(root), document_files=["PROJECT.md"])
    )
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "_default_model_name", lambda preset: "test-model")
    monkeypatch.setattr(server, "_default_base_url", lambda preset: "https://example.invalid/v1")
    monkeypatch.setattr(server, "_default_api_key", lambda preset: "test-key")
    responses = iter([
        {"ok": True, "model": "test-model", "content": '{"overall_goal": {"summary": "缺少来源"}, "items": []}'},
        {
            "ok": True,
            "model": "test-model",
            "content": json.dumps({
                "overall_goal": {
                    "summary": "完成可复现研究",
                    "source_refs": [{"path": "PROJECT.md", "line_start": 3, "line_end": 4}],
                },
                "items": [{
                    "type": "next_action",
                    "title": "整理并复核实验结果",
                    "summary": "汇总实验结果并检查可复现信息。",
                    "declared_status": "planned",
                    "actual_status": "planned",
                    "source_refs": [{"path": "PROJECT.md", "line_start": 6, "line_end": 7}],
                    "evidence_refs": [],
                    "confidence": 0.7,
                    "rationale": "文档列为后续计划。",
                }],
            }, ensure_ascii=False),
        },
    ])
    calls = []

    def fake_probe(payload):
        calls.append(payload)
        return next(responses)

    monkeypatch.setattr(server, "run_model_probe", fake_probe)

    result = server.analyze_project_plan({"project_id": "repair"})

    assert result["ok"] is True
    assert len(calls) == 2
    assert "上一次输出未通过校验" in calls[1]["prompt"]
    assert result["analysis"]["items"][0]["title"] == "整理并复核实验结果"


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


def test_workbench_project_overview_supports_document_only_directory(tmp_path, monkeypatch):
    from conflux.workbench import server

    research = tmp_path / "research"
    docs = research / "docs"
    docs.mkdir(parents=True)
    (docs / "notes.md").write_text("# Notes\n", encoding="utf-8")
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "notes.yaml").write_text(yaml.safe_dump({
        "id": "notes",
        "name": "Notes",
        "path": "research",
        "plan": {"overall_goal": "形成可复核的研究记录"},
        "refresh": {"mode": "manual", "schedule_enabled": False},
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    result = server.refresh_projects({"project_id": "notes"})
    overview = result["projects"][0]

    assert result["ok"] is True
    assert overview["repository"]["sync_status"] == "not_applicable"
    assert overview["repository"]["errors"] == []
    assert overview["documents"]["count"] == 1
    assert json.loads((tmp_path / "reports/workbench/projects/notes.json").read_text(encoding="utf-8"))["project"]["id"] == "notes"


def test_confirmed_plan_suggestion_updates_authoritative_project_yaml(tmp_path, monkeypatch):
    from conflux.workbench import server

    research = tmp_path / "research"
    research.mkdir()
    (research / "README.md").write_text(
        "## Research direction\n\nGoal: 建立知识图谱增强生成基线。\n",
        encoding="utf-8",
    )
    projects = tmp_path / "projects"
    projects.mkdir()
    config_path = projects / "kg-llm.yaml"
    config_path.write_text(yaml.safe_dump({
        "id": "kg-llm",
        "name": "KG LLM",
        "path": "research",
        "plan": {"overall_goal": "旧目标"},
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    suggestion = server.suggest_project_plan({"project_id": "kg-llm"})["suggestions"][0]

    result = server.apply_project_plan_suggestions({
        "project_id": "kg-llm",
        "selections": [{
            **suggestion,
            "title": "建立可复现的知识图谱增强生成基线。",
            "type": "overall_goal",
        }],
    })

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert result["applied"]["overall_goal"] == 1
    assert saved["plan"]["overall_goal"] == "建立可复现的知识图谱增强生成基线。"
    assert saved["plan"]["source_documents"] == ["README.md"]


def test_project_settings_update_preserves_plan_schedule_and_metadata(tmp_path, monkeypatch):
    from conflux.workbench import server

    research = tmp_path / "research"
    research.mkdir()
    projects = tmp_path / "projects"
    projects.mkdir()
    config_path = projects / "editable.yaml"
    config_path.write_text(yaml.safe_dump({
        "id": "editable",
        "name": "旧名称",
        "path": "research",
        "metadata": {"owner": "researcher"},
        "plan": {
            "overall_goal": "保留总体目标",
            "milestones": [{"id": "m1", "title": "保留阶段", "status": "in_progress"}],
        },
        "refresh": {
            "mode": "scheduled",
            "schedule_enabled": False,
            "interval_minutes": 180,
        },
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    result = server.update_registered_project_settings({
        "project_id": "editable",
        "name": "新名称",
        "path": str(research),
        "description": "新的项目说明",
        "test_command": "python -m pytest -q",
        "document_dirs": "docs\nnotes",
        "document_files": "README.md\nPLAN.md",
        "result_dirs": "results\nexperiments",
        "report_dirs": "reports",
    })

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert saved["name"] == "新名称"
    assert saved["plan"]["overall_goal"] == "保留总体目标"
    assert saved["plan"]["milestones"][0]["title"] == "保留阶段"
    assert saved["refresh"]["mode"] == "scheduled"
    assert saved["refresh"]["interval_minutes"] == 180
    assert saved["metadata"] == {"owner": "researcher"}
    assert saved["documents"]["directories"] == ["docs", "notes"]


def test_plan_suggestion_translation_preserves_original_for_review(monkeypatch):
    from conflux.workbench import server

    monkeypatch.setattr(server, "run_model_probe", lambda payload: {
        "ok": True,
        "content": json.dumps({
            "translations": [{"index": 0, "title": "建立可复现的知识图谱增强生成基线"}],
        }, ensure_ascii=False),
    })
    suggestions = [
        {"type": "overall_goal", "title": "Build a reproducible KG-augmented generation baseline."},
        {"type": "milestone", "title": "完成中文阶段目标"},
    ]

    translated, status = server._translate_plan_suggestions(suggestions)

    assert status == {"requested": True, "translated": 1, "error": ""}
    assert translated[0]["title"] == "建立可复现的知识图谱增强生成基线"
    assert translated[0]["original_title"] == suggestions[0]["title"]
    assert translated[1]["title"] == "完成中文阶段目标"


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
