"""YAML persistence for the local project registry."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import ProjectDefinition, RegistryLoadResult


PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ProjectRegistry:
    def __init__(self, registry_dir: str | Path, *, base_dir: str | Path | None = None) -> None:
        self.registry_dir = Path(registry_dir).expanduser().resolve()
        self.base_dir = Path(base_dir or self.registry_dir.parent).expanduser().resolve()

    def load_all(self) -> RegistryLoadResult:
        result = RegistryLoadResult()
        if not self.registry_dir.exists():
            return result
        paths = sorted([*self.registry_dir.glob("*.yaml"), *self.registry_dir.glob("*.yml")])
        seen: set[str] = set()
        for path in paths:
            try:
                project = self._load_file(path)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                result.errors.append(f"{path.name}：{exc}")
                continue
            if project.id in seen:
                result.errors.append(f"{path.name}：项目 ID 重复：{project.id}")
                continue
            seen.add(project.id)
            result.projects.append(project)
        return result

    def get(self, project_id: str) -> ProjectDefinition | None:
        clean_id = _validate_project_id(project_id)
        for suffix in (".yaml", ".yml"):
            path = self.registry_dir / f"{clean_id}{suffix}"
            if path.exists():
                return self._load_file(path)
        return None

    def save(self, project: ProjectDefinition) -> Path:
        project.id = _validate_project_id(project.id)
        project.name = project.name.strip()
        if not project.name:
            raise ValueError("项目名称不能为空")
        if not project.path.strip():
            raise ValueError("项目路径不能为空")
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        output = self.registry_dir / f"{project.id}.yaml"
        payload = {"version": 1, **project.to_dict(include_source=False)}
        payload["path"] = self._portable_path(project.path)
        output.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        project.source_file = str(output)
        return output

    def _load_file(self, path: Path) -> ProjectDefinition:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("项目配置必须是 YAML 对象")
        project = ProjectDefinition.from_dict(payload)
        project.id = _validate_project_id(project.id or path.stem)
        if not project.name:
            raise ValueError("缺少项目名称")
        if not project.path:
            raise ValueError("缺少项目路径")
        project.path = str(self.resolve_project_path(project.path))
        project.source_file = str(path.resolve())
        return project

    def resolve_project_path(self, value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.base_dir / path
        return path.resolve()

    def _portable_path(self, value: str) -> str:
        resolved = self.resolve_project_path(value)
        try:
            relative = resolved.relative_to(self.base_dir)
        except ValueError:
            return str(resolved)
        text = relative.as_posix()
        return text or "."


def _validate_project_id(value: str) -> str:
    clean = str(value or "").strip().lower()
    if not PROJECT_ID_PATTERN.fullmatch(clean):
        raise ValueError("项目 ID 只能包含小写字母、数字和连字符，且最长 64 个字符")
    return clean
