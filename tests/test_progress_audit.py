import json
import subprocess
import sys
from pathlib import Path

import pytest


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


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Conflux Test")
    _git(root, "config", "user.email", "test@example.com")
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "Initial baseline")
    return root


def test_git_snapshot_reads_branch_head_and_dirty_files(tmp_path):
    from conflux.progress_audit import create_project_snapshot

    root = _project(tmp_path)
    (root / "README.md").write_text("# Fixture\n\nChanged\n", encoding="utf-8")

    snapshot = create_project_snapshot(root, project_id="fixture")

    assert snapshot.git_branch
    assert snapshot.git_head == _git(root, "rev-parse", "HEAD")
    assert "README.md" in snapshot.dirty_files
    assert snapshot.recent_commits[0].subject == "Initial baseline"


def test_first_run_without_baseline_is_graceful(tmp_path):
    from conflux.progress_audit import audit_project

    report = audit_project(_project(tmp_path), project_id="fixture")

    assert report.baseline_status == "created"
    assert not report.real_progress
    assert "尚无历史基线" in report.weak_signals[0]
    assert report.snapshot is not None


def test_new_commit_and_artifact_are_real_progress_with_evidence(tmp_path):
    from conflux.progress_audit import audit_project, create_project_snapshot

    root = _project(tmp_path)
    baseline = create_project_snapshot(root, project_id="fixture")
    (root / "src").mkdir()
    (root / "src" / "method.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "src/method.py")
    _git(root, "commit", "-m", "Implement experiment method")
    (root / "results").mkdir()
    (root / "results" / "metrics.json").write_text('{"accuracy": 0.91}', encoding="utf-8")

    report = audit_project(
        root,
        baseline=baseline,
        test_command=[sys.executable, "-c", "print('tests passed')"],
    )

    summaries = [claim.summary for claim in report.real_progress]
    refs = [ref for claim in report.real_progress for ref in claim.evidence_refs]
    assert any("新增 1 个提交" in summary for summary in summaries)
    assert any("研究产物" in summary for summary in summaries)
    assert any(ref.startswith("git:") for ref in refs)
    assert "artifact:results/metrics.json" in refs
    assert report.evidence_refs == list(dict.fromkeys(refs))


def test_failing_test_and_dirty_worktree_become_risks(tmp_path):
    from conflux.progress_audit import audit_project, create_project_snapshot

    root = _project(tmp_path)
    baseline = create_project_snapshot(root)
    (root / "README.md").write_text("dirty\n", encoding="utf-8")

    report = audit_project(
        root,
        baseline=baseline,
        test_command=[sys.executable, "-c", "raise SystemExit(3)"],
    )

    assert any("未提交文件" in risk for risk in report.risks)
    assert any("测试命令失败" in risk for risk in report.risks)
    assert any("尚不能作为已完成进展" in signal for signal in report.weak_signals)


def test_test_inspector_does_not_leak_workbench_api_keys(tmp_path, monkeypatch):
    from conflux.progress_audit.test_inspector import inspect_tests

    root = _project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    result = inspect_tests(
        root,
        [
            sys.executable,
            "-c",
            "import os; raise SystemExit(1 if os.getenv('OPENAI_API_KEY') else 0)",
        ],
    )

    assert result.status == "passed"


def test_progress_claim_requires_evidence_refs():
    from conflux.progress_audit.models import ProgressClaim

    with pytest.raises(ValueError, match="evidence reference"):
        ProgressClaim(summary="Unverified progress", evidence_refs=[])


def test_progress_artifacts_persist_report_and_next_baseline(tmp_path):
    from conflux.progress_audit import audit_project, write_progress_artifacts

    report = audit_project(_project(tmp_path), project_id="fixture")
    artifacts = write_progress_artifacts(report, out_dir=tmp_path / "out")
    payload = json.loads(artifacts.json_path.read_text(encoding="utf-8"))
    markdown = artifacts.markdown_path.read_text(encoding="utf-8")

    assert payload["project_id"] == "fixture"
    assert artifacts.snapshot_path.exists()
    assert "# 项目进度审计：fixture" in markdown
    assert "首次基线" in markdown


def test_progress_audit_does_not_treat_its_own_reports_as_project_activity(tmp_path):
    from conflux.progress_audit import audit_project, create_project_snapshot, write_progress_artifacts

    root = _project(tmp_path)
    baseline = create_project_snapshot(root)
    first_report = audit_project(root, baseline=baseline)
    write_progress_artifacts(first_report, out_dir=root / "reports" / "workbench" / "progress" / "fixture")

    second_report = audit_project(root, baseline=first_report.snapshot)

    assert not any("progress_audit" in signal for signal in second_report.weak_signals)


def test_progress_cli_builds_snapshot_from_profile(tmp_path, capsys):
    from conflux.progress_audit.cli import main

    root = _project(tmp_path)
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "\n".join([
            "id: fixture-profile",
            "name: Fixture Profile",
            "fields: [cs.AI]",
            f"research_questions: [{json.dumps('What changed?')}]",
            f"keywords: [{json.dumps('progress audit')}]",
            f"project_paths: [{json.dumps(str(root))}]",
        ]),
        encoding="utf-8",
    )
    output = tmp_path / "reports"

    exit_code = main(["snapshot", "--profile", str(profile), "--out-dir", str(output)])
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed[0]["project_id"] == "fixture-profile"
    assert (output / "fixture-profile" / "project_snapshot.json").exists()
