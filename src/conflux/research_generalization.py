"""Pure P1.5 planning, coverage, budgeting, and report-contract helpers."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import replace
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .query_planner import concept_alias_groups
from .research_protocol import (
    CoverageAction,
    CoverageDimension,
    CoverageMatrix,
    DomainMap,
    DynamicResearchBudget,
    QueryArchetype,
    ReportOutline,
    ResearchDimension,
    ResearchStrategy,
    ScopeContract,
    SectionClaim,
    SectionContract,
    SectionDraft,
    SectionEvidencePack,
    SourcePlan,
)


ARCHETYPE_SPECS: dict[str, dict[str, Any]] = {
    "method_survey": {
        "patterns": (
            r"方法(?:有|包括|综述|分类|路线)",
            r"技术(?:有|包括|综述|分类|路线)",
            r"(?:有哪些|有什么|主要有哪些).{0,10}(?:方法|技术|方案|路径)",
            r"(?:methods?|approaches?|techniques?)\s+(?:(?:are|is)\s+)?(?:existing|available|used)",
            r"\b(?:method|technology)\s+(?:survey|taxonomy|landscape)\b",
        ),
        "actions": (
            "define_scope",
            "discover_taxonomy",
            "explain_mechanisms",
            "identify_representative_implementations",
            "assess_applicability",
            "compare_strengths_and_limits",
            "assess_maturity",
            "identify_combinations",
        ),
        "synthesis": ("taxonomy_synthesis", "mechanism_synthesis", "comparative_synthesis"),
        "dimensions": (
            "分类与范围",
            "机制与代表实现",
            "适用条件与成熟度",
            "优势、限制与组合关系",
        ),
    },
    "state_and_trends": {
        "patterns": (
            r"现状|进展|趋势|发展脉络|演进|最新状态|当前状态",
            r"\bstate\s+of\s+the\s+art\b",
            r"\b(?:current status|progress|trend|evolution|landscape|recent advances?)\b",
            r"\bas\s+of\s+(?:20\d{2}|today|now)\b",
            r"\bwhat\s+is\s+the\s+(?:current\s+)?state\s+of\b",
            r"\b(?:implementation|deployment|adoption|migration|rollout)\s+status\b",
        ),
        "actions": (
            "define_scope",
            "establish_current_state",
            "trace_time_evolution",
            "identify_drivers",
            "assess_maturity",
            "identify_emerging_directions",
            "identify_open_questions",
        ),
        "synthesis": ("timeline_synthesis", "trend_synthesis", "maturity_synthesis"),
        "dimensions": (
            "当前状态与范围",
            "关键进展与时间演化",
            "驱动因素与趋势",
            "未决问题与不确定性",
        ),
    },
    "limitations_and_challenges": {
        "patterns": (
            r"局限|限制|挑战|瓶颈|失败模式|开放问题|研究空白|不足",
            r"\b(?:limitations?|challenges?|bottlenecks?|failure modes?|open problems?|research gaps?)\b",
            r"\bwhat\b.{0,32}\blimits?\b",
            r"\b(?:main|key|major|principal)\s+limitations?\s+of\b",
        ),
        "actions": (
            "define_scope",
            "identify_limitations",
            "explain_failure_mechanisms",
            "assess_impact",
            "identify_boundary_conditions",
            "review_mitigations",
            "identify_open_questions",
        ),
        "synthesis": ("limitation_synthesis", "causal_synthesis", "boundary_synthesis"),
        "dimensions": (
            "范围与成熟度边界",
            "机制与方法限制",
            "实施与运行约束",
            "评估、风险与开放问题",
        ),
    },
    "comparison": {
        "patterns": (
            r"比较|对比|区别|差异|优劣|共同.*特有|孰优",
            r"\b(?:compare|comparison|versus|vs\.?|differences?|trade-?offs?)\b",
            r"\b(?:differ|differs|differed|differing)\b",
        ),
        "actions": (
            "define_comparison_scope",
            "establish_common_baseline",
            "identify_comparison_axes",
            "compare_mechanisms",
            "compare_evidence",
            "compare_applicability",
            "identify_tradeoffs",
        ),
        "synthesis": ("comparative_synthesis", "tradeoff_synthesis", "boundary_synthesis"),
        "dimensions": (
            "比较对象与共同基线",
            "能力与机制差异",
            "证据、性能与成熟度",
            "适用条件、权衡与边界",
        ),
    },
    "causal_mechanism": {
        "patterns": (
            r"为什么|原因|因果|机制|作用机理|如何影响|导致|驱动因素",
            r"\b(?:why|cause|causal|mechanism|impact|effect|driver)\b",
        ),
        "actions": (
            "define_causal_scope",
            "identify_causal_factors",
            "explain_mechanisms",
            "assess_evidence_strength",
            "test_alternative_explanations",
            "identify_boundary_conditions",
            "trace_feedback",
        ),
        "synthesis": ("causal_synthesis", "mechanism_synthesis", "uncertainty_synthesis"),
        "dimensions": (
            "因果对象与边界",
            "作用机制与中介因素",
            "证据强度与替代解释",
            "影响、边界条件与反馈",
        ),
    },
    "solution_design": {
        "patterns": (
            r"如何(?:设计|构建|建立|实施|解决|选择|制定|迁移|部署|改进)",
            r"解决方案|实施路径|技术路线|参考架构|架构设计|路线图",
            r"\b(?:design|architecture|implementation plan|roadmap|solution|how to build|how to implement)\b",
        ),
        "actions": (
            "define_objectives",
            "identify_constraints",
            "design_candidate_architectures",
            "explain_key_mechanisms",
            "plan_implementation",
            "identify_dependencies",
            "define_validation",
            "assess_risks_and_tradeoffs",
        ),
        "synthesis": ("design_synthesis", "implementation_synthesis", "risk_synthesis"),
        "dimensions": (
            "目标、约束与成功标准",
            "候选架构与关键机制",
            "实施路径与依赖",
            "验证、风险与迭代",
        ),
    },
    "evidence_review": {
        "patterns": (
            r"证据综述|系统综述|元分析|共识|争议评估|证据强度|文献证据",
            r"\b(?:systematic review|meta-analysis|evidence review|consensus|controversy|quality of evidence)\b",
            r"\bwhat\s+is\s+the\s+evidence\s+that\b",
            r"\bwhat\s+does\s+(?:the\s+)?(?:current\s+)?evidence\s+(?:show|say|indicate)\b",
        ),
        "actions": (
            "define_review_scope",
            "define_evidence_criteria",
            "collect_review_and_primary_evidence",
            "assess_evidence_quality",
            "identify_consensus",
            "analyze_heterogeneity",
            "analyze_conflicts",
            "identify_evidence_gaps",
        ),
        "synthesis": ("evidence_synthesis", "consensus_synthesis", "conflict_synthesis"),
        "dimensions": (
            "研究范围与证据标准",
            "主要证据与共识",
            "异质性、冲突与争议",
            "证据缺口与结论边界",
        ),
    },
    "general_exploration": {
        "patterns": (),
        "actions": (
            "define_scope",
            "discover_key_concepts",
            "discover_dimensions",
            "collect_representative_evidence",
            "explain_relationships",
            "identify_boundaries_and_gaps",
        ),
        "synthesis": ("direct_answer", "relationship_synthesis", "gap_synthesis"),
        "dimensions": (
            "范围与核心概念",
            "主要机制或组成",
            "证据与代表实例",
            "边界、争议与待研究问题",
        ),
    },
}


_EVIDENCE_TYPES: dict[str, tuple[str, ...]] = {
    "method_survey": (
        "scholarly_review",
        "primary_research",
        "technical_documentation",
        "benchmark",
        "source_repository",
    ),
    "state_and_trends": (
        "official_document",
        "recent_research",
        "version_notes",
        "authoritative_report",
    ),
    "limitations_and_challenges": (
        "scholarly_review",
        "primary_research",
        "benchmark",
        "case_study",
    ),
    "comparison": (
        "primary_research",
        "benchmark",
        "official_document",
        "technical_documentation",
    ),
    "causal_mechanism": (
        "primary_research",
        "scholarly_review",
        "authoritative_report",
    ),
    "solution_design": (
        "official_document",
        "standard_or_policy",
        "technical_documentation",
        "source_repository",
        "reproducible_material",
        "case_study",
    ),
    "evidence_review": (
        "systematic_review",
        "primary_research",
        "preprint",
        "authoritative_report",
    ),
    "general_exploration": (
        "scholarly_review",
        "official_document",
        "primary_research",
        "case_study",
    ),
}


_ACTION_DIMENSION_TITLES: dict[str, str] = {
    "define_scope": "核心对象与研究范围",
    "define_comparison_scope": "比较范围与对象边界",
    "define_causal_scope": "因果对象与分析边界",
    "define_review_scope": "综述范围与纳入边界",
    "define_objectives": "目标、约束与成功标准",
    "define_evidence_criteria": "证据标准与质量等级",
    "discover_key_concepts": "关键概念与术语边界",
    "discover_dimensions": "分类结构与维度关系",
    "discover_taxonomy": "分类体系与方法谱系",
    "establish_current_state": "当前状态与事实基线",
    "establish_common_baseline": "共同基线与可比条件",
    "trace_time_evolution": "时间演化与关键转折",
    "trace_feedback": "反馈路径与动态效应",
    "identify_drivers": "驱动因素与变化条件",
    "identify_causal_factors": "因果因素与中介变量",
    "identify_comparison_axes": "比较轴与评价标准",
    "identify_representative_implementations": "代表实现与案例证据",
    "identify_emerging_directions": "新兴方向与趋势信号",
    "identify_limitations": "主要局限与失败模式",
    "identify_boundary_conditions": "适用边界与例外条件",
    "identify_constraints": "实施约束与关键依赖",
    "identify_dependencies": "系统依赖与组合关系",
    "identify_consensus": "研究共识与稳定结论",
    "identify_evidence_gaps": "证据缺口与待研究问题",
    "identify_open_questions": "开放问题与不确定性",
    "identify_tradeoffs": "关键权衡与选择条件",
    "identify_combinations": "组合关系与集成路径",
    "explain_mechanisms": "核心机制与作用路径",
    "explain_failure_mechanisms": "失败机制与影响链",
    "explain_key_mechanisms": "关键机制与架构作用",
    "compare_mechanisms": "机制差异与替代关系",
    "compare_evidence": "证据、性能与可信度比较",
    "compare_applicability": "适用场景与边界比较",
    "compare_strengths_and_limits": "优势、限制与关键权衡",
    "assess_applicability": "适用条件与场景边界",
    "assess_maturity": "成熟度、采用状态与趋势",
    "assess_impact": "影响、风险与实际后果",
    "assess_evidence_strength": "证据强度与因果可信度",
    "assess_evidence_quality": "证据质量、偏倚与直接性",
    "assess_risks_and_tradeoffs": "风险、成本与实施权衡",
    "review_mitigations": "缓解措施与剩余风险",
    "test_alternative_explanations": "替代解释、反例与混杂因素",
    "design_candidate_architectures": "候选架构与设计选择",
    "plan_implementation": "实施路径、阶段与资源",
    "define_validation": "验证指标、基准与验收方法",
    "collect_review_and_primary_evidence": "综述与原始研究证据",
    "collect_representative_evidence": "代表证据、案例与实现",
    "analyze_heterogeneity": "异质性、样本与方法差异",
    "analyze_conflicts": "来源冲突、争议与解释",
    "explain_relationships": "跨维度关系与综合机制",
    "identify_boundaries_and_gaps": "结论边界、争议与缺口",
}


_GENERIC_BREADTH_DIMENSIONS = (
    "核心对象与研究范围",
    "关键概念与术语边界",
    "分类结构与维度关系",
    "核心机制与作用路径",
    "代表实现、案例与数据",
    "适用条件、优势与局限",
    "成熟度、时间演化与趋势",
    "证据质量与交叉验证",
    "比较关系、替代与互补",
    "实施依赖、风险与验证",
    "争议、反例与开放问题",
)


_BUDGET_DEFAULTS: dict[str, dict[str, int]] = {
    "quick": {
        "major_dimension_limit": 4,
        "breadth_query_limit": 6,
        "depth_query_limit": 2,
        "evidence_limit": 8,
        "web_fetch_limit": 2,
        "web_fetch_attempts": 3,
        "max_gap_iterations": 0,
        "total_output_chars": 3000,
        "token_budget": 55000,
        "timeout_seconds": 180,
    },
    "standard": {
        "major_dimension_limit": 7,
        "breadth_query_limit": 12,
        "depth_query_limit": 7,
        "evidence_limit": 16,
        "web_fetch_limit": 4,
        "web_fetch_attempts": 7,
        "max_gap_iterations": 1,
        "total_output_chars": 6500,
        "token_budget": 75000,
        "timeout_seconds": 240,
    },
    "deep": {
        "major_dimension_limit": 10,
        "breadth_query_limit": 18,
        "depth_query_limit": 12,
        "evidence_limit": 26,
        "web_fetch_limit": 6,
        "web_fetch_attempts": 12,
        "max_gap_iterations": 2,
        "total_output_chars": 10000,
        "token_budget": 140000,
        "timeout_seconds": 480,
    },
}


_BUDGET_HARD_LIMITS: dict[str, dict[str, int]] = {
    "quick": {
        "major_dimension_limit": 6,
        "breadth_query_limit": 10,
        "depth_query_limit": 4,
        "evidence_limit": 14,
        "web_fetch_limit": 4,
        "web_fetch_attempts": 6,
        "max_gap_iterations": 1,
        "total_output_chars": 4500,
    },
    "standard": {
        "major_dimension_limit": 11,
        "breadth_query_limit": 20,
        "depth_query_limit": 14,
        "evidence_limit": 28,
        "web_fetch_limit": 7,
        "web_fetch_attempts": 14,
        "max_gap_iterations": 3,
        "total_output_chars": 10000,
    },
    "deep": {
        "major_dimension_limit": 15,
        "breadth_query_limit": 30,
        "depth_query_limit": 24,
        "evidence_limit": 40,
        "web_fetch_limit": 10,
        "web_fetch_attempts": 20,
        "max_gap_iterations": 4,
        "total_output_chars": 16000,
    },
}


def classify_query_archetype(query: str, *, user_intent: str = "") -> QueryArchetype:
    """Classify a query into one primary and optional secondary archetypes."""

    clean = _normalize_text(query)
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}
    for name, spec in ARCHETYPE_SPECS.items():
        if name == "general_exploration":
            continue
        hits = [pattern for pattern in spec["patterns"] if re.search(pattern, clean, re.IGNORECASE)]
        if hits:
            scores[name] = float(len(hits))
            matched[name] = hits

    if "comparison" in scores and _comparison_object_count(clean) >= 2:
        scores["comparison"] += 0.75
    if "state_and_trends" in scores and _is_temporal_query(clean):
        scores["state_and_trends"] += 0.5
    if "evidence_review" in scores and any(term in clean for term in ("共识", "争议", "证据强度")):
        scores["evidence_review"] += 0.5

    if not scores:
        spec = ARCHETYPE_SPECS["general_exploration"]
        return QueryArchetype(
            type="general_exploration",
            confidence=0.35,
            user_intent=user_intent.strip() or clean,
            expected_research_actions=list(spec["actions"]),
            required_synthesis_functions=list(spec["synthesis"]),
            selection_reason="未检测到足够明确的问题原型信号，使用通用探索流程。",
        )

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    primary, top_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    secondary = [
        name
        for name, score in ordered[1:]
        if score >= max(1.0, top_score * 0.55) and top_score - score <= 1.25
    ]
    margin = max(0.0, top_score - second_score)
    confidence = min(0.98, 0.5 + min(0.25, top_score * 0.1) + min(0.2, margin * 0.1))
    actions = list(ARCHETYPE_SPECS[primary]["actions"])
    synthesis = list(ARCHETYPE_SPECS[primary]["synthesis"])
    for name in secondary:
        actions = _unique([*actions, *ARCHETYPE_SPECS[name]["actions"]])
        synthesis = _unique([*synthesis, *ARCHETYPE_SPECS[name]["synthesis"]])
    reason = f"主类型 {primary} 命中 {len(matched.get(primary, []))} 组通用意图信号。"
    if secondary:
        reason += " 同时保留次类型：" + "、".join(secondary) + "。"
    return QueryArchetype(
        type=primary,  # type: ignore[arg-type]
        confidence=round(confidence, 3),
        user_intent=user_intent.strip() or clean,
        expected_research_actions=actions,
        required_synthesis_functions=synthesis,
        secondary_types=secondary,
        selection_reason=reason,
    )


def build_scope_contract(
    query: str,
    archetype: QueryArchetype | None = None,
    *,
    planner_payload: Mapping[str, Any] | None = None,
) -> ScopeContract:
    """Extract a conservative subject boundary before any model planning."""

    clean = _normalize_text(query)
    candidate = clean
    candidate = re.sub(r"^(?:请|请问|帮我|请帮我|分析|说明|阐述|综述|调研)\s*", "", candidate)
    candidate = re.sub(
        r"(?:目前|当前|现阶段|截至[^，,；;。?？]{0,24})?"
        r"(?:都)?(?:有)?(?:哪些|什么)(?:主要)?"
        r"(?:瓶颈|局限|限制|挑战|方法|技术|方案|问题|趋势|进展)?[？?。.]?$",
        "",
        candidate,
    ).strip(" ，,；;。?？:：")
    candidate = re.sub(
        r"\b(?:what|which|how|why)\b.{0,20}\b(?:limitations?|challenges?|bottlenecks?|methods?|approaches?)\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip(" ,;:.?")
    subject = candidate if len(candidate) >= 2 else clean

    planner = dict(planner_payload or {})
    planner_subject = str(planner.get("subject") or "").strip()
    planner_specificity = len(_normalize_key(planner_subject)) / max(1, len(_normalize_key(subject)))
    if (
        planner_subject
        and planner_specificity >= 0.6
        and _scope_subject_relevance(clean, planner_subject) >= 0.35
    ):
        subject = planner_subject

    latin_entities = re.findall(r"\b[A-Z][A-Z0-9.+_-]{1,14}\b", clean)
    named_entities = [
        item for item in re.findall(r"[A-Za-z][A-Za-z0-9.+_-]{2,}", subject)
        if item.casefold() not in {"the", "and", "for", "with", "current", "research"}
    ]
    planner_entities = [
        str(item).strip() for item in planner.get("required_entities") or []
        if str(item).strip()
    ]
    required_entities = _unique([*latin_entities, *named_entities, *planner_entities])[:12]
    inclusions = _unique([
        subject,
        *[str(item).strip() for item in planner.get("scope_inclusions") or [] if str(item).strip()],
    ])
    task = str(planner.get("task") or (archetype.type if archetype else "research")).strip()
    return ScopeContract(
        subject=subject,
        task=task,
        scope_inclusions=inclusions,
        scope_exclusions=[
            str(item).strip() for item in planner.get("scope_exclusions") or []
            if str(item).strip()
        ],
        time_scope=str(planner.get("time_scope") or "unspecified").strip(),
        audience=str(planner.get("audience") or "researcher").strip(),
        required_entities=required_entities,
        ambiguities=[
            str(item).strip() for item in planner.get("ambiguities") or []
            if str(item).strip()
        ],
        original_query=clean,
    )


def anchor_domain_map(domain_map: DomainMap, scope_contract: ScopeContract) -> DomainMap:
    """Keep fallback dimensions and their questions tied to the research subject."""

    subject = scope_contract.subject.strip() or domain_map.scope
    dimensions = []
    for dimension in domain_map.dimensions:
        questions = [
            _anchor_research_query(subject, question)
            for question in dimension.questions_to_answer
        ]
        dimensions.append(replace(
            dimension,
            questions_to_answer=_unique(questions),
            terminology=_unique([
                *dimension.terminology,
                subject,
                *scope_contract.required_entities,
            ]),
        ))
    return replace(
        domain_map,
        scope=scope_contract.original_query or domain_map.scope,
        key_concepts=_unique([
            subject,
            *scope_contract.required_entities,
            *domain_map.key_concepts,
        ])[:24],
        terminology=_unique([
            subject,
            *scope_contract.required_entities,
            *domain_map.terminology,
        ])[:40],
        dimensions=dimensions,
    )


def gate_evidence_items(
    evidence: Sequence[Mapping[str, Any] | Any],
    scope_contract: ScopeContract,
    *,
    domain_relevance_threshold: float = 0.7,
    claim_entailment_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Classify evidence before it may support coverage or report claims."""

    domain_threshold = max(0.0, min(1.0, float(domain_relevance_threshold)))
    entailment_threshold = max(0.0, min(1.0, float(claim_entailment_threshold)))
    gated: list[dict[str, Any]] = []
    for raw_item in evidence:
        item = _payload(raw_item)
        is_model = _is_model_item(item)
        body_valid = _evidence_body_valid(item, is_model=is_model)
        domain_relevance = _evidence_domain_relevance(item, scope_contract)
        claim_entailment = _evidence_claim_entailment(item, body_valid=body_valid)
        relationship = str(item.get("relationship") or "supports").casefold()

        if is_model:
            role = "model_analysis"
        elif not body_valid:
            role = "discovery_only"
        elif domain_relevance < domain_threshold:
            role = "analogy" if claim_entailment >= entailment_threshold else "discovery_only"
        elif claim_entailment < entailment_threshold:
            role = "discovery_only"
        elif relationship in {"contradicts", "conflicts", "counterexample"}:
            role = "counterexample"
        elif relationship in {"limits", "qualifies", "boundary"}:
            role = "boundary"
        else:
            role = "direct_support"

        gate_passed = role in {"direct_support", "boundary", "counterexample", "model_analysis"}
        gated.append({
            **item,
            "domain_relevance": round(domain_relevance, 3),
            "claim_entailment": round(claim_entailment, 3),
            "evidence_role": role,
            "source_identity": _source_identity(item),
            "body_valid": body_valid,
            "evidence_gate_passed": gate_passed,
        })
    return gated


def derive_research_strategy(archetype: QueryArchetype) -> ResearchStrategy:
    """Translate an archetype into generic discovery, depth, and stop actions."""

    actions = list(archetype.expected_research_actions)
    if not actions:
        actions = list(ARCHETYPE_SPECS.get(archetype.type, ARCHETYPE_SPECS["general_exploration"])["actions"])
    discovery_markers = ("define_", "discover_", "establish_", "identify_comparison_axes")
    discovery = [item for item in actions if item.startswith(discovery_markers)]
    if not discovery:
        discovery = actions[:2]
    depth = [item for item in actions if item not in discovery]
    return ResearchStrategy(
        primary_archetype=archetype.type,
        secondary_archetypes=list(archetype.secondary_types),
        rationale=archetype.selection_reason,
        discovery_actions=discovery,
        depth_actions=depth,
        required_synthesis_functions=list(archetype.required_synthesis_functions),
        stop_policy=[
            "high_importance_dimensions_reach_coverage_target",
            "evidence_and_dimension_saturation",
            "explicit_evidence_scarcity",
            "run_budget_or_deadline_exhausted",
        ],
        breadth_first=True,
    )


def deduplicate_dimensions(
    dimensions: Iterable[ResearchDimension | Mapping[str, Any] | str],
    *,
    similarity_threshold: float = 0.72,
) -> list[ResearchDimension]:
    """Merge lexically equivalent dimensions while preserving richer metadata."""

    merged: list[ResearchDimension] = []
    for index, value in enumerate(dimensions):
        dimension = _coerce_dimension(value, index=index)
        if not dimension.name:
            continue
        match_index = next(
            (
                existing_index
                for existing_index, existing in enumerate(merged)
                if _dimension_similarity(existing, dimension) >= similarity_threshold
            ),
            None,
        )
        if match_index is None:
            merged.append(dimension)
        else:
            merged[match_index] = _merge_dimension(merged[match_index], dimension)
    return merged


_MAJOR_JURISDICTION_OBJECTS = (
    (
        "eu",
        "欧盟",
        ("European Union", "EU", "GPAI", "general-purpose AI model", "AI Act"),
    ),
    (
        "us",
        "美国",
        ("United States", "US", "U.S.", "frontier AI", "BIS"),
    ),
    (
        "uk",
        "英国",
        ("United Kingdom", "UK", "foundation model", "AI regulation"),
    ),
    (
        "cn",
        "中国",
        ("China", "生成式人工智能", "generative AI", "网信办"),
    ),
)

_JURISDICTION_OFFICIAL_HOSTS = {
    "jurisdiction-eu": (
        "europa.eu",
        "eur-lex.europa.eu",
    ),
    "jurisdiction-us": (
        "bis.gov",
        "commerce.gov",
        "federalregister.gov",
        "nist.gov",
        "whitehouse.gov",
    ),
    "jurisdiction-uk": ("gov.uk",),
    "jurisdiction-cn": (
        "gov.cn",
        "cac.gov.cn",
    ),
}


def deterministic_comparison_dimensions(
    query: str,
    archetype: QueryArchetype,
) -> list[ResearchDimension]:
    """Build object-level dimensions when a comparison set is deterministic."""

    if archetype.type != "comparison" or not re.search(
        r"主要司法辖区|各司法辖区|major jurisdictions?|across jurisdictions?",
        str(query),
        re.IGNORECASE,
    ):
        return []
    subject = build_scope_contract(query, archetype).subject or _normalize_text(query)
    dimensions: list[ResearchDimension] = []
    for code, label, aliases in _MAJOR_JURISDICTION_OBJECTS:
        dimensions.append(ResearchDimension(
            id=f"jurisdiction-{code}",
            name=f"{label}：义务、适用范围与执行状态",
            inclusion_reason=(
                "问题要求比较主要司法辖区；该对象有可定位的官方规则、政策或监管材料。"
            ),
            questions_to_answer=[
                f"{label}针对{subject}规定或提出了哪些可核验义务与透明度机制？",
                f"这些要求适用于哪些提供者、模型或服务，当前法律状态和执行主体是什么？",
            ],
            expected_evidence_types=[
                "official_document",
                "standard_or_policy",
                "authoritative_report",
            ],
            required_actions=[
                "define_comparison_scope",
                "compare_mechanisms",
                "compare_applicability",
            ],
            cross_validation_required=False,
            importance=0.78,
            terminology=[label, *aliases, subject],
        ))
    dimensions.append(ResearchDimension(
        id="jurisdiction-cross-comparison",
        name="跨司法辖区：共同基线、比较轴与可核验差异",
        inclusion_reason="比较结论必须在统一口径下综合各对象，而不是并列摘录规则。",
        questions_to_answer=[
            f"围绕{subject}，各司法辖区共同要求披露什么，差异集中在哪些义务类型？",
            "适用门槛、法律状态、监管主体和执行方式如何影响可比性？",
        ],
        expected_evidence_types=[
            "official_document",
            "standard_or_policy",
            "authoritative_report",
        ],
        required_actions=[
            "establish_common_baseline",
            "identify_comparison_axes",
            "compare_mechanisms",
        ],
        cross_validation_required=True,
        importance=0.9,
        terminology=[
            subject,
            "transparency obligations",
            "reporting requirements",
            "technical documentation",
            "applicability threshold",
            "enforcement status",
        ],
    ))
    return dimensions


def build_domain_map(
    query: str,
    archetype: QueryArchetype,
    *,
    discovered_dimensions: Sequence[ResearchDimension | Mapping[str, Any] | str] | None = None,
    terminology: Sequence[str] | None = None,
    scope: str = "",
) -> DomainMap:
    """Build a bounded domain map from discovered dimensions or generic actions."""

    supplied_dimensions = bool(discovered_dimensions)
    inputs: list[ResearchDimension | Mapping[str, Any] | str] = list(discovered_dimensions or [])
    deterministic_dimensions: list[ResearchDimension] = []
    if not inputs:
        deterministic_dimensions = deterministic_comparison_dimensions(query, archetype)
        inputs.extend(deterministic_dimensions)
    if not inputs:
        inputs.extend(ARCHETYPE_SPECS.get(archetype.type, ARCHETYPE_SPECS["general_exploration"])["dimensions"])
        if _is_broad_query(query):
            inputs.extend(
                _ACTION_DIMENSION_TITLES[action]
                for action in archetype.expected_research_actions
                if action in _ACTION_DIMENSION_TITLES
            )
    dimensions = deduplicate_dimensions(inputs)
    if not supplied_dimensions and not deterministic_dimensions and _is_broad_query(query) and len(dimensions) < 8:
        for name in _GENERIC_BREADTH_DIMENSIONS:
            candidate = _coerce_dimension(name, index=len(dimensions))
            if all(_dimension_similarity(candidate, existing) < 0.78 for existing in dimensions):
                dimensions.append(candidate)
            if len(dimensions) >= 8:
                break
    evidence_types = list(_EVIDENCE_TYPES.get(archetype.type, _EVIDENCE_TYPES["general_exploration"]))
    normalized: list[ResearchDimension] = []
    for index, dimension in enumerate(dimensions[:15]):
        dimension_id = dimension.id
        if not dimension_id or dimension_id.startswith("dim-") and dimension_id[4:].isdigit():
            dimension_id = _dimension_id(dimension.name, index)
        questions = dimension.questions_to_answer or _dimension_questions(dimension.name, archetype.type)
        normalized.append(replace(
            dimension,
            id=dimension_id,
            inclusion_reason=dimension.inclusion_reason or "由问题原型的通用研究动作生成，待首轮证据复核。",
            questions_to_answer=questions,
            expected_evidence_types=dimension.expected_evidence_types or evidence_types,
            required_actions=list(dimension.required_actions),
            cross_validation_required=dimension.cross_validation_required,
            importance=max(dimension.importance, 0.85 if index == 0 else 0.7),
            stop_conditions=dimension.stop_conditions or [
                "取得直接正文证据并完成必要研究动作",
                "新增检索不再改变主要结论",
                "明确记录证据稀缺或超出范围",
            ],
        ))
    relations = _dimension_relations(normalized)
    key_concepts = _unique([
        *_key_concepts(query),
        *(dimension.name for dimension in normalized),
    ])[:24]
    terms = _unique([
        *(str(item).strip() for item in terminology or [] if str(item).strip()),
        *(term for dimension in normalized for term in dimension.terminology),
        *key_concepts,
    ])[:40]
    return DomainMap(
        scope=scope.strip() or _normalize_text(query),
        key_concepts=key_concepts,
        terminology=terms,
        dimensions=normalized,
        dimension_relations=relations,
        disputed_boundaries=(
            ["“主要司法辖区”在本轮操作化为欧盟、美国、英国和中国；其他司法辖区不在本轮比较范围内。"]
            if deterministic_dimensions else []
        ),
        discovery_sources=_unique([
            *list(_EVIDENCE_TYPES.get(archetype.type, _EVIDENCE_TYPES["general_exploration"])),
            *( ["deterministic_comparison_objects"] if deterministic_dimensions else [] ),
        ]),
    )


def merge_discovered_dimensions(
    domain_map: DomainMap,
    discovered_dimensions: Sequence[ResearchDimension | Mapping[str, Any] | str],
    *,
    query: str = "",
    scope_contract: ScopeContract | None = None,
    max_dimensions: int = 15,
) -> DomainMap:
    """Merge newly discovered dimensions after relevance scoring and deduplication."""

    accepted: list[ResearchDimension] = list(domain_map.dimensions)
    for index, value in enumerate(discovered_dimensions):
        dimension = _coerce_dimension(value, index=len(accepted) + index)
        relevance = _dimension_relevance(query or domain_map.scope, dimension)
        if scope_contract is not None:
            if not _dimension_has_scope_anchor(dimension, scope_contract) or relevance < 0.08:
                continue
        elif relevance < 0.08 and dimension.importance < 0.65 and not dimension.inclusion_reason:
            continue
        if relevance > 0:
            dimension = replace(dimension, importance=max(dimension.importance, min(0.9, 0.45 + relevance)))
        accepted.append(dimension)
    merged = deduplicate_dimensions(accepted)
    merged = sorted(
        enumerate(merged),
        key=lambda item: (-item[1].importance, item[0]),
    )[: max(1, int(max_dimensions))]
    dimensions = [item for _, item in merged]
    return DomainMap(
        scope=domain_map.scope,
        key_concepts=_unique([*domain_map.key_concepts, *(item.name for item in dimensions)])[:24],
        terminology=_unique([*domain_map.terminology, *(term for item in dimensions for term in item.terminology)])[:40],
        dimensions=dimensions,
        dimension_relations=_dimension_relations(dimensions),
        disputed_boundaries=list(domain_map.disputed_boundaries),
        discovery_sources=list(domain_map.discovery_sources),
    )


def _dimension_has_scope_anchor(
    dimension: ResearchDimension,
    scope_contract: ScopeContract,
) -> bool:
    """Require model-discovered dimensions to name the actual research subject."""

    dimension_text = " ".join([
        dimension.name,
        *dimension.questions_to_answer,
        *dimension.terminology,
    ])
    anchors = _unique([
        scope_contract.subject,
        *scope_contract.required_entities,
        *scope_contract.scope_inclusions,
    ])
    return any(
        _scope_subject_relevance(dimension_text, anchor) >= 0.25
        for anchor in anchors
        if _text_tokens(anchor)
    )


def estimate_query_complexity(
    query: str,
    archetype: QueryArchetype,
    domain_map: DomainMap,
    *,
    user_detail_level: str = "standard",
    source_health: Mapping[str, Any] | None = None,
) -> float:
    """Return a normalized complexity score from breadth, intent, and source health."""

    clean = _normalize_text(query)
    dimension_factor = min(1.0, len(domain_map.dimensions) / 12.0)
    action_factor = min(1.0, len(archetype.expected_research_actions) / 8.0)
    comparison_factor = min(1.0, max(0, _comparison_object_count(clean) - 1) / 4.0)
    temporal_factor = 1.0 if _is_temporal_query(clean) else 0.0
    broad_factor = 1.0 if _is_broad_query(clean) else 0.25
    detail_factor = {
        "brief": 0.1,
        "low": 0.1,
        "standard": 0.5,
        "medium": 0.5,
        "detailed": 0.85,
        "high": 0.85,
        "deep": 1.0,
    }.get(str(user_detail_level).casefold(), 0.5)
    health_factor = _source_stress(source_health or {})
    conflict_factor = min(
        1.0,
        sum(bool(item.conflicts or item.gaps) for item in domain_map.dimensions)
        / max(1, len(domain_map.dimensions)),
    )
    score = (
        0.24 * dimension_factor
        + 0.15 * action_factor
        + 0.12 * comparison_factor
        + 0.1 * temporal_factor
        + 0.13 * broad_factor
        + 0.1 * detail_factor
        + 0.1 * health_factor
        + 0.06 * conflict_factor
    )
    if _is_narrow_query(clean) and len(domain_map.dimensions) <= 4:
        score -= 0.15
    return round(max(0.05, min(1.0, score)), 3)


def allocate_dynamic_budget(
    depth: str,
    query: str,
    archetype: QueryArchetype,
    domain_map: DomainMap,
    *,
    source_health: Mapping[str, Any] | None = None,
    base_profile: Mapping[str, Any] | None = None,
    hard_limits: Mapping[str, Any] | None = None,
) -> DynamicResearchBudget:
    """Allocate a run budget from a depth baseline, complexity, and hard caps."""

    normalized_depth = _normalize_depth(depth)
    base = dict(_BUDGET_DEFAULTS[normalized_depth])
    hard = dict(_BUDGET_HARD_LIMITS[normalized_depth])
    profile = dict(base_profile or {})
    if profile:
        base["token_budget"] = _positive_int(profile.get("token_budget"), base["token_budget"])
        base["timeout_seconds"] = _positive_int(profile.get("timeout_seconds"), base["timeout_seconds"])
        base["max_gap_iterations"] = max(
            base["max_gap_iterations"],
            _nonnegative_int(profile.get("max_gap_iterations"), base["max_gap_iterations"]),
        )
        profile_evidence = _positive_int(profile.get("final_evidence_limit"), 0)
        if profile_evidence:
            base["evidence_limit"] = max(base["evidence_limit"], profile_evidence)
        for key in ("web_fetch_limit", "web_fetch_attempts"):
            if key in profile:
                base[key] = max(base[key], _positive_int(profile.get(key), base[key]))
    for key, value in dict(hard_limits or {}).items():
        normalized = {
            "max_dimensions": "major_dimension_limit",
            "max_breadth_queries": "breadth_query_limit",
            "max_depth_queries": "depth_query_limit",
            "max_evidence": "evidence_limit",
            "max_final_evidence": "evidence_limit",
            "max_web_fetches": "web_fetch_limit",
            "max_web_fetch_attempts": "web_fetch_attempts",
            "max_coverage_iterations": "max_gap_iterations",
            "max_output_chars": "total_output_chars",
            "max_report_chars": "total_output_chars",
        }.get(str(key), str(key))
        if normalized in hard:
            if normalized == "max_gap_iterations":
                hard[normalized] = _nonnegative_int(value, hard[normalized])
            else:
                hard[normalized] = _positive_int(value, hard[normalized])

    complexity = estimate_query_complexity(
        query,
        archetype,
        domain_map,
        user_detail_level="deep" if normalized_depth == "deep" else "standard",
        source_health=source_health,
    )
    scale = 0.62 + 0.82 * complexity
    stress = _source_stress(source_health or {})

    def scaled(key: str, *, minimum: int = 1, stress_weight: float = 0.0) -> int:
        value = round(base[key] * (scale + stress * stress_weight))
        return max(minimum, min(hard[key], value))

    actual_dimensions = len([item for item in domain_map.dimensions if item.current_coverage != "out_of_scope"])
    major_dimension_limit = max(
        min(actual_dimensions, hard["major_dimension_limit"]),
        scaled("major_dimension_limit"),
    )
    breadth_query_limit = max(
        min(actual_dimensions, hard["breadth_query_limit"]),
        scaled("breadth_query_limit", stress_weight=0.12),
    )
    depth_query_limit = scaled("depth_query_limit", minimum=0, stress_weight=0.22)
    evidence_limit = scaled("evidence_limit", stress_weight=0.08)
    web_fetch_limit = scaled("web_fetch_limit", stress_weight=0.18)
    web_fetch_attempts = max(
        web_fetch_limit,
        scaled("web_fetch_attempts", stress_weight=0.3),
    )
    # When local retrieval is unavailable, spend the configured Web hard cap on
    # a broad query so every discovered dimension can still receive a route.
    if (
        _is_broad_query(query)
        and not _source_available(source_health or {}, "RAG")
        and _source_available(source_health or {}, "Web")
    ):
        web_fetch_limit = hard["web_fetch_limit"]
        web_fetch_attempts = hard["web_fetch_attempts"]
    max_gap_iterations = scaled("max_gap_iterations", minimum=0, stress_weight=0.25)
    total_output_chars = scaled("total_output_chars")
    if _is_narrow_query(query):
        major_dimension_limit = max(
            1,
            min(actual_dimensions or 1, hard["major_dimension_limit"], 5),
        )
        breadth_query_limit = min(
            hard["breadth_query_limit"],
            max(major_dimension_limit, min(breadth_query_limit, major_dimension_limit * 2)),
        )
        depth_query_limit = min(
            hard["depth_query_limit"],
            depth_query_limit,
            major_dimension_limit * (2 if normalized_depth == "deep" else 1),
        )
        evidence_limit = min(
            hard["evidence_limit"],
            evidence_limit,
            max(6, major_dimension_limit * 3),
        )
        web_fetch_limit = min(
            hard["web_fetch_limit"],
            web_fetch_limit,
            max(2, major_dimension_limit),
        )
        web_fetch_attempts = min(
            hard["web_fetch_attempts"],
            web_fetch_attempts,
            max(web_fetch_limit, web_fetch_limit * 2),
        )
        max_gap_iterations = min(max_gap_iterations, 1)
        total_output_chars = min(
            hard["total_output_chars"],
            total_output_chars,
            max(2500, major_dimension_limit * 1400),
        )
    elif normalized_depth == "deep" and _is_broad_query(query):
        evidence_limit = min(hard["evidence_limit"], max(20, evidence_limit))
        major_dimension_limit = max(min(8, hard["major_dimension_limit"]), major_dimension_limit)

    section_length_budgets = _allocate_section_lengths(
        domain_map.dimensions[:major_dimension_limit],
        total_output_chars,
    )
    hard_payload = {
        **hard,
        "token_budget": base["token_budget"],
        "timeout_seconds": base["timeout_seconds"],
    }
    return DynamicResearchBudget(
        depth=normalized_depth,
        complexity_score=complexity,
        major_dimension_limit=major_dimension_limit,
        breadth_query_limit=breadth_query_limit,
        depth_query_limit=depth_query_limit,
        evidence_limit=evidence_limit,
        web_fetch_limit=web_fetch_limit,
        web_fetch_attempts=web_fetch_attempts,
        max_gap_iterations=max_gap_iterations,
        per_dimension_min_queries=1,
        per_dimension_min_evidence=2 if normalized_depth == "deep" else 1,
        section_length_budgets=section_length_budgets,
        total_output_chars=total_output_chars,
        token_budget=base["token_budget"],
        timeout_seconds=base["timeout_seconds"],
        global_hard_limits=hard_payload,
    )


def build_source_plans(
    domain_map: DomainMap,
    archetype: QueryArchetype,
    *,
    coverage_matrix: CoverageMatrix | None = None,
    source_health: Mapping[str, Any] | None = None,
    budget: DynamicResearchBudget | None = None,
    authority_threshold: float = 0.75,
    scope_contract: ScopeContract | None = None,
) -> list[SourcePlan]:
    """Create one evidence-need-driven source route for each active dimension."""

    health = source_health or {}
    coverage = coverage_matrix.by_dimension() if coverage_matrix else {}
    active = [item for item in domain_map.dimensions if item.current_coverage != "out_of_scope"]
    plan_count = max(1, len(active))
    query_shares = _integer_budget_shares(
        budget.breadth_query_limit if budget else plan_count,
        plan_count,
    )
    evidence_shares = _integer_budget_shares(
        budget.evidence_limit if budget else plan_count * 2,
        plan_count,
    )
    fetch_shares = _integer_budget_shares(
        budget.web_fetch_limit if budget else plan_count,
        plan_count,
    )
    plans: list[SourcePlan] = []
    for index, dimension in enumerate(active):
        row = coverage.get(dimension.id)
        evidence_needs = _unique([
            *dimension.expected_evidence_types,
            *archetype.expected_research_actions,
            *(row.missing_actions if row else []),
        ])
        source_types = _unique([
            *dimension.expected_evidence_types,
            *_EVIDENCE_TYPES.get(archetype.type, _EVIDENCE_TYPES["general_exploration"]),
            "model_knowledge",
        ])
        web_first = _is_temporal_query(domain_map.scope) or any(
            item in source_types
            for item in ("official_document", "version_notes", "standard_or_policy")
        )
        authoritative_web_only = bool(
            dimension.id.startswith("jurisdiction-")
            and web_first
            and _source_available(health, "Web")
        )
        source_ids: list[str] = []
        if web_first and _source_available(health, "Web"):
            source_ids.append("builtin.web")
        if _source_available(health, "RAG") and not authoritative_web_only:
            source_ids.append("builtin.rag")
        if not web_first and _source_available(health, "Web"):
            source_ids.append("builtin.web")
        source_ids.append("builtin.model")
        cross_check = bool(
            dimension.cross_validation_required
            if dimension.cross_validation_required is not None
            else (
                archetype.type in {"comparison", "evidence_review"}
                or _is_temporal_query(domain_map.scope)
                or dimension.conflicts
                or (row and (row.status == "conflicting" or row.cross_validation_required))
            )
        )
        query_intents = dimension.questions_to_answer or [
            f"{dimension.name}需要哪些直接证据？",
        ]
        if scope_contract is not None:
            query_intents = [
                _anchor_research_query(scope_contract.subject, question)
                for question in query_intents
            ]
        fallback = list(source_ids[1:])
        if authoritative_web_only and _source_available(health, "RAG"):
            fallback.append("builtin.rag")
        plans.append(SourcePlan(
            id=f"source-plan-{index + 1}",
            dimension_id=dimension.id,
            evidence_needs=evidence_needs,
            source_types=source_types,
            source_ids=_unique(source_ids),
            query_intents=_unique(query_intents),
            recency_requirement="current" if _is_temporal_query(domain_map.scope) else "stable_or_current_as_needed",
            authority_threshold=min(
                1.0,
                max(0.0, float(authority_threshold)) + (0.05 if cross_check else 0.0),
            ),
            cross_check_required=cross_check,
            budget={
                "queries": query_shares[index],
                "evidence": evidence_shares[index],
                "web_fetches": fetch_shares[index] if "builtin.web" in source_ids else 0,
            },
            fallback_order=_unique(fallback),
            model_role="conceptual_framework_query_expansion_and_analysis",
        ))
    return plans


def build_coverage_matrix(
    domain_map: DomainMap,
    evidence: Sequence[Mapping[str, Any] | Any],
    *,
    archetype: QueryArchetype | None = None,
    previous: CoverageMatrix | None = None,
    authority_threshold: float = 0.75,
    min_external_evidence_per_dimension: int = 1,
    coverage_target: float = 0.8,
    domain_relevance_threshold: float = 0.7,
    claim_entailment_threshold: float = 0.7,
) -> CoverageMatrix:
    """Evaluate body evidence, research actions, authority, and conflicts by dimension."""

    items = [_payload(item) for item in evidence]
    rows: list[CoverageDimension] = []
    importance: dict[str, float] = {}
    for dimension in domain_map.dimensions:
        importance[dimension.id] = dimension.importance
        if dimension.current_coverage == "out_of_scope":
            rows.append(CoverageDimension(dimension_id=dimension.id, status="out_of_scope"))
            continue
        required_actions = list(
            dimension.required_actions
            or (archetype.expected_research_actions if archetype else [])
        )
        scoped = [item for item in items if _evidence_matches_dimension(item, dimension)]
        usable = [
            item for item in scoped
            if _item_status_allows_evidence(
                item,
                domain_relevance_threshold=domain_relevance_threshold,
                claim_entailment_threshold=claim_entailment_threshold,
            )
        ]
        evidence_ids = _unique([
            str(item.get("id") or item.get("evidence_id") or "").strip()
            for item in usable
            if str(item.get("id") or item.get("evidence_id") or "").strip()
        ])
        source_ids = _unique([
            str(item.get("source") or item.get("source_id") or "").strip()
            for item in usable
            if str(item.get("source") or item.get("source_id") or "").strip()
        ])
        model_items = [item for item in usable if _is_model_item(item)]
        external = [item for item in usable if not _is_model_item(item)]
        body = [item for item in external if _has_body_evidence(item)]
        detected_actions = _unique([
            action
            for item in usable
            for action in _evidence_actions(item)
        ])
        action_coverage = _build_action_coverage(required_actions, usable)
        covered_actions = [
            item.action for item in action_coverage
            if item.status in {"covered", "model_analysis", "conflicting"}
        ] if required_actions else detected_actions
        missing_actions = [
            item.action for item in action_coverage
            if item.status in {"gap", "model_analysis"} and (item.high_risk or item.status == "gap")
        ]
        high_authority = any(
            _evidence_authority(item) >= max(0.0, min(1.0, authority_threshold))
            for item in body
        )
        identities = {_source_identity(item) for item in body if _source_identity(item)}
        conflicts = _unique([
            str(item.get("conflict") or item.get("conflict_reason") or "").strip()
            for item in usable
            if str(item.get("conflict") or item.get("conflict_reason") or "").strip()
        ])
        conflicts.extend(
            str(item.get("claim") or item.get("text") or "").strip()
            for item in usable
            if str(item.get("relationship") or "").casefold() in {"contradicts", "conflicts"}
        )
        conflicts = _unique(conflicts)
        temporal_conflicts = _unique([
            str(value).strip()
            for item in usable
            for value in _as_list(item.get("temporal_conflicts"))
            if str(value).strip()
        ])
        terminology_ambiguities = _unique([
            str(value).strip()
            for item in usable
            for value in _as_list(item.get("terminology_ambiguities"))
            if str(value).strip()
        ])
        cross_validation_required = bool(
            dimension.cross_validation_required
            if dimension.cross_validation_required is not None
            else (
                dimension.importance >= 0.85
                or conflicts
                or temporal_conflicts
                or (archetype and archetype.type in {"comparison", "evidence_review"})
            )
        )
        action_ratio = (
            sum(item.status == "covered" for item in action_coverage) / len(action_coverage)
            if required_actions else 1.0
        )
        model_only = bool(usable) and len(model_items) == len(usable)
        saturation = _dimension_saturation(usable, body, identities, action_ratio)
        if conflicts or temporal_conflicts:
            status = "conflicting"
        elif len(body) >= max(1, int(min_external_evidence_per_dimension)) and high_authority and action_ratio >= 0.85 and (
            not cross_validation_required or len(identities) >= 2
        ):
            status = "covered"
        elif body or usable:
            status = "partial"
        else:
            status = "evidence_scarce"
        gaps: list[str] = []
        if not body:
            gaps.append("缺少可核验正文证据")
        if not high_authority and body:
            gaps.append("缺少高权威来源")
        if cross_validation_required and len(identities) < 2:
            gaps.append("需要第二个独立来源交叉验证")
        if missing_actions:
            gaps.append("未覆盖研究动作：" + "、".join(missing_actions[:6]))
        if model_only:
            gaps.append("当前只有 Model 分析，没有外部证据")
        if conflicts:
            gaps.append("存在待解释的来源冲突")
        rows.append(CoverageDimension(
            dimension_id=dimension.id,
            status=status,  # type: ignore[arg-type]
            body_evidence=bool(body),
            covered_actions=covered_actions,
            missing_actions=missing_actions,
            action_coverage=action_coverage,
            high_authority_source=high_authority,
            independent_source_count=len(identities),
            cross_validation_required=cross_validation_required,
            conflicts=conflicts,
            temporal_conflicts=temporal_conflicts,
            terminology_ambiguities=terminology_ambiguities,
            model_only=model_only,
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            evidence_count=len(usable),
            saturation=saturation,
            gap_summary=gaps,
        ))
    overall, high_importance = _coverage_scores(rows, importance)
    active_saturation = [item.saturation for item in rows if item.status != "out_of_scope"]
    return CoverageMatrix(
        dimensions=rows,
        iteration=(previous.iteration + 1) if previous else 0,
        target=max(0.0, min(1.0, coverage_target)),
        overall_coverage=overall,
        high_importance_coverage=high_importance,
        saturation=round(sum(active_saturation) / len(active_saturation), 3) if active_saturation else 1.0,
        stop_reason="",
        exhausted=False,
    )


def update_coverage_matrix(
    domain_map: DomainMap,
    evidence: Sequence[Mapping[str, Any] | Any],
    previous: CoverageMatrix,
    *,
    archetype: QueryArchetype | None = None,
    authority_threshold: float = 0.75,
    min_external_evidence_per_dimension: int = 1,
    coverage_target: float = 0.8,
) -> CoverageMatrix:
    """Recompute coverage after a retrieval iteration while advancing its counter."""

    return build_coverage_matrix(
        domain_map,
        evidence,
        archetype=archetype,
        previous=previous,
        authority_threshold=authority_threshold,
        min_external_evidence_per_dimension=min_external_evidence_per_dimension,
        coverage_target=coverage_target,
    )


def prioritize_coverage_gaps(
    domain_map: DomainMap,
    coverage_matrix: CoverageMatrix,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Rank important, weak, conflicting, and evidence-poor dimensions."""

    rows = coverage_matrix.by_dimension()
    ranked: list[dict[str, Any]] = []
    status_weight = {
        "covered": 0.0,
        "partial": 0.3,
        "evidence_scarce": 0.95,
        "conflicting": 1.0,
        "out_of_scope": -1.0,
    }
    for dimension in domain_map.dimensions:
        row = rows.get(dimension.id)
        if row is None or row.status == "out_of_scope":
            continue
        missing_ratio = len(row.missing_actions) / max(
            1,
            len(row.covered_actions) + len(row.missing_actions),
        )
        score = (
            0.38 * dimension.importance
            + 0.3 * status_weight[row.status]
            + 0.12 * missing_ratio
            + 0.08 * (0.0 if row.high_authority_source else 1.0)
            + 0.06 * (1.0 if row.model_only else 0.0)
            + 0.06 * (1.0 if row.cross_validation_required and row.independent_source_count < 2 else 0.0)
        )
        reasons = list(row.gap_summary)
        if row.status == "conflicting" and "需要解释冲突" not in reasons:
            reasons.insert(0, "需要解释冲突")
        if row.status == "covered" and not reasons:
            continue
        ranked.append({
            "dimension_id": dimension.id,
            "dimension": dimension.name,
            "priority": round(max(0.0, min(1.0, score)), 3),
            "status": row.status,
            "importance": dimension.importance,
            "reasons": reasons,
            "questions": list(dimension.questions_to_answer),
            "evidence_needs": _unique([
                *dimension.expected_evidence_types,
                *row.missing_actions,
            ]),
        })
    ranked.sort(key=lambda item: (-float(item["priority"]), str(item["dimension_id"])))
    return ranked[: max(0, int(limit))] if limit is not None else ranked


def research_should_stop(
    coverage_matrix: CoverageMatrix,
    budget: DynamicResearchBudget,
    *,
    elapsed_seconds: float = 0.0,
    evidence_growth: float = 1.0,
) -> tuple[bool, str]:
    """Combine coverage, saturation, scarcity, deadline, and iteration stops."""

    if coverage_matrix.exhausted:
        return True, coverage_matrix.stop_reason or "budget_exhausted"
    if elapsed_seconds >= budget.timeout_seconds:
        return True, "deadline_exhausted"
    actionable = [
        item
        for item in coverage_matrix.dimensions
        if item.status in {"partial", "evidence_scarce", "conflicting"}
    ]
    if not actionable:
        return True, "coverage_complete"
    target = max(0.5, min(1.0, coverage_matrix.target))
    if (
        coverage_matrix.high_importance_coverage >= min(1.0, target + 0.08)
        and coverage_matrix.overall_coverage >= target
        and coverage_matrix.saturation >= 0.75
    ):
        return True, "coverage_and_saturation_reached"
    if (
        evidence_growth <= 0.05
        and coverage_matrix.saturation >= 0.65
        and coverage_matrix.high_importance_coverage >= 0.75
    ):
        return True, "evidence_saturation_reached"
    if coverage_matrix.iteration >= budget.max_gap_iterations:
        return True, "gap_iteration_budget_exhausted"
    if all(item.status == "evidence_scarce" and item.evidence_count == 0 for item in actionable) and evidence_growth <= 0:
        return True, "explicit_evidence_scarcity"
    return False, "continue_for_coverage_gaps"


def build_report_outline(
    query: str,
    archetype: QueryArchetype,
    domain_map: DomainMap,
    coverage_matrix: CoverageMatrix,
    *,
    audience: str = "researcher",
    user_intent: str = "",
    budget: DynamicResearchBudget | None = None,
) -> ReportOutline:
    """Generate a dynamic report outline from active research dimensions."""

    rows = coverage_matrix.by_dimension()
    active = [item for item in domain_map.dimensions if item.current_coverage != "out_of_scope"]
    parents = [item for item in active if not item.parent_id]
    section_roots = parents or active
    by_parent: dict[str, list[ResearchDimension]] = {}
    for dimension in active:
        if dimension.parent_id:
            by_parent.setdefault(dimension.parent_id, []).append(dimension)
    sections: list[SectionContract] = []
    for index, dimension in enumerate(section_roots):
        children = by_parent.get(dimension.id, [])
        dimension_ids = [dimension.id, *(item.id for item in children)]
        questions = _unique([
            *dimension.questions_to_answer,
            *(question for child in children for question in child.questions_to_answer),
        ])
        coverage_target = min(0.95, 0.65 + 0.25 * dimension.importance)
        row = rows.get(dimension.id)
        evidence_requirements = list(dimension.expected_evidence_types)
        if row and row.cross_validation_required:
            evidence_requirements.append("independent_cross_validation")
        if row and row.model_only:
            evidence_requirements.append("external_body_evidence_or_explicit_model_boundary")
        claim_types = ["external_fact", "analysis", "open_question"]
        if archetype.type == "solution_design" or _requests_recommendations(user_intent or query):
            claim_types.append("recommendation")
        comparison_axes = (
            _unique([item.name for item in children])
            if archetype.type == "comparison" and children
            else []
        )
        dependencies = [
            section.id
            for section in sections
            if any(parent_id == dimension.id for parent_id in dimension.child_ids)
        ]
        length_budget = (
            budget.section_length_budgets.get(dimension.id, 0)
            if budget else max(500, round(6000 / max(1, len(section_roots))))
        )
        sections.append(SectionContract(
            id=f"section-{index + 1}",
            title=dimension.name,
            function=_section_function(archetype.type, first=index == 0),
            dimension_ids=dimension_ids,
            questions_to_answer=questions,
            required_claim_types=_unique(claim_types),
            evidence_requirements=_unique(evidence_requirements),
            comparison_axes=comparison_axes,
            dependencies=dependencies,
            coverage_target=round(coverage_target, 3),
            length_budget=length_budget,
        ))
    strategy = (
        "先直接回答并界定范围，再按动态研究维度展开证据、机制和边界，"
        "最后综合跨维度关系并披露未覆盖问题。"
    )
    if archetype.type == "comparison":
        strategy = "先建立共同基线，再按证据一致的比较轴展开对象差异，最后综合权衡与适用边界。"
    elif archetype.type == "solution_design":
        strategy = "先明确目标和约束，再比较候选设计、实施依赖与验证路径，最后披露风险和取舍。"
    elif archetype.type == "evidence_review":
        strategy = "先定义证据范围和质量标准，再综合共识、异质性与冲突，最后限定结论强度。"
    return ReportOutline(
        query_archetype=archetype.type,
        audience=audience,
        scope=domain_map.scope or _normalize_text(query),
        answer_strategy=strategy,
        sections=sections,
        cross_section_synthesis=list(archetype.required_synthesis_functions),
        citation_policy=(
            "外部可核验事实必须引用本轮取得的正文证据；搜索标题、摘要片段和 URL 线索不得作证。"
        ),
        reliability_policy=(
            "Model 分析与外部事实保持可区分；披露来源状态、争议、未覆盖维度和后续检索问题。"
        ),
    )


def build_section_drafts(
    outline: ReportOutline,
    evidence: Sequence[Mapping[str, Any] | Any],
    *,
    coverage_matrix: CoverageMatrix | None = None,
    contents: Mapping[str, str] | None = None,
) -> list[SectionDraft]:
    """Create traceable section-level claim bundles without generating prose."""

    items = [_payload(item) for item in evidence]
    rows = coverage_matrix.by_dimension() if coverage_matrix else {}
    result: list[SectionDraft] = []
    for contract in outline.sections:
        scoped = [
            item for item in items
            if _item_matches_dimension_ids(item, contract.dimension_ids)
        ]
        claims: list[SectionClaim] = []
        seen_claims: set[str] = set()
        for index, item in enumerate(scoped):
            text = str(item.get("claim") or item.get("text") or item.get("verbatim_quote") or "").strip()
            key = _normalize_key(text)
            if not text or key in seen_claims:
                continue
            seen_claims.add(key)
            model = _is_model_item(item)
            evidence_id = str(item.get("id") or item.get("evidence_id") or "").strip()
            refs = [str(value).strip() for value in _as_list(item.get("evidence_refs")) if str(value).strip()]
            claims.append(SectionClaim(
                id=evidence_id or f"{contract.id}-claim-{index + 1}",
                text=text,
                claim_type=str(item.get("claim_type") or item.get("research_type") or ("analysis" if model else "external_fact")),
                evidence_ids=[evidence_id] if evidence_id else [],
                citation_refs=refs,
                confidence=max(0.0, min(1.0, _number(item.get("confidence"), 0.5))),
                limitations=[str(value) for value in _as_list(item.get("limitations")) if str(value).strip()],
                relationship=str(item.get("relationship") or "supports"),
                externally_supported=not model and _has_body_evidence(item) and bool(refs),
            ))
        section_rows = [rows[item] for item in contract.dimension_ids if item in rows]
        statuses = {item.status for item in section_rows}
        if "conflicting" in statuses:
            coverage_status = "conflicting"
        elif section_rows and statuses == {"covered"}:
            coverage_status = "covered"
        elif statuses & {"covered", "partial"}:
            coverage_status = "partial"
        elif statuses == {"out_of_scope"}:
            coverage_status = "out_of_scope"
        else:
            coverage_status = "evidence_scarce"
        conflicts = _unique([item for row in section_rows for item in row.conflicts])
        gaps = _unique([item for row in section_rows for item in row.gap_summary])
        supported_external = [item for item in claims if item.externally_supported]
        external_claims = [item for item in claims if item.claim_type == "external_fact"]
        verified = bool(claims) and coverage_status == "covered" and (
            not external_claims or len(supported_external) == len(external_claims)
        )
        priority = contract.coverage_target
        if coverage_status in {"conflicting", "evidence_scarce"}:
            priority = min(1.0, priority + 0.15)
        result.append(SectionDraft(
            section_id=contract.id,
            title=contract.title,
            dimension_ids=list(contract.dimension_ids),
            research_questions=list(contract.questions_to_answer),
            claims=claims,
            content=str((contents or {}).get(contract.id) or "").strip(),
            coverage_status=coverage_status,
            conflicts=conflicts,
            unresolved_gaps=gaps,
            suggested_length=contract.length_budget,
            synthesis_priority=round(priority, 3),
            verified=verified,
        ))
    return result


def build_section_evidence_packs(
    outline: ReportOutline,
    evidence: Sequence[Mapping[str, Any] | Any],
    *,
    coverage_matrix: CoverageMatrix,
    drafts: Sequence[SectionDraft] | None = None,
) -> list[SectionEvidencePack]:
    """Build bounded, auditable evidence payloads for section synthesis."""

    items = [_payload(item) for item in evidence]
    rows = coverage_matrix.by_dimension()
    draft_map = {item.section_id: item for item in drafts or []}
    packs: list[SectionEvidencePack] = []
    for contract in outline.sections:
        dimension_ids = set(contract.dimension_ids)
        scoped = [
            item for item in items
            if _item_matches_dimension_ids(item, dimension_ids)
        ]
        direct: list[dict[str, Any]] = []
        boundary: list[dict[str, Any]] = []
        counterexamples: list[dict[str, Any]] = []
        for item in scoped:
            compact = _pack_evidence_item(item)
            role = str(item.get("evidence_role") or item.get("relationship") or "direct_support").casefold()
            if _is_model_item(item):
                continue
            if role in {"counterexample", "contradicts", "conflicts"}:
                counterexamples.append(compact)
            elif role in {"boundary", "limits"}:
                boundary.append(compact)
            elif role not in {"analogy", "discovery_only", "context"}:
                direct.append(compact)
        section_rows = [rows[item] for item in contract.dimension_ids if item in rows]
        required_actions = _unique([
            cell.action
            for row in section_rows
            for cell in row.action_coverage
        ])
        distinctions = _unique([
            *contract.evidence_requirements,
            *(value for row in section_rows for value in row.terminology_ambiguities),
        ])
        mitigations = _unique([
            str(item.get("claim") or item.get("text") or "").strip()
            for item in scoped
            if any("mitigat" in action or "remedi" in action for action in _evidence_actions(item))
            and str(item.get("claim") or item.get("text") or "").strip()
        ])
        draft = draft_map.get(contract.id)
        claims = list(draft.claims) if draft else []
        verified_claims = [
            claim for claim in claims
            if claim.externally_supported or claim.claim_type in {"analysis", "recommendation", "open_question"}
        ]
        forbidden = [
            claim.text for claim in claims
            if claim.claim_type == "external_fact" and not claim.externally_supported
        ]
        allowed_citations = _unique([
            str(ref)
            for item in scoped
            for ref in _as_list(item.get("evidence_refs"))
            if str(ref).strip()
        ])
        packs.append(SectionEvidencePack(
            section_id=contract.id,
            questions=list(contract.questions_to_answer),
            required_actions=required_actions,
            direct_evidence=direct,
            boundary_evidence=boundary,
            counterexamples=counterexamples,
            verified_claims=verified_claims,
            distinctions=distinctions,
            mitigations=mitigations,
            unresolved_gaps=_unique([
                *(draft.unresolved_gaps if draft else []),
                *(gap for row in section_rows for gap in row.gap_summary),
            ]),
            forbidden_claims=forbidden,
            allowed_citations=allowed_citations,
        ))
    return packs


def evaluate_generalized_research_quality(
    report: str,
    outline: ReportOutline,
    coverage_matrix: CoverageMatrix,
    *,
    section_drafts: Sequence[SectionDraft] | None = None,
    evidence: Sequence[Mapping[str, Any] | Any] | None = None,
) -> dict[str, Any]:
    """Evaluate P1.5 richness by coverage and evidence, never by length alone."""

    text = str(report or "").strip()
    drafts = list(section_drafts or [])
    evidence_items = [_payload(item) for item in evidence or []]
    draft_by_id = {item.section_id: item for item in drafts}
    substantive_sections = 0
    for contract in outline.sections:
        draft = draft_by_id.get(contract.id)
        title_context = _context_around(text, contract.title)
        if (
            draft and (len(draft.content) >= 80 or len(draft.claims) >= 2)
        ) or len(title_context) >= 100:
            substantive_sections += 1
    contract_coverage = substantive_sections / max(1, len(outline.sections))
    dimension_ratio = max(
        coverage_matrix.high_importance_coverage,
        coverage_matrix.overall_coverage,
        contract_coverage,
    )

    units = [
        line.strip()
        for line in text.splitlines()
        if len(line.strip()) >= 30 and not line.lstrip().startswith("#")
    ]
    mechanism_ratio = _marker_ratio(
        units,
        ("机制", "因为", "由于", "导致", "依赖", "约束", "作用", "mechanism", "because", "causes", "depends"),
    )
    boundary_ratio = _marker_ratio(
        units,
        ("边界", "条件", "限制", "例外", "不确定", "缺口", "适用", "boundary", "condition", "limitation", "uncertainty"),
    )
    implementation_ratio = _marker_ratio(
        units,
        ("实现", "案例", "系统", "数据集", "基准", "步骤", "部署", "implementation", "case", "benchmark", "deployment"),
    )
    synthesis_ratio = _marker_ratio(
        units,
        ("相比", "共同", "差异", "互补", "替代", "依赖", "冲突", "演化", "trade-off", "complement", "contrast"),
    )

    claims = [claim for draft in drafts for claim in draft.claims]
    external_claims = [item for item in claims if item.claim_type == "external_fact"]
    supported_claims = [item for item in external_claims if item.externally_supported]
    if external_claims:
        evidence_ratio = len(supported_claims) / len(external_claims)
    else:
        body_external = [item for item in evidence_items if not _is_model_item(item) and _has_body_evidence(item)]
        evidence_ratio = min(1.0, len(body_external) / max(1, len(outline.sections))) if body_external else 0.5

    claim_texts = [_normalize_key(item.text) for item in claims if item.text]
    unique_claim_ratio = len(set(claim_texts)) / len(claim_texts) if claim_texts else 0.5
    cross_function_count = len(outline.cross_section_synthesis)
    insight_ratio = min(1.0, 0.55 * synthesis_ratio + 0.25 * unique_claim_ratio + 0.2 * min(1.0, cross_function_count / 3))
    source_blocked = bool(re.search(r"(?im)^#{1,4}\s+(?:RAG|Web|Model)\s*$", text))
    coherence_ratio = max(0.0, min(1.0, 0.65 * contract_coverage + 0.35 * unique_claim_ratio - (0.35 if source_blocked else 0.0)))

    applicable = {
        "dimension_coverage": True,
        "mechanism_expansion": True,
        "evidence_density": True,
        "comparative_synthesis": bool(
            outline.query_archetype == "comparison" or cross_function_count or len(outline.sections) > 1
        ),
        "implementation_detail": outline.query_archetype in {"method_survey", "solution_design"} or bool(evidence_items),
        "boundary_conditions": True,
        "insight_gain": True,
        "coherence": True,
    }
    ratios = {
        "dimension_coverage": dimension_ratio,
        "mechanism_expansion": mechanism_ratio,
        "evidence_density": evidence_ratio,
        "comparative_synthesis": synthesis_ratio,
        "implementation_detail": implementation_ratio,
        "boundary_conditions": boundary_ratio,
        "insight_gain": insight_ratio,
        "coherence": coherence_ratio,
    }
    scores = {
        name: _ratio_score(value) if applicable[name] else None
        for name, value in ratios.items()
    }
    active_scores = [value for value in scores.values() if isinstance(value, int)]
    overall = round(sum(active_scores) / len(active_scores), 2) if active_scores else 1.0
    traceable_sections = sum(
        bool(item.dimension_ids) and (bool(item.claims) or bool(item.unresolved_gaps))
        for item in drafts
    )
    traceability_ratio = traceable_sections / len(drafts) if drafts else contract_coverage
    notes: list[str] = []
    for name, score in scores.items():
        if isinstance(score, int) and score < 4:
            notes.append(f"{name} 低于达标线：{score}/5")
    if traceability_ratio < 0.8:
        notes.append("主要章节未全部回溯到研究维度、声明或未解决缺口。")
    passed = bool(text) and overall >= 4.0 and (scores["dimension_coverage"] or 0) >= 4 and (
        scores["evidence_density"] or 0
    ) >= 3 and traceability_ratio >= 0.8
    return {
        "scores": scores,
        "applicable": applicable,
        "ratios": {key: round(value, 3) for key, value in ratios.items()},
        "overall": overall,
        "passed": passed,
        "section_traceability_ratio": round(traceability_ratio, 3),
        "notes": notes,
    }


def _coerce_dimension(
    value: ResearchDimension | Mapping[str, Any] | str,
    *,
    index: int,
) -> ResearchDimension:
    if isinstance(value, ResearchDimension):
        return value
    if isinstance(value, Mapping):
        return ResearchDimension.from_dict(dict(value), index=index)
    name = str(value).strip()
    return ResearchDimension(
        id=_dimension_id(name, index),
        name=name,
        importance=0.85 if index == 0 else 0.7,
    )


def _dimension_id(name: str, index: int) -> str:
    digest = hashlib.sha1(_normalize_key(name).encode("utf-8")).hexdigest()[:8]
    return f"dim-{index + 1}-{digest}"


def _merge_dimension(left: ResearchDimension, right: ResearchDimension) -> ResearchDimension:
    coverage_order = {
        "out_of_scope": 0,
        "evidence_scarce": 1,
        "partial": 2,
        "conflicting": 3,
        "covered": 4,
    }
    coverage = max(
        (left.current_coverage, right.current_coverage),
        key=lambda item: coverage_order.get(item, 1),
    )
    return ResearchDimension(
        id=left.id or right.id,
        name=left.name if len(left.name) >= len(right.name) else right.name,
        inclusion_reason=left.inclusion_reason or right.inclusion_reason,
        parent_id=left.parent_id or right.parent_id,
        child_ids=_unique([*left.child_ids, *right.child_ids]),
        questions_to_answer=_unique([*left.questions_to_answer, *right.questions_to_answer]),
        expected_evidence_types=_unique([*left.expected_evidence_types, *right.expected_evidence_types]),
        required_actions=_unique([*left.required_actions, *right.required_actions]),
        cross_validation_required=(
            left.cross_validation_required
            if left.cross_validation_required is not None
            else right.cross_validation_required
        ),
        importance=max(left.importance, right.importance),
        current_coverage=coverage,
        conflicts=_unique([*left.conflicts, *right.conflicts]),
        gaps=_unique([*left.gaps, *right.gaps]),
        stop_conditions=_unique([*left.stop_conditions, *right.stop_conditions]),
        terminology=_unique([*left.terminology, *right.terminology]),
    )


def _dimension_similarity(left: ResearchDimension, right: ResearchDimension) -> float:
    if (
        left.id.startswith("jurisdiction-")
        and right.id.startswith("jurisdiction-")
        and left.id != right.id
    ):
        return 0.0
    left_key = _normalize_key(left.name)
    right_key = _normalize_key(right.name)
    if not left_key or not right_key:
        return 0.0
    if left_key == right_key:
        return 1.0
    if min(len(left_key), len(right_key)) >= 4 and (left_key in right_key or right_key in left_key):
        return 0.86
    left_tokens = _text_tokens(" ".join([left.name, *left.terminology]))
    right_tokens = _text_tokens(" ".join([right.name, *right.terminology]))
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def _dimension_relevance(query: str, dimension: ResearchDimension) -> float:
    query_tokens = _text_tokens(query)
    dimension_tokens = _text_tokens(" ".join([
        dimension.name,
        dimension.inclusion_reason,
        *dimension.questions_to_answer,
        *dimension.terminology,
    ]))
    if not query_tokens or not dimension_tokens:
        return 0.0
    overlap = len(query_tokens & dimension_tokens) / max(1, len(dimension_tokens))
    phrase = 1.0 if _normalize_key(dimension.name) in _normalize_key(query) else 0.0
    return min(1.0, 0.75 * overlap + 0.25 * phrase)


def _dimension_questions(name: str, archetype: str) -> list[str]:
    templates = {
        "method_survey": [
            f"{name}包含哪些类别、机制和代表实现？",
            f"{name}的适用条件、优势、限制和成熟度如何？",
        ],
        "state_and_trends": [
            f"{name}的当前状态、关键时间点和近期变化是什么？",
            f"哪些证据支持其趋势、成熟度和未决问题？",
        ],
        "limitations_and_challenges": [
            f"{name}的具体局限、形成机制和影响是什么？",
            f"已有缓解措施、适用边界和剩余缺口是什么？",
        ],
        "comparison": [
            f"各比较对象在{name}上的共同基线和差异是什么？",
            f"这些差异的证据、适用条件和权衡是什么？",
        ],
        "causal_mechanism": [
            f"{name}涉及哪些因果因素、机制和中介路径？",
            f"证据强度、替代解释和边界条件是什么？",
        ],
        "solution_design": [
            f"{name}的目标、约束、候选设计和依赖是什么？",
            f"如何实施、验证并控制风险和权衡？",
        ],
        "evidence_review": [
            f"{name}有哪些主要证据、共识和证据等级？",
            f"异质性、冲突、偏倚和证据缺口是什么？",
        ],
    }
    return templates.get(archetype, [
        f"{name}的范围、核心事实和机制是什么？",
        f"有哪些代表证据、边界、争议和待研究问题？",
    ])


def _dimension_relations(dimensions: Sequence[ResearchDimension]) -> list[dict[str, str]]:
    ids = {item.id for item in dimensions}
    relations: list[dict[str, str]] = []
    for dimension in dimensions:
        if dimension.parent_id and dimension.parent_id in ids:
            relations.append({
                "source": dimension.parent_id,
                "target": dimension.id,
                "relation": "parent_of",
            })
        for child_id in dimension.child_ids:
            if child_id in ids:
                relations.append({
                    "source": dimension.id,
                    "target": child_id,
                    "relation": "parent_of",
                })
    seen: set[tuple[str, str, str]] = set()
    result = []
    for item in relations:
        key = (item["source"], item["target"], item["relation"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _allocate_section_lengths(dimensions: Sequence[ResearchDimension], total_chars: int) -> dict[str, int]:
    if not dimensions:
        return {}
    usable = max(400, round(total_chars * 0.82))
    weights = [max(0.2, item.importance) for item in dimensions]
    total_weight = sum(weights)
    raw = [max(320, round(usable * weight / total_weight)) for weight in weights]
    if sum(raw) > usable and usable >= len(raw) * 240:
        scale = usable / sum(raw)
        raw = [max(240, round(item * scale)) for item in raw]
    return {dimension.id: length for dimension, length in zip(dimensions, raw)}


def _integer_budget_shares(total: int, count: int) -> list[int]:
    """Split a run-level integer budget without granting every dimension a full copy."""

    count = max(1, int(count))
    total = max(0, int(total))
    quotient, remainder = divmod(total, count)
    return [quotient + (1 if index < remainder else 0) for index in range(count)]


def _coverage_scores(
    rows: Sequence[CoverageDimension],
    importance: Mapping[str, float],
) -> tuple[float, float]:
    values = {
        "covered": 1.0,
        "partial": 0.5,
        "evidence_scarce": 0.0,
        "conflicting": 0.35,
        "out_of_scope": 0.0,
    }
    active = [item for item in rows if item.status != "out_of_scope"]
    if not active:
        return 1.0, 1.0
    action_values = {
        "covered": 1.0,
        "model_analysis": 0.25,
        "conflicting": 0.25,
        "gap": 0.0,
        "out_of_scope": 0.0,
    }

    def row_score(row: CoverageDimension, *, external_only: bool = False) -> float:
        if not row.action_coverage:
            return values[row.status]
        if external_only:
            return sum(item.status == "covered" for item in row.action_coverage) / len(row.action_coverage)
        return sum(action_values[item.status] for item in row.action_coverage) / len(row.action_coverage)

    total_weight = sum(max(0.1, importance.get(item.dimension_id, 0.5)) for item in active)
    overall = sum(
        row_score(item) * max(0.1, importance.get(item.dimension_id, 0.5))
        for item in active
    ) / total_weight
    high = [item for item in active if importance.get(item.dimension_id, 0.5) >= 0.75]
    high_score = sum(row_score(item, external_only=True) for item in high) / len(high) if high else overall
    return round(overall, 3), round(high_score, 3)


def _build_action_coverage(
    required_actions: Sequence[str],
    evidence: Sequence[Mapping[str, Any]],
) -> list[CoverageAction]:
    high_risk_actions = {
        "assess_impact",
        "assess_maturity",
        "compare_evidence",
        "define_validation",
        "establish_current_state",
        "trace_time_evolution",
    }
    cells: list[CoverageAction] = []
    for action in required_actions:
        matching = [item for item in evidence if action in _evidence_actions(item)]
        external = [
            item for item in matching
            if not _is_model_item(item)
            and _has_body_evidence(item)
            and str(item.get("evidence_role") or item.get("relationship") or "direct_support").casefold()
            not in {"analogy", "discovery_only", "context"}
        ]
        model = [item for item in matching if _is_model_item(item)]
        conflicting = [
            item for item in matching
            if str(item.get("relationship") or item.get("evidence_role") or "").casefold()
            in {"contradicts", "conflicts", "counterexample"}
        ]
        if conflicting:
            status = "conflicting"
            reason = "存在尚未消解的反例或冲突证据"
        elif external:
            status = "covered"
            reason = ""
        elif model:
            status = "model_analysis"
            reason = "仅有明确标注的 Model analysis，缺少直接外部证据"
        else:
            status = "gap"
            reason = "没有通过门禁的证据覆盖该研究动作"
        cells.append(CoverageAction(
            action=action,
            status=status,  # type: ignore[arg-type]
            evidence_ids=_unique([
                str(item.get("id") or item.get("evidence_id") or "") for item in matching
            ]),
            external_evidence_ids=_unique([
                str(item.get("id") or item.get("evidence_id") or "") for item in external
            ]),
            model_evidence_ids=_unique([
                str(item.get("id") or item.get("evidence_id") or "") for item in model
            ]),
            citation_refs=_unique([
                str(ref) for item in external for ref in _as_list(item.get("evidence_refs"))
            ]),
            high_risk=action in high_risk_actions,
            gap_reason=reason,
        ))
    return cells


def _pack_evidence_item(item: Mapping[str, Any]) -> dict[str, Any]:
    quote = str(
        item.get("verbatim_quote") or item.get("quote") or item.get("text")
        or item.get("claim") or ""
    ).strip()
    return {
        "id": str(item.get("id") or item.get("evidence_id") or "").strip(),
        "claim": str(item.get("claim") or item.get("text") or "").strip()[:700],
        "verbatim_quote": quote[:1200],
        "evidence_refs": _unique(_as_list(item.get("evidence_refs"))),
        "source_identity": str(item.get("source_identity") or item.get("source") or "").strip(),
        "document_title": str(item.get("document_title") or item.get("title") or "").strip(),
        "publication_year": str(item.get("publication_year") or item.get("year") or "").strip(),
        "evidence_role": str(item.get("evidence_role") or item.get("relationship") or "direct_support"),
        "research_actions": _evidence_actions(item),
        "limitations": _unique(_as_list(item.get("limitations"))),
    }


def _dimension_saturation(
    scoped: Sequence[Mapping[str, Any]],
    body: Sequence[Mapping[str, Any]],
    identities: set[str],
    action_ratio: float,
) -> float:
    claims = {
        _normalize_key(str(item.get("claim") or item.get("text") or ""))
        for item in scoped
        if str(item.get("claim") or item.get("text") or "").strip()
    }
    claim_factor = min(1.0, len(claims) / 3.0)
    body_factor = min(1.0, len(body) / 2.0)
    diversity_factor = min(1.0, len(identities) / 2.0)
    return round(
        0.3 * claim_factor + 0.25 * body_factor + 0.2 * diversity_factor + 0.25 * action_ratio,
        3,
    )


def _evidence_matches_dimension(item: Mapping[str, Any], dimension: ResearchDimension) -> bool:
    explicit = _item_dimension_ids(item)
    if explicit:
        if dimension.id == "jurisdiction-cross-comparison" and any(
            item_id in _JURISDICTION_OFFICIAL_HOSTS for item_id in explicit
        ):
            return True
        return dimension.id in explicit
    text = " ".join(str(item.get(key) or "") for key in (
        "claim", "text", "verbatim_quote", "document_title", "paper_section",
    ))
    return _dimension_relevance(text, dimension) >= 0.22


def _item_dimension_ids(item: Mapping[str, Any]) -> set[str]:
    ids = {
        str(item.get("dimension_id") or "").strip(),
        str(item.get("subquestion_id") or "").strip(),
    }
    ids.update(str(value).strip() for value in _as_list(item.get("dimension_ids")))
    return {item for item in ids if item}


def _item_matches_dimension_ids(
    item: Mapping[str, Any],
    dimension_ids: Iterable[str],
) -> bool:
    expected = {str(value).strip() for value in dimension_ids if str(value).strip()}
    explicit = _item_dimension_ids(item)
    if explicit & expected:
        return True
    return "jurisdiction-cross-comparison" in expected and any(
        item_id in _JURISDICTION_OFFICIAL_HOSTS for item_id in explicit
    )


def _evidence_actions(item: Mapping[str, Any]) -> list[str]:
    explicit = _unique([
        *(str(value).strip() for value in _as_list(item.get("research_actions"))),
        *(str(value).strip() for value in _as_list(item.get("covered_actions"))),
        *(str(value).strip() for value in _as_list(item.get("action_types"))),
    ])
    if explicit:
        return explicit
    text = _normalize_text(" ".join(str(item.get(key) or "") for key in (
        "claim", "text", "verbatim_quote", "document_title", "paper_section", "url",
    ))).casefold()
    markers = {
        "define_scope": ("定义", "范围", "scope", "definition"),
        "define_comparison_scope": (
            "适用于", "适用对象", "提供者", "开发者", "服务提供者",
            "applies to", "provider", "developer", "service provider", "signator",
            "regulator", "authority", "监管机构", "主管部门", "ai system", "scope",
        ),
        "establish_common_baseline": (
            "透明度", "义务", "要求", "报告", "披露", "技术文档",
            "transparency", "obligation", "requirement", "reporting", "disclosure",
            "technical documentation",
        ),
        "identify_comparison_axes": (
            "透明度", "报告", "披露", "技术文档", "版权", "网络安全", "监管主体",
            "transparency", "reporting", "disclosure", "technical documentation",
            "copyright", "cybersecurity", "supervisory authority",
        ),
        "compare_mechanisms": (
            "必须", "应当", "义务", "要求", "监管", "监督", "技术文档", "标准", "指南", "原则", "透明度",
            "must", "shall", "require", "obligation", "regulation", "supervision",
            "technical documentation", "standard", "guidance", "principle", "transparency",
        ),
        "compare_applicability": (
            "适用于", "适用对象", "提供者", "开发者", "服务", "门槛", "生效",
            "applies", "provider", "developer", "service", "threshold", "effective",
            "fine-tuning", "systemic risk", "signator", "ai system", "consumer", "user", "regulator",
        ),
        "discover_taxonomy": ("分类", "类别", "taxonomy", "category"),
        "explain_mechanisms": ("机制", "原因", "mechanism", "because"),
        "identify_representative_implementations": ("实现", "系统", "工具", "implementation", "system"),
        "assess_applicability": ("适用", "条件", "场景", "applicable", "condition"),
        "compare_strengths_and_limits": ("优势", "局限", "比较", "strength", "limitation", "compare"),
        "assess_maturity": ("成熟度", "现状", "maturity", "current"),
        "identify_limitations": ("局限", "限制", "挑战", "limitation", "challenge"),
        "explain_failure_mechanisms": ("失败", "错误", "故障", "failure", "error"),
        "assess_impact": ("影响", "风险", "后果", "impact", "risk"),
        "identify_boundary_conditions": ("边界", "例外", "条件", "boundary", "condition"),
        "compare_evidence": ("证据", "结果", "基准", "evidence", "result", "benchmark"),
        "trace_time_evolution": ("时间", "演进", "趋势", "timeline", "evolution", "trend"),
        "plan_implementation": ("实施", "部署", "步骤", "implement", "deploy"),
        "define_validation": ("验证", "评估", "指标", "validate", "evaluate", "metric"),
        "analyze_conflicts": ("冲突", "争议", "矛盾", "conflict", "controversy"),
        "establish_current_state": ("当前", "现状", "部署", "current", "status", "deployment"),
        "identify_drivers": ("驱动", "促进", "推动", "driver", "enable"),
        "identify_emerging_directions": ("新兴", "未来", "方向", "emerging", "future", "direction"),
        "identify_open_questions": ("开放问题", "未知", "待解决", "open question", "unresolved"),
        "review_mitigations": ("缓解", "修复", "改进", "mitigation", "remediation"),
        "identify_tradeoffs": ("权衡", "取舍", "trade-off", "tradeoff"),
        "assess_risks_and_tradeoffs": ("风险", "权衡", "取舍", "risk", "trade-off"),
        "identify_evidence_gaps": ("证据不足", "证据缺口", "缺少研究", "evidence gap", "lack of evidence"),
        "define_evidence_criteria": ("证据标准", "纳入标准", "排除标准", "evidence criteria", "inclusion criteria"),
        "define_review_scope": ("综述范围", "检索范围", "review scope", "search scope"),
    }
    return [name for name, terms in markers.items() if any(term in text for term in terms)]


def _has_body_evidence(item: Mapping[str, Any]) -> bool:
    if not _item_status_allows_evidence(item):
        return False
    quote = str(item.get("verbatim_quote") or item.get("quote") or "").strip()
    kind = str(item.get("content_kind") or "").casefold()
    if kind in {"snippet", "search_result", "unfetched", "url", "title_only", "discovery_metadata"}:
        return False
    if quote:
        return True
    content = str(item.get("body") or item.get("content") or "").strip()
    return bool(content) and kind in {
        "body", "html", "pdf", "fulltext", "document", "official_document", "abstract",
        "local_full_text", "local_document", "run_scoped_fulltext",
    }


def _item_status_allows_evidence(
    item: Mapping[str, Any],
    *,
    domain_relevance_threshold: float = 0.7,
    claim_entailment_threshold: float = 0.7,
) -> bool:
    status = str(item.get("status") or "success").casefold()
    if status in {"failed", "no_evidence", "low_relevance", "fallback", "disabled"}:
        return False
    if item.get("body_valid") is False:
        return False
    role = str(item.get("evidence_role") or "").casefold()
    if role in {"analogy", "discovery_only"}:
        return False
    if role and role != "model_analysis":
        domain = _number(item.get("domain_relevance"), 0.0)
        entailment = _number(item.get("claim_entailment"), 0.0)
        if domain < max(0.0, min(1.0, domain_relevance_threshold)):
            return False
        if entailment < max(0.0, min(1.0, claim_entailment_threshold)):
            return False
    return True


def _is_model_item(item: Mapping[str, Any]) -> bool:
    source = str(item.get("source") or item.get("source_id") or "").casefold()
    evidence_class = str(item.get("evidence_class") or "").casefold()
    return source.endswith("model") or source == "model" or evidence_class == "model_inference"


def _evidence_authority(item: Mapping[str, Any]) -> float:
    explicit = _number(item.get("authority") or item.get("authority_score"), -1.0)
    if explicit >= 0:
        return max(0.0, min(1.0, explicit))
    evidence_class = str(item.get("evidence_class") or "").casefold()
    return {
        "peer_reviewed": 0.9,
        "authoritative_document": 0.88,
        "systematic_review": 0.9,
        "preprint": 0.7,
        "community_content": 0.45,
        "model_inference": 0.0,
    }.get(evidence_class, 0.55)


def _source_identity(item: Mapping[str, Any]) -> str:
    for key in ("source_identity", "paper_id", "document_id", "url", "document_title", "source"):
        value = str(item.get(key) or "").strip().casefold()
        if value:
            value = re.sub(r"[#?].*$", "", value)
            value = re.sub(r"\.pdf$", "", value, flags=re.IGNORECASE)
            arxiv = re.search(r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/|papers?/)(\d{4}\.\d{4,5})", value)
            return f"arxiv:{arxiv.group(1)}" if arxiv else value.rstrip("/")
    return ""


def _evidence_domain_relevance(item: Mapping[str, Any], scope: ScopeContract) -> float:
    explicit = _number(item.get("domain_relevance"), 0.0)
    text = " ".join(str(item.get(key) or "") for key in (
        "document_title", "claim", "verbatim_quote", "paper_section", "url",
    ))
    lexical = _scope_subject_relevance(text, scope.subject)
    lexical = max(lexical, _scope_concept_alias_relevance(text, scope))
    lexical = max(lexical, _jurisdiction_object_relevance(item, scope))
    lowered = text.casefold()
    required = [entity for entity in scope.required_entities if str(entity).strip()]
    if any(str(entity).casefold() in lowered for entity in required):
        lexical = max(lexical, 1.0)
    if any(str(entity).casefold() == "gis" for entity in required):
        if re.search(r"\b(?:geospatial|geographic(?:al)?|spatial data|geoinformatics)\b", lowered):
            lexical = max(lexical, 0.9)
    retrieval_relevance = _number(item.get("relevance"), 0.0)
    # Retrieval similarity cannot establish domain identity on its own because
    # generic fallback queries can score unrelated papers highly.
    corroborated_retrieval = retrieval_relevance if lexical >= 0.25 else min(retrieval_relevance, 0.69)
    return max(0.0, min(1.0, max(explicit, lexical, corroborated_retrieval)))


def _jurisdiction_object_relevance(
    item: Mapping[str, Any],
    scope: ScopeContract,
) -> float:
    """Recognize an official comparison object without relaxing the general domain gate."""

    dimension_id = str(
        item.get("subquestion_id") or item.get("dimension_id") or ""
    ).strip()
    allowed_hosts = _JURISDICTION_OFFICIAL_HOSTS.get(dimension_id)
    if not allowed_hosts:
        return 0.0
    scope_text = _normalize_text(" ".join((scope.subject, scope.original_query))).casefold()
    if not any(marker in scope_text for marker in (
        "司法辖区", "jurisdiction", "基础模型", "通用人工智能模型",
        "foundation model", "general-purpose ai", "gpai",
    )):
        return 0.0
    identity = str(
        item.get("url") or item.get("paper_id") or item.get("source_identity") or ""
    ).strip()
    host = (urlparse(identity).hostname or "").casefold()
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts):
        return 0.0
    candidate = _normalize_text(" ".join(str(item.get(key) or "") for key in (
        "document_title", "claim", "verbatim_quote", "paper_section", "url",
    ))).casefold()
    ai_anchor = re.search(
        r"\b(?:ai|gpai)\b|artificial intelligence|foundation model|frontier ai|"
        r"general-purpose ai|generative ai|人工智能|基础模型|生成式人工智能",
        candidate,
        re.IGNORECASE,
    )
    policy_anchor = re.search(
        r"transparen|explainab|reporting|disclos|documentation|obligation|require|"
        r"regulat|guidance|standard|provider|透明度|可解释|报告|披露|文档|义务|"
        r"要求|监管|规则|标准|提供者",
        candidate,
        re.IGNORECASE,
    )
    return 0.9 if ai_anchor and policy_anchor else 0.0


_GENERIC_SCOPE_CONCEPT_TRIGGERS = {
    "自动化",
    "司法辖区",
    "局限性",
    "局限",
    "挑战",
    "失败模式",
    "未来工作",
    "研究空白",
    "limitations",
    "failure modes",
    "research gaps",
}

_GENERIC_SCOPE_ALIASES = {
    "agent",
    "automation",
    "automated workflow",
    "challenges",
    "failure cases",
    "failure modes",
    "future work",
    "limitations",
    "open problems",
    "research gaps",
    "workflow automation",
}


def _scope_concept_alias_relevance(text: str, scope: ScopeContract) -> float:
    """Match explicit bilingual domain aliases without weakening the gate."""

    scope_text = " ".join([
        scope.subject,
        *scope.required_entities,
        *scope.scope_inclusions,
        scope.original_query,
    ])
    candidate = _normalize_text(text).casefold()
    candidate_tokens = _text_tokens(candidate)
    best = 0.0
    for group in concept_alias_groups(scope_text):
        trigger = str(group[0] if group else "").casefold()
        if trigger in _GENERIC_SCOPE_CONCEPT_TRIGGERS:
            continue
        for raw_alias in group:
            alias = _normalize_text(raw_alias).casefold()
            if not alias or alias in _GENERIC_SCOPE_ALIASES:
                continue
            alias_tokens = _text_tokens(alias)
            ascii_tokens = re.findall(r"[a-z0-9][a-z0-9_.+-]*", alias)
            is_acronym = bool(re.fullmatch(r"[A-Z0-9.+_-]{2,}", str(raw_alias).strip()))
            is_specific = (
                bool(re.search(r"[\u4e00-\u9fff]{3,}", alias))
                or len(ascii_tokens) >= 2
                or is_acronym
                or (len(ascii_tokens) == 1 and len(ascii_tokens[0]) >= 6)
            )
            if not is_specific:
                continue
            if re.search(r"[\u4e00-\u9fff]", alias):
                exact = alias in candidate
            else:
                exact = bool(re.search(
                    rf"(?<![a-z0-9]){re.escape(alias)}(?:s|es)?(?![a-z0-9])",
                    candidate,
                ))
            if exact:
                best = max(best, 0.9)
                continue
            if len(alias_tokens) >= 2:
                overlap = len(alias_tokens & candidate_tokens) / len(alias_tokens)
                if overlap >= 0.75:
                    best = max(best, 0.8)
    return best


def _evidence_claim_entailment(item: Mapping[str, Any], *, body_valid: bool) -> float:
    explicit = _number(item.get("claim_entailment"), 0.0)
    directness = _number(item.get("directness"), 0.0)
    quote = str(item.get("verbatim_quote") or item.get("quote") or "").strip()
    inferred = 0.75 if body_valid and quote else 0.4 if body_valid else 0.0
    return max(0.0, min(1.0, max(explicit, directness, inferred)))


def _evidence_body_valid(item: Mapping[str, Any], *, is_model: bool) -> bool:
    if is_model:
        return True
    if item.get("body_valid") is False:
        return False
    kind = str(item.get("content_kind") or "").casefold()
    if kind in {"snippet", "search_result", "unfetched", "url", "title_only", "discovery_metadata"}:
        return False
    text = str(
        item.get("verbatim_quote") or item.get("quote")
        or item.get("body") or item.get("content") or ""
    ).strip()
    if len(text) < 24:
        return False
    normalized = re.sub(r"\s+", " ", text).casefold()
    chrome_patterns = (
        r"show details\s+hide details",
        r"enable javascript .* (?:view|continue)",
        r"accept all cookies",
        r"sign in\s+(?:register|create account)",
        r"\bcaptcha\b",
        r"\brequest access\b",
        r"\baccess denied\b",
        r"\bverify (?:that )?you are (?:a )?human\b",
        r"\bsite help.*wider ip range\b",
    )
    if any(re.search(pattern, normalized) for pattern in chrome_patterns):
        return False
    meaningful = re.findall(r"[a-z0-9\u4e00-\u9fff]", normalized)
    return len(meaningful) >= 16


def _source_available(source_health: Mapping[str, Any], source: str) -> bool:
    payload = source_health.get(source) or source_health.get(source.casefold()) or source_health.get(f"builtin.{source.casefold()}")
    if payload is None:
        return True
    if isinstance(payload, Mapping):
        if bool((payload.get("metadata") or {}).get("disabled")) if isinstance(payload.get("metadata"), Mapping) else False:
            return False
        status = str(payload.get("status") or "").casefold()
    else:
        status = str(payload).casefold()
    if source.casefold() == "rag" and status == "low_relevance":
        return False
    return status not in {"failed", "no_evidence", "fallback", "disabled"}


def _source_stress(source_health: Mapping[str, Any]) -> float:
    if not source_health:
        return 0.0
    statuses = []
    for payload in source_health.values():
        status = str(payload.get("status") or "") if isinstance(payload, Mapping) else str(payload)
        statuses.append(status.casefold())
    stressed = sum(item in {"failed", "no_evidence", "low_relevance", "fallback", "disabled"} for item in statuses)
    return stressed / len(statuses) if statuses else 0.0


def _section_function(archetype: str, *, first: bool) -> str:
    role = {
        "method_survey": "taxonomy_and_mechanism",
        "state_and_trends": "time_evolution",
        "limitations_and_challenges": "limitations_and_boundaries",
        "comparison": "evidence_comparison",
        "causal_mechanism": "mechanism_explanation",
        "solution_design": "implementation_design",
        "evidence_review": "evidence_synthesis",
        "general_exploration": "scope_and_analysis",
    }.get(archetype, "scope_and_analysis")
    return f"direct_answer_and_{role}" if first else role


def _requests_recommendations(text: str) -> bool:
    return bool(re.search(r"建议|选型|行动|实施|怎么做|recommend|action|implement", str(text), re.IGNORECASE))


def _is_temporal_query(query: str) -> bool:
    return bool(re.search(
        r"(?:截至|当前|最新|近期|近\s*\d+\s*年|趋势|进展|20\d{2}|current|latest|recent|trend|progress)",
        str(query),
        re.IGNORECASE,
    ))


def _is_broad_query(query: str) -> bool:
    clean = str(query)
    specific_document = _is_specific_document_query(clean)
    specific_scope = _has_specific_scope_signal(clean)
    broad_signal = bool(re.search(
        r"综述|全景|系统性|全面|主要.*有哪些|都有哪些|存在哪些|领域|整体|"
        r"当前.{0,16}研究|现状.{0,8}(?:趋势|进展)|landscape|comprehensive|survey|state of the art|"
        r"\bacross\b.{0,80}(?:,|\band\b)|\bmajor\b.{0,32}\b(?:methods?|technologies|approaches|"
        r"factors|limitations?|challenges?|standards?|products?|operations?)\b|\beach\s+(?:method|approach|"
        r"technology)\b|\bwhat\s+currently\s+limits?\b",
        clean,
        re.IGNORECASE,
    ))
    return bool(
        (broad_signal and not specific_scope)
        or (_comparison_object_count(clean) >= 3 and not specific_scope)
        or (len(clean) >= 45 and not specific_scope and not specific_document)
    )


def is_broad_research_query(query: str) -> bool:
    """Expose the shared broad-query decision to graph orchestration."""

    return _is_broad_query(query)


def _is_specific_document_query(query: str) -> bool:
    return bool(re.search(
        r"(?:某一|单个|具体).{0,8}(?:论文|文档|页面|条款)|(?:论文|文档|页面|条款).{0,8}(?:明确|具体|报告了哪些)|"
        r"\b(?:specific|single|one)\b.{0,24}\b(?:paper|article|document|report|study|page|section|clause)\b|"
        r"\b(?:paper|article|document|report|study)\b.{0,40}\b(?:reported|reports|states|found|findings|results)\b|"
        r"\b(?:paper|article|document|report)\s*[:,-]",
        str(query),
        re.IGNORECASE,
    ))


def _has_specific_scope_signal(query: str) -> bool:
    clean = str(query)
    return bool(
        _is_specific_document_query(clean)
        or re.search(
            r"\b(?:one|single|specific)\b|"
            r"\bwhat\s+(?:is|are)\s+the\s+(?:implementation\s+)?status\s+of\b|"
            r"\bwhat\s+(?:is|are)\s+the\s+(?:main\s+)?limitations?\s+of\b|"
            r"\bwhat\s+(?:rollback\s+)?methods?\s+(?:is|are)\s+available\s+for\b|"
            r"\bhow\s+do\b[^,;?]{1,80}\band\b[^,;?]{1,80}\bdiffer\b|"
            r"\bwhat\s+is\s+the\s+evidence\s+that\b|"
            r"\bthrough\s+which\s+mechanisms?\s+do\b",
            clean,
            re.IGNORECASE,
        )
    )


def _is_narrow_query(query: str) -> bool:
    clean = str(query)
    return bool(
        _has_specific_scope_signal(clean)
        or (
            len(clean) <= 28
            and re.search(
                r"具体|单一|一个|某一|是否|是什么|define|specific|single|whether|what is",
                clean,
                re.IGNORECASE,
            )
        )
        or not _is_broad_query(clean)
    )


def _comparison_object_count(query: str) -> int:
    clean = re.sub(r"[？?。.]$", "", str(query))
    if not re.search(r"比较|对比|versus|\bvs\.?\b|compare", clean, re.IGNORECASE):
        return 0
    lead = re.split(r"(?:的|在|方面|之间|差异|局限|优劣)", clean, 1)[0]
    lead = re.sub(r"^(?:请|比较|对比|compare)\s*", "", lead, flags=re.IGNORECASE)
    parts = [item.strip() for item in re.split(r"、|，|,|/|\band\b|和|与|及|versus|\bvs\.?\b", lead, flags=re.IGNORECASE) if item.strip()]
    return len(parts)


def _key_concepts(query: str) -> list[str]:
    clean = _normalize_text(query)
    parts = [
        item.strip(" ，,；;。?？:：")
        for item in re.split(r"[，,；;。?？:：]|如何|为什么|哪些|什么|是否|比较|分析|综述", clean)
        if 2 <= len(item.strip()) <= 36
    ]
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_.+-]{1,}", clean)
    return _unique([*parts, *latin])


def _anchor_research_query(subject: str, question: str) -> str:
    clean_subject = _normalize_text(subject)
    clean_question = _normalize_text(question)
    if not clean_subject:
        return clean_question
    if _scope_subject_relevance(clean_question, clean_subject) >= 0.45:
        return clean_question
    return f"{clean_subject}：{clean_question}"


def _scope_subject_relevance(text: str, subject: str) -> float:
    text_tokens = _text_tokens(text)
    subject_tokens = _text_tokens(subject)
    if not text_tokens or not subject_tokens:
        return 0.0
    return len(text_tokens & subject_tokens) / max(1, len(subject_tokens))


def _text_tokens(text: str) -> set[str]:
    normalized = _normalize_text(text).casefold()
    tokens = set(re.findall(r"[a-z0-9][a-z0-9_.+-]{1,}", normalized))
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        tokens.add(sequence)
        tokens.update(sequence[index:index + 2] for index in range(len(sequence) - 1))
    return tokens


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", _normalize_text(value).casefold())


def _payload(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        return dict(payload) if isinstance(payload, Mapping) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _unique(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _nonnegative_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _normalize_depth(depth: str) -> str:
    return {
        "low": "quick",
        "quick": "quick",
        "medium": "standard",
        "standard": "standard",
        "high": "deep",
        "deep": "deep",
    }.get(str(depth).strip().casefold(), "standard")


def _marker_ratio(units: Sequence[str], markers: Sequence[str]) -> float:
    if not units:
        return 0.0
    hits = sum(any(marker.casefold() in unit.casefold() for marker in markers) for unit in units)
    return min(1.0, hits / max(2, min(6, len(units))))


def _ratio_score(ratio: float) -> int:
    if ratio >= 0.8:
        return 5
    if ratio >= 0.6:
        return 4
    if ratio >= 0.4:
        return 3
    if ratio > 0:
        return 2
    return 1


def _context_around(text: str, needle: str) -> str:
    if not text or not needle:
        return ""
    match = re.search(re.escape(needle), text, re.IGNORECASE)
    if not match:
        return ""
    return text[max(0, match.start() - 60):match.end() + 240]


__all__ = [
    "ARCHETYPE_SPECS",
    "allocate_dynamic_budget",
    "anchor_domain_map",
    "build_coverage_matrix",
    "build_domain_map",
    "build_report_outline",
    "build_scope_contract",
    "build_section_drafts",
    "build_section_evidence_packs",
    "build_source_plans",
    "classify_query_archetype",
    "deduplicate_dimensions",
    "deterministic_comparison_dimensions",
    "derive_research_strategy",
    "gate_evidence_items",
    "estimate_query_complexity",
    "evaluate_generalized_research_quality",
    "merge_discovered_dimensions",
    "prioritize_coverage_gaps",
    "research_should_stop",
    "update_coverage_matrix",
]
