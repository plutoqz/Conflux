"""Offline paper fixture loading."""

from __future__ import annotations

import json
from pathlib import Path

from .models import PaperAnalysis, PaperRecord


def load_paper_fixture(path: str | Path) -> list[PaperRecord]:
    """Load a deterministic paper fixture from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("papers", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("paper fixture must be a list or an object with a 'papers' list")
    return [PaperRecord.from_dict(item) for item in records if isinstance(item, dict)]


def load_analysis_fixture(path: str | Path) -> list[PaperAnalysis]:
    """Load analysis fixture records from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("analyses", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("analysis fixture must be a list or an object with an 'analyses' list")
    return [PaperAnalysis.from_dict(item) for item in records if isinstance(item, dict)]
