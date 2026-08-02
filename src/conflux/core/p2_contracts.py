"""P2 Project-Driven Paper Radar — core protocol types.

These Pydantic v2 models define the stable contracts for project-scoped paper
discovery, search intent generation, and project-paper linkage.  They extend
the M1 plugin protocol without modifying its contracts.

All models are JSON-serializable and versioned via ``p2_protocol_version``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── protocol versioning ───────────────────────────────────────────

P2_PROTOCOL_VERSION: str = "conflux.dev/p2/v1alpha1"


# ── project research config ────────────────────────────────────────

class PaperSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"


class Cadence(str, Enum):
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"


class ProjectResearchConfig(BaseModel):
    """Project-level research configuration (stored in project YAML)."""

    profile: str = Field(description="Path to ResearchProfile YAML, e.g. 'profiles/example_gis_agent.yaml'")
    sources: list[PaperSource] = Field(
        default_factory=lambda: [PaperSource.ARXIV, PaperSource.SEMANTIC_SCHOLAR]
    )
    cadence: Cadence = Field(default=Cadence.MANUAL)
    max_candidates: int = Field(default=100, ge=10, le=500)
    deep_read_limit: int = Field(default=5, ge=0, le=20)
    auto_generate_queries: bool = Field(default=True)
    require_query_review: bool = Field(default=True)
    require_plan_writeback_approval: bool = Field(default=True)
    track_overrides: list[str] = Field(
        default_factory=list,
        description="List of track ids to override profile defaults; empty = use all profile tracks",
    )


# ── track & query spec ─────────────────────────────────────────────

class TrackQuery(BaseModel):
    """A single query within a research Track."""

    terms: str = Field(description="Boolean search terms, e.g. 'GIS agent OR geospatial LLM'")
    suffix: str = Field(
        default="",
        description="Appended to every query, e.g. 'workflow OR execution'",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="arXiv categories, e.g. ['cs.AI', 'cs.CL']",
    )
    date_window_days: int = Field(default=365, ge=1, description="Look-back window in days")
    priority: int = Field(default=50, ge=0, le=100)


class Track(BaseModel):
    """A human-designed research Track that groups related queries."""

    id: str = Field(description="Unique track id, e.g. 'runtime_reliability'")
    name: str = Field(description="Human-readable track name")
    description: str = Field(default="")
    related_rqs: list[str] = Field(
        default_factory=list, description="Related research question indices/ids"
    )
    queries: list[TrackQuery] = Field(default_factory=list)
    budget_ratio: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Fraction of total search budget allocated to this track",
    )


class QuerySpec(BaseModel):
    """A fully-resolved query ready for execution against a paper source."""

    id: str = Field(description="Unique query-spec id (deterministic hash of source+query)")
    track_id: str = Field(default="")
    source: PaperSource
    query: str = Field(description="Final resolved query string sent to the source API")
    categories: list[str] = Field(default_factory=list)
    date_window_days: int = Field(default=365)
    max_results: int = Field(default=20, ge=1, le=100)
    priority: int = Field(default=50, ge=0, le=100)
    provenance: str = Field(
        default="",
        description="How this query was generated: 'track_manual' | 'intent_auto' | 'gap_fill'",
    )
    profile_version: str = Field(default="", description="SHA of profile at generation time")
    context_version: str = Field(default="", description="SHA of project context at generation time")


# ── project research context ───────────────────────────────────────

class SearchIntentType(str, Enum):
    CORE_TOPIC = "core_topic"
    MILESTONE = "milestone"
    BLOCKER = "blocker"
    EVIDENCE_GAP = "evidence_gap"
    COMPETITOR = "competitor"
    DATASET_METRIC = "dataset_metric"


class SearchIntent(BaseModel):
    """A search intention derived from project context."""

    id: str = Field(description="Deterministic id derived from context hash + type + summary")
    project_id: str
    type: SearchIntentType
    summary: str = Field(description="One-sentence description of what this intent searches for")
    query_terms: list[str] = Field(default_factory=list)
    expected_evidence_types: list[str] = Field(
        default_factory=list,
        description="method | dataset | baseline | metric | background | counterexample | competitor",
    )
    related_rq_ids: list[str] = Field(default_factory=list)
    related_milestone_ids: list[str] = Field(default_factory=list)
    related_risk_ids: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    source_refs: list[str] = Field(
        default_factory=list,
        description="Project YAML keys or document paths that justify this intent",
    )
    context_version: str = Field(default="")
    status: Literal["proposed", "active", "archived"] = "proposed"


class EvidenceGap(BaseModel):
    """A known evidence gap derived from project audit."""

    id: str
    description: str
    related_rq_ids: list[str] = Field(default_factory=list)
    related_milestone_ids: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class ProjectResearchContext(BaseModel):
    """Runtime context assembled from ProjectDefinition + ResearchProfile + audit."""

    project_id: str
    project_revision: str = Field(default="", description="Content hash of project YAML at assembly time")
    profile_id: str = ""
    profile_version: str = ""
    overall_goal: str = ""
    research_questions: list[str] = Field(default_factory=list)
    active_milestones: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    current_risks: list[str] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    source_refs: list[str] = Field(
        default_factory=list,
        description="Files that contributed to this context (project YAML, audit reports, etc.)",
    )


# ── paper identity & project linkage ───────────────────────────────

class PaperIdentity(BaseModel):
    """Globally-unique paper identity.  One identity = one paper, regardless of source."""

    source: str = Field(description="Primary source: 'arxiv' | 'semantic_scholar' | 'openalex' | 'crossref'")
    canonical_id: str = Field(description="Source-specific canonical id, e.g. arXiv '2405.12345v1'")
    version: str = Field(default="", description="Version string if applicable, e.g. 'v2'")
    doi: str = Field(default="")
    title_hash: str = Field(default="", description="SHA-256 of normalized title for cross-source matching")

    @property
    def dedup_key(self) -> str:
        """Return the strongest available deduplication key."""
        return self.doi or f"{self.source}:{self.canonical_id}"


class PaperLinkStatus(str, Enum):
    DISCOVERED = "discovered"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    SAVED = "saved"
    PROMOTED = "promoted"
    NEEDS_REVIEW = "needs_review"


class EvidenceUtility(str, Enum):
    METHOD = "method"
    DATASET = "dataset"
    BASELINE = "baseline"
    METRIC = "metric"
    BACKGROUND = "background"
    COUNTEREXAMPLE = "counterexample"
    COMPETITOR = "competitor"
    NONE = "none"


class ProjectPaperLink(BaseModel):
    """Project-scoped paper state.  One paper can have different links per project."""

    project_id: str
    paper_identity: PaperIdentity
    status: PaperLinkStatus = PaperLinkStatus.DISCOVERED
    matched_intent_ids: list[str] = Field(default_factory=list)
    matched_track_ids: list[str] = Field(default_factory=list)
    matched_rq_ids: list[str] = Field(default_factory=list)
    matched_milestone_ids: list[str] = Field(default_factory=list)
    evidence_utility: EvidenceUtility = EvidenceUtility.NONE
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    review_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    profile_version: str = ""
    context_version: str = ""
    prompt_version: str = ""
    model_version: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── project impact suggestion ──────────────────────────────────────

class ImpactSuggestionType(str, Enum):
    LINK_EVIDENCE = "link_evidence"
    CREATE_NEXT_ACTION = "create_next_action"
    CREATE_RISK = "create_risk"
    PROPOSE_EXPERIMENT = "propose_experiment"
    UPDATE_SEARCH_INTENT = "update_search_intent"


class ProjectImpactSuggestion(BaseModel):
    """A reviewable suggestion for project or knowledge updates, backed by paper evidence."""

    id: str = Field(description="Unique suggestion id")
    project_id: str
    paper_identity: PaperIdentity
    type: ImpactSuggestionType
    target_id: str = Field(default="", description="Milestone, risk, or RQ id this targets")
    summary: str = Field(description="One-sentence suggestion")
    rationale: str = Field(default="")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="References to paper sections, chunks, or evidence ids",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: Literal["proposed", "accepted", "rejected", "applied"] = "proposed"
    created_by_run: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── radar run result ───────────────────────────────────────────────

class RadarRunStats(BaseModel):
    """Aggregate statistics for a single radar run."""

    project_id: str
    run_id: str
    total_candidates: int = 0
    after_dedup: int = 0
    after_negative_filter: int = 0
    after_coarse_rank: int = 0
    shortlisted: int = 0
    deep_read: int = 0
    saved: int = 0
    rejected: int = 0
    suggestions_proposed: int = 0
    sources_used: list[str] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list)
    intent_count: int = 0
    query_count: int = 0
    # LLM deep-analysis telemetry (Phase P2 real-API integration)
    llm_calls: int = 0
    llm_total_tokens: int = 0
    llm_elapsed_ms: int = 0
    llm_fallback_count: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    elapsed_seconds: float = 0.0


class RadarRunResult(BaseModel):
    """Complete result of one paper radar run for a project."""

    project_id: str
    context: ProjectResearchContext
    intents: list[SearchIntent] = Field(default_factory=list)
    queries: list[QuerySpec] = Field(default_factory=list)
    links: list[ProjectPaperLink] = Field(default_factory=list)
    suggestions: list[ProjectImpactSuggestion] = Field(default_factory=list)
    stats: RadarRunStats = Field(default_factory=lambda: RadarRunStats(project_id="", run_id=""))
