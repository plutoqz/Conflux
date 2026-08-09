"""V3 阶段一回归测试（§8.11.1）—— 引用错配防护。

固化两个回归约束：
1. 无关引用必须失败（unrelated citation must fail）：
   正文引用了合法标号，但该标号未被分配给本节、且与本节子问题无任何
   主题重叠时，确定性审计必须检出 off-domain evidence，交付必须失败。
2. 无主题重叠不得分配全局引用（no topic overlap → no global citation）：
   _section_citation_map 只允许分配与子问题有主题重叠的全局引用；
   全部无重叠时返回空，不得按位置顺序兜底塞入无关引用。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.evaluation_v2 import build_v2_run_record  # noqa: E402
from conflux.graph_v2 import (  # noqa: E402
    SectionResult,
    _compute_deterministic_metrics,
    _section_citation_map,
    audit_node,
    factcheck_v2_node,
)

# 混合语料：GIS 主题 + 量子密码主题，两个主题域互不重叠
CITATION_MAP = {
    "[1]": "GIS 空间分析支持网络分析与缓冲区分析。 地理处理自动化存在脚本化瓶颈。（来源：RAG）ArcGIS 文档",
    "[2]": "后量子密码标准化进程由 NIST 主导，FIPS 203 ML-KEM 已发布。 迁移路径存在兼容性挑战。（来源：Web）NIST 报告",
}


def _state(sections: list[SectionResult]) -> dict:
    return {
        "_section_results": [sr.to_dict() for sr in sections],
        "_citation_map": CITATION_MAP,
        "_rag_status": "success",
        "_web_status": "success",
        "_rag_count": 2,
        "_web_count": 2,
        "_report_markdown": "",
        "_started_at": 0.0,
        "_deadline_at": None,
        "_run_id": "regression-run",
        "query": "test",
    }


# ============================================================
# 回归约束 2：无主题重叠不得分配全局引用
# ============================================================

class TestNoTopicOverlapNoGlobalCitation:
    def test_no_overlap_returns_empty(self):
        # 灾害知识图谱子问题与 GIS / 量子密码语料均无主题重叠 → 不得分配任何引用
        selected = _section_citation_map("地质灾害知识图谱构建有哪些方法？", CITATION_MAP)
        assert selected == {}

    def test_overlap_returns_matching_only(self):
        selected = _section_citation_map("GIS 自动化处理有哪些瓶颈？", CITATION_MAP)
        assert "[1]" in selected
        assert "[2]" not in selected

    def test_overlap_returns_matching_only_other_domain(self):
        selected = _section_citation_map("后量子密码迁移有哪些挑战？", CITATION_MAP)
        assert "[2]" in selected
        assert "[1]" not in selected

    def test_empty_terms_returns_empty(self):
        # 子问题提取不到任何 term 时同样不得分配全局引用
        selected = _section_citation_map("???", CITATION_MAP)
        assert selected == {}

    def test_generation_records_allowed_refs(self):
        # 生成路径：无重叠时 allowed_refs 为空，模型只能写分析判断
        from conflux.graph_v2 import _generate_section

        class _FakeModel:
            def invoke(self, messages):
                return type("R", (), {
                    "content": "本节无外部证据，纯分析判断。（分析判断）\n---summary---\n核心结论：无证据。\n来源：无",
                })()

        sr = _generate_section(
            {"id": "sq-1", "question": "地质灾害知识图谱构建有哪些方法？"},
            "研究问题",
            "（本地知识库中暂未检索到相关内容）",
            "（网络搜索暂未检索到相关内容）",
            CITATION_MAP,
            _FakeModel(),
            target_length=500,
        )
        assert sr.allowed_refs == []
        assert sr.citation_refs == []


# ============================================================
# 回归约束 1：无关引用必须失败
# ============================================================

class TestUnrelatedCitationMustFail:
    def _gis_section_with_quantum_citation(self) -> SectionResult:
        # GIS 节引用了后量子密码引用 [2]（与 GIS 完全无主题重叠），
        # 且该节只被分配了 [1]（GIS 主题引用）
        return SectionResult(
            sub_question_id="sq-1",
            title="GIS 自动化处理有哪些瓶颈？",
            body="正文引用了无关证据[2]。",
            citation_refs=["[2]"],
            allowed_refs=["[1]"],  # 该节仅被分配 [1]
            finish_reason="complete",
        )

    def test_metrics_flags_off_domain_evidence(self):
        state = _state([self._gis_section_with_quantum_citation()])
        metrics = _compute_deterministic_metrics(state)
        assert metrics["off_domain_evidence_in_report"] == 1
        assert metrics["off_domain_citation_list"][0]["ref"] == "[2]"

    def test_audit_delivery_fails_on_off_domain(self):
        state = _state([self._gis_section_with_quantum_citation()])
        result = audit_node(state, None)
        assert result["_delivery_status"] == "diagnostic_only"
        assert result["_audit_metrics"]["off_domain_evidence_in_report"] == 1

    def test_run_summary_reports_off_domain(self):
        # 回归：run_summary 里的 off_domain_evidence_in_report 曾硬编码为 0
        state = _state([self._gis_section_with_quantum_citation()])
        state.update(audit_node(state, None))
        result = factcheck_v2_node(state, None)
        summary = result["_run_summary"]
        assert summary["off_domain_evidence_in_report"] == 1
        assert summary["off_domain_citation_list"]

    def test_evaluation_gate_fails_no_off_domain(self):
        # 评测门禁：off-domain > 0 → no_off_domain_evidence 确定性检查失败
        state = _state([self._gis_section_with_quantum_citation()])
        state.update(audit_node(state, None))
        result = factcheck_v2_node(state, None)
        summary = result["_run_summary"]
        record = build_v2_run_record(
            {"id": "case-off-domain", "query": "GIS 自动化处理有哪些瓶颈？", "domain": "gis", "category": "limitations"},
            summary,
        )
        assert "no_off_domain_evidence" in record["deterministic_failures"]
        assert record["deterministic_passed"] is False

    def test_in_section_allowed_ref_is_not_off_domain(self):
        # 正常路径：被分配的引用不触发失败（防误报）
        sr = SectionResult(
            sub_question_id="sq-1",
            title="后量子密码迁移有哪些挑战？",
            body="迁移存在兼容性问题[2]。",
            citation_refs=["[2]"],
            allowed_refs=["[2]"],  # 该节被分配了 [2]
            finish_reason="complete",
        )
        metrics = _compute_deterministic_metrics(_state([sr]))
        assert metrics["off_domain_evidence_in_report"] == 0


# ============================================================
# V2 wiring 回归（§8.11.2）：查询改写器、重排器、run_id 不得被丢弃
# ============================================================

class TestV2Wiring:
    def test_graph_passes_rewriter_reranker_and_run_id_to_tools(self, monkeypatch):
        from conflux import graph_v2 as gv2
        from conflux.research_modes import resolve_research_profile

        captured: dict[str, tuple] = {}

        def fake_rag_tool(retriever, query_rewriter, semantic_reranker, profile):
            captured["rag"] = (query_rewriter is not None, semantic_reranker is not None)
            return object()  # tool stub；编译期不会调用

        def fake_web_tool(profile, **kwargs):
            captured["web"] = (kwargs.get("query_rewriter") is not None, kwargs.get("run_id"))
            return object()

        monkeypatch.setattr(gv2, "create_rag_tool", fake_rag_tool)
        monkeypatch.setattr(gv2, "create_web_tool", fake_web_tool)

        profile = resolve_research_profile("quick")
        gv2.create_v2_research_graph(
            None, None,  # retriever 存在时 agent 分支不启用
            planner_model=object(),
            synthesizer_model=object(),
            profile=profile,
            retriever=object(),
            query_rewriter=object(),
            semantic_reranker=object(),
            run_id="run-wiring-test",
            deadline_at=None,
        )

        # 回归：曾用 create_rag_tool(retriever, None, None, profile) 与
        # create_web_tool(profile, run_id=new_run_id()) 重建，丢弃全部配置
        assert captured["rag"] == (True, True), captured
        assert captured["web"] == (True, "run-wiring-test"), captured

    def test_llm_rerank_disabled_by_default(self, monkeypatch):
        from conflux import graph_v2 as gv2
        from conflux.research_modes import resolve_research_profile

        captured: dict[str, tuple] = {}

        def fake_rag_tool(retriever, query_rewriter, semantic_reranker, profile):
            captured["rag"] = (query_rewriter is not None, semantic_reranker is not None)
            return object()

        monkeypatch.setattr(gv2, "create_rag_tool", fake_rag_tool)
        profile = resolve_research_profile("quick")
        gv2.create_v2_research_graph(
            None,
            None,
            planner_model=object(),
            synthesizer_model=object(),
            profile=profile,
            retriever=object(),
            query_rewriter=object(),
            reranker_model=object(),
            llm_rerank_enabled=False,
            run_id="run-rerank-off",
            deadline_at=None,
        )
        assert captured["rag"] == (True, False), captured

    def test_llm_rerank_created_when_enabled(self, monkeypatch):
        from conflux import graph_v2 as gv2
        from conflux.research_modes import resolve_research_profile

        captured: dict[str, tuple] = {}

        def fake_rag_tool(retriever, query_rewriter, semantic_reranker, profile):
            captured["rag"] = (query_rewriter is not None, semantic_reranker is not None)
            return object()

        monkeypatch.setattr(gv2, "create_rag_tool", fake_rag_tool)
        profile = resolve_research_profile("quick")
        gv2.create_v2_research_graph(
            None,
            None,
            planner_model=object(),
            synthesizer_model=object(),
            profile=profile,
            retriever=object(),
            query_rewriter=object(),
            reranker_model=object(),
            llm_rerank_enabled=True,
            run_id="run-rerank-on",
            deadline_at=None,
        )
        assert captured["rag"] == (True, True), captured

    def test_graph_falls_back_to_agent_when_no_retriever(self, monkeypatch):
        from conflux import graph_v2 as gv2
        from conflux.research_modes import resolve_research_profile

        created = {"rag": False, "web": False}

        def fake_rag_tool(*args, **kwargs):
            created["rag"] = True
            return object()

        def fake_web_tool(*args, **kwargs):
            created["web"] = True
            return object()

        monkeypatch.setattr(gv2, "create_rag_tool", fake_rag_tool)
        monkeypatch.setattr(gv2, "create_web_tool", fake_web_tool)

        profile = resolve_research_profile("quick")
        gv2.create_v2_research_graph(
            object(), object(),  # rag_agent / web_agent 直接用作 tool
            planner_model=object(),
            synthesizer_model=object(),
            profile=profile,
        )
        # 无 retriever 时不重建工具，使用传入的 agent/tool
        assert created == {"rag": False, "web": False}
