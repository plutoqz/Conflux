"""Compatibility entrypoint for `python -m conflux.papers`."""

from .paper_ingestion.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
