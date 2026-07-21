from __future__ import annotations

import hashlib
import json
import re
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool


class PromptRouterModel:
    """Return deterministic responses by prompt role, not call position."""

    def __init__(self) -> None:
        self.calls: list[object] = []
        self.tools: list[object] = []

    def bind_tools(self, tools):
        self.tools = list(tools)
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        prompt = str(messages[-1].content)
        if "Plan generalized deep research" in prompt:
            return AIMessage(content=json.dumps({
                "query_archetype": {
                    "type": "limitations_and_challenges",
                    "confidence": 0.98,
                    "user_intent": "identify production limitations",
                    "expected_research_actions": [],
                    "required_synthesis_functions": [
                        "limitation_synthesis",
                        "boundary_synthesis",
                    ],
                    "selection_reason": "the query explicitly asks what limits production use",
                },
                "research_strategy": {
                    "primary_archetype": "limitations_and_challenges",
                    "rationale": "scan the limitation space before synthesis",
                    "discovery_actions": ["define_scope"],
                    "depth_actions": ["identify_limitations"],
                    "required_synthesis_functions": [
                        "limitation_synthesis",
                        "boundary_synthesis",
                    ],
                    "stop_policy": ["evidence_and_dimension_saturation"],
                    "breadth_first": True,
                },
                "domain_map": {
                    "scope": "production coding-agent limitations",
                    "key_concepts": ["correctness", "operations"],
                    "terminology": ["verification", "recovery"],
                    "dimensions": [
                        {
                            "id": "correctness",
                            "name": "Correctness and verification",
                            "inclusion_reason": "production changes require verification",
                            "questions_to_answer": [
                                "What evidence describes correctness failures?"
                            ],
                            "expected_evidence_types": ["official_document"],
                            "importance": 0.7,
                        },
                        {
                            "id": "operations",
                            "name": "Operational recovery",
                            "inclusion_reason": "production incidents require recovery",
                            "questions_to_answer": [
                                "What evidence describes operational recovery?"
                            ],
                            "expected_evidence_types": ["official_document"],
                            "importance": 0.7,
                        },
                    ],
                    "dimension_relations": [],
                    "disputed_boundaries": [],
                    "discovery_sources": ["model_prior"],
                },
                "claims": [],
                "model_prior": "Correctness and recovery are distinct production concerns.",
            }))
        if "Analyze acquired evidence" in prompt:
            return AIMessage(content=json.dumps({
                "analysis": "The Web body evidence covers both planned dimensions.",
                "claim_assessments": [],
                "model_claims": [],
                "discovered_dimensions": [],
                "gaps": [],
                "conflicts": [],
            }))
        if "Write one section" in prompt:
            refs = re.findall(r"\[Web:[^\]]+\]", prompt)
            if not refs:
                return AIMessage(content=(
                    "Model analysis: this dimension remains a conceptual limitation, but no "
                    "external body evidence was available in this run."
                ))
            citation = f" {refs[0]}"
            return AIMessage(content=(
                "The official body evidence documents a production limitation and its "
                f"operational boundary.{citation}"
            ))
        if "Create the two global layers" in prompt:
            refs = re.findall(r"\[Web:[^\]]+\]", prompt)
            if not refs:
                return AIMessage(content=json.dumps({
                    "direct_answer": (
                        "Model analysis: correctness verification and operational recovery are "
                        "plausible constraints, but neither was externally verified in this run."
                    ),
                    "cross_dimension_synthesis": (
                        "Model analysis: the two constraints may interact, and that relationship "
                        "remains a follow-up research question rather than an established fact."
                    ),
                }))
            first_ref = refs[0]
            last_ref = refs[-1]
            return AIMessage(content=json.dumps({
                "direct_answer": (
                    "Production use is constrained by correctness verification and operational "
                    "recovery, with both findings grounded in acquired Web body evidence "
                    f"{first_ref}."
                ),
                "cross_dimension_synthesis": (
                    "The dimensions interact because weak verification increases recovery load, "
                    "while recovery limits determine the impact of correctness failures "
                    f"{first_ref} {last_ref}."
                ),
            }))
        if "Fact-check this generalized research report" in prompt:
            return AIMessage(content=json.dumps({"overall": "passed", "issues": []}))
        raise AssertionError(f"unexpected model prompt: {prompt[:120]}")


def test_p1_5_graph_completes_with_rag_empty_and_web_body_evidence() -> None:
    from conflux.__main__ import _empty_multi_agent_state
    from conflux.agent import create_sub_agent
    from conflux.graph_p15 import create_p15_research_graph
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import AgentClaim, SourceResult

    query_log = {"rag": [], "web": []}

    @tool
    def empty_rag(query: str) -> str:
        """Return an explicit empty local corpus result."""
        query_log["rag"].append(query)
        return SourceResult(
            source="RAG",
            status="no_evidence",
            detail="fixture corpus has no relevant documents",
            content="No relevant local evidence.",
        ).to_tool_text()

    @tool
    def web_body(query: str) -> str:
        """Return fetched official body evidence for every planned dimension."""
        query_log["web"].append(query)
        slug = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
        url = f"https://official.example/limitations/{slug}"
        return SourceResult(
            source="Web",
            status="success",
            detail="fixture official body",
            content="The official document describes a production limitation.",
            evidence_class="authoritative_document",
            claims=[AgentClaim(
                claim=(
                    f"The official document for query {slug} describes a production limitation and "
                    "its operational boundary."
                ),
                source="Web",
                verbatim_quote=(
                    "The production control requires verified changes and a recoverable "
                    "operational checkpoint."
                ),
                paper_id=url,
                paper_section="body",
                evidence_refs=[f"[Web:{url}]"],
                evidence_class="authoritative_document",
                relevance=0.95,
                directness=0.95,
                authority=0.95,
                url=url,
                content_kind="html",
            )],
        ).to_tool_text()

    tool_model = PromptRouterModel()
    planner = PromptRouterModel()
    analyst = PromptRouterModel()
    synthesizer = PromptRouterModel()
    verifier = PromptRouterModel()
    profile = resolve_research_profile("standard")
    graph = create_p15_research_graph(
        create_sub_agent("rag", tool_model, empty_rag),
        create_sub_agent("web", tool_model, web_body),
        planner_model=planner,
        analyst_model=analyst,
        synthesizer_model=synthesizer,
        verifier_model=verifier,
        profile=profile,
        model_trace={"roles": {}},
    )
    initial_state = _empty_multi_agent_state(
        "What currently limits autonomous coding agents in production software engineering?",
        run_id="p15-test",
        thread_id="p15-test",
    )

    result = graph.invoke(initial_state)

    planned_questions = {
        "What evidence describes correctness failures?",
        "What evidence describes operational recovery?",
    }
    assert query_log["rag"]
    assert query_log["web"]
    assert planned_questions <= set(query_log["rag"])
    assert planned_questions <= set(query_log["web"])
    prompt_corpus = "\n".join(
        [*query_log["rag"], *query_log["web"]]
        + [
            str(messages[-1].content)
            for model in (planner, analyst, synthesizer, verifier)
            for messages in model.calls
        ]
    )
    assert re.search(r"\bgis\b|geoprocess|地理处理", prompt_corpus, re.IGNORECASE) is None
    assert result["_source_statuses"]["RAG"]["status"] == "no_evidence"
    assert result["_source_statuses"]["Web"]["status"] == "success"
    assert result["_query_archetype"]["type"] == "limitations_and_challenges"
    domain_dimension_ids = {
        item["id"] for item in result["_domain_map"]["dimensions"]
    }
    assert {"correctness", "operations"} <= domain_dimension_ids
    assert 7 <= len(domain_dimension_ids) <= 9
    assert {
        item["dimension_id"] for item in result["_coverage_matrix"]["dimensions"]
    } == domain_dimension_ids
    coverage_rows = result["_coverage_matrix"]["dimensions"]
    assert all(item["body_evidence"] for item in coverage_rows)
    assert all(item["evidence_ids"] for item in coverage_rows)
    assert result["_coverage_matrix"]["stop_reason"] in {
        "coverage_complete",
        "no_actionable_coverage_gaps",
        "coverage_iteration_budget_exhausted",
    }
    assert len(result["_section_contracts"]) == len(domain_dimension_ids)
    assert {item["section_id"] for item in result["_section_drafts"]} == {
        item["id"] for item in result["_section_contracts"]
    }
    assert result["_factcheck_status"] == "passed", json.dumps(
        result["_factcheck_findings"], ensure_ascii=False, indent=2
    )
    assert result["final_answer"].strip()
    assert "[1]" in result["final_answer"]
    assert result["_pipeline_stage"] == "completed"
    assert result["_run_summary"]["mode"] == "p15"
    assert planner.calls
    assert analyst.calls
    assert synthesizer.calls
    assert verifier.calls


def test_coverage_research_retains_completed_plan_but_executes_only_gap_dimension() -> None:
    from conflux.agent import create_sub_agent
    from conflux.graph_p15 import _coverage_research_node, _focus_source_plans
    from conflux.research_modes import resolve_research_profile
    from conflux.research_protocol import DynamicResearchBudget, SourcePlan
    from conflux.source_status import SourceResult

    query_log: list[str] = []

    @tool
    def unused_rag(query: str) -> str:
        """Return no local evidence if unexpectedly routed."""
        raise AssertionError(f"completed or Web-only plan was routed to RAG: {query}")

    @tool
    def gap_web(query: str) -> str:
        """Record the one targeted Web gap query."""
        query_log.append(query)
        return SourceResult(
            source="Web",
            status="success",
            content="Targeted body evidence was fetched.",
        ).to_tool_text()

    plans = [
        SourcePlan(
            id="plan-complete",
            dimension_id="complete",
            source_ids=["builtin.web", "builtin.model"],
            query_intents=["Do not repeat the completed dimension"],
        ),
        SourcePlan(
            id="plan-gap",
            dimension_id="gap",
            source_ids=["builtin.web", "builtin.model"],
            query_intents=["Original broad gap query"],
        ),
    ]
    focused = _focus_source_plans(
        plans,
        [{
            "dimension_id": "gap",
            "dimension": "Operational recovery",
            "questions": ["Find independent operational recovery evidence"],
            "reasons": ["cross-validation is missing"],
        }],
    )

    assert [item.id for item in focused] == ["plan-complete", "plan-gap"]
    assert focused[0].query_intents == []
    assert focused[1].query_intents == ["Find independent operational recovery evidence"]

    profile = resolve_research_profile("standard")
    result = _coverage_research_node(
        {
            "query": "production reliability",
            "source_results": {},
            "_source_plans": [item.to_dict() for item in focused],
            "_research_budget": DynamicResearchBudget(
                depth="standard",
                depth_query_limit=4,
            ).to_dict(),
            "_coverage_iteration": 0,
            "_run_summary": {"stages": []},
        },
        rag_agent=create_sub_agent("rag", PromptRouterModel(), unused_rag),
        web_agent=create_sub_agent("web", PromptRouterModel(), gap_web),
        profile=profile,
    )

    assert query_log == ["Find independent operational recovery evidence"]
    assert result["_coverage_iteration"] == 1
    assert "builtin.web" in result["source_results"]
    assert re.search(r"\bgis\b|geoprocess|地理处理", query_log[0], re.IGNORECASE) is None


def test_source_plan_web_budget_reaches_profiled_tool_arguments() -> None:
    from conflux.agent import create_sub_agent
    from conflux.graph_p15 import _run_source_tasks, _source_tasks
    from conflux.research_modes import resolve_research_profile
    from conflux.research_protocol import DynamicResearchBudget, SourcePlan
    from conflux.source_status import SourceResult

    calls: list[dict[str, int | str | None]] = []

    @tool("search_web")
    def budgeted_web(
        query: str,
        max_subqueries: int | None = None,
        fetch_limit: int | None = None,
        fetch_attempts: int | None = None,
    ) -> str:
        """Record the P1.5 runtime Web budget overrides."""

        calls.append({
            "query": query,
            "max_subqueries": max_subqueries,
            "fetch_limit": fetch_limit,
            "fetch_attempts": fetch_attempts,
        })
        return SourceResult(
            source="Web",
            status="success",
            content="A fetched body was returned within the routed budget.",
        ).to_tool_text()

    plan = SourcePlan(
        id="budgeted-plan",
        dimension_id="recovery",
        source_ids=["builtin.web", "builtin.model"],
        query_intents=["Find recovery body evidence"],
        budget={"queries": 1, "web_fetches": 2},
    )
    tasks = _source_tasks([plan.to_dict()], "builtin.web", limit=4)
    budget = DynamicResearchBudget(
        depth="standard",
        web_fetch_limit=4,
        web_fetch_attempts=6,
    )

    result = _run_source_tasks(
        create_sub_agent("web", PromptRouterModel(), budgeted_web),
        "Web",
        tasks,
        resolve_research_profile("standard"),
        budget=budget,
    )

    assert result.status == "success"
    assert calls == [{
        "query": "Find recovery body evidence",
        "max_subqueries": 1,
        "fetch_limit": 2,
        "fetch_attempts": 6,
    }]


def test_low_relevance_source_status_cannot_become_report_evidence() -> None:
    from conflux.graph_p15 import _p15_evidence_table, _select_p15_evidence
    from conflux.source_status import AgentClaim, SourceResult

    result = SourceResult(
        source="Web",
        status="low_relevance",
        content="A weakly related fetched page.",
        evidence_class="community_content",
        claims=[AgentClaim(
            claim="The weak page mentions recovery only in passing.",
            source="Web",
            verbatim_quote="Recovery is mentioned without supporting the requested claim.",
            evidence_refs=["[Web:https://example.org/weak]"],
            url="https://example.org/weak",
            content_kind="html",
            subquestion_id="recovery",
        )],
    )

    table = _p15_evidence_table({"builtin.web": result})

    assert table[0]["status"] == "low_relevance"
    assert _select_p15_evidence(table, 10) == []


def test_p1_5_graph_dual_external_failure_keeps_public_envelope_without_citations() -> None:
    from conflux.__main__ import _empty_multi_agent_state
    from conflux.agent import create_sub_agent
    from conflux.graph_p15 import create_p15_research_graph
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import SourceResult

    @tool
    def empty_rag(query: str) -> str:
        """Return an explicit empty local source."""
        return SourceResult(
            source="RAG",
            status="no_evidence",
            content="No relevant local evidence.",
        ).to_tool_text()

    @tool
    def failed_web(query: str) -> str:
        """Return an explicit Web failure."""
        return SourceResult(
            source="Web",
            status="failed",
            error="fixture timeout",
            content="Web retrieval failed.",
        ).to_tool_text()

    model = PromptRouterModel()
    profile = resolve_research_profile("standard")
    graph = create_p15_research_graph(
        create_sub_agent("rag", PromptRouterModel(), empty_rag),
        create_sub_agent("web", PromptRouterModel(), failed_web),
        planner_model=model,
        analyst_model=model,
        synthesizer_model=model,
        verifier_model=model,
        profile=profile,
    )
    result = graph.invoke(_empty_multi_agent_state(
        "What currently limits autonomous coding agents in production software engineering?",
        run_id="p15-dual-failure",
        thread_id="p15-dual-failure",
    ))

    report = result["final_answer"]
    assert re.findall(r"^##\s+(.+)$", report, re.MULTILINE) == [
        "回答",
        "参考文献与证据",
        "置信度附录",
    ]
    assert result["_source_statuses"]["RAG"]["status"] == "no_evidence"
    assert result["_source_statuses"]["Web"]["status"] == "failed"
    assert "Model analysis:" in report
    assert "[RAG:" not in report
    assert "[Web:" not in report
    assert re.search(r"\[\d+(?:,\d+)*\]", report) is None
    assert result["_factcheck_status"] == "passed"
    assert result["_pipeline_stage"] == "completed"


def test_finalize_combines_base_generalization_and_richness_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import conflux.graph_p15 as graph_p15

    monkeypatch.setattr(
        graph_p15,
        "evaluate_p1_quality",
        lambda state: {"passed": True, "overall": 5.0},
    )
    monkeypatch.setattr(
        graph_p15,
        "evaluate_p15_quality",
        lambda state: {"passed": True, "overall": 5.0},
    )
    monkeypatch.setattr(
        graph_p15,
        "evaluate_generalized_research_quality",
        lambda *args, **kwargs: {"passed": False, "overall": 3.5},
    )

    result = graph_p15._p15_finalize_node({
        "query": "quality gate",
        "final_answer": "A non-empty but insufficiently rich report.",
        "source_results": {},
        "_report_outline": {"query_archetype": "comparison", "sections": []},
        "_coverage_matrix": {"dimensions": []},
        "_section_drafts": [],
        "_research_budget": {"evidence_limit": 1},
        "_run_summary": {"stages": []},
    })

    quality = result["_quality_report"]
    assert quality["overall"] == 5.0
    assert quality["generalization"]["research_quality"] == {
        "passed": False,
        "overall": 3.5,
    }
    assert quality["generalization"]["passed"] is False
    assert quality["passed"] is False


def test_finalize_rejects_actual_dispatch_usage_above_runtime_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import conflux.graph_p15 as graph_p15

    monkeypatch.setattr(graph_p15, "evaluate_p1_quality", lambda state: {"passed": True})
    monkeypatch.setattr(graph_p15, "evaluate_p15_quality", lambda state: {"passed": True})
    monkeypatch.setattr(
        graph_p15,
        "evaluate_generalized_research_quality",
        lambda *args, **kwargs: {"passed": True},
    )

    result = graph_p15._p15_finalize_node({
        "query": "runtime budget gate",
        "final_answer": "A traced report.",
        "source_results": {},
        "_report_outline": {"query_archetype": "comparison", "sections": []},
        "_coverage_matrix": {"dimensions": []},
        "_section_drafts": [],
        "_research_budget": {
            "breadth_query_limit": 2,
            "depth_query_limit": 1,
            "web_fetch_limit": 1,
            "web_fetch_attempts": 2,
            "max_gap_iterations": 1,
            "evidence_limit": 1,
        },
        "_budget_usage": {
            "breadth_queries": 3,
            "depth_queries": 1,
            "web_fetches": 1,
            "web_fetch_attempts": 2,
            "gap_iterations": 1,
            "breadth_committed": True,
        },
        "_run_summary": {"stages": []},
    })

    runtime = result["_quality_report"]["generalization"]["runtime_budget"]
    assert runtime["passed"] is False
    assert runtime["within_limits"]["breadth_queries"] is False
    assert result["_quality_report"]["passed"] is False


def test_verifier_gap_research_shares_coverage_iteration_budget() -> None:
    from conflux.graph_p15 import _p15_verification_router
    from conflux.research_modes import resolve_research_profile

    route = _p15_verification_router(
        {
            "query": "shared gap budget",
            "_gap_questions": ["Find one more source"],
            "_research_budget": {
                "depth_query_limit": 4,
                "web_fetch_limit": 4,
                "web_fetch_attempts": 6,
                "max_gap_iterations": 1,
            },
            "_budget_usage": {
                "depth_queries": 1,
                "gap_iterations": 1,
                "breadth_committed": True,
            },
            "_source_statuses": {
                "RAG": {"status": "success"},
                "Web": {"status": "success"},
            },
            "_run_summary": {"started_at": 0},
        },
        resolve_research_profile("standard"),
    )

    assert route == "finalize"


@pytest.mark.parametrize(
    ("pipeline", "generalization_enabled", "expected_factory"),
    [("p15", True, "p15"), ("p15", False, "p1"), ("p1", True, "p1")],
)
def test_research_pipeline_flag_selects_p15_or_rolls_back_to_p1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    pipeline: str,
    generalization_enabled: bool,
    expected_factory: str,
) -> None:
    import conflux.__main__ as cli

    selected: list[str] = []

    def graph_factory(name: str):
        def create(*args, **kwargs):
            selected.append(name)
            return {"graph": name}

        return create

    role_models = {
        "planner": object(),
        "analyst": object(),
        "synthesizer": object(),
        "verifier": object(),
        "reranker": object(),
    }
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "research": {
                "pipeline": pipeline,
                "generalization": {"enabled": generalization_enabled},
            }
        },
    )
    monkeypatch.setattr(cli, "validate_runtime_credentials", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "create_vector_store", lambda: object())
    monkeypatch.setattr(cli, "HybridRetriever", lambda store: object())
    monkeypatch.setattr(cli, "create_research_models", lambda depth, **kwargs: (role_models, {"roles": {}}))
    monkeypatch.setattr(cli, "set_model", lambda model: None)
    monkeypatch.setattr(cli, "create_rag_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_web_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_sub_agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        cli,
        "create_checkpointer",
        lambda backend: SimpleNamespace(backend="memory", checkpointer=None),
    )
    monkeypatch.setattr(cli, "create_p15_research_graph", graph_factory("p15"))
    monkeypatch.setattr(cli, "create_p1_research_graph", graph_factory("p1"))
    monkeypatch.setattr(
        cli,
        "_run_phase2_graph",
        lambda graph, initial_state, query, **kwargs: (
            {
                **initial_state,
                "final_answer": "",
                "_run_summary": {},
                "_source_statuses": {},
                "_quality_report": {},
            },
            [],
        ),
    )
    monkeypatch.setattr(cli, "write_trace_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "write_run_summary", lambda *args, **kwargs: None)

    result = cli.query_command(
        "offline feature flag test",
        mode="phase2",
        output_dir=str(tmp_path),
        run_id=f"feature-{pipeline}",
        depth="quick",
    )

    assert selected == [expected_factory]
    assert result["_report_artifacts"]["markdown_path"] == ""
