"""LLM-based paper relevance and evidence-quality review (M2)."""

from __future__ import annotations

import hashlib
from typing import Any

from conflux.builtin.research.plugin import evidence_review
from conflux.core.contracts import (
    CapabilityMode,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    StepResult,
    StepStatus,
)
from conflux.core.executor import sanitize_error
from conflux.sdk.plugin import Capability, Plugin


class PaperPlugin(Plugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="builtin.paper",
            version="0.1.0",
            entrypoint="conflux.builtin.paper.plugin:plugin",
            capabilities=[
                CapabilitySpec(
                    id="builtin.paper.review",
                    description="LLM-based paper relevance and evidence quality review",
                    mode=CapabilityMode.AGENTIC,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "papers": {"type": "array", "items": {"type": "object"}},
                            "profile_id": {"type": "string"},
                            "profile_version": {"type": "string"},
                            "profile_keywords": {"type": "array"},
                            "profile_questions": {"type": "array"},
                            "profile_fields": {"type": "array"},
                        },
                        "required": ["papers"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "reviews": {"type": "array"},
                            "reviewed": {"type": "integer"},
                            "unreviewed": {"type": "integer"},
                            "next_action": {"type": "string"},
                        },
                        "required": ["reviews", "reviewed", "unreviewed", "next_action"],
                    },
                )
            ],
            permissions=[PluginPermission.MODEL_INFERENCE],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        return paper_review if capability_id == "builtin.paper.review" else None


plugin = PaperPlugin()


def paper_review(
    ctx: PluginContext,
    *,
    papers: list[dict[str, Any]],
    profile_id: str = "unversioned",
    profile_version: str = "unversioned",
    profile_keywords: list[str] | None = None,
    profile_questions: list[str] | None = None,
    profile_fields: list[str] | None = None,
) -> StepResult:
    """Review papers using the shared strict evidence-review protocol."""

    if not papers:
        return StepResult(
            status=StepStatus.SUCCESS,
            output={"reviews": [], "reviewed": 0, "unreviewed": 0, "next_action": ""},
            plugin_id="builtin.paper",
            capability_id="builtin.paper.review",
        )

    candidates = [
        {
            "text": _paper_text(paper),
            "paper_id": str(paper.get("paper_id") or paper.get("id") or index),
            "title": str(paper.get("title") or ""),
        }
        for index, paper in enumerate(papers)
    ]
    context = ". ".join(
        item
        for item in (
            f"Profile: {profile_id}",
            f"Keywords: {', '.join(profile_keywords or [])}" if profile_keywords else "",
            f"Questions: {'; '.join((profile_questions or [])[:3])}" if profile_questions else "",
            f"Fields: {', '.join(profile_fields or [])}" if profile_fields else "",
        )
        if item
    )
    try:
        reviewed = evidence_review(
            ctx,
            query=" ".join((profile_questions or [])[:2]) or "research relevance",
            candidates=candidates,
            research_context=context,
            profile_version=profile_version,
        )
    except Exception as exc:
        error = sanitize_error(f"Paper review unavailable: {type(exc).__name__}: {exc}", ctx.secrets)
        return _unreviewed_result(papers, error, profile_version)

    reviews = list(reviewed.output.get("reviews") or [])
    for index, review in enumerate(reviews):
        paper = papers[index] if index < len(papers) else {}
        review["paper_id"] = paper.get("paper_id", paper.get("id", str(index)))
        review["title_hash"] = _hash_text(str(paper.get("title") or ""))
        review.setdefault("profile_id", profile_id)

    status = reviewed.status
    next_action = "" if status == StepStatus.SUCCESS else "Configure a working review model and retry unreviewed papers."
    return StepResult(
        status=status,
        output={
            "reviews": reviews,
            "reviewed": sum(1 for item in reviews if item.get("relevance") != "unreviewed"),
            "unreviewed": sum(1 for item in reviews if item.get("relevance") == "unreviewed"),
            "next_action": next_action,
        },
        error=reviewed.error,
        plugin_id="builtin.paper",
        capability_id="builtin.paper.review",
    )


def _unreviewed_result(papers: list[dict[str, Any]], error: str, profile_version: str) -> StepResult:
    reviews = []
    for index, paper in enumerate(papers):
        reviews.append({
            "paper_id": paper.get("paper_id", paper.get("id", str(index))),
            "relevance": "unreviewed",
            "research_value": "none",
            "evidence_quality": "unreviewed",
            "reasoning": error,
            "confidence": 0.0,
            "needs_deeper_review": False,
            "content_hash": _hash_text(_paper_text(paper)),
            "title_hash": _hash_text(str(paper.get("title") or "")),
            "profile_version": profile_version,
            "next_action": "Configure a working review model and retry unreviewed papers.",
        })
    return StepResult(
        status=StepStatus.UNREVIEWED,
        output={
            "reviews": reviews,
            "reviewed": 0,
            "unreviewed": len(reviews),
            "next_action": "Configure a working review model and retry unreviewed papers.",
        },
        error=error,
        plugin_id="builtin.paper",
        capability_id="builtin.paper.review",
    )


def _paper_text(paper: dict[str, Any]) -> str:
    title = str(paper.get("title") or "")
    abstract = str(paper.get("abstract") or paper.get("summary") or "")
    return f"{title}. {abstract}"[:1200]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
