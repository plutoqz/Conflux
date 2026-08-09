"""M5 evaluation manifest and complementary SDK extension contracts."""

from __future__ import annotations

import json
from pathlib import Path

from conflux.adapters.plugin_loader import load_plugins_from_dirs
from conflux.core.contracts import PluginContext, RunContext, StepStatus
from conflux.core.registry import PluginRegistry
from conflux.evaluation_m5 import evaluate_manifest, render_markdown


ROOT = Path(__file__).resolve().parents[1]


def test_m5_manifest_covers_strategy_matrix_r3_and_hashes() -> None:
    manifest = json.loads((ROOT / "evaluation/m5/manifest.json").read_text(encoding="utf-8"))
    evidence_prefix = "evaluation/m5/evidence/"
    evidence_paths = [item["artifact"] for item in manifest["strategies"]]
    evidence_paths.extend(
        config
        for item in manifest["strategies"]
        for config in item.get("configs", [])
    )
    evidence_paths.append(manifest["r3"]["artifact"])
    evidence_paths.extend(
        value
        for key, value in manifest["debt"].items()
        if key.endswith("_artifact")
    )

    assert all(path.startswith(evidence_prefix) for path in evidence_paths)
    assert all((ROOT / path).is_file() for path in evidence_paths)

    result = evaluate_manifest(manifest, root=ROOT)

    assert result["checks"]["four_strategy_matrix_complete"] is True
    assert result["checks"]["all_artifacts_hashed"] is True
    assert result["checks"]["all_failures_structured"] is True
    assert result["checks"]["complementary_extensions"] is True
    assert result["checks"]["r3_uses_current_path"] is True
    assert result["r3"]["live_quality_claim"] is False
    assert {item["variant"] for item in result["r3"]["conditions"]} == {"B2", "B3", "B4"}
    assert "Recorded and replay artifacts" in render_markdown(result)


def test_local_jsonl_source_extension_is_workspace_bounded(tmp_path: Path) -> None:
    source = tmp_path / "papers.jsonl"
    source.write_text(
        '{"id":"p1","title":"Graph RAG"}\n{"id":"p2","title":"Remote sensing"}\n',
        encoding="utf-8",
    )
    registry = load_plugins_from_dirs(
        [ROOT / "examples/m5_plugins/local_jsonl_source"],
        PluginRegistry(),
    )
    capability = registry.resolve_capability("example.local-jsonl-source.search")
    assert capability is not None
    ctx = PluginContext(run=RunContext(run_id="m5-source", workspace=str(tmp_path)))

    result = capability(ctx, path="papers.jsonl", query="Graph")
    blocked = capability(ctx, path="../outside.jsonl", query="Graph")

    assert result.status == StepStatus.SUCCESS
    assert [item["id"] for item in result.output["items"]] == ["p1"]
    assert blocked.status == StepStatus.FAILED


def test_evidence_coverage_evaluator_is_non_source_extension() -> None:
    registry = load_plugins_from_dirs(
        [ROOT / "examples/m5_plugins/evidence_coverage_evaluator"],
        PluginRegistry(),
    )
    capability = registry.resolve_capability("example.evidence-coverage-evaluator.score")
    assert capability is not None
    ctx = PluginContext(run=RunContext(run_id="m5-evaluator"))
    result = capability(ctx, claims=[
        {"claim_id": "c1", "evidence_ids": ["e1"]},
        {"claim_id": "c2", "evidence_ids": []},
    ])

    assert result.status == StepStatus.SUCCESS
    assert result.output == {"coverage": 0.5, "uncovered_claim_ids": ["c2"]}
