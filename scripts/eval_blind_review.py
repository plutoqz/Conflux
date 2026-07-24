"""H2: Anonymous pairwise blind review — V2 vs P1.5 baseline.

Usage:
  python scripts/eval_blind_review.py \
    --cases evaluation/generalized_research_representative_set.json \
    --v2-dir reports/v2-h \
    --baseline-dir reports/workbench/query \
    --output reports/evaluation/blind_reviews.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from conflux.config import PROJECT_ROOT
from conflux.model_factory import create_chat_model

# ── Rubric dimensions (from research_evaluation.py) ──
RUBRIC_DIMENSIONS = (
    "factual_citation_match",
    "scope_and_coverage",
    "mechanism_rigor",
    "quantitative_and_implementation_detail",
    "comparative_synthesis",
    "decision_value",
)
PAIRWISE_DIMENSIONS = ("breadth", "depth", "evidence_correctness", "synthesis_insight")

BLIND_SYSTEM = (
    "你是一名独立科研评审人。你将看到同一个研究问题的两份匿名报告（A和B）。"
    "请忽略格式和排版，关注内容本身。"
    "即使两份报告都不完美，也要给出相对判断，不要全部打平分。"
    "只输出 JSON，不要加任何其他文字。"
)


def _load_v2_reports(v2_dir: Path) -> dict[str, str]:
    """Map case_id → latest V2 report markdown."""
    mapping: dict[str, str] = {}
    for summary_path in sorted(v2_dir.glob("*.summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        query = str(summary.get("query") or "").strip()
        report_path = summary.get("report_md_path")
        if not report_path or not query:
            continue
        report_file = Path(report_path)
        if not report_file.exists():
            continue
        mapping[query] = report_file.read_text(encoding="utf-8")
    return mapping


def _load_baseline_reports(baseline_dir: Path, case_queries: list[str]) -> dict[str, str]:
    """Map case query → P1.5 baseline report markdown (best effort)."""
    mapping: dict[str, str] = {}
    # Known run_ids from the snapshot
    known = {
        "GIS处理自动化研究目前有哪些瓶颈？": "245f93f1726c",
        "当前自主编码智能体进入生产软件工程的主要瓶颈是什么？": "5437e8ae556e",
        "当前主要司法辖区对基础模型透明度义务有哪些可核验差异？": "86b4415f70e1",
    }
    for query, run_id in known.items():
        draft = baseline_dir / f"{run_id}.draft.md"
        if draft.exists():
            mapping[query] = draft.read_text(encoding="utf-8")
        else:
            # Try glob for any file containing the run_id
            for candidate in baseline_dir.glob(f"*{run_id}*.md"):
                mapping[query] = candidate.read_text(encoding="utf-8")
                break
    return mapping


def _truncate(text: str, limit: int = 8000) -> str:
    """Truncate to first `limit` chars for model context."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n（报告过长，已截断）"


def _build_blind_prompt(
    query: str,
    report_a: str,
    report_b: str,
    a_is_v2: bool,
) -> str:
    dimension_descriptions = {
        "factual_citation_match": "事实与引用匹配度：声明是否有外部来源支撑，引用是否可追溯",
        "scope_and_coverage": "范围与覆盖面：是否涵盖问题的关键维度，有无重大遗漏",
        "mechanism_rigor": "机制分析严谨度：是否解释了形成机制/因果关系，而非仅罗列现象",
        "quantitative_and_implementation_detail": "定量与实现细节：是否包含数据、实例或实现层面信息",
        "comparative_synthesis": "比较综合能力：是否做了跨维度/跨来源的综合比较",
        "decision_value": "决策参考价值：对研究者/实践者是否有可行动的洞察",
    }
    pairwise_descriptions = {
        "breadth": "广度：哪份报告覆盖了更多关键维度",
        "depth": "深度：哪份报告对机制/原因的分析更深入",
        "evidence_correctness": "证据正确性：哪份报告的引用更可靠、更相关",
        "synthesis_insight": "综合洞察：哪份报告的跨节综合更有洞见",
    }

    dim_parts = []
    for dim in RUBRIC_DIMENSIONS:
        dim_parts.append(f"  - {dim}（{dimension_descriptions[dim]}）")
    pwd_parts = []
    for dim in PAIRWISE_DIMENSIONS:
        pwd_parts.append(f"  - {dim}（{pairwise_descriptions[dim]}）")

    prompt = f"""请对以下两份匿名研究报告进行评审。

研究问题：{query}

--- 报告 A ---
{_truncate(report_a)}

--- 报告 B ---
{_truncate(report_b)}

## 评审要求

### 1. 维度评分（每份报告独立评分，1-5 分，允许 0.5 精度）
{"".join(dim_parts)}

### 2. 成对比较（A vs B）
对于每个维度，用 -2 到 +2 表示偏好（负值偏好 A，正值偏好 B，0 表示无差异）：
{"".join(pwd_parts)}

### 3. 综合判断
- 用 1 句话说明哪份报告整体更好
- 指出 A 的主要优势（1 条）
- 指出 B 的主要优势（1 条）

返回 JSON：
{{
  "scores_A": {{"factual_citation_match": 3.5, "scope_and_coverage": 3.0, ...}},
  "scores_B": {{"factual_citation_match": 2.5, ...}},
  "pairwise": {{
    "breadth": -1,
    "depth": 0,
    "evidence_correctness": -2,
    "synthesis_insight": 1
  }},
  "overall_winner": "A" 或 "B" 或 "tie",
  "advantage_A": "一句话",
  "advantage_B": "一句话"
}}"""
    return prompt


def _parse_blind_response(raw: str) -> dict[str, Any] | None:
    """Extract JSON from model response."""
    raw = str(raw or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def run_blind_review(
    cases_path: Path,
    v2_dir: Path,
    baseline_dir: Path,
    output_path: Path,
) -> int:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    v2_map = _load_v2_reports(v2_dir)
    bl_map = _load_baseline_reports(baseline_dir, [c["query"] for c in cases])

    # Find overlapping cases (have both V2 and baseline)
    overlapping = []
    for case in cases:
        q = case["query"]
        if q in v2_map and q in bl_map:
            overlapping.append((case, v2_map[q], bl_map[q]))

    if not overlapping:
        print("No overlapping cases found between V2 and baseline")
        return 1

    print(f"Running blind review on {len(overlapping)} cases...")
    model = create_chat_model(
        "reasoning",
        max_tokens=4096,
    )

    results: list[dict[str, Any]] = []
    for case, v2_text, bl_text in overlapping:
        # Randomize order
        a_is_v2 = random.choice([True, False])
        if a_is_v2:
            report_a, report_b = v2_text, bl_text
        else:
            report_a, report_b = bl_text, v2_text

        prompt = _build_blind_prompt(case["query"], report_a, report_b, a_is_v2)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = model.invoke([
                SystemMessage(content=BLIND_SYSTEM),
                HumanMessage(content=prompt),
            ])
            content = str(response.content) if hasattr(response, "content") else str(response)
        except Exception as exc:
            print(f"  FAIL {case['id']}: {exc}")
            continue

        parsed = _parse_blind_response(content)
        if not parsed:
            print(f"  PARSE FAIL {case['id']}: {content[:200]}")
            continue

        # Un-shuffle scores
        if a_is_v2:
            scores_v2 = parsed.get("scores_A", {})
            scores_p15 = parsed.get("scores_B", {})
            pairwise = {
                k: -v if isinstance(v, (int, float)) else v
                for k, v in parsed.get("pairwise", {}).items()
            }
        else:
            scores_v2 = parsed.get("scores_B", {})
            scores_p15 = parsed.get("scores_A", {})
            pairwise = parsed.get("pairwise", {})

        result = {
            "case_id": case["id"],
            "query": case["query"],
            "scores": scores_v2,
            "p1_comparison": pairwise,
            "p1_scores": scores_p15,
            "overall_winner": parsed.get("overall_winner", "tie"),
            "v2_advantage": parsed.get(
                ("advantage_A" if a_is_v2 else "advantage_B") or "",
            ),
            "p15_advantage": parsed.get(
                ("advantage_B" if a_is_v2 else "advantage_A") or "",
            ),
        }
        results.append(result)
        print(f"  OK {case['id']}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {len(results)} blind reviews → {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="H2 blind review: V2 vs P1.5")
    parser.add_argument(
        "--cases",
        default=str(PROJECT_ROOT / "evaluation" / "generalized_research_representative_set.json"),
    )
    parser.add_argument("--v2-dir", default=str(PROJECT_ROOT / "reports" / "v2-h"))
    parser.add_argument("--baseline-dir", default=str(PROJECT_ROOT / "reports" / "workbench" / "query"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "evaluation" / "blind_reviews.json"))
    args = parser.parse_args(argv)
    return run_blind_review(
        Path(args.cases),
        Path(args.v2_dir),
        Path(args.baseline_dir),
        Path(args.output),
    )


if __name__ == "__main__":
    raise SystemExit(main())
