"""Run an explicitly configured test command and capture a bounded result."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Sequence

from .models import TestResult


CONFLUX_SECRET_ENV_KEYS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "SERPAPI_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CONFLUX_MODELS__REASONING__API_KEY",
    "CONFLUX_MODELS__CHEAP__API_KEY",
    "CONFLUX_EMBEDDING__API_KEY",
}


def inspect_tests(
    project_path: str | Path,
    command: str | Sequence[str] | None,
    *,
    timeout_seconds: int = 120,
) -> TestResult:
    if not command:
        return TestResult()
    display_command = command if isinstance(command, str) else " ".join(command)
    args = _command_args(command)
    if not args:
        return TestResult(status="error", command=str(display_command), output="测试命令为空。")

    started = time.perf_counter()
    try:
        result = subprocess.run(
            args,
            cwd=Path(project_path).resolve(),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=_sanitized_test_env(),
            timeout=max(1, min(timeout_seconds, 600)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return TestResult(
            status="timed_out",
            command=str(display_command),
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            output=_bounded_output(exc.stdout, exc.stderr),
        )
    except OSError as exc:
        return TestResult(
            status="error",
            command=str(display_command),
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            output=str(exc),
        )

    return TestResult(
        status="passed" if result.returncode == 0 else "failed",
        command=str(display_command),
        exit_code=result.returncode,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        output=_bounded_output(result.stdout, result.stderr),
    )


def _command_args(command: str | Sequence[str]) -> list[str]:
    if not isinstance(command, str):
        return [str(part) for part in command]
    return shlex.split(command, posix=os.name != "nt")


def _sanitized_test_env() -> dict[str, str]:
    environment = dict(os.environ)
    for name in CONFLUX_SECRET_ENV_KEYS:
        environment.pop(name, None)
    return environment


def _bounded_output(stdout: object, stderr: object, *, limit: int = 6000) -> str:
    text = "\n".join(part.strip() for part in (str(stdout or ""), str(stderr or "")) if part)
    return text[-limit:]
