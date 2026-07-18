"""Plugin registry — discover, validate, and look up plugins.

In v1alpha1 the registry loads plugins from:
1. Built-in plugins bundled with Conflux (explicit list)
2. User-specified directories (``--plugin-dir`` or ``CONFLUX_PLUGIN_DIRS``)

It never scans arbitrary Python files; every plugin must have a manifest.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from .contracts import CapabilitySpec, PluginManifest

logger = logging.getLogger(__name__)


class PluginRecord:
    """A loaded, validated plugin held by the registry."""

    def __init__(self, manifest: PluginManifest, instance: Any = None) -> None:
        self.manifest = manifest
        self.instance = instance  # Plugin instance (lazy or None)

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def capabilities(self) -> list[CapabilitySpec]:
        return self.manifest.capabilities

    def get_capability(self, capability_id: str) -> Any | None:
        """Return a callable capability or None."""
        if self.instance is None:
            return None
        return self.instance.get_capability(capability_id)


class PluginRegistry:
    """Central registry for all loaded plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginRecord] = {}
        self._capability_index: dict[str, PluginRecord] = {}
        self._disabled: set[str] = set()

    # ── registration ──────────────────────────────────────────

    def register(self, manifest: PluginManifest, instance: Any = None) -> PluginRecord:
        """Register a plugin by manifest.  Raises ValueError on conflict.

        Registration is atomic: all conflict checks run before any state is
        committed, so a failed register leaves the registry unchanged.
        """
        if manifest.id in self._plugins:
            raise ValueError(f"Plugin '{manifest.id}' is already registered")

        # Pre-check every capability for conflicts before committing.
        for cap in manifest.capabilities:
            if cap.id in self._capability_index:
                raise ValueError(
                    f"Capability '{cap.id}' conflicts with plugin "
                    f"'{self._capability_index[cap.id].id}'"
                )

        from ..sdk.manifest import validate_manifest

        manifest_issues = validate_manifest(manifest)
        if manifest_issues:
            raise ValueError("Invalid plugin manifest: " + "; ".join(manifest_issues))

        # All checks passed — commit.
        record = PluginRecord(manifest, instance)
        self._plugins[manifest.id] = record
        for cap in manifest.capabilities:
            self._capability_index[cap.id] = record

        logger.info("Registered plugin %s v%s (%d capabilities)", manifest.id, manifest.version, len(manifest.capabilities))
        return record

    def unregister(self, plugin_id: str) -> None:
        """Remove a plugin and its capabilities from the registry."""
        record = self._plugins.pop(plugin_id, None)
        if record is None:
            return
        for cap in record.capabilities:
            self._capability_index.pop(cap.id, None)
        self._disabled.discard(plugin_id)
        logger.info("Unregistered plugin %s", plugin_id)

    def disable(self, plugin_id: str) -> None:
        if plugin_id not in self._plugins:
            raise KeyError(f"Plugin '{plugin_id}' is not registered")
        self._disabled.add(plugin_id)

    def enable(self, plugin_id: str) -> None:
        if plugin_id not in self._plugins:
            raise KeyError(f"Plugin '{plugin_id}' is not registered")
        self._disabled.discard(plugin_id)

    def is_enabled(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins and plugin_id not in self._disabled

    # ── lookup ─────────────────────────────────────────────────

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._plugins.get(plugin_id)

    def get_capability(self, capability_id: str) -> PluginRecord | None:
        return self._capability_index.get(capability_id)

    def resolve_capability(
        self,
        capability_id: str,
        *,
        wrap: bool = True,
    ) -> Any | None:
        """Return a callable capability or None.

        When ``wrap=True`` (default), the callable is wrapped through
        ``execute_capability`` for exception handling and secret sanitisation.
        """
        record = self._capability_index.get(capability_id)
        if record is None:
            return None
        if not self.is_enabled(record.id):
            return None
        raw = record.get_capability(capability_id)
        if raw is None:
            return None
        if not wrap:
            return raw
        from .executor import execute_capability
        from functools import partial

        # Find the matching CapabilitySpec for metadata.
        cap_spec = None
        for c in record.capabilities:
            if c.id == capability_id:
                cap_spec = c
                break

        def wrapped(ctx, **inputs):
            return execute_capability(raw, ctx, capability_spec=cap_spec, **inputs)

        return wrapped

    def list_plugins(self, *, include_disabled: bool = False) -> list[PluginRecord]:
        if include_disabled:
            return list(self._plugins.values())
        return [record for record in self._plugins.values() if self.is_enabled(record.id)]

    def list_capabilities(self) -> list[str]:
        return list(self._capability_index.keys())

    def is_registered(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    @property
    def capability_count(self) -> int:
        return len(self._capability_index)


# ── singleton ──────────────────────────────────────────────────────

_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Return the process-wide singleton registry (lazy init)."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the singleton (for tests)."""
    global _registry
    _registry = None
