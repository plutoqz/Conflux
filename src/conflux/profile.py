"""Compatibility entrypoint for `python -m conflux.profile`."""

from .research_profile.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
