"""配置加载 — 从 YAML + 环境变量读取，提供统一访问接口"""

import os
from pathlib import Path
from typing import Any

import yaml


def _find_config() -> Path:
    """查找 config.yaml：先看环境变量，再看当前目录，再看项目根"""
    env_path = os.environ.get("CONFLUX_CONFIG")
    if env_path:
        return Path(env_path)
    cwd = Path.cwd() / "config.yaml"
    if cwd.exists():
        return cwd
    # 最后回退到项目根（src/conflux 的上级）
    project_root = Path(__file__).parent.parent.parent
    return project_root / "config.yaml"


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


# 模块级加载（惰性）
_config: dict | None = None


def load() -> dict:
    global _config
    if _config is None:
        _config = _env_override(_load_raw())
    return _config


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
