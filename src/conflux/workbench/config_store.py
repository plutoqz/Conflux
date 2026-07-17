"""Unified config store for the Conflux workbench.

Consolidates config.yaml, .env.workbench, and runtime depth presets
into a single accessor that the workbench UI can query.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conflux import config


PROJECT_ROOT = config.PROJECT_ROOT
WORKBENCH_ENV = PROJECT_ROOT / ".env.workbench"

# Track values that existed before .env.workbench overrode them so an explicit
# clear restores the parent environment instead of leaving stale process state.
_loaded_env_keys: set[str] = set()
_original_env_values: dict[str, str | None] = {}


@dataclass
class DepthPreset:
    key: str
    label: str
    agent_max_iterations: int
    enable_l4: bool
    max_deep_questions: int
    retrieval_top_k: int
    retrieval_final_k: int


DEPTH_PRESETS: dict[str, DepthPreset] = {
    "quick": DepthPreset(
        key="quick",
        label="⚡ 快速 — 轻量检索，单轮迭代",
        agent_max_iterations=1,
        enable_l4=False,
        max_deep_questions=0,
        retrieval_top_k=3,
        retrieval_final_k=3,
    ),
    "standard": DepthPreset(
        key="standard",
        label="⚖️ 标准 — 使用配置文件默认值",
        agent_max_iterations=3,
        enable_l4=True,
        max_deep_questions=2,
        retrieval_top_k=10,
        retrieval_final_k=5,
    ),
    "deep": DepthPreset(
        key="deep",
        label="🔬 深度 — 多轮迭代 + L4 深化研究",
        agent_max_iterations=5,
        enable_l4=True,
        max_deep_questions=5,
        retrieval_top_k=15,
        retrieval_final_k=10,
    ),
}


def get_depth_preset(key: str | None = None) -> DepthPreset:
    """Return the active depth preset. Falls back to 'standard'."""
    key = key or os.environ.get("CONFLUX_DEPTH", "standard")
    return DEPTH_PRESETS.get(key, DEPTH_PRESETS["standard"])


def build_sanitized_config() -> dict[str, Any]:
    """Return the full current config, with all secret values replaced by presence flags.

    This is safe to expose via API.
    """

    raw = config.load()
    sanitized = _sanitize_dict(raw, redact_keys={"api_key", "api_secret", "password", "token"})
    sanitized["_meta"] = {
        "project_root": str(PROJECT_ROOT),
        "workbench_env_exists": WORKBENCH_ENV.exists(),
        "depth": os.environ.get("CONFLUX_DEPTH", "standard"),
        "depth_presets": {
            k: {
                "label": p.label,
                "agent_max_iterations": p.agent_max_iterations,
                "enable_l4": p.enable_l4,
                "max_deep_questions": p.max_deep_questions,
                "retrieval_top_k": p.retrieval_top_k,
                "retrieval_final_k": p.retrieval_final_k,
            }
            for k, p in DEPTH_PRESETS.items()
        },
    }
    return sanitized


def _sanitize_dict(d: dict, redact_keys: set, depth: int = 0) -> dict:
    """Recursively replace secret values with a presence flag."""
    if depth > 10:
        return d
    result = {}
    for k, v in d.items():
        key_lower = k.lower()
        if isinstance(v, dict):
            result[k] = _sanitize_dict(v, redact_keys, depth + 1)
        elif any(rk in key_lower for rk in redact_keys):
            result[k] = {"_present": bool(v and str(v).strip()), "_redacted": True}
        else:
            result[k] = v
    return result


def save_workbench_env(
    *,
    base_url: str = "",
    api_key: str = "",
    model: str = "",
    embedding_base_url: str = "",
    embedding_api_key: str = "",
    embedding_model: str = "",
    web_search_provider: str = "",
    serpapi_api_key: str = "",
    depth: str = "",
    clear_keys: list[str] | None = None,
) -> int:
    """Persist workbench settings to .env.workbench. Returns number of lines written.

    Reads existing .env.workbench keys first, then merges non-empty new values
    on top.  Pass *clear_keys* to explicitly remove one or more keys.
    """

    clear_keys = clear_keys or []

    # ── Read existing .env.workbench with python-dotenv semantics ──
    existing: dict[str, str] = {}
    if WORKBENCH_ENV.exists():
        try:
            from dotenv import dotenv_values

            existing = {
                str(key): str(value or "")
                for key, value in dotenv_values(WORKBENCH_ENV).items()
                if key
            }
        except (OSError, ValueError):
            pass

    # ── Merge incoming non-empty values ──
    if depth:
        existing["CONFLUX_DEPTH"] = depth
    if base_url:
        existing["CONFLUX_MODELS__REASONING__BASE_URL"] = base_url
        existing["CONFLUX_MODELS__CHEAP__BASE_URL"] = base_url
    if api_key:
        existing["CONFLUX_MODELS__REASONING__API_KEY"] = api_key
        existing["CONFLUX_MODELS__CHEAP__API_KEY"] = api_key
        existing["OPENAI_API_KEY"] = api_key
    if model:
        existing["CONFLUX_MODELS__REASONING__MODEL"] = model
        existing["CONFLUX_MODELS__CHEAP__MODEL"] = model
    if embedding_base_url:
        existing["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url
    if embedding_api_key:
        existing["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key
    if embedding_model:
        existing["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    if web_search_provider:
        existing["CONFLUX_WEB_SEARCH__PROVIDER"] = web_search_provider
    if serpapi_api_key:
        existing["SERPAPI_API_KEY"] = serpapi_api_key

    # ── Apply explicit key removals ──
    for k in clear_keys:
        existing.pop(k.strip(), None)

    # ── Serialize (sorted for readability) ──
    lines = [f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in sorted(existing.items())]

    try:
        WORKBENCH_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _reload_env()
        return len(lines)
    except Exception as exc:
        raise RuntimeError(f"Failed to save workbench env: {exc}") from exc


def _reload_env() -> None:
    """Reload .env.workbench into the current process."""
    global _loaded_env_keys

    from dotenv import dotenv_values, load_dotenv

    current_values: dict[str, str | None] = {}
    if WORKBENCH_ENV.exists():
        try:
            current_values = dict(dotenv_values(WORKBENCH_ENV))
        except (OSError, ValueError):
            current_values = {}

    current_keys = {str(key) for key in current_values if key}
    removed_keys = _loaded_env_keys - current_keys
    for key in removed_keys:
        original = _original_env_values.pop(key, None)
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original

    for key in current_keys - _loaded_env_keys:
        _original_env_values[key] = os.environ.get(key)

    if WORKBENCH_ENV.exists():
        try:
            load_dotenv(WORKBENCH_ENV, override=True)
        except Exception:
            pass
    _loaded_env_keys = current_keys
    config._config = None  # type: ignore[attr-defined]
