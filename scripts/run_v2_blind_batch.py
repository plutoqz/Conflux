# -*- coding: utf-8 -*-
"""V2 batch blind evaluation with deepseek-v4-flash.

Runs V2 answer_first pipeline on remaining 9 representative cases,
blind-reviews each report, and stops after 3 consecutive successes.

Usage:
    python scripts/run_v2_blind_batch.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = PROJECT_ROOT / "evaluation" / "generalized_research_representative_set.json"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "evaluation" / "v2_batch_deepseek"
RESULT_FILE = OUTPUT_DIR / "batch_result.json"

ALREADY_RUN = {"gis-limitations", "software-agent-limitations", "empty-rag-policy"}

RUBRIC_DIMENSIONS = (
    "factual_citation_match",
    "scope_and_coverage",
    "mechanism_rigor",
    "quantitative_and_implementation_detail",
    "comparative_synthesis",
    "decision_value",
)

BLIND_SYSTEM = (
    "You are an independent research quality reviewer. Score the report objectively. "
    "Output valid JSON only, no markdown or commentary."
)

BLIND_PROMPT_TEMPLATE = """Score each dimension 1-5 (1=poor, 5=excellent):

- factual_citation_match: 1=core factual errors; 3=mostly correct but overconfident; 5=key facts, boundaries and citations all accurate.
- scope_and_coverage: 1=covers only one narrow area; 3=covers about half of important dimensions; 5=all important dimensions have substance.
- mechanism_rigor: 1=lists conclusions only; 3=some causal explanation; 5=persistent mechanism, cause-effect, tradeoffs, boundaries.
- quantitative_and_implementation_detail: 1=no concrete examples/data; 3=few weakly-connected examples; 5=core dimensions have direct verifiable cases.
- comparative_synthesis: 1=fragmented or source-stitched; 3=cross-dimension links but repetitive; 5=coherent whole with cross-section comparison and synthesis.
- decision_value: 1=no suggestions or sloganeering; 3=relevant suggestions but lack conditions; 5=actionable with priority, conditions and tradeoffs.

Output ONLY this JSON (1-5 integers for each dimension):
{"scores":{"factual_citation_match":3,"scope_and_coverage":3,"mechanism_rigor":3,"quantitative_and_implementation_detail":3,"comparative_synthesis":3,"decision_value":3},"overall":3.0,"reason":"brief comment","is_empty":false}

Evaluation date: {date}
Research question: {query}

Report text:
{report}

Notes:
- If the report is nearly empty (<200 chars of body), set is_empty=true, all scores=1
- Content marked as "analysis judgment" or "model analysis" should NOT be penalized, but score 2-3 if lacking concrete evidence
- Do NOT penalize short reports if they substantively answer the core question
"""

SUCCESS_THRESHOLD = 3.0


def main() -> int:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    pending = [c for c in cases if c["id"] not in ALREADY_RUN]
    print(f"Total cases: {len(cases)}, Already run: {len(ALREADY_RUN)}, Pending: {len(pending)}")
    print(f"Output dir: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    consecutive_success = 0
    batch_started = datetime.now()

    for i, case in enumerate(pending):
        case_id = case["id"]
        query = case["query"]
        print(f"\n[{i+1}/{len(pending)}] {case_id}: {query[:80]}...")
        sys.stdout.flush()

        case_dir = OUTPUT_DIR / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        # Clean previous runs for this case
        for old in case_dir.glob("*.summary.json"):
            old.unlink()

        print(f"  Running V2 answer_first pipeline...")
        sys.stdout.flush()

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
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            print(f"  [FAIL] Pipeline timed out after 600s")
            results.append(_fail_entry(case_id, query, time.time() - started, "timeout"))
            consecutive_success = 0
            continue

        elapsed = time.time() - started

        if proc.returncode != 0:
            print(f"  [FAIL] Pipeline exit={proc.returncode}")
            stderr_tail = proc.stderr.strip().splitlines()[-8:] if proc.stderr else ["(no stderr)"]
            for line in stderr_tail:
                print(f"    stderr: {line[:200]}")
            sys.stdout.flush()
            # Try to find summary anyway - sometimes exit code is non-zero but output exists
            pass

        # Find the summary.json file
        summary_files = sorted(case_dir.glob("*.summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not summary_files:
            print(f"  [FAIL] No summary.json found in {case_dir}")
            # Print stdout tail for diagnostics
            stdout_lines = proc.stdout.strip().splitlines()[-10:] if proc.stdout else []
            for line in stdout_lines:
                print(f"    stdout: {line[:200]}")
            results.append(_fail_entry(case_id, query, elapsed, "no_summary"))
            consecutive_success = 0
            continue

        summary = json.loads(summary_files[0].read_text(encoding="utf-8"))
        run_status = summary.get("run_status", "unknown")
        report_available = summary.get("report_available", False)
        confidence = summary.get("confidence", "unverified")

        # Get the report text
        report_text = ""
        report_md_path = summary.get("report_md_path", "")
        if report_md_path and Path(report_md_path).exists():
            report_text = Path(report_md_path).read_text(encoding="utf-8")
        else:
            report_text = summary.get("final_answer", "")

        report_len = len(report_text)
        print(f"  Pipeline: status={run_status}, report_avail={report_available}, "
              f"conf={confidence}, report_len={report_len}, elapsed={elapsed:.1f}s")
        sys.stdout.flush()

        # Blind review
        print(f"  Running blind review...")
        sys.stdout.flush()
        review = _blind_review_single(query, report_text)
        scores = review.get("scores", {})
        overall = float(review.get("overall", 0.0))
        is_empty = bool(review.get("is_empty", False))

        success = overall >= SUCCESS_THRESHOLD and not is_empty
        if success:
            consecutive_success += 1
        else:
            consecutive_success = 0

        score_str = ", ".join(f"{k}={v}" for k, v in scores.items())
        status_mark = "PASS" if success else "FAIL"
        print(f"  Scores: {score_str}")
        print(f"  Overall: {overall:.1f}, Empty: {is_empty}, "
              f"Status: {status_mark}, Streak: {consecutive_success}")
        sys.stdout.flush()

        result_entry = {
            "case_id": case_id,
            "query": query,
            "run_status": run_status,
            "report_available": report_available,
            "confidence": confidence,
            "report_len": report_len,
            "elapsed_s": round(elapsed, 1),
            "scores": scores,
            "overall": overall,
            "is_empty": is_empty,
            "success": success,
            "reason": review.get("reason", ""),
            "summary_path": str(summary_files[0]),
        }
        results.append(result_entry)

        if consecutive_success >= 3:
            print(f"\n  *** 3 consecutive successes! Stopping batch. ***")
            break

    # Aggregate results
    batch_elapsed = (datetime.now() - batch_started).total_seconds()
    total = len(results)
    success_count = sum(1 for r in results if r.get("success"))
    run_count = sum(1 for r in results if r.get("run_status") not in ("failed", "no_summary", "timeout"))
    overall_scores = [r["overall"] for r in results if r.get("overall", 0) > 0]
    avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0

    batch_result = {
        "batch_date": datetime.now().isoformat(),
        "model": "deepseek-v4-flash",
        "pipeline": "answer_first",
        "depth": "standard",
        "total_pending": len(pending),
        "cases_run": total,
        "success_count": success_count,
        "run_count": run_count,
        "avg_overall_score": round(avg_score, 2),
        "consecutive_success_streak": consecutive_success,
        "stopped_early": consecutive_success >= 3,
        "batch_elapsed_s": round(batch_elapsed, 1),
        "cases": results,
    }

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(batch_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Batch complete: {total} cases run, {success_count} successes, "
          f"avg score {avg_score:.2f}, streak {consecutive_success}")
    print(f"Results: {RESULT_FILE}")
    print(f"{'='*60}")

    return 0 if success_count >= 2 else 1


def _fail_entry(case_id: str, query: str, elapsed: float, error: str) -> dict:
    return {
        "case_id": case_id,
        "query": query,
        "run_status": error,
        "error": error,
        "elapsed_s": round(elapsed, 1),
        "scores": {},
        "overall": 0.0,
        "success": False,
    }


def _blind_review_single(query: str, report: str) -> dict:
    """Run a single-side blind review using the configured LLM."""
    from conflux.model_factory import create_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    model = create_chat_model("balanced")

    max_report_chars = 12000
    if len(report) > max_report_chars:
        report = report[:max_report_chars] + "\n\n[... report truncated ...]"

    prompt = BLIND_PROMPT_TEMPLATE.format(
        date=date.today().isoformat(),
        query=query,
        report=report,
    )

    try:
        response = model.invoke([
            SystemMessage(content=BLIND_SYSTEM),
            HumanMessage(content=prompt),
        ])
        text = str(response.content) if hasattr(response, "content") else str(response)
    except Exception as exc:
        return {
            "scores": {d: 1 for d in RUBRIC_DIMENSIONS},
            "overall": 1.0,
            "reason": f"LLM call failed: {exc}",
            "is_empty": True,
        }

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group())
            except json.JSONDecodeError:
                return _empty_review(text)
        else:
            return _empty_review(text)

    scores = payload.get("scores", {})
    overall = float(payload.get("overall", 0.0))
    if overall == 0.0 and scores:
        score_values = [float(v) for v in scores.values() if isinstance(v, (int, float))]
        overall = sum(score_values) / len(score_values) if score_values else 1.0

    validated_scores = {}
    for dim in RUBRIC_DIMENSIONS:
        val = scores.get(dim)
        validated_scores[dim] = max(1, min(5, int(val))) if isinstance(val, (int, float)) else 1

    return {
        "scores": validated_scores,
        "overall": round(overall, 1),
        "reason": str(payload.get("reason", ""))[:500],
        "is_empty": bool(payload.get("is_empty", False)),
    }


def _empty_review(raw_text: str) -> dict:
    return {
        "scores": {d: 1 for d in RUBRIC_DIMENSIONS},
        "overall": 1.0,
        "reason": f"JSON parse failed: {raw_text[:200]}",
        "is_empty": True,
    }


if __name__ == "__main__":
    raise SystemExit(main())
