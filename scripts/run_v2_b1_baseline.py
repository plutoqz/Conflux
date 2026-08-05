# -*- coding: utf-8 -*-
"""B1 基线重建（§8.10 基线顺序：B0 当前系统 → B1 修复 V2 wiring）。

在修复 V2 wiring（查询改写器 / 重排器 / RAG-Web 工具实际接线）之后，
用与 B0 完全相同的 3 个代表案例重跑 answer_first 管道，盲评后生成
B1 批次，并与 B0（reports/evaluation/v2_batch_deepseek/batch_result.json）
做同案例对比，产出 docs/benchmarks/B1基线快照.md。

用法：
    python scripts/run_v2_b1_baseline.py [--skip-pipeline] [--skip-review]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.evaluation_v2 import (  # noqa: E402
    V2_REVIEW_DIMENSIONS as RUBRIC_DIMENSIONS,
    build_v2_review_prompt,
    build_v2_run_record,
    evaluate_v2_batch,
    normalize_v2_review,
)
from conflux.p1_evaluation import PAIRWISE_SYSTEM  # noqa: E402

B0_RESULT = PROJECT_ROOT / "reports" / "evaluation" / "v2_batch_deepseek" / "batch_result.json"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "evaluation" / "v2_batch_b1"
RESULT_FILE = OUTPUT_DIR / "batch_result.json"
SNAPSHOT_FILE = PROJECT_ROOT / "docs" / "benchmarks" / "B1基线快照.md"

# 与 B0 相同的案例集，保证同案例可比
CASES = [
    {"id": "policy-ai-governance", "query": "高影响公共决策中的生成式AI治理目前存在哪些主要制度与实施缺口？"},
    {"id": "gis-architecture-design", "query": "如何设计一个可审计、可恢复的LLM驱动GIS自动化架构？"},
    {"id": "materials-method-comparison", "query": "材料发现中图神经网络与等变神经网络的证据、适用边界和计算取舍有何差异？"},
]

CASE_QUERY_BY_ID = {c["id"]: c["query"] for c in CASES}


def run_case(case_id: str, query: str) -> dict:
    case_dir = OUTPUT_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    for old in case_dir.glob("*.summary.json"):
        old.unlink()
    started = time.time()
    try:
        proc = subprocess.run(
            [
                sys.executable, "-m", "conflux", "research",
                "--query", query,
                "--depth", "standard",
                "--trace-dir", str(case_dir),
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return {"case_id": case_id, "error": "timeout", "elapsed_s": round(time.time() - started, 1)}
    elapsed = time.time() - started
    if proc.returncode != 0:
        print(f"  [warn] pipeline exit={proc.returncode}: {(proc.stderr or '').splitlines()[-3:]}")
    summaries = sorted(case_dir.glob("*.summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not summaries:
        print(f"  [fail] no summary for {case_id}")
        print("  stdout tail:", (proc.stdout or "").splitlines()[-8:])
        return {"case_id": case_id, "error": "no_summary", "elapsed_s": round(elapsed, 1)}
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    summary["_b1_elapsed_s"] = round(elapsed, 1)
    return summary


def blind_review(query: str, report: str) -> dict:
    from conflux.model_factory import create_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    model = create_chat_model("balanced")
    prompt = build_v2_review_prompt(query, report, evaluation_date=date.today().isoformat())
    try:
        response = model.invoke([
            SystemMessage(content=PAIRWISE_SYSTEM),
            HumanMessage(content=prompt),
        ])
        text = str(response.content) if hasattr(response, "content") else str(response)
    except Exception as exc:
        return {"scores": {d: 1 for d in RUBRIC_DIMENSIONS}, "overall": 1.0,
                "reason": f"LLM call failed: {exc}", "is_empty": True}
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"scores": {d: 1 for d in RUBRIC_DIMENSIONS}, "overall": 1.0,
                    "reason": f"JSON parse failed: {text[:200]}", "is_empty": True}
        try:
            payload = json.loads(match.group())
        except json.JSONDecodeError:
            return {"scores": {d: 1 for d in RUBRIC_DIMENSIONS}, "overall": 1.0,
                    "reason": f"JSON parse failed: {text[:200]}", "is_empty": True}
    return normalize_v2_review(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-pipeline", action="store_true", help="复用已有 summary，跳过重跑管道")
    parser.add_argument("--skip-review", action="store_true", help="跳过盲评（只出确定性指标）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, dict] = {}
    for case in CASES:
        case_id = case["id"]
        query = case["query"]
        print(f"\n[{case_id}] {query[:60]}...")
        if not args.skip_pipeline:
            summary = run_case(case_id, query)
            if "error" in summary:
                print(f"  [fail] {summary['error']}")
                continue
        else:
            candidates = sorted((OUTPUT_DIR / case_id).glob("*.summary.json"),
                                key=lambda p: p.stat().st_mtime, reverse=True)
            if not candidates:
                print(f"  [fail] no existing summary for {case_id}")
                continue
            summary = json.loads(candidates[0].read_text(encoding="utf-8"))
        summaries[case_id] = summary
        print(f"  status={summary.get('run_status')} conf={summary.get('confidence')} "
              f"off_domain={summary.get('off_domain_evidence_in_report')} "
              f"invalid_cit={summary.get('invalid_citation_count')}")

    if not summaries:
        print("No runs succeeded.")
        return 1

    # 确定性记录
    case_records = []
    for case in CASES:
        summary = summaries.get(case["id"])
        if not summary:
            continue
        record = build_v2_run_record(
            {"id": case["id"], "query": case["query"], "domain": "baseline", "category": "baseline"},
            summary,
        )
        record["elapsed_s"] = summary.get("_b1_elapsed_s", 0)
        case_records.append(record)

    # 盲评
    reviews = []
    if not args.skip_review:
        for case in CASES:
            summary = summaries.get(case["id"])
            if not summary:
                continue
            report_md = summary.get("report_markdown") or ""
            if not report_md and summary.get("report_md_path") and Path(summary["report_md_path"]).exists():
                report_md = Path(summary["report_md_path"]).read_text(encoding="utf-8")
            print(f"  reviewing {case['id']} (len={len(report_md)})...")
            review = blind_review(case["query"], report_md)
            review["case_id"] = case["id"]
            reviews.append(review)

    batch = evaluate_v2_batch(case_records, reviews)
    batch.update({
        "batch_date": datetime.now().isoformat(),
        "pipeline": "answer_first",
        "depth": "standard",
        "label": "B1 (V2 wiring 修复后)",
        "cases": [
            {
                "case_id": r["case_id"],
                "run_status": r["run_status"],
                "confidence": r["confidence"],
                "report_len": r["report_length_chars"],
                "elapsed_s": r.get("elapsed_s"),
                "deterministic_failures": r["deterministic_failures"],
                "review": next((rv for rv in reviews if rv.get("case_id") == r["case_id"]), None),
            }
            for r in case_records
        ],
    })

    # B0 对比
    b0 = json.loads(B0_RESULT.read_text(encoding="utf-8")) if B0_RESULT.exists() else {}
    b0_by_case = {c["case_id"]: c for c in b0.get("cases", [])}
    per_case = []
    for case in CASES:
        old = b0_by_case.get(case["id"])
        new_record = next((r for r in case_records if r["case_id"] == case["id"]), None)
        new_review = next((rv for rv in reviews if rv.get("case_id") == case["id"]), None)
        new_summary = summaries.get(case["id"]) or {}
        per_case.append({
            "case_id": case["id"],
            "b0": {"run_status": old.get("run_status") if old else None,
                   "overall": old.get("overall") if old else None,
                   "report_len": old.get("report_len") if old else None,
                   "elapsed_s": old.get("elapsed_s") if old else None} if old else None,
            "b1": {"run_status": new_record["run_status"] if new_record else None,
                   "overall": new_review.get("overall") if new_review else None,
                   "report_len": new_record["report_length_chars"] if new_record else None,
                   "elapsed_s": new_record.get("elapsed_s") if new_record else None,
                   "off_domain_evidence_in_report": int(
                       new_summary.get("off_domain_evidence_in_report") or 0),
                   "invalid_citation_count": int(
                       new_summary.get("invalid_citation_count") or 0),
                   "deterministic_failures": new_record["deterministic_failures"] if new_record else None
                   } if new_record else None,
        })
    batch["b0_vs_b1"] = {
        "b0_batch_date": b0.get("batch_date", ""),
        "b0_avg_overall": b0.get("avg_overall_score"),
        "b1_avg_overall": batch.get("blind_review_overall_median"),
        "b0_run_count": b0.get("run_count"),
        "b1_run_count": batch.get("run_count"),
        "per_case": per_case,
    }

    RESULT_FILE.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote: {RESULT_FILE}")
    print(f"B1 median overall: {batch.get('blind_review_overall_median')}, "
          f"deterministic_passed: {batch.get('deterministic_passed')}")
    write_snapshot(batch, b0)
    return 0


def write_snapshot(batch: dict, b0: dict) -> None:
    lines = [
        "# B1 基线快照 —— V2 wiring 修复后",
        "",
        f"> 日期：{datetime.now().strftime('%Y-%m-%d')}",
        f"> 基线顺序（§8.10）：B0 当前系统 → **B1 修复 V2 wiring** → B2 按子问题检索 + EvidenceLedger → ...",
        f"> 本次改动：查询改写器 / 语义重排器 / RAG-Web 工具实际 wiring 修复；"
        f"无关引用必须失败 + 无主题重叠不分配全局引用两个回归测试固化",
        f"> 方法：与 B0 相同 3 个代表案例，standard 深度，盲评 6 维 rubric",
        "",
        "## 1. B0 vs B1 同案例对比",
        "",
        "| case_id | B0 overall | B1 overall | B0 run_status | B1 run_status | B1 off_domain | B1 确定性失败 |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in (batch.get("b0_vs_b1") or {}).get("per_case", []):
        old_case = entry.get("b0") or {}
        new_case = entry.get("b1") or {}
        b0_overall = old_case.get("overall") if old_case.get("overall") is not None else "-"
        b1_det_fail = ";".join(new_case.get("deterministic_failures") or []) or "-"
        lines.append(
            f"| {entry['case_id']} | {b0_overall} | {new_case.get('overall', '-')} | "
            f"{old_case.get('run_status', '-')} | {new_case.get('run_status', '-')} | "
            f"{new_case.get('off_domain_evidence_in_report', 0)} | {b1_det_fail} |"
        )
    b0_cases = b0.get("cases") or []
    b0_avg_len = (
        round(sum(int(c.get("report_len") or 0) for c in b0_cases) / len(b0_cases))
        if b0_cases else "-"
    )
    lines += [
        "",
        "## 2. 批次汇总",
        "",
        "| 指标 | B0 | B1 |",
        "|---|---|---|",
        f"| 平均盲评 overall | {b0.get('avg_overall_score', '-')} | {batch.get('blind_review_overall_median', '-')} |",
        f"| 报告可用（run_count） | {b0.get('run_count', '-')} | {batch.get('run_count', '-')} |",
        f"| confidence high | {sum(1 for c in b0_cases if c.get('confidence') == 'high')} | {batch.get('confidence_high')} |",
        f"| 平均报告长度（chars） | {b0_avg_len} | {round(batch.get('avg_report_length', 0)) if batch.get('avg_report_length') else '-'} |",
        "",
        "## 3. B1 确定性门禁",
        "",
        f"- deterministic_passed：**{batch.get('deterministic_passed')}**",
        "- off_domain_evidence_in_report（各案例）："
        + " / ".join(
            str((c.get("b1") or {}).get("off_domain_evidence_in_report", 0))
            for c in (batch.get("b0_vs_b1") or {}).get("per_case", [])
        ),
        "- invalid_citation_count（各案例）："
        + " / ".join(
            str((c.get("b1") or {}).get("invalid_citation_count", 0))
            for c in (batch.get("b0_vs_b1") or {}).get("per_case", [])
        ),
        "",
        "## 4. 结论",
        "",
        "- wiring 修复目标：查询改写器、语义重排器、run_id 正确传入 RAG/Web 工具（`create_v2_research_graph`）。",
        "- 两个回归测试（`tests/test_v3_regression_offdomain.py`，12 例）已固化：无关引用必须失败、无主题重叠不得分配全局引用。",
        "- 下一步（§8.11.3+）：EvidenceLedger 建立、按子问题独立检索（Round 0/Barrier/一次纠偏）、Model 三模式隔离。",
        "",
        f"> 批次详情：`reports/evaluation/v2_batch_b1/batch_result.json`（B0 对照：`reports/evaluation/v2_batch_deepseek/batch_result.json`）",
    ]
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {SNAPSHOT_FILE}")


if __name__ == "__main__":
    raise SystemExit(main())
