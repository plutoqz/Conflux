"""Plugin loader — discover plugins from entry points and directories.

Loads plugins into the singleton ``PluginRegistry``.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

from ..core.contracts import PluginManifest
from ..core.registry import PluginRegistry, get_registry
from ..sdk.manifest import load_manifest, validate_manifest

logger = logging.getLogger(__name__)


def load_plugins_from_dirs(
    dirs: list[str | Path],
    registry: PluginRegistry | None = None,
) -> PluginRegistry:
    """Scan explicit directories for manifest files and load plugins.

    Each directory is scanned for ``plugin.yaml`` or ``manifest.yaml``.
    """
    registry = registry or get_registry()
    for d in dirs:
        dpath = Path(d).expanduser().resolve()
        if not dpath.is_dir():
            logger.warning("Plugin dir not found: %s", dpath)
            continue
        for manifest_path in sorted(dpath.glob("**/manifest.yaml")):
            _load_one(manifest_path, registry)
        for manifest_path in sorted(dpath.glob("**/plugin.yaml")):
            _load_one(manifest_path, registry)
    return registry


def load_builtin_plugins(registry: PluginRegistry | None = None) -> PluginRegistry:
    """Load built-in plugins shipped with Conflux.

    Built-in plugins are explicitly listed here; the loader never scans
    arbitrary ``conflux.builtin`` submodules.
    """
    registry = registry or get_registry()
    # Built-in plugins list — each is (entrypoint_str, manifest_import_path)
    builtins: list[tuple[str, str]] = [
        ("conflux.builtin.text.plugin:plugin", "conflux.builtin.text.plugin"),
        ("conflux.builtin.rag.plugin:plugin", "conflux.builtin.rag.plugin"),
        ("conflux.builtin.web.plugin:plugin", "conflux.builtin.web.plugin"),
        ("conflux.builtin.research.plugin:plugin", "conflux.builtin.research.plugin"),
        ("conflux.builtin.paper.plugin:plugin", "conflux.builtin.paper.plugin"),
    ]
    for entrypoint, module_path in builtins:
        try:
            module = importlib.import_module(module_path)
            plugin_instance = getattr(module, "plugin", None)
            if plugin_instance is not None:
                manifest = plugin_instance.manifest
                registry.register(manifest, plugin_instance)
                logger.info("Loaded builtin plugin: %s", manifest.id)
        except Exception:
            logger.exception("Failed to load builtin plugin from %s", module_path)
    return registry


def _load_one(manifest_path: Path, registry: PluginRegistry) -> None:
    """Load a single manifest file into the registry."""
    try:
        manifest = load_manifest(manifest_path)
        issues = validate_manifest(manifest)
        if issues:
            logger.warning("Manifest issues in %s: %s", manifest_path, issues)
            return
        # Try to import the plugin instance
        instance = _import_plugin_instance(manifest)
        registry.register(manifest, instance)
    except Exception:
        logger.exception("Failed to load plugin manifest %s", manifest_path)


def _import_plugin_instance(manifest: PluginManifest) -> Any:
    """Import a plugin instance from its entrypoint string.

    Format: ``module.path:variable``
    """
    entrypoint = manifest.entrypoint
    if ":" not in entrypoint:
        raise ValueError(f"Entrypoint '{entrypoint}' must be 'module:variable'")
    module_path, var_name = entrypoint.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Cannot import plugin module '{module_path}': {exc}"
        ) from exc
    instance = getattr(module, var_name, None)
    if instance is None:
        raise AttributeError(
            f"Module '{module_path}' has no attribute '{var_name}'"
        )
    return instance
