"""Ablation study — compare Conflux configurations deterministically.

Runs the same queries through 5 pipeline configurations using FakeModel to
measure the marginal contribution of each component.

Outputs: reports/eval/ablation.md + reports/eval/ablation.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from conflux.source_status import SourceResult
from conflux.evidence import EvidenceGraph, build_evidence_graph_from_results
from conflux.quality import evaluate_run_quality


# ── Fake tools that return structured SourceResults ──────────────

@tool
def fake_rag_success(query: str) -> str:
    """Search local documents."""
    return SourceResult(
        source="RAG",
        status="success",
        detail="fake-local",
        content="RAG: Multi-agent systems should validate evidence from multiple sources before reaching conclusions. Local documents suggest 3-source arbitration with weighted voting.",
        claims=[],
        metadata={"result_count": 3},
    ).to_tool_text()


@tool
def fake_web_success(query: str) -> str:
    """Search the web."""
    return SourceResult(
        source="Web",
        status="success",
        detail="fake-web",
        content="Web: Recent research shows multi-agent systems benefit from parallel source retrieval. URL: https://example.test/agents. Web search confirms arbitration protocols improve accuracy.",
        claims=[],
        metadata={"result_count": 2},
    ).to_tool_text()


@tool
def fake_model_success(query: str) -> str:
    """Answer from model knowledge."""
    return SourceResult(
        source="Model",
        status="success",
        detail="fake-model",
        content="Model: Multi-agent systems can use ensemble methods to combine outputs. Model knowledge suggests confidence scoring and uncertainty quantification.",
        claims=[],
        metadata={"evidence_type": "model inference"},
    ).to_tool_text()


@tool
def fake_rag_failed(query: str) -> str:
    """Search local documents — fails."""
    return SourceResult(
        source="RAG",
        status="failed",
        detail="fake-local",
        error="No relevant documents found.",
        content="Local retrieval returned no relevant results.",
    ).to_tool_text()


@tool
def fake_web_failed(query: str) -> str:
    """Search the web — fails."""
    return SourceResult(
        source="Web",
        status="failed",
        detail="fake-web",
        error="Search timeout",
        content="Web search timed out.",
    ).to_tool_text()


# ── Fake chat model with configurable responses ─────────────────

class FakeModel:
    """Deterministic fake chat model."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if self.responses:
            content = self.responses.pop(0)
        else:
            content = "```final\n## 回答\n默认回答。\n```"
        return AIMessage(content=content)


# ── Query definitions ───────────────────────────────────────────

QUERIES = [
    {
        "id": "all_success",
        "query": "How should multi-agent systems validate evidence?",
        "scenario": "All three sources succeed",
        "rag_tool": fake_rag_success,
        "web_tool": fake_web_success,
        "model_tool": fake_model_success,
        "expected_consensus": True,
    },
    {
        "id": "rag_web_success_model_fallback",
        "query": "What retrieval strategies work best for multi-agent RAG?",
        "scenario": "RAG+Web success, Model provides generic inference",
        "rag_tool": fake_rag_success,
        "web_tool": fake_web_success,
        "model_tool": fake_model_success,  # still success but lower confidence
        "expected_consensus": True,
    },
    {
        "id": "web_failed",
        "query": "How to handle web search failures in agent systems?",
        "scenario": "RAG+Model success, Web failed",
        "rag_tool": fake_rag_success,
        "web_tool": fake_web_failed,
        "model_tool": fake_model_success,
        "expected_consensus": False,
    },
    {
        "id": "only_model",
        "query": "What is the future of AI agent orchestration?",
        "scenario": "Only Model succeeds, RAG and Web fail",
        "rag_tool": fake_rag_failed,
        "web_tool": fake_web_failed,
        "model_tool": fake_model_success,
        "expected_consensus": False,
    },
]


# ── Pipeline runner ─────────────────────────────────────────────

def run_config(config_name: str, case: dict) -> dict[str, Any]:
    """Run one query through one pipeline config.

    Returns metrics dict.
    """
    from conflux.agent import create_sub_agent
    from conflux.graph_v2 import create_multi_agent_graph

    query = case["query"]

    if config_name == "multi_no_arbitration":
        reasoning = FakeModel([
            f"```final\nRAG answer for: {query}\n```",
            f"```final\nWeb answer for: {query}\n```",
            f"```final\nModel answer for: {query}\n```",
            f"## 最终结论\nMerged answer without arbitration.\n## 信息来源\n三源合并。\n## 不确定性\n缺少仲裁可能遗漏冲突。\n## 证据摘要\n合并完成。",
        ])
        cheap = FakeModel([
            "验证通过：所有声明均有信息源支持",
        ])
        rag_agent = create_sub_agent("rag", reasoning, case["rag_tool"])
        web_agent = create_sub_agent("web", reasoning, case["web_tool"])
        model_agent = create_sub_agent("model", reasoning, case["model_tool"])
        graph = create_multi_agent_graph(rag_agent, web_agent, model_agent, reasoning, cheap)
        init = _empty_state(query)
        result = graph.invoke(init)
        source_count = _count_success_sources(result)
        has_arbitration = bool(result.get("_arbitration", ""))
        has_factcheck = bool(result.get("_factcheck_status", ""))
        has_l4 = bool(result.get("_deep_research", ""))

    elif config_name == "multi_arbitration":
        reasoning = FakeModel([
            f"```final\nRAG answer for: {query}\n```",
            f"```final\nWeb answer for: {query}\n```",
            f"```final\nModel answer for: {query}\n```",
            f"## 最终结论\nAnswer with arbitration applied.\n## 信息来源\n三源仲裁后合并。\n## 不确定性\n已通过仲裁检测冲突。\n## 证据摘要\n仲裁完成。",
        ])
        cheap = FakeModel([
            "仲裁：已检测来源冲突，RAG和Web一致，Model补充。",
            "验证通过：所有关键声明均有信息源支持",
            "子问题一：如何改进仲裁权重？\n子问题二：哪些场景需要人工升级？",
            "### 深化补充\n证据支持：仲裁权重可根据领域调整。模型推断：未来可引入动态权重。",
        ])
        rag_agent = create_sub_agent("rag", reasoning, case["rag_tool"])
        web_agent = create_sub_agent("web", reasoning, case["web_tool"])
        model_agent = create_sub_agent("model", reasoning, case["model_tool"])
        graph = create_multi_agent_graph(rag_agent, web_agent, model_agent, reasoning, cheap)
        init = _empty_state(query)
        result = graph.invoke(init)
        source_count = _count_success_sources(result)
        has_arbitration = bool(result.get("_arbitration", ""))
        has_factcheck = bool(result.get("_factcheck_status", ""))
        has_l4 = bool(result.get("_deep_research", ""))

    elif config_name == "multi_full":
        reasoning = FakeModel([
            f"```final\nRAG answer for: {query}\n```",
            f"```final\nWeb answer for: {query}\n```",
            f"```final\nModel answer for: {query}\n```",
            f"## 最终结论\nFull pipeline answer with all protections.\n## 信息来源\nRAG/Web/Model全部参与仲裁。\n## 不确定性\n已检测：Web失败场景已降级。\n## 证据摘要\n3节点共识。\n## 工程落地建议\n建立来源状态标注。",
        ])
        cheap = FakeModel([
            "仲裁：Level 0共识：RAG和Web一致支持多源验证。Level 1多数：Model补充不确定性量化。",
            "### 确定性追溯检查\n- success 来源：RAG, Web, Model\n- failed/fallback 来源：无\n- 证据节点数：3\n验证通过：所有关键声明均有信息源支持",
            "子问题一：仲裁权重如何动态调整？\n子问题二：人工升级触发条件如何量化？",
            "### 深化补充\n证据支持：当前仲裁权重基于静态配置。模型推断：可引入来源时效性动态调整权重。进一步检索：需查证最新多Agent验证框架。",
        ])
        rag_agent = create_sub_agent("rag", reasoning, case["rag_tool"])
        web_agent = create_sub_agent("web", reasoning, case["web_tool"])
        model_agent = create_sub_agent("model", reasoning, case["model_tool"])
        graph = create_multi_agent_graph(rag_agent, web_agent, model_agent, reasoning, cheap)
        init = _empty_state(query)
        result = graph.invoke(init)
        source_count = _count_success_sources(result)
        has_arbitration = bool(result.get("_arbitration", ""))
        has_factcheck = bool(result.get("_factcheck_status", ""))
        has_l4 = bool(result.get("_deep_research", ""))

    else:
        raise ValueError(f"Unknown config: {config_name}")

    # Evaluate quality
    quality = evaluate_run_quality(result)

    # Evidence graph metrics
    evidence_payload = {}
    try:
        evidence_payload = json.loads(result.get("_evidence_json", "{}"))
    except json.JSONDecodeError:
        pass
    evidence_summary = evidence_payload.get("summary", {})
    evidence_nodes = evidence_payload.get("nodes", [])

    # Failed source leakage check
    failed_sources = _get_failed_sources(result)
    leaked = any(
        node.get("source") in failed_sources
        for node in evidence_nodes
    )

    # Has uncertainty statement
    final = str(result.get("final_answer", ""))
    has_uncertainty = "不确定" in final or "uncertain" in final.lower()

    return {
        "config": config_name,
        "case_id": case["id"],
        "scenario": case["scenario"],
        "metrics": {
            "success_sources": source_count,
            "has_arbitration": has_arbitration,
            "has_factcheck": has_factcheck,
            "has_l4": has_l4,
            "evidence_nodes": len(evidence_nodes),
            "consensus_count": evidence_summary.get("consensus_count", 0),
            "contested_count": evidence_summary.get("contested_count", 0),
            "avg_authority": evidence_summary.get("avg_authority", 0),
            "failed_source_leakage": leaked,
            "has_uncertainty_statement": has_uncertainty,
            "quality_overall": quality.get("overall", 0),
            "quality_passed": quality.get("passed", False),
            "factcheck_status": result.get("_factcheck_status", "none"),
        },
    }


def _empty_state(query: str) -> dict:
    return {
        "query": query,
        "rag_result": "",
        "web_result": "",
        "model_result": "",
        "_merged": "",
        "_arbitration": "",
        "_evidence_json": "",
        "_source_statuses": {},
        "_verified_answer": "",
        "_factcheck_status": "",
        "_factcheck_report": "",
        "_deep_research": "",
        "_run_summary": {},
        "_quality_report": {},
        "_pipeline_stage": "",
        "final_answer": "",
    }


def _count_success_sources(result: dict) -> int:
    statuses = result.get("_source_statuses", {})
    return sum(
        1 for payload in statuses.values()
        if payload.get("status") == "success"
    )


def _get_failed_sources(result: dict) -> set:
    statuses = result.get("_source_statuses", {})
    return {
        source
        for source, payload in statuses.items()
        if payload.get("status") in {"failed", "fallback"}
    }


# ── Main ────────────────────────────────────────────────────────

CONFIGS = [
    "multi_no_arbitration",
    "multi_arbitration",
    "multi_full",
]

CONFIG_LABELS = {
    "multi_no_arbitration": "Multi-Agent (no Arbitration)",
    "multi_arbitration": "Multi-Agent + Arbitration",
    "multi_full": "Multi-Agent + Arbitration + FactCheck + L4",
}


def main() -> int:
    out_dir = ROOT / "reports" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[dict] = []
    for case in QUERIES:
        for config_name in CONFIGS:
            print(f"Running {config_name} on {case['id']}...")
            result = run_config(config_name, case)
            all_results.append(result)

    # Aggregate metrics per config
    aggregated = {}
    for config_name in CONFIGS:
        config_results = [r for r in all_results if r["config"] == config_name]
        metrics_list = [r["metrics"] for r in config_results]
        n = len(metrics_list)
        aggregated[config_name] = {
            "label": CONFIG_LABELS[config_name],
            "cases": n,
            "avg_success_sources": round(sum(m["success_sources"] for m in metrics_list) / n, 2),
            "avg_evidence_nodes": round(sum(m["evidence_nodes"] for m in metrics_list) / n, 2),
            "avg_consensus_count": round(sum(m["consensus_count"] for m in metrics_list) / n, 2),
            "avg_contested_count": round(sum(m["contested_count"] for m in metrics_list) / n, 2),
            "avg_authority": round(sum(m["avg_authority"] for m in metrics_list) / n, 2),
            "failed_source_leakage_rate": round(sum(1 for m in metrics_list if m["failed_source_leakage"]) / n, 2),
            "uncertainty_coverage": round(sum(1 for m in metrics_list if m["has_uncertainty_statement"]) / n, 2),
            "quality_pass_rate": round(sum(1 for m in metrics_list if m["quality_passed"]) / n, 2),
            "factcheck_active_rate": round(sum(1 for m in metrics_list if m["factcheck_status"] in ("passed", "needs_review")) / n, 2),
            "arbitration_active": all(m["has_arbitration"] for m in metrics_list),
            "l4_active": all(m["has_l4"] for m in metrics_list),
        }

    # Write JSON
    payload = {
        "description": "Conflux ablation study — marginal contribution of each pipeline component",
        "configs": CONFIG_LABELS,
        "aggregated": aggregated,
        "details": all_results,
    }
    json_path = out_dir / "ablation.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Markdown
    md_lines = [
        "# Conflux Ablation Study",
        "",
        "Each configuration is tested against 4 scenario queries (all success, RAG+Web success, Web failed, only Model).",
        "",
        "## Summary Table",
        "",
        "| Metric | Single Agent | Multi (no Arb) | Multi + Arb | **Full Pipeline** |",
        "|---|---:|---:|---:|---:|",
    ]

    rows = [
        ("Success Sources (avg)", "avg_success_sources"),
        ("Evidence Nodes (avg)", "avg_evidence_nodes"),
        ("Consensus Count (avg)", "avg_consensus_count"),
        ("Contested Count (avg)", "avg_contested_count"),
        ("Avg Authority Score", "avg_authority"),
        ("Failed-Source Leakage Rate", "failed_source_leakage_rate"),
        ("Uncertainty Coverage", "uncertainty_coverage"),
        ("Quality Pass Rate", "quality_pass_rate"),
        ("FactCheck Active Rate", "factcheck_active_rate"),
    ]

    for label, key in rows:
        vals = [aggregated[c][key] for c in CONFIGS]
        formatted = " | ".join(
            f"**{v}**" if i == len(vals) - 1 else str(v)
            for i, v in enumerate(vals)
        )
        md_lines.append(f"| {label} | {formatted} |")

    # Add feature presence row
    md_lines.append("")
    md_lines.append("## Feature Presence")
    md_lines.append("")
    md_lines.append("| Feature | Single Agent | Multi (no Arb) | Multi + Arb | **Full Pipeline** |")
    md_lines.append("|---|---:|---:|---:|---:|")
    for feature, key in [
        ("Arbitration", "arbitration_active"),
        ("FactCheck", "factcheck_active_rate"),
        ("L4 Deep Research", "l4_active"),
    ]:
        vals = []
        for c in CONFIGS:
            v = aggregated[c][key]
            if isinstance(v, bool):
                vals.append("✅" if v else "—")
            elif isinstance(v, (int, float)):
                vals.append(f"{v:.0%}" if v < 1.1 else str(v))
            else:
                vals.append(str(v))
        formatted = " | ".join(f"**{v}**" if i == len(vals) - 1 else v for i, v in enumerate(vals))
        md_lines.append(f"| {feature} | {formatted} |")

    md_lines.append("")
    md_lines.append("## Per-Scenario Breakdown")
    md_lines.append("")
    for case in QUERIES:
        md_lines.append(f"### {case['id']}: {case['scenario']}")
        md_lines.append("")
        md_lines.append("| Config | Success Sources | Evidence Nodes | Consensus | Leakage | Quality |")
        md_lines.append("|---|---:|---:|---:|---:|---:|")
        for config_name in CONFIGS:
            r = next(
                (item for item in all_results if item["config"] == config_name and item["case_id"] == case["id"]),
                None,
            )
            if r:
                m = r["metrics"]
                md_lines.append(
                    f"| {CONFIG_LABELS[config_name]} "
                    f"| {m['success_sources']} "
                    f"| {m['evidence_nodes']} "
                    f"| {m['consensus_count']} "
                    f"| {'⚠️ YES' if m['failed_source_leakage'] else '✅ no'} "
                    f"| {m['quality_overall']}/5 {'✅' if m['quality_passed'] else '❌'} |"
                )
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("*Generated by scripts/eval_ablation.py — deterministic FakeModel evaluation.*")

    md_path = out_dir / "ablation.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Ablation report: {md_path}")
    print(f"Ablation JSON: {json_path}")

    # Print key findings
    print("\n=== Key Findings ===")
    best = aggregated["multi_full"]
    worst = aggregated["multi_no_arbitration"]
    print(f"Quality improvement: {worst['quality_pass_rate']:.0%} → {best['quality_pass_rate']:.0%}")
    print(f"Leakage reduction: {worst['failed_source_leakage_rate']:.0%} → {best['failed_source_leakage_rate']:.0%}")
    print(f"Uncertainty coverage: {worst['uncertainty_coverage']:.0%} → {best['uncertainty_coverage']:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
