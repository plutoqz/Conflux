"""Markdown and JSON output for paper radar inboxes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from conflux.research_profile import ResearchProfile

from .models import PaperAnalysis, PaperRecord


@dataclass(slots=True)
class InboxArtifacts:
    markdown_path: Path
    json_path: Path


def build_inbox_payload(
    profile: ResearchProfile,
    analyzed: list[tuple[PaperRecord, PaperAnalysis]],
    *,
    stats: dict | None = None,
) -> dict:
    """Build a machine-readable paper inbox payload."""

    return {
        "profile_id": profile.id,
        "profile_name": profile.name,
        "stats": stats or {},
        "papers": [
            {
                "paper": paper.to_dict(),
                "analysis": analysis.to_dict(),
            }
            for paper, analysis in analyzed
        ],
    }


def build_inbox_markdown(
    profile: ResearchProfile,
    analyzed: list[tuple[PaperRecord, PaperAnalysis]],
    *,
    stats: dict | None = None,
) -> str:
    """Render a concise Markdown paper inbox."""

    stats = stats or {}
    deep = [(p, a) for p, a in analyzed if a.reading_level == "deep"]
    skim = [(p, a) for p, a in analyzed if a.reading_level == "skim"]
    skip = [(p, a) for p, a in analyzed if a.reading_level == "skip"]

    lines = [
        f"# Paper Radar Inbox: {profile.name}",
        "",
        "## Summary",
        f"- Profile: `{profile.id}`",
        f"- Total crawled/loaded: {stats.get('total_loaded', len(analyzed))}",
        f"- After deduplication: {stats.get('after_dedup', len(analyzed))}",
        f"- After negative filters: {stats.get('after_filter', len(analyzed))}",
        f"- Deep reads: {len(deep)}",
        f"- Skim reads: {len(skim)}",
        f"- Skipped: {len(skip)}",
        "",
    ]
    lines.extend(_section("Deep Reads", deep))
    lines.extend(_section("Skim Reads", skim))
    lines.extend(_section("Skipped", skip))
    return "\n".join(lines).rstrip() + "\n"


def write_inbox_artifacts(
    profile: ResearchProfile,
    analyzed: list[tuple[PaperRecord, PaperAnalysis]],
    *,
    out_dir: str | Path,
    stats: dict | None = None,
) -> InboxArtifacts:
    """Write Markdown and JSON inbox artifacts."""

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / "paper_inbox.md"
    json_path = root / "paper_inbox.json"
    markdown_path.write_text(build_inbox_markdown(profile, analyzed, stats=stats), encoding="utf-8")
    json_path.write_text(
        json.dumps(build_inbox_payload(profile, analyzed, stats=stats), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return InboxArtifacts(markdown_path=markdown_path, json_path=json_path)


def _section(title: str, items: list[tuple[PaperRecord, PaperAnalysis]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.extend(["No papers in this group.", ""])
        return lines
    for idx, (paper, analysis) in enumerate(items, start=1):
        reasons = analysis.metadata.get("score_reasons") or []
        lines.extend([
            f"### {idx}. {paper.title}",
            f"- Paper ID: `{paper.id}`",
            f"- Score: {analysis.relevance_score:.3f}",
            f"- Reading level: `{analysis.reading_level}`",
            f"- Citation value: `{analysis.citation_value}`",
            f"- Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}",
            f"- URL: {paper.url or 'N/A'}",
            f"- PDF: {paper.pdf_url or 'N/A'}",
            f"- Reasons: {'; '.join(reasons) if reasons else 'N/A'}",
            f"- Method summary: {analysis.method_summary}",
            f"- Limitations: {analysis.limitations}",
            "",
        ])
    return lines
