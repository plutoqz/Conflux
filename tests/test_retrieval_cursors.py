"""P2.6 retrieval cursors — tier refresh skipping, force refresh, and
cross-profile sharing of cursors."""

from __future__ import annotations

import time
from pathlib import Path

from conflux.adapters.sqlite_store import SQLiteDatabase, RetrievalCursorStore


def _db(tmp_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(str(tmp_path / "conflux.db")).connect()
    db.bootstrap_schema()
    return db


def test_cursor_missing_means_refresh(tmp_path: Path) -> None:
    store = RetrievalCursorStore(_db(tmp_path))
    # No cursor yet -> must refresh regardless of refresh window.
    assert store.should_refresh("p1", "t1", "milestone", 30) is True


def test_cursor_within_window_skips_refresh(tmp_path: Path) -> None:
    store = RetrievalCursorStore(_db(tmp_path))
    store.upsert("p1", "t1", "milestone", run_id="r1", year_from=2016, year_to=2026, candidate_count=20)
    # refresh_days=30, just written -> skip.
    assert store.should_refresh("p1", "t1", "milestone", 30) is False
    # refresh_days=0 (frontier/hot) -> always refresh.
    assert store.should_refresh("p1", "t1", "milestone", 0) is True
    # force -> always refresh.
    assert store.should_refresh("p1", "t1", "milestone", 30, force=True) is True


def test_cursor_expired_refreshes(tmp_path: Path) -> None:
    store = RetrievalCursorStore(_db(tmp_path))
    store.upsert("p1", "t1", "classic", run_id="r1", candidate_count=10)
    # Backdate the cursor beyond the refresh window.
    store.db.connection.execute(
        "UPDATE retrieval_cursors SET last_retrieved_at = ? WHERE profile_id = 'p1' AND track_id = 't1' AND tier = 'classic'",
        (time.time() - 31 * 86400,),
    )
    store.db.connection.commit()
    assert store.should_refresh("p1", "t1", "classic", 30) is True
    assert store.should_refresh("p1", "t1", "classic", 60) is False


def test_cursors_are_profile_scoped_but_shared_across_projects(tmp_path: Path) -> None:
    db = _db(tmp_path)
    store = RetrievalCursorStore(db)
    store.upsert("profile-A", "track-1", "hot", run_id="r1", candidate_count=5)
    # Same profile + track + tier is one row (shared across projects).
    store.upsert("profile-A", "track-1", "hot", run_id="r2", candidate_count=8)
    rows = store.list("profile-A")
    assert len(rows) == 1
    assert rows[0]["last_run_id"] == "r2"
    assert rows[0]["candidate_count"] == 8
    # Different profile is isolated.
    assert store.list("profile-B") == []
    assert store.should_refresh("profile-B", "track-1", "hot", 0) is True


def test_clear_resets_all_tiers(tmp_path: Path) -> None:
    store = RetrievalCursorStore(_db(tmp_path))
    store.upsert("p1", "t1", "frontier", run_id="r1")
    store.upsert("p1", "t1", "classic", run_id="r1")
    assert store.clear("p1") == 2
    assert store.should_refresh("p1", "t1", "classic", 30) is True


def test_upsert_is_idempotent_with_same_key(tmp_path: Path) -> None:
    store = RetrievalCursorStore(_db(tmp_path))
    for _ in range(3):
        store.upsert("p1", "t1", "classic", run_id="r9", year_from=2006, year_to=2026)
    rows = store.list("p1")
    assert len(rows) == 1
    assert rows[0]["last_year_from"] == 2006
