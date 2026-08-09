"""M3 runtime home resolution.

Runtime data (SQLite, objects, logs) lives outside the source tree so it can
survive re-clones and process restarts.
"""

from __future__ import annotations

import os
from pathlib import Path


ENV_HOME = "CONFLUX_HOME"
DEFAULT_HOME_NAME = "Conflux"
LOCAL_MODE = "local"
SUB_DIRECTORIES = ("objects", "indexes", "exports", "logs", "config")


def resolve_conflux_home() -> Path:
    """Return the configured runtime home path."""
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / DEFAULT_HOME_NAME
    return Path.home() / ".conflux"


def ensure_conflux_home(home: str | Path | None = None, *, mode: str = LOCAL_MODE) -> Path:
    """Create the runtime home directory tree and return its absolute path."""
    if mode != LOCAL_MODE:
        raise ValueError(f"unsupported mode: {mode}")
    path = Path(home).expanduser() if home is not None else resolve_conflux_home()
    path = path.resolve()
    for sub in SUB_DIRECTORIES:
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path


def database_path(home: str | Path | None = None) -> Path:
    """Return the SQLite database path for the runtime home."""
    base = Path(home).expanduser() if home is not None else resolve_conflux_home()
    return base.resolve() / "conflux.db"
