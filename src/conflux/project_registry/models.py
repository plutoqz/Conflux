"""Typed contracts for registered research projects and their plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MilestoneStatus = Literal["planned", "in_progress", "completed", "blocked"]
RefreshMode = Literal["manual", "scheduled"]


@dataclass(slots=True)
class Milestone:
    id: str
    title: str
    status: MilestoneStatus = "planned"
    description: str = ""
    planned_start: str = ""
    planned_end: str = ""
    deliverables: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Milestone":
        status = str(payload.get("status") or "planned")
        if status not in {"planned", "in_progress", "completed", "blocked"}:
            status = "planned"
        return cls(
            id=str(payload.get("id") or "").strip(),
            title=str(payload.get("title") or "").strip(),
            status=status,  # type: ignore[arg-type]
            description=str(payload.get("description") or "").strip(),
            planned_start=str(payload.get("planned_start") or "").strip(),
            planned_end=str(payload.get("planned_end") or "").strip(),
            deliverables=_string_list(payload.get("deliverables")),
        )


@dataclass(slots=True)
class ProjectPlan:
    overall_goal: str = ""
    milestones: list[Milestone] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    source_documents: list[str] = field(default_factory=list)
    updated_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectPlan":
        milestones = []
        for index, item in enumerate(payload.get("milestones") or [], start=1):
            if not isinstance(item, dict):
                continue
            milestone = Milestone.from_dict(item)
            if milestone.title:
                milestone.id = milestone.id or f"milestone-{index}"
                milestones.append(milestone)
        return cls(
            overall_goal=str(payload.get("overall_goal") or "").strip(),
            milestones=milestones,
            next_actions=_string_list(payload.get("next_actions")),
            source_documents=_string_list(payload.get("source_documents")),
            updated_at=str(payload.get("updated_at") or "").strip(),
        )


@dataclass(slots=True)
class RefreshPolicy:
    mode: RefreshMode = "manual"
    schedule_enabled: bool = False
    interval_minutes: int | None = None
    timezone: str = "Asia/Shanghai"
    last_refreshed_at: str = ""
    next_refresh_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RefreshPolicy":
        mode = str(payload.get("mode") or "manual")
        if mode not in {"manual", "scheduled"}:
            mode = "manual"
        interval = payload.get("interval_minutes")
        try:
            parsed_interval = max(1, int(interval)) if interval not in (None, "") else None
        except (TypeError, ValueError):
            parsed_interval = None
        return cls(
            mode=mode,  # type: ignore[arg-type]
            schedule_enabled=bool(payload.get("schedule_enabled", False)),
            interval_minutes=parsed_interval,
            timezone=str(payload.get("timezone") or "Asia/Shanghai").strip(),
            last_refreshed_at=str(payload.get("last_refreshed_at") or "").strip(),
            next_refresh_at=str(payload.get("next_refresh_at") or "").strip(),
        )


@dataclass(slots=True)
class ProjectDefinition:
    id: str
    name: str
    path: str
    description: str = ""
    enabled: bool = True
    document_dirs: list[str] = field(default_factory=lambda: ["docs"])
    document_files: list[str] = field(default_factory=lambda: ["README.md"])
    result_dirs: list[str] = field(default_factory=lambda: ["results", "artifacts", "experiments"])
    report_dirs: list[str] = field(default_factory=lambda: ["reports"])
    test_command: str = ""
    test_timeout_seconds: int = 120
    plan: ProjectPlan = field(default_factory=ProjectPlan)
    refresh: RefreshPolicy = field(default_factory=RefreshPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    research: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectDefinition":
        documents = payload.get("documents") or {}
        artifacts = payload.get("artifacts") or {}
        tests = payload.get("test") or {}
        try:
            timeout = max(1, min(3600, int(tests.get("timeout_seconds") or 120)))
        except (TypeError, ValueError):
            timeout = 120
        return cls(
            id=str(payload.get("id") or "").strip(),
            name=str(payload.get("name") or "").strip(),
            path=str(payload.get("path") or "").strip(),
            description=str(payload.get("description") or "").strip(),
            enabled=bool(payload.get("enabled", True)),
            document_dirs=_string_list(documents.get("directories")) or ["docs"],
            document_files=_string_list(documents.get("root_files")) or ["README.md"],
            result_dirs=_string_list(artifacts.get("result_dirs")) or ["results", "artifacts", "experiments"],
            report_dirs=_string_list(artifacts.get("report_dirs")) or ["reports"],
            test_command=str(tests.get("command") or "").strip(),
            test_timeout_seconds=timeout,
            plan=ProjectPlan.from_dict(payload.get("plan") or {}),
            refresh=RefreshPolicy.from_dict(payload.get("refresh") or {}),
            metadata=dict(payload.get("metadata") or {}),
            research=dict(payload.get("research")) if payload.get("research") else None,
        )

    def to_dict(self, *, include_source: bool = True) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "enabled": self.enabled,
            "documents": {
                "directories": list(self.document_dirs),
                "root_files": list(self.document_files),
            },
            "artifacts": {
                "result_dirs": list(self.result_dirs),
                "report_dirs": list(self.report_dirs),
            },
            "test": {
                "command": self.test_command,
                "timeout_seconds": self.test_timeout_seconds,
            },
            "plan": asdict(self.plan),
            "refresh": asdict(self.refresh),
            "metadata": dict(self.metadata),
        }
        if include_source:
            payload["source_file"] = self.source_file
        if self.research is not None:
            payload["research"] = dict(self.research)
        return payload


@dataclass(slots=True)
class RegistryLoadResult:
    projects: list[ProjectDefinition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    result = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
