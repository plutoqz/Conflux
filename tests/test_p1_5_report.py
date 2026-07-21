from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conflux.research_generalization import (
    build_report_outline,
    build_section_drafts,
    evaluate_generalized_research_quality,
)
from conflux.research_protocol import (
    CoverageDimension,
    CoverageMatrix,
    DomainMap,
    QueryArchetype,
    ReportOutline,
    ResearchDimension,
    SectionClaim,
    SectionContract,
    SectionDraft,
)


ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "architecture" / "p1_5"
EVAL_SCRIPT = ROOT / "scripts" / "eval_p1_5.py"
DATASET = ROOT / "data" / "p1_5_research_eval.yaml"


def _domain_and_coverage() -> tuple[DomainMap, CoverageMatrix]:
    domain_map = DomainMap(
        scope="compare two systems under operational constraints",
        dimensions=[
            ResearchDimension(
                id="performance",
                name="Performance and scale",
                importance=0.9,
                questions_to_answer=["How do the systems behave under load?"],
                expected_evidence_types=["benchmark"],
            ),
            ResearchDimension(
                id="reliability",
                name="Failure recovery and reliability",
                importance=0.95,
                questions_to_answer=["Which failures are recoverable?"],
                expected_evidence_types=["technical_documentation"],
            ),
        ],
    )
    coverage = CoverageMatrix(
        dimensions=[
            CoverageDimension(
                dimension_id="performance",
                status="covered",
                body_evidence=True,
                high_authority_source=True,
                evidence_ids=["e-performance"],
                source_ids=["benchmark-a"],
                evidence_count=1,
                saturation=0.9,
            ),
            CoverageDimension(
                dimension_id="reliability",
                status="partial",
                body_evidence=True,
                high_authority_source=True,
                evidence_ids=["e-reliability"],
                source_ids=["docs-a"],
                evidence_count=1,
                saturation=0.55,
                gap_summary=["independent recovery evidence"],
            ),
        ],
        overall_coverage=0.75,
        high_importance_coverage=0.75,
        saturation=0.72,
    )
    return domain_map, coverage


def test_dynamic_outline_uses_discovered_dimension_titles() -> None:
    domain_map, coverage = _domain_and_coverage()
    archetype = QueryArchetype(
        type="comparison",
        expected_research_actions=["compare_evidence"],
        required_synthesis_functions=["comparative_synthesis", "tradeoff_synthesis"],
    )

    outline = build_report_outline(
        "Compare the systems.",
        archetype,
        domain_map,
        coverage,
        user_intent="compare evidence only",
    )

    assert [section.title for section in outline.sections] == [
        "Performance and scale",
        "Failure recovery and reliability",
    ]
    assert [section.dimension_ids for section in outline.sections] == [
        ["performance"],
        ["reliability"],
    ]
    assert outline.scope == domain_map.scope


def test_recommendation_claims_are_conditional_on_user_intent() -> None:
    domain_map, coverage = _domain_and_coverage()
    comparison = QueryArchetype(type="comparison")
    solution = QueryArchetype(type="solution_design")

    comparison_outline = build_report_outline(
        "Compare the systems.",
        comparison,
        domain_map,
        coverage,
        user_intent="compare evidence only",
    )
    requested_outline = build_report_outline(
        "Compare the systems.",
        comparison,
        domain_map,
        coverage,
        user_intent="recommend one option for deployment",
    )
    solution_outline = build_report_outline(
        "Design a recoverable system.",
        solution,
        domain_map,
        coverage,
        user_intent="design an implementation",
    )

    assert all(
        "recommendation" not in section.required_claim_types
        for section in comparison_outline.sections
    )
    assert all(
        "recommendation" in section.required_claim_types
        for section in requested_outline.sections
    )
    assert all(
        "recommendation" in section.required_claim_types
        for section in solution_outline.sections
    )


def test_section_drafts_only_resolve_evidence_from_their_dimensions() -> None:
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[
            SectionContract(
                id="section-performance",
                title="Performance",
                function="evidence_comparison",
                dimension_ids=["performance"],
            ),
            SectionContract(
                id="section-reliability",
                title="Reliability",
                function="evidence_comparison",
                dimension_ids=["reliability"],
            ),
        ],
    )
    coverage = CoverageMatrix(
        dimensions=[
            CoverageDimension(dimension_id="performance", status="covered"),
            CoverageDimension(dimension_id="reliability", status="covered"),
        ]
    )
    evidence = [
        {
            "id": "e-performance",
            "dimension_id": "performance",
            "source": "Web",
            "content_kind": "html_body",
            "verbatim_quote": "The benchmark records the throughput result.",
            "claim": "System A sustains the documented throughput.",
            "evidence_refs": ["[1]"],
            "confidence": 0.9,
        },
        {
            "id": "e-reliability",
            "dimension_id": "reliability",
            "source": "RAG",
            "content_kind": "full_text",
            "verbatim_quote": "The implementation resumes from a durable checkpoint.",
            "claim": "System B documents checkpoint recovery.",
            "evidence_refs": ["[2]"],
            "confidence": 0.85,
        },
        {
            "id": "e-unrelated",
            "dimension_id": "governance",
            "source": "Web",
            "content_kind": "html_body",
            "verbatim_quote": "An unrelated governance fact.",
            "claim": "This claim belongs to no section in the outline.",
            "evidence_refs": ["[3]"],
        },
    ]

    drafts = build_section_drafts(outline, evidence, coverage_matrix=coverage)
    claims_by_section = {
        draft.section_id: {claim.id for claim in draft.claims} for draft in drafts
    }

    assert claims_by_section == {
        "section-performance": {"e-performance"},
        "section-reliability": {"e-reliability"},
    }
    assert all(claim.externally_supported for draft in drafts for claim in draft.claims)


def test_report_traceability_fixture_has_no_orphan_contracts_drafts_or_evidence() -> None:
    payload = json.loads((FIXTURES / "report_traceability.json").read_text(encoding="utf-8"))
    coverage = CoverageMatrix.from_dict(payload["coverage_matrix"])
    contracts = [
        SectionContract.from_dict(item, index=index)
        for index, item in enumerate(payload["section_contracts"])
    ]
    drafts = [SectionDraft.from_dict(item) for item in payload["section_drafts"]]
    coverage_by_dimension = coverage.by_dimension()
    contract_by_id = {contract.id: contract for contract in contracts}
    draft_by_id = {draft.section_id: draft for draft in drafts}

    assert set(contract_by_id) == set(draft_by_id)
    assert set(payload["report_outline"]["sections"]) == set(contract_by_id)

    for section_id, draft in draft_by_id.items():
        contract = contract_by_id[section_id]
        assert set(draft.dimension_ids) <= set(contract.dimension_ids)
        allowed_evidence = {
            evidence_id
            for dimension_id in draft.dimension_ids
            for evidence_id in coverage_by_dimension[dimension_id].evidence_ids
        }
        assert all(set(claim.evidence_ids) <= allowed_evidence for claim in draft.claims)


def test_quality_ignores_raw_length_and_rewards_substantive_traced_sections() -> None:
    outline = ReportOutline(
        query_archetype="comparison",
        sections=[
            SectionContract(
                id="section-mechanism",
                title="Mechanism",
                function="evidence_comparison",
                dimension_ids=["mechanism"],
            ),
            SectionContract(
                id="section-boundary",
                title="Boundary",
                function="evidence_comparison",
                dimension_ids=["boundary"],
            ),
        ],
        cross_section_synthesis=[
            "comparative_synthesis",
            "tradeoff_synthesis",
            "boundary_synthesis",
        ],
    )
    coverage = CoverageMatrix(
        dimensions=[
            CoverageDimension(dimension_id="mechanism", status="covered"),
            CoverageDimension(dimension_id="boundary", status="covered"),
        ],
        overall_coverage=1.0,
        high_importance_coverage=1.0,
        saturation=0.9,
    )
    short_filler = "Generic filler contains no research substance."
    long_filler = "Generic filler contains no research substance. " * 500

    short_score = evaluate_generalized_research_quality(short_filler, outline, coverage)
    long_score = evaluate_generalized_research_quality(long_filler, outline, coverage)

    assert len(long_filler) > len(short_filler) * 100
    assert long_score["overall"] == short_score["overall"]
    assert long_score["scores"] == short_score["scores"]

    claims = [
        SectionClaim(
            id="claim-a",
            text="The mechanism depends on a durable checkpoint.",
            claim_type="external_fact",
            evidence_ids=["e-a"],
            citation_refs=["[1]"],
            externally_supported=True,
        ),
        SectionClaim(
            id="claim-b",
            text="The boundary changes under regional failure.",
            claim_type="external_fact",
            evidence_ids=["e-b"],
            citation_refs=["[2]"],
            externally_supported=True,
        ),
    ]
    drafts = [
        SectionDraft(
            section_id="section-mechanism",
            title="Mechanism",
            dimension_ids=["mechanism"],
            claims=claims,
            content=(
                "The mechanism works because the durable checkpoint constrains replay and "
                "depends on an implementation-specific recovery sequence."
            ),
            coverage_status="covered",
            verified=True,
        ),
        SectionDraft(
            section_id="section-boundary",
            title="Boundary",
            dimension_ids=["boundary"],
            claims=claims,
            content=(
                "The boundary condition limits deployment during a regional outage; the case "
                "benchmark exposes a trade-off and uncertainty that requires validation."
            ),
            coverage_status="covered",
            verified=True,
        ),
    ]
    substantive_report = "\n".join(
        [
            "# Mechanism",
            "The mechanism works because the durable checkpoint constrains replay; the implementation depends on a verified recovery sequence.",
            "A benchmark case contrasts the alternatives and identifies a deployment trade-off under load.",
            "# Boundary",
            "The boundary condition limits recovery during regional failure, creating uncertainty and a documented limitation.",
            "The implementation case provides a benchmark, while the contrast exposes a complementary validation path.",
        ]
    )

    substantive = evaluate_generalized_research_quality(
        substantive_report,
        outline,
        coverage,
        section_drafts=drafts,
    )

    assert substantive["overall"] > long_score["overall"]
    assert substantive["section_traceability_ratio"] == 1.0
    assert substantive["scores"]["evidence_density"] == 5


def _run_eval(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_offline_evaluator_writes_machine_and_human_readable_results(tmp_path: Path) -> None:
    result = _run_eval("--out-dir", str(tmp_path))

    assert result.returncode == 0, result.stdout + result.stderr
    json_path = tmp_path / "p1_5_eval.json"
    markdown_path = tmp_path / "p1_5_eval.md"
    assert json_path.exists()
    assert markdown_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["real_api"] is False
    assert all(gate["passed"] for gate in payload["gates"].values())


@pytest.mark.parametrize("corruption", ["dataset", "fixture"])
def test_offline_evaluator_returns_nonzero_for_corrupt_inputs(
    tmp_path: Path, corruption: str
) -> None:
    output_dir = tmp_path / "output"
    dataset = DATASET
    fixtures = FIXTURES

    if corruption == "dataset":
        dataset = tmp_path / "broken.yaml"
        dataset.write_text(
            "- id: broken\n  domain: one\n  query: incomplete\n  archetype: unknown\n",
            encoding="utf-8",
        )
    else:
        fixtures = tmp_path / "fixtures"
        shutil.copytree(FIXTURES, fixtures)
        (fixtures / "source_scenarios.json").write_text(
            json.dumps({"scenarios": []}),
            encoding="utf-8",
        )

    result = _run_eval(
        "--dataset",
        str(dataset),
        "--fixtures-dir",
        str(fixtures),
        "--out-dir",
        str(output_dir),
    )

    assert result.returncode != 0
    payload = json.loads((output_dir / "p1_5_eval.json").read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["errors"]
