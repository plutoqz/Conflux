"""Unified config store for the Conflux workbench.

Consolidates config.yaml, .env.workbench, and runtime depth presets
into a single accessor that the workbench UI can query.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
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
    retrieval_top_k: int | None
    retrieval_final_k: int | None


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
        retrieval_top_k=None,
        retrieval_final_k=None,
    ),
    "deep": DepthPreset(
        key="deep",
        label="🔬 深度 — 多轮迭代 + L4 深化研究",
        agent_max_iterations=5,
        enable_l4=True,
        max_deep_questions=5,
        retrieval_top_k=None,
        retrieval_final_k=None,
    ),
}


def get_depth_preset(key: str | None = None) -> DepthPreset:
    """Return the active depth preset. Falls back to 'standard'."""
    key = key or os.environ.get("CONFLUX_DEPTH", "standard")
    preset = DEPTH_PRESETS.get(key, DEPTH_PRESETS["standard"])
    return replace(
        preset,
        retrieval_top_k=(
            preset.retrieval_top_k
            if preset.retrieval_top_k is not None
            else int(config.get("retrieval", "top_k", default=60))
        ),
        retrieval_final_k=(
            preset.retrieval_final_k
            if preset.retrieval_final_k is not None
            else int(config.get("retrieval", "final_k", default=20))
        ),
    )


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
                "label": resolved.label,
                "agent_max_iterations": resolved.agent_max_iterations,
                "enable_l4": resolved.enable_l4,
                "max_deep_questions": resolved.max_deep_questions,
                "retrieval_top_k": resolved.retrieval_top_k,
                "retrieval_final_k": resolved.retrieval_final_k,
            }
            for k in DEPTH_PRESETS
            for resolved in (get_depth_preset(k),)
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
    tier_models: dict[str, dict[str, Any]] | None = None,
    feature_models: dict[str, dict[str, Any]] | None = None,
    embedding_base_url: str = "",
    embedding_api_key: str = "",
    embedding_model: str = "",
    vector_collection_name: str = "",
    web_search_provider: str = "",
    serpapi_api_key: str = "",
    bing_api_key: str = "",
    google_api_key: str = "",
    google_cse_id: str = "",
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
    for tier in ("quick", "standard", "deep"):
        tier_config = dict((tier_models or {}).get(tier) or {})
        if not tier_config:
            continue
        prefix = f"CONFLUX_MODELS__{tier.upper()}"
        existing[f"{prefix}__PROVIDER"] = "openai_compatible"
        for field in ("base_url", "api_key", "model", "temperature"):
            value = tier_config.get(field)
            if value is None or str(value).strip() == "":
                continue
            existing[f"{prefix}__{field.upper()}"] = str(value).strip()
        for role in ("planner", "analyst", "reranker", "synthesizer", "verifier"):
            existing[
                f"CONFLUX_RESEARCH__PROFILES__{tier.upper()}__{role.upper()}_MODEL"
            ] = tier
    for feature, feature_config in (feature_models or {}).items():
        if not isinstance(feature_config, dict):
            continue
        prefix = f"CONFLUX_MODELS__{str(feature).upper()}"
        existing[f"{prefix}__PROVIDER"] = "openai_compatible"
        for field in ("base_url", "api_key", "model", "temperature"):
            value = feature_config.get(field)
            if value is None or str(value).strip() == "":
                continue
            existing[f"{prefix}__{field.upper()}"] = str(value).strip()
    if embedding_base_url:
        existing["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url
    if embedding_api_key:
        existing["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key
    if embedding_model:
        existing["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    if vector_collection_name:
        existing["CONFLUX_VECTOR_STORE__COLLECTION_NAME"] = vector_collection_name
    if web_search_provider:
        existing["CONFLUX_WEB_SEARCH__PROVIDER"] = web_search_provider
    if serpapi_api_key:
        existing["SERPAPI_API_KEY"] = serpapi_api_key
    if bing_api_key:
        existing["BING_SEARCH_API_KEY"] = bing_api_key
    if google_api_key:
        existing["GOOGLE_API_KEY"] = google_api_key
    if google_cse_id:
        existing["GOOGLE_CSE_ID"] = google_cse_id

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


def save_config_field(path: str, value: Any) -> dict[str, Any]:
    """Update a single dot-path field in config.yaml and return the new config.

    Only allow-safe paths under `research.profiles.<depth>.*` are accepted.
    The file is atomically replaced.
    """

    import yaml

    allowed_prefixes = (
        "research.profiles.quick.",
        "research.profiles.standard.",
        "research.profiles.deep.",
    )
    path = str(path or "").strip()
    if not any(path.startswith(p) for p in allowed_prefixes):
        return {"ok": False, "error": f"不允许修改的配置路径: {path}"}

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {"ok": False, "error": "config.yaml 不存在"}

    raw = config.load()

    # Navigate nested keys
    keys = path.split(".")
    target = raw
    for key in keys[:-1]:
        if not isinstance(target, dict):
            return {"ok": False, "error": f"路径 {path} 中的 {key} 不是字典"}
        target = target.setdefault(key, {})
    target[keys[-1]] = value

    # Atomic write
    tmp = config_path.with_suffix(".yaml.tmp")
    try:
        tmp.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
        tmp.replace(config_path)
        config._config = None  # type: ignore[attr-defined]
        return {"ok": True, "path": path, "value": value}
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return {"ok": False, "error": str(exc)}
