"""Checkpoint helper utilities for LangGraph runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckpointHandle:
    """Description of the active checkpoint backend."""

    backend: str
    checkpointer: object | None


def create_checkpointer(backend: str | None = "memory") -> CheckpointHandle:
    """Create a LangGraph checkpointer by backend name.

    The project intentionally starts with an in-memory backend: it proves the
    graph is checkpoint-ready without introducing a database dependency.
    """

    normalized = (backend or "none").lower()
    if normalized in {"none", "off", "disabled"}:
        return CheckpointHandle(backend="none", checkpointer=None)
    if normalized == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return CheckpointHandle(backend="memory", checkpointer=MemorySaver())
    raise ValueError(f"Unsupported checkpoint backend: {backend}")


def graph_config(thread_id: str | None = None) -> dict:
    """Return the LangGraph config carrying the checkpoint thread id."""

    if not thread_id:
        return {}
    return {"configurable": {"thread_id": thread_id}}
