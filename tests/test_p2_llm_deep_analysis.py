"""P2 LLM 深度分析测试（真实 API 联调改造）。

覆盖：LLM 成功路径（suggestions 映射）、降级路径（失败/无效 JSON → 确定性）、
telemetry 统计、prompt 格式、chunk 预览截断。
"""

from __future__ import annotations

import json

import pytest

from conflux.core.p2_contracts import (
    ImpactSuggestionType,
    PaperIdentity,
    ProjectPaperLink,
    ProjectResearchContext,
    RadarRunStats,
    SearchIntent,
    SearchIntentType,
)
from conflux.paper_radar.deep_analyzer import (
    LLM_ANALYSIS_PROMPT,
    _llm_analyze_paper,
    _llm_chunk_preview,
    _llm_payload_to_suggestions,
    _parse_llm_json,
    _score_chunks,
    run_deep_analysis,
)


def _context() -> ProjectResearchContext:
    return ProjectResearchContext(
        project_id="test",
        overall_goal="Build GIS agents with knowledge graphs",
        research_questions=["How to integrate knowledge graphs with geospatial reasoning?"],
    )


def _link(paper_id: str = "2401.00001") -> ProjectPaperLink:
    return ProjectPaperLink(
        project_id="test",
        paper_identity=PaperIdentity(source="arxiv", canonical_id=paper_id),
        relevance=0.85,
    )


def _paper_dict(**overrides) -> dict:
    base = {
        "id": "2401.00001",
        "title": "Knowledge-Grounded GIS Agents",
        "abstract": "A framework for GIS agent workflow verification.",
        "source": "arxiv",
        "authors": ["Alice"],
        "year": 2025,
    }
    base.update(overrides)
    return base


class _FakeLLM:
    """Chat model stub returning a canned response with usage metadata."""

    def __init__(self, content: str, total_tokens: int = 120):
        self.content = content
        self.total_tokens = total_tokens

    def invoke(self, messages):
        class _Resp:
            content = self.content
            usage_metadata = {"total_tokens": self.total_tokens}

        return _Resp()


class TestLLMAnalysisSuccess:
    def test_maps_llm_payload_to_suggestions(self):
        link = _link()
        payload = {
            "relevance": 0.9,
            "suggestions": [
                {
                    "type": "link_evidence",
                    "summary": "Knowledge graphs improve geospatial fusion",
                    "rationale": "Paper proposes graph-based fusion",
                    "evidence_refs": ["p1:c0"],
                    "confidence": 0.85,
                    "target_id": "",
                },
                {
                    "type": "propose_experiment",
                    "summary": "Adapt the pipeline for our benchmark",
                    "rationale": "Methods align with project",
                    "evidence_refs": ["abstract"],
                    "confidence": 0.6,
                    "target_id": "",
                },
            ],
        }
        suggestions = _llm_payload_to_suggestions(payload, link, run_id="run-1")
        assert len(suggestions) == 2
        assert suggestions[0].type == ImpactSuggestionType.LINK_EVIDENCE
        assert suggestions[0].evidence_refs == ["p1:c0"]
        assert suggestions[0].confidence == 0.85
        assert suggestions[0].created_by_run == "run-1"
        assert suggestions[1].type == ImpactSuggestionType.PROPOSE_EXPERIMENT

    def test_ignores_invalid_types_and_empty_summaries(self):
        link = _link()
        payload = {
            "relevance": 0.5,
            "suggestions": [
                {"type": "not_a_type", "summary": "x", "evidence_refs": []},
                {"type": "link_evidence", "summary": "", "evidence_refs": []},
                {"type": "link_evidence", "summary": "valid", "evidence_refs": []},
            ],
        }
        suggestions = _llm_payload_to_suggestions(payload, link, run_id="r")
        assert len(suggestions) == 1
        assert suggestions[0].summary == "valid"

    def test_clamps_confidence_out_of_range(self):
        link = _link()
        payload = {
            "suggestions": [
                {"type": "link_evidence", "summary": "s", "confidence": 99, "evidence_refs": []},
            ],
        }
        suggestions = _llm_payload_to_suggestions(payload, link, run_id="r")
        assert suggestions[0].confidence == 1.0


class TestLLMAnalysisFallback:
    def test_llm_exception_falls_back_with_telemetry(self):
        class _Boom:
            def invoke(self, messages):
                raise RuntimeError("network down")

        link = _link()
        suggestions, telemetry = _llm_analyze_paper(
            link=link,
            paper_dict=_paper_dict(),
            context=_context(),
            chunks=[{"page": 0, "chunk_idx": 0, "text": "GIS agents"}],
            run_id="r",
            llm_model=_Boom(),
        )
        assert suggestions == []
        assert telemetry["fell_back"] is True
        assert telemetry["calls"] == 1

    def test_invalid_json_falls_back(self):
        model = _FakeLLM("this is not json at all")
        link = _link()
        suggestions, telemetry = _llm_analyze_paper(
            link=link,
            paper_dict=_paper_dict(),
            context=_context(),
            chunks=[{"page": 0, "chunk_idx": 0, "text": "GIS"}],
            run_id="r",
            llm_model=model,
        )
        assert suggestions == []
        assert telemetry["fell_back"] is True
        assert telemetry["total_tokens"] == 120

    def test_empty_suggestions_falls_back(self):
        model = _FakeLLM(json.dumps({"relevance": 0.1, "suggestions": []}))
        link = _link()
        suggestions, telemetry = _llm_analyze_paper(
            link=link,
            paper_dict=_paper_dict(),
            context=_context(),
            chunks=[{"page": 0, "chunk_idx": 0, "text": "GIS"}],
            run_id="r",
            llm_model=model,
        )
        assert suggestions == []
        assert telemetry["fell_back"] is True


class TestRunDeepAnalysisWithLLM:
    def test_run_deep_analysis_llm_success_records_stats(self):
        model = _FakeLLM(json.dumps({
            "relevance": 0.9,
            "suggestions": [
                {"type": "link_evidence", "summary": "Relevant evidence",
                 "rationale": "x", "evidence_refs": ["p0:c0"], "confidence": 0.8, "target_id": ""},
            ],
        }), total_tokens=150)
        stats = RadarRunStats(project_id="test", run_id="run-1")
        suggestions = run_deep_analysis(
            [(_link(), _paper_dict())],
            _context(),
            [],
            max_papers=1,
            llm_model=model,
            stats=stats,
        )
        assert len(suggestions) == 1
        assert stats.llm_calls == 1
        assert stats.llm_total_tokens == 150
        assert stats.llm_fallback_count == 0

    def test_run_deep_analysis_llm_failure_falls_back_to_deterministic(self):
        class _Boom:
            def invoke(self, messages):
                raise RuntimeError("timeout")

        stats = RadarRunStats(project_id="test", run_id="run-1")
        suggestions = run_deep_analysis(
            [(_link(), _paper_dict(abstract="GIS agents with knowledge graphs"))],
            _context(),
            [],
            max_papers=1,
            llm_model=_Boom(),
            stats=stats,
        )
        # Deterministic fallback still produces the link_evidence suggestion.
        assert len(suggestions) >= 1
        assert suggestions[0].type == ImpactSuggestionType.LINK_EVIDENCE
        assert stats.llm_calls == 1
        assert stats.llm_fallback_count == 1

    def test_without_llm_model_uses_deterministic_only(self):
        stats = RadarRunStats(project_id="test", run_id="run-1")
        suggestions = run_deep_analysis(
            [(_link(), _paper_dict(abstract="GIS agents with knowledge graphs"))],
            _context(),
            [],
            max_papers=1,
            stats=stats,
        )
        assert len(suggestions) >= 1
        assert stats.llm_calls == 0
        assert stats.llm_fallback_count == 0


class TestLLMPrompt:
    def test_prompt_contains_context_and_paper(self):
        prompt = LLM_ANALYSIS_PROMPT.format(
            overall_goal="goal",
            research_questions="- rq1",
            milestones="- m1",
            gaps="- gap",
            title="title",
            authors="a",
            year="2025",
            abstract="abstract text",
            chunks_text="[p0:c0] chunk",
        )
        assert "总体目标" in prompt
        assert "title" in prompt
        assert "p0:c0" in prompt
        assert "link_evidence" in prompt

    def test_chunk_preview_is_bounded(self):
        chunks = [
            {"page": i, "chunk_idx": 0, "text": "x" * 2000}
            for i in range(10)
        ]
        preview = _llm_chunk_preview(chunks, limit=4000)
        assert len(preview) <= 4500  # budget + ref prefixes
        assert preview.count("[p") <= 4  # about 2000 chars each

    def test_chunk_preview_empty(self):
        assert _llm_chunk_preview([]) == "（无全文）"


class TestParseLLMJson:
    def test_plain_json(self):
        assert _parse_llm_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert _parse_llm_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_with_trailing_text(self):
        assert _parse_llm_json('ok {"a": 1} done') == {"a": 1}

    def test_invalid_json_returns_none(self):
        assert _parse_llm_json("no braces here") is None
        assert _parse_llm_json("{bad") is None
        assert _parse_llm_json("") is None
