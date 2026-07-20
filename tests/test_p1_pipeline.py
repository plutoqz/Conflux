"""P1 graph regressions for planning, source fusion, and answer revision."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage
from langchain_core.tools import tool


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("unexpected model call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return AIMessage(content=response)


def _plan(*questions: str) -> str:
    return json.dumps({
        "question_type": "research_synthesis",
        "audience": "researcher",
        "time_scope": "current",
        "key_terms": ["automation", "limitations"],
        "subquestions": [
            {
                "id": f"subq-{index + 1}",
                "question": question,
                "source_preferences": ["Model", "RAG", "Web"],
                "importance": "high",
                "stop_condition": "direct evidence",
            }
            for index, question in enumerate(questions)
        ],
        "claims": [{
            "id": "claim-prior",
            "text": "Automation systems often trade flexibility for reliability.",
            "claim_type": "parametric_background",
            "importance": "medium",
            "temporal_sensitivity": "low",
            "risk": "low",
        }],
        "model_prior": "A useful conceptual prior about reliability, error recovery, and data access.",
    }, ensure_ascii=False)


def _analysis() -> str:
    return json.dumps({
        "analysis": "Local papers explain error recovery; the web source adds current deployment context.",
        "claim_assessments": [],
        "model_claims": [{"claim": "These limitations interact at workflow boundaries.", "claim_type": "analysis"}],
        "gaps": [],
        "conflicts": [],
    }, ensure_ascii=False)


def _source_tools(query_log: dict[str, list[str]]):
    from conflux.source_status import AgentClaim, SourceResult

    @tool
    def rag_tool(query: str) -> str:
        """Return local paper evidence."""
        query_log["rag"].append(query)
        return SourceResult(
            source="RAG",
            status="success",
            detail="fixture",
            content="The paper states that generated-code errors require manual recovery.",
            evidence_class="peer_reviewed",
            claims=[AgentClaim(
                claim="Generated-code errors require manual recovery in complex workflows.",
                source="RAG",
                verbatim_quote="Generated-code errors require manual recovery in complex workflows.",
                paper_id="paper",
                paper_section="limitations",
                evidence_refs=["[RAG:paper#chunk-1]"],
                evidence_class="peer_reviewed",
                relevance=0.95,
                directness=0.95,
                authority=0.9,
            )],
        ).to_tool_text()

    @tool
    def web_tool(query: str) -> str:
        """Return fetched web-body evidence."""
        query_log["web"].append(query)
        return SourceResult(
            source="Web",
            status="success",
            detail="fixture fetched body",
            content="Operational deployments remain constrained by online data discovery.",
            evidence_class="authoritative_document",
            claims=[AgentClaim(
                claim="Operational deployments remain constrained by online data discovery.",
                source="Web",
                verbatim_quote="Operational deployments remain constrained by online data discovery.",
                paper_id="https://example.gov/report",
                paper_section="body",
                evidence_refs=["[Web:https://example.gov/report]"],
                evidence_class="authoritative_document",
                relevance=0.9,
                directness=0.9,
                authority=0.88,
                url="https://example.gov/report",
                content_kind="html",
            )],
        ).to_tool_text()

    return rag_tool, web_tool


def _initial_state(query: str) -> dict:
    from conflux.__main__ import _empty_multi_agent_state

    return _empty_multi_agent_state(query, run_id="p1-test", thread_id="p1-test")


def test_p1_graph_plans_independent_queries_and_passes_verification():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile

    queries = {"rag": [], "web": []}
    rag_tool, web_tool = _source_tools(queries)
    tool_model = FakeModel([])
    planner = FakeModel([_plan("What are the error-recovery limitations?", "What limits online data discovery?")])
    analyst = FakeModel([_analysis()])
    report = """## 回答

- 复杂工作流中的生成代码错误仍需要人工恢复。[RAG:paper#chunk-1]
- 在线数据发现仍限制实际部署。[Web:https://example.gov/report]

这些问题会在跨工具工作流边界相互放大，因此评测不能只观察单步成功率。

## 研究依据

本地论文给出错误恢复限制，官方网页正文给出在线数据发现限制。

## 可靠性与缺口

两项关键事实都有直接来源；跨限制的交互属于综合分析。"""
    synthesizer = FakeModel([report])
    verifier = FakeModel([json.dumps({"overall": "passed", "issues": []})])
    profile = resolve_research_profile("standard")
    graph = create_p1_research_graph(
        create_sub_agent("rag", tool_model, rag_tool),
        create_sub_agent("web", tool_model, web_tool),
        planner_model=planner,
        analyst_model=analyst,
        synthesizer_model=synthesizer,
        verifier_model=verifier,
        profile=profile,
        model_trace={"roles": {}},
    )
    result = graph.invoke(_initial_state("What are the limitations?"))

    assert queries["rag"] == ["What are the error-recovery limitations?", "What limits online data discovery?"]
    assert queries["web"] == queries["rag"]
    assert result["_factcheck_status"] == "passed"
    assert result["final_answer"] == report
    assert result["_quality_report"]["passed"] is True
    assert "research_plan" in result["_run_summary"]["stages"]
    assert "factcheck_revision" in result["_run_summary"]["stages"]
    assert result["_run_summary"]["slo_p95_ms"] == profile.timeout_seconds * 1000


def test_p1_factcheck_rewrites_main_answer_instead_of_appending_notes():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile

    queries = {"rag": [], "web": []}
    rag_tool, web_tool = _source_tools(queries)
    tool_model = FakeModel([])
    bad_report = """## 回答

- 错误恢复已经完全自动化。[RAG:invented]

## 研究依据

引用见正文。

## 可靠性与缺口

无。"""
    corrected = """## 回答

- 复杂工作流中的生成代码错误仍需要人工恢复。[RAG:paper#chunk-1]
- 在线数据发现仍限制实际部署。[Web:https://example.gov/report]

## 研究依据

结论分别来自论文限制章节和已获取的官方网页正文。

## 可靠性与缺口

关键事实已有直接证据，跨场景普适性仍需更多评测。"""
    graph = create_p1_research_graph(
        create_sub_agent("rag", tool_model, rag_tool),
        create_sub_agent("web", tool_model, web_tool),
        planner_model=FakeModel([_plan("What are the limitations?")]),
        analyst_model=FakeModel([_analysis()]),
        synthesizer_model=FakeModel([bad_report, corrected]),
        verifier_model=FakeModel([
            json.dumps({
                "overall": "needs_revision",
                "issues": [{
                    "claim_id": "",
                    "issue_type": "citation_mismatch",
                    "severity": "high",
                    "description": "The invented citation does not resolve.",
                    "evidence_ids": ["[RAG:invented]"],
                    "suggested_action": "replace with acquired evidence",
                    "requires_research": False,
                }, {
                    "claim_id": "claim-prior",
                    "issue_type": "overstated_claim",
                    "severity": "high",
                    "description": "The wording claims complete automation beyond the evidence.",
                    "evidence_ids": ["[RAG:paper#chunk-1]"],
                    "suggested_action": "qualify the conclusion",
                    "requires_research": False,
                }, {
                    "claim_id": "claim-missing",
                    "issue_type": "missing_dimension",
                    "severity": "medium",
                    "description": "The answer omits online data discovery limitations.",
                    "evidence_ids": ["[Web:https://example.gov/report]"],
                    "suggested_action": "add the missing dimension",
                    "requires_research": False,
                }],
            }),
            json.dumps({"issues": []}),
        ]),
        profile=resolve_research_profile("standard"),
    )
    result = graph.invoke(_initial_state("What are the limitations?"))

    assert result["final_answer"] == corrected
    assert "invented" not in result["final_answer"]
    assert result["_factcheck_findings"]["revision_applied"] is True
    assert result["_factcheck_status"] == "passed"
    assert "Verification Revision Log" not in result["final_answer"]
    assert {item["issue_type"] for item in result["_verification_issues"]} == {
        "citation_mismatch", "overstated_claim", "missing_dimension",
    }


def test_p1_model_only_still_returns_a_usable_answer_when_external_sources_fail():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import SourceResult

    @tool
    def unavailable_rag(query: str) -> str:
        """Return an explicit local-source failure."""
        return SourceResult(source="RAG", status="no_evidence", content="No local evidence.").to_tool_text()

    @tool
    def unavailable_web(query: str) -> str:
        """Return an explicit web-source failure."""
        return SourceResult(source="Web", status="failed", error="timeout", content="Web unavailable.").to_tool_text()

    report = """## 回答

低风险开放问题仍可使用模型世界知识给出概念框架、主要机制和候选判断，但不应把近期数字或高风险事实说成已经外部核验。

## 研究依据

本轮使用模型参数化知识完成问题拆解和综合，没有生成外部引用。

## 可靠性与缺口

RAG 与 Web 本轮不可用；涉及近期变化的事实需要恢复外部来源后复核。"""
    graph = create_p1_research_graph(
        create_sub_agent("rag", FakeModel([]), unavailable_rag),
        create_sub_agent("web", FakeModel([]), unavailable_web),
        planner_model=FakeModel([_plan("How should the problem be framed?")]),
        analyst_model=FakeModel([_analysis()]),
        synthesizer_model=FakeModel([report]),
        verifier_model=FakeModel([json.dumps({"overall": "passed", "issues": []})]),
        profile=resolve_research_profile("standard"),
    )
    result = graph.invoke(_initial_state("How should the problem be framed?"))

    assert result["final_answer"] == report
    assert result["_factcheck_status"] == "passed"
    assert result["_quality_report"]["passed"] is True
    assert result["_quality_report"]["available_sources"] == ["Model"]


def test_p1_quick_mode_uses_light_deterministic_factcheck_without_llm_verifier():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import SourceResult

    @tool
    def unavailable_rag(query: str) -> str:
        """Return no local evidence for the quick-mode fixture."""
        return SourceResult(source="RAG", status="no_evidence", content="No local evidence.").to_tool_text()

    @tool
    def unavailable_web(query: str) -> str:
        """Return no web evidence for the quick-mode fixture."""
        return SourceResult(source="Web", status="no_evidence", content="No web evidence.").to_tool_text()

    report = """## 回答

可用模型知识先给出概念框架，并避免把强时效事实表述为已核验结论。

## 研究依据

本轮依据模型参数化知识完成问题拆解和综合。

## 可靠性与缺口

外部证据尚未覆盖，近期事实需后续复核。"""
    verifier = FakeModel([])
    graph = create_p1_research_graph(
        create_sub_agent("rag", FakeModel([]), unavailable_rag),
        create_sub_agent("web", FakeModel([]), unavailable_web),
        planner_model=FakeModel([_plan("How should the problem be framed?")]),
        analyst_model=FakeModel([_analysis()]),
        synthesizer_model=FakeModel([report]),
        verifier_model=verifier,
        profile=resolve_research_profile("quick"),
    )
    result = graph.invoke(_initial_state("How should the problem be framed?"))

    assert verifier.calls == []
    assert result["final_answer"] == report
    assert result["_factcheck_status"] == "passed"


def test_p1_standard_mode_marks_failed_semantic_verification_for_review():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile

    queries = {"rag": [], "web": []}
    rag_tool, web_tool = _source_tools(queries)
    report = """## 回答

复杂工作流中的生成代码错误仍需要人工恢复。[RAG:paper#chunk-1]

## 研究依据

结论来自论文限制章节。

## 可靠性与缺口

跨系统适用性仍需更多案例验证。"""
    graph = create_p1_research_graph(
        create_sub_agent("rag", FakeModel([]), rag_tool),
        create_sub_agent("web", FakeModel([]), web_tool),
        planner_model=FakeModel([_plan("What are the limitations?")]),
        analyst_model=FakeModel([_analysis()]),
        synthesizer_model=FakeModel([report]),
        verifier_model=FakeModel([TimeoutError("verifier deadline")]),
        profile=resolve_research_profile("standard"),
    )
    result = graph.invoke(_initial_state("What are the limitations?"))

    assert result["_factcheck_status"] == "needs_review"
    assert "TimeoutError" in result["_factcheck_findings"]["verifier_error"]
    assert result["_quality_report"]["passed"] is False


def test_p1_evidence_gap_triggers_bounded_research_resynthesis_and_recheck():
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.research_modes import resolve_research_profile

    queries = {"rag": [], "web": []}
    rag_tool, web_tool = _source_tools(queries)
    initial = """## 回答

现有证据说明错误恢复仍有限。[RAG:paper#chunk-1]

## 研究依据

初始论文证据。

## 可靠性与缺口

在线数据发现的部署影响仍待补证。"""
    pre_gap_revision = """## 回答

错误恢复仍有限，在线数据发现的影响暂不作确定判断。[RAG:paper#chunk-1]

## 研究依据

初始论文证据。

## 可靠性与缺口

需要补充在线数据发现的直接证据。"""
    after_gap = """## 回答

错误恢复和在线数据发现分别限制复杂工作流与实际部署。[RAG:paper#chunk-1] [Web:https://example.gov/report]

## 研究依据

新增网页正文补齐了部署维度，并与本地论文限制章节共同进入重新综合。

## 可靠性与缺口

两个关键维度已有直接证据，跨场景泛化仍需更多评测。"""
    verifier = FakeModel([
        json.dumps({
            "overall": "needs_research",
            "issues": [{
                "claim_id": "claim-deployment",
                "issue_type": "unsupported_claim",
                "severity": "high",
                "description": "What direct evidence shows that online data discovery limits deployment?",
                "evidence_ids": [],
                "suggested_action": "retrieve direct deployment evidence",
                "requires_research": True,
            }],
        }),
        json.dumps({
            "issues": [{
                "claim_id": "claim-deployment",
                "issue_type": "unsupported_claim",
                "severity": "high",
                "description": "What direct evidence shows that online data discovery limits deployment?",
                "evidence_ids": [],
                "suggested_action": "retrieve direct deployment evidence",
                "requires_research": True,
            }],
        }),
        json.dumps({"issues": []}),
    ])
    graph = create_p1_research_graph(
        create_sub_agent("rag", FakeModel([]), rag_tool),
        create_sub_agent("web", FakeModel([]), web_tool),
        planner_model=FakeModel([_plan("What are the known limitations?")]),
        analyst_model=FakeModel([_analysis(), _analysis()]),
        synthesizer_model=FakeModel([initial, pre_gap_revision, after_gap]),
        verifier_model=verifier,
        profile=resolve_research_profile("standard"),
    )
    result = graph.invoke(_initial_state("What are the limitations?"))

    gap_question = "What direct evidence shows that online data discovery limits deployment?"
    assert queries["rag"] == ["What are the known limitations?", gap_question]
    assert queries["web"] == queries["rag"]
    assert result["final_answer"] == after_gap
    assert result["_gap_iteration"] == 1
    assert result["_deep_queries"] == [gap_question]
    assert "gap_research_1" in result["_run_summary"]["stages"]
    assert result["_factcheck_status"] == "passed"


def test_analyst_gap_alone_does_not_force_more_retrieval():
    from conflux.graph_p1 import _gap_questions

    assert _gap_questions([], ["A useful but nonessential open question"]) == []
