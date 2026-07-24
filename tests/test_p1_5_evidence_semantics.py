from __future__ import annotations

from conflux.evidence import build_evidence_graph_from_results
from conflux.research_generalization import (
    build_coverage_matrix,
    build_section_drafts,
    build_section_evidence_packs,
    build_scope_contract,
    gate_evidence_items,
)
from conflux.research_protocol import (
    DomainMap,
    QueryArchetype,
    ReportOutline,
    ResearchDimension,
    SectionContract,
)
from conflux.source_status import AgentClaim, SourceResult


def _scope():
    return build_scope_contract("GIS处理自动化研究目前有哪些瓶颈？")


def test_off_domain_limitations_are_not_direct_support() -> None:
    items = [
        {
            "id": f"off-{index}",
            "source": "RAG",
            "claim": title + " describes limitations in another domain.",
            "verbatim_quote": title + " reports limitations and coordination failures in its own domain.",
            "document_title": title,
            "content_kind": "local_full_text",
            "relevance": 0.95,
            "directness": 0.9,
            "evidence_class": "preprint",
        }
        for index, title in enumerate((
            "DuMate DeepResearch",
            "Multi-agent transparency",
            "AI-assisted social science",
            "Kubernetes root-cause analysis",
        ))
    ]

    gated = gate_evidence_items(items, _scope())

    assert {item["evidence_role"] for item in gated} <= {"analogy", "discovery_only"}
    assert all(not item["evidence_gate_passed"] for item in gated)


def test_geospatial_evidence_passes_and_page_chrome_fails() -> None:
    gated = gate_evidence_items(
        [
            {
                "id": "geo",
                "source": "RAG",
                "claim": "GeoNatureAgent automates geospatial data processing workflows.",
                "verbatim_quote": "GeoNatureAgent automates geospatial data processing workflows with tool validation.",
                "document_title": "GeoNatureAgent",
                "content_kind": "local_full_text",
                "relevance": 0.82,
                "directness": 0.9,
                "evidence_class": "preprint",
            },
            {
                "id": "sage-chrome",
                "source": "Web",
                "claim": "Recommendation page chrome",
                "verbatim_quote": "Show details Hide details Show details Hide details accept all cookies and continue.",
                "document_title": "SAGE recommendation page",
                "content_kind": "html",
                "relevance": 0.9,
                "directness": 0.9,
                "evidence_class": "community_content",
            },
        ],
        _scope(),
    )

    by_id = {item["id"]: item for item in gated}
    assert by_id["geo"]["evidence_role"] == "direct_support"
    assert by_id["geo"]["evidence_gate_passed"] is True
    assert by_id["sage-chrome"]["body_valid"] is False
    assert by_id["sage-chrome"]["evidence_role"] == "discovery_only"


def test_chinese_scope_accepts_specific_english_alias_but_not_generic_transparency() -> None:
    scope = build_scope_contract(
        "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？"
    )
    gated = gate_evidence_items(
        [
            {
                "id": "gpai",
                "source": "RAG",
                "claim": "Providers of general-purpose AI models must provide technical documentation.",
                "verbatim_quote": (
                    "Providers of general-purpose AI models must maintain technical documentation and provide "
                    "information to downstream providers."
                ),
                "document_title": "General-purpose AI obligations under the EU AI Act",
                "content_kind": "local_full_text",
                "directness": 0.9,
                "evidence_class": "authoritative_document",
            },
            {
                "id": "generic",
                "source": "RAG",
                "claim": "A multi-agent benchmark reports transparency limitations.",
                "verbatim_quote": (
                    "The benchmark reports transparency limitations in coordination among "
                    "multiple software agents."
                ),
                "document_title": "Multi-agent coordination benchmark",
                "content_kind": "local_full_text",
                "directness": 0.9,
                "evidence_class": "peer_reviewed",
            },
        ],
        scope,
    )

    by_id = {item["id"]: item for item in gated}
    assert by_id["gpai"]["domain_relevance"] >= 0.7
    assert by_id["gpai"]["evidence_gate_passed"] is True
    assert by_id["generic"]["domain_relevance"] < 0.7
    assert by_id["generic"]["evidence_gate_passed"] is False


def test_captcha_access_page_cannot_pass_body_gate() -> None:
    gated = gate_evidence_items(
        [{
            "id": "captcha",
            "source": "Web",
            "claim": "Foundation model transparency reporting requirements.",
            "verbatim_quote": (
                "If you are experiencing issues with the CAPTCHA, use Site Help "
                "to request a wider IP range."
            ),
            "document_title": "Federal Register Request Access",
            "content_kind": "html",
            "directness": 0.9,
            "evidence_class": "authoritative_document",
        }],
        build_scope_contract("基础模型透明度义务有哪些差异？"),
    )

    assert gated[0]["body_valid"] is False
    assert gated[0]["evidence_gate_passed"] is False


def test_dimension_specific_actions_can_close_single_source_official_cell() -> None:
    scope = build_scope_contract(
        "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？"
    )
    dimension = ResearchDimension(
        id="jurisdiction-us",
        name="美国：义务、适用范围与执行状态",
        questions_to_answer=["美国前沿 AI 开发者适用哪些报告要求？"],
        required_actions=[
            "define_comparison_scope",
            "compare_mechanisms",
            "compare_applicability",
        ],
        cross_validation_required=False,
        importance=0.9,
    )
    gated = gate_evidence_items(
        [{
            "id": "bis",
            "source": "Web",
            "subquestion_id": "jurisdiction-us",
            "claim": (
                "The proposed rule requires frontier AI developers and compute providers "
                "to report development and security information."
            ),
            "verbatim_quote": (
                "The proposed rule requires frontier AI developers and compute providers "
                "to report development and security information to the federal government."
            ),
            "document_title": "BIS frontier AI reporting requirements",
            "content_kind": "html",
            "directness": 0.9,
            "authority": 0.9,
            "evidence_class": "authoritative_document",
            "evidence_refs": ["[Web:https://bis.gov/rule]"],
        }],
        scope,
    )

    matrix = build_coverage_matrix(
        DomainMap(scope=scope.original_query, dimensions=[dimension]),
        gated,
        archetype=QueryArchetype(
            type="comparison",
            expected_research_actions=[
                "define_comparison_scope",
                "establish_common_baseline",
                "identify_comparison_axes",
                "compare_mechanisms",
                "compare_evidence",
                "compare_applicability",
                "identify_tradeoffs",
            ],
        ),
    )

    assert matrix.dimensions[0].status == "covered"
    assert matrix.high_importance_coverage == 1.0


def test_official_jurisdiction_object_anchor_accepts_broad_uk_policy_evidence() -> None:
    scope = build_scope_contract(
        "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？"
    )
    gated = gate_evidence_items(
        [
            {
                "id": "uk-policy",
                "source": "Web",
                "subquestion_id": "jurisdiction-uk",
                "claim": (
                    "Existing regulators will implement cross-sectoral AI principles."
                ),
                "verbatim_quote": (
                    "Existing regulators will be expected to implement the framework underpinned "
                    "by cross-sectoral principles including appropriate transparency and explainability."
                ),
                "document_title": "A pro-innovation approach to AI regulation",
                "url": "https://www.gov.uk/government/publications/ai-regulation/white-paper",
                "content_kind": "html",
                "directness": 0.9,
                "authority": 0.9,
                "evidence_refs": ["[Web:https://www.gov.uk/government/publications/ai-regulation/white-paper]"],
                "evidence_class": "authoritative_document",
            },
            {
                "id": "unrelated-uk",
                "source": "Web",
                "subquestion_id": "jurisdiction-uk",
                "claim": "The department published annual tax statistics.",
                "verbatim_quote": "The department published annual tax statistics for the current year.",
                "document_title": "Annual tax statistics",
                "url": "https://www.gov.uk/government/statistics/annual-tax-statistics",
                "content_kind": "html",
                "directness": 0.9,
                "evidence_class": "authoritative_document",
            },
        ],
        scope,
    )

    by_id = {item["id"]: item for item in gated}
    assert by_id["uk-policy"]["domain_relevance"] >= 0.7
    assert by_id["uk-policy"]["evidence_gate_passed"] is True
    assert by_id["unrelated-uk"]["domain_relevance"] < 0.7
    assert by_id["unrelated-uk"]["evidence_gate_passed"] is False
    matrix = build_coverage_matrix(
        DomainMap(scope=scope.original_query, dimensions=[ResearchDimension(
            id="jurisdiction-uk",
            name="UK transparency policy",
            required_actions=[
                "define_comparison_scope",
                "compare_mechanisms",
                "compare_applicability",
            ],
            cross_validation_required=False,
            importance=0.9,
        )]),
        gated,
        archetype=QueryArchetype(type="comparison"),
    )
    assert matrix.dimensions[0].status == "covered"


def test_cross_jurisdiction_dimension_aggregates_object_level_evidence() -> None:
    scope = build_scope_contract(
        "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？"
    )
    dimension = ResearchDimension(
        id="jurisdiction-cross-comparison",
        name="跨司法辖区比较",
        required_actions=[
            "establish_common_baseline",
            "identify_comparison_axes",
            "compare_mechanisms",
        ],
        cross_validation_required=True,
        importance=0.9,
    )
    evidence = gate_evidence_items(
        [
            {
                "id": "eu",
                "source": "Web",
                "subquestion_id": "jurisdiction-eu",
                "claim": "GPAI providers must publish transparency documentation.",
                "verbatim_quote": "GPAI providers must publish transparency documentation.",
                "document_title": "General-purpose AI obligations under the AI Act",
                "url": "https://digital-strategy.ec.europa.eu/gpai-obligations",
                "content_kind": "html",
                "directness": 0.9,
                "authority": 0.9,
                "evidence_class": "authoritative_document",
                "source_identity": "eu-official",
                "research_actions": list(dimension.required_actions),
            },
            {
                "id": "us",
                "source": "Web",
                "subquestion_id": "jurisdiction-us",
                "claim": "Frontier AI developers must report specified information.",
                "verbatim_quote": "Frontier AI developers must report specified information.",
                "document_title": "BIS frontier AI reporting requirements",
                "url": "https://www.bis.gov/frontier-ai-reporting",
                "content_kind": "html",
                "directness": 0.9,
                "authority": 0.9,
                "evidence_class": "authoritative_document",
                "source_identity": "us-official",
                "research_actions": list(dimension.required_actions),
            },
        ],
        scope,
    )
    matrix = build_coverage_matrix(
        DomainMap(scope=scope.original_query, dimensions=[dimension]),
        evidence,
        archetype=QueryArchetype(type="comparison"),
    )

    row = matrix.dimensions[0]
    assert set(row.evidence_ids) == {"eu", "us"}
    assert row.status == "covered"
    assert matrix.high_importance_coverage == 1.0
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[SectionContract(
            id="section-cross",
            title="Cross-jurisdiction comparison",
            function="comparison",
            dimension_ids=["jurisdiction-cross-comparison"],
        )],
    )
    drafts = build_section_drafts(outline, evidence, coverage_matrix=matrix)
    packs = build_section_evidence_packs(
        outline,
        evidence,
        coverage_matrix=matrix,
        drafts=drafts,
    )
    assert {claim.id for claim in drafts[0].claims} == {"eu", "us"}
    assert {item["id"] for item in packs[0].direct_evidence} == {"eu", "us"}


def test_rejected_analogy_cannot_raise_dimension_coverage() -> None:
    domain = DomainMap(
        scope="GIS processing automation",
        dimensions=[ResearchDimension(
            id="limits",
            name="Bottlenecks",
            importance=0.9,
            terminology=["GIS"],
        )],
    )
    gated = gate_evidence_items(
        [{
            "id": "off",
            "source": "RAG",
            "subquestion_id": "limits",
            "claim": "Kubernetes root-cause analysis has operational bottlenecks.",
            "verbatim_quote": "Kubernetes root-cause analysis has operational bottlenecks in cluster diagnosis.",
            "content_kind": "local_full_text",
            "relevance": 0.95,
            "directness": 0.95,
            "evidence_class": "preprint",
        }],
        _scope(),
    )

    matrix = build_coverage_matrix(domain, gated)

    assert matrix.dimensions[0].status == "evidence_scarce"
    assert matrix.dimensions[0].evidence_count == 0


def test_pages_from_one_pdf_count_as_one_independent_source() -> None:
    result = SourceResult(
        source="RAG",
        status="success",
        content="two relevant pages",
        evidence_class="preprint",
        claims=[
            AgentClaim(
                claim=f"Claim from page {page} with enough body detail.",
                source="RAG",
                verbatim_quote=f"The paper provides direct body evidence on page {page} for this claim.",
                paper_id=f"papers/2606.12848.pdf#page-{page}",
                evidence_refs=[f"[RAG:papers/2606.12848.pdf#page-{page}#chunk-1]"],
                evidence_class="preprint",
                relevance=0.9,
                directness=0.9,
                content_kind="local_full_text",
            )
            for page in (1, 16)
        ],
    )

    graph = build_evidence_graph_from_results({"RAG": result})

    assert {node.paper_id for node in graph.nodes.values()} == {"papers/2606.12848"}
    assert graph.consensus_summary()["independent_external_sources"] == 1


def test_evidence_item_round_trip_preserves_page_numbers_and_gate_fields() -> None:
    item = AgentClaim.from_dict({
        "claim": "A page-specific evidence claim.",
        "source": "RAG",
        "page_start": "7",
        "page_end": 8,
        "domain_relevance": 0.91,
        "claim_entailment": 0.88,
        "evidence_role": "direct_support",
        "source_identity": "arxiv:2606.12848",
        "body_valid": True,
    })

    assert item.page_start == 7
    assert item.page_end == 8
    assert item.evidence_role == "direct_support"
    assert item.body_valid is True
