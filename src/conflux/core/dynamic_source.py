"""Dynamic source results protocol (M2).

Replaces the hard-coded ``rag_result`` / ``web_result`` / ``model_result``
triplet with a namespaced ``source_results`` dict that can hold any number
of sources registered through the plugin system.

Key design:
- ``source_results`` keys are namespaced IDs, e.g. ``"builtin.rag"``.
- Each value is a ``SourceResult.to_dict()`` payload.
- Old fixed fields are merged in for backward compat.
- The ``merge_source_result`` reducer preserves last-write-wins per source.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..source_status import SourceResult


def init_source_results() -> dict[str, dict]:
    """Return an empty source_results dict."""
    return {}


def merge_source_result(
    existing: dict[str, dict] | None,
    source: str,
    result: SourceResult | dict,
) -> dict[str, dict]:
    """Add or replace a source entry in the dynamic collection.

    Returns a new dict (suitable as a LangGraph reducer).
    """
    merged = dict(existing or {})
    if isinstance(result, SourceResult):
        merged[source] = namespace_source_result(source, result).to_dict()
    else:
        payload = dict(result)
        payload["source"] = source
        merged[source] = payload
    return merged


def merge_source_results_reducer(
    left: dict[str, dict] | None,
    right: dict[str, dict] | None,
) -> dict[str, dict]:
    """LangGraph reducer: merge two source_results dicts, right wins on conflict."""
    merged = dict(left or {})
    if right:
        merged.update(right)
    return merged


def merge_legacy_fields(
    source_results: dict[str, dict],
    rag_result: str = "",
    web_result: str = "",
    model_result: str = "",
) -> dict[str, dict]:
    """Merge old fixed fields into the dynamic collection for backward compat.

    Old fields take lower priority — if a namespaced source already exists
    (e.g. ``"builtin.rag"``), the old field is NOT merged.
    """
    from ..source_status import parse_source_results as _parse

    merged = dict(source_results)
    mapping = [
        ("builtin.rag", rag_result),
        ("builtin.web", web_result),
        ("builtin.model", model_result),
    ]
    for ns_id, text in mapping:
        if ns_id not in merged and text:
            parsed = _parse(text)
            if parsed:
                merged[ns_id] = namespace_source_result(ns_id, parsed[0]).to_dict()
    return merged


def namespace_source_result(source_id: str, result: SourceResult) -> SourceResult:
    """Return a result whose source and claim sources use the namespaced ID."""

    claims = [replace(claim, source=source_id) for claim in result.claims]
    return replace(result, source=source_id, claims=claims)


def source_ids(collection: dict[str, dict]) -> list[str]:
    """Return sorted list of registered source IDs."""
    return sorted(collection.keys())


def get_source_result(collection: dict[str, dict], source_id: str) -> SourceResult | None:
    """Look up a source by namespaced ID."""
    payload = collection.get(source_id)
    if payload is None:
        return None
    return SourceResult.from_dict(payload)
