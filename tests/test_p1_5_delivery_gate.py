from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from conflux.core.dynamic_source import namespace_source_result
from conflux.graph_p15 import (
    _p15_verify_revise_node,
    _verifier_replacement_is_grounded,
)
from conflux.quality import evaluate_p15_delivery
from conflux.report import write_report_artifacts
from conflux.source_status import AgentClaim, SourceResult
from conflux.workbench.jobs import ResearchJob, _capture_report_snapshot


def _delivery_state() -> dict:
    return {
        "query": "GIS automation bottlenecks",
        "final_answer": "A cited and verified research answer.",
        "_scope_contract": {"subject": "GIS automation"},
        "_synthesis_status": "completed",
        "_synthesis_error": "",
        "_factcheck_status": "passed",
        "_factcheck_findings": {
            "semantic_verifier_status": "completed",
            "verified_claim_ratio": 0.95,
            "citation_coverage_applicable": True,
            "valid_citation_count": 4,
            "invalid_citation_count": 0,
        },
        "_verification_issues": [],
        "_evidence_gate": {"passed": True, "external_passed": 4},
        "_domain_map": {
            "dimensions": [
                {"id": "limits", "importance": 0.9},
                {"id": "boundaries", "importance": 0.8},
            ]
        },
        "_coverage_matrix": {
            "high_importance_coverage": 1.0,
            "dimensions": [
                {"dimension_id": "limits", "status": "covered"},
                {"dimension_id": "boundaries", "status": "covered"},
            ],
        },
        "_source_statuses": {},
        "_run_summary": {"mode": "p15"},
    }


def test_delivery_gate_classifies_deliverable_limited_and_diagnostic() -> None:
    state = _delivery_state()
    assert evaluate_p15_delivery(state)["status"] == "deliverable"

    limited = {
        **state,
        "_factcheck_findings": {
            **state["_factcheck_findings"],
            "verified_claim_ratio": 0.86,
        },
        "_coverage_matrix": {
            **state["_coverage_matrix"],
            "high_importance_coverage": 0.7,
            "dimensions": [
                {"dimension_id": "limits", "status": "covered"},
                {"dimension_id": "boundaries", "status": "partial"},
            ],
        },
    }
    limited_result = evaluate_p15_delivery(limited)
    assert limited_result["status"] == "limited"
    assert limited_result["limitations"]

    diagnostic = {
        **state,
        "_factcheck_status": "needs_review",
        "_verification_issues": [{"severity": "high", "resolved": False}],
    }
    diagnostic_result = evaluate_p15_delivery(diagnostic)
    assert diagnostic_result["status"] == "diagnostic_only"
    assert "factcheck_not_passed" in diagnostic_result["hard_failures"]
    assert "unresolved_high_severity_issue" in diagnostic_result["hard_failures"]


def test_delivery_gate_allows_deterministic_verifier_fallback_only_as_limited() -> None:
    state = _delivery_state()
    state["_factcheck_findings"] = {
        **state["_factcheck_findings"],
        "semantic_verifier_status": "deterministic_fallback",
    }

    result = evaluate_p15_delivery(state)

    assert result["status"] == "limited"
    assert "semantic_verifier_unavailable" not in result["hard_failures"]
    assert "semantic_verifier_deterministic_fallback" in result["limitations"]


def test_malformed_semantic_verifier_falls_back_to_clean_deterministic_factcheck() -> None:
    ref = "[Web:https://official.example/gis]"
    claim = AgentClaim(
        claim="The official GIS workflow records a validated automation constraint.",
        source="Web",
        verbatim_quote="The official GIS workflow records a validated automation constraint.",
        paper_id="https://official.example/gis",
        document_title="GIS processing automation official evidence",
        url="https://official.example/gis",
        content_kind="html",
        directness=0.95,
        authority=0.9,
        relevance=0.9,
        evidence_refs=[ref],
        evidence_class="authoritative_document",
    )
    web = namespace_source_result(
        "builtin.web",
        SourceResult(
            source="Web",
            status="success",
            content=claim.claim,
            claims=[claim],
            evidence_class="authoritative_document",
        ),
    )
    report = (
        "## 回答\n\n### Findings\n\n"
        "The official GIS workflow records a validated automation constraint. "
        + ref
        + "\n\n## 可靠性与缺口\n\n- One official source was available."
    )

    class MalformedVerifier:
        def invoke(self, messages):
            return SimpleNamespace(content="not json")

    result = _p15_verify_revise_node(
        {
            "query": "GIS processing automation",
            "final_answer": report,
            "source_results": {"builtin.web": web.to_dict()},
            "_scope_contract": {
                "subject": "GIS processing automation",
                "scope_inclusions": ["GIS processing automation"],
                "original_query": "GIS processing automation",
            },
            "_research_budget": {"depth_query_limit": 4, "timeout_seconds": 240},
            "_deadline_at": time.time() + 120,
            "_source_statuses": {"Web": {"status": "success"}},
            "_section_contracts": [],
            "_section_drafts": [],
            "_section_verification": [],
            "_run_summary": {"started_at": time.time(), "stages": []},
        },
        MalformedVerifier(),
        object(),
        SimpleNamespace(factcheck_strength="full"),
    )

    assert result["_factcheck_status"] == "passed"
    assert result["_factcheck_findings"]["semantic_verifier_status"] == "deterministic_fallback"
    assert "ValueError" in result["_factcheck_findings"]["verifier_error"]


def test_factcheck_replacement_cannot_launder_uncited_facts() -> None:
    ref = "[Web:https://official.example/policy]"
    report = f"The official policy defines one reporting duty.{ref}"

    assert _verifier_replacement_is_grounded(
        f"The official policy defines one reporting duty.{ref}",
        report,
        [ref],
    )
    assert not _verifier_replacement_is_grounded(
        (
            "The official policy defines one reporting duty. "
            "It also binds every downstream provider without exception."
            + ref
        ),
        report,
        [ref],
    )


def test_diagnostic_artifacts_are_segregated(tmp_path: Path) -> None:
    state = {
        **_delivery_state(),
        "_delivery_status": "diagnostic_only",
        "_delivery_assessment": {"hard_failures": ["factcheck_not_passed"]},
    }

    artifacts = write_report_artifacts(
        state["query"],
        state,
        tmp_path,
        diagnostic=True,
    )

    assert artifacts.markdown_path.parent == tmp_path / "diagnostics"
    assert ".diagnostic.md" in artifacts.markdown_path.name
    assert "未通过交付门禁" in artifacts.markdown_path.read_text(encoding="utf-8")


def test_formal_artifact_exports_only_gate_eligible_evidence(tmp_path: Path) -> None:
    import json

    state = {
        **_delivery_state(),
        "_delivery_status": "deliverable",
        "_evidence_json": json.dumps({"nodes": [{"id": "rejected"}]}),
        "_gated_evidence_json": json.dumps({"nodes": [{"id": "eligible"}]}),
    }

    artifacts = write_report_artifacts(state["query"], state, tmp_path)
    exported = json.loads(artifacts.evidence_json_path.read_text(encoding="utf-8"))

    assert exported["nodes"] == [{"id": "eligible"}]


def test_limited_artifact_discloses_delivery_limit(tmp_path: Path) -> None:
    state = {
        **_delivery_state(),
        "_delivery_status": "limited",
        "_delivery_assessment": {
            "limitations": ["citation_coverage_below_delivery_target"]
        },
    }

    artifacts = write_report_artifacts(state["query"], state, tmp_path)
    markdown = artifacts.markdown_path.read_text(encoding="utf-8")

    assert markdown.startswith("# Conflux 有限证据研究报告")
    assert "citation_coverage_below_delivery_target" in markdown


def test_workbench_diagnostic_snapshot_never_becomes_formal_report(tmp_path: Path) -> None:
    job = ResearchJob(run_id="diagnostic", query="q", pipeline="p15")
    state = {
        **_delivery_state(),
        "_delivery_status": "diagnostic_only",
        "final_answer": "diagnostic body",
    }

    _capture_report_snapshot(job, state, str(tmp_path), stage="verified")

    assert job.delivery_status == "diagnostic_only"
    assert job.has_report is False
    assert "markdown_path" not in job.artifacts
    assert Path(job.artifacts["verified_markdown_path"]).is_file()


def test_cli_diagnostic_summary_has_no_formal_report_paths(monkeypatch, tmp_path: Path) -> None:
    import conflux.__main__ as cli

    role_models = {role: object() for role in (
        "planner", "analyst", "reranker", "synthesizer", "verifier"
    )}
    captured = {}
    monkeypatch.setattr(cli, "load_config", lambda: {
        "research": {"pipeline": "p15", "generalization": {"enabled": True}}
    })
    monkeypatch.setattr(cli, "validate_runtime_credentials", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "create_vector_store", lambda: object())
    monkeypatch.setattr(cli, "HybridRetriever", lambda store: object())
    monkeypatch.setattr(cli, "create_research_models", lambda depth, **kwargs: (role_models, {"roles": {}}))
    monkeypatch.setattr(cli, "set_model", lambda model: None)
    monkeypatch.setattr(cli, "create_rag_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_web_tool", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_sub_agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "create_p15_research_graph", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        cli,
        "create_checkpointer",
        lambda backend: SimpleNamespace(backend="memory", checkpointer=None),
    )
    monkeypatch.setattr(
        cli,
        "_run_phase2_graph",
        lambda graph, initial_state, query, **kwargs: ({
            **initial_state,
            "final_answer": "diagnostic answer",
            "_delivery_status": "diagnostic_only",
            "_delivery_assessment": {"hard_failures": ["factcheck_not_passed"]},
            "_run_summary": {"mode": "p15"},
            "_source_statuses": {},
            "_quality_report": {},
        }, []),
    )
    diagnostic_md = tmp_path / "diagnostics" / "run.diagnostic.md"
    diagnostic_html = tmp_path / "diagnostics" / "run.diagnostic.html"

    def fake_write(*args, **kwargs):
        captured["diagnostic"] = kwargs.get("diagnostic")
        return SimpleNamespace(
            markdown_path=diagnostic_md,
            html_path=diagnostic_html,
            evidence_json_path=None,
            raw_sources_path=None,
            deep_evidence_json_path=None,
            audit_markdown_path=None,
        )

    summaries = []
    monkeypatch.setattr(cli, "write_report_artifacts", fake_write)
    monkeypatch.setattr(cli, "write_trace_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "write_run_summary", lambda summary, path: summaries.append(summary))

    result = cli.query_command(
        "diagnostic fixture",
        mode="phase2",
        output_dir=str(tmp_path),
        run_id="diagnostic-fixture",
        depth="quick",
    )

    assert captured["diagnostic"] is True
    assert summaries[-1]["report_md_path"] == ""
    assert summaries[-1]["report_html_path"] == ""
    assert summaries[-1]["diagnostic_markdown_path"] == str(diagnostic_md.resolve())
    assert result["_report_artifacts"]["markdown_path"] == ""
    assert result["_report_artifacts"]["diagnostic_markdown_path"] == str(diagnostic_md.resolve())


def test_session_reader_does_not_promote_explicitly_empty_report_path(monkeypatch, tmp_path: Path) -> None:
    import json
    from conflux.workbench import sessions

    run_id = "diagnostic-session"
    summary = tmp_path / f"{run_id}.summary.json"
    summary.write_text(json.dumps({
        "run_id": run_id,
        "delivery_status": "diagnostic_only",
        "report_md_path": "",
        "report_html_path": "",
    }), encoding="utf-8")
    (tmp_path / f"{run_id}.verified.md").write_text(
        f"# staged\n\nRun id: {run_id}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sessions, "_REPORTS_ROOT", tmp_path)

    detail = sessions.get_session_detail(run_id)

    assert detail is not None
    assert detail["report_md_available"] is False
    assert detail["report_md_path"] == ""
