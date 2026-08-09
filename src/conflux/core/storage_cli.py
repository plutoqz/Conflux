"""CLI helpers for M3 runtime-home initialization and diagnostics."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from conflux.adapters.sqlite_store import (
    SCHEMA_MIGRATIONS,
    SQLiteDatabase,
    import_legacy_project_research,
)
from conflux.config import get as config_get
from conflux.core.runtime_home import (
    SUB_DIRECTORIES,
    database_path,
    ensure_conflux_home,
    resolve_conflux_home,
)


def init_command(home: str | None = None, mode: str = "local") -> int:
    """Create the runtime home and bootstrap the SQLite schema idempotently."""
    path = ensure_conflux_home(home, mode=mode)
    db = SQLiteDatabase(database_path(path))
    db.connect()
    db.bootstrap_schema()
    db.close()
    print(f"Conflux home: {path}")
    print(f"Database: {database_path(path)}")
    print("Schema: ready")
    return 0


def migrate_command(home: str | None = None, dry_run: bool = False) -> int:
    """Apply pending schema migrations, or preview them with --dry-run."""
    path = Path(home).expanduser() if home else resolve_conflux_home()
    db_path = database_path(path)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run 'conflux init' first.")
        return 1
    db = SQLiteDatabase(db_path).connect()
    try:
        try:
            db.connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()
        except sqlite3.Error:
            pending_versions = [version for version, _ in SCHEMA_MIGRATIONS]
            if dry_run:
                print(f"Current schema version: 0")
                print(f"Pending migrations: {', '.join(pending_versions)} (schema_migrations missing)")
                return 0
            db.bootstrap_schema()
            print(f"Applied migrations: {len(pending_versions)} ({', '.join(pending_versions)})")
            return 0
        pending = db.pending_migrations()
        if dry_run:
            print(f"Current schema version: {db.schema_version()}")
            print(f"Pending migrations: {', '.join(version for version, _ in pending) or 'none'}")
            return 0
        applied = db.apply_migrations()
        print(f"Applied migrations: {applied}")
        return 0
    finally:
        db.close()


def doctor_command(home: str | None = None) -> int:
    """Report runtime-home, database, and model configuration health."""
    path = Path(home).expanduser() if home else resolve_conflux_home()
    problems: list[str] = []

    if not path.exists():
        problems.append(f"runtime home missing: {path}")
    else:
        for sub in SUB_DIRECTORIES:
            candidate = path / sub
            if not candidate.exists():
                problems.append(f"missing subdirectory: {candidate}")
            elif not os.access(candidate, os.W_OK):
                problems.append(f"not writable: {candidate}")

    db_path = database_path(path)
    schema_version: int | None = None
    if not db_path.exists():
        problems.append(f"database missing: {db_path}")
    else:
        try:
            db = SQLiteDatabase(db_path).connect()
            try:
                has_migrations = db.connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
                ).fetchone()
                if has_migrations is None:
                    problems.append("schema_migrations table missing; run 'conflux migrate'")
                else:
                    schema_version = db.schema_version()
                    pending = db.pending_migrations()
                    if pending:
                        problems.append(
                            "pending migrations: " + ", ".join(version for version, _ in pending)
                        )
            finally:
                db.close()
        except sqlite3.Error as exc:
            problems.append(f"database error: {exc}")

    required_model_presets = ("flash", "balanced", "verifier")
    missing_models = [
        preset for preset in required_model_presets
        if not isinstance(config_get("models", preset), dict)
    ]
    if missing_models:
        problems.append(f"missing model presets in config.yaml: {', '.join(missing_models)}")
    if not isinstance(config_get("embedding"), dict):
        problems.append("missing embedding config in config.yaml")

    print(f"Runtime home: {path}")
    print(f"Database: {db_path}")
    print(f"Schema version: {schema_version if schema_version is not None else 'n/a'}")
    if problems:
        print("Problems:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("OK")
    return 0


def import_legacy_command(home: str | None, source: str, dry_run: bool = False) -> int:
    """Import legacy P2 project research JSON into the runtime database."""
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        print(f"Legacy source not found: {source_path}")
        return 1
    if dry_run:
        candidates = [source_path] if source_path.is_file() else list(source_path.rglob("*.json"))
        count = sum(
            path.name in {"latest.json", "seen.json"} or path.name.startswith("run_")
            for path in candidates
        )
        print(f"Legacy source: {source_path}")
        print(f"Candidate files: {count}")
        return 0
    path = ensure_conflux_home(home)
    db = SQLiteDatabase(database_path(path)).connect()
    try:
        db.bootstrap_schema()
        summary = import_legacy_project_research(db, source_path)
    finally:
        db.close()
    print(f"Legacy source: {source_path}")
    print(
        "Imported: "
        f"files={summary['files']} runs={summary['runs']} "
        f"intents={summary['intents']} papers={summary['papers']} skipped={summary['skipped']}"
    )
    return 0
