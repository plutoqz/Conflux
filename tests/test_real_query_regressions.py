"""Regression tests for real-query RAG/Web/arbitration failure modes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_rag_complex_chinese_query_keeps_weak_gis_context():
    from langchain_core.documents import Document

    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class FakeRetriever:
        def search(self, query):
            return [
                Document(
                    page_content=(
                        "Geographic information systems (GIS) integrate spatial data, "
                        "web mapping, geospatial analysis, remote sensing, and databases."
                    ),
                    metadata={
                        "source": "wiki--geographic-information-system.md",
                        "chunk_id": "wiki--geographic-information-system.md#p0#c0",
                    },
                ),
                Document(
                    page_content="ArcGIS is Esri software for mapping and spatial analysis.",
                    metadata={
                        "source": "wiki--arcgis.md",
                        "chunk_id": "wiki--arcgis.md#p0#c0",
                    },
                ),
            ]

    result = create_rag_tool(FakeRetriever()).invoke({
        "query": "OSM 与 ArcGIS 语义映射、知识图谱和 GeoSPARQL 在 GIS 系统里如何结合？"
    })
    parsed = parse_source_results(str(result))

    assert parsed
    source_result = parsed[-1]
    assert source_result.status in {"success", "low_relevance"}
    assert source_result.status != "failed"
    assert "wiki--geographic-information-system.md" in source_result.metadata["matched_sources"]
    assert source_result.metadata["query_plan"]["subqueries"]
    assert "top_relevance_score" in source_result.metadata


def test_web_garbage_results_return_no_evidence(monkeypatch):
    from conflux.source_status import parse_source_results
    import conflux.tools.web as web_tool

    monkeypatch.setattr(
        web_tool,
        "_search_duckduckgo",
        lambda query, max_results=5: [
            {
                "title": "Instagram photos and videos",
                "snippet": "Sign up to see photos and videos from your friends.",
                "url": "https://www.instagram.com/example/",
            },
            {
                "title": "GIS agent slides",
                "snippet": "Upload and share presentations online.",
                "url": "https://www.slideshare.net/example/gis-agent",
            },
            {
                "title": "Random profile",
                "snippet": "Short page.",
                "url": "https://www.pinterest.com/example/",
            },
        ],
    )

    result = web_tool.search_web.invoke({"query": "GIS agent GeoAI LLM GIS agent history"})
    parsed = parse_source_results(str(result))

    assert parsed
    source_result = parsed[-1]
    assert source_result.status == "no_evidence"
    assert source_result.metadata["kept_count"] == 0
    assert source_result.metadata["filtered_count"] >= 3
    assert not source_result.claims


def test_synthesize_replaces_short_refusal_with_model_only_report():
    from conflux.graph_v2 import _ensure_model_fallback_report

    source_statuses = {
        "RAG": {"status": "no_evidence", "content": "No relevant local chunks."},
        "Web": {"status": "no_evidence", "content": "Search returned unrelated pages."},
        "Model": {
            "status": "success",
            "content": (
                "GIS 智能体的发展脉络可概括为：早期 GIS 自动化脚本和专家系统，"
                "随后发展到 GeoAI 与空间数据科学，再到结合 LLM 的工具调用、规划、"
                "地图制图、空间查询和多步骤地理分析智能体。"
            ),
        },
    }

    report = _ensure_model_fallback_report(
        "GIS 智能体的发展脉络是什么？",
        "你好，我无法给到相关内容。",
        source_statuses,
        "",
    )

    assert len(report) > 600
    assert "模型推断" in report
    assert "[Model]" in report
    assert "无法给到相关内容" not in report
    assert "GIS 智能体的发展脉络" in report
