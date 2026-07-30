"""Data contracts for graduate research profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ResearchProfile:
    """A user's research context shared by paper radar, RAG, and audit flows."""

    id: str
    name: str
    fields: list[str]
    research_questions: list[str]
    keywords: list[str]
    negative_keywords: list[str] = field(default_factory=list)
    target_venues: list[str] = field(default_factory=list)
    tracked_scholars: list[str] = field(default_factory=list)
    project_paths: list[str] = field(default_factory=list)
    document_paths: list[str] = field(default_factory=list)
    paper_sources: list[str] = field(default_factory=lambda: ["arxiv"])
    report_cadence: str = "weekly"
    tracks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-serializable representation."""

        return asdict(self)

    def get_tracks(self):
        """Parse raw track dicts into Pydantic Track objects."""
        from conflux.core.p2_contracts import Track
        result = []
        for t in self.tracks:
            try:
                result.append(Track(**t))
            except Exception:
                continue
        return result

    def normalized_project_paths(self, base_dir: Path | None = None) -> list[Path]:
        """Return project paths resolved against an optional profile directory."""

        return [_normalize_path(path, base_dir) for path in self.project_paths]

    def normalized_document_paths(self, base_dir: Path | None = None) -> list[Path]:
        """Return document paths resolved against an optional profile directory."""

        return [_normalize_path(path, base_dir) for path in self.document_paths]


def _normalize_path(path: str, base_dir: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and base_dir is not None:
        candidate = base_dir / candidate
    return candidate.resolve()
