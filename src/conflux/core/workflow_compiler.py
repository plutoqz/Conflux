"""Workflow compiler (M2).

Compiles a ``WorkflowDefinition`` into an executable plan by resolving
every step's ``uses`` capability against the ``PluginRegistry``.

Supports:
- Validation: check all capabilities exist, schemas connect, budget/policy.
- Dry-run: print the execution plan without running anything.
- Text-graph preview: ASCII representation of the workflow topology.
"""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Any

from .contracts import (
    CapabilitySpec,
    PluginContext,
    RunContext,
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStepSpec,
)
from .policy import (
    check_budget,
    check_step_schema,
    check_workflow_steps,
    validate_workflow_inputs,
)
from .registry import PluginRegistry
from .executor import execute_capability

logger = logging.getLogger(__name__)


class CompilationIssue:
    """A single issue found during compilation."""
    def __init__(self, step_id: str, message: str, severity: str = "error") -> None:
        self.step_id = step_id
        self.message = message
        self.severity = severity  # error | warning

    def __str__(self) -> str:
        tag = "ERROR" if self.severity == "error" else "WARN"
        return f"[{tag}] step='{self.step_id}': {self.message}"


class CompilationResult:
    """The result of compiling a WorkflowDefinition."""
    def __init__(
        self,
        workflow: WorkflowDefinition,
        issues: list[CompilationIssue] | None = None,
        execution_order: list[str] | None = None,
        resolved_capabilities: dict[str, CapabilitySpec] | None = None,
    ) -> None:
        self.workflow = workflow
        self.issues = issues or []
        self.execution_order = execution_order or []
        self.resolved_capabilities = resolved_capabilities or {}

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def warnings(self) -> list[CompilationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def compile_workflow(
    workflow: WorkflowDefinition,
    registry: PluginRegistry | None = None,
    actual_inputs: dict[str, Any] | None = None,
) -> CompilationResult:
    """Compile a workflow definition into an executable plan.

    Args:
        workflow: The YAML-based workflow definition.
        registry: Plugin registry for capability resolution.
        actual_inputs: Optional runtime inputs for schema validation.

    Returns:
        ``CompilationResult`` with issues, execution order, and resolved caps.
    """
    from .registry import get_registry

    registry = registry or get_registry()
    issues: list[CompilationIssue] = []
    resolved: dict[str, CapabilitySpec] = {}
    order: list[str] = []
    seen_steps: set[str] = set()

    # 1. Check every step's capability exists.
    step_issues = check_workflow_steps(workflow, registry)
    for msg in step_issues:
        # Parse step id from message: "Step 'X' uses unknown capability..."
        sid = _extract_step_id(msg)
        issues.append(CompilationIssue(sid or "?", msg))

    # 2. Validate workflow inputs if provided.
    if actual_inputs is not None:
        input_issues = validate_workflow_inputs(workflow, actual_inputs)
        for msg in input_issues:
            issues.append(CompilationIssue("inputs", msg))

    # 3. Resolve each step and check schema connectivity.
    for step in workflow.steps:
        if step.id in seen_steps:
            issues.append(CompilationIssue(step.id, "Duplicate workflow step id"))
        seen_steps.add(step.id)
        order.append(step.id)

        if step.max_iterations > 1 and not step.stop_conditions:
            issues.append(CompilationIssue(
                step.id,
                "max_iterations > 1 requires at least one stop_condition",
            ))

        for reference in _step_references(step):
            root = reference.split(".", 1)[0]
            if root in workflow.inputs:
                continue
            if root not in seen_steps:
                issues.append(CompilationIssue(
                    step.id,
                    f"Input reference '{reference}' must point to a workflow input or prior step",
                ))

        record = registry.get_capability(step.uses)
        if record is None:
            issues.append(CompilationIssue(
                step.id,
                f"Capability '{step.uses}' not found in registry",
            ))
            continue

        # Find the matching CapabilitySpec.
        cap_spec = None
        for c in record.capabilities:
            if c.id == step.uses:
                cap_spec = c
                break

        if cap_spec is None:
            issues.append(CompilationIssue(
                step.id,
                f"Capability '{step.uses}' declared but not found in plugin {record.id}",
            ))
            continue

        resolved[step.id] = cap_spec

        if record.manifest.side_effects and not workflow.policies.get("approval_required"):
            issues.append(CompilationIssue(
                step.id,
                "Side-effecting capability requires workflow policy approval_required=true",
            ))

        # Check step schema.
        schema_issues = check_step_schema(step, cap_spec)
        for msg in schema_issues:
            severity = "warning" if "not installed" in msg else "error"
            issues.append(CompilationIssue(step.id, msg, severity))

    # 4. Check budget if declared.
    budget = workflow.policies.get("budget_token_limit")
    if budget and isinstance(budget, (int, float)):
        # Estimate tokens from steps config.
        estimated = _estimate_tokens(workflow)
        try:
            check_budget(estimated, int(budget))
        except Exception as e:
            issues.append(CompilationIssue("budget", str(e)))

    return CompilationResult(workflow, issues, order, resolved)


def execute_workflow(
    workflow: WorkflowDefinition,
    registry: PluginRegistry,
    inputs: dict[str, Any],
    ctx: PluginContext | None = None,
) -> dict[str, StepResult]:
    """Execute a validated linear workflow through the M1 capability boundary."""

    compilation = compile_workflow(workflow, registry, actual_inputs=inputs)
    if not compilation.is_valid:
        raise ValueError("Workflow is invalid: " + "; ".join(str(item) for item in compilation.issues))
    context = ctx or PluginContext(run=RunContext())
    values: dict[str, Any] = dict(inputs)
    results: dict[str, StepResult] = {}
    for step in workflow.steps:
        record = registry.get_capability(step.uses)
        capability = registry.resolve_capability(step.uses, wrap=False)
        if record is None or capability is None:
            raise ValueError(f"Capability '{step.uses}' is unavailable")
        kwargs = _resolve_value(step.config, values)
        for input_name, reference in step.inputs.items():
            kwargs[input_name] = _resolve_reference(reference, values)
        result = execute_capability(
            capability,
            context,
            capability_spec=next(c for c in record.capabilities if c.id == step.uses),
            **kwargs,
        )
        results[step.id] = result
        values[step.id] = result.output
        if result.status != StepStatus.SUCCESS:
            break
    return results


def dry_run_workflow(
    workflow: WorkflowDefinition,
    registry: PluginRegistry | None = None,
    inputs: dict[str, Any] | None = None,
) -> str:
    """Compile and produce a human-readable dry-run preview.

    Returns a formatted string suitable for display.
    """
    result = compile_workflow(workflow, registry, inputs)
    lines = [
        f"Workflow: {workflow.id} v{workflow.version}",
        f"Steps: {len(workflow.steps)}",
        f"Status: {'VALID' if result.is_valid else 'INVALID'}",
        "",
    ]

    if result.issues:
        lines.append("Issues:")
        for i in result.issues:
            lines.append(f"  {i}")
        lines.append("")

    if result.is_valid:
        lines.append("Execution order:")
        for sid in result.execution_order:
            cap = result.resolved_capabilities.get(sid)
            mode = cap.mode.value if cap else "?"
            lines.append(f"  {sid} → {cap.id if cap else '?'} [{mode}]")
        lines.append("")
        lines.append("(Dry-run: no capabilities executed)")

    return "\n".join(lines)


def workflow_text_graph(workflow: WorkflowDefinition) -> str:
    """Return an ASCII topology preview."""
    lines = [f"Workflow: {workflow.id}"]
    for i, step in enumerate(workflow.steps):
        connector = "├──" if i < len(workflow.steps) - 1 else "└──"
        lines.append(f"{connector} [{step.mode.value}] {step.id}")
        lines.append(f"    uses: {step.uses}")
    return "\n".join(lines)


# ── helpers ────────────────────────────────────────────────────────

def _extract_step_id(msg: str) -> str | None:
    """Try to extract step id from an issue message."""
    import re
    m = re.search(r"Step '(\S+)'", msg)
    return m.group(1) if m else None


def _estimate_tokens(workflow: WorkflowDefinition) -> int:
    """Rough token estimate from step configs."""
    total = 0
    for step in workflow.steps:
        cfg_str = str(step.config)
        total += len(cfg_str) // 2  # rough: 2 chars ≈ 1 token
    return max(total, 100)


_REFERENCE_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def _step_references(step: WorkflowStepSpec) -> list[str]:
    values = [*step.inputs.values(), *step.config.values()]
    references: list[str] = []
    for value in values:
        if isinstance(value, str):
            references.extend(match.group(1).strip() for match in _REFERENCE_PATTERN.finditer(value))
    return references


def _resolve_reference(reference: str, values: dict[str, Any]) -> Any:
    text = reference.strip()
    if text.startswith("{{") and text.endswith("}}"):
        text = text[2:-2].strip()
    current: Any = values
    for part in text.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def _resolve_value(value: Any, values: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_value(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, values) for item in value]
    if not isinstance(value, str):
        return value
    match = _REFERENCE_PATTERN.fullmatch(value.strip())
    if match:
        return _resolve_reference(match.group(1), values)
    return _REFERENCE_PATTERN.sub(
        lambda item: str(_resolve_reference(item.group(1), values) or ""), value
    )
