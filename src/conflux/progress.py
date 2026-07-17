"""Compatibility entrypoint for ``python -m conflux.progress``."""

from conflux.progress_audit.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
