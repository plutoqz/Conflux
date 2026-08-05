"""Deterministic V2 replay providers for offline workflow verification."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .source_status import SourceResult


REPLAY_SCHEMA_VERSION = "conflux-v2-replay-v1"


def message_fingerprint(messages: Any) -> str:
    """Return a stable fingerprint for a model request without storing secrets."""

    normalized = []
    for message in messages if isinstance(messages, (list, tuple)) else [messages]:
        content = getattr(message, "content", message)
        normalized.append({
            "type": type(message).__name__,
            "content": content if isinstance(content, (str, int, float, bool, type(None), list, dict)) else str(content),
        })
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class ReplayResponse:
    content: str
    usage_metadata: dict[str, int]
    response_metadata: dict[str, Any]


class ReplayModel:
    """Return recorded responses in a deterministic, role-scoped sequence."""

    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        *,
        by_fingerprint: dict[str, dict[str, Any]] | None = None,
        role: str = "model",
    ) -> None:
        self.role = role
        self._responses = list(responses or [])
        self._by_fingerprint = dict(by_fingerprint or {})
        self._cursor = 0
        self._lock = threading.Lock()
        self.requests: list[dict[str, Any]] = []

    @classmethod
    def from_payload(cls, payload: Any, *, role: str) -> "ReplayModel":
        if isinstance(payload, list):
            return cls(payload, role=role)
        if not isinstance(payload, dict):
            raise ValueError(f"replay model payload for {role} must be an object or list")
        responses = payload.get("responses") or []
        by_fingerprint = payload.get("by_fingerprint") or {}
        if not isinstance(responses, list) or not isinstance(by_fingerprint, dict):
            raise ValueError(f"replay model payload for {role} has invalid response containers")
        return cls(responses, by_fingerprint=by_fingerprint, role=role)

    def invoke(self, messages: Any, **_: Any) -> ReplayResponse:
        fingerprint = message_fingerprint(messages)
        with self._lock:
            request = {
                "role": self.role,
                "fingerprint": fingerprint,
                "request_index": len(self.requests),
            }
            self.requests.append(request)
            payload = self._by_fingerprint.get(fingerprint)
            if payload is None:
                if self._cursor >= len(self._responses):
                    raise KeyError(f"no replay response for model role {self.role}: {fingerprint}")
                payload = self._responses[self._cursor]
                self._cursor += 1
        if isinstance(payload, str):
            payload = {"content": payload}
        if not isinstance(payload, dict):
            raise ValueError(f"replay response for {self.role} must be an object or string")
        return ReplayResponse(
            content=str(payload.get("content") or ""),
            usage_metadata=dict(payload.get("usage_metadata") or {}),
            response_metadata=dict(payload.get("response_metadata") or {}),
        )


class ReplayTool:
    """Return recorded source results keyed by the exact retrieval query."""

    def __init__(
        self,
        source: str,
        responses_by_query: dict[str, Any] | None = None,
        *,
        default: Any = None,
    ) -> None:
        self.source = source
        self.responses_by_query = dict(responses_by_query or {})
        self.default = default
        self.queries: list[str] = []

    @classmethod
    def from_payload(cls, source: str, payload: Any) -> "ReplayTool":
        if not isinstance(payload, dict):
            raise ValueError(f"replay retrieval payload for {source} must be an object")
        return cls(
            source,
            payload.get("by_query") or {},
            default=payload.get("default"),
        )

    def invoke(self, payload: dict[str, Any]) -> str:
        query = str((payload or {}).get("query") or "")
        self.queries.append(query)
        item = self.responses_by_query.get(query, self.default)
        if item is None:
            raise KeyError(f"no replay response for {self.source} query: {query}")
        if isinstance(item, SourceResult):
            return item.to_tool_text()
        if isinstance(item, str):
            return item
        if not isinstance(item, dict):
            raise ValueError(f"replay retrieval response for {self.source} must be an object or string")
        return SourceResult.from_dict({"source": self.source, **item}).to_tool_text()


def load_replay_bundle(path: str | Path) -> dict[str, Any]:
    bundle_path = Path(path)
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("replay bundle must be a JSON object")
    if payload.get("schema_version") != REPLAY_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported replay schema: {payload.get('schema_version')!r}; "
            f"expected {REPLAY_SCHEMA_VERSION!r}"
        )
    for key in ("models", "retrieval"):
        if not isinstance(payload.get(key), dict):
            raise ValueError(f"replay bundle is missing object field: {key}")
    return payload


def build_replay_components(bundle: dict[str, Any]) -> tuple[dict[str, ReplayModel], ReplayTool, ReplayTool]:
    models_payload = bundle.get("models") or {}
    role_models = {
        role: ReplayModel.from_payload(models_payload[role], role=role)
        for role in ("planner", "analyst", "reranker", "synthesizer", "verifier")
        if role in models_payload
    }
    missing = [role for role in ("planner", "analyst", "synthesizer", "verifier") if role not in role_models]
    if missing:
        raise ValueError("replay bundle is missing model roles: " + ", ".join(missing))
    retrieval = bundle.get("retrieval") or {}
    rag = ReplayTool.from_payload("RAG", retrieval.get("RAG") or {})
    web = ReplayTool.from_payload("Web", retrieval.get("Web") or {})
    return role_models, rag, web
