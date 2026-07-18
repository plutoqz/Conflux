"""Manifest loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..core.contracts import ApiVersion, PluginManifest, WorkflowDefinition

SDK_VERSION = "0.1.0"


def load_manifest(path: str | Path) -> PluginManifest:
    """Load and validate a plugin manifest from a YAML file."""
    raw = _read_yaml(Path(path))
    manifest = PluginManifest.model_validate(raw)
    _validate_capability_ids(manifest)
    return manifest


def load_workflow(path: str | Path) -> WorkflowDefinition:
    """Load and validate a workflow definition from a YAML file."""
    raw = _read_yaml(Path(path))
    return WorkflowDefinition.model_validate(raw)


def validate_manifest(manifest: PluginManifest) -> list[str]:
    """Return a (possibly empty) list of validation issues.

    Checks:
    - Required fields (id, entrypoint, at least one capability)
    - Capability id prefixing
    - Entrypoint format (``module:variable``)
    - SDK compat range
    - Basic permission sanity (model:inference for agentic caps, etc.)
    """
    issues: list[str] = []
    if not manifest.id:
        issues.append("Manifest id is required")
    if not manifest.entrypoint:
        issues.append("Manifest entrypoint is required")
    elif ":" not in manifest.entrypoint:
        issues.append("Entrypoint must be 'module:variable' format")

    if not manifest.capabilities:
        issues.append("Manifest must declare at least one capability")

    # SDK compat check.
    if manifest.sdk_compat:
        if not manifest.sdk_compat.startswith(">=") and not manifest.sdk_compat.startswith("^"):
            issues.append(f"SDK compat '{manifest.sdk_compat}' should start with '>=' or '^'")
        elif not _sdk_compat_matches(manifest.sdk_compat):
            issues.append(f"SDK compat '{manifest.sdk_compat}' does not include SDK {SDK_VERSION}")

    # Permission sanity: agentic capability without model:inference is a warning.
    has_model_perm = any(p.value == "model:inference" for p in manifest.permissions)
    for cap in manifest.capabilities:
        issues.extend(_validate_capability_spec(cap, manifest.id))
        if cap.mode.value == "agentic" and not has_model_perm:
            issues.append(
                f"Capability '{cap.id}' is agentic but manifest lacks model:inference permission"
            )

    return issues


# ── internal helpers ──────────────────────────────────────────────

def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest at {path} must be a YAML mapping, got {type(raw).__name__}")
    return raw


def _validate_capability_ids(manifest: PluginManifest) -> None:
    """Ensure every capability id is prefixed by the plugin id."""
    for cap in manifest.capabilities:
        if not cap.id.startswith(manifest.id + "."):
            raise ValueError(
                f"Capability '{cap.id}' must be prefixed by plugin id '{manifest.id}'"
            )


def _validate_capability_spec(cap: Any, plugin_id: str) -> list[str]:
    issues: list[str] = []
    if not cap.id:
        issues.append(f"Capability in plugin '{plugin_id}' has no id")
    if not cap.id.startswith(plugin_id + "."):
        issues.append(f"Capability '{cap.id}' must be prefixed by '{plugin_id}'")
    return issues


def _sdk_compat_matches(spec: str) -> bool:
    try:
        operator = spec[:2] if spec[:2] in {">=", "^"} else ""
        required = _version_tuple(spec[2:].strip())
        current = _version_tuple(SDK_VERSION)
        if operator == ">=":
            return current >= required
        if operator == "^":
            return current[0] == required[0] and current >= required
    except ValueError:
        return False
    return False


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError(value)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]
