"""Command line helpers for research profiles."""

from __future__ import annotations

import argparse
import json
import sys

import yaml

from .loader import load_profile
from .validators import ProfileValidationError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Conflux research profile utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a research profile YAML file")
    validate_parser.add_argument("profile", help="Path to a research profile YAML file")

    show_parser = subparsers.add_parser("show", help="Print a normalized research profile")
    show_parser.add_argument("profile", help="Path to a research profile YAML file")
    show_parser.add_argument("--json", action="store_true", help="Print JSON instead of YAML")

    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
    except (OSError, ProfileValidationError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.command == "validate":
        print(f"Profile OK: {profile.id} ({profile.name})")
        for warning in profile.warnings:
            print(f"Warning: {warning}")
        return 0

    if args.command == "show":
        payload = profile.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
