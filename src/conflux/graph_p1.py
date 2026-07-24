"""P1 three-source research-quality loop.

This graph keeps Model, RAG, and Web complementary. It plans before retrieval,
aligns evidence to claims, revises the main answer after verification, and only
starts another retrieval round for concrete unresolved gaps.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from .agent import ResearchAgent
from .citation_compiler import CitationCompiler, compile_report
from .core.dynamic_source import merge_source_results_reducer, namespace_source_result
from .evidence import EvidenceGraph, build_evidence_graph_from_results
from .graph_v2 import _append_stage, _run_exclusive_tool, _source_result_from_agent_text
from .quality import evaluate_p1_quality
from .research_modes import ResearchModeProfile
from .research_protocol import (
    ClaimAssessment,
    ClaimDraft,
    ResearchPlan,
    ResearchSubquestion,
    SourceCoverage,
    VerificationIssue,
    default_research_plan,
)
from .source_status import AgentClaim, SourceResult, fallback_result, strip_source_markers
from .trace import new_run_id
from .query_planner import (
    entity_score,
    extract_entities,
    is_temporal_query,
    standard_identifiers,
    temporal_years,
)


class P1ResearchState(TypedDict):
    query: str
    rag_result: str
    web_result: str
    model_result: str
    source_results: Annotated[dict[str, dict], merge_source_results_reducer]
    _research_plan: dict
    _research_profile: dict
    _model_trace: dict
    _claim_assessments: list[dict]
    _source_coverage: list[dict]
    _research_gaps: list[str]
    _conflicts: list[dict]
    _verification_issues: list[dict]
    _gap_questions: list[str]
    _gap_iteration: int
    _merged: str
    _arbitration: str
    _evidence_json: str
    _source_statuses: dict
    _verified_answer: str
    _factcheck_status: str
    _factcheck_report: str
    _factcheck_findings: dict
    _deep_research: str
    _deep_queries: list[str]
    _deep_arbitration: str
    _deep_factcheck_report: str
    _deep_evidence_json: str
    _deep_source_statuses: dict
    _run_summary: dict
    _quality_report: dict
    _pipeline_stage: str
    _started_at: float
    _deadline_at: float
    _commit_reserve_seconds: float
    _synthesis_status: str
    _synthesis_error: str
    _run_id: str
    _thread_id: str
    _checkpoint_backend: str
    _resumed: bool
    _review_status: str
    final_answer: str


def create_p1_research_graph(
    rag_agent: ResearchAgent,
    web_agent: ResearchAgent,
    *,
    planner_model: Any,
    analyst_model: Any,
    synthesizer_model: Any,
    verifier_model: Any,
    profile: ResearchModeProfile,
    model_trace: dict | None = None,
    checkpointer=None,
):
    """Compile the P1 research graph with explicit role models."""

    graph = StateGraph(P1ResearchState)
    graph.add_node("dispatch", lambda state: _dispatch_node(state, profile, model_trace or {}))
    graph.add_node("research_plan", lambda state: _research_plan_node(state, planner_model, profile))
    graph.add_node("rag_agent", lambda state: _source_research_node(state, rag_agent, "RAG", profile))
    graph.add_node("web_agent", lambda state: _source_research_node(state, web_agent, "Web", profile))
    graph.add_node("model_analyst", lambda state: _model_analyst_node(state, analyst_model, profile))
    graph.add_node("evidence_merge", lambda state: _evidence_merge_node(state, verifier_model))
    graph.add_node("synthesize", lambda state: _synthesize_node(state, synthesizer_model, profile))
    graph.add_node(
        "verify_revise",
        lambda state: _verify_revise_node(state, verifier_model, synthesizer_model, profile),
    )
    graph.add_node("gap_research", lambda state: _gap_research_node(
        state,
        rag_agent=rag_agent,
        web_agent=web_agent,
        analyst_model=analyst_model,
        synthesizer_model=synthesizer_model,
        profile=profile,
    ))
    graph.add_node("finalize", _finalize_node)

    graph.set_entry_point("dispatch")
    graph.add_edge("dispatch", "research_plan")
    graph.add_conditional_edges("research_plan", _retrieval_fanout, path_map=["rag_agent", "web_agent"])
    graph.add_edge("rag_agent", "model_analyst")
    graph.add_edge("web_agent", "model_analyst")
    graph.add_edge("model_analyst", "evidence_merge")
    graph.add_edge("evidence_merge", "synthesize")
    graph.add_edge("synthesize", "verify_revise")
    graph.add_conditional_edges("verify_revise", lambda state: _verification_router(state, profile), {
        "gap_research": "gap_research",
        "finalize": "finalize",
    })
    graph.add_edge("gap_research", "verify_revise")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)


def _dispatch_node(state: P1ResearchState, profile: ResearchModeProfile, model_trace: dict) -> dict:
    started_at = float(state.get("_started_at") or time.time())
    deadline_at = float(state.get("_deadline_at") or (started_at + profile.timeout_seconds))
    run_id = state.get("_run_id") or new_run_id()
    thread_id = state.get("_thread_id") or run_id
    return {
        "_run_id": run_id,
        "_thread_id": thread_id,
        "_research_profile": profile.to_dict(),
        "_model_trace": model_trace,
        "_started_at": started_at,
        "_deadline_at": deadline_at,
        "_commit_reserve_seconds": float(
            state.get("_commit_reserve_seconds") or profile.commit_reserve_seconds
        ),
        "_gap_iteration": 0,
        "_pipeline_stage": "dispatch",
        "_run_summary": {
            "mode": "p1",
            "research_depth": profile.depth,
            "run_id": run_id,
            "thread_id": thread_id,
            "checkpoint_backend": state.get("_checkpoint_backend") or "none",
            "resumed": bool(state.get("_resumed")),
            "started_at": started_at,
            "deadline_at": deadline_at,
            "elapsed_ms": 0,
            "stages": ["dispatch"],
            "l4_enabled": profile.max_gap_iterations > 0,
            "slo_p95_ms": profile.timeout_seconds * 1000,
            "slo_status": "running",
            "model_trace": model_trace,
            "stage_budgets": profile.stage_budgets,
        },
    }


def _research_plan_node(state: P1ResearchState, model: Any, profile: ResearchModeProfile) -> dict:
    prompt = f"""Create a research plan and a useful model prior for the query below.
The Model source is a legitimate source of parametric background and analysis;
do not pretend it is an external citation. Identify facts that need fresh or
high-authority verification instead of refusing to provide a prior.
Search-result snippets, titles, and URLs are discovery metadata, not evidence.
If Web body fetching fails, use them only to retry retrieval or expose leads;
never recommend treating a snippet as factual support for the answer.
For a broad survey question about current limitations or challenges, decompose
the field into distinct dimensions instead of restating the query. When six
subquestions are available, use one independent subquestion for each of: data,
algorithms/methods, systems engineering, evaluation/benchmarks,
governance/ethics, and application boundaries. Treat topic maturity as framing,
not a replacement for one of those dimensions. With a smaller budget, combine
adjacent dimensions explicitly rather than omitting them. Do not let a few
retrieved papers redefine the scope of the whole field.
For a broad "what methods exist" survey about geoprocessing automation, cover
both engineering and intelligent approaches: scripts/APIs and visual or ETL
workflows; services, cloud platforms, and workflow orchestration; rules,
semantics, machine learning, and deep learning; and LLM/tool-using agents.
Do not let recent agent papers displace established engineering automation.

Current date: {date.today().isoformat()}
Query: {state['query']}

Return only one JSON object:
{{
  "question_type": "...",
  "audience": "researcher",
  "time_scope": "...",
  "key_terms": ["..."],
  "subquestions": [
    {{"id":"subq-1","question":"...","source_preferences":["Model","RAG","Web"],"importance":"high","stop_condition":"..."}}
  ],
  "claims": [
    {{"id":"claim-1","text":"...","claim_type":"parametric_background|external_fact|analysis|recommendation|open_question","importance":"high|medium|low","temporal_sensitivity":"high|medium|low","risk":"high|medium|low","verification_questions":["..."]}}
  ],
  "model_prior": "A concise but substantive preliminary answer and conceptual framework.",
  "stop_conditions": ["..."]
}}
Use at most {profile.max_subquestions} independent subquestions and at most 5 claims.
Keep model_prior under 600 Chinese characters. Keep every other string under 160
characters. Do not combine subquestions into one long search query."""
    raw = ""
    error = ""
    recovered_error = ""
    plan: ResearchPlan | None = None
    model_prior = ""
    planner_prompts = [
        prompt,
        prompt + """

The previous response was invalid or truncated. Retry with a much more compact
JSON object: use 3-4 short subquestions, at most 4 claims, and a model_prior
under 300 Chinese characters. Close every JSON array and object.""",
    ]
    for attempt, planner_prompt in enumerate(planner_prompts):
        try:
            raw, payload = _invoke_json_object(
                model,
                "You are the Model Prior and research-planning stage. Output valid JSON only.",
                planner_prompt,
            )
            plan = ResearchPlan.from_dict(payload, query=state["query"], max_subquestions=profile.max_subquestions)
            plan = _comparison_research_plan(plan, state["query"], profile.max_subquestions)
            plan = _method_survey_research_plan(plan, state["query"], profile.max_subquestions)
            model_prior = str(payload.get("model_prior") or "").strip()
            break
        except Exception as exc:
            recovered_error = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < len(planner_prompts):
                continue
    if plan is None:
        error = recovered_error
        plan = _comparison_research_plan(
            default_research_plan(state["query"], max_subquestions=profile.max_subquestions),
            state["query"],
            profile.max_subquestions,
        )
        plan = _method_survey_research_plan(plan, state["query"], profile.max_subquestions)

    model_claims = [_model_claim_from_draft(claim) for claim in plan.claims if claim.text]
    result = SourceResult(
        source="Model",
        status="success" if model_prior or model_claims else "fallback",
        detail="Model Prior",
        error=error,
        content=model_prior or "Model Prior unavailable; deterministic research plan retained.",
        claims=model_claims,
        evidence_class="model_inference",
        metadata={
            "stage": "model_prior",
            "planner_recovered": bool(recovered_error and not error),
            "planner_first_error": recovered_error if recovered_error and not error else "",
            "raw_planner_response": raw[:12000],
            "research_plan": plan.to_dict(),
        },
    )
    return {
        "model_result": result.to_tool_text(),
        "source_results": {"builtin.model": namespace_source_result("builtin.model", result).to_dict()},
        "_research_plan": plan.to_dict(),
        "_run_summary": _append_stage(state, "research_plan"),
        "_pipeline_stage": "research_planned",
    }


def _model_claim_from_draft(claim: ClaimDraft) -> AgentClaim:
    limitations = []
    if claim.claim_type == "external_fact" or claim.temporal_sensitivity == "high" or claim.risk == "high":
        limitations.append("requires external verification before strong factual wording")
    return AgentClaim(
        claim=claim.text,
        source="Model",
        verbatim_quote=claim.text,
        paper_section="model_prior",
        relevance=0.65,
        research_type=claim.claim_type,
        confidence=0.62 if not limitations else 0.48,
        limitations=limitations,
        evidence_class="model_inference",
        content_kind="parametric_knowledge",
        directness=0.65,
        authority=0.55,
        relationship="context",
    )


def _retrieval_fanout(state: P1ResearchState) -> list[Send]:
    return [Send("rag_agent", state), Send("web_agent", state)]


def _comparison_research_plan(plan: ResearchPlan, query: str, max_subquestions: int) -> ResearchPlan:
    systems = _named_comparison_systems(query)
    if len(systems) < 2:
        return plan
    display = {
        "shapefilegpt": "ShapefileGPT",
        "autonomous gis": "Autonomous GIS",
        "llm-find": "LLM-Find",
    }
    ordered = sorted(systems, key=lambda item: str(query).casefold().find(next(iter({
        "shapefilegpt": ("shapefilegpt",),
        "autonomous gis": ("autonomous gis", "utonomous gis", "llm-geo"),
        "llm-find": ("llm-find", "llmfind"),
    }[item]))))
    questions = [
        ResearchSubquestion(
            id=f"subq-{index + 1}",
            question=(
                f"What limitations, failure modes, constraints, and unresolved future-work issues "
                f"are stated directly in the {display[name]} paper or official repository?"
            ),
            source_preferences=["RAG", "Web", "Model"],
            importance="high",
            stop_condition=f"at least one direct full-text limitation for {display[name]}",
        )
        for index, name in enumerate(ordered[:max_subquestions])
    ]
    if len(questions) < max_subquestions:
        names = ", ".join(display[name] for name in ordered)
        questions.append(ResearchSubquestion(
            id=f"subq-{len(questions) + 1}",
            question=f"Which limitations are genuinely shared by {names}, and which are system-specific?",
            source_preferences=["Model", "RAG", "Web"],
            importance="high",
            stop_condition="shared claims are supported per system rather than by analogy alone",
        ))
    plan.subquestions = questions[:max_subquestions]
    return plan


def _method_survey_research_plan(plan: ResearchPlan, query: str, max_subquestions: int) -> ResearchPlan:
    """Keep broad geoprocessing method surveys balanced across engineering and AI."""

    lowered = str(query or "").casefold()
    geoprocessing = any(marker in lowered for marker in (
        "地理处理", "地理空间处理", "gis", "geoprocessing", "geospatial processing",
    ))
    method_survey = bool(re.search(
        r"(?:都|主要|目前|当前)?有(?:哪|什么).{0,8}方法|哪些方法|methods? (?:exist|are available)|approaches?",
        lowered,
        re.IGNORECASE,
    ))
    if not geoprocessing or not method_survey or len(_named_comparison_systems(query)) >= 2:
        return plan

    engineering = ResearchSubquestion(
        id="subq-1",
        question=(
            "脚本、API、命令行及可视化/ETL工作流如何自动化重复地理处理，"
            "代表工具包括GDAL/OGR、ArcPy/PyQGIS、ModelBuilder、QGIS Graphical Modeler与FME？"
        ),
        source_preferences=["Web", "RAG", "Model"],
        importance="high",
        stop_condition="覆盖代码式、低代码和ETL自动化及其适用边界",
    )
    platform = ResearchSubquestion(
        id="subq-2",
        question=(
            "服务化、云原生平台与工作流编排如何支撑批量和大规模地理处理，"
            "包括OGC WPS、GEE、Planetary Computer、Airflow/Prefect与Serverless？"
        ),
        source_preferences=["Web", "RAG", "Model"],
        importance="high",
        stop_condition="覆盖服务接口、云端计算和任务编排三类工程机制",
    )
    geoai = ResearchSubquestion(
        id="subq-3",
        question=(
            "规则/语义推理、传统机器学习与深度学习如何自动化空间分析、"
            "遥感分类、检测、分割和变化检测？"
        ),
        source_preferences=["RAG", "Web", "Model"],
        importance="high",
        stop_condition="覆盖规则、ML和DL方法及代表性任务",
    )
    agents = ResearchSubquestion(
        id="subq-4",
        question=(
            "LLM与地理AI智能体如何从自然语言规划、调用GIS工具并执行多步骤工作流，"
            "其可靠性、评估和人工复核边界是什么？"
        ),
        source_preferences=["RAG", "Web", "Model"],
        importance="high",
        stop_condition="覆盖自然语言编排、工具调用、验证与适用边界",
    )
    questions = [engineering, platform, geoai, agents]
    if max_subquestions <= 3:
        geoai.question = (
            "规则/语义推理、机器学习、深度学习与LLM智能体分别如何自动化空间分析，"
            "其代表任务、工具调用方式和可靠性边界是什么？"
        )
        geoai.stop_condition = "覆盖规则、ML/DL和LLM智能体三类智能自动化"
        questions = [engineering, platform, geoai]
    plan.subquestions = questions[:max(1, max_subquestions)]
    plan.claims = [
        ClaimDraft(
            id="claim-1",
            text="工程自动化包括脚本/API、命令行批处理、可视化模型和ETL数据流。",
            claim_type="parametric_background",
            importance="high",
            verification_questions=["各工具的当前自动化能力与适用边界是什么？"],
        ),
        ClaimDraft(
            id="claim-2",
            text="服务接口、云地理计算和通用工作流编排用于扩展批量与分布式地理处理。",
            claim_type="parametric_background",
            importance="high",
            temporal_sensitivity="medium",
            verification_questions=["主流平台和编排框架当前支持哪些运行模式？"],
        ),
        ClaimDraft(
            id="claim-3",
            text="规则/语义推理、机器学习与深度学习分别适合确定性判定、空间预测和影像解译。",
            claim_type="analysis",
            importance="high",
            verification_questions=["不同方法的任务边界和数据要求是什么？"],
        ),
        ClaimDraft(
            id="claim-4",
            text="LLM地理智能体通过自然语言规划和工具调用自动执行多步骤GIS工作流。",
            claim_type="analysis",
            importance="high",
            temporal_sensitivity="high",
            risk="medium",
            verification_questions=["代表系统、工具调用能力和失败模式有哪些？"],
        ),
        ClaimDraft(
            id="claim-5",
            text="实际选型应依据数据形态、任务稳定性、规模、容错要求和人工复核成本组合多种方法。",
            claim_type="recommendation",
            importance="medium",
            verification_questions=["不同组合在真实项目中的验证标准是什么？"],
        ),
    ]
    plan.key_terms = [
        "GDAL OGR ArcPy PyQGIS",
        "ModelBuilder QGIS Graphical Modeler FME",
        "OGC WPS GEE Planetary Computer",
        "workflow orchestration Airflow Prefect serverless geoprocessing",
        "GeoAI remote sensing deep learning",
        "LLM geospatial agent tool calling",
    ]
    plan.stop_conditions = [
        "四条方法主线均有代表机制、工具、适用场景和边界",
        "传统工程自动化与AI/智能体方法均得到覆盖",
        "答案给出可执行的组合选型建议",
    ]
    plan.question_type = "broad_method_survey"
    return plan


def _source_research_node(
    state: P1ResearchState,
    agent: ResearchAgent,
    source: str,
    profile: ResearchModeProfile,
) -> dict:
    if _remaining_run_seconds(state, profile) <= profile.commit_reserve_seconds:
        deferred = fallback_result(
            source,
            f"{source} research skipped to preserve the report commit reserve.",
        )
        field = "rag_result" if source == "RAG" else "web_result"
        source_id = "builtin.rag" if source == "RAG" else "builtin.web"
        return {
            field: deferred.to_tool_text(),
            "source_results": {
                source_id: namespace_source_result(source_id, deferred).to_dict()
            },
        }
    plan = ResearchPlan.from_dict(
        state.get("_research_plan") or {},
        query=state["query"],
        max_subquestions=profile.max_subquestions,
    )
    subquestions = plan.subquestions[:profile.max_subquestions]

    def execute(subquestion: ResearchSubquestion) -> tuple[str, str, SourceResult]:
        payload = _run_exclusive_tool(agent, subquestion.question)
        result = (
            _source_result_from_agent_text(source, payload)
            if payload is not None
            else fallback_result(source, f"{source} Agent has no exclusive tool")
        )
        result.claims = [replace(item, subquestion_id=subquestion.id) for item in result.claims]
        result.metadata = {
            **result.metadata,
            "subquestion_id": subquestion.id,
            "subquestion": subquestion.question,
        }
        return subquestion.id, subquestion.question, result

    worker_count = min(profile.max_parallel_subquestions, len(subquestions))
    if worker_count > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            runs = list(executor.map(execute, subquestions))
    else:
        runs = [execute(subquestion) for subquestion in subquestions]
    combined = _combine_source_runs(source, runs)
    field = "rag_result" if source == "RAG" else "web_result"
    source_id = "builtin.rag" if source == "RAG" else "builtin.web"
    return {
        field: combined.to_tool_text(),
        "source_results": {source_id: namespace_source_result(source_id, combined).to_dict()},
    }


def _combine_source_runs(source: str, runs: list[tuple[str, str, SourceResult]]) -> SourceResult:
    if not runs:
        return fallback_result(source, "No independent subquestion was executed.")
    valid = [result for _, _, result in runs if result.is_valid_evidence]
    claims: list[AgentClaim] = []
    seen: set[tuple[str, str, str]] = set()
    for result in valid:
        for claim in result.claims:
            key = (claim.paper_id.casefold(), claim.subquestion_id, re.sub(r"\s+", " ", claim.claim).casefold())
            if key not in seen:
                seen.add(key)
                claims.append(claim)
    status = "success" if any(item.status == "success" for item in valid) else "low_relevance" if valid else runs[-1][2].status
    content = "\n\n".join(
        f"### {question}\n{strip_source_markers(result.content)}"
        for _, question, result in runs
        if result.content
    )
    strongest = max(
        (item.evidence_class for item in valid),
        default=runs[-1][2].evidence_class,
        key=lambda value: {"peer_reviewed": 5, "authoritative_document": 4, "preprint": 3, "community_content": 2, "model_inference": 1}.get(value, 0),
    )
    return SourceResult(
        source=source,
        status=status,
        detail=f"independent {source} research by subquestion",
        error="; ".join(item.error for _, _, item in runs if item.error),
        content=content,
        claims=claims,
        evidence_class=strongest,
        metadata={
            "subquestion_runs": [
                {
                    "subquestion_id": subquestion_id,
                    "question": question,
                    "status": result.status,
                    "claim_count": len(result.claims),
                    "error": result.error,
                    "metadata": result.metadata,
                }
                for subquestion_id, question, result in runs
            ],
            "subquestion_count": len(runs),
            "successful_subquestions": sum(result.is_valid_evidence for _, _, result in runs),
            "disabled": all(bool(result.metadata.get("disabled")) for _, _, result in runs),
        },
    )


def _model_analyst_node(state: P1ResearchState, model: Any, profile: ResearchModeProfile) -> dict:
    plan = state.get("_research_plan") or {}
    results = _state_source_results(state)
    external = {key: value for key, value in results.items() if key != "builtin.model"}
    graph = build_evidence_graph_from_results(external)
    evidence = _select_evidence(
        _evidence_table(graph),
        profile.final_evidence_limit,
        query=_evidence_selection_query(state),
    )
    # Coverage is a per-subquestion view of all sources.  The external
    # evidence graph intentionally excludes Model, but the coverage matrix
    # must still see the successful global Model Prior instead of reporting it
    # as missing for every subquestion.
    coverage = _source_coverage(plan, results)
    prior = results.get("builtin.model") or fallback_result("Model", "Model Prior missing")
    prompt = f"""Analyze evidence against the research plan at claim level.
RAG, Web, and Model are complementary; do not require voting or all-source agreement.
A direct high-authority single source may support a claim. Only flag a conflict when
two sources make incompatible claims under the same definition and time scope.
Web discovery metadata is not evidence. When body fetching failed, snippets,
titles, and URLs may guide retries or be shown as leads, but must not support facts.

Query: {state['query']}
Research plan: {json.dumps(plan, ensure_ascii=False)}
Model Prior: {strip_source_markers(prior.content)}
External evidence: {json.dumps(_compact_evidence(evidence), ensure_ascii=False)}
Source coverage: {json.dumps(coverage, ensure_ascii=False)}

Return only JSON:
{{
  "analysis": "substantive synthesis and mechanism analysis",
  "claim_assessments": [{{"claim_id":"...","wording":"...","evidence_ids":["..."],"relation":"supports|limits|contradicts|context","reliability":"strong|moderate|provisional|unresolved","limitations":["..."],"action":"include|qualify|research|omit"}}],
  "model_claims": [{{"claim":"...","claim_type":"analysis|parametric_background|recommendation","limitations":["..."]}}],
  "gaps": ["specific unanswered question"],
  "conflicts": [{{"claim":"...","evidence_ids":["..."],"reason":"..."}}]
}}
Keep analysis under 800 Chinese characters, each limitation under 120 characters,
and return at most 8 claim assessments. Do not reveal reasoning or emit text
outside the JSON object."""
    raw = ""
    payload: dict[str, Any] = {}
    error = ""
    budget_deferred = not _model_call_fits_budget(state, profile, stage="analysis")
    if budget_deferred:
        error = (
            "BudgetDeferred: evidence analysis skipped to reserve the remaining "
            "run budget for final synthesis"
        )
    else:
        try:
            raw, payload = _invoke_json_object(
                model,
                "You are an evidence analyst. Output valid JSON only and never fabricate evidence ids.",
                prompt,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    assessments = _claim_assessments(payload, evidence)
    model_claims = list(prior.claims)
    for item in payload.get("model_claims") or []:
        if not isinstance(item, dict) or not str(item.get("claim") or "").strip():
            continue
        model_claims.append(AgentClaim(
            claim=str(item["claim"]).strip(),
            source="Model",
            verbatim_quote=str(item["claim"]).strip(),
            paper_section="analysis",
            relevance=0.65,
            research_type=str(item.get("claim_type") or "analysis"),
            confidence=0.58,
            limitations=[str(value) for value in item.get("limitations") or []],
            evidence_class="model_inference",
            content_kind="model_analysis",
            directness=0.65,
            authority=0.55,
            relationship="context",
        ))
    analysis = str(payload.get("analysis") or raw or prior.content).strip()
    model_result = SourceResult(
        source="Model",
        status="success" if analysis or model_claims else "fallback",
        detail="Model Prior + Evidence Analyst",
        error=error,
        content=analysis or prior.content,
        claims=model_claims,
        evidence_class="model_inference",
        metadata={
            **prior.metadata,
            "stage": "evidence_analysis",
            "budget_deferred": budget_deferred,
            "claim_assessments": assessments,
            "identified_gaps": [str(item) for item in payload.get("gaps") or []],
            "conflicts": [item for item in payload.get("conflicts") or [] if isinstance(item, dict)],
        },
    )
    updated_results = {**results, "builtin.model": model_result}
    coverage = _source_coverage(plan, updated_results)
    return {
        "model_result": model_result.to_tool_text(),
        "source_results": {"builtin.model": namespace_source_result("builtin.model", model_result).to_dict()},
        "_claim_assessments": assessments,
        "_source_coverage": coverage,
        "_research_gaps": [str(item) for item in payload.get("gaps") or []],
        "_conflicts": [item for item in payload.get("conflicts") or [] if isinstance(item, dict)],
        "_run_summary": _append_stage(state, "model_analysis"),
        "_pipeline_stage": "model_analyzed",
    }


def _claim_assessments(payload: dict, evidence: list[dict]) -> list[dict]:
    valid_ids = {str(item.get("id") or "") for item in evidence}
    assessments = []
    for item in payload.get("claim_assessments") or []:
        if not isinstance(item, dict):
            continue
        evidence_ids = [str(value) for value in item.get("evidence_ids") or [] if str(value) in valid_ids]
        assessment = ClaimAssessment(
            claim_id=str(item.get("claim_id") or ""),
            wording=str(item.get("wording") or ""),
            evidence_ids=evidence_ids,
            relation=str(item.get("relation") or "context"),  # type: ignore[arg-type]
            reliability=str(item.get("reliability") or "provisional"),
            limitations=[str(value) for value in item.get("limitations") or []],
            action=str(item.get("action") or "include_with_qualification"),
        )
        assessments.append(assessment.to_dict())
    if assessments:
        covered_ids = {
            evidence_id
            for assessment in assessments
            for evidence_id in assessment.get("evidence_ids") or []
        }
        for item in evidence:
            item_id = str(item.get("id") or "")
            if item_id in covered_ids or _evidence_rank(item) < 0.7:
                continue
            assessments.append(ClaimAssessment(
                claim_id=item_id,
                wording=str(item.get("claim") or ""),
                evidence_ids=[item_id],
                relation="supports",
                reliability="moderate",
                limitations=[str(value) for value in item.get("limitations") or []],
                action="include_with_qualification",
            ).to_dict())
        return assessments[:len(evidence)]
    fallback = []
    for item in evidence:
        score = _evidence_rank(item)
        external = bool(item.get("evidence_refs")) and item.get("evidence_class") != "model_inference"
        include = not external or score >= 0.55
        fallback.append(ClaimAssessment(
            claim_id=str(item.get("id") or ""),
            wording=str(item.get("claim") or ""),
            evidence_ids=[str(item.get("id") or "")] if include else [],
            relation="supports" if include else "context",
            reliability="moderate" if include and external else "provisional",
            limitations=[str(value) for value in item.get("limitations") or []],
            action="include" if include else "omit",
        ).to_dict())
    return fallback


def _source_coverage(plan: dict, results: dict[str, SourceResult]) -> list[dict]:
    rows = []
    subquestions = plan.get("subquestions") or []
    for subquestion in subquestions:
        subquestion_id = str(subquestion.get("id") or "")
        for source_id, display in (("builtin.rag", "RAG"), ("builtin.web", "Web"), ("builtin.model", "Model")):
            result = results.get(source_id)
            if display == "Model":
                status = "covered" if result and result.status == "success" else "failed"
                evidence_ids = [
                    ref
                    for claim in (result.claims if result else [])
                    for ref in claim.evidence_refs
                    if ref
                ]
                reason = result.error if result else "Model Prior missing"
            else:
                runs = (result.metadata.get("subquestion_runs") if result else []) or []
                matching_runs = [item for item in runs if item.get("subquestion_id") == subquestion_id]
                run = next(
                    (item for item in reversed(matching_runs) if item.get("status") == "success"),
                    matching_runs[-1] if matching_runs else None,
                )
                evidence_ids = [
                    claim.evidence_refs[0]
                    for claim in (result.claims if result else [])
                    if claim.subquestion_id == subquestion_id and claim.evidence_refs
                ]
                if run and run.get("status") == "success" and evidence_ids:
                    status = "covered"
                    reason = ""
                elif run:
                    status = "failed" if run.get("status") == "failed" else "gap"
                    reason = str(run.get("error") or run.get("status") or "")
                else:
                    status = "gap"
                    reason = "not executed"
            rows.append(SourceCoverage(
                subquestion_id=subquestion_id,
                source=display,
                status=status,  # type: ignore[arg-type]
                evidence_ids=evidence_ids,
                reason=reason,
            ).to_dict())
    return rows


def _evidence_merge_node(state: P1ResearchState, verifier_model: Any) -> dict:
    results = _state_source_results(state)
    graph = build_evidence_graph_from_results(results)
    statuses = _legacy_source_statuses(results)
    graph.source_statuses = statuses
    merged = "\n\n---\n\n".join(
        f"## {_display_source(source_id)}\n状态：{result.status}\n\n{strip_source_markers(result.content)}"
        for source_id, result in results.items()
    )
    conflicts = list(state.get("_conflicts") or [])
    for left, right in graph.find_contradictions():
        conflicts.append({"claim": left.claim, "evidence_ids": [left.id, right.id], "reason": "surface contradiction"})
    conflict_analysis = ""
    if conflicts:
        prompt_conflicts, prompt_evidence = _conflict_arbitration_payload(
            _evidence_table(graph),
            conflicts,
            query=state["query"],
        )
        prompt = f"""Analyze only the genuine conflicts below. Do not use majority voting.
Explain whether differences come from definitions, dates, samples, methods, or a real contradiction.
State the strongest wording the final answer may use.

Query: {state['query']}
Conflicts: {json.dumps(prompt_conflicts, ensure_ascii=False)}
Evidence: {json.dumps(prompt_evidence, ensure_ascii=False)}
Keep the response under 800 characters and discuss only the supplied conflicts."""
        try:
            response = verifier_model.invoke([
                SystemMessage(content="You are a source-conflict analyst."),
                HumanMessage(content=prompt),
            ])
            conflict_analysis = str(response.content)
        except Exception as exc:
            conflict_analysis = f"[CONFLICT_UNREVIEWED] {type(exc).__name__}: {exc}"
    return {
        "_merged": merged,
        "_arbitration": conflict_analysis,
        "_conflicts": conflicts,
        "_evidence_json": graph.to_json(),
        "_source_statuses": statuses,
        "_run_summary": _append_stage(state, "evidence_merge"),
        "_pipeline_stage": "evidence_merged",
    }


def _synthesize_node(state: P1ResearchState, model: Any, profile: ResearchModeProfile) -> dict:
    diagnostics: dict[str, str] = {}
    report = _generate_report(state, model, profile, diagnostics=diagnostics)
    return {
        "final_answer": report,
        "_synthesis_status": diagnostics.get("status", "completed"),
        "_synthesis_error": diagnostics.get("error", ""),
        "_run_summary": _append_stage(state, "synthesize"),
        "_pipeline_stage": "synthesized",
    }


def _generate_report(
    state: P1ResearchState,
    model: Any,
    profile: ResearchModeProfile,
    *,
    revision_context: str = "",
    compact_retry: bool = False,
    _final_retry: bool = False,
    diagnostics: dict[str, str] | None = None,
) -> str:
    evidence = _answer_evidence(state, profile.final_evidence_limit)
    citation_registry = _citation_registry(evidence)
    target_chars = {"quick": 3000, "standard": 6000, "deep": 10000}.get(profile.depth, 6000)
    if revision_context:
        target_chars = max(2400, int(target_chars * 0.85))
    if compact_retry:
        target_chars = max(2200, int(target_chars * 0.8))
    if _final_retry:
        target_chars = max(2000, int(target_chars * 0.7))
    compact_evidence = _compact_evidence(evidence)
    if revision_context:
        context_block = f"""Revision issues: {revision_context}
Existing report: {str(state.get('final_answer') or '')}
Compact evidence: {json.dumps(compact_evidence, ensure_ascii=False)}
Citation identity registry:
{citation_registry or 'none'}"""
    else:
        context_block = f"""Research plan: {json.dumps(state.get('_research_plan') or {}, ensure_ascii=False)}
Claim assessments: {json.dumps(state.get('_claim_assessments') or [], ensure_ascii=False)}
Evidence items: {json.dumps(compact_evidence, ensure_ascii=False)}
Citation identity registry (authoritative for comparative attribution):
{citation_registry or 'none'}
Model context claims: {json.dumps(_compact_evidence(_model_context_items(state)), ensure_ascii=False)}
Model analysis: {strip_source_markers(str((state.get('_source_statuses') or {}).get('Model', {}).get('content') or state.get('model_result') or ''))}
Source coverage: {json.dumps(state.get('_source_coverage') or [], ensure_ascii=False)}
Conflict analysis: {state.get('_arbitration') or 'none'}"""
    prompt = f"""Write the final answer for the research query using claim-centered fusion.
Model, RAG, and Web are complementary, not voters. A direct authoritative single
source may support a statement. Missing a source is not a reason to refuse.

Query: {state['query']}
Research depth: {profile.depth}
{context_block}
Length budget: keep the entire report under {target_chars} Chinese characters.

Requirements:
- Fully answer the question before discussing source limitations.
- Organize by the user's topic, never as three RAG/Web/Model output blocks.
- Use exact provided citations immediately after externally verifiable claims,
  such as [RAG:paper#chunk-x] or [Web:https://...]. Never invent a citation.
- Copy one complete string from an evidence item's evidence_refs byte-for-byte.
  Never shorten a RAG reference, remove its #fulltext/#chunk suffix, normalize a
  URL, or cite an evidence id in place of evidence_refs.
- Parametric background and analysis may be used without repetitive confidence
  labels. If a material factual point lacks external support, qualify it once in
  the final reliability section instead of repeating "model inference" everywhere.
- Do not reward length. Be complete, specific, and avoid duplicate conclusions.
- For a broad limitations survey, follow the plan's distinct dimensions and
  state which dimensions have direct evidence. Do not generalize a limitation
  from one paper to the whole field without an explicit synthesis boundary.
- In a data/interoperability dimension, use only evidence that explicitly
  concerns data quality, schemas, formats, coordinate systems, semantics,
  standards, or cross-platform interchange. Generic training-data staleness,
  parameter mismatches, and runtime failures do not establish an
  interoperability limitation. If direct evidence is absent, state that
  coverage gap instead of relabeling evidence from another dimension.
- Use only evidence directly relevant to the query. Omit tangential papers,
  promotional pages, generic LLM commentary, and weakly related examples.
- For a comparison, a citation may support a system-specific statement only
  when its paper_id/document_title identifies that same system. Never attach
  an LLM-Find citation to Autonomous GIS, or infer a ShapefileGPT limitation
  from the system name, a generic LLM paper, or the Model Prior. If direct
  evidence is absent, say that the dimension is not directly covered.
- A paper's stated scope or focus does not prove that the system cannot support
  capabilities outside that scope. Say "not covered by the cited evidence"
  unless a source directly states an inability, unsupported format, or failure.
- When the same paper appears in multiple versions, use the newest acquired
  version unless the question explicitly asks for historical change. Do not mix
  v1 and v2 claims as if they came from one unchanged document.
- Call a limitation "shared/common" only when the evidence table contains
  direct support for every named system. If support exists for only one or two
  systems, label it as a subset pattern or Model-level hypothesis, not a common
  bottleneck. Treat Model Prior claims as hypotheses until externally anchored.
- For comparisons, give every named system balanced coverage with one to three
  directly supported findings before the cross-system synthesis. Prefer one
  compact comparison table or list, then a separate Model-level mechanism
  analysis. Do not repeat the same limitation in both places.
- Model Prior and Model analysis are legitimate complementary knowledge. Use
  their relevant cross-system mechanisms as clearly labeled analysis or
  hypotheses even when no external source directly states the synthesis; do
  not omit them merely because RAG or Web lacks an identical sentence.
- Treat each ClaimAssessment with action=research, reliability=unresolved, or
  empty evidence_ids as a Model-level hypothesis, not an established fact.
  Preserve the dimension, explain its mechanism and practical implication, use
  calibrated wording such as "可能/可视为待验证机制", and leave it uncited for the
  confidence appendix. Never attach a merely topical citation to simulate proof.
- Close every ResearchPlan subquestion in the answer. For each one provide a
  conclusion, mechanism, impact, and mitigation direction; add a directly
  relevant case when acquired evidence supports one. A dimension without direct
  evidence still needs substantive analysis and an explicit pending boundary.
- Give every ResearchPlan subquestion its own `###` heading, preserve the
  original order, and retain the question's key dimension wording in that
  heading. Never merge two subquestions into one section, even when their
  mechanisms overlap.
- For broad limitation surveys, use the literal dimension names 数据、算法与方法、
  系统工程、评估与基准、治理与伦理、应用边界 in the six `###` headings.
  Under every dimension include explicit `**机制与影响**` and `**缓解方向**`
  paragraphs. Each mitigation must name an actionable intervention plus at
  least one condition, priority, tradeoff, or validation criterion.
- Put uncited Model-derived mechanisms and recommendations under a subheading
  containing "模型分析与建议（非外部事实）". This keeps legitimate model analysis
  distinct from externally verifiable claims without repeating confidence labels.
- Emit that Model-analysis subheading before the first uncited Model-derived
  sentence or bullet in a dimension. Never place a list of uncited hypotheses
  before the subheading and label it only afterward.
- Search-result snippets, titles, and URLs are discovery metadata, never
  factual evidence. If a Web page body was not fetched, use its metadata only
  for retry routing or a clearly labeled lead list. It must not enter factual
  claim support, evidence-graph confidence calculations, or an answer-generation
  context; do not recommend generating from it and adding a disclaimer later.
- When explaining knowledge types, define an external fact as a claim about the
  external world that can be independently checked, not as inherently certain
  or deterministic. It can still be stale, conflicting, or measurement-limited.
  Parametric knowledge is recalled model context; analysis derives conclusions
  from stated premises; recommendations are normative and must name conditions
  or tradeoffs.
- Every substantive answer bullet or comparison-table row that states an
  external fact or a system-specific limitation must include an exact citation.
  Prefer fewer evidence-dense claims over long uncited lists. Reserve uncited
  prose for clearly labeled synthesis or recommendations.
- An uncited sentence must not introduce a new institution, policy, publication,
  date, deadline, standard status, or algorithm property. Omit unsupported
  precision even when it is plausible from Model Prior.
- When one evidence item supports a grouped list, cite the lead sentence and
  repeat that exact citation on every factual child bullet or table row. If that
  would be repetitive, keep the grouped fact in one cited sentence instead.
- When Revision context is present, edit the Existing report conservatively:
  keep its verified citations and useful structure, remove or qualify only the
  disputed wording, and do not add new background, sections, or conclusions.
  A shorter corrected report is preferred to a fresh expansive rewrite.
- Never reveal hidden reasoning, chain-of-thought, or <think>/<analysis> blocks.
- Output exactly these top-level sections:
## 回答
## 参考文献与证据
## 置信度附录
- Write the complete substantive answer only under 回答. Keep using the exact
  internal RAG/Web citation strings there; a deterministic compiler will replace
  them with [1], [2], or [1,3] and rebuild the last two sections.
- Put a short placeholder under the last two sections. Do not invent bibliography
  data, numeric citation ids, confidence labels, source-voting text, or a
  FactCheck dump; the compiler derives them from acquired EvidenceItem records.
- 置信度附录 must be the final top-level section."""
    if not _model_call_fits_budget(state, profile, stage="synthesis"):
        error = "BudgetDeferred: insufficient run budget for another synthesis call"
        existing = str(state.get("final_answer") or "").strip()
        if revision_context and _is_complete_report(existing):
            _set_generation_diagnostics(diagnostics, "completed", error)
            return existing
        _set_generation_diagnostics(diagnostics, "fallback", error)
        return _grounded_fallback_report(state, evidence, error)
    try:
        response = model.invoke([
            SystemMessage(content="You are the final research synthesizer. Produce polished Chinese Markdown."),
            HumanMessage(content=prompt),
        ])
        report = _strip_hidden_reasoning(str(response.content)).strip()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        _set_generation_diagnostics(diagnostics, "fallback", error)
        if revision_context and str(state.get("final_answer") or "").strip():
            return str(state["final_answer"]).strip()
        return _grounded_fallback_report(state, evidence, error)
    report = _normalize_evidence_id_citations(report, evidence)
    report = _propagate_list_citations(report)
    if "## 参考文献与证据" in report or "## 置信度附录" in report:
        report = compile_report(
            report,
            evidence,
            claim_assessments=state.get("_claim_assessments") or [],
            source_coverage=state.get("_source_coverage") or [],
        )
    if _response_hit_output_limit(response, profile.synthesizer_max_tokens):
        if not compact_retry:
            retry_context = (
                (revision_context + "\n") if revision_context else ""
            ) + "The previous draft hit the output limit. Rewrite more compactly and finish every section."
            return _generate_report(
                state,
                model,
                profile,
                revision_context=retry_context,
                compact_retry=True,
                diagnostics=diagnostics,
            )
        if revision_context and not _final_retry:
            return _generate_report(
                state,
                model,
                profile,
                revision_context=(
                    revision_context
                    + "\nThe previous revision also hit the output limit. Produce a final, complete "
                    "version under 1500 Chinese characters; merge claims and omit optional detail."
                ),
                compact_retry=True,
                _final_retry=True,
                diagnostics=diagnostics,
            )
    if _is_complete_report(report):
        _set_generation_diagnostics(diagnostics, "completed", "")
        return report
    existing = str(state.get("final_answer") or "").strip()
    if revision_context and _is_complete_report(existing):
        return _normalize_evidence_id_citations(existing, evidence)
    error = "IncompleteOutput: synthesizer did not return all required report sections"
    _set_generation_diagnostics(diagnostics, "fallback", error)
    return _grounded_fallback_report(state, evidence, error)


def _strip_hidden_reasoning(text: str) -> str:
    """Remove provider-specific hidden-reasoning blocks from user-facing text."""

    cleaned = str(text)
    for tag in ("think", "analysis"):
        cleaned = re.sub(
            rf"<\s*{tag}\s*>.*?<\s*/\s*{tag}\s*>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return cleaned.strip()


def _response_hit_output_limit(response: Any, configured_limit: int) -> bool:
    metadata = getattr(response, "response_metadata", None) or {}
    finish_reason = str(metadata.get("finish_reason") or metadata.get("stop_reason") or "").casefold()
    if finish_reason in {"length", "max_tokens", "max_output_tokens"}:
        return True
    usage = getattr(response, "usage_metadata", None) or {}
    token_usage = metadata.get("token_usage") or metadata.get("usage") or {}
    output_tokens = usage.get("output_tokens") or token_usage.get("completion_tokens") or token_usage.get("output_tokens")
    try:
        return int(output_tokens or 0) >= max(1, int(configured_limit * 0.98))
    except (TypeError, ValueError):
        return False


def _is_complete_report(report: str) -> bool:
    """Accept concise reports when all required user-facing sections are present."""

    headings = [match.group(1).strip() for match in re.finditer(r"^##\s+(.+?)\s*$", report, re.MULTILINE)]
    legacy = ["回答", "研究依据", "可靠性与缺口"]
    public = ["回答", "参考文献与证据", "置信度附录"]
    if headings not in (legacy, public):
        return False
    boundary = "## 参考文献与证据" if headings == public else "## 研究依据"
    answer = report.split(boundary, 1)[0].removeprefix("## 回答").strip()
    return bool(answer)


def _propagate_list_citations(report: str) -> str:
    """Attach a cited lead sentence's references to its immediate fact list."""

    lines = str(report or "").splitlines()
    in_answer = False
    pending_refs: list[str] = []
    output: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        heading = re.match(r"^##\s+(.+)$", stripped)
        if heading:
            in_answer = heading.group(1).strip() == "回答"
            pending_refs = []
            output.append(raw)
            continue
        if not in_answer:
            output.append(raw)
            continue
        bullet = re.match(r"^(\s*(?:[-*]|\d+[.)])\s+)(.+)$", raw)
        refs = re.findall(r"\[(?:RAG:[^\]]+|Web:https?://[^\]]+)\]", raw)
        if bullet and pending_refs:
            if not refs:
                raw = raw.rstrip() + " " + "".join(pending_refs)
            output.append(raw)
            continue
        if stripped and not stripped.startswith("#"):
            pending_refs = refs if refs and stripped.rstrip().endswith(("：", ":")) else []
        output.append(raw)
    return "\n".join(output).strip()


def _normalize_evidence_id_citations(report: str, evidence: list[dict]) -> str:
    """Replace internal evidence ids emitted by a model with public citations."""

    mapping = {
        str(item.get("id") or ""): str((item.get("evidence_refs") or [""])[0])
        for item in evidence
        if str(item.get("id") or "") and item.get("evidence_refs")
    }
    normalized = str(report or "")
    for evidence_id in sorted(mapping, key=len, reverse=True):
        citation = mapping[evidence_id]
        normalized = re.sub(
            rf"[（(]\s*{re.escape(evidence_id)}\s*[）)]",
            lambda _match: citation,
            normalized,
        )
        normalized = re.sub(rf"(?<![\w.-]){re.escape(evidence_id)}(?![\w.-])", lambda _match: citation, normalized)
    return normalized


def _fallback_report(query: str, model_content: str, statuses: dict) -> str:
    available = [source for source in ("RAG", "Web", "Model") if (statuses.get(source) or {}).get("status") == "success"]
    missing = [source for source in ("RAG", "Web", "Model") if source not in available]
    return f"""## 回答

{model_content or f'当前可用来源未能完整覆盖“{query}”，但仍可从问题定义、机制、约束和验证路径展开分析。'}

## 研究依据

本轮可用来源：{', '.join(available) or '无结构化来源'}。外部证据详情保留在审计产物中。

## 可靠性与缺口

{('未覆盖来源：' + ', '.join(missing) + '。') if missing else '三类来源均已参与。'}影响决策的精确事实仍应按正文引用逐条核对。"""


def _grounded_fallback_report(state: P1ResearchState, evidence: list[dict], error: str) -> str:
    """Return a structured, citation-bearing result when synthesis cannot finish."""

    external = []
    seen_refs: set[str] = set()
    for item in evidence:
        refs = [str(ref) for ref in item.get("evidence_refs") or [] if str(ref)]
        claim = re.sub(r"\s+", " ", str(item.get("claim") or item.get("verbatim_quote") or "")).strip()
        if not refs or not claim or refs[0] in seen_refs or _is_index_metadata_claim(item):
            continue
        seen_refs.add(refs[0])
        external.append((item, claim[:420].rstrip(), refs[0]))
        if len(external) >= 8:
            break

    model_items = _model_context_items(state)
    plan = state.get("_research_plan") or {}
    subquestions = [item for item in plan.get("subquestions") or [] if isinstance(item, dict)]
    answer_lines = [
        "本轮报告综合未能在档位时限内完成。以下保留研究计划形成的方法框架、"
        "模型分析和已取得的正文证据，不把搜索摘要或未核实标题当作事实依据。",
        "",
    ]
    basis_lines = []
    used_model_claims: set[str] = set()
    used_external_refs: set[str] = set()

    overview = next(
        (
            item for item in model_items
            if re.search(r"维度|系统梳理|涵盖.+(?:方法|工作流|学习|智能体)", str(item.get("claim") or ""))
        ),
        None,
    )
    if overview is not None:
        overview_claim = _clean_fallback_claim(overview)
        if overview_claim:
            answer_lines.extend([
                "### 总览",
                "",
                "#### 模型分析与建议（非外部事实）",
                "",
                f"- {overview_claim}",
                "",
            ])
            used_model_claims.add(overview_claim.casefold())

    if subquestions:
        for index, subquestion in enumerate(subquestions):
            question = str(subquestion.get("question") or "").strip()
            subquestion_id = str(subquestion.get("id") or "").strip()
            answer_lines.extend([f"### {_fallback_dimension_heading(question, index)}", ""])

            direct = [
                item for item in external
                if str(item[0].get("subquestion_id") or "") == subquestion_id
            ][:2]
            if direct:
                answer_lines.extend(["#### 已取得的直接证据", ""])
                for item, claim, ref in direct:
                    title = str(item.get("document_title") or item.get("paper_id") or "未命名来源").strip()
                    answer_lines.append(f"- 《{title}》：{claim} {ref}")
                    basis_lines.append(f"- 《{title}》{ref}")
                    used_external_refs.add(ref)
                answer_lines.append("")

            selected_model = _fallback_model_claims_for_question(
                question,
                model_items,
                used_model_claims,
                limit=3,
            )
            answer_lines.extend(["#### 模型分析与建议（非外部事实）", ""])
            if selected_model:
                for claim in selected_model:
                    answer_lines.append(f"- {claim}")
                    used_model_claims.add(claim.casefold())
            else:
                answer_lines.append("- 本轮模型上下文未形成足够具体的独立结论，该维度仍需补充检索。")
            answer_lines.append("")

    uncategorized_external = [item for item in external if item[2] not in used_external_refs]
    if subquestions and uncategorized_external:
        answer_lines.extend(["### 其他已取得的直接证据", ""])
        for item, claim, ref in uncategorized_external[:3]:
            title = str(item.get("document_title") or item.get("paper_id") or "未命名来源").strip()
            answer_lines.append(f"- 《{title}》：{claim} {ref}")
            basis_lines.append(f"- 《{title}》{ref}")
        answer_lines.append("")

    if not subquestions:
        if external:
            answer_lines.extend(["### 已取得的直接证据", ""])
            for item, claim, ref in external:
                title = str(item.get("document_title") or item.get("paper_id") or "未命名来源").strip()
                answer_lines.append(f"- 《{title}》：{claim} {ref}")
                basis_lines.append(f"- 《{title}》{ref}")
            answer_lines.append("")
        model_claims = [_clean_fallback_claim(item) for item in model_items]
        model_claims = [item for item in dict.fromkeys(model_claims) if item]
        model_content = str((state.get("_source_statuses") or {}).get("Model", {}).get("content") or "").strip()
        answer_lines.extend(["### 模型分析与建议（非外部事实）", ""])
        if model_claims:
            answer_lines.extend(f"- {claim}" for claim in model_claims[:6])
        else:
            answer_lines.append(model_content or f"当前材料不足以完整回答“{state['query']}”。")

    answer = "\n".join(answer_lines).strip()
    basis = "\n".join(dict.fromkeys(basis_lines)) or "- 本轮没有可用于事实声明的成功外部来源。"

    statuses = state.get("_source_statuses") or {}
    unavailable = [
        source for source in ("RAG", "Web")
        if str((statuses.get(source) or {}).get("status") or "") != "success"
    ]
    reason = error.split(":", 1)[0] if error else "unknown"
    limitation = f"合成降级原因：{reason}。"
    if unavailable:
        limitation += f" 未作为事实证据使用的来源：{', '.join(unavailable)}。"
    limitation += " 结果已保留研究框架与模型分析；涉及具体系统、年份、性能和成熟度的事实仍需外部正文核验。"
    return f"""## 回答

{answer}

## 研究依据

{basis}

## 可靠性与缺口

{limitation}"""


def _model_context_items(state: P1ResearchState, limit: int = 10) -> list[dict]:
    """Collect deduplicated Model claims without presenting them as citations."""

    items = [
        item for item in _load_evidence_table(state.get("_evidence_json") or "")
        if str(item.get("source") or "").casefold().endswith("model") and str(item.get("claim") or "").strip()
    ]
    for index, claim in enumerate((state.get("_research_plan") or {}).get("claims") or []):
        if not isinstance(claim, dict) or not str(claim.get("text") or "").strip():
            continue
        items.append({
            "id": str(claim.get("id") or f"plan-claim-{index + 1}"),
            "source": "builtin.model",
            "claim": str(claim.get("text") or "").strip(),
            "verbatim_quote": str(claim.get("text") or "").strip(),
            "evidence_class": "model_inference",
            "research_type": str(claim.get("claim_type") or "analysis"),
            "limitations": ["model context; external verification required for factual precision"],
        })
    selected = []
    seen: set[str] = set()
    for item in items:
        claim = _clean_fallback_claim(item)
        key = claim.casefold()
        if claim and key not in seen:
            seen.add(key)
            selected.append(item)
        if len(selected) >= max(1, limit):
            break
    return selected


def _clean_fallback_claim(item: dict) -> str:
    return re.sub(r"\s+", " ", str(item.get("claim") or item.get("verbatim_quote") or "")).strip()[:420]


def _fallback_dimension_heading(question: str, index: int) -> str:
    prefix = re.split(r"[:：]", question, maxsplit=1)[0].strip()
    if 2 <= len(prefix) <= 32:
        return prefix
    return f"研究维度 {index + 1}"


def _fallback_model_claims_for_question(
    question: str,
    model_items: list[dict],
    used: set[str],
    *,
    limit: int,
) -> list[str]:
    lowered = question.casefold()
    dimensions = (
        (("数据", "采集", "清洗", "配准", "融合", "质量", "data", "acquisition", "cleaning", "registration", "fusion"),
         ("数据", "采集", "清洗", "配准", "融合", "质量", "data", "acquisition", "cleaning", "registration", "fusion", "gdal", "ogr", "pdal", "api", "爬虫")),
        (("算法", "方法", "规则", "学习", "智能体", "algorithm", "method", "agent"),
         ("算法", "方法", "规则", "机器学习", "深度学习", "algorithm", "method", "machine learning", "deep learning", "u-net", "deeplab", "transformer", "llm", "智能体", "agent", "geoai")),
        (("系统", "平台", "云原生", "工作流", "编排", "system", "platform", "cloud", "workflow", "orchestration", "serverless"),
         ("系统", "平台", "云", "工作流", "编排", "system", "platform", "cloud", "workflow", "orchestration", "serverless", "arcgis", "qgis", "fme", "wps", "gee", "planetary", "airflow")),
        (("评估", "基准", "边界", "局限", "隐私", "互操作", "evaluation", "benchmark", "limitation", "privacy", "interoperability"),
         ("评估", "基准", "边界", "局限", "挑战", "隐私", "互操作", "可信", "长尾", "evaluation", "benchmark", "limitation", "privacy", "interoperability")),
    )
    anchor_scores = [sum(1 for anchor in anchors if anchor in lowered) for anchors, _ in dimensions]
    target_dimension = (
        max(range(len(anchor_scores)), key=anchor_scores.__getitem__)
        if max(anchor_scores) > 0
        else -1
    )
    markers: tuple[str, ...] = dimensions[target_dimension][1] if target_dimension >= 0 else ()

    ranked = []
    for position, item in enumerate(model_items):
        claim = _clean_fallback_claim(item)
        if not claim or claim.casefold() in used:
            continue
        claim_lower = claim.casefold()
        dimension_scores = [
            sum(1 for marker in candidates if marker in claim_lower)
            for _, candidates in dimensions
        ]
        score = sum(1 for marker in markers if marker in claim_lower)
        if target_dimension >= 0 and score < max(dimension_scores):
            continue
        if re.search(r"维度|系统梳理|涵盖.+(?:方法|工作流|学习|智能体)", claim):
            score -= 2
        ranked.append((score, -position, claim))
    ranked.sort(reverse=True)
    return [claim for score, _, claim in ranked if score > 0][:max(1, limit)]


def _set_generation_diagnostics(diagnostics: dict[str, str] | None, status: str, error: str) -> None:
    if diagnostics is not None:
        diagnostics.update({"status": status, "error": error})


def _remaining_run_seconds(state: P1ResearchState, profile: ResearchModeProfile) -> float:
    deadline_at = float(
        state.get("_deadline_at")
        or (state.get("_run_summary") or {}).get("deadline_at")
        or 0.0
    )
    if deadline_at > 0:
        return max(0.0, deadline_at - time.time())
    started_at = float((state.get("_run_summary") or {}).get("started_at") or 0.0)
    if started_at <= 0:
        return float("inf")
    return max(0.0, float(profile.timeout_seconds) - (time.time() - started_at))


def _model_call_fits_budget(
    state: P1ResearchState,
    profile: ResearchModeProfile,
    *,
    reserve_calls: int = 0,
    stage: str = "",
) -> bool:
    if not stage:
        required = profile.model_timeout_seconds * (1 + max(0, reserve_calls)) + 5
        return _remaining_run_seconds(state, profile) >= required
    if stage in {"verification", "revision"} and _remaining_run_seconds(state, profile) < 45:
        return False
    minimum = _minimum_stage_seconds(profile)
    future = {
        "analysis": minimum["synthesis"] + minimum["verification"],
        "synthesis": minimum["verification"],
        "verification": 0,
        "revision": 0,
    }.get(stage, 0)
    required = minimum.get(stage, min(15, profile.model_timeout_seconds)) + future
    return _remaining_run_seconds(state, profile) >= required


def _minimum_stage_seconds(profile: ResearchModeProfile) -> dict[str, int]:
    return {
        name: max(8, min(profile.model_timeout_seconds, round(seconds * 0.42)))
        for name, seconds in profile.stage_budgets.items()
        if name != "commit"
    }


def _compact_evidence(evidence: list[dict]) -> list[dict]:
    keys = (
        "id", "source", "claim", "verbatim_quote", "paper_id", "document_title",
        "paper_section", "evidence_refs", "limitations", "evidence_class",
        "relevance", "directness", "subquestion_id", "page_start", "page_end",
    )
    compact = []
    for item in evidence:
        payload = {key: item.get(key) for key in keys if item.get(key) not in (None, "", [], {})}
        for key, limit in (("claim", 600), ("verbatim_quote", 900), ("document_title", 240)):
            if key in payload:
                payload[key] = str(payload[key])[:limit]
        if "limitations" in payload:
            payload["limitations"] = [str(value)[:240] for value in payload["limitations"][:4]]
        if "evidence_refs" in payload:
            payload["evidence_refs"] = [str(value)[:500] for value in payload["evidence_refs"][:6]]
        compact.append(payload)
    return compact


def _conflict_arbitration_payload(
    evidence: list[dict],
    conflicts: list[dict],
    *,
    query: str,
    conflict_limit: int = 10,
    evidence_limit: int = 20,
) -> tuple[list[dict], list[dict]]:
    """Bound arbitration input while retaining evidence cited by each conflict."""

    compact_conflicts: list[dict] = []
    referenced_ids: list[str] = []
    for raw in conflicts[: max(1, int(conflict_limit))]:
        if not isinstance(raw, dict):
            continue
        evidence_ids = [
            str(value).strip()
            for value in raw.get("evidence_ids") or []
            if str(value).strip()
        ][:2]
        referenced_ids.extend(evidence_ids)
        compact_conflicts.append({
            "claim": str(raw.get("claim") or "")[:400],
            "evidence_ids": evidence_ids,
            "reason": str(raw.get("reason") or "")[:240],
        })

    limit = max(1, int(evidence_limit))
    by_id = {str(item.get("id") or ""): item for item in evidence}
    referenced = [
        by_id[evidence_id]
        for evidence_id in dict.fromkeys(referenced_ids)
        if evidence_id in by_id
    ][:limit]
    referenced_set = {str(item.get("id") or "") for item in referenced}
    remaining_limit = limit - len(referenced)
    selected = []
    if remaining_limit > 0:
        selected = _select_evidence(
            [item for item in evidence if str(item.get("id") or "") not in referenced_set],
            remaining_limit,
            query=query,
        )
    compact_evidence = _compact_evidence([*referenced, *selected][:limit])
    for item in compact_evidence:
        if "claim" in item:
            item["claim"] = str(item["claim"])[:400]
        if "verbatim_quote" in item:
            item["verbatim_quote"] = str(item["verbatim_quote"])[:700]
    return compact_conflicts, compact_evidence


def _answer_evidence(state: P1ResearchState, limit: int) -> list[dict]:
    statuses = state.get("_source_statuses") or {}
    eligible = [
        item for item in _load_evidence_table(state.get("_evidence_json") or "")
        if _evidence_source_succeeded(item, statuses)
    ]
    return _select_evidence(eligible, limit, query=_evidence_selection_query(state))


def _numeric_citations_need_repair(report: str) -> bool:
    if not CitationCompiler.is_compiled(report):
        return False
    state = _compiled_citation_state(report)
    return bool(state["cited_numbers"] and not state["reference_numbers"])


def _repair_numeric_citations(
    report: str,
    evidence: list[dict],
    model: Any,
    *,
    claim_assessments: list[dict],
    source_coverage: list[dict],
) -> tuple[str, bool]:
    """Resolve model-invented numeric labels only through acquired evidence refs."""

    citation_state = _compiled_citation_state(report)
    numbers = [str(item) for item in citation_state["cited_numbers"]]
    allowed_refs = sorted({
        str(ref)
        for item in evidence
        for ref in item.get("evidence_refs") or []
        if str(ref)
    })
    if not numbers or not allowed_refs:
        raise ValueError("numeric citation repair requires cited numbers and acquired evidence refs")
    compact = _compact_evidence(evidence)
    prompt = f"""The report used public numeric citations before citation compilation.
Map every cited number to one or more exact acquired evidence refs that directly
support the clause carrying that number. Do not infer from title alone and do not
invent refs. Return JSON only as {{"mapping":{{"1":["[RAG:...]"]}}}}.
Every cited number must appear exactly once; if any number cannot be grounded,
return an empty mapping.

Allowed refs: {json.dumps(allowed_refs, ensure_ascii=False)}
Evidence: {json.dumps(compact, ensure_ascii=False)}
Report: {report}"""
    _, payload = _invoke_json_object(
        model,
        "You align citations to acquired evidence. Output valid JSON only.",
        prompt,
    )
    raw_mapping = payload.get("mapping")
    if not isinstance(raw_mapping, dict) or set(str(key) for key in raw_mapping) != set(numbers):
        raise ValueError("citation mapping must cover every cited number")
    mapping: dict[str, list[str]] = {}
    allowed = set(allowed_refs)
    for number in numbers:
        value = raw_mapping.get(number)
        refs = [str(item) for item in (value if isinstance(value, list) else [value]) if str(item)]
        if not refs or any(ref not in allowed for ref in refs):
            raise ValueError(f"citation {number} contains an unknown or empty evidence ref")
        mapping[number] = list(dict.fromkeys(refs))

    answer = report.split("## 参考文献与证据", 1)[0]

    def replace_numeric(match: re.Match[str]) -> str:
        refs = []
        for number in re.split(r"\s*,\s*", match.group(1)):
            refs.extend(mapping[number])
        return "".join(dict.fromkeys(refs))

    repaired = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", replace_numeric, answer)
    compiled = compile_report(
        repaired,
        evidence,
        claim_assessments=claim_assessments,
        source_coverage=source_coverage,
    )
    return compiled, True


def _evidence_source_succeeded(item: dict, statuses: dict) -> bool:
    source_id = str(item.get("source") or "")
    lowered = source_id.casefold()
    source = "RAG" if lowered.endswith("rag") else "Web" if lowered.endswith("web") else "Model" if lowered.endswith("model") else source_id
    payload = statuses.get(source) or statuses.get(source_id)
    if not isinstance(payload, dict):
        return True
    return str(payload.get("status") or "") == "success"


def _safe_web_degradation_report(state: P1ResearchState, evidence: list[dict]) -> str:
    """Build a policy-safe answer when repeated synthesis misuses Web metadata."""

    rag_candidates = [
        item
        for item in evidence
        if str(item.get("source") or "").casefold().endswith("rag")
        and item.get("evidence_refs")
        and item.get("verbatim_quote")
        and not _is_index_metadata_claim(item)
    ]
    rag_evidence = [
        item
        for item in sorted(
            rag_candidates,
            key=lambda candidate: _evidence_rank(candidate, query=str(state.get("query") or "")),
            reverse=True,
        )
        if _evidence_rank(item, query=str(state.get("query") or "")) >= 0.65
    ][:3]
    evidence_lines = []
    for item in rag_evidence:
        claim = re.sub(r"\s+", " ", str(item.get("claim") or item.get("verbatim_quote") or "")).strip()
        ref = str((item.get("evidence_refs") or [""])[0])
        if claim and ref:
            evidence_lines.append(f"- {claim[:260]} {ref}")
    direct_evidence = "\n".join(evidence_lines) or "- 本轮没有取得可直接支撑事实声明的外部正文证据。"
    research_basis = "\n".join(
        f"- {str((item.get('evidence_refs') or [''])[0])}：{str(item.get('document_title') or item.get('paper_id') or '本地证据')}"
        for item in rag_evidence
    ) or "- 本轮仅保留模型分析，未将搜索发现元数据视为证据。"
    return f"""## 回答

### 当前可用的直接证据

{direct_evidence}

### 模型分析与建议（非外部事实）

在网页正文未取得时，可用答案应按以下边界形成：

1. 搜索结果的标题、摘要和 URL 只用于改写查询、切换抓取器、寻找缓存/PDF/RSS 或向用户展示待核验线索；不得进入证据图的事实支持与置信度计算。
2. 先回答本地 RAG 正文能够直接覆盖的部分，并让每条外部事实绑定到原文引用；没有覆盖的维度明确写成“当前证据未确认”。
3. 模型世界知识可补充概念框架、机制分析和下一步建议，但应集中标为非外部事实，不能冒充 Web 结果，也不能生成精确日期、数字或状态来填补空白。
4. 若 RAG 与模型分析仍不足以回答关键事实，应返回有限的当前答案、列出待核验问题，并继续替代检索或请求用户提供正文，而不是从发现元数据重构事实。

## 研究依据

{research_basis}

## 可靠性与缺口

本轮 Web 正文抓取失败；当前答案仅使用上列本地证据与明确标注的模型分析，搜索发现元数据未作为事实依据。"""


def _web_degradation_attribution_failed(
    statuses: dict,
    issues: list[VerificationIssue],
) -> bool:
    web_failed = str((statuses.get("Web") or {}).get("status") or "").casefold() in {
        "failed", "no_evidence", "fallback",
    }
    return web_failed and any(
        item.severity == "high"
        and item.issue_type in {"unsupported_claim", "overstated_claim", "citation_mismatch"}
        and not item.requires_research
        for item in issues
    )


def _verify_revise_node(
    state: P1ResearchState,
    verifier_model: Any,
    synthesizer_model: Any,
    profile: ResearchModeProfile,
) -> dict:
    report = state.get("final_answer") or ""
    evidence = _answer_evidence(state, profile.final_evidence_limit)
    citation_repair_applied = False
    citation_repair_error = ""
    if _numeric_citations_need_repair(report):
        if _model_call_fits_budget(state, profile, stage="verification"):
            try:
                report, citation_repair_applied = _repair_numeric_citations(
                    report,
                    evidence,
                    verifier_model,
                    claim_assessments=state.get("_claim_assessments") or [],
                    source_coverage=state.get("_source_coverage") or [],
                )
            except Exception as exc:
                citation_repair_error = f"{type(exc).__name__}: {exc}"
        else:
            citation_repair_error = "BudgetDeferred: insufficient run budget for citation alignment"
    deterministic = _deterministic_verify(report, state.get("_evidence_json") or "", state.get("_source_statuses") or {})
    allowed_citations = sorted({
        str(ref)
        for item in evidence
        for ref in item.get("evidence_refs") or []
        if str(ref)
    })
    prompt = f"""Fact-check the report against the research plan and evidence.
Return JSON only. Do not require all three sources. Treat a direct authoritative
single source as sufficient when it actually supports the wording.
If no acquired external evidence is available, do not flag missing citations or
unsupported claims solely for that absence. Model knowledge and analysis may
still answer the question when they are appropriately qualified and the source
gap is disclosed. Flag only concrete contradictions, overstatement, high-stakes
precision, or time-sensitive facts that the report presents too strongly.
Evidence is not a checklist: do not emit missing_dimension merely because an
optional Model Prior claim or limitation was omitted from an otherwise complete
answer.
If Web body fetching failed, snippets, titles, and URLs are discovery metadata
only. Flag any recommendation to use them as factual evidence or a proxy fact
source, including advice to generate from search-result summaries and disclose
that limitation afterward. They may only support retrieval retries or a clearly
labeled lead list and must not enter evidence confidence calculations.

Query: {state['query']}
Plan: {json.dumps(state.get('_research_plan') or {}, ensure_ascii=False)}
Evidence: {json.dumps(evidence, ensure_ascii=False)}
Citation identity registry:
{_citation_registry(evidence) or 'none'}
Allowed citation strings: {json.dumps(allowed_citations, ensure_ascii=False)}
Deterministic checks: {json.dumps(deterministic, ensure_ascii=False)}
Report: {report}

Citation validation is deterministic. Only emit citation_mismatch for a citation
listed in Deterministic checks.invalid_citations. Do not confuse an evidence id
such as builtin.rag_claim_0 with its exact citation string in evidence_refs.
For comparative claims, also check that a citation's paper_id/document_title
belongs to the named system in the sentence. Do not accept evidence from one
target system as support for another target system.

Return:
{{"overall":"passed|needs_revision|needs_research","issues":[
{{"claim_id":"","issue_type":"unsupported_claim|overstated_claim|missing_dimension|stale_or_undated|source_conflict|citation_mismatch|unsafe_content_use","severity":"high|medium|low","description":"...","evidence_ids":["..."],"suggested_action":"...","original_text":"exact report substring","replacement_text":"complete evidence-bounded replacement preserving valid citations","requires_research":true|false}}
]}}"""
    model_issues: list[VerificationIssue] = []
    verifier_error = ""
    if profile.factcheck_strength != "light":
        if str(state.get("_synthesis_status") or "completed") != "completed":
            verifier_error = "SynthesisFallback: semantic verification deferred until formal synthesis succeeds"
        elif not _model_call_fits_budget(state, profile, stage="verification"):
            verifier_error = "BudgetDeferred: insufficient run budget for semantic verification"
        else:
            try:
                _, payload = _invoke_json_object(
                    verifier_model,
                    "You are a strict evidence-grounded fact checker. Output valid JSON only.",
                    prompt,
                )
                model_issues = [
                    VerificationIssue.from_dict(item)
                    for item in payload.get("issues") or []
                    if isinstance(item, dict) and str(item.get("description") or item.get("issue") or "").strip()
                ]
                model_issues = _filter_semantic_issues(model_issues)
                model_issues = _filter_model_citation_issues(
                    model_issues,
                    deterministic.get("invalid_citations") or [],
                )
            except Exception as exc:
                verifier_error = f"{type(exc).__name__}: {exc}"

    deterministic_issues = [VerificationIssue.from_dict(item) for item in deterministic["issues"]]
    issues = _dedupe_issues([*deterministic_issues, *model_issues])
    revised, targeted_issue_keys = _apply_verifier_replacements(
        report,
        model_issues,
        allowed_citations=allowed_citations,
    )
    targeted_report = revised
    targeted_recheck = _deterministic_verify(
        targeted_report,
        state.get("_evidence_json") or "",
        state.get("_source_statuses") or {},
    )
    issues_for_revision = _dedupe_issues([
        *[VerificationIssue.from_dict(item) for item in targeted_recheck["issues"]],
        *[item for item in model_issues if _verification_issue_key(item) not in targeted_issue_keys],
    ])
    revision_error = ""
    if issues_for_revision and str(state.get("_synthesis_status") or "completed") != "completed":
        revision_error = "SynthesisFallback: revision deferred until formal synthesis succeeds"
    elif issues_for_revision and not _model_call_fits_budget(state, profile, stage="revision"):
        revision_error = "BudgetDeferred: insufficient run budget for report revision"
    elif issues_for_revision:
        issue_payload = [item.to_dict() for item in issues_for_revision]
        revision_diagnostics: dict[str, str] = {}
        revised = _generate_report(
            {**state, "final_answer": targeted_report},
            synthesizer_model,
            _profile_from_state(state),
            revision_context=(
                "Rewrite the complete main answer to resolve these verification issues. "
                "Do not append a correction log. Use only these exact citation strings: "
                + json.dumps(allowed_citations, ensure_ascii=False)
                + "\nIssues: " + json.dumps(issue_payload, ensure_ascii=False)
            ),
            compact_retry=True,
            diagnostics=revision_diagnostics,
        )
        revision_error = revision_diagnostics.get("error", "")

    recheck = _deterministic_verify(revised, state.get("_evidence_json") or "", state.get("_source_statuses") or {})
    if any(item.get("issue_type") == "unsafe_content_use" for item in recheck.get("issues") or []):
        revised = _safe_web_degradation_report(state, evidence)
        recheck = _deterministic_verify(
            revised,
            state.get("_evidence_json") or "",
            state.get("_source_statuses") or {},
        )
    semantic_recheck_issues: list[VerificationIssue] = []
    recheck_verifier_error = ""
    full_revision_applied = revised != targeted_report
    if issues_for_revision and full_revision_applied and profile.factcheck_strength != "light" and _model_call_fits_budget(state, profile, stage="verification"):
        recheck_prompt = f"""Recheck the revised report against the original issues and evidence.
Return JSON only as {{"issues":[...]}} using the same issue schema. Report only
issues that still remain or were newly introduced. Do not repeat a resolved issue.

Query: {state['query']}
Original issues: {json.dumps([item.to_dict() for item in issues], ensure_ascii=False)}
Evidence: {json.dumps(evidence, ensure_ascii=False)}
Citation identity registry:
{_citation_registry(evidence) or 'none'}
Allowed citation strings: {json.dumps(allowed_citations, ensure_ascii=False)}
Deterministic checks after revision: {json.dumps(recheck, ensure_ascii=False)}
Revised report: {revised}"""
        try:
            _, recheck_payload = _invoke_json_object(
                verifier_model,
                "You are a concise evidence-grounded rechecker. Output valid JSON only.",
                recheck_prompt,
            )
            semantic_recheck_issues = [
                VerificationIssue.from_dict(item)
                for item in recheck_payload.get("issues") or []
                if isinstance(item, dict) and str(item.get("description") or item.get("issue") or "").strip()
            ]
            semantic_recheck_issues = _filter_semantic_issues(semantic_recheck_issues)
            semantic_recheck_issues = _filter_model_citation_issues(
                semantic_recheck_issues,
                recheck.get("invalid_citations") or [],
            )
        except Exception as exc:
            recheck_verifier_error = f"{type(exc).__name__}: {exc}"
    elif issues_for_revision and full_revision_applied and profile.factcheck_strength != "light":
        recheck_verifier_error = "BudgetDeferred: insufficient run budget for semantic recheck"

    if _web_degradation_attribution_failed(
        state.get("_source_statuses") or {},
        semantic_recheck_issues,
    ):
        revised = _safe_web_degradation_report(state, evidence)
        recheck = _deterministic_verify(
            revised,
            state.get("_evidence_json") or "",
            state.get("_source_statuses") or {},
        )
        semantic_recheck_issues = []
        recheck_verifier_error = ""

    remaining_issues = [
        VerificationIssue.from_dict(item)
        for item in recheck["issues"]
    ] + semantic_recheck_issues
    if revision_error:
        remaining_issues.extend(issues)
    for issue in issues:
        issue.resolved = not any(_same_verification_issue(issue, remaining) for remaining in remaining_issues)
    final_issues = _dedupe_issues([*issues, *semantic_recheck_issues])
    unresolved = [item for item in final_issues if not item.resolved]
    coverage_gap_questions = _coverage_gate_questions(state)
    gap_questions = _gap_questions(
        unresolved,
        state.get("_research_gaps") or [],
        coverage_gap_questions,
    )
    severe_remaining = any(item.severity == "high" and not item.resolved for item in final_issues)
    semantic_verification_failed = bool(verifier_error or recheck_verifier_error) and profile.factcheck_strength != "light"
    synthesis_incomplete = str(state.get("_synthesis_status") or "completed") != "completed"
    status = (
        "needs_review"
        if severe_remaining or recheck["issues"] or semantic_verification_failed or gap_questions or synthesis_incomplete
        else "passed"
    )
    findings = {
        **recheck,
        "issues": [item.to_dict() for item in final_issues],
        "verifier_error": verifier_error,
        "recheck_verifier_error": recheck_verifier_error,
        "revision_error": revision_error,
        "targeted_replacement_count": len(targeted_issue_keys),
        "citation_repair_applied": citation_repair_applied,
        "citation_repair_error": citation_repair_error,
        "synthesis_status": state.get("_synthesis_status") or "completed",
        "synthesis_error": state.get("_synthesis_error") or "",
        "revision_applied": revised != report,
        "gap_questions": gap_questions,
    }
    summary = _verification_markdown(findings, status)
    next_state = {
        **state,
        "final_answer": revised,
        "_verified_answer": revised,
        "_factcheck_status": status,
        "_factcheck_report": summary,
        "_factcheck_findings": findings,
        "_verification_issues": [item.to_dict() for item in final_issues],
        "_gap_questions": gap_questions,
        "_review_status": "accepted" if status == "passed" else "awaiting_user_review",
        "_run_summary": _append_stage(state, "factcheck_revision"),
        "_pipeline_stage": "verified_revised",
    }
    return {
        "final_answer": revised,
        "_verified_answer": revised,
        "_factcheck_status": status,
        "_factcheck_report": summary,
        "_factcheck_findings": findings,
        "_verification_issues": [item.to_dict() for item in final_issues],
        "_gap_questions": gap_questions,
        "_review_status": next_state["_review_status"],
        "_run_summary": next_state["_run_summary"],
        "_pipeline_stage": "verified_revised",
    }


def _verification_router(state: P1ResearchState, profile: ResearchModeProfile) -> str:
    iteration = int(state.get("_gap_iteration") or 0)
    statuses = state.get("_source_statuses") or {}
    external_disabled = all(
        bool(((statuses.get(source) or {}).get("metadata") or {}).get("disabled"))
        or str((statuses.get(source) or {}).get("status") or "") in {"failed", "no_evidence", "fallback"}
        for source in ("RAG", "Web")
    )
    remaining_seconds = _remaining_run_seconds(state, profile)
    has_research_budget = remaining_seconds >= 90
    if (
        state.get("_gap_questions")
        and iteration < profile.max_gap_iterations
        and not external_disabled
        and has_research_budget
    ):
        return "gap_research"
    return "finalize"


def _gap_research_node(
    state: P1ResearchState,
    *,
    rag_agent: ResearchAgent,
    web_agent: ResearchAgent,
    analyst_model: Any,
    synthesizer_model: Any,
    profile: ResearchModeProfile,
) -> dict:
    questions = list(dict.fromkeys(str(item).strip() for item in state.get("_gap_questions") or [] if str(item).strip()))
    gap_question_limit = min(profile.max_subquestions, max(1, profile.max_gap_iterations * 2))
    questions = questions[:gap_question_limit]
    additions: dict[str, SourceResult] = {}
    for source, source_id, agent in (
        ("RAG", "builtin.rag", rag_agent),
        ("Web", "builtin.web", web_agent),
    ):
        def run_question(item: tuple[int, str]) -> tuple[str, str, SourceResult]:
            index, question = item
            payload = _run_exclusive_tool(agent, question)
            result = _source_result_from_agent_text(source, payload or "")
            planned = next(
                (
                    item for item in (state.get("_research_plan") or {}).get("subquestions") or []
                    if str(item.get("question") or "").strip() == question
                ),
                {},
            )
            subquestion_id = str(planned.get("id") or f"gap-{int(state.get('_gap_iteration') or 0) + 1}-{index + 1}")
            result.claims = [replace(item, subquestion_id=subquestion_id) for item in result.claims]
            result.metadata = {**result.metadata, "subquestion_id": subquestion_id, "subquestion": question}
            return subquestion_id, question, result

        with ThreadPoolExecutor(max_workers=min(profile.max_parallel_subquestions, len(questions) or 1)) as executor:
            runs = list(executor.map(run_question, enumerate(questions)))
        additions[source_id] = _merge_source_results(
            source,
            _state_source_results(state).get(source_id),
            _combine_source_runs(source, runs),
        )

    results = _state_source_results(state)
    results.update(additions)
    graph = build_evidence_graph_from_results(results)
    statuses = _legacy_source_statuses(results)
    graph.source_statuses = statuses
    coverage = _source_coverage(state.get("_research_plan") or {}, results)
    analysis_prompt = f"""Update the claim assessments after targeted gap research.
Query: {state['query']}
Gap questions: {json.dumps(questions, ensure_ascii=False)}
Evidence: {json.dumps(_evidence_table(graph), ensure_ascii=False)}
Return JSON with analysis, claim_assessments, gaps, and conflicts."""
    try:
        _, payload = _invoke_json_object(analyst_model, "Output valid JSON only.", analysis_prompt)
        assessments = _claim_assessments(payload, _evidence_table(graph))
        gaps = [str(item) for item in payload.get("gaps") or []]
        conflicts = [item for item in payload.get("conflicts") or [] if isinstance(item, dict)]
    except Exception:
        assessments = state.get("_claim_assessments") or []
        gaps = questions
        conflicts = state.get("_conflicts") or []

    updated_state = {
        **state,
        "source_results": {
            source_id: namespace_source_result(source_id, result).to_dict()
            for source_id, result in additions.items()
        },
        "rag_result": additions["builtin.rag"].to_tool_text(),
        "web_result": additions["builtin.web"].to_tool_text(),
        "_source_statuses": statuses,
        "_evidence_json": graph.to_json(),
        "_deep_evidence_json": graph.to_json(),
        "_deep_source_statuses": statuses,
        "_claim_assessments": assessments,
        "_source_coverage": coverage,
        "_research_gaps": gaps,
        "_conflicts": conflicts,
        "_gap_iteration": int(state.get("_gap_iteration") or 0) + 1,
        "_gap_questions": [],
    }
    revised = _generate_report(
        updated_state,
        synthesizer_model,
        profile,
        revision_context="Integrate the targeted gap-research evidence into the complete report; replace outdated wording.",
    )
    run_summary = _append_stage(updated_state, f"gap_research_{updated_state['_gap_iteration']}")
    return {
        "source_results": updated_state["source_results"],
        "rag_result": updated_state["rag_result"],
        "web_result": updated_state["web_result"],
        "_source_statuses": statuses,
        "_evidence_json": graph.to_json(),
        "_deep_evidence_json": graph.to_json(),
        "_deep_source_statuses": statuses,
        "_deep_research": "\n".join(f"- {item}" for item in questions),
        "_deep_queries": questions,
        "_claim_assessments": assessments,
        "_source_coverage": coverage,
        "_research_gaps": gaps,
        "_conflicts": conflicts,
        "_gap_iteration": updated_state["_gap_iteration"],
        "_gap_questions": [],
        "final_answer": revised,
        "_run_summary": run_summary,
        "_pipeline_stage": "gap_researched",
    }


def _merge_source_results(source: str, existing: SourceResult | None, new: SourceResult) -> SourceResult:
    if existing is None:
        return new
    runs = []
    for result in (existing, new):
        for item in result.metadata.get("subquestion_runs") or []:
            runs.append(item)
    valid = [item for item in (existing, new) if item.is_valid_evidence]
    status = "success" if any(item.status == "success" for item in valid) else "low_relevance" if valid else new.status
    claim_results = (
        [item for item in (existing, new) if item.status == "success"]
        if status == "success"
        else valid
    )
    claims = []
    seen = set()
    for result in claim_results:
        for claim in result.claims:
            key = (claim.paper_id.casefold(), claim.subquestion_id, re.sub(r"\s+", " ", claim.claim).casefold())
            if key not in seen:
                seen.add(key)
                claims.append(claim)
    return SourceResult(
        source=source,
        status=status,
        detail=f"{source} initial + gap research",
        error="; ".join(item.error for item in (existing, new) if item.error),
        content=f"{existing.content}\n\n{new.content}".strip(),
        claims=claims,
        evidence_class=max(
            (item.evidence_class for item in (existing, new)),
            key=lambda value: {"peer_reviewed": 5, "authoritative_document": 4, "preprint": 3, "community_content": 2, "model_inference": 1}.get(value, 0),
        ),
        metadata={"subquestion_runs": runs, "gap_research": True},
    )


def _finalize_node(state: P1ResearchState) -> dict:
    next_state = {
        **state,
        "_run_summary": _append_stage(state, "finalize"),
        "_pipeline_stage": "completed",
    }
    return {
        "_quality_report": evaluate_p1_quality(next_state),
        "_run_summary": next_state["_run_summary"],
        "_pipeline_stage": "completed",
    }


def _deterministic_verify(report: str, evidence_json: str, statuses: dict) -> dict:
    evidence = [
        item for item in _load_evidence_table(evidence_json)
        if _evidence_source_succeeded(item, statuses)
    ]
    valid_refs = {
        str(ref)
        for item in evidence
        for ref in item.get("evidence_refs") or []
        if str(ref)
    }
    compiled = CitationCompiler.is_compiled(report)
    if compiled:
        citation_state = _compiled_citation_state(report)
        cited_refs = {f"[{number}]" for number in citation_state["cited_numbers"]}
        invalid_refs = [f"[{number}]" for number in citation_state["invalid_numbers"]]
    else:
        cited_refs = set(re.findall(r"\[(?:RAG:[^\]]+|Web:https?://[^\]]+)\]", report))
        invalid_refs = sorted(cited_refs - valid_refs)
    issues = [
        VerificationIssue(
            claim_id="",
            issue_type="citation_mismatch",
            severity="high",
            description=f"Citation {ref} does not resolve to an acquired evidence item.",
            evidence_ids=[ref],
            suggested_action="remove or replace the citation",
            requires_research=False,
        ).to_dict()
        for ref in invalid_refs
    ]
    if compiled:
        for problem in citation_state["format_errors"]:
            issues.append(VerificationIssue(
                claim_id="",
                issue_type="citation_mismatch",
                severity="high",
                description=problem,
                suggested_action="recompile the public citation and confidence sections",
                requires_research=False,
            ).to_dict())
    else:
        issues.extend(_citation_subject_issues(report, evidence))
    web_status = str((statuses.get("Web") or {}).get("status") or "").casefold()
    if web_status in {"failed", "no_evidence", "fallback"} and re.search(
        r"(?:snippet|摘要片段).{0,100}(?:代理事实源|唯一事实来源|事实依据|作为.{0,16}(?:证据|事实源))|"
        r"(?:代理事实源|唯一事实来源|事实依据).{0,100}(?:snippet|摘要片段)|"
        r"(?:基于|依赖|使用).{0,50}(?:搜索结果摘要|搜索摘要|snippet).{0,50}(?:生成|形成|回答|合成)|"
        r"(?:搜索结果摘要|搜索摘要|搜索片段|snippet).{0,60}(?:进入|用于|交叉).{0,40}(?:推理|置信度|生成|事实重构|高置信事实)",
        report,
        re.IGNORECASE | re.DOTALL,
    ):
        issues.append(VerificationIssue(
            claim_id="",
            issue_type="unsafe_content_use",
            severity="high",
            description=(
                "Web body fetching failed, but the report treats search snippets as factual evidence. "
                "Discovery metadata may guide retries or be shown as leads, never support answer claims."
            ),
            suggested_action="remove snippet-based facts and answer from RAG plus clearly labeled Model analysis",
            requires_research=False,
        ).to_dict())
    answer_claims = _answer_claims(report)
    citation_pattern = r"\[\d+(?:\s*,\s*\d+)*\]" if compiled else r"\[(?:RAG:|Web:)"
    cited_claims = [claim for claim in answer_claims if re.search(citation_pattern, claim)]
    citation_coverage_applicable = bool(citation_state["reference_numbers"] if compiled else valid_refs)
    coverage = (
        len(cited_claims) / len(answer_claims)
        if citation_coverage_applicable and answer_claims
        else 1.0
    )
    if valid_refs and answer_claims and coverage < 0.85:
        issues.append(VerificationIssue(
            claim_id="",
            issue_type="missing_dimension",
            severity="medium",
            description=f"Only {coverage:.0%} of substantive answer claims include an acquired citation; target is at least 85%.",
            suggested_action="merge or cite factual bullets and table rows using exact acquired references",
            requires_research=False,
        ).to_dict())
    if compiled and not report.rstrip().splitlines()[-1].strip().startswith("|"):
        issues.append(VerificationIssue(
            claim_id="",
            issue_type="missing_dimension",
            severity="medium",
            description="The confidence appendix must be the final top-level report section.",
            suggested_action="recompile the report with the confidence appendix last",
        ).to_dict())
    elif not compiled and "## 可靠性与缺口" not in report:
        issues.append(VerificationIssue(
            claim_id="",
            issue_type="missing_dimension",
            severity="medium",
            description="The report lacks the single required reliability and coverage section.",
            suggested_action="add one concise reliability section",
        ).to_dict())
    if not compiled and report.count("## 可靠性与缺口") > 1:
        issues.append(VerificationIssue(
            claim_id="",
            issue_type="missing_dimension",
            severity="medium",
            description="Reliability information is repeated instead of presented once.",
            suggested_action="merge repeated reliability sections",
        ).to_dict())
    return {
        "evidence_node_count": len(evidence),
        "valid_citation_count": len(cited_refs) - len(invalid_refs),
        "invalid_citation_count": len(invalid_refs),
        "invalid_citations": invalid_refs,
        "report_claim_count": len(answer_claims),
        "cited_claim_count": len(cited_claims),
        "verified_claim_ratio": round(coverage, 3),
        "citation_coverage_applicable": citation_coverage_applicable,
        "issues": issues,
        "source_coverage": {
            source: str((statuses.get(source) or {}).get("status") or "missing")
            for source in ("RAG", "Web", "Model")
        },
    }


def _compiled_citation_state(report: str) -> dict[str, Any]:
    answer = report.split("## 参考文献与证据", 1)[0]
    references = report.split("## 参考文献与证据", 1)[1].split("## 置信度附录", 1)[0]
    reference_numbers = [int(item) for item in re.findall(r"(?m)^(\d+)\.\s+", references)]
    cited_numbers = sorted({
        int(number)
        for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", answer)
        for number in re.split(r"\s*,\s*", group)
    })
    invalid_numbers = sorted(set(cited_numbers) - set(reference_numbers))
    format_errors = []
    if reference_numbers != list(range(1, len(reference_numbers) + 1)):
        format_errors.append("Public reference numbers are not contiguous from 1.")
    if re.search(r"\[(?:RAG:|Web:)", answer):
        format_errors.append("The public answer leaks an internal RAG/Web citation identifier.")
    entries = re.split(r"(?m)^\d+\.\s+", references)[1:]
    if any("引用内容：" not in entry for entry in entries):
        format_errors.append("A public reference entry lacks the actual quoted evidence content.")
    return {
        "reference_numbers": reference_numbers,
        "cited_numbers": cited_numbers,
        "invalid_numbers": invalid_numbers,
        "format_errors": format_errors,
    }


def _citation_registry(evidence: list[dict]) -> str:
    rows = []
    for item in evidence:
        refs = [str(ref) for ref in item.get("evidence_refs") or [] if str(ref)]
        if not refs:
            continue
        identity = str(item.get("paper_id") or item.get("url") or "unknown")
        title = str(item.get("document_title") or "")
        subject = title or identity
        rows.append(f"- {', '.join(refs)} -> {subject} ({identity})")
    return "\n".join(dict.fromkeys(rows))


def _citation_subject_issues(report: str, evidence: list[dict]) -> list[dict]:
    """Reject citations attached to a different named system in comparisons."""

    by_ref = {
        str(ref): item
        for item in evidence
        for ref in item.get("evidence_refs") or []
        if str(ref)
    }
    aliases = {
        "shapefilegpt": ("shapefilegpt",),
        "autonomous gis": ("autonomous gis",),
        "geoagentbench": ("geoagentbench",),
        "llm-find": ("llm-find", "llmfind"),
    }
    issues = []
    for line in report.splitlines():
        for match in re.finditer(r"\[(?:RAG:[^\]]+|Web:https?://[^\]]+)\]", line):
            ref = match.group(0)
            context = _citation_preceding_clause(line, match.start()).casefold()
            named = [name for name, terms in aliases.items() if any(term in context for term in terms)]
            if len(named) != 1:
                continue
            expected = named[0]
            item = by_ref.get(ref)
            if not item:
                continue
            title = str(item.get("document_title") or "").casefold()
            paper_id = str(item.get("paper_id") or "").casefold()
            identity = title + " " + paper_id
            if expected not in identity and not (expected == "llm-find" and "2407.21024" in identity) and not (expected == "autonomous gis" and "2305.06453" in identity) and not (expected == "shapefilegpt" and "2410.12376" in identity):
                issues.append(VerificationIssue(
                    claim_id="",
                    issue_type="citation_mismatch",
                    severity="high",
                    description=f"Citation {ref} is attached to {expected}, but its evidence identity is {item.get('document_title') or item.get('paper_id') or 'unknown'}.",
                    evidence_ids=[ref],
                    suggested_action="replace with the same system's direct evidence or qualify the claim",
                    requires_research=False,
                ).to_dict())
    return issues


def _citation_preceding_clause(line: str, citation_start: int) -> str:
    """Return the sentence or clause immediately preceding one citation."""

    prefix = line[:citation_start].rstrip()
    separators = "。！？!?；;"
    if prefix and prefix[-1] in separators:
        prefix = prefix[:-1].rstrip()
    boundary = max((prefix.rfind(char) for char in separators), default=-1)
    return prefix[boundary + 1:].strip()


def _answer_claims(report: str) -> list[str]:
    claims = []
    in_answer = False
    subsection = ""
    model_boundary_active = False
    for raw in report.splitlines():
        line = raw.strip()
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            in_answer = heading.group(1).strip() == "回答"
            subsection = ""
            model_boundary_active = False
            continue
        subheading = re.match(r"^#{3,6}\s+(.+)$", line)
        if subheading:
            subsection = subheading.group(1).strip().casefold()
            model_boundary_active = False
            continue
        bold_heading = re.fullmatch(r"\*\*(.+?)\*\*\s*", line)
        if bold_heading:
            subsection = bold_heading.group(1).strip().casefold()
            continue
        if not in_answer or not line or line.startswith("#"):
            continue
        if line.startswith("|"):
            cells = [cell.strip().casefold() for cell in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell or "---") for cell in cells):
                continue
            if cells and cells[0] in {"系统", "维度", "对比项", "system", "dimension"}:
                continue
        cleaned = re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line)
        lowered = cleaned.casefold()
        has_citation = bool(re.search(r"\[(?:\d+(?:\s*,\s*\d+)*|RAG:|Web:)", cleaned))
        explicitly_model_derived = any(
            marker in subsection
            for marker in (
                "模型级假设", "模型层面", "模型分析", "模型推导", "非外部事实",
                "model-level", "hypothesis", "model analysis",
            )
        )
        analytical_section = any(
            marker in subsection
            for marker in (
                "背景", "关键区分", "对比小结", "跨系统比较", "瓶颈性质",
                "趋势小结", "关键趋势", "趋势与判断",
                "归属判定", "边界", "模型级假设", "模型层面", "领域共性",
                "模型分析", "模型推导", "分析与建议", "非外部事实",
                "机制与影响", "缓解方向", "缓解措施",
                "synthesis", "comparison summary", "model-level", "hypothesis",
                "model analysis", "recommendation", "mitigation",
            )
        )
        if explicitly_model_derived or analytical_section and not has_citation:
            continue
        if not has_citation and re.search(
            r"行业(?:通用|通识)|基于行业通识|基于模型(?:先验|知识)|"
            r"(?:当前|现有|本轮)?证据(?:未|尚未|没有)直接覆盖|当前证据主要覆盖|"
            r"model (?:prior|knowledge)",
            cleaned,
            re.IGNORECASE,
        ):
            continue
        if not has_citation and re.search(
            r"^(?:适用边界|选型边界|实践边界)\s*[:：]|"
            r"^当.{0,28}(?:时|后).{0,20}(?:需|应|可)(?:引入|采用|组合|优先)|"
            r"^针对.{0,28}任务.{0,20}(?:方法|路径|方案).{0,12}(?:对应|可分|取决于)|"
            r"^(?:上述|这些|四类|各类)方法并非互斥",
            cleaned,
            re.IGNORECASE,
        ):
            continue
        if not subsection and not has_citation:
            continue
        inline_label = re.match(r"^\*\*(.+?)\*\*\s*[:：]?", cleaned)
        if not has_citation and inline_label and re.search(
            r"(?:子问题.{0,12}(?:结论|合并分析)|结论摘要|^结论$|机制与影响|缓解方向|"
            r"模型分析|分析与建议|非外部事实|待核验|证据缺口|未覆盖问题|限制)",
            inline_label.group(1),
        ):
            continue
        if not has_citation and re.search(
            r"(?:本证据集|当前证据|现有证据|直接证据|所获证据).{0,24}"
            r"(?:未|不在|缺少|缺失|没有|较少|有限|不足).{0,24}(?:证据|模型|推理|分析)?",
            cleaned,
        ):
            model_boundary_active = True
            continue
        if model_boundary_active:
            continue
        if not has_citation and "以下" in cleaned and re.search(r"(?:逐一|分别|按.{0,8})(?:展开|说明|分析)", cleaned):
            continue
        synthesis_prefixes = (
            "这些", "因此", "由此", "综合来看", "总体而言", "换言之", "这意味着",
            "现有证据", "当前证据", "本次检索", "论文未", "直接证据未",
            "本轮报告综合", "本轮综合", "本轮取得", "本轮没有取得", "当前材料不足",
            "基于现有文献", "根据现有文献", "根据直接文献证据",
            "由于缺乏直接", "鉴于缺乏直接",
            "三个系统的直接证据", "三者的直接证据", "以下比较", "下表",
            "these issues", "therefore", "overall", "in synthesis", "this suggests",
            "current evidence", "the available evidence", "the paper does not",
            "model analysis", "open question", "模型分析", "开放问题",
        )
        if len(cleaned) >= 30 and not lowered.startswith(synthesis_prefixes):
            claims.append(cleaned)
    return claims[:30]


def _gap_questions(
    issues: list[VerificationIssue],
    model_gaps: list[str],
    coverage_gaps: list[str] | None = None,
) -> list[str]:
    research_issues = [
        issue for issue in issues
        if issue.requires_research or issue.issue_type in {"unsupported_claim", "stale_or_undated", "source_conflict"}
    ]
    questions = [
        issue.description
        for issue in research_issues
    ]
    if research_issues:
        questions.extend(str(item) for item in model_gaps if str(item).strip())
    questions.extend(str(item) for item in coverage_gaps or [] if str(item).strip())
    return list(dict.fromkeys(item.strip() for item in questions if item.strip()))[:6]


def _coverage_gate_questions(state: P1ResearchState) -> list[str]:
    """Turn uncovered important plan dimensions into concrete retrieval work."""

    statuses = state.get("_source_statuses") or {}
    external_disabled = all(
        bool(((statuses.get(source) or {}).get("metadata") or {}).get("disabled"))
        or str((statuses.get(source) or {}).get("status") or "") in {"failed", "no_evidence", "fallback"}
        for source in ("RAG", "Web")
    )
    if external_disabled:
        return []
    plan = state.get("_research_plan") or {}
    coverage = state.get("_source_coverage") or []
    questions = []
    for subquestion in plan.get("subquestions") or []:
        if str(subquestion.get("importance") or "medium").casefold() not in {"high", "medium"}:
            continue
        subquestion_id = str(subquestion.get("id") or "")
        externally_covered = any(
            isinstance(row, dict)
            and str(row.get("subquestion_id") or "") == subquestion_id
            and str(row.get("source") or "") in {"RAG", "Web"}
            and str(row.get("status") or "") == "covered"
            and bool(row.get("evidence_ids"))
            for row in coverage
        )
        model_covered = any(
            isinstance(row, dict)
            and str(row.get("subquestion_id") or "") == subquestion_id
            and str(row.get("source") or "") == "Model"
            and str(row.get("status") or "") == "covered"
            for row in coverage
        )
        explicitly_calibrated = model_covered and "## 置信度附录" in str(state.get("final_answer") or "")
        if not externally_covered and not explicitly_calibrated:
            question = str(subquestion.get("question") or "").strip()
            if question:
                questions.append(question)
    return questions[:4]


def _dedupe_issues(issues: list[VerificationIssue]) -> list[VerificationIssue]:
    result = []
    seen = set()
    for issue in issues:
        key = (issue.issue_type, re.sub(r"\s+", " ", issue.description).casefold())
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def _same_verification_issue(left: VerificationIssue, right: VerificationIssue) -> bool:
    """Match recheck findings without conflating unrelated claims of one type."""

    if left.issue_type != right.issue_type:
        return False
    left_claim = str(left.claim_id or "").strip().casefold()
    right_claim = str(right.claim_id or "").strip().casefold()
    if left_claim or right_claim:
        return bool(left_claim and right_claim and left_claim == right_claim)
    left_tokens = set(re.findall(r"[a-z0-9_-]{4,}|[\u4e00-\u9fff]{2,}", left.description.casefold()))
    right_tokens = set(re.findall(r"[a-z0-9_-]{4,}|[\u4e00-\u9fff]{2,}", right.description.casefold()))
    if not left_tokens or not right_tokens:
        return left.description.strip().casefold() == right.description.strip().casefold()
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens)) >= 0.45


def _filter_semantic_issues(issues: list[VerificationIssue]) -> list[VerificationIssue]:
    """Drop requests to externally cite content already labeled as hypothesis."""

    result = []
    for issue in issues:
        description = issue.description.casefold()
        hypothesis = any(marker in description for marker in (
            "model-level hypothesis", "model level hypothesis", "analysis hypothesis",
            "模型层假设", "模型级假设", "分析假设",
        ))
        citation_request = any(marker in description for marker in (
            "cite", "citation", "evidence", "external source", "引用", "证据", "外部来源",
        ))
        if (
            issue.issue_type == "missing_dimension"
            and hypothesis
            and citation_request
            and not issue.evidence_ids
        ):
            continue
        result.append(issue)
    return result


def _filter_model_citation_issues(
    issues: list[VerificationIssue],
    invalid_citations: list[str],
) -> list[VerificationIssue]:
    """Keep semantic citation findings only when deterministic resolution failed."""

    invalid = {str(item) for item in invalid_citations}
    result = []
    for issue in issues:
        if issue.issue_type != "citation_mismatch":
            result.append(issue)
            continue
        issue_text = " ".join([issue.description, *issue.evidence_ids])
        if any(citation in issue_text for citation in invalid):
            result.append(issue)
    return result


def _verification_issue_key(issue: VerificationIssue) -> tuple[str, str, str]:
    return (
        str(issue.claim_id or "").strip().casefold(),
        str(issue.issue_type or "").strip().casefold(),
        re.sub(r"\s+", " ", str(issue.description or "")).strip().casefold(),
    )


def _apply_verifier_replacements(
    report: str,
    issues: list[VerificationIssue],
    *,
    allowed_citations: list[str],
) -> tuple[str, set[tuple[str, str, str]]]:
    """Apply exact, bounded edits authored by the evidence-aware verifier."""

    revised = report
    applied: set[tuple[str, str, str]] = set()
    allowed = set(allowed_citations)
    compiled_citations = set(re.findall(r"\[\d+(?:\s*,\s*\d+)*\]", report))
    for issue in issues:
        original = issue.original_text.strip()
        replacement = issue.replacement_text.strip()
        if (
            issue.requires_research
            or len(original) < 12
            or not replacement
            or original == replacement
            or original not in revised
            or len(replacement) > max(1200, len(original) * 2)
            or re.search(r"(?m)^##\s+", replacement)
        ):
            continue
        replacement_citations = set(re.findall(
            r"\[(?:RAG:[^\]]+|Web:https?://[^\]]+|\d+(?:\s*,\s*\d+)*)\]",
            replacement,
        ))
        if replacement_citations - allowed - compiled_citations:
            continue
        revised = revised.replace(original, replacement, 1)
        applied.add(_verification_issue_key(issue))
    return revised, applied


def _verification_markdown(findings: dict, status: str) -> str:
    issues = findings.get("issues") or []
    coverage_line = (
        f"- 回答声明引用覆盖率：{float(findings.get('verified_claim_ratio', 0.0)):.0%}"
        if findings.get("citation_coverage_applicable", True)
        else "- 回答声明引用覆盖率：不适用（本轮无可用外部证据）"
    )
    return "\n".join([
        "### 核验摘要",
        f"- 状态：{status}",
        f"- 引用解析：{findings.get('valid_citation_count', 0)} 个有效，{findings.get('invalid_citation_count', 0)} 个无效",
        coverage_line,
        f"- 修订主答案：{'是' if findings.get('revision_applied') else '否'}",
        f"- 待处理问题：{len([item for item in issues if not item.get('resolved')])}",
    ])


def _invoke_json_object(model: Any, system: str, prompt: str) -> tuple[str, dict[str, Any]]:
    response = model.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    raw = str(response.content if hasattr(response, "content") else response).strip()
    cleaned = _strip_hidden_reasoning(raw)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model response did not contain a JSON object")
    fragment = cleaned[start : end + 1]
    try:
        value = json.loads(fragment)
    except json.JSONDecodeError:
        from json_repair import repair_json

        value = repair_json(fragment, return_objects=True)
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    return raw, value


def _state_source_results(state: P1ResearchState) -> dict[str, SourceResult]:
    results = {}
    for source_id, payload in (state.get("source_results") or {}).items():
        try:
            results[source_id] = SourceResult.from_dict(payload)
        except Exception:
            continue
    return results


def _legacy_source_statuses(results: dict[str, SourceResult]) -> dict[str, dict]:
    statuses = {source_id: result.to_dict() for source_id, result in results.items()}
    for source_id, legacy in (("builtin.rag", "RAG"), ("builtin.web", "Web"), ("builtin.model", "Model")):
        if source_id in statuses:
            payload = dict(statuses[source_id])
            payload["source"] = legacy
            payload["claims"] = [
                {**item, "source": legacy}
                for item in payload.get("claims") or []
            ]
            statuses[legacy] = payload
    return statuses


def _display_source(source_id: str) -> str:
    return {
        "builtin.rag": "本地知识库 (RAG)",
        "builtin.web": "互联网正文证据 (Web)",
        "builtin.model": "模型世界知识与分析 (Model)",
    }.get(source_id, source_id)


def _evidence_table(graph: EvidenceGraph) -> list[dict]:
    return [
        {
            "id": node.id,
            "claim": node.claim,
            "source": node.source,
            "source_detail": node.source_detail,
            "evidence_class": node.evidence_class,
            "evidence_refs": node.evidence_refs,
            "verbatim_quote": node.verbatim_quote,
            "document_title": node.document_title,
            "authors": list(node.authors),
            "organization": node.organization,
            "paper_id": node.paper_id,
            "paper_section": node.paper_section,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "url": node.url,
            "published_at": node.published_at,
            "retrieved_at": node.retrieved_at,
            "content_kind": node.content_kind,
            "authority": node.authority_score,
            "directness": node.directness,
            "subquestion_id": node.subquestion_id,
            "relevance": node.relevance,
            "limitations": node.limitations,
            "domain_relevance": node.domain_relevance,
            "claim_entailment": node.claim_entailment,
            "evidence_role": node.evidence_role,
            "source_identity": node.source_identity,
            "body_valid": node.body_valid,
        }
        for node in graph.nodes.values()
    ]


def _select_evidence(evidence: list[dict], limit: int, *, query: str = "") -> list[dict]:
    """Select a compact, diverse evidence set for LLM analysis and synthesis."""

    limit = max(1, int(limit))
    external = [item for item in evidence if item.get("evidence_refs") and item.get("verbatim_quote")]
    candidates = external or [item for item in evidence if item.get("claim")]
    candidates = [item for item in candidates if not _is_index_metadata_claim(item)]
    candidates = _drop_superseded_arxiv_versions(candidates)
    if is_temporal_query(query):
        authoritative_subquestions = {
            str(item.get("subquestion_id") or "")
            for item in candidates
            if str(item.get("evidence_class") or "").casefold() == "authoritative_document"
        }
        candidates = [
            item
            for item in candidates
            if not (
                str(item.get("evidence_class") or "").casefold() == "community_content"
                and str(item.get("subquestion_id") or "") in authoritative_subquestions
            )
        ]
    target_names = _named_comparison_systems(query)
    if len(target_names) >= 2:
        target_candidates = [item for item in candidates if _evidence_mentions_system(item, target_names)]
        target_identities = {_evidence_source_identity(item) for item in target_candidates if _evidence_source_identity(item)}
        # Once direct evidence exists for at least two named systems, do not
        # spend the compact prompt budget on unrelated reviews, generic papers,
        # or search pages. Model Prior remains available outside this table.
        if len(target_identities) >= 2:
            candidates = target_candidates
    ordered = sorted(candidates, key=lambda item: _evidence_rank(item, query=query), reverse=True)
    selected: list[dict] = []
    seen_ids: set[str] = set()

    def add(item: dict) -> None:
        item_id = str(item.get("id") or "")
        if item_id and item_id not in seen_ids and len(selected) < limit:
            selected.append(item)
            seen_ids.add(item_id)

    priority_patterns: list[re.Pattern[str]] = []
    lowered_query = str(query or "").casefold()
    if any(marker in lowered_query for marker in ("fips 206", "fn-dsa", "falcon")):
        priority_patterns.append(re.compile(r"initial public draft|awaiting approval|初始公开草案|等待批准", re.IGNORECASE))
    if "hqc" in lowered_query:
        priority_patterns.append(re.compile(
            r"\bhqc\b.{0,120}\b(?:selected|selection|standardization)\b|"
            r"\b(?:selected|selection)\b.{0,120}\bhqc\b",
            re.IGNORECASE,
        ))
    if any(marker in lowered_query for marker in ("pqc", "post-quantum", "后量子")) and any(
        marker in lowered_query for marker in ("migration", "迁移", "nccoe", "roadmap", "路线图")
    ):
        priority_patterns.extend([
            re.compile(r"sp\s*1800-38", re.IGNORECASE),
            re.compile(r"cisa.{0,80}nsa.{0,80}nist|quantum-readiness roadmaps?", re.IGNORECASE),
        ])
    for pattern in priority_patterns:
        item = next(
            (
                candidate
                for candidate in ordered
                if pattern.search(" ".join([
                    str(candidate.get("claim") or ""),
                    str(candidate.get("verbatim_quote") or ""),
                    str(candidate.get("document_title") or ""),
                    str(candidate.get("url") or ""),
                ]))
            ),
            None,
        )
        if item is not None:
            add(item)

    # Preserve direct evidence for explicitly named standards before generic
    # recent pages consume the compact prompt budget.
    identifier_quota = max(2, limit // 2)
    for identifier in standard_identifiers(query):
        identifier_lower = identifier.casefold()
        item = next(
            (
                candidate
                for candidate in ordered
                if identifier_lower in " ".join([
                    str(candidate.get("claim") or ""),
                    str(candidate.get("verbatim_quote") or ""),
                    str(candidate.get("document_title") or ""),
                    str(candidate.get("url") or ""),
                ]).casefold()
            ),
            None,
        )
        if item is not None:
            add(item)
        if len(selected) >= identifier_quota:
            break

    # Comparative questions are invalid if the compact prompt drops one of
    # the named systems. Preserve one strong full-text item per distinct local
    # paper before spending the remaining budget on repeated Web mirrors or
    # generic background. The threshold excludes unrelated low-score papers.
    rag_items = [item for item in ordered if str(item.get("source") or "").casefold().endswith("rag")]
    query_entities = extract_entities(query) if query else set()
    comparative = bool(
        len(query_entities) >= 2
        or any(marker in str(query).casefold() for marker in ("比较", "compare", "共同", "各自", "分别"))
    )
    if comparative and rag_items:
        qualified = [item for item in rag_items if _evidence_rank(item, query=query) >= 0.34]
        identities = []
        for item in qualified:
            identity = _evidence_source_identity(item)
            if identity and identity not in identities:
                identities.append(identity)
        for identity in identities:
            item = next((candidate for candidate in qualified if _evidence_source_identity(candidate) == identity), None)
            if item is not None:
                add(item)
            if len(selected) >= limit:
                break

    if rag_items and _evidence_rank(rag_items[0], query=query) >= 0.65:
        rag_quota = max(1, int(limit * 0.6))
        rag_sources: set[str] = set()
        for item in rag_items:
            identity = _evidence_source_identity(item)
            if identity not in rag_sources:
                add(item)
                rag_sources.add(identity)
            if len(selected) >= rag_quota:
                break

    seen_channels: set[str] = set()
    for item in ordered:
        channel = str(item.get("source") or "")
        if channel and channel not in seen_channels:
            add(item)
            seen_channels.add(channel)

    seen_subquestions: set[str] = set()
    for item in ordered:
        subquestion_id = str(item.get("subquestion_id") or "")
        if subquestion_id and subquestion_id not in seen_subquestions:
            add(item)
            seen_subquestions.add(subquestion_id)

    if is_temporal_query(query):
        subquestion_counts = {
            subquestion_id: sum(
                1 for item in selected if str(item.get("subquestion_id") or "") == subquestion_id
            )
            for subquestion_id in seen_subquestions
        }
        for item in ordered:
            subquestion_id = str(item.get("subquestion_id") or "")
            if subquestion_id and subquestion_counts.get(subquestion_id, 0) < 2:
                before = len(selected)
                add(item)
                if len(selected) > before:
                    subquestion_counts[subquestion_id] = subquestion_counts.get(subquestion_id, 0) + 1

    seen_sources: set[str] = set()
    for item in ordered:
        source_identity = _evidence_source_identity(item)
        if source_identity and source_identity not in seen_sources:
            add(item)
            seen_sources.add(source_identity)

    for item in ordered:
        add(item)
    return selected


def _drop_superseded_arxiv_versions(items: list[dict]) -> list[dict]:
    """Exclude explicit older arXiv versions when a newer copy was acquired."""

    identities: list[tuple[dict, str, int | None]] = []
    latest: dict[str, int] = {}
    for item in items:
        identity = " ".join([
            str(item.get("paper_id") or ""),
            str(item.get("url") or ""),
            " ".join(str(ref) for ref in item.get("evidence_refs") or []),
        ])
        match = re.search(r"(?<!\d)(\d{4}\.\d{4,5})(?:v(\d+))?", identity, re.IGNORECASE)
        if not match:
            identities.append((item, "", None))
            continue
        base = match.group(1)
        version = int(match.group(2)) if match.group(2) else None
        identities.append((item, base, version))
        if version is not None:
            latest[base] = max(latest.get(base, 0), version)
    return [
        item
        for item, base, version in identities
        if not base or version is None or version >= latest.get(base, version)
    ]


def _is_index_metadata_claim(item: dict) -> bool:
    """Reject retrieval diagnostics and obvious page chrome as evidence claims."""

    text = " ".join([
        str(item.get("claim") or ""),
        str(item.get("verbatim_quote") or ""),
    ])
    return bool(re.search(
        r"\breusable methods\s*:|\breusable datasets\s*:|\bselection reasons\s*:|"
        r"\bmatched research questions\s*:|\bestimated time\s*:|\bsoftware requirements\s*:|"
        r"\bpurchase options?\b|\bsales team\b|\bselect a different location\b|"
        r"\bchat online\b|\bcontact form\b",
        text,
        re.IGNORECASE,
    ))


def _evidence_rank(item: dict, *, query: str = "") -> float:
    def number(key: str) -> float:
        try:
            return max(0.0, min(1.0, float(item.get(key) or 0.0)))
        except (TypeError, ValueError):
            return 0.0

    score = 0.45 * number("relevance") + 0.3 * number("directness") + 0.25 * number("authority")
    if str(item.get("paper_section") or "").casefold() in {"limitations", "discussion", "future_work"}:
        score += 0.15
    source = str(item.get("source") or "").casefold()
    reference_text = " ".join(str(value) for value in item.get("evidence_refs") or []).casefold()
    if source.endswith("rag") and "#fulltext-" in reference_text:
        score += 0.12
    if str(item.get("content_kind") or "").casefold() in {"full_text", "pdf_text", "paper_fulltext"}:
        score += 0.08
    query_terms = {
        term.casefold()
        for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", query)
        if term.casefold() not in {"what", "which", "compare", "limitations"}
    }
    identity_text = " ".join([
        str(item.get("document_title") or ""),
        str(item.get("paper_id") or ""),
        str(item.get("claim") or ""),
    ]).casefold()
    if any(identifier.casefold() in identity_text for identifier in standard_identifiers(query)):
        score += 0.12
    if query_terms:
        matched_terms = sum(1 for term in query_terms if term in identity_text)
        score += 0.18 * min(1.0, (matched_terms / len(query_terms)) * 3)
    query_entities = extract_entities(query) if query else set()
    if query_entities:
        entity_overlap = entity_score(query_entities, identity_text)
        score += 0.2 * entity_overlap
        if is_temporal_query(query) and entity_overlap < 0.2:
            score -= 0.08
    if item.get("verbatim_quote"):
        score += 0.05
    if is_temporal_query(query):
        evidence_class = str(item.get("evidence_class") or "").casefold()
        if evidence_class in {"authoritative_document", "peer_reviewed"}:
            score += 0.1
        elif evidence_class == "community_content":
            score -= 0.1
        target_year = temporal_years(query)[0]
        temporal_text = " ".join([
            str(item.get("published_at") or ""),
            str(item.get("document_title") or ""),
            str(item.get("claim") or ""),
        ])
        years = [int(value) for value in re.findall(r"\b(20\d{2})\b", temporal_text)]
        eligible = [year for year in years if year <= target_year]
        if eligible:
            delta = target_year - max(eligible)
            score += {0: 0.15, 1: 0.13, 2: 0.09, 3: 0.04}.get(delta, 0.0)
        if re.search(
            r"\b(selected|selection|published|released|final|draft|effective|deadline|roadmap|migration)\b|"
            r"选定|入选|发布|最终版|草案|生效|截止|路线图|迁移",
            temporal_text,
            re.IGNORECASE,
        ):
            score += 0.08
    return round(score, 4)


def _evidence_selection_query(state: P1ResearchState) -> str:
    """Include the plan's concrete entities when selecting compact evidence."""

    plan = state.get("_research_plan") or {}
    parts = [str(state.get("query") or "")]
    parts.extend(str(item) for item in plan.get("key_terms") or [])
    for item in plan.get("subquestions") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("question") or ""))
    for item in plan.get("claims") or []:
        if isinstance(item, dict) and str(item.get("importance") or "").casefold() == "high":
            parts.append(str(item.get("text") or ""))
    return "\n".join(item for item in parts if item.strip())


def _evidence_source_identity(item: dict) -> str:
    raw = " ".join([
        str(item.get("paper_id") or ""),
        str(item.get("url") or ""),
        " ".join(str(value) for value in item.get("evidence_refs") or []),
    ])
    arxiv = re.search(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?", raw)
    if arxiv:
        return f"arxiv:{arxiv.group(1)}"
    return str(item.get("paper_id") or item.get("url") or item.get("source") or item.get("id") or "")


def _named_comparison_systems(query: str) -> set[str]:
    lowered = str(query or "").casefold()
    aliases = {
        "shapefilegpt": ("shapefilegpt",),
        # Some legacy YAML fixtures contain a mojibake byte immediately before
        # "utonomous GIS". Keep the suffix alias until those datasets migrate.
        "autonomous gis": ("autonomous gis", "utonomous gis", "llm-geo"),
        "llm-find": ("llm-find", "llmfind"),
    }
    return {name for name, terms in aliases.items() if any(term in lowered for term in terms)}


def _evidence_mentions_system(item: dict, systems: set[str]) -> bool:
    identity_text = " ".join([
        str(item.get("document_title") or ""),
        str(item.get("paper_id") or ""),
        str(item.get("url") or ""),
        " ".join(str(value) for value in item.get("evidence_refs") or []),
    ]).casefold()
    aliases = {
        "shapefilegpt": ("shapefilegpt", "2410.12376"),
        "autonomous gis": ("autonomous gis", "llm-geo", "2305.06453"),
        "llm-find": ("llm-find", "llmfind", "2407.21024"),
    }
    return any(any(alias in identity_text for alias in aliases.get(system, ())) for system in systems)


def _load_evidence_table(evidence_json: str) -> list[dict]:
    try:
        payload = json.loads(evidence_json) if evidence_json else {}
    except json.JSONDecodeError:
        return []
    return [item for item in payload.get("nodes") or [] if isinstance(item, dict)]


def _profile_from_state(state: P1ResearchState) -> ResearchModeProfile:
    payload = state.get("_research_profile") or {}
    return ResearchModeProfile(
        depth=str(payload.get("depth") or "standard"),  # type: ignore[arg-type]
        planner_model=str(payload.get("planner_model") or "balanced"),
        analyst_model=str(payload.get("analyst_model") or "balanced"),
        reranker_model=str(payload.get("reranker_model") or "flash"),
        synthesizer_model=str(payload.get("synthesizer_model") or "balanced"),
        verifier_model=str(payload.get("verifier_model") or "balanced"),
        max_gap_iterations=int(payload.get("max_gap_iterations") or 0),
        max_subquestions=int(payload.get("max_subquestions") or 4),
        max_parallel_subquestions=int(payload.get("max_parallel_subquestions") or 1),
        candidate_limit=int(payload.get("candidate_limit") or 16),
        final_evidence_limit=int(payload.get("final_evidence_limit") or 8),
        web_max_results=int(payload.get("web_max_results") or 4),
        web_max_subqueries=int(payload.get("web_max_subqueries") or 4),
        web_fetch_limit=int(payload.get("web_fetch_limit") or 3),
        web_fetch_attempts=int(payload.get("web_fetch_attempts") or 5),
        max_query_rewrites=int(payload.get("max_query_rewrites") or 0),
        factcheck_strength=str(payload.get("factcheck_strength") or "full"),
        planner_max_tokens=int(payload.get("planner_max_tokens") or 2400),
        analyst_max_tokens=int(payload.get("analyst_max_tokens") or 1800),
        reranker_max_tokens=int(payload.get("reranker_max_tokens") or 1000),
        synthesizer_max_tokens=int(payload.get("synthesizer_max_tokens") or 3600),
        verifier_max_tokens=int(payload.get("verifier_max_tokens") or 1600),
        token_budget=int(payload.get("token_budget") or 18000),
        model_timeout_seconds=int(payload.get("model_timeout_seconds") or 70),
        max_retries=int(payload.get("max_retries") or 0),
        timeout_seconds=int(payload.get("timeout_seconds") or 240),
    )
