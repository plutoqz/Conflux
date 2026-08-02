"""P2 Paper Radar 真实 API 冒烟评测（Phase P2 联调）。

真实调用 arxiv / Semantic Scholar 检索 + LLM 深度分析（balanced 档），
输出 LLM 遥测（token / 时耗 / 降级次数）、检索统计与建议样例，
用于验证 LLM 深度分析在真实模型上的质量与成本。

用法:
    python scripts/eval_paper_radar.py \
        --profile profiles/example_gis_agent.yaml \
        --limit 3 \
        [--with-pdf]          # 默认跳过 PDF 下载（arxiv 网络不稳时）
        [--out-dir reports/eval/paper_radar]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description="P2 Paper Radar real-API smoke eval")
    parser.add_argument("--profile", default="profiles/example_gis_agent.yaml")
    parser.add_argument("--limit", type=int, default=3, help="deep_read_limit override (LLM calls)")
    parser.add_argument("--with-pdf", action="store_true", help="Allow PDF downloads (default: skip)")
    parser.add_argument("--out-dir", default="reports/eval/paper_radar")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.workbench", override=False)

    from conflux.core.p2_contracts import ProjectResearchConfig
    from conflux.model_factory import create_chat_model
    from conflux.paper_radar.radar import run_paper_radar
    from conflux.project_registry.models import ProjectDefinition
    from conflux.research_profile import load_profile

    profile = load_profile(args.profile, validate=False)
    cfg = ProjectResearchConfig(profile=args.profile)

    proj = ProjectDefinition(id="radar-smoke", name="Radar Smoke", path=str(ROOT))
    proj.plan.overall_goal = "验证知识图谱增强 GIS Agent 工作流的有效性与可复现性"
    proj.research = {
        "profile": args.profile,
        "sources": ["arxiv"],
        "max_candidates": 30,
        "deep_read_limit": args.limit,
    }

    # 默认跳过 PDF 下载：arxiv 网络不稳时 LLM 分析退回摘要模式。
    if not args.with_pdf:
        import conflux.paper_radar.deep_analyzer as da

        da._download_pdf = lambda *a, **k: None
        print("[info] PDF 下载已跳过（--with-pdf 可开启）；LLM 使用摘要 + 全文节选（如有）")

    model = create_chat_model("balanced")
    print(f"[info] LLM 模型: balanced")
    print(f"[info] deep_read_limit: {args.limit} | sources: arxiv")

    started = time.time()
    result = run_paper_radar(
        proj,
        profile,
        out_dir=str(ROOT / args.out_dir / "run"),
        llm_review=True,
        review_model=model,
    )
    total_elapsed = time.time() - started

    stats = result.stats
    print("\n" + "=" * 60)
    print("P2 Paper Radar 真实 API 冒烟结果")
    print("=" * 60)
    print(f"总耗时: {stats.elapsed_seconds:.1f}s（含检索） | 脚本总耗时: {total_elapsed:.1f}s")
    print(f"候选论文: {stats.total_candidates} | 去重后: {stats.after_dedup} | 过滤后: {stats.after_negative_filter}")
    print(f"失败来源: {stats.failed_sources or '无'}")
    print(f"查询数: {stats.query_count} | Intent 数: {stats.intent_count}")
    print(f"Deep read: {stats.deep_read} 篇 | 建议数: {stats.suggestions_proposed}")
    print("\n-- LLM 遥测 --")
    print(f"LLM 调用次数: {stats.llm_calls}")
    print(f"LLM 总 token: {stats.llm_total_tokens}")
    print(f"LLM 总耗时: {stats.llm_elapsed_ms}ms")
    print(f"LLM 降级次数: {stats.llm_fallback_count}")
    if stats.llm_calls:
        print(f"平均每次调用: {stats.llm_total_tokens / stats.llm_calls:.0f} tokens, "
              f"{stats.llm_elapsed_ms / stats.llm_calls:.0f}ms")

    print("\n-- 建议样例（前 3 条）--")
    for suggestion in result.suggestions[:3]:
        print(f"- [{suggestion.type.value}] {suggestion.summary[:80]}")
        print(f"  conf={suggestion.confidence:.2f} refs={suggestion.evidence_refs[:2]}")

    # 输出 JSON 报告
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "profile": args.profile,
        "deep_read_limit": args.limit,
        "with_pdf": args.with_pdf,
        "stats": stats.model_dump(mode="json"),
        "suggestions": [s.model_dump(mode="json") for s in result.suggestions],
        "queries": [q.model_dump(mode="json") for q in result.queries],
    }
    json_path = out_dir / "paper_radar_smoke.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON 报告: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
