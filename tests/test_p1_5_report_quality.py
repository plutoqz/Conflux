from __future__ import annotations

import time
from types import SimpleNamespace

from conflux.graph_p15 import (
    _fallback_section_content,
    _synthesize_global_layers,
    _synthesize_sections_batch,
)
from conflux.research_generalization import (
    build_coverage_matrix,
    build_section_drafts,
    build_section_evidence_packs,
    evaluate_generalized_research_quality,
    research_should_stop,
)
from conflux.research_protocol import (
    DomainMap,
    DynamicResearchBudget,
    QueryArchetype,
    ReportOutline,
    ResearchDimension,
    SectionClaim,
    SectionContract,
    SectionDraft,
    SectionEvidencePack,
)


def _archetype() -> QueryArchetype:
    return QueryArchetype(
        type="limitations_and_challenges",
        expected_research_actions=[
            "define_scope",
            "identify_limitations",
            "assess_impact",
        ],
    )


def _domain_map() -> DomainMap:
    return DomainMap(
        scope="GIS automation bottlenecks",
        dimensions=[
            ResearchDimension(
                id="operations",
                name="Operational constraints",
                importance=0.9,
            )
        ],
    )


def _external(action: str, *, role: str = "direct_support") -> dict:
    return {
        "id": f"external-{action}",
        "dimension_id": "operations",
        "source": "Web",
        "status": "success",
        "claim": f"The official GIS document covers {action}.",
        "verbatim_quote": "The documented GIS workflow has a directly observed operational constraint.",
        "content_kind": "html",
        "body_valid": True,
        "evidence_class": "authoritative_document",
        "evidence_role": role,
        "domain_relevance": 0.95,
        "claim_entailment": 0.95,
        "authority": 0.9,
        "source_identity": f"official:{action}",
        "research_actions": [action],
        "evidence_refs": [f"[Web:https://official.example/{action}]"],
    }


def _model(action: str) -> dict:
    return {
        "id": f"model-{action}",
        "dimension_id": "operations",
        "source": "Model",
        "status": "success",
        "claim": f"Model analysis for {action}.",
        "verbatim_quote": f"Model analysis for {action}.",
        "evidence_class": "model_inference",
        "evidence_role": "model_analysis",
        "research_actions": [action],
    }


def test_coverage_is_dimension_by_action_and_model_only_high_risk_stays_open() -> None:
    matrix = build_coverage_matrix(
        _domain_map(),
        [_external("define_scope"), _model("assess_impact")],
        archetype=_archetype(),
    )

    row = matrix.dimensions[0]
    cells = {item.action: item for item in row.action_coverage}
    assert cells["define_scope"].status == "covered"
    assert cells["identify_limitations"].status == "gap"
    assert cells["assess_impact"].status == "model_analysis"
    assert cells["assess_impact"].high_risk is True
    assert row.status == "partial"
    assert row.missing_actions == ["identify_limitations", "assess_impact"]
    assert matrix.high_importance_coverage == 0.333


def test_action_gap_prevents_quality_stop_even_when_one_dimension_has_evidence() -> None:
    matrix = build_coverage_matrix(
        _domain_map(),
        [_external("define_scope")],
        archetype=_archetype(),
    )
    budget = DynamicResearchBudget(max_gap_iterations=2)

    stop, reason = research_should_stop(matrix, budget, evidence_growth=0.5)

    assert stop is False
    assert reason == "continue_for_coverage_gaps"


def test_titles_and_gap_placeholders_do_not_create_substantive_coverage() -> None:
    matrix = build_coverage_matrix(_domain_map(), [], archetype=_archetype())
    outline = ReportOutline(
        query_archetype="limitations_and_challenges",
        sections=[
            SectionContract(
                id="section-1",
                title="Operational constraints",
                function="limitations",
                dimension_ids=["operations"],
            )
        ],
    )

    quality = evaluate_generalized_research_quality(
        "## 回答\n\n### Operational constraints\n\n证据不足，待核验。",
        outline,
        matrix,
    )

    assert quality["scores"]["dimension_coverage"] < 2


def test_section_evidence_pack_categorizes_evidence_and_forbids_unsupported_facts() -> None:
    evidence = [
        _external("define_scope"),
        _external("identify_limitations", role="boundary"),
        _external("assess_impact", role="counterexample"),
        _model("identify_limitations"),
    ]
    matrix = build_coverage_matrix(_domain_map(), evidence, archetype=_archetype())
    outline = ReportOutline(
        query_archetype="limitations_and_challenges",
        sections=[
            SectionContract(
                id="section-1",
                title="Operational constraints",
                function="limitations",
                dimension_ids=["operations"],
                questions_to_answer=["What limits GIS automation?"],
            )
        ],
    )
    drafts = build_section_drafts(outline, evidence, coverage_matrix=matrix)
    packs = build_section_evidence_packs(
        outline,
        evidence,
        coverage_matrix=matrix,
        drafts=drafts,
    )

    pack = packs[0]
    assert [item["id"] for item in pack.direct_evidence] == ["external-define_scope"]
    assert [item["id"] for item in pack.boundary_evidence] == ["external-identify_limitations"]
    assert [item["id"] for item in pack.counterexamples] == ["external-assess_impact"]
    assert set(pack.required_actions) == set(_archetype().expected_research_actions)
    assert all(len(item["verbatim_quote"]) <= 1200 for item in pack.direct_evidence)
    assert pack.allowed_citations


def test_partial_batch_synthesis_discards_all_model_prose_and_uses_evidence_fallback() -> None:
    refs = [
        "[Web:https://official.example/eu]",
        "[Web:https://official.example/us]",
    ]
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[
            SectionContract(
                id="section-1",
                title="EU",
                function="comparison",
                length_budget=600,
            ),
            SectionContract(
                id="section-2",
                title="US",
                function="comparison",
                length_budget=600,
            ),
        ],
    )
    drafts = [
        SectionDraft(
            section_id=f"section-{index + 1}",
            title=title,
            claims=[SectionClaim(
                id=f"claim-{index + 1}",
                text=f"Verified {title} obligation.",
                claim_type="external_fact",
                citation_refs=[refs[index]],
                externally_supported=True,
            )],
            coverage_status="covered",
            verified=True,
        )
        for index, title in enumerate(("EU", "US"))
    ]
    packs = [
        SectionEvidencePack(
            section_id=f"section-{index + 1}",
            direct_evidence=[{"id": f"claim-{index + 1}"}],
            allowed_citations=[refs[index]],
        )
        for index in range(2)
    ]

    class PartialModel:
        def invoke(self, messages):
            return SimpleNamespace(content=(
                '{"sections":[{"section_id":"section-1",'
                '"content":"Unsupported model prose '
                + refs[0]
                + '"}]}'
            ))

    contents, error = _synthesize_sections_batch(
        {
            "query": "compare policies",
            "_deadline_at": time.time() + 120,
            "_research_budget": {"timeout_seconds": 240},
        },
        PartialModel(),
        outline,
        drafts,
        packs,
        existing_drafts={},
        revision_context="",
    )

    assert error == ""
    assert "Unsupported model prose" not in contents["section-1"]
    assert "Verified EU obligation" in contents["section-1"]
    assert "Verified US obligation" in contents["section-2"]


def test_complete_but_uncited_batch_synthesis_uses_evidence_fallback() -> None:
    ref = "[Web:https://official.example/policy]"
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[SectionContract(
            id="section-1",
            title="Policy",
            function="comparison",
            length_budget=600,
        )],
    )
    draft = SectionDraft(
        section_id="section-1",
        title="Policy",
        claims=[SectionClaim(
            id="claim-1",
            text="Verified policy obligation.",
            claim_type="external_fact",
            citation_refs=[ref],
            externally_supported=True,
        )],
        coverage_status="covered",
        verified=True,
    )
    pack = SectionEvidencePack(
        section_id="section-1",
        direct_evidence=[{"id": "claim-1"}],
        allowed_citations=[ref],
    )

    class UngroundedModel:
        def invoke(self, messages):
            return SimpleNamespace(content=(
                '{"sections":[{"section_id":"section-1",'
                '"content":"Verified policy obligation'
                + ref
                + '. The policy is already binding across every downstream system."}]}'
            ))

    contents, error = _synthesize_sections_batch(
        {
            "query": "compare policies",
            "_deadline_at": time.time() + 120,
            "_research_budget": {"timeout_seconds": 240},
        },
        UngroundedModel(),
        outline,
        [draft],
        [pack],
        existing_drafts={},
        revision_context="",
    )

    assert error == ""
    assert contents["section-1"] == f"- Verified policy obligation.{ref}"


def test_global_direct_answer_rejects_citation_laundering_without_discarding_valid_cross_synthesis() -> None:
    ref = "[Web:https://official.example/eu]"
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[SectionContract(
            id="section-1",
            title="EU",
            function="comparison",
            length_budget=600,
        )],
    )
    draft = SectionDraft(
        section_id="section-1",
        title="EU",
        claims=[SectionClaim(
            id="claim-1",
            text="The official EU instrument defines a transparency obligation.",
            claim_type="external_fact",
            citation_refs=[ref],
            externally_supported=True,
        )],
        coverage_status="covered",
        verified=True,
    )

    class LaunderedDirectModel:
        def invoke(self, messages):
            return SimpleNamespace(content=(
                '{"direct_answer":"The EU instrument defines a transparency obligation '
                + ref
                + '; every comparable jurisdiction has already adopted the same binding rule.",'
                '"cross_dimension_synthesis":"The verified EU section establishes the '
                'available comparison baseline '
                + ref
                + '."}'
            ))

    direct, cross, error = _synthesize_global_layers(
        {"query": "compare policies", "_deadline_at": time.time() + 120},
        LaunderedDirectModel(),
        outline,
        [draft],
        [{"evidence_refs": [ref]}],
        revision_context="",
    )

    assert error == ""
    assert "every comparable jurisdiction" not in direct
    assert direct == f"The official EU instrument defines a transparency obligation.{ref}"
    assert "available comparison baseline" in cross


def test_global_cross_synthesis_rejects_uncited_sentence_without_discarding_valid_direct_answer() -> None:
    ref = "[Web:https://official.example/us]"
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[SectionContract(
            id="section-1",
            title="US",
            function="comparison",
            length_budget=600,
        )],
    )
    draft = SectionDraft(
        section_id="section-1",
        title="US",
        claims=[SectionClaim(
            id="claim-1",
            text="The official US instrument defines a reporting mechanism.",
            claim_type="external_fact",
            citation_refs=[ref],
            externally_supported=True,
        )],
        coverage_status="covered",
        verified=True,
    )

    class LaunderedCrossModel:
        def invoke(self, messages):
            return SimpleNamespace(content=(
                '{"direct_answer":"The official US instrument defines a reporting mechanism '
                + ref
                + '.",'
                '"cross_dimension_synthesis":"The verified US section supplies one comparison '
                'point '
                + ref
                + '. It proves that disclosure duties always reduce deployment risk."}'
            ))

    direct, cross, error = _synthesize_global_layers(
        {"query": "compare policies", "_deadline_at": time.time() + 120},
        LaunderedCrossModel(),
        outline,
        [draft],
        [{"evidence_refs": [ref]}],
        revision_context="",
    )

    assert error == ""
    assert "defines a reporting mechanism" in direct
    assert "always reduce deployment risk" not in cross
    assert cross.startswith("本轮可核验材料覆盖US")


def test_cross_jurisdiction_fallback_compares_representative_supported_mechanisms() -> None:
    draft = SectionDraft(
        section_id="section-cross",
        title="跨司法辖区：共同基线、比较轴与可核验差异",
        claims=[
            SectionClaim(
                id="eu",
                text="EU providers must publish technical documentation.",
                claim_type="external_fact",
                citation_refs=["[Web:https://europa.eu/policy]"],
                externally_supported=True,
            ),
            SectionClaim(
                id="us",
                text="The US notice proposes a reporting requirement.",
                claim_type="external_fact",
                citation_refs=["[Web:https://bis.gov/policy]"],
                externally_supported=True,
            ),
            SectionClaim(
                id="cn",
                text="提供者应当对生成内容进行标识。",
                claim_type="external_fact",
                citation_refs=["[Web:https://cac.gov.cn/policy]"],
                externally_supported=True,
            ),
        ],
        verified=True,
    )

    content = _fallback_section_content(draft)

    assert "**欧盟：**" in content
    assert "**美国：**" in content
    assert "**中国：**" in content
    assert "**模型分析：**" in content
