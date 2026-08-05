"""Read-only Git inspection for local projects."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GitCommit


@dataclass(slots=True)
class GitInspection:
    is_repository: bool = False
    root: str = ""
    branch: str = ""
    head: str = ""
    tag: str = ""
    dirty_files: list[str] = field(default_factory=list)
    recent_commits: list[GitCommit] = field(default_factory=list)
    remote_name: str = ""
    remote_url: str = ""
    upstream: str = ""
    cached_remote_head: str = ""
    remote_default_branch: str = ""
    remote_branch: str = ""
    remote_head: str = ""
    ahead: int | None = None
    behind: int | None = None
    remote_checked: bool = False
    remote_tracking_stale: bool = False
    checked_at: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def sync_status(self) -> str:
        if not self.is_repository:
            return "not_applicable"
        if self.errors:
            return "error"
        if self.ahead is None or self.behind is None:
            return "unknown" if self.remote_name else "local_only"
        if self.ahead and self.behind:
            return "diverged"
        if self.behind:
            return "behind"
        if self.ahead:
            return "ahead"
        return "in_sync"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sync_status"] = self.sync_status
        return payload


def inspect_git(
    project_path: str | Path,
    *,
    max_commits: int = 20,
    check_remote: bool = False,
) -> GitInspection:
    root = Path(project_path).resolve()
    inspection = GitInspection(checked_at=datetime.now(timezone.utc).isoformat())
    try:
        top_level = _git(root, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and _is_not_repository(exc):
            return inspection
        inspection.errors.append(f"无法读取 Git 仓库：{_error_text(exc)}")
        return inspection

    inspection.is_repository = True
    inspection.root = top_level.strip()

    try:
        inspection.branch = _git(root, "branch", "--show-current").strip()
        inspection.head = _git(root, "rev-parse", "HEAD").strip()
        inspection.tag = _git_optional(root, "describe", "--tags", "--exact-match", "HEAD")
        status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
        inspection.dirty_files = [line[3:].strip() for line in status.splitlines() if len(line) >= 4]
        log = _git(
            root,
            "log",
            f"-{max(1, max_commits)}",
            "--format=%H%x1f%s%x1f%cI%x1e",
        )
        inspection.recent_commits = _parse_log(log)
        _inspect_tracking(root, inspection, check_remote=check_remote)
    except (OSError, subprocess.CalledProcessError) as exc:
        inspection.errors.append(f"Git 检查未完成：{_error_text(exc)}")
    return inspection


def inspect_git_status(project_path: str | Path) -> GitInspection:
    root = Path(project_path).resolve()
    inspection = GitInspection(checked_at=datetime.now(timezone.utc).isoformat())
    try:
        output = _git(root, "status", "--porcelain=v2", "--branch", "--untracked-files=all")
    except (OSError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and _is_not_repository(exc):
            return inspection
        inspection.errors.append(f"无法读取 Git 仓库：{_error_text(exc)}")
        return inspection

    inspection.is_repository = True
    inspection.root = str(root)
    for line in output.splitlines():
        if line.startswith("# branch.oid "):
            inspection.head = line.removeprefix("# branch.oid ").strip()
        elif line.startswith("# branch.head "):
            inspection.branch = line.removeprefix("# branch.head ").strip()
        elif line.startswith("# branch.upstream "):
            inspection.upstream = line.removeprefix("# branch.upstream ").strip()
            inspection.remote_name = inspection.upstream.split("/", 1)[0]
        elif line.startswith("# branch.ab "):
            ahead, behind = line.removeprefix("# branch.ab ").split()
            inspection.ahead = int(ahead.removeprefix("+"))
            inspection.behind = int(behind.removeprefix("-"))
        elif line.startswith("? "):
            inspection.dirty_files.append(line[2:].strip())
        elif line.startswith("1 "):
            inspection.dirty_files.append(line.split(" ", 8)[8].strip())
        elif line.startswith("2 "):
            inspection.dirty_files.append(line.split(" ", 9)[9].split("\t", 1)[0].strip())
        elif line.startswith("u "):
            inspection.dirty_files.append(line.split(" ", 10)[10].strip())
    return inspection


def _inspect_tracking(root: Path, inspection: GitInspection, *, check_remote: bool) -> None:
    if not inspection.branch:
        inspection.warnings.append("当前处于 detached HEAD，无法比较同名远程分支。")
    inspection.remote_name = _git_optional(root, "config", f"branch.{inspection.branch}.remote")
    if not inspection.remote_name:
        inspection.remote_name = _first_line(_git_optional(root, "remote"))
    if not inspection.remote_name:
        return

    inspection.remote_url = _git_optional(root, "remote", "get-url", inspection.remote_name)
    inspection.upstream = _git_optional(
        root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )
    if inspection.upstream:
        inspection.cached_remote_head = _git_optional(root, "rev-parse", inspection.upstream)
        counts = _git_optional(root, "rev-list", "--left-right", "--count", f"HEAD...{inspection.upstream}")
        inspection.ahead, inspection.behind = _parse_counts(counts)

    if not check_remote:
        return
    inspection.remote_checked = True
    try:
        head_output = _git(root, "ls-remote", "--symref", inspection.remote_name, "HEAD")
        inspection.remote_default_branch = _parse_default_branch(head_output)
        if inspection.branch:
            branch_output = _git(
                root,
                "ls-remote",
                "--heads",
                inspection.remote_name,
                f"refs/heads/{inspection.branch}",
            )
            inspection.remote_branch = inspection.branch
            inspection.remote_head = _parse_remote_head(branch_output)
    except (OSError, subprocess.CalledProcessError) as exc:
        inspection.warnings.append(f"无法读取远程仓库版本：{_error_text(exc)}")
        return

    if not inspection.branch:
        return
    if not inspection.remote_head:
        inspection.warnings.append(f"远程仓库没有分支 {inspection.branch}。")
        inspection.ahead = None
        inspection.behind = None
        return
    if inspection.remote_head == inspection.head:
        inspection.ahead = 0
        inspection.behind = 0
        return
    if inspection.remote_head == inspection.cached_remote_head:
        return
    inspection.remote_tracking_stale = True
    if not _git_succeeds(root, "cat-file", "-e", f"{inspection.remote_head}^{{commit}}"):
        inspection.ahead = None
        inspection.behind = None
        inspection.warnings.append(
            "远程分支已有本地未获取的版本；为保持只读监控，本次未执行 git fetch。"
        )
        return
    counts = _git_optional(root, "rev-list", "--left-right", "--count", f"HEAD...{inspection.remote_head}")
    inspection.ahead, inspection.behind = _parse_counts(counts)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
        timeout=15,
    )
    return result.stdout


def _git_optional(root: Path, *args: str) -> str:
    try:
        return _git(root, *args).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _git_succeeds(root: Path, *args: str) -> bool:
    try:
        _git(root, *args)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _parse_log(value: str) -> list[GitCommit]:
    commits = []
    for record in value.split("\x1e"):
        fields = record.strip().split("\x1f")
        if len(fields) >= 2 and fields[0]:
            commits.append(GitCommit(
                sha=fields[0],
                subject=fields[1],
                committed_at=fields[2] if len(fields) > 2 else "",
            ))
    return commits


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return str(exc.stderr or exc.stdout or exc).strip()
    return str(exc)


def _is_not_repository(exc: subprocess.CalledProcessError) -> bool:
    text = _error_text(exc).casefold()
    return "not a git repository" in text or "不是 git 仓库" in text


def _first_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "")


def _parse_counts(value: str) -> tuple[int | None, int | None]:
    fields = value.replace("\t", " ").split()
    if len(fields) < 2:
        return None, None
    try:
        return int(fields[0]), int(fields[1])
    except ValueError:
        return None, None


def _parse_default_branch(value: str) -> str:
    for line in value.splitlines():
        if line.startswith("ref:") and line.rstrip().endswith("\tHEAD"):
            ref = line.split("\t", 1)[0].removeprefix("ref:").strip()
            return ref.removeprefix("refs/heads/")
    return ""


def _parse_remote_head(value: str) -> str:
    line = _first_line(value)
    return line.split()[0] if line else ""
