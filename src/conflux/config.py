"""配置加载 — 从 YAML + 本地 .env + 环境变量读取，提供统一访问接口"""

import copy
import os
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_local_env() -> None:
    """Load local dotenv files into the current process only.

    Values are not written to the OS environment, and real environment
    variables still take precedence when already set.
    """

    for env_path in (PROJECT_ROOT / ".env", Path.cwd() / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def _find_config() -> Path:
    """查找 config.yaml：先看环境变量，再看当前目录，再看项目根"""
    env_path = os.environ.get("CONFLUX_CONFIG")
    if env_path:
        return Path(env_path)
    cwd = Path.cwd() / "config.yaml"
    if cwd.exists():
        return cwd
    # 最后回退到项目根（src/conflux 的上级）
    return PROJECT_ROOT / "config.yaml"


def _load_raw() -> dict:
    with open(_find_config(), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _env_override(raw: dict, prefix: str = "CONFLUX") -> dict:
    """环境变量覆盖：CONFLUX_MODELS_REASONING_PROVIDER=openai → raw["models"]["reasoning"]["provider"]"""
    for key, val in os.environ.items():
        if not key.startswith(f"{prefix}_"):
            continue
        parts = key[len(prefix) + 1 :].lower().split("__")
        d = raw
        for p in parts[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[parts[-1]] = _cast_env_val(val)
    return raw


def _cast_env_val(val: str) -> Any:
    if val.isdigit():
        return int(val)
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    try:
        return float(val)
    except ValueError:
        return val


def _apply_context_overrides(raw: dict, values: Mapping[str, str]) -> dict:
    for key, val in values.items():
        if not key.startswith("CONFLUX_"):
            continue
        parts = key[len("CONFLUX_") :].lower().split("__")
        target = raw
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = _cast_env_val(val)
    return raw


# 模块级加载（惰性）
_config: dict | None = None
_config_overrides: ContextVar[tuple[dict[str, str], ...]] = ContextVar(
    "conflux_config_overrides",
    default=(),
)


def load() -> dict:
    global _config
    if _config is None:
        _load_local_env()
        _config = _env_override(_load_raw())
    overlays = _config_overrides.get()
    if not overlays:
        return _config
    resolved = copy.deepcopy(_config)
    for values in overlays:
        _apply_context_overrides(resolved, values)
    return resolved


@contextmanager
def override(values: Mapping[str, Any] | None):
    """Apply CONFLUX_* values only within the current execution context."""

    normalized = {
        str(key): str(value)
        for key, value in (values or {}).items()
        if str(key).startswith("CONFLUX_") and value not in (None, "")
    }
    token = _config_overrides.set((*_config_overrides.get(), normalized))
    try:
        yield
    finally:
        _config_overrides.reset(token)


def _context_override_value(key: str, default: Any = None) -> Any:
    for values in reversed(_config_overrides.get()):
        if key in values:
            return values[key]
    return default


def submit_with_context(executor, func, /, *args, **kwargs):
    """Submit work while preserving the caller's context-local configuration."""

    context = copy_context()
    return executor.submit(context.run, func, *args, **kwargs)


def get(*path: str, default: Any = None) -> Any:
    """便捷访问：config.get("models", "reasoning", "provider")"""
    d = load()
    for p in path:
        if isinstance(d, dict):
            d = d.get(p)
        else:
            return default
        if d is None:
            return default
    return d
