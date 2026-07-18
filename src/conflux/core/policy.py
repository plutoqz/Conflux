"""Policy enforcement for plugin execution.

In v1alpha1, permissions are validated and audited but NOT enforced as
a sandbox — plugins run in-process and are trusted.

Policy checks cover:
- Permission declarations match requested capabilities
- Budget limits
- Schema compatibility between workflow steps
"""

from __future__ import annotations

import logging
from typing import Any

from .contracts import (
    CapabilitySpec,
    PluginPermission,
    WorkflowDefinition,
    WorkflowStepSpec,
)
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PolicyViolation(Exception):
    """Raised when a policy check fails."""
    def __init__(self, message: str, *, plugin_id: str = "", detail: str = "") -> None:
        super().__init__(message)
        self.plugin_id = plugin_id
        self.detail = detail


def check_permissions(
    required: list[PluginPermission],
    declared: list[PluginPermission],
    plugin_id: str = "",
) -> None:
    """Raise PolicyViolation if any required permission is not declared."""
    declared_set = set(declared)
    missing = [p for p in required if p not in declared_set]
    if missing:
        names = ", ".join(p.value for p in missing)
        raise PolicyViolation(
            f"Plugin '{plugin_id}' requires permissions [{names}] not declared in manifest",
            plugin_id=plugin_id,
            detail=f"Declared: {[p.value for p in declared]}",
        )


def check_workflow_steps(
    workflow: WorkflowDefinition,
    registry: PluginRegistry | None = None,
) -> list[str]:
    """Validate that every step's ``uses`` capability is registered.

    Returns a list of issues (empty = valid).
    """
    issues: list[str] = []
    for step in workflow.steps:
        if registry is not None and not registry.get_capability(step.uses):
            issues.append(
                f"Step '{step.id}' uses unknown capability '{step.uses}'"
            )
    return issues


def check_step_schema(
    step: WorkflowStepSpec,
    capability: CapabilitySpec | None,
) -> list[str]:
    """Check that step inputs match capability input schema.

    Runs real JSON Schema validation when ``jsonschema`` is installed.
    Returns a list of issues (empty = valid).
    """
    issues: list[str] = []
    if capability is None:
        return issues  # unknown capability handled elsewhere

    input_schema = capability.input_schema
    if not input_schema:
        return issues

    # Required-field mapping check (lightweight, always runs).
    required_inputs = input_schema.get("required", []) if isinstance(input_schema, dict) else []
    for req in required_inputs:
        if req not in step.inputs and req not in step.config:
            issues.append(
                f"Step '{step.id}': required input '{req}' is not mapped"
            )

    # Full JSON Schema validation (if jsonschema is available).
    # Only validate when all required fields are present in config
    # (mapped inputs from prior steps are not yet available at compile time).
    try:
        import jsonschema
        instance = dict(step.config)
        # Skip full validation if required fields are mapped via step.inputs
        # rather than provided as literal config values.
        missing_from_config = [r for r in required_inputs if r not in instance]
        if not missing_from_config:
            validator = jsonschema.Draft202012Validator(input_schema)
            errs = sorted(validator.iter_errors(instance), key=lambda e: e.path)
            for err in errs:
                issues.append(f"Step '{step.id}': {err.message} at {'/'.join(map(str, err.path))}")
    except ImportError:
        pass  # jsonschema not installed — field-mapping check is enough
    except Exception as exc:
        # Catches SchemaError, RefResolutionError, etc.
        issues.append(f"Step '{step.id}': invalid schema — {exc}")

    return issues


def validate_output(
    output: dict[str, Any],
    output_schema: dict[str, Any],
) -> list[str]:
    """Validate a capability output against its declared JSON Schema.

    Returns a list of issues (empty = valid).
    """
    issues: list[str] = []
    if not output_schema:
        return issues
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(output_schema)
        errs = sorted(validator.iter_errors(output), key=lambda e: e.path)
        for err in errs:
            issues.append(f"Output: {err.message} at {'/'.join(map(str, err.path))}")
    except ImportError:
        pass
    except Exception as exc:
        issues.append(f"Output: invalid output schema — {exc}")
    return issues


def validate_capability_input(
    inputs: dict[str, Any],
    input_schema: dict[str, Any],
) -> list[str]:
    """Validate concrete capability inputs against their JSON Schema."""

    if not input_schema:
        return []
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(input_schema)
        return [
            f"Input: {error.message} at {'/'.join(map(str, error.path))}"
            for error in sorted(validator.iter_errors(inputs), key=lambda item: item.path)
        ]
    except ImportError:
        required = input_schema.get("required", [])
        return [f"Missing required input: '{name}'" for name in required if name not in inputs]
    except Exception as exc:
        return [f"Input: invalid input schema - {exc}"]


def validate_workflow_inputs(
    workflow: WorkflowDefinition,
    actual_inputs: dict[str, Any],
) -> list[str]:
    """Validate actual inputs against the workflow's declared input schema.

    Returns a list of issues (empty = valid).
    """
    issues: list[str] = []
    if not workflow.inputs:
        return issues
    try:
        import jsonschema
        # Build a JSON Schema from the workflow input declarations.
        schema = {
            "type": "object",
            "properties": {
                name: {"type": spec.get("type", "string")}
                for name, spec in workflow.inputs.items()
            },
            "required": [
                name for name, spec in workflow.inputs.items()
                if spec.get("required", False)
            ],
        }
        validator = jsonschema.Draft202012Validator(schema)
        errs = sorted(validator.iter_errors(actual_inputs), key=lambda e: e.path)
        for err in errs:
            issues.append(f"Workflow input: {err.message} at {'/'.join(map(str, err.path))}")
    except ImportError:
        # Fallback: just check required fields exist.
        for name, spec in workflow.inputs.items():
            if spec.get("required") and name not in actual_inputs:
                issues.append(f"Missing required input: '{name}'")
    return issues


def check_budget(
    estimated_tokens: int,
    budget_limit: int | None,
) -> None:
    """Raise PolicyViolation if estimated tokens exceed budget."""
    if budget_limit is not None and estimated_tokens > budget_limit:
        raise PolicyViolation(
            f"Estimated {estimated_tokens} tokens exceeds budget of {budget_limit}",
            detail=f"Budget limit: {budget_limit}",
        )
