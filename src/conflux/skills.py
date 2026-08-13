"""P4.0 A4 技能库：声明式技能（skills/*.yaml）→ 编译进 workflow_compiler。

- 技能 = 用户级声明式工作流；插件 = 代码级能力（M1 协议）。
- 触发召回：when.intent + when.tags；步骤白名单 tools；门禁 gates；
  输出契约 output.contract。
- to_workflow 把技能映射为 WorkflowDefinition（tool 名解析为注册 capability id），
  再经 compile_workflow 校验；未知 capability 如实报 issue，不静默降级。
- 内置种子技能 3 个：读论文笔记 / 周报草稿 / 实验可复现性检查。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILLS_DIR = PROJECT_ROOT / "skills"


@dataclass
class Skill:
    name: str
    description: str = ""
    when: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    gates: list[dict[str, Any]] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)
    version: str = "0.1.0"
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "when": self.when,
            "steps": self.steps,
            "tools": self.tools,
            "gates": self.gates,
            "output": self.output,
            "version": self.version,
        }


def _validate_skill(payload: dict[str, Any], source: str) -> tuple[Skill | None, list[str]]:
    problems: list[str] = []
    name = str(payload.get("name") or "").strip()
    if not name:
        problems.append(f"{source}: missing name")
    if not isinstance(payload.get("steps"), list) or not payload.get("steps"):
        problems.append(f"{source}: steps 必须为非空列表")
    if not isinstance(payload.get("tools"), list) or not payload.get("tools"):
        problems.append(f"{source}: tools 白名单必须为非空列表")
    whitelist = {str(tool) for tool in (payload.get("tools") or [])}
    for index, step in enumerate(payload.get("steps") or []):
        tool = str((step or {}).get("tool") or "")
        if tool not in whitelist:
            problems.append(f"{source}: step {index + 1} 的 tool {tool!r} 不在 tools 白名单内")
    if problems:
        return None, problems
    when = payload.get("when") or {}
    if not isinstance(when, dict):
        problems.append(f"{source}: when 必须为映射")
    if problems:
        return None, problems
    return Skill(
        name=name,
        description=str(payload.get("description") or "").strip(),
        when=when,
        steps=[dict(step) for step in payload.get("steps") or []],
        tools=[str(tool) for tool in payload.get("tools") or []],
        gates=[dict(gate) for gate in (payload.get("gates") or []) if isinstance(gate, dict)],
        output=payload.get("output") or {},
        version=str(payload.get("version") or "0.1.0"),
        source_path=str(source),
    ), []


class SkillLibrary:
    """加载/校验/匹配/编译 skills 目录下的声明式技能。"""

    def __init__(self, skills_dir: str | Path = DEFAULT_SKILLS_DIR) -> None:
        self.skills_dir = Path(skills_dir)

    def load(self) -> tuple[list[Skill], list[str]]:
        skills: list[Skill] = []
        problems: list[str] = []
        if not self.skills_dir.exists():
            return skills, [f"技能目录不存在：{self.skills_dir}"]
        for path in sorted(self.skills_dir.glob("*.yaml")) + sorted(self.skills_dir.glob("*.yml")):
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                problems.append(f"{path}: YAML 解析失败 {exc}")
                continue
            if not isinstance(payload, dict):
                problems.append(f"{path}: 顶层必须是映射")
                continue
            skill, issues = _validate_skill(payload, str(path))
            if skill is None:
                problems.extend(issues)
                continue
            if any(existing.name == skill.name for existing in skills):
                problems.append(f"{path}: 技能名重复 {skill.name}")
                continue
            skills.append(skill)
        return skills, problems

    def match(self, intent: str | None = None, tags: list[str] | None = None) -> list[Skill]:
        skills, _ = self.load()
        matches = []
        for skill in skills:
            when = skill.when or {}
            when_intent = str(when.get("intent") or "")
            when_tags = {str(tag) for tag in (when.get("tags") or [])}
            intent_ok = (not when_intent) or (intent == when_intent)
            tag_ok = (not when_tags) or (when_tags & set(tags or []))
            if intent_ok and tag_ok:
                matches.append(skill)
        return matches

    def to_workflow(self, skill: Skill, registry: Any | None = None) -> Any:
        """把技能映射为 WorkflowDefinition（tool → capability id）。"""

        import re

        from conflux.core.contracts import WorkflowDefinition, WorkflowStepSpec

        steps = []
        for index, step in enumerate(skill.steps, start=1):
            tool = str(step.get("tool") or "")
            steps.append(WorkflowStepSpec(
                id=f"{skill.name}.step{index}",
                uses=self._resolve_capability(tool, registry),
                mode=step.get("mode", "deterministic"),
                config=step.get("config") or {},
                inputs=step.get("inputs") or {},
            ))
        # 工作流输入名 = 步骤 config/inputs 中 {{root.key}} 引用的根名。
        root_refs: set[str] = set()
        for step in skill.steps:
            for value in [*(step.get("inputs") or {}).values(), *(step.get("config") or {}).values()]:
                for match in re.findall(r"\{\{([^}]+)\}\}", str(value)):
                    root_refs.add(match.split(".")[0])
        inputs = {
            name: {"type": "string", "required": True}
            for name in sorted(root_refs)
        }
        return WorkflowDefinition(
            id=f"skill.{skill.name}",
            version=skill.version,
            inputs=inputs,
            steps=steps,
            policies={
                "description": skill.description,
                "tools_whitelist": skill.tools,
                "gates": skill.gates,
                "output_contract": skill.output.get("contract", ""),
            },
        )

    def compile(self, skill: Skill, registry: Any | None = None) -> Any:
        from conflux.core.workflow_compiler import compile_workflow

        return compile_workflow(self.to_workflow(skill, registry), registry=registry)

    @staticmethod
    def _resolve_capability(tool: str, registry: Any | None) -> str:
        """tool → capability id：显式 builtin.* 原样用；否则在注册表里按后缀匹配。"""

        if tool.startswith("builtin."):
            return tool
        if registry is not None:
            candidates = getattr(registry, "_capability_index", {}) or {}
            for capability_id in candidates:
                if capability_id.endswith(f".{tool}") or capability_id == tool:
                    return capability_id
        return tool
