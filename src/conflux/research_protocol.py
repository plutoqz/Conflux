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


LedgerVisibility = Literal["primary", "verification_only"]


@dataclass(slots=True)
class EvidenceRecord:
    """Evidence metadata shared by retrieval stages and frozen at a Barrier."""

    evidence_id: str
    subquestion_id: str
    query_id: str
    source_identity: str
    publisher: str
    content_hash: str
    source_type: str
    source_authority: float = 0.0
    claim_fitness: float = 0.0
    published_at: str = ""
    retrieved_at: str = ""
    evidence_role: str = "direct_support"
    claim: str = ""
    verbatim_quote: str = ""
    evidence_class: str = ""
    url: str = ""
    document_title: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    visibility: LedgerVisibility = "primary"
    relationship: str = "supports"
    subquestion_ids: list[str] = field(default_factory=list)
    supersedes: str = ""
    promoted_from: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRecord":
        visibility = str(payload.get("visibility") or "primary")
        if visibility not in {"primary", "verification_only"}:
            visibility = "primary"
        subquestion_id = str(payload.get("subquestion_id") or "")
        subquestion_ids = _string_list(payload.get("subquestion_ids"))
        if subquestion_id and subquestion_id not in subquestion_ids:
            subquestion_ids.insert(0, subquestion_id)
        return cls(
            evidence_id=str(payload.get("evidence_id") or ""),
            subquestion_id=subquestion_id,
            query_id=str(payload.get("query_id") or ""),
            source_identity=str(payload.get("source_identity") or ""),
            publisher=str(payload.get("publisher") or ""),
            content_hash=str(payload.get("content_hash") or ""),
            source_type=str(payload.get("source_type") or ""),
            source_authority=_bounded_float(payload.get("source_authority"), default=0.0),
            claim_fitness=_bounded_float(payload.get("claim_fitness"), default=0.0),
            published_at=str(payload.get("published_at") or ""),
            retrieved_at=str(payload.get("retrieved_at") or ""),
            evidence_role=str(payload.get("evidence_role") or "direct_support"),
            claim=str(payload.get("claim") or ""),
            verbatim_quote=str(payload.get("verbatim_quote") or ""),
            evidence_class=str(payload.get("evidence_class") or ""),
            url=str(payload.get("url") or ""),
            document_title=str(payload.get("document_title") or ""),
            evidence_refs=_string_list(payload.get("evidence_refs")),
            visibility=visibility,  # type: ignore[arg-type]
            relationship=str(payload.get("relationship") or "supports"),
            subquestion_ids=subquestion_ids,
            supersedes=str(payload.get("supersedes") or ""),
            promoted_from=str(payload.get("promoted_from") or ""),
        )


@dataclass(slots=True)
class ActionProposal:
    """One bounded coordinator-approved correction action."""

    action_id: str
    subquestion_id: str
    source: str
    query: str
    trigger: str
    round: int = 1
    approved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionProposal":
        return cls(
            action_id=str(payload.get("action_id") or ""),
            subquestion_id=str(payload.get("subquestion_id") or ""),
            source=str(payload.get("source") or ""),
            query=str(payload.get("query") or ""),
            trigger=str(payload.get("trigger") or ""),
            round=max(1, _int_value(payload.get("round"), default=1)),
            approved=bool(payload.get("approved", True)),
        )


@dataclass(frozen=True, slots=True)
class LedgerSnapshot:
    """Read-only evidence view consumed after a Barrier."""

    snapshot_id: str
    run_id: str
    round: str
    records: tuple[EvidenceRecord, ...] = ()
    source_statuses: tuple[tuple[str, dict[str, Any]], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "run_id": self.run_id,
            "round": self.round,
            "records": [record.to_dict() for record in self.records],
            "source_statuses": {key: value for key, value in self.source_statuses},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LedgerSnapshot":
        statuses = payload.get("source_statuses") or {}
        status_items = (
            tuple((str(key), dict(value or {})) for key, value in statuses.items())
            if isinstance(statuses, dict)
            else ()
        )
        records = tuple(
            EvidenceRecord.from_dict(item)
            for item in payload.get("records") or []
            if isinstance(item, dict)
        )
        return cls(
            snapshot_id=str(payload.get("snapshot_id") or ""),
            run_id=str(payload.get("run_id") or ""),
            round=str(payload.get("round") or ""),
            records=records,
            source_statuses=status_items,
        )

    def primary_records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(record for record in self.records if record.visibility == "primary")


@dataclass(slots=True)
class EvidenceLedger:
    """Single run-scoped append-only store for source evidence."""

    run_id: str
    records: dict[str, EvidenceRecord] = field(default_factory=dict)
    source_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)
    action_proposals: list[ActionProposal] = field(default_factory=list)
    snapshot_count: int = 0

    def append_record(self, record: EvidenceRecord) -> str:
        key = (record.source_identity, record.content_hash, record.visibility)
        existing = next(
            (
                item
                for item in self.records.values()
                if (item.source_identity, item.content_hash, item.visibility) == key
            ),
            None,
        )
        if existing is not None:
            for subquestion_id in [record.subquestion_id, *record.subquestion_ids]:
                if subquestion_id and subquestion_id not in existing.subquestion_ids:
                    existing.subquestion_ids.append(subquestion_id)
            return existing.evidence_id
        self.records[record.evidence_id] = record
        return record.evidence_id

    def append_source_result(
        self,
        result: Any,
        *,
        subquestion_id: str,
        query_id: str,
        visibility: LedgerVisibility = "primary",
    ) -> list[str]:
        from hashlib import sha256

        ids: list[str] = []
        claims = list(getattr(result, "claims", []) or [])
        for claim in claims:
            text = str(getattr(claim, "verbatim_quote", "") or getattr(claim, "claim", "")).strip()
            if not text:
                continue
            content_hash = str(getattr(claim, "content_hash", "") or "")
            if not content_hash:
                content_hash = sha256(text.encode("utf-8")).hexdigest()
            source = str(getattr(claim, "source", "") or getattr(result, "source", ""))
            source_identity = str(
                getattr(claim, "source_identity", "")
                or getattr(claim, "url", "")
                or getattr(claim, "paper_id", "")
                or getattr(claim, "document_title", "")
                or source
            )
            evidence_id = f"{self.run_id}:ev-{len(self.records) + len(ids) + 1:04d}"
            record = EvidenceRecord(
                evidence_id=evidence_id,
                subquestion_id=subquestion_id,
                query_id=query_id,
                source_identity=source_identity,
                publisher=str(getattr(claim, "organization", "") or source),
                content_hash=content_hash,
                source_type=source,
                source_authority=float(getattr(claim, "authority", 0.0) or 0.0),
                claim_fitness=float(getattr(claim, "relevance", 0.0) or 0.0),
                published_at=str(getattr(claim, "published_at", "") or ""),
                retrieved_at=str(getattr(claim, "retrieved_at", "") or ""),
                evidence_role=str(getattr(claim, "evidence_role", "") or "direct_support"),
                claim=str(getattr(claim, "claim", "") or text),
                verbatim_quote=text,
                evidence_class=str(getattr(claim, "evidence_class", "") or getattr(result, "evidence_class", "")),
                url=str(getattr(claim, "url", "") or ""),
                document_title=str(getattr(claim, "document_title", "") or ""),
                evidence_refs=[str(item) for item in getattr(claim, "evidence_refs", []) or []],
                visibility=visibility,
                relationship=str(getattr(claim, "relationship", "supports") or "supports"),
                subquestion_ids=[subquestion_id],
            )
            ids.append(self.append_record(record))
        self.source_statuses[f"{subquestion_id}:{getattr(result, 'source', '')}:{visibility}"] = result.to_dict()
        return ids

    def add_action_proposal(self, proposal: ActionProposal) -> None:
        if not any(item.action_id == proposal.action_id for item in self.action_proposals):
            self.action_proposals.append(proposal)

    def freeze(self, round_name: str) -> LedgerSnapshot:
        self.snapshot_count += 1
        return LedgerSnapshot(
            snapshot_id=f"{self.run_id}:snapshot-{self.snapshot_count}",
            run_id=self.run_id,
            round=round_name,
            records=tuple(self.records.values()),
            source_statuses=tuple((key, dict(value)) for key, value in self.source_statuses.items()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "records": [record.to_dict() for record in self.records.values()],
            "source_statuses": self.source_statuses,
            "action_proposals": [item.to_dict() for item in self.action_proposals],
            "snapshot_count": self.snapshot_count,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceLedger":
        ledger = cls(
            run_id=str(payload.get("run_id") or ""),
            source_statuses={
                str(key): dict(value or {})
                for key, value in (payload.get("source_statuses") or {}).items()
            },
            action_proposals=[
                ActionProposal.from_dict(item)
                for item in payload.get("action_proposals") or []
                if isinstance(item, dict)
            ],
            snapshot_count=max(0, _int_value(payload.get("snapshot_count"))),
        )
        for item in payload.get("records") or []:
            if isinstance(item, dict):
                record = EvidenceRecord.from_dict(item)
                if record.evidence_id:
                    ledger.records[record.evidence_id] = record
        return ledger


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
    authors: list[str] = field(default_factory=list)
    organization: str = ""
    publication_year: str = ""
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


# P1.5 generalized deep-research contracts. These objects stay run-scoped and
# deliberately use JSON-native field types so they can be persisted in traces.
ArchetypeType = Literal[
    "method_survey",
    "state_and_trends",
    "limitations_and_challenges",
    "comparison",
    "causal_mechanism",
    "solution_design",
    "evidence_review",
    "general_exploration",
]
DimensionCoverageStatus = Literal[
    "covered",
    "partial",
    "evidence_scarce",
    "conflicting",
    "out_of_scope",
]
ActionCoverageStatus = Literal[
    "covered",
    "model_analysis",
    "conflicting",
    "gap",
    "out_of_scope",
]


@dataclass(slots=True)
class ScopeContract:
    """Stable research-object boundary carried through every P1.5 stage."""

    subject: str
    task: str = ""
    scope_inclusions: list[str] = field(default_factory=list)
    scope_exclusions: list[str] = field(default_factory=list)
    time_scope: str = "unspecified"
    audience: str = "researcher"
    required_entities: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    original_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, query: str = "") -> "ScopeContract":
        original_query = str(payload.get("original_query") or query or "").strip()
        subject = str(payload.get("subject") or original_query).strip()
        return cls(
            subject=subject,
            task=str(payload.get("task") or "").strip(),
            scope_inclusions=_string_list(payload.get("scope_inclusions")),
            scope_exclusions=_string_list(payload.get("scope_exclusions")),
            time_scope=str(payload.get("time_scope") or "unspecified").strip(),
            audience=str(payload.get("audience") or "researcher").strip(),
            required_entities=_string_list(payload.get("required_entities")),
            ambiguities=_string_list(payload.get("ambiguities")),
            original_query=original_query,
        )


@dataclass(slots=True)
class QueryArchetype:
    type: ArchetypeType = "general_exploration"
    confidence: float = 0.0
    user_intent: str = ""
    expected_research_actions: list[str] = field(default_factory=list)
    required_synthesis_functions: list[str] = field(default_factory=list)
    secondary_types: list[str] = field(default_factory=list)
    selection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QueryArchetype":
        archetype = str(payload.get("type") or "general_exploration")
        allowed = {
            "method_survey",
            "state_and_trends",
            "limitations_and_challenges",
            "comparison",
            "causal_mechanism",
            "solution_design",
            "evidence_review",
            "general_exploration",
        }
        if archetype not in allowed:
            archetype = "general_exploration"
        return cls(
            type=archetype,  # type: ignore[arg-type]
            confidence=_bounded_float(payload.get("confidence"), default=0.0),
            user_intent=str(payload.get("user_intent") or "").strip(),
            expected_research_actions=_string_list(payload.get("expected_research_actions")),
            required_synthesis_functions=_string_list(payload.get("required_synthesis_functions")),
            secondary_types=_string_list(payload.get("secondary_types")),
            selection_reason=str(payload.get("selection_reason") or payload.get("reason") or "").strip(),
        )


@dataclass(slots=True)
class ResearchStrategy:
    primary_archetype: str = "general_exploration"
    secondary_archetypes: list[str] = field(default_factory=list)
    rationale: str = ""
    discovery_actions: list[str] = field(default_factory=list)
    depth_actions: list[str] = field(default_factory=list)
    required_synthesis_functions: list[str] = field(default_factory=list)
    stop_policy: list[str] = field(default_factory=list)
    breadth_first: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchStrategy":
        return cls(
            primary_archetype=str(payload.get("primary_archetype") or "general_exploration"),
            secondary_archetypes=_string_list(payload.get("secondary_archetypes")),
            rationale=str(payload.get("rationale") or "").strip(),
            discovery_actions=_string_list(payload.get("discovery_actions")),
            depth_actions=_string_list(payload.get("depth_actions")),
            required_synthesis_functions=_string_list(payload.get("required_synthesis_functions")),
            stop_policy=_string_list(payload.get("stop_policy")),
            breadth_first=_bool_value(payload.get("breadth_first"), default=True),
        )


@dataclass(slots=True)
class ResearchDimension:
    id: str
    name: str
    inclusion_reason: str = ""
    parent_id: str = ""
    child_ids: list[str] = field(default_factory=list)
    questions_to_answer: list[str] = field(default_factory=list)
    expected_evidence_types: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    cross_validation_required: bool | None = None
    importance: float = 0.5
    current_coverage: str = "evidence_scarce"
    conflicts: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    terminology: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "ResearchDimension":
        name = str(payload.get("name") or payload.get("title") or f"dimension-{index + 1}").strip()
        return cls(
            id=str(payload.get("id") or f"dim-{index + 1}"),
            name=name,
            inclusion_reason=str(payload.get("inclusion_reason") or payload.get("reason") or "").strip(),
            parent_id=str(payload.get("parent_id") or "").strip(),
            child_ids=_string_list(payload.get("child_ids")),
            questions_to_answer=_string_list(
                payload.get("questions_to_answer") or payload.get("questions")
            ),
            expected_evidence_types=_string_list(
                payload.get("expected_evidence_types") or payload.get("evidence_types")
            ),
            required_actions=_string_list(payload.get("required_actions")),
            cross_validation_required=(
                None
                if payload.get("cross_validation_required") is None
                else _bool_value(payload.get("cross_validation_required"))
            ),
            importance=_importance_float(payload.get("importance"), default=0.5),
            current_coverage=str(payload.get("current_coverage") or "evidence_scarce"),
            conflicts=_string_list(payload.get("conflicts")),
            gaps=_string_list(payload.get("gaps")),
            stop_conditions=_string_list(payload.get("stop_conditions")),
            terminology=_string_list(payload.get("terminology")),
        )


@dataclass(slots=True)
class DomainMap:
    scope: str = ""
    key_concepts: list[str] = field(default_factory=list)
    terminology: list[str] = field(default_factory=list)
    dimensions: list[ResearchDimension] = field(default_factory=list)
    dimension_relations: list[dict[str, str]] = field(default_factory=list)
    disputed_boundaries: list[str] = field(default_factory=list)
    discovery_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DomainMap":
        dimensions = [
            ResearchDimension.from_dict(item, index=index)
            for index, item in enumerate(payload.get("dimensions") or [])
            if isinstance(item, dict)
        ]
        relations = [
            {str(key): str(value) for key, value in item.items() if str(key)}
            for item in payload.get("dimension_relations") or []
            if isinstance(item, dict)
        ]
        return cls(
            scope=str(payload.get("scope") or "").strip(),
            key_concepts=_string_list(payload.get("key_concepts")),
            terminology=_string_list(payload.get("terminology")),
            dimensions=dimensions,
            dimension_relations=relations,
            disputed_boundaries=_string_list(payload.get("disputed_boundaries")),
            discovery_sources=_string_list(payload.get("discovery_sources")),
        )


@dataclass(slots=True)
class CoverageAction:
    action: str
    status: ActionCoverageStatus = "gap"
    evidence_ids: list[str] = field(default_factory=list)
    external_evidence_ids: list[str] = field(default_factory=list)
    model_evidence_ids: list[str] = field(default_factory=list)
    citation_refs: list[str] = field(default_factory=list)
    high_risk: bool = False
    gap_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoverageAction":
        status = str(payload.get("status") or "gap")
        if status not in {"covered", "model_analysis", "conflicting", "gap", "out_of_scope"}:
            status = "gap"
        return cls(
            action=str(payload.get("action") or "").strip(),
            status=status,  # type: ignore[arg-type]
            evidence_ids=_string_list(payload.get("evidence_ids")),
            external_evidence_ids=_string_list(payload.get("external_evidence_ids")),
            model_evidence_ids=_string_list(payload.get("model_evidence_ids")),
            citation_refs=_string_list(payload.get("citation_refs")),
            high_risk=_bool_value(payload.get("high_risk")),
            gap_reason=str(payload.get("gap_reason") or "").strip(),
        )


@dataclass(slots=True)
class CoverageDimension:
    dimension_id: str
    status: DimensionCoverageStatus = "evidence_scarce"
    body_evidence: bool = False
    covered_actions: list[str] = field(default_factory=list)
    missing_actions: list[str] = field(default_factory=list)
    action_coverage: list[CoverageAction] = field(default_factory=list)
    high_authority_source: bool = False
    independent_source_count: int = 0
    cross_validation_required: bool = False
    conflicts: list[str] = field(default_factory=list)
    temporal_conflicts: list[str] = field(default_factory=list)
    terminology_ambiguities: list[str] = field(default_factory=list)
    model_only: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_count: int = 0
    saturation: float = 0.0
    gap_summary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoverageDimension":
        status = str(payload.get("status") or "evidence_scarce")
        if status not in {"covered", "partial", "evidence_scarce", "conflicting", "out_of_scope"}:
            status = "evidence_scarce"
        return cls(
            dimension_id=str(payload.get("dimension_id") or ""),
            status=status,  # type: ignore[arg-type]
            body_evidence=_bool_value(payload.get("body_evidence")),
            covered_actions=_string_list(payload.get("covered_actions")),
            missing_actions=_string_list(payload.get("missing_actions")),
            action_coverage=[
                CoverageAction.from_dict(item)
                for item in payload.get("action_coverage") or []
                if isinstance(item, dict)
            ],
            high_authority_source=_bool_value(payload.get("high_authority_source")),
            independent_source_count=max(0, _int_value(payload.get("independent_source_count"))),
            cross_validation_required=_bool_value(payload.get("cross_validation_required")),
            conflicts=_string_list(payload.get("conflicts")),
            temporal_conflicts=_string_list(payload.get("temporal_conflicts")),
            terminology_ambiguities=_string_list(payload.get("terminology_ambiguities")),
            model_only=_bool_value(payload.get("model_only")),
            evidence_ids=_string_list(payload.get("evidence_ids")),
            source_ids=_string_list(payload.get("source_ids")),
            evidence_count=max(0, _int_value(payload.get("evidence_count"))),
            saturation=_bounded_float(payload.get("saturation"), default=0.0),
            gap_summary=_string_list(payload.get("gap_summary")),
        )


@dataclass(slots=True)
class CoverageMatrix:
    dimensions: list[CoverageDimension] = field(default_factory=list)
    iteration: int = 0
    target: float = 0.8
    overall_coverage: float = 0.0
    high_importance_coverage: float = 0.0
    saturation: float = 0.0
    stop_reason: str = ""
    exhausted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoverageMatrix":
        return cls(
            dimensions=[
                CoverageDimension.from_dict(item)
                for item in payload.get("dimensions") or []
                if isinstance(item, dict)
            ],
            iteration=max(0, _int_value(payload.get("iteration"))),
            target=_bounded_float(payload.get("target"), default=0.8),
            overall_coverage=_bounded_float(payload.get("overall_coverage"), default=0.0),
            high_importance_coverage=_bounded_float(
                payload.get("high_importance_coverage"), default=0.0
            ),
            saturation=_bounded_float(payload.get("saturation"), default=0.0),
            stop_reason=str(payload.get("stop_reason") or "").strip(),
            exhausted=_bool_value(payload.get("exhausted")),
        )

    def by_dimension(self) -> dict[str, CoverageDimension]:
        return {item.dimension_id: item for item in self.dimensions if item.dimension_id}


@dataclass(slots=True)
class DynamicResearchBudget:
    depth: str = "standard"
    complexity_score: float = 0.5
    major_dimension_limit: int = 8
    breadth_query_limit: int = 10
    depth_query_limit: int = 6
    evidence_limit: int = 16
    web_fetch_limit: int = 4
    web_fetch_attempts: int = 8
    max_gap_iterations: int = 1
    per_dimension_min_queries: int = 1
    per_dimension_min_evidence: int = 1
    section_length_budgets: dict[str, int] = field(default_factory=dict)
    total_output_chars: int = 6000
    token_budget: int = 75000
    timeout_seconds: int = 240
    global_hard_limits: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DynamicResearchBudget":
        return cls(
            depth=str(payload.get("depth") or "standard"),
            complexity_score=_bounded_float(payload.get("complexity_score"), default=0.5),
            major_dimension_limit=max(1, _int_value(payload.get("major_dimension_limit"), default=8)),
            breadth_query_limit=max(1, _int_value(payload.get("breadth_query_limit"), default=10)),
            depth_query_limit=max(0, _int_value(payload.get("depth_query_limit"), default=6)),
            evidence_limit=max(1, _int_value(payload.get("evidence_limit"), default=16)),
            web_fetch_limit=max(1, _int_value(payload.get("web_fetch_limit"), default=4)),
            web_fetch_attempts=max(1, _int_value(payload.get("web_fetch_attempts"), default=8)),
            max_gap_iterations=max(0, _int_value(payload.get("max_gap_iterations"), default=1)),
            per_dimension_min_queries=max(
                0, _int_value(payload.get("per_dimension_min_queries"), default=1)
            ),
            per_dimension_min_evidence=max(
                0, _int_value(payload.get("per_dimension_min_evidence"), default=1)
            ),
            section_length_budgets=_int_dict(payload.get("section_length_budgets")),
            total_output_chars=max(1, _int_value(payload.get("total_output_chars"), default=6000)),
            token_budget=max(1, _int_value(payload.get("token_budget"), default=75000)),
            timeout_seconds=max(1, _int_value(payload.get("timeout_seconds"), default=240)),
            global_hard_limits=_int_dict(payload.get("global_hard_limits")),
        )


@dataclass(slots=True)
class SourcePlan:
    id: str
    dimension_id: str
    evidence_needs: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    query_intents: list[str] = field(default_factory=list)
    recency_requirement: str = "unspecified"
    authority_threshold: float = 0.7
    cross_check_required: bool = False
    budget: dict[str, int] = field(default_factory=dict)
    fallback_order: list[str] = field(default_factory=list)
    model_role: str = "analysis_and_query_expansion"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "SourcePlan":
        return cls(
            id=str(payload.get("id") or f"source-plan-{index + 1}"),
            dimension_id=str(payload.get("dimension_id") or ""),
            evidence_needs=_string_list(payload.get("evidence_needs")),
            source_types=_string_list(payload.get("source_types")),
            source_ids=_string_list(payload.get("source_ids")),
            query_intents=_string_list(payload.get("query_intents")),
            recency_requirement=str(payload.get("recency_requirement") or "unspecified"),
            authority_threshold=_bounded_float(payload.get("authority_threshold"), default=0.7),
            cross_check_required=_bool_value(payload.get("cross_check_required")),
            budget=_int_dict(payload.get("budget")),
            fallback_order=_string_list(payload.get("fallback_order")),
            model_role=str(payload.get("model_role") or "analysis_and_query_expansion"),
        )


@dataclass(slots=True)
class SectionClaim:
    id: str
    text: str
    claim_type: str = "analysis"
    evidence_ids: list[str] = field(default_factory=list)
    citation_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    limitations: list[str] = field(default_factory=list)
    relationship: str = "supports"
    externally_supported: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "SectionClaim":
        return cls(
            id=str(payload.get("id") or f"section-claim-{index + 1}"),
            text=str(payload.get("text") or payload.get("claim") or "").strip(),
            claim_type=str(payload.get("claim_type") or payload.get("type") or "analysis"),
            evidence_ids=_string_list(payload.get("evidence_ids")),
            citation_refs=_string_list(payload.get("citation_refs") or payload.get("evidence_refs")),
            confidence=_bounded_float(payload.get("confidence"), default=0.5),
            limitations=_string_list(payload.get("limitations")),
            relationship=str(payload.get("relationship") or "supports"),
            externally_supported=_bool_value(payload.get("externally_supported")),
        )


@dataclass(slots=True)
class SectionDraft:
    section_id: str
    title: str
    dimension_ids: list[str] = field(default_factory=list)
    research_questions: list[str] = field(default_factory=list)
    claims: list[SectionClaim] = field(default_factory=list)
    content: str = ""
    coverage_status: str = "evidence_scarce"
    conflicts: list[str] = field(default_factory=list)
    unresolved_gaps: list[str] = field(default_factory=list)
    suggested_length: int = 0
    synthesis_priority: float = 0.5
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SectionDraft":
        return cls(
            section_id=str(payload.get("section_id") or payload.get("id") or ""),
            title=str(payload.get("title") or "").strip(),
            dimension_ids=_string_list(payload.get("dimension_ids")),
            research_questions=_string_list(
                payload.get("research_questions") or payload.get("questions_to_answer")
            ),
            claims=[
                SectionClaim.from_dict(item, index=index)
                for index, item in enumerate(payload.get("claims") or [])
                if isinstance(item, dict)
            ],
            content=str(payload.get("content") or "").strip(),
            coverage_status=str(payload.get("coverage_status") or "evidence_scarce"),
            conflicts=_string_list(payload.get("conflicts")),
            unresolved_gaps=_string_list(payload.get("unresolved_gaps")),
            suggested_length=max(0, _int_value(payload.get("suggested_length"))),
            synthesis_priority=_bounded_float(payload.get("synthesis_priority"), default=0.5),
            verified=_bool_value(payload.get("verified")),
        )


@dataclass(slots=True)
class SectionEvidencePack:
    section_id: str
    questions: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    direct_evidence: list[dict[str, Any]] = field(default_factory=list)
    boundary_evidence: list[dict[str, Any]] = field(default_factory=list)
    counterexamples: list[dict[str, Any]] = field(default_factory=list)
    verified_claims: list[SectionClaim] = field(default_factory=list)
    distinctions: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    unresolved_gaps: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    allowed_citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SectionEvidencePack":
        return cls(
            section_id=str(payload.get("section_id") or "").strip(),
            questions=_string_list(payload.get("questions")),
            required_actions=_string_list(payload.get("required_actions")),
            direct_evidence=[dict(item) for item in payload.get("direct_evidence") or [] if isinstance(item, dict)],
            boundary_evidence=[dict(item) for item in payload.get("boundary_evidence") or [] if isinstance(item, dict)],
            counterexamples=[dict(item) for item in payload.get("counterexamples") or [] if isinstance(item, dict)],
            verified_claims=[
                SectionClaim.from_dict(item, index=index)
                for index, item in enumerate(payload.get("verified_claims") or [])
                if isinstance(item, dict)
            ],
            distinctions=_string_list(payload.get("distinctions")),
            mitigations=_string_list(payload.get("mitigations")),
            unresolved_gaps=_string_list(payload.get("unresolved_gaps")),
            forbidden_claims=_string_list(payload.get("forbidden_claims")),
            allowed_citations=_string_list(payload.get("allowed_citations")),
        )


@dataclass(slots=True)
class SectionContract:
    id: str
    title: str
    function: str
    dimension_ids: list[str] = field(default_factory=list)
    questions_to_answer: list[str] = field(default_factory=list)
    required_claim_types: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    comparison_axes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    coverage_target: float = 0.75
    length_budget: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, index: int = 0) -> "SectionContract":
        return cls(
            id=str(payload.get("id") or f"section-{index + 1}"),
            title=str(payload.get("title") or f"Section {index + 1}").strip(),
            function=str(payload.get("function") or "direct_answer"),
            dimension_ids=_string_list(payload.get("dimension_ids")),
            questions_to_answer=_string_list(payload.get("questions_to_answer")),
            required_claim_types=_string_list(payload.get("required_claim_types")),
            evidence_requirements=_string_list(payload.get("evidence_requirements")),
            comparison_axes=_string_list(payload.get("comparison_axes")),
            dependencies=_string_list(payload.get("dependencies")),
            coverage_target=_bounded_float(payload.get("coverage_target"), default=0.75),
            length_budget=max(0, _int_value(payload.get("length_budget"))),
        )


@dataclass(slots=True)
class ReportOutline:
    query_archetype: str
    audience: str = "researcher"
    scope: str = ""
    answer_strategy: str = ""
    sections: list[SectionContract] = field(default_factory=list)
    cross_section_synthesis: list[str] = field(default_factory=list)
    citation_policy: str = "cite externally verifiable claims with acquired body evidence"
    reliability_policy: str = "separate external facts from model analysis and disclose gaps"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReportOutline":
        return cls(
            query_archetype=str(payload.get("query_archetype") or "general_exploration"),
            audience=str(payload.get("audience") or "researcher"),
            scope=str(payload.get("scope") or "").strip(),
            answer_strategy=str(payload.get("answer_strategy") or "").strip(),
            sections=[
                SectionContract.from_dict(item, index=index)
                for index, item in enumerate(payload.get("sections") or [])
                if isinstance(item, dict)
            ],
            cross_section_synthesis=_string_list(payload.get("cross_section_synthesis")),
            citation_policy=str(
                payload.get("citation_policy")
                or "cite externally verifiable claims with acquired body evidence"
            ),
            reliability_policy=str(
                payload.get("reliability_policy")
                or "separate external facts from model analysis and disclose gaps"
            ),
        )


def _bounded_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _importance_float(value: Any, *, default: float = 0.5) -> float:
    if isinstance(value, str):
        mapped = {
            "critical": 1.0,
            "high": 0.85,
            "medium": 0.6,
            "normal": 0.6,
            "low": 0.3,
        }.get(value.strip().casefold())
        if mapped is not None:
            return mapped
    return _bounded_float(value, default=default)


def _int_value(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "1", "on", "enabled"}:
            return True
        if normalized in {"false", "no", "0", "off", "disabled"}:
            return False
    return bool(value)


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        name = str(key).strip()
        if name:
            result[name] = _int_value(item)
    return result
