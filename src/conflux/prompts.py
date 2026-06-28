"""Prompt 文件加载。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=32)
def load_prompt(relative_path: str) -> dict:
    """加载 prompts/ 下的 YAML prompt。"""
    path = PROMPT_ROOT / relative_path
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Prompt file must contain a YAML mapping: {path}")
    return data


def load_system_prompt(relative_path: str, default: str) -> str:
    """加载 system 字段；文件缺失或字段为空时回退到 default。"""
    path = PROMPT_ROOT / relative_path
    if not path.exists():
        return default
    data = load_prompt(relative_path)
    system = data.get("system")
    return system if isinstance(system, str) and system.strip() else default
