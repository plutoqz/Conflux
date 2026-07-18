"""Plugin execution boundary.

Every capability call goes through ``execute_capability``, which:
- Catches all exceptions and converts them to ``StepResult(status=failed)``.
- Sanitises error messages to never leak secret values.
- Records a ``TraceEvent`` on every execution.
- Marks unexpected failures for human review (unreviewed / needs_review).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable

from .contracts import (
    CapabilitySpec,
    PluginContext,
    StepResult,
    StepStatus,
    TraceEvent,
)

logger = logging.getLogger(__name__)

# Simple patterns that look like API keys or tokens in error messages.
_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_-]{10,})"),           # OpenAI-style
    re.compile(r"(AKIA[A-Z0-9]{16})"),                # AWS access key
    re.compile(r"([a-zA-Z0-9+/]{40,}={0,2})"),        # base64-ish long token
]


def sanitize_error(message: str, secrets: dict[str, str] | None = None) -> str:
    """Strip configured secret values and common token patterns from text."""
    sanitized = message
    for value in sorted((secrets or {}).values(), key=len, reverse=True):
        if value:
            sanitized = sanitized.replace(value, "[REDACTED]")
    for pat in _SECRET_PATTERNS:
        sanitized = pat.sub("[REDACTED]", sanitized)
    return sanitized


def _sanitize_value(value: Any, secrets: dict[str, str]) -> Any:
    if isinstance(value, str):
        return sanitize_error(value, secrets)
    if isinstance(value, dict):
        return {key: _sanitize_value(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item, secrets) for item in value)
    return value


def execute_capability(
    capability: Callable,
    ctx: PluginContext,
    capability_spec: CapabilitySpec | None = None,
    capability_id: str = "",
    **inputs: Any,
) -> StepResult:
    """Execute a capability with unified exception handling and tracing.

    Returns a ``StepResult`` in every code path — success, failure, or
    cancellation — which means callers never see raw exceptions.
    """
    capability_id = capability_spec.id if capability_spec else capability_id
    plugin_id = capability_id.rsplit(".", 1)[0] if capability_id else ""
    started = time.time()

    try:
        if capability_spec is not None:
            from .policy import validate_capability_input

            input_issues = validate_capability_input(inputs, capability_spec.input_schema)
            if input_issues:
                return _finalize_result(
                    StepResult.failed(
                        "; ".join(input_issues),
                        detail="Capability input failed JSON Schema validation",
                        plugin_id=plugin_id,
                        capability_id=capability_id,
                    ),
                    ctx,
                    started,
                )

        result = capability(ctx, **inputs)

        # If the plugin returned a raw dict, wrap it.
        if not isinstance(result, StepResult):
            result = StepResult(
                status=StepStatus.SUCCESS,
                output=result if isinstance(result, dict) else {"value": result},
                plugin_id=plugin_id,
                capability_id=capability_id,
            )

    except Exception as exc:
        elapsed = (time.time() - started) * 1000
        raw_msg = f"{type(exc).__name__}: {exc}"
        sanitized = sanitize_error(raw_msg, ctx.secrets)
        if sanitized != raw_msg:
            logger.warning("Sanitised secret from error for capability %s", capability_id)

        result = StepResult(
            status=StepStatus.FAILED,
            error=sanitized,
            detail="Unhandled plugin exception",
            metrics={"elapsed_ms": elapsed},
            plugin_id=plugin_id,
            capability_id=capability_id,
        )

    if capability_spec is not None and result.status == StepStatus.SUCCESS:
        from .policy import validate_output

        output_issues = validate_output(result.output, capability_spec.output_schema)
        if output_issues:
            status = (
                StepStatus.UNREVIEWED
                if capability_spec.mode.value == "agentic"
                else StepStatus.FAILED
            )
            result = StepResult(
                status=status,
                error="; ".join(output_issues),
                detail="Capability output failed JSON Schema validation",
                plugin_id=plugin_id,
                capability_id=capability_id,
            )

    return _finalize_result(result, ctx, started, plugin_id, capability_id)


def _finalize_result(
    result: StepResult,
    ctx: PluginContext,
    started: float,
    plugin_id: str = "",
    capability_id: str = "",
) -> StepResult:
    """Sanitize a result, attach metrics, and emit one trace event."""

    elapsed = (time.time() - started) * 1000
    result.metrics["elapsed_ms"] = round(elapsed, 2)

    # Ensure plugin_id / capability_id are set.
    if not result.plugin_id:
        result.plugin_id = plugin_id
    if not result.capability_id:
        result.capability_id = capability_id

    result.error = sanitize_error(result.error, ctx.secrets)
    result.detail = sanitize_error(result.detail, ctx.secrets)
    result.output = _sanitize_value(result.output, ctx.secrets)
    result.metrics = _sanitize_value(result.metrics, ctx.secrets)

    event = TraceEvent(
        stage="capability.execute",
        status=result.status.value,
        elapsed_ms=round(elapsed, 2),
        run_id=ctx.run.run_id,
        thread_id=ctx.run.thread_id or "",
        plugin_id=result.plugin_id,
        capability_id=result.capability_id,
        summary=result.error[:180] if result.error else "capability completed",
        metadata={"output_keys": sorted(result.output)},
    )
    ctx.trace_events.append(event)
    if ctx.emit_trace is not None:
        try:
            ctx.emit_trace(event)
        except Exception:
            logger.exception("Trace sink failed for capability %s", result.capability_id)

    return result
