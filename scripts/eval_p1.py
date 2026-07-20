"""P1 research-quality evaluation and ablation runner.

Offline mode validates dataset/matrix coverage without inventing answer scores.
Real mode is opt-in and executes the P1 graph against configured APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import queue
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


DEPTHS = ("quick", "standard", "deep")
SCENARIOS = ("model_only", "model_rag", "model_web", "full", "rag_failure", "web_failure")
REQUIRED_CATEGORIES = {
    "local_section",
    "model_synthesis",
    "recent_web",
    "cross_language_conflict",
    "degradation",
    "safety",
}
JUDGE_SYSTEM = "你是独立的研究质量评审者。只输出有效 JSON，不因篇幅长或术语多而加分。"
JUDGE_TEMPLATE = """按 1-5 分评审研究答案。Model、RAG、Web 是互补来源，不要求三源投票；
单一直接且高权威的来源可以支撑声明。重点检查正确性、完整性、分析深度、问题覆盖、
时效性、表达效率和引用是否能由给定证据反向定位。
评审必须以给定证据为可审计依据。不得仅凭模型记忆断言某标准已经发布、某政策已经
生效或答案与事实冲突；若反证不在给定证据中，只能列为待独立核验问题，不能作为确定
错误扣分。每个 critical issue 应能指向答案与证据之间的具体缺口或矛盾。

问题：{query}
要求覆盖：{dimensions}
答案：
{answer}

证据摘要：
{evidence}

仅输出：
{{"correctness":1,"completeness":1,"depth":1,"coverage":1,"recency":1,
"efficiency":1,"citation_quality":1,"overall":1,"reason":"具体理由",
"critical_issues":["失败点"]}}"""


@dataclass
class UsageMeter:
    calls: list[dict[str, Any]] = field(default_factory=list)
    trace_path: Path | None = None

    def record(self, role: str, model: Any, response: Any, elapsed_ms: float) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        response_metadata = getattr(response, "response_metadata", None) or {}
        token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}
        input_tokens = _first_int(usage, token_usage, keys=("input_tokens", "prompt_tokens"))
        output_tokens = _first_int(usage, token_usage, keys=("output_tokens", "completion_tokens"))
        total_tokens = _first_int(usage, token_usage, keys=("total_tokens",)) or input_tokens + output_tokens
        item = {
            "role": role,
            "model": str(getattr(model, "model_name", None) or getattr(model, "model", None) or ""),
            "elapsed_ms": round(elapsed_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
        self.calls.append(item)
        if self.trace_path is not None:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "call_count": len(self.calls),
            "input_tokens": sum(item["input_tokens"] for item in self.calls),
            "output_tokens": sum(item["output_tokens"] for item in self.calls),
            "total_tokens": sum(item["total_tokens"] for item in self.calls),
            "estimated_cost_usd": None,
            "cost_note": "网关未返回统一计费字段，未虚构价格；可结合实际账单回填。",
            "calls": self.calls,
        }


class MeteredModel:
    def __init__(self, model: Any, meter: UsageMeter, role: str) -> None:
        self.model = model
        self.meter = meter
        self.role = role

    def bind_tools(self, tools: list[Any]):
        return MeteredModel(self.model.bind_tools(tools), self.meter, self.role)

    def invoke(self, messages: Any):
        started = time.perf_counter()
        response = self.model.invoke(messages)
        self.meter.record(self.role, self.model, response, (time.perf_counter() - started) * 1000)
        return response


def load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"P1 dataset must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def validate_dataset(cases: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(item.get("id") or "") for item in cases]
    categories = {str(item.get("category") or "") for item in cases}
    errors = []
    if len(cases) < 30:
        errors.append(f"评测集不足 30 问：{len(cases)}")
    if len(set(ids)) != len(ids) or any(not item for item in ids):
        errors.append("评测集 ID 缺失或重复")
    missing_categories = sorted(REQUIRED_CATEGORIES - categories)
    if missing_categories:
        errors.append("缺少类别：" + ", ".join(missing_categories))
    for case in cases:
        if not case.get("query") or not case.get("required_dimensions"):
            errors.append(f"{case.get('id') or 'unknown'} 缺少 query/required_dimensions")
    counts = {
        category: sum(str(item.get("category")) == category for item in cases)
        for category in sorted(categories)
    }
    return {
        "passed": not errors,
        "case_count": len(cases),
        "category_counts": counts,
        "matrix_run_count": len(cases) * len(DEPTHS) * len(SCENARIOS),
        "depths": list(DEPTHS),
        "scenarios": list(SCENARIOS),
        "errors": errors,
    }


def run_real_case(
    case: dict[str, Any],
    depth: str,
    scenario: str,
    *,
    judge: bool,
    judge_preset: str,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Any]:
    from conflux import config
    from conflux.__main__ import _empty_multi_agent_state
    from conflux.agent import create_sub_agent
    from conflux.graph_p1 import create_p1_research_graph
    from conflux.model_factory import BoundedChatModel, create_chat_model, create_research_models
    from conflux.query_planner import QueryRewriteProvider
    from conflux.rag.indexer import create_vector_store
    from conflux.rag.reranker import SemanticReranker
    from conflux.rag.retriever import HybridRetriever
    from conflux.report import write_report_artifacts
    from conflux.research_modes import resolve_research_profile
    from conflux.source_status import SourceResult
    from conflux.tools.rag import create_rag_tool
    from conflux.tools.web import create_web_tool

    config._config = None
    run_id = run_id or f"eval-{case['id']}-{depth}-{scenario}-{int(time.time())}"
    profile = resolve_research_profile(depth)
    role_models, model_trace = create_research_models(depth)
    meter = UsageMeter(trace_path=output_dir / run_id / "live_usage.jsonl")
    metered = {role: MeteredModel(model, meter, role) for role, model in role_models.items()}
    enabled, failed = _scenario_sources(scenario)

    if "RAG" in enabled and "RAG" not in failed:
        retriever = HybridRetriever(create_vector_store())
        rag_tool = create_rag_tool(
            retriever,
            QueryRewriteProvider(),
            SemanticReranker(metered["reranker"], batch_size=profile.candidate_limit),
            profile,
        )
    else:
        rag_tool = _unavailable_tool("RAG", failed="RAG" in failed)
    web_tool = (
        create_web_tool(profile, run_id=run_id)
        if "Web" in enabled and "Web" not in failed
        else _unavailable_tool("Web", failed="Web" in failed)
    )

    graph = create_p1_research_graph(
        create_sub_agent("rag", metered["reranker"], rag_tool),
        create_sub_agent("web", metered["reranker"], web_tool),
        planner_model=metered["planner"],
        analyst_model=metered["analyst"],
        synthesizer_model=metered["synthesizer"],
        verifier_model=metered["verifier"],
        profile=profile,
        model_trace=model_trace,
    )
    started = time.perf_counter()
    state = graph.invoke(_empty_multi_agent_state(str(case["query"]), run_id=run_id, thread_id=run_id))
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    artifacts = write_report_artifacts(str(case["query"]), state, output_dir / run_id)
    judgement = {}
    if judge:
        judge_timeout = min(60, max(45, profile.model_timeout_seconds))
        judge_model = BoundedChatModel(
            create_chat_model(
                judge_preset,
                max_tokens=3200,
                timeout=judge_timeout,
                max_retries=0,
            ),
            judge_timeout,
        )
        judgement = _judge_result(case, state, judge_model)
    evidence = _json_object(str(state.get("_evidence_json") or ""))
    findings = state.get("_factcheck_findings") or {}
    from conflux.p1_evaluation import deterministic_output_rubric

    output_rubric = deterministic_output_rubric(
        str(state.get("final_answer") or ""),
        case.get("required_dimensions") or [],
    )
    if case.get("require_all_dimensions") and output_rubric["coverage_ratio"] < 1.0:
        output_rubric["passed"] = False
    quality = _apply_judge_gate(state.get("_quality_report") or {}, judgement, enabled=judge)
    if not output_rubric["passed"]:
        quality["passed"] = False
        quality.setdefault("notes", []).append(
            "反窄短 Rubric 未通过："
            f"广度 {output_rubric['breadth']}/5、深度 {output_rubric['depth']}/5、"
            f"案例 {output_rubric['case_specificity']}/5、建议 {output_rubric['recommendation_value']}/5"
        )
    source_diversity = _external_source_metrics(
        evidence.get("nodes") or [],
        state.get("_source_statuses") or {},
    )
    minimum_external = int(case.get("minimum_external_evidence") or 0)
    minimum_independent = int(case.get("minimum_independent_sources") or 0)
    if source_diversity["external_evidence_count"] < minimum_external:
        quality["passed"] = False
        quality.setdefault("notes", []).append(
            f"有效外部证据不足：{source_diversity['external_evidence_count']}/{minimum_external}"
        )
    if source_diversity["independent_source_count"] < minimum_independent:
        quality["passed"] = False
        quality.setdefault("notes", []).append(
            f"独立外部来源不足：{source_diversity['independent_source_count']}/{minimum_independent}"
        )
    return {
        "case_id": case["id"],
        "category": case.get("category"),
        "query": case["query"],
        "depth": depth,
        "scenario": scenario,
        "model_trace": model_trace,
        "elapsed_ms": elapsed_ms,
        "usage": meter.summary(),
        "quality": quality,
        "judge": judgement,
        "output_rubric": output_rubric,
        "factcheck_status": state.get("_factcheck_status"),
        "citation_metrics": {
            "verified_claim_ratio": findings.get("verified_claim_ratio", 0.0),
            "valid": findings.get("valid_citation_count", 0),
            "invalid": findings.get("invalid_citation_count", 0),
        },
        "evidence_count": len(evidence.get("nodes") or []),
        "source_diversity": source_diversity,
        "source_statuses": {
            source: (payload or {}).get("status")
            for source, payload in (state.get("_source_statuses") or {}).items()
            if source in {"RAG", "Web", "Model"}
        },
        "gap_iterations": state.get("_gap_iteration", 0),
        "report_path": str(artifacts.markdown_path),
        "audit_path": str(artifacts.audit_markdown_path or ""),
        "answer": str(state.get("final_answer") or ""),
    }


def _apply_judge_gate(quality: dict[str, Any], judgement: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    """Make the independent blind score part of the real P1 exit gate."""

    result = {**quality, "notes": list(quality.get("notes") or [])}
    if not enabled:
        return result
    if str(judgement.get("status") or "").casefold() == "unreviewed":
        result["passed"] = False
        result["notes"].append(
            "匿名成对盲评未完成：" + str(judgement.get("error") or "评审模型未返回有效结构化结果")
        )
        return result
    if "passed" in judgement:
        if not bool(judgement.get("passed")):
            result["passed"] = False
            scores = judgement.get("candidate_scores") or {}
            result["notes"].append(
                "匿名成对盲评未达到参考基线："
                + "、".join(f"{key}={value}/5" for key, value in scores.items())
            )
        return result
    try:
        overall = int(judgement.get("overall") or 0)
    except (TypeError, ValueError):
        overall = 0
    if overall < 4:
        result["passed"] = False
        result["notes"].append(f"独立盲评低于达标线：{overall}/5")
    return result


def _real_case_worker(
    result_queue: Any,
    case: dict[str, Any],
    depth: str,
    scenario: str,
    judge: bool,
    judge_preset: str,
    output_dir: str,
    run_id: str,
) -> None:
    try:
        result_queue.put({
            "ok": True,
            "result": run_real_case(
                case,
                depth,
                scenario,
                judge=judge,
                judge_preset=judge_preset,
                output_dir=Path(output_dir),
                run_id=run_id,
            ),
        })
    except BaseException as exc:
        result_queue.put({
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        })


def run_real_case_with_timeout(
    case: dict[str, Any],
    depth: str,
    scenario: str,
    *,
    judge: bool,
    judge_preset: str,
    output_dir: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Run one real case in an isolated process with a hard profile deadline."""

    context = mp.get_context("spawn")
    run_id = f"eval-{case['id']}-{depth}-{scenario}-{int(time.time())}"
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_real_case_worker,
        args=(result_queue, case, depth, scenario, judge, judge_preset, str(output_dir), run_id),
        daemon=False,
    )
    process.start()
    deadline = time.monotonic() + timeout_seconds
    payload: dict[str, Any] | None = None
    while payload is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            payload = result_queue.get(timeout=min(0.5, remaining))
        except queue.Empty:
            if not process.is_alive():
                break

    if payload is None and process.is_alive():
        process.terminate()
        process.join(5)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(5)
        result_queue.close()
        result_queue.join_thread()
        trace_path = output_dir / run_id / "live_usage.jsonl"
        calls = _read_usage_trace(trace_path)
        error = f"TimeoutError: research profile deadline exceeded: {timeout_seconds}s"
        return {
            "case_id": case["id"],
            "category": case.get("category"),
            "query": case.get("query"),
            "depth": depth,
            "scenario": scenario,
            "elapsed_ms": timeout_seconds * 1000,
            "usage": _usage_summary(calls),
            "quality": {"passed": False, "notes": [error]},
            "error": error,
            "live_usage_path": str(trace_path),
        }

    process.join(5)
    if process.is_alive():
        process.terminate()
        process.join(5)
    result_queue.close()
    result_queue.join_thread()

    if payload is None:
        raise RuntimeError(f"evaluation worker exited without a result (exitcode={process.exitcode})")

    if not payload.get("ok"):
        raise RuntimeError(str(payload.get("error") or "evaluation worker failed"))
    return dict(payload["result"])


def _read_usage_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    calls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            calls.append(item)
    return calls


def _usage_summary(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "call_count": len(calls),
        "input_tokens": sum(int(item.get("input_tokens") or 0) for item in calls),
        "output_tokens": sum(int(item.get("output_tokens") or 0) for item in calls),
        "total_tokens": sum(int(item.get("total_tokens") or 0) for item in calls),
        "estimated_cost_usd": None,
        "cost_note": "硬超时前已完成调用的部分统计。",
        "calls": calls,
    }


def _scenario_sources(scenario: str) -> tuple[set[str], set[str]]:
    mapping = {
        "model_only": (set(), set()),
        "model_rag": ({"RAG"}, set()),
        "model_web": ({"Web"}, set()),
        "full": ({"RAG", "Web"}, set()),
        "rag_failure": ({"RAG", "Web"}, {"RAG"}),
        "web_failure": ({"RAG", "Web"}, {"Web"}),
    }
    return mapping[scenario]


def _unavailable_tool(source: str, *, failed: bool):
    status = "failed" if failed else "no_evidence"

    @tool(f"eval_{source.casefold()}_{status}")
    def unavailable(query: str) -> str:
        """Return an explicit evaluation source outage or disabled result."""
        return SourceResult(
            source=source,
            status=status,
            detail="P1 evaluation ablation",
            error="injected source failure" if failed else "source disabled for ablation",
            content=f"{source} unavailable in this evaluation scenario.",
            metadata={"disabled": not failed, "evaluation_scenario": True},
        ).to_tool_text()

    from conflux.source_status import SourceResult
    return unavailable


def _judge_result(case: dict[str, Any], state: dict[str, Any], model: Any) -> dict[str, Any]:
    evidence = _json_object(str(state.get("_evidence_json") or ""))
    from conflux.graph_p1 import _evidence_selection_query, _select_evidence

    compact_nodes = _select_evidence(
        [item for item in evidence.get("nodes") or [] if isinstance(item, dict)],
        12,
        query=_evidence_selection_query(state),
    )
    compact_evidence_rows = [
        {
            key: item.get(key)
            for key in (
                "id", "claim", "verbatim_quote", "document_title", "paper_id",
                "url", "evidence_refs", "evidence_class", "published_at",
            )
        }
        for item in compact_nodes
    ]
    compact_evidence = _bounded_json_array(compact_evidence_rows, 16000)
    reference_path = str(case.get("reference_report") or "").strip()
    pair = None
    if reference_path:
        from conflux.p1_evaluation import (
            PAIRWISE_SYSTEM,
            build_anonymous_pair,
            build_pairwise_prompt,
            normalize_pairwise_judgement,
        )

        reference = (ROOT / reference_path).read_text(encoding="utf-8")
        pair = build_anonymous_pair(
            str(case["query"]),
            str(state.get("final_answer") or "")[:16000],
            reference[:16000],
            case.get("required_dimensions") or [],
            seed=str(case.get("id") or "p1"),
        )
        system = PAIRWISE_SYSTEM
        prompt = build_pairwise_prompt(pair, _bounded_json_array(compact_evidence_rows, 8000))
    else:
        system = JUDGE_SYSTEM
        prompt = JUDGE_TEMPLATE.format(
            query=case["query"],
            dimensions="、".join(str(item) for item in case.get("required_dimensions") or []),
            answer=str(state.get("final_answer") or "")[:16000],
            evidence=compact_evidence,
        )
    started = time.perf_counter()
    response = model.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    raw = str(response.content if hasattr(response, "content") else response)
    payload = _json_object(raw)
    if pair is not None and not _valid_pairwise_payload(payload):
        judged = {
            "status": "unreviewed",
            "passed": False,
            "error": "评审模型未返回完整的匿名成对评分 JSON",
            "anonymous_order": {"candidate": pair.candidate_label, "reference": pair.reference_label},
        }
    else:
        judged = normalize_pairwise_judgement(payload, pair) if pair is not None else payload
    return {
        **judged,
        "judge_model": str(getattr(model, "model_name", None) or getattr(model, "model", None) or "verifier"),
        "prompt_sha256": hashlib.sha256((system + prompt).encode("utf-8")).hexdigest(),
        "input_sha256": hashlib.sha256((str(case["query"]) + str(state.get("final_answer") or "") + compact_evidence).encode("utf-8")).hexdigest(),
        "elapsed_ms": elapsed_ms,
        "raw": raw[:2000] if not payload or judged.get("status") == "unreviewed" else "",
    }


def _valid_pairwise_payload(payload: dict[str, Any]) -> bool:
    from conflux.p1_evaluation import RUBRIC_DIMENSIONS

    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return False
    for dimension in RUBRIC_DIMENSIONS:
        row = scores.get(dimension)
        if not isinstance(row, dict) or not {"A", "B"} <= set(row):
            return False
        try:
            if any(not 1 <= int(row[label]) <= 5 for label in ("A", "B")):
                return False
        except (TypeError, ValueError):
            return False
    return str(payload.get("preference") or "").upper() in {"A", "B", "TIE"}


def _bounded_json_array(items: list[dict[str, Any]], max_chars: int) -> str:
    """Keep judge evidence valid JSON while respecting a prompt-size ceiling."""

    selected: list[dict[str, Any]] = []
    for item in items:
        candidate = json.dumps([*selected, item], ensure_ascii=False)
        if len(candidate) > max_chars and selected:
            break
        selected.append(item)
    return json.dumps(selected, ensure_ascii=False)


def _external_source_metrics(
    nodes: list[dict[str, Any]],
    statuses: dict[str, Any] | None = None,
) -> dict[str, Any]:
    statuses = statuses or {}

    def source_succeeded(item: dict[str, Any]) -> bool:
        source = str(item.get("source") or "").casefold()
        label = "Web" if "web" in source else "RAG" if "rag" in source else ""
        return not label or not statuses or str((statuses.get(label) or {}).get("status") or "") == "success"

    external = [
        item for item in nodes
        if any(str(ref).startswith(("[RAG:", "[Web:")) for ref in item.get("evidence_refs") or [])
        and str(item.get("evidence_class") or "").casefold() != "model_inference"
        and source_succeeded(item)
    ]
    identities: set[str] = set()
    for item in external:
        raw = " ".join([
            str(item.get("paper_id") or ""),
            str(item.get("url") or ""),
            " ".join(str(ref) for ref in item.get("evidence_refs") or []),
        ]).casefold()
        arxiv = re.search(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?", raw)
        doi = re.search(r"10\.\d{4,9}/[^\s\]\"']+", raw)
        if arxiv:
            identity = f"arxiv:{arxiv.group(1)}"
        elif doi:
            identity = f"doi:{doi.group(0).rstrip('.,;')}"
        else:
            identity = str(item.get("paper_id") or item.get("url") or (item.get("evidence_refs") or [""])[0])
        if identity:
            identities.add(identity.casefold())
    return {
        "external_evidence_count": len(external),
        "independent_source_count": len(identities),
        "identities": sorted(identities),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault(f"{result['depth']}:{result['scenario']}", []).append(result)
    summary = {}
    for key, rows in groups.items():
        latencies = [float(item["elapsed_ms"]) for item in rows]
        judge_scores = [
            float((item.get("judge") or {}).get("candidate_overall") or (item.get("judge") or {}).get("overall"))
            for item in rows
            if (item.get("judge") or {}).get("candidate_overall") or (item.get("judge") or {}).get("overall")
        ]
        summary[key] = {
            "runs": len(rows),
            "quality_pass_rate": round(sum(bool((item.get("quality") or {}).get("passed")) for item in rows) / len(rows), 3),
            "judge_overall_median": round(statistics.median(judge_scores), 3) if judge_scores else None,
            "citation_invalid": sum(int((item.get("citation_metrics") or {}).get("invalid") or 0) for item in rows),
            "citation_coverage_mean": round(statistics.mean(float((item.get("citation_metrics") or {}).get("verified_claim_ratio") or 0) for item in rows), 3),
            "latency_p50_ms": round(statistics.median(latencies), 2),
            "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
            "total_tokens": sum(int((item.get("usage") or {}).get("total_tokens") or 0) for item in rows),
            "failures": [item["case_id"] for item in rows if not (item.get("quality") or {}).get("passed")],
        }
    return summary


def write_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "p1_eval.json"
    md_path = out_dir / "p1_eval.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    validation = payload["dataset_validation"]
    lines = [
        "# P1 研究质量评测",
        "",
        f"- 评测集：{validation['case_count']} 问",
        f"- 数据集校验：{'通过' if validation['passed'] else '失败'}",
        f"- 完整消融矩阵：{validation['matrix_run_count']} 个运行组合",
        f"- 本次真实运行：{len(payload.get('results') or [])} 个",
        "",
        "## 分组结果",
        "",
        "| 分组 | 运行 | 质量通过率 | 盲评中位数 | 引用覆盖 | 无效引用 | p50 ms | p95 ms | Token |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, item in (payload.get("summary") or {}).items():
        lines.append(
            f"| {key} | {item['runs']} | {item['quality_pass_rate']:.0%} | "
            f"{item['judge_overall_median'] if item['judge_overall_median'] is not None else 'n/a'} | "
            f"{item['citation_coverage_mean']:.0%} | {item['citation_invalid']} | "
            f"{item['latency_p50_ms']} | {item['latency_p95_ms']} | {item['total_tokens']} |"
        )
    failures = [item for item in payload.get("results") or [] if not (item.get("quality") or {}).get("passed")]
    lines.extend(["", "## 失败样本", ""])
    lines.extend(
        f"- {item['case_id']} / {item['depth']} / {item['scenario']}："
        f"{'; '.join((item.get('quality') or {}).get('notes') or ['未通过质量门禁'])}"
        for item in failures
    )
    if not failures:
        lines.append("- 本次没有失败样本；离线校验不计为答案质量通过。")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def _json_object(text: str) -> dict[str, Any]:
    start, end = str(text).find("{"), str(text).rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        value = json.loads(str(text)[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _first_int(*payloads: dict[str, Any], keys: tuple[str, ...]) -> int:
    for payload in payloads:
        for key in keys:
            try:
                if payload.get(key) is not None:
                    return int(payload[key])
            except (TypeError, ValueError):
                continue
    return 0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * quantile) - 1))
    return ordered[index]


def _evaluation_succeeded(validation: dict[str, Any], results: list[dict[str, Any]], *, real: bool) -> bool:
    return bool(validation.get("passed")) and all(not item.get("error") for item in results) and (
        not real or all(bool((item.get("quality") or {}).get("passed")) for item in results)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P1 research-quality evaluation.")
    parser.add_argument("--dataset", default="data/p1_research_eval.yaml")
    parser.add_argument("--out-dir", default="reports/eval/p1")
    parser.add_argument("--real", action="store_true", help="Call configured model/search/embedding APIs")
    parser.add_argument("--limit", type=int, default=0, help="Limit selected cases; 0 means all")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--depths", nargs="+", choices=DEPTHS, default=list(DEPTHS))
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument(
        "--judge-preset",
        default="cheap",
        help="Configured model preset used for independent answer judging",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=0,
        help="Override the per-run hard deadline; 0 uses the research profile budget",
    )
    args = parser.parse_args()

    cases = load_dataset(ROOT / args.dataset)
    validation = validate_dataset(cases)
    selected = [item for item in cases if not args.case_id or item.get("id") in set(args.case_id)]
    if args.limit > 0:
        selected = selected[: args.limit]
    results = []
    if args.real:
        load_dotenv(ROOT / ".env", override=False)
        load_dotenv(ROOT / ".env.workbench", override=False)
        from conflux.research_modes import resolve_research_profile

        for case in selected:
            for depth in args.depths:
                for scenario in args.scenarios:
                    print(f"Running {case['id']} depth={depth} scenario={scenario}", flush=True)
                    profile_timeout = args.timeout_seconds or resolve_research_profile(depth).timeout_seconds
                    timeout_seconds = profile_timeout + (60 if not args.no_judge else 0)
                    try:
                        result = run_real_case_with_timeout(
                            case,
                            depth,
                            scenario,
                            judge=not args.no_judge,
                            judge_preset=args.judge_preset,
                            output_dir=ROOT / args.out_dir / "runs",
                            timeout_seconds=timeout_seconds,
                        )
                        results.append(result)
                    except Exception as exc:
                        results.append({
                            "case_id": case["id"],
                            "category": case.get("category"),
                            "query": case.get("query"),
                            "depth": depth,
                            "scenario": scenario,
                            "elapsed_ms": 0,
                            "quality": {"passed": False, "notes": [f"{type(exc).__name__}: {exc}"]},
                            "error": f"{type(exc).__name__}: {exc}",
                        })
    payload = {
        "dataset": str(args.dataset),
        "dataset_sha256": hashlib.sha256((ROOT / args.dataset).read_bytes()).hexdigest(),
        "dataset_validation": validation,
        "real_api": bool(args.real),
        "results": results,
        "summary": aggregate(results),
    }
    md_path, json_path = write_outputs(payload, ROOT / args.out_dir)
    print(f"P1 eval Markdown: {md_path}")
    print(f"P1 eval JSON: {json_path}")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if _evaluation_succeeded(validation, results, real=bool(args.real)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
