import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.messages import AIMessage


def test_missing_evidence_class_keeps_legacy_model_as_inference():
    from conflux.source_status import SourceResult

    result = SourceResult.from_dict({"source": "Model", "status": "success", "content": "推断"})

    assert result.evidence_class == "model_inference"
    assert not result.can_support_external_fact


def test_trace_parses_nested_failed_source_result():
    from conflux.source_status import AgentClaim, SourceResult
    from conflux.trace import _trace_agent_status

    text = SourceResult(
        source="Web",
        status="failed",
        content="",
        claims=[AgentClaim(claim="nested", source="Web")],
        metadata={"request": {"query": "nested"}},
    ).to_tool_text()

    assert _trace_agent_status(text) == "failed"


def test_true_consensus_requires_same_claim_and_distinct_document_identity():
    from conflux.evidence import EvidenceGraph, EvidenceNode

    unrelated = EvidenceGraph()
    unrelated.add_node(EvidenceNode(
        id="r1", claim="视觉模型可以估算城市洪水深度。", source="RAG",
        paper_id="paper-a", evidence_class="peer_reviewed",
    ))
    unrelated.add_node(EvidenceNode(
        id="w1", claim="该城市明天可能出现降雨。", source="Web",
        paper_id="page-b", evidence_class="authoritative_document",
    ))
    unrelated.link_surface_relations()
    assert unrelated.consensus_summary()["true_consensus_count"] == 0

    supported = EvidenceGraph()
    for node in (
        EvidenceNode(
            id="r1", claim="视觉模型可以估算城市洪水深度。", source="RAG",
            paper_id="paper-a", evidence_class="peer_reviewed",
        ),
        EvidenceNode(
            id="w1", claim="视觉模型可以估算城市洪水深度。", source="Web",
            paper_id="paper-b", evidence_class="peer_reviewed",
        ),
    ):
        supported.add_node(node)
    supported.link_surface_relations()
    assert supported.consensus_summary()["true_consensus_count"] == 1

    supported.nodes["w1"].paper_id = "paper-a"
    assert supported.consensus_summary()["true_consensus_count"] == 0


def test_evidence_dedup_uses_full_normalized_claim_not_prefix():
    from conflux.evidence import build_evidence_graph_from_results
    from conflux.source_status import AgentClaim, SourceResult

    prefix = "知识图谱可用于城市数据集成"
    result = SourceResult(
        source="RAG", status="success", content="evidence", evidence_class="peer_reviewed",
        claims=[
            AgentClaim(claim=f"{prefix}，并提升洪水深度估算精度。", source="RAG", paper_id="p1"),
            AgentClaim(claim=f"{prefix}，但不会提升洪水深度估算精度。", source="RAG", paper_id="p1"),
            AgentClaim(claim=f"{prefix}，并提升洪水深度估算精度。", source="RAG", paper_id="p1"),
        ],
    )

    graph = build_evidence_graph_from_results({"RAG": result})
    assert len(graph.nodes) == 2


def test_model_only_success_with_weak_external_hits_is_capped_and_fails():
    from conflux.quality import evaluate_run_quality

    evidence = {
        "summary": {"source_counts": {"RAG": 1, "Web": 1, "Model": 1}},
        "source_statuses": {"RAG": {}, "Web": {}, "Model": {}},
        "nodes": [
            {
                "id": "r1", "claim": "弱相关本地声明", "source": "RAG",
                "evidence_class": "authoritative_document", "verbatim_quote": "弱相关本地声明",
                "evidence_refs": ["[RAG:p#chunk-1]"],
            },
            {
                "id": "w1", "claim": "弱相关网页声明", "source": "Web",
                "evidence_class": "authoritative_document", "verbatim_quote": "弱相关网页声明",
                "evidence_refs": ["[Web:https://example.test]"],
            },
        ],
    }
    report = """## 最终结论
- 弱相关本地声明。[RAG]
- 弱相关网页声明。[Web]

## 信息来源
RAG/Web 均为弱相关。

## 不确定性
缺少高相关外部证据。

## 证据摘要
仅有弱相关上下文。

## 工程落地建议
继续检索。
"""
    quality = evaluate_run_quality({
        "final_answer": report,
        "_source_statuses": {
            "RAG": {"status": "low_relevance", "can_support_external_fact": True},
            "Web": {"status": "low_relevance", "can_support_external_fact": True},
            "Model": {"status": "success", "can_support_external_fact": False},
        },
        "_run_summary": {
            "stages": ["dispatch", "evidence_merge", "synthesize", "factcheck"],
            "slo_status": "pass",
        },
        "_factcheck_status": "passed",
        "_factcheck_findings": {"issues": [], "verified_claim_ratio": 1.0},
        "_deep_research": "证据支持；模型推断。",
        "_evidence_json": json.dumps(evidence, ensure_ascii=False),
    })

    assert not quality["passed"]
    assert quality["overall"] <= 3.5
    assert quality["external_fact_sources"] == []


def test_quality_marks_disabled_l4_as_not_applicable():
    from conflux.quality import evaluate_run_quality

    quality = evaluate_run_quality({
        "final_answer": "report",
        "_run_summary": {"stages": ["dispatch"], "l4_enabled": False},
        "_source_statuses": {},
        "_evidence_json": "",
    })

    assert quality["scores"]["L4深化质量"] is None


def test_report_writes_real_sidecars_and_acceptance_reads_evidence(tmp_path):
    from conflux.acceptance import validate_report_pair
    from conflux.report import write_report_artifacts

    statuses = {
        "RAG": {"status": "success", "detail": "local", "content": "evidence"},
        "Web": {"status": "failed", "detail": "web", "error": "timeout"},
        "Model": {"status": "success", "detail": "analyst", "content": "analysis"},
    }
    evidence = {
        "summary": {"total_nodes": 1, "source_counts": {"RAG": 1}},
        "source_statuses": statuses,
        "nodes": [{
            "id": "r1", "source": "RAG", "claim": "外部证据支持该结论。",
            "evidence_refs": ["[RAG:paper-a#chunk-1]"],
        }],
    }
    state = {
        "final_answer": """## 最终结论
- 外部证据支持该结论。[RAG]

## 信息来源
RAG 提供证据。

## 不确定性
Web 不可用。

## 证据摘要
存在一条可追溯证据。
""",
        "_verified_answer": "### 确定性追溯检查\n- success 来源：RAG, Model\n- low_relevance 来源：无",
        "_evidence_json": json.dumps(evidence, ensure_ascii=False),
        "_source_statuses": statuses,
        "_merged": "原始 RAG 输出",
        "_run_summary": {"mode": "phase2", "stages": ["dispatch"], "slo_status": "pass"},
        "_quality_report": {"overall": 4.2, "passed": True, "scores": {}, "notes": []},
    }

    artifacts = write_report_artifacts("sidecar", state, tmp_path)
    result = validate_report_pair(artifacts.markdown_path, artifacts.html_path)

    assert artifacts.evidence_json_path and artifacts.evidence_json_path.exists()
    assert artifacts.raw_sources_path and artifacts.raw_sources_path.exists()
    assert result.passed


def test_rag_claim_skips_markdown_title_and_prefers_results():
    from conflux.tools.rag import _claim_from_chunk

    text = """# FloodVision: Urban Flood Depth Estimation

## Abstract
This paper introduces a flood estimation framework for urban scenes.

## Results
The proposed method reduced depth RMSE by 12% on the benchmark dataset.
"""

    claim = _claim_from_chunk(text)
    assert not claim.startswith("FloodVision")
    assert "reduced depth RMSE by 12%" in claim


def test_flood_query_plan_contains_bilingual_domain_terms():
    from conflux.query_planner import plan_queries

    plan = plan_queries("知识图谱如何用于城市洪水水深评估", target="web", max_subqueries=8)
    combined = " ".join(plan.subqueries).lower()

    assert "flood depth estimation" in combined
    assert "water level" in combined


def test_academic_search_aggregates_all_configured_public_apis(monkeypatch):
    from conflux.tools import web

    providers = (
        ("_search_semantic_scholar", "semantic_scholar"),
        ("_search_openalex", "openalex"),
        ("_search_crossref", "crossref"),
        ("_search_arxiv", "arxiv"),
    )
    for function_name, provider_name in providers:
        monkeypatch.setattr(
            web,
            function_name,
            lambda query, limit, name=provider_name: [{
                "title": name,
                "snippet": f"{name} returned a sufficiently detailed academic abstract.",
                "url": f"https://example.test/{name}",
                "provider_source": name,
            }],
        )

    results = web._search_academic_sources("flood depth estimation", max_results=5)
    assert {item["provider_source"] for item in results} == {
        "semantic_scholar", "openalex", "crossref", "arxiv",
    }


def test_rag_limits_each_paper_to_two_chunks():
    from langchain_core.documents import Document
    from conflux.tools.rag import _limit_per_paper

    scored = [
        {
            "doc": Document(page_content=f"chunk {index}", metadata={"paper_id": paper_id, "chunk_id": f"c{index}"}),
            "score": 0.9 - index * 0.01,
        }
        for index, paper_id in enumerate(["paper-a", "paper-a", "paper-a", "paper-b"])
    ]

    limited = _limit_per_paper(scored, limit=2)
    identities = [item["doc"].metadata["paper_id"] for item in limited]
    assert identities.count("paper-a") == 2
    assert identities.count("paper-b") == 1


def test_rag_low_relevance_triggers_rewritten_query_retry():
    from langchain_core.documents import Document
    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class Retriever:
        def __init__(self):
            self.calls = []

        def search(self, query):
            self.calls.append(query)
            if "method results limitations" in query:
                return [Document(
                    page_content="The obscure alpha method improved benchmark accuracy by 14%.",
                    metadata={
                        "paper_id": "paper-retry", "source": "retry-paper",
                        "chunk_id": "retry-paper#c1", "relevance_score": 0.95,
                        "paper_section": "results", "peer_reviewed": True,
                    },
                )]
            return [Document(
                page_content="Generic unrelated background without a usable finding.",
                metadata={"paper_id": "weak", "source": "weak", "chunk_id": "weak#c1", "relevance_score": 0.05},
            )]

    retriever = Retriever()
    payload = create_rag_tool(retriever).invoke({"query": "obscure alpha"})
    result = parse_source_results(str(payload))[0]

    assert result.status == "success"
    assert result.metadata["retry_queries"]
    assert any("method results limitations" in query for query in retriever.calls)


def test_factcheck_matches_report_claim_to_structured_quote():
    from conflux.graph_v2 import _deterministic_factcheck

    claim = "该方法在基准数据集上将洪水深度 RMSE 降低了 12%。"
    evidence = {
        "nodes": [{
            "id": "r1", "claim": claim, "source": "RAG",
            "evidence_class": "peer_reviewed", "verbatim_quote": claim,
            "evidence_refs": ["[RAG:paper-a#chunk-results]"],
        }],
    }
    findings = _deterministic_factcheck(
        f"## 最终结论\n- {claim}[RAG]\n\n## 不确定性\n结果仅适用于该数据集。",
        {
            "RAG": {"status": "success"},
            "Web": {"status": "no_evidence"},
            "Model": {"status": "success"},
        },
        json.dumps(evidence, ensure_ascii=False),
    )

    assert findings["verified_claim_ratio"] == 1.0
    assert findings["claim_checks"][0]["verification"] == "verified"


def test_factcheck_persists_quality_when_l4_is_disabled():
    from conflux.graph_v2 import factcheck_node

    claim = "该方法在基准数据集上将洪水深度 RMSE 降低了 12%。"
    statuses = {
        "RAG": {"status": "success", "can_support_external_fact": True},
        "Web": {"status": "failed", "can_support_external_fact": False},
        "Model": {"status": "success", "can_support_external_fact": False},
    }
    evidence = {
        "summary": {"source_counts": {"RAG": 1}},
        "source_statuses": statuses,
        "nodes": [{
            "id": "r1", "claim": claim, "source": "RAG",
            "evidence_class": "peer_reviewed", "verbatim_quote": claim,
            "evidence_refs": ["[RAG:paper-a#chunk-results]"],
        }],
    }

    class Model:
        def invoke(self, messages):
            return AIMessage(content="验证通过：所有关键声明均有信息源支持")

    result = factcheck_node({
        "final_answer": f"""## 最终结论
- {claim}[RAG:paper-a#chunk-results]

## 信息来源
RAG 提供同行评审证据。

## 不确定性
结果仅适用于该数据集。

## 证据摘要
一条外部声明可追溯。

## 工程落地建议
在更多数据集复现。
""",
        "_source_statuses": statuses,
        "_evidence_json": json.dumps(evidence, ensure_ascii=False),
        "_run_summary": {
            "stages": ["dispatch", "evidence_merge", "synthesize"],
            "l4_enabled": False,
            "slo_status": "pass",
        },
    }, agent=SimpleNamespace(raw_model=Model()))

    assert result["_factcheck_status"] == "passed"
    assert result["_quality_report"]
    assert result["_quality_report"]["scores"]["L4深化质量"] is None


def test_acceptance_does_not_fabricate_nodes_without_evidence_sidecar(tmp_path):
    from conflux.acceptance import _extract_evidence_payload

    markdown_path = tmp_path / "missing.md"
    markdown_path.write_text("# report", encoding="utf-8")
    issues = []

    assert _extract_evidence_payload("# report", issues, markdown_path) == {}
    assert any("证据图附件不存在" in issue for issue in issues)


def test_model_analyst_runs_once_after_receiving_external_evidence():
    from conflux.graph_v2 import model_agent_node
    from conflux.source_status import AgentClaim, SourceResult, parse_source_results

    class FakeModel:
        def __init__(self):
            self.calls = []

        def invoke(self, messages):
            self.calls.append(messages)
            return AIMessage(content="模型推断：两条外部证据需要进一步比较。")

    model = FakeModel()
    state = {
        "query": "研究问题",
        "rag_result": SourceResult(
            source="RAG", status="success", content="RAG evidence",
            evidence_class="peer_reviewed",
            claims=[AgentClaim(
                claim="RAG 外部声明", source="RAG", verbatim_quote="RAG 外部声明",
                paper_id="p1", evidence_refs=["[RAG:p1#chunk-1]"], evidence_class="peer_reviewed",
            )],
        ).to_tool_text(),
        "web_result": SourceResult(
            source="Web", status="success", content="Web evidence",
            evidence_class="authoritative_document",
            claims=[AgentClaim(
                claim="Web 外部声明", source="Web", verbatim_quote="Web 外部声明",
                paper_id="p2", evidence_refs=["[Web:https://example.test]"],
                evidence_class="authoritative_document",
            )],
        ).to_tool_text(),
        "_run_summary": {},
    }

    output = model_agent_node(state, agent=SimpleNamespace(raw_model=model))
    result = parse_source_results(output["model_result"])[0]

    assert len(model.calls) == 1
    assert result.evidence_class == "model_inference"
    assert result.metadata["evidence_ids"]
    assert "RAG 外部声明" in str(model.calls[0])
