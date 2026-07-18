"""Plugin base class and decorators.

Plugins implement ``Plugin`` and are discovered via entry points or explicit
directories.  Each plugin exposes one or more ``Capability`` callables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from ..core.contracts import (
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    StepResult,
)


class Plugin(ABC):
    """Base class for all Conflux plugins.

    Subclasses must supply a ``manifest`` property and implement
    ``get_capability(id)`` to return a callable that accepts
    ``(context: PluginContext, **inputs)`` and returns ``StepResult``.
    """

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """The plugin's validated manifest."""
        ...

    @abstractmethod
    def get_capability(self, capability_id: str) -> Capability | None:
        """Return a registered capability by id, or None."""
        ...

    def list_capabilities(self) -> list[str]:
        """Return all capability ids declared by this plugin."""
        return [c.id for c in self.manifest.capabilities]


# A Capability is a callable (context, **inputs) → StepResult
Capability = Callable[..., StepResult]


def capability(
    *,
    id: str,
    description: str = "",
    mode: str = "deterministic",
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> Callable:
    """Decorator that attaches a ``CapabilitySpec`` to a function.

    Usage::

        @capability(id="builtin.text.keyword_match", description="Match keywords in text")
        def keyword_match(ctx: PluginContext, *, text: str, keywords: list[str]) -> StepResult:
            ...
    """

    from ..core.contracts import CapabilityMode, CapabilitySpec

    spec = CapabilitySpec(
        id=id,
        description=description,
        mode=CapabilityMode(mode),
        input_schema=input_schema or {},
        output_schema=output_schema or {},
    )

    def decorator(fn: Callable) -> Callable:
        fn._capability_spec = spec  # type: ignore[attr-defined]
        return fn

    return decorator
