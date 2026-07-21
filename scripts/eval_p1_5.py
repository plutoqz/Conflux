"""Deterministic P1.5 generalized deep-research evaluation.

The default mode validates checked-in datasets, recorded planner outputs,
source-degradation fixtures, budget cases, report traceability, and protocol
round trips. It never calls a model, network provider, vector store, or PDF
extractor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


REQUIRED_ARCHETYPES = {
    "method_survey",
    "state_and_trends",
    "limitations_and_challenges",
    "comparison",
    "causal_mechanism",
    "solution_design",
    "evidence_review",
}
ARCHETYPE_ALIASES = {
    "status_trend": "state_and_trends",
    "limitations_challenges": "limitations_and_challenges",
}
REQUIRED_SOURCE_SCENARIOS = {
    "rag_success_web_success",
    "rag_no_evidence_web_success",
    "rag_failed_web_success",
    "rag_success_web_failed",
    "both_external_failed",
}
VALID_SOURCE_STATUSES = {"success", "no_evidence", "low_relevance", "failed"}
EXTERNAL_SOURCES = {"RAG", "Web"}
BODY_CONTENT_KINDS = {"full_text", "html_body", "pdf_body", "repository_body"}
ARCHETYPE_ACTIONS = {
    "method_survey": {
        "taxonomy_discovery", "mechanism_analysis", "representative_implementations",
        "applicability", "limitations", "maturity", "combination_relations",
    },
    "state_and_trends": {
        "baseline_state", "recent_changes", "adoption_drivers", "trajectory",
        "uncertainty_analysis",
    },
    "limitations_and_challenges": {
        "scope_definition", "failure_modes", "root_causes", "impacts", "mitigations",
        "open_questions",
    },
    "comparison": {
        "comparison_axes", "per_target_evidence", "tradeoffs", "boundary_conditions",
        "conflict_analysis",
    },
    "causal_mechanism": {
        "causal_chain", "mechanism_analysis", "confounders", "counterevidence",
        "boundary_conditions",
    },
    "solution_design": {
        "requirements", "architecture", "alternatives", "implementation_steps", "risks",
        "validation",
    },
    "evidence_review": {
        "evidence_hierarchy", "consensus", "disagreement", "study_quality", "evidence_gaps",
    },
}


def canonical_archetype(value: Any) -> str:
    normalized = str(value or "").strip().casefold()
    return ARCHETYPE_ALIASES.get(normalized, normalized)


def load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"P1.5 dataset must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"P1.5 fixture must be a JSON object: {path}")
    return payload


def validate_dataset(cases: list[dict[str, Any]], scenario_ids: set[str]) -> dict[str, Any]:
    errors: list[str] = []
    ids = [str(case.get("id") or "").strip() for case in cases]
    if len(cases) < 14:
        errors.append(f"dataset must contain at least 14 covering cases: {len(cases)}")
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        errors.append("dataset case ids must be non-empty and unique")

    domains: set[str] = set()
    archetypes: list[str] = []
    breadths: set[str] = set()
    temporalities: set[str] = set()
    rag_states: set[str] = set()
    selected_scenarios: set[str] = set()
    recommendation_cases = 0
    for case in cases:
        case_id = str(case.get("id") or "unknown")
        domain = str(case.get("domain") or "").strip()
        query = str(case.get("query") or "").strip()
        archetype = canonical_archetype(case.get("archetype"))
        breadth = str(case.get("breadth") or "").strip()
        temporality = str(case.get("temporality") or "").strip()
        rag_coverage = str(case.get("rag_coverage") or "").strip()
        scenario = str(case.get("source_scenario") or "").strip()
        actions = {str(item) for item in case.get("expected_research_actions") or []}
        dimensions = [str(item) for item in case.get("expected_dimensions") or [] if str(item)]
        recommendations = bool(case.get("requires_recommendation"))

        domains.add(domain)
        archetypes.append(archetype)
        breadths.add(breadth)
        temporalities.add(temporality)
        rag_states.add(rag_coverage)
        selected_scenarios.add(scenario)
        recommendation_cases += int(recommendations)

        if not domain or not query:
            errors.append(f"{case_id}: domain and query are required")
        if archetype not in REQUIRED_ARCHETYPES:
            errors.append(f"{case_id}: invalid archetype {archetype!r}")
        if breadth not in {"broad", "narrow"}:
            errors.append(f"{case_id}: breadth must be broad or narrow")
        if temporality not in {"current", "stable"}:
            errors.append(f"{case_id}: temporality must be current or stable")
        if rag_coverage not in {"covered", "none"}:
            errors.append(f"{case_id}: rag_coverage must be covered or none")
        if scenario not in scenario_ids:
            errors.append(f"{case_id}: unknown source scenario {scenario!r}")
        required_actions = ARCHETYPE_ACTIONS.get(archetype, set())
        missing_actions = sorted(required_actions - actions)
        if missing_actions:
            errors.append(f"{case_id}: missing research actions {', '.join(missing_actions)}")
        minimum_dimensions = 6 if breadth == "broad" else 4
        if len(set(dimensions)) < minimum_dimensions:
            errors.append(
                f"{case_id}: {breadth} case needs at least {minimum_dimensions} distinct dimensions"
            )
        if recommendations and archetype != "solution_design":
            errors.append(f"{case_id}: recommendations are only required by explicit solution intent")
        if archetype == "solution_design" and not recommendations:
            errors.append(f"{case_id}: explicit design query must request recommendations")

    if len(domains - {""}) < 6:
        errors.append(f"dataset must cover at least 6 domains: {len(domains - {''})}")
    if set(archetypes) != REQUIRED_ARCHETYPES:
        errors.append(
            "dataset archetype coverage mismatch: "
            + ", ".join(sorted(REQUIRED_ARCHETYPES - set(archetypes)))
        )
    if breadths != {"broad", "narrow"}:
        errors.append("dataset must cover broad and narrow questions")
    if temporalities != {"current", "stable"}:
        errors.append("dataset must cover current and stable knowledge")
    if rag_states != {"covered", "none"}:
        errors.append("dataset must cover RAG-covered and RAG-empty cases")
    missing_scenarios = sorted(REQUIRED_SOURCE_SCENARIOS - selected_scenarios)
    if missing_scenarios:
        errors.append("dataset does not select mandatory source scenarios: " + ", ".join(missing_scenarios))
    if recommendation_cases == 0 or recommendation_cases == len(cases):
        errors.append("dataset must contain both recommendation and non-recommendation intents")

    return _result(
        errors,
        {
            "case_count": len(cases),
            "domain_count": len(domains - {""}),
            "archetype_counts": dict(sorted(Counter(archetypes).items())),
            "breadth_counts": dict(sorted(Counter(str(case.get("breadth")) for case in cases).items())),
            "temporality_counts": dict(
                sorted(Counter(str(case.get("temporality")) for case in cases).items())
            ),
            "rag_coverage_counts": dict(
                sorted(Counter(str(case.get("rag_coverage")) for case in cases).items())
            ),
            "source_scenario_count": len(selected_scenarios),
        },
    )


def validate_planner_recordings(payload: dict[str, Any]) -> dict[str, Any]:
    from conflux.research_protocol import DomainMap, QueryArchetype

    errors: list[str] = []
    recordings = [item for item in payload.get("recordings") or [] if isinstance(item, dict)]
    lexicon_independent = 0
    for recording in recordings:
        recording_id = str(recording.get("id") or "unknown")
        archetype = QueryArchetype.from_dict(recording.get("query_archetype") or {})
        domain_map = DomainMap.from_dict(recording.get("domain_map") or {})
        expected = recording.get("expected") or {}
        dimension_ids = [item.id for item in domain_map.dimensions]
        dimension_set = set(dimension_ids)
        if not recording.get("query"):
            errors.append(f"{recording_id}: query is required")
        if archetype.type not in REQUIRED_ARCHETYPES:
            errors.append(f"{recording_id}: recording must resolve to a known archetype")
        if len(dimension_ids) != len(dimension_set) or any(not item for item in dimension_ids):
            errors.append(f"{recording_id}: dimension ids must be unique and non-empty")
        minimum = int(expected.get("minimum_major_dimensions") or 0)
        if len(domain_map.dimensions) < minimum:
            errors.append(f"{recording_id}: domain map recovered too few dimensions")
        for relation in domain_map.dimension_relations:
            endpoints = {str(relation.get("from") or ""), str(relation.get("to") or "")}
            if "" in endpoints or not endpoints <= dimension_set:
                errors.append(f"{recording_id}: dimension relation has a dangling endpoint")
        if expected.get("lexicon_independent"):
            lexicon_independent += 1
            if recording.get("domain_lexicon"):
                errors.append(f"{recording_id}: lexicon-independent fixture must have an empty lexicon")
            if expected.get("fallback_used"):
                errors.append(f"{recording_id}: generic discovery must not be reported as fallback")
        try:
            json.dumps(archetype.to_dict(), ensure_ascii=True)
            json.dumps(domain_map.to_dict(), ensure_ascii=True)
        except (TypeError, ValueError) as exc:
            errors.append(f"{recording_id}: protocol payload is not JSON serializable: {exc}")

    if len(recordings) < 2:
        errors.append("planner fixtures must include primary and composite archetype recordings")
    if lexicon_independent != len(recordings):
        errors.append("every planner recording must prove empty-lexicon discovery")
    return _result(
        errors,
        {
            "recording_count": len(recordings),
            "lexicon_independent_count": lexicon_independent,
        },
    )


def validate_budget_cases(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    hard_caps = payload.get("hard_caps") or {}
    cases = [item for item in payload.get("cases") or [] if isinstance(item, dict)]
    for key in (
        "max_dimensions", "max_final_evidence", "max_gap_iterations", "max_web_fetches",
        "max_output_tokens",
    ):
        if int(hard_caps.get(key) or 0) <= 0:
            errors.append(f"hard cap {key} must be positive")

    by_id = {str(case.get("id") or ""): case for case in cases}
    narrow = by_id.get("narrow_stable_healthy") or {}
    broad = by_id.get("broad_current_conflicted") or {}
    outage = by_id.get("broad_external_outage") or {}
    quick = by_id.get("quick_broad_is_bounded") or {}
    if len(by_id) != len(cases) or "" in by_id:
        errors.append("budget case ids must be unique and non-empty")
    if int((narrow.get("expected") or {}).get("max_dimensions") or 0) >= int(
        hard_caps.get("max_dimensions") or 0
    ):
        errors.append("narrow questions must stay below the global dimension hard cap")
    if int((broad.get("expected") or {}).get("min_final_evidence") or 0) < 20:
        errors.append("broad Deep case must reserve at least 20 final evidence items")
    if (broad.get("expected") or {}).get("web_budget_increases") is not True:
        errors.append("RAG-empty/Web-success broad case must shift budget to Web")
    if (outage.get("expected") or {}).get("completion_mode") != "model_analysis_only":
        errors.append("dual external outage must use labeled model-analysis-only completion")
    if (quick.get("expected") or {}).get("shall_not_match_deep_budget") is not True:
        errors.append("Quick broad fixture must remain distinguishable from Deep")
    if {str(case.get("breadth")) for case in cases} != {"broad", "narrow"}:
        errors.append("budget fixtures must cover broad and narrow questions")
    if {str(case.get("depth")) for case in cases} < {"quick", "deep"}:
        errors.append("budget fixtures must cover Quick and Deep")

    return _result(errors, {"case_count": len(cases), "hard_caps": hard_caps})


def validate_source_scenarios(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    scenarios = [item for item in payload.get("scenarios") or [] if isinstance(item, dict)]
    scenario_ids = {str(item.get("id") or "") for item in scenarios}
    missing = sorted(REQUIRED_SOURCE_SCENARIOS - scenario_ids)
    if missing:
        errors.append("missing mandatory source scenarios: " + ", ".join(missing))

    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "unknown")
        statuses = scenario.get("statuses") or {}
        evidence = [item for item in scenario.get("evidence") or [] if isinstance(item, dict)]
        expected = scenario.get("expected") or {}
        if set(statuses) != {"RAG", "Web", "Model"}:
            errors.append(f"{scenario_id}: statuses must contain RAG, Web, and Model")
        invalid_statuses = sorted(
            {str(value) for value in statuses.values()} - VALID_SOURCE_STATUSES
        )
        if invalid_statuses:
            errors.append(f"{scenario_id}: invalid statuses {', '.join(invalid_statuses)}")

        evidence_sources: set[str] = set()
        for item in evidence:
            source = str(item.get("source") or "")
            evidence_sources.add(source)
            if source not in EXTERNAL_SOURCES:
                errors.append(f"{scenario_id}: external evidence fixture has invalid source {source!r}")
            if statuses.get(source) != "success":
                errors.append(f"{scenario_id}: non-success source leaked into evidence: {source}")
            required = ("id", "dimension_id", "claim", "verbatim_quote", "evidence_ref")
            if any(not str(item.get(key) or "").strip() for key in required):
                errors.append(f"{scenario_id}: evidence item is missing traceability fields")
            if str(item.get("content_kind") or "") not in BODY_CONTENT_KINDS:
                errors.append(f"{scenario_id}: search metadata or snippet is not body evidence")

        allowed = {str(item) for item in expected.get("allowed_fact_sources") or []}
        if evidence_sources != allowed:
            errors.append(
                f"{scenario_id}: allowed fact sources {sorted(allowed)} do not match evidence "
                f"{sorted(evidence_sources)}"
            )
        if int(expected.get("failed_source_leakage") or 0) != 0:
            errors.append(f"{scenario_id}: expected leakage must be zero")
        if int(expected.get("invalid_citations") or 0) != 0:
            errors.append(f"{scenario_id}: expected invalid citations must be zero")
        if expected.get("completion_mode") == "model_analysis_only" and evidence:
            errors.append(f"{scenario_id}: model-analysis-only scenario cannot contain external evidence")
        if statuses.get("Web") != "success" and "Web" in evidence_sources:
            errors.append(f"{scenario_id}: failed Web source leaked into evidence")
        if scenario_id == "rag_no_evidence_web_success" and expected.get(
            "rag_absence_confidence_penalty"
        ) is not False:
            errors.append("RAG absence must not penalize sufficiently supported Web claims")
        if scenario_id == "web_snippet_without_body":
            if evidence or expected.get("snippets_are_evidence") is not False:
                errors.append("unfetched search snippets must remain discovery-only")

    return _result(errors, {"scenario_count": len(scenarios), "scenario_ids": sorted(scenario_ids)})


def validate_prompt_injection(path: Path) -> dict[str, Any]:
    from conflux.tools.web import _sanitize_untrusted_content

    errors: list[str] = []
    raw = path.read_text(encoding="utf-8")
    sanitized, detected = _sanitize_untrusted_content(raw)
    if not detected:
        errors.append("prompt injection fixture was not detected")
    if "Ignore previous instructions" in sanitized or "system prompt" in sanitized:
        errors.append("instruction-like text leaked through sanitization")
    for fact in ("durable checkpoint", "verify the checkpoint identifier"):
        if fact not in sanitized:
            errors.append(f"factual body content was removed: {fact}")
    return _result(
        errors,
        {"injection_detected": detected, "sanitized_length": len(sanitized)},
    )


def validate_report_traceability(payload: dict[str, Any]) -> dict[str, Any]:
    from conflux.research_protocol import (
        CoverageMatrix,
        DomainMap,
        ReportOutline,
        SectionContract,
        SectionDraft,
    )

    errors: list[str] = []
    domain_map = DomainMap.from_dict(payload.get("domain_map") or {})
    coverage = CoverageMatrix.from_dict(payload.get("coverage_matrix") or {})
    contracts = [
        SectionContract.from_dict(item, index=index)
        for index, item in enumerate(payload.get("section_contracts") or [])
        if isinstance(item, dict)
    ]
    raw_outline = payload.get("report_outline") or {}
    outline = ReportOutline.from_dict({**raw_outline, "sections": [item.to_dict() for item in contracts]})
    drafts = [
        SectionDraft.from_dict(item)
        for item in payload.get("section_drafts") or []
        if isinstance(item, dict)
    ]
    expected = payload.get("expected") or {}

    dimension_ids = {item.id for item in domain_map.dimensions}
    high_importance = {
        item.id for item in domain_map.dimensions
        if str(item.importance).casefold() == "high" or float(item.importance) >= 0.75
    }
    coverage_by_id = coverage.by_dimension()
    contract_by_id = {item.id: item for item in contracts}
    draft_by_id = {item.section_id: item for item in drafts}
    if len(contract_by_id) != len(contracts) or "" in contract_by_id:
        errors.append("section contract ids must be unique and non-empty")
    if len(draft_by_id) != len(drafts) or "" in draft_by_id:
        errors.append("section draft ids must be unique and non-empty")
    if set(coverage_by_id) != dimension_ids:
        errors.append("CoverageMatrix must contain exactly the DomainMap dimensions")
    if not high_importance:
        errors.append("report fixture must contain high-importance dimensions")

    raw_section_ids = [str(item) for item in raw_outline.get("sections") or []]
    if raw_section_ids != [item.id for item in contracts]:
        errors.append("ReportOutline section order must match SectionContract order")
    if {item.id for item in outline.sections} != set(contract_by_id):
        errors.append("ReportOutline must embed every SectionContract")
    if set(draft_by_id) != set(contract_by_id):
        errors.append("every SectionContract must have exactly one SectionDraft")

    covered_by_contract: set[str] = set()
    for contract in contracts:
        contract_dimensions = set(contract.dimension_ids)
        if not contract_dimensions <= dimension_ids:
            errors.append(f"{contract.id}: contract references an unknown dimension")
        covered_by_contract.update(contract_dimensions)
        unknown_dependencies = set(contract.dependencies) - set(contract_by_id)
        if unknown_dependencies or contract.id in contract.dependencies:
            errors.append(f"{contract.id}: invalid section dependency")
        draft = draft_by_id.get(contract.id)
        if draft is None:
            continue
        if not set(draft.dimension_ids) <= contract_dimensions:
            errors.append(f"{contract.id}: draft dimension is outside its contract")
        allowed_evidence: set[str] = set()
        for dimension_id in draft.dimension_ids:
            item = coverage_by_id.get(dimension_id)
            if item:
                allowed_evidence.update(item.evidence_ids)
        for claim in draft.claims:
            if not set(claim.evidence_ids) <= allowed_evidence:
                errors.append(f"{contract.id}: claim references evidence outside its dimensions")
            if claim.externally_supported and not claim.evidence_ids:
                errors.append(f"{contract.id}: externally supported claim has no evidence")

    missing_high = high_importance - covered_by_contract
    if missing_high:
        errors.append("high-importance dimensions lack a SectionContract: " + ", ".join(sorted(missing_high)))
    if _has_dependency_cycle(contract_by_id):
        errors.append("SectionContract dependencies contain a cycle")
    declared_traceable = {
        str(item) for item in expected.get("traceable_high_importance_dimensions") or []
    }
    if declared_traceable != high_importance:
        errors.append("declared high-importance traceability does not match DomainMap")

    actual_uncovered = {
        item.dimension_id for item in coverage.dimensions
        if item.status in {"partial", "evidence_scarce"}
    }
    actual_conflicting = {
        item.dimension_id for item in coverage.dimensions if item.status == "conflicting"
    }
    actual_out_of_scope = {
        item.dimension_id for item in coverage.dimensions if item.status == "out_of_scope"
    }
    for label, actual in (
        ("uncovered_dimensions", actual_uncovered),
        ("conflicting_dimensions", actual_conflicting),
        ("out_of_scope_dimensions", actual_out_of_scope),
    ):
        declared = {str(item) for item in expected.get(label) or []}
        if declared != actual:
            errors.append(f"{label} does not match CoverageMatrix")

    recommendations_required = bool(expected.get("recommendations_required"))
    recommendation_contracts = [
        item for item in contracts
        if "recommend" in item.function.casefold()
        or "recommendation" in {value.casefold() for value in item.required_claim_types}
    ]
    if not recommendations_required and recommendation_contracts:
        errors.append("report adds recommendations without user intent")

    try:
        for value in (domain_map, coverage, outline, *contracts, *drafts):
            json.dumps(value.to_dict(), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        errors.append(f"report protocol payload is not JSON serializable: {exc}")

    traceable = len(high_importance & covered_by_contract)
    ratio = traceable / max(1, len(high_importance))
    return _result(
        errors,
        {
            "dimension_count": len(dimension_ids),
            "section_count": len(contracts),
            "draft_count": len(drafts),
            "high_importance_traceability": round(ratio, 3),
            "uncovered_dimensions": sorted(actual_uncovered),
            "conflicting_dimensions": sorted(actual_conflicting),
            "out_of_scope_dimensions": sorted(actual_out_of_scope),
        },
    )


def run_offline(dataset_path: Path, fixtures_dir: Path, out_dir: Path) -> dict[str, Any]:
    source_payload = load_fixture(fixtures_dir / "source_scenarios.json")
    scenario_ids = {
        str(item.get("id") or "")
        for item in source_payload.get("scenarios") or []
        if isinstance(item, dict)
    }
    cases = load_dataset(dataset_path)
    gates = {
        "dataset_coverage": validate_dataset(cases, scenario_ids),
        "planner_recordings": validate_planner_recordings(
            load_fixture(fixtures_dir / "planner_recordings.json")
        ),
        "dynamic_budget_fixtures": validate_budget_cases(
            load_fixture(fixtures_dir / "budget_cases.json")
        ),
        "source_degradation_matrix": validate_source_scenarios(source_payload),
        "prompt_injection_sanitization": validate_prompt_injection(
            fixtures_dir / "web_prompt_injection.txt"
        ),
        "report_traceability": validate_report_traceability(
            load_fixture(fixtures_dir / "report_traceability.json")
        ),
    }
    passed = all(bool(item.get("passed")) for item in gates.values())
    payload = {
        "evaluation": "p1_5_generalized_deep_research_offline",
        "real_api": False,
        "dataset": str(dataset_path),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "fixtures_dir": str(fixtures_dir),
        "passed": passed,
        "gates": gates,
        "errors": [
            f"{name}: {error}"
            for name, gate in gates.items()
            for error in gate.get("errors") or []
        ],
    }
    write_outputs(payload, out_dir)
    return payload


def write_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "p1_5_eval.json"
    md_path = out_dir / "p1_5_eval.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# P1.5 Generalized Deep Research Offline Evaluation",
        "",
        f"- Passed: {payload['passed']}",
        f"- Dataset: `{payload['dataset']}`",
        f"- Dataset SHA-256: `{payload['dataset_sha256']}`",
        "- Real API calls: false",
        "",
        "| Gate | Passed | Metrics |",
        "|---|---:|---|",
    ]
    for name, gate in payload.get("gates", {}).items():
        metrics = json.dumps(gate.get("metrics") or {}, ensure_ascii=False, sort_keys=True)
        lines.append(f"| {name} | {gate.get('passed')} | `{metrics}` |")
    lines.extend(["", "## Errors", ""])
    errors = payload.get("errors") or []
    lines.extend(f"- {item}" for item in errors)
    if not errors:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def _has_dependency_cycle(contracts: dict[str, Any]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(section_id: str) -> bool:
        if section_id in visiting:
            return True
        if section_id in visited:
            return False
        visiting.add(section_id)
        contract = contracts.get(section_id)
        for dependency in getattr(contract, "dependencies", []):
            if visit(str(dependency)):
                return True
        visiting.remove(section_id)
        visited.add(section_id)
        return False

    return any(visit(section_id) for section_id in contracts)


def _result(errors: list[str], metrics: dict[str, Any]) -> dict[str, Any]:
    return {"passed": not errors, "errors": errors, "metrics": metrics}


def _resolve(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic P1.5 offline evaluation.")
    parser.add_argument("--dataset", default="data/p1_5_research_eval.yaml")
    parser.add_argument(
        "--fixtures-dir",
        default="tests/fixtures/architecture/p1_5",
    )
    parser.add_argument("--out-dir", default="reports/eval/p1_5")
    args = parser.parse_args()

    payload = run_offline(
        _resolve(args.dataset),
        _resolve(args.fixtures_dir),
        _resolve(args.out_dir),
    )
    print(json.dumps({
        "passed": payload["passed"],
        "gates": {name: gate["passed"] for name, gate in payload["gates"].items()},
        "errors": payload["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
