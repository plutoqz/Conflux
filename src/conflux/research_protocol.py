"""Run-scoped claim and evidence contracts for the P1 research pipeline."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ClaimType = Literal["external_fact", "parametric_background", "analysis", "recommendation", "open_question"]
CoverageStatus = Literal["available", "covered", "failed", "not_needed", "gap"]
EvidenceRelation = Literal["supports", "limits", "contradicts", "context"]


@dataclass(slots=True)
class ClaimDraft:
    id: str
    text: str
    claim_type: ClaimType = "analysis"
    importance: str = "medium"
    temporal_sensitivity: str = "low"
    risk: str = "low"
    verification_questions: list[str] = field(default_factory=list)
    origin: str = "Model"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "ClaimDraft":
        claim_type = str(payload.get("claim_type") or payload.get("type") or "analysis")
        if claim_type not in {"external_fact", "parametric_background", "analysis", "recommendation", "open_question"}:
            claim_type = "analysis"
        return cls(
            id=str(payload.get("id") or f"claim-{index + 1}"),
            text=str(payload.get("text") or payload.get("claim") or "").strip(),
            claim_type=claim_type,  # type: ignore[arg-type]
            importance=str(payload.get("importance") or "medium"),
            temporal_sensitivity=str(payload.get("temporal_sensitivity") or "low"),
            risk=str(payload.get("risk") or "low"),
            verification_questions=_string_list(payload.get("verification_questions")),
            origin=str(payload.get("origin") or "Model"),
        )


@dataclass(slots=True)
class ResearchSubquestion:
    id: str
    question: str
    source_preferences: list[str] = field(default_factory=lambda: ["Model", "RAG", "Web"])
    importance: str = "medium"
    stop_condition: str = "direct evidence or budget exhausted"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "ResearchSubquestion":
        return cls(
            id=str(payload.get("id") or f"subq-{index + 1}"),
            question=str(payload.get("question") or "").strip(),
            source_preferences=_string_list(payload.get("source_preferences")) or ["Model", "RAG", "Web"],
            importance=str(payload.get("importance") or "medium"),
            stop_condition=str(payload.get("stop_condition") or "direct evidence or budget exhausted"),
        )


@dataclass(slots=True)
class ResearchPlan:
    original_query: str
    question_type: str = "open_research"
    audience: str = "researcher"
    time_scope: str = "unspecified"
    subquestions: list[ResearchSubquestion] = field(default_factory=list)
    claims: list[ClaimDraft] = field(default_factory=list)
    key_terms: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, query: str, max_subquestions: int = 4) -> "ResearchPlan":
        subquestions = [
            ResearchSubquestion.from_dict(item, index=index)
            for index, item in enumerate(payload.get("subquestions") or [])
            if isinstance(item, dict) and str(item.get("question") or "").strip()
        ][:max_subquestions]
        claims = [
            ClaimDraft.from_dict(item, index=index)
            for index, item in enumerate(payload.get("claims") or payload.get("claim_drafts") or [])
            if isinstance(item, dict) and str(item.get("text") or item.get("claim") or "").strip()
        ]
        plan = cls(
            original_query=query,
            question_type=str(payload.get("question_type") or "open_research"),
            audience=str(payload.get("audience") or "researcher"),
            time_scope=str(payload.get("time_scope") or "unspecified"),
            subquestions=subquestions,
            claims=claims,
            key_terms=_string_list(payload.get("key_terms")),
            stop_conditions=_string_list(payload.get("stop_conditions")),
        )
        return plan if plan.subquestions else default_research_plan(query, max_subquestions=max_subquestions)


@dataclass(slots=True)
class SourceCoverage:
    subquestion_id: str
    source: str
    status: CoverageStatus
    evidence_ids: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClaimAssessment:
    claim_id: str
    wording: str
    evidence_ids: list[str] = field(default_factory=list)
    relation: EvidenceRelation = "context"
    reliability: str = "provisional"
    limitations: list[str] = field(default_factory=list)
    action: str = "include_with_qualification"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VerificationIssue:
    claim_id: str
    issue_type: str
    severity: str
    description: str
    evidence_ids: list[str] = field(default_factory=list)
    suggested_action: str = "revise"
    original_text: str = ""
    replacement_text: str = ""
    requires_research: bool = False
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VerificationIssue":
        return cls(
            claim_id=str(payload.get("claim_id") or ""),
            issue_type=str(payload.get("issue_type") or "unsupported_claim"),
            severity=str(payload.get("severity") or "medium"),
            description=str(payload.get("description") or payload.get("issue") or "").strip(),
            evidence_ids=_string_list(payload.get("evidence_ids")),
            suggested_action=str(payload.get("suggested_action") or "revise"),
            original_text=str(payload.get("original_text") or "").strip(),
            replacement_text=str(payload.get("replacement_text") or "").strip(),
            requires_research=bool(payload.get("requires_research")),
            resolved=bool(payload.get("resolved")),
        )


@dataclass(slots=True)
class CitationEntry:
    number: int
    title: str
    source_type: str
    identifier: str = ""
    url: str = ""
    location: str = ""
    quote: str = ""
    evidence_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConfidenceAssessment:
    claim_id: str
    conclusion: str
    level: str
    citation_numbers: list[int] = field(default_factory=list)
    rationale: str = ""
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_research_plan(query: str, *, max_subquestions: int = 4) -> ResearchPlan:
    """Create a conservative plan when the planner model is unavailable."""

    clean = re.sub(r"\s+", " ", str(query or "")).strip()
    pieces = [
        item.strip(" ，,；;。?？")
        for item in re.split(r"[；;。?？]|以及|并且|同时|分别", clean)
        if len(item.strip()) >= 6
    ]
    questions = pieces[:max_subquestions] or [clean]
    if len(questions) == 1 and any(term in clean.casefold() for term in ("局限", "limitations", "挑战", "failure")):
        questions = [
            f"{clean}：研究对象、任务边界与当前成熟度有哪些限制",
            f"{clean}：数据、知识、工具与环境依赖有哪些限制",
            f"{clean}：方法可靠性、泛化、错误恢复与可解释性有哪些限制",
            f"{clean}：系统工程、评测基准、治理合规与实际部署有哪些限制",
        ][:max_subquestions]
    if len(questions) == 1 and (
        re.search(r"\b20\d{2}\b", clean)
        or any(term in clean.casefold() for term in ("截至", "最新", "当前", "recent", "latest", "current"))
    ):
        questions = [
            f"{clean}：核心对象的当前状态、版本与官方日期是什么",
            f"{clean}：近两年有哪些新增决定、发布或状态变化",
            f"{clean}：有哪些实施、迁移或实践指导",
            f"{clean}：还有哪些未决问题、风险或合规要求",
        ][:max_subquestions]
    return ResearchPlan(
        original_query=clean,
        subquestions=[
            ResearchSubquestion(id=f"subq-{index + 1}", question=item, importance="high" if index == 0 else "medium")
            for index, item in enumerate(dict.fromkeys(questions))
        ],
        claims=[],
        stop_conditions=["重要问题已有直接证据", "继续检索不会改变结论", "达到模式预算"],
    )


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []
