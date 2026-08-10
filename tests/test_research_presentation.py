"""Focused regressions for research report presentation and FactCheck wording."""

from __future__ import annotations

import json
import time

from conflux.graph_v2 import (
    SectionResult,
    _compile_claim_record_body,
    _new_state,
    _short_section_title,
    factcheck_v2_node,
    finalize_node,
    synthesize_node,
)
from conflux.research_protocol import ClaimRecord
from conflux.research_prompts import (
    CLAIM_GENERATION_NO_EVIDENCE_PROMPT,
    CLAIM_GENERATION_PROMPT,
)


class _JsonModel:
    def __init__(self, payload: dict):
        self.payload = payload

    def invoke(self, messages):
        return type("Response", (), {"content": json.dumps(self.payload, ensure_ascii=False)})()


def _claim(
    claim_id: str,
    subquestion_id: str,
    text: str,
    claim_type: str,
    *,
    importance: str = "medium",
    refs: list[str] | None = None,
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        subquestion_id=subquestion_id,
        text=text,
        claim_type=claim_type,
        importance=importance,
        generation_attribution={
            "section_title": subquestion_id,
            "citation_refs": refs or [],
        },
        verification_result={
            "verdict": "supports",
            "confidence": 1.0,
            "reason": "test verification",
            "verifier_version": "test-v1",
        },
    )


def test_claim_records_render_as_grouped_section_paragraphs():
    section = SectionResult(sub_question_id="sq-1", title="智能体能力现状")
    records = [
        _claim("c1", "sq-1", "已有系统能够完成工具调用任务", "direct_fact", importance="critical", refs=["[1]"]),
        _claim("c2", "sq-1", "公开评测仍存在任务覆盖不足", "direct_fact", refs=["[2]"]),
        _claim("c3", "sq-1", "部署时需要权衡可靠性与成本", "derived_analysis"),
        _claim("c4", "sq-1", "长期自主性仍缺乏充分证据", "model_analysis"),
    ]

    body = _compile_claim_record_body(section, records, {"[1]": "one", "[2]": "two"})

    assert all(record.text in body for record in records)
    assert body.count("（分析判断）") == 1
    assert body.count("（推导分析）") == 1
    assert len(body.split("\n\n")) == 4
    assert "[1]" in body and "[2]" in body


def test_many_analysis_claims_are_split_into_readable_paragraphs():
    section = SectionResult(sub_question_id="sq-1", title="能力边界")
    records = [
        _claim(
            f"m{index}",
            "sq-1",
            f"分析结论 {index}",
            "model_analysis",
            importance="critical" if index == 1 else "medium",
        )
        for index in range(1, 11)
    ]

    body = _compile_claim_record_body(section, records, {})
    paragraphs = body.split("\n\n")

    assert len(paragraphs) == 4
    assert body.count("（分析判断）") == 4
    assert all(paragraph.count("分析结论") <= 4 for paragraph in paragraphs)


def test_claim_generation_prompts_follow_the_query_language():
    assert "Match the language of the research question and subquestion" in CLAIM_GENERATION_PROMPT
    assert "Match the language of the research question and subquestion" in CLAIM_GENERATION_NO_EVIDENCE_PROMPT


def test_synthesis_keeps_direct_and_cross_section_content_distinct():
    state = _new_state("用户原始问题")
    sections = [
        SectionResult(sub_question_id="sq-1", title="能力现状"),
        SectionResult(sub_question_id="sq-2", title="技术路线"),
    ]
    records = [
        _claim("a1", "sq-1", "Alpha primary conclusion", "direct_fact", refs=["[1]"]),
        _claim("a2", "sq-1", "Alpha secondary trade-off", "model_analysis"),
        _claim("b1", "sq-2", "Beta primary conclusion", "direct_fact", refs=["[2]"]),
        _claim("b2", "sq-2", "Beta secondary limitation", "derived_analysis"),
    ]
    state.update({
        "_core_question": "模型扩写后的核心问题",
        "_section_results": [section.to_dict() for section in sections],
        "_claim_records": [record.to_dict() for record in records],
        "_citation_map": {"[1]": "one", "[2]": "two"},
    })
    model = _JsonModel({
        "direct_answer": {
            "text": "The two sections show established primary capabilities with different evidence bases.",
            "claim_ids": ["a1", "b1"],
        },
        "cross_synthesis": {
            "text": "Across sections, the remaining trade-off and limitation should be evaluated together.",
            "claim_ids": ["a2", "b2"],
        },
    })

    result = synthesize_node(state, model)

    assert "established primary capabilities" in result["_direct_answer"]
    assert "Alpha primary conclusion" not in result["_direct_answer"]
    assert "remaining trade-off and limitation" in result["_cross_synthesis"]
    assert "Alpha secondary trade-off" not in result["_cross_synthesis"]
    assert result["_cross_synthesis"].count("跨节综合分析") == 1
    assert result["_synthesis_bindings"]["direct_answer"]["claim_ids"] == ["a1", "b1"]
    assert result["_synthesis_bindings"]["cross_synthesis"]["claim_ids"] == ["a2", "b2"]


def test_finalize_uses_original_query_and_bounded_section_title():
    long_question = "截至2026年，基于大模型的智能体在工具调用、网页操作、编码和办公任务中的能力水平与落地现状如何？"
    title = _short_section_title(long_question)
    result = finalize_node({
        "query": "基于大模型的智能体发展现状如何？",
        "_core_question": long_question,
        "_direct_answer": "直接结论。",
        "_section_results": [{
            "sub_question_id": "sq-1",
            "title": title,
            "body": "章节正文。",
            "finish_reason": "complete",
        }],
        "_started_at": 0,
    })

    markdown = result["_report_markdown"]
    assert markdown.startswith("# 基于大模型的智能体发展现状如何？")
    assert f"## {title}" in markdown
    assert len(title) <= 42
    assert not title.endswith("？")


def test_factcheck_separates_external_fact_support_from_analysis_protocol():
    records = [
        _claim("f1", "sq-1", "Externally supported fact", "direct_fact", refs=["[1]"]),
        _claim("d1", "sq-1", "Evidence-derived interpretation", "derived_analysis"),
        _claim("m1", "sq-1", "Model analysis judgment", "model_analysis"),
    ]
    state = {
        "query": "research question",
        "_run_id": "presentation-factcheck",
        "_run_status": "completed",
        "_report_available": True,
        "_report_markdown": "# research question\n\n## 直接回答\n\nanswer\n\n## 可信度说明\n\nmedium\n",
        "_citation_map": {"[1]": "external evidence"},
        "_section_results": [{
            "sub_question_id": "sq-1",
            "title": "section",
            "body": "body",
            "finish_reason": "complete",
        }],
        "_claim_records": [record.to_dict() for record in records],
        "_audit_metrics": {"sections_completed": 1, "sections_failed": 0},
        "_delivery_assessment": {
            "claim_gate": {
                "claim_gate": True,
                "status": "deliverable",
                "protocol_errors": {},
                "metrics": {"critical_claim_failures": []},
            },
        },
    }

    result = factcheck_v2_node(state, model=None)
    factcheck = result["_verified_answer"]

    assert "外部事实核验：1/1 条 factual claims 获得外部证据支持" in factcheck
    assert "分析声明检查：2/2 条分析性声明" in factcheck
    assert "不代表这些分析具有外部事实支持" in factcheck
    assert "3/3 条声明有证据支持" not in factcheck
    assert result["_factcheck_findings"]["factual_claims"] == 1
    assert result["_factcheck_findings"]["analysis_claims"] == 2


def test_failed_generation_uses_compact_honest_report_language():
    long_title = "当前基于大模型的智能体在哪些领域和场景中已有实际应用？有哪些成熟的平台、框架或代表性系统？"
    state = _new_state("基于大模型的智能体发展现状如何？", deadline_at=time.time())
    state.update({
        "_core_question": "扩写后的核心问题",
        "_section_results": [{
            "sub_question_id": "sq-1",
            "title": long_title,
            "body": "本节未能在本次运行时限内完成，因此不提供未经核验的替代结论。",
            "finish_reason": "failed",
        }],
        "_citation_map": {
            "[1]": (
                "Learn more × Back to arXiv License: CC BY 4.0 raw navigation text "
                "（来源：Web Example Agent Study https://example.test/paper）"
            ),
        },
    })

    synthesized = synthesize_node(state, model=None)
    state.update(synthesized)
    state.update({
        "_credibility_text": "当前可信度为 low。",
        "_started_at": 0,
    })
    finalized = finalize_node(state)
    state.update(finalized)
    state.update({
        "_report_available": True,
        "_audit_metrics": {"sections_completed": 0, "sections_failed": 1},
    })
    checked = factcheck_v2_node(state, model=None)
    markdown = checked["_report_markdown"]

    assert "不能作为该研究问题的结论性回答" in markdown
    assert "## 跨节综合" not in markdown
    assert "## 当前基于大模型的智能体在哪些领域和场景中已有实际应用？有哪些成熟的平台" not in markdown
    assert "Learn more" not in markdown
    assert "[1] Web Example Agent Study https://example.test/paper" in markdown
    assert "本次未生成可核验声明" in markdown
    assert "0/0 条声明有证据支持" not in markdown
