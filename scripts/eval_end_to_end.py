"""Real API smoke test runner for Conflux.

This script is intentionally opt-in. It exits successfully without doing work
unless --real is provided, so CI can import or invoke it safely.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real Conflux smoke test.")
    parser.add_argument("--real", action="store_true", help="Actually call configured APIs")
    parser.add_argument("--query", default="Explain how Conflux should handle RAG/Web/Model arbitration.")
    parser.add_argument("--output-dir", default="reports_real")
    args = parser.parse_args()

    if not args.real:
        print("Skipping real API smoke test. Pass --real to execute.")
        return 0
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("CONFLUX_MODELS__REASONING__API_KEY")):
        print("Missing API key for real smoke test.", file=sys.stderr)
        return 2

    command = [
        sys.executable,
        "-m",
        "conflux",
        args.query,
        "--mode",
        "phase2",
        "--output-dir",
        args.output_dir,
        "--stream-events",
        "--checkpoint-backend",
        "memory",
    ]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
