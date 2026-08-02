"""R2 Web 搜索质量评测 — 合并人工标注并生成总结报告。

读取 web_search_annotations.md 中的人工评分（1-3），
合并到 web_search_eval.json 并输出 R2_summary.md。

用法:
    python scripts/finalize_r2.py
    输出: reports/eval/web/R2_summary.md（更新 web_search_eval.json 写入评分）
"""

from __future__ import annotations

import io
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EVAL_JSON = ROOT / "reports/eval/web/web_search_eval.json"
ANNOTATIONS = ROOT / "reports/eval/web/web_search_annotations.md"
OUT_MD = ROOT / "reports/eval/web/R2_summary.md"


def parse_scores(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    rows = re.findall(r"^\| (web_\d+) \| .*? \| (\d) \|", text, re.M)
    return {qid: int(score) for qid, score in rows}


def main() -> int:
    payload = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    scores = parse_scores(ANNOTATIONS)

    by_id = {str(r["id"]): r for r in payload["results"]}
    missing = [qid for qid in by_id if qid not in scores]
    if missing:
        print(f"[WARN] 未标注: {missing}")

    distribution = {"3": [], "2": [], "1": []}
    for r in payload["results"]:
        qid = str(r["id"])
        r["manual_score"] = scores.get(qid)
        bucket = distribution.get(str(scores.get(qid)))
        if bucket is not None:
            bucket.append(qid)
    # 持久化评分到 eval JSON
    EVAL_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(scores.values())
    n = len(scores)
    mean = total / max(1, n)
    agg = payload["aggregate"]

    lines = [
        "# R2 Web Search Quality — 评测总结",
        "",
        "> 生成日期：2026-08-02  |  深度：standard  |  模型："
        f"{payload.get('model_trace', {}).get('roles', {}).get('reranker', {}).get('model', 'N/A')}",
        "> 数据：18 题时效敏感查询（`data/web_eval_queries.yaml`），DuckDuckGo 为主 provider。",
        "",
        "## 1. 结论",
        "",
        f"**人工标注均分 2.06 / 3**：7 题直接命中（38.9%）、5 题部分相关（27.8%）、6 题不相关（33.3%）。",
        "检索管道本身稳定（fetch 成功率 100%、18/18 有返回），但**结果相关性是主要短板**：",
        "具体产品/法规类查询容易偏移到学术论文或全球通用报告，中国政策类查询缺少本地来源覆盖。",
        "",
        "## 2. 自动指标 vs 人工标注",
        "",
        "| 指标 | 自动 | 人工 | 说明 |",
        "|---|---|---|---|",
        f"| 命中率 | {agg['hit_rate']:.0%}（18/18） | — | 有返回 ≠ 有相关结果 |",
        f"| 均分 | — | **{mean:.2f} / 3** | 相关性主指标 |",
        f"| 平均结果数 | {agg['mean_result_count']:.1f} 条 | 5 题仅 1-2 条 | 平均数掩盖长尾不足 |",
        f"| Fetch 成功率 | {agg['mean_fetch_success_rate']:.0%} | — | 与相关性无关 |",
        f"| 平均耗时 | {agg['mean_elapsed_seconds']:.0f}s/题 | — | 可接受 |",
        "",
        "## 3. 分数分布",
        "",
        "| 分数 | 题数 | 占比 | 查询 ID |",
        "|---|---|---|---|",
        f"| 3（直接相关） | {len(distribution['3'])} | {len(distribution['3'])/n:.0%} | {', '.join(distribution['3'])} |",
        f"| 2（部分相关） | {len(distribution['2'])} | {len(distribution['2'])/n:.0%} | {', '.join(distribution['2'])} |",
        f"| 1（不相关） | {len(distribution['1'])} | {len(distribution['1'])/n:.0%} | {', '.join(distribution['1'])} |",
        "",
        "## 4. 失败模式",
        "",
        "| 模式 | 涉及查询 | 根因 |",
        "|---|---|---|",
        "| 产品/法规查询偏移到学术论文 | web_001, web_002, web_005 | DuckDuckGo 对\"产品名+年份\"返回 arxiv 论文而非官方公告/新闻 |",
        "| 国家政策查询偏移到全球报告 | web_006, web_014 | 特定国家监管查询被泛化为全球性 AI 报告 |",
        "| 对比研究查询偏移到单方改进 | web_018 | 返回 RAG 单方论文，缺长上下文对比视角 |",
        "| 结果数量不足 | web_005, web_010, web_012 | 仅 1-2 条，需多 provider 合并或提高 max_results |",
        "| 时效滞后 | web_008 | 命中 2023 旧闻，排序缺时效权重 |",
        "| 来源权威性不足 | web_007, web_010 | 日文博客/小型统计站，缺官方来源优先 |",
        "",
        "## 5. 改进建议（按优先级）",
        "",
        "1. **查询改写强化**：对法规/产品类查询强制追加 `site:` 官方域或新闻源（如 `site:ec.europa.eu`、`site:anthropic.com`）。",
        "2. **多 provider 融合**：当前 18/18 来自 DuckDuckGo，SerpAPI/Google 覆盖不足；启用 fallback 合并去重可补结果数量与中文本地来源。",
        "3. **时效排序权重**：`_temporal_relevance` 已存在，可对含年份查询提升新鲜度占比（当前 0.20 权重偏低）。",
        "4. **领域权威过滤**：对技术/政策查询提高 `.gov`/官方域分数，过滤低质内容站。",
        "",
        "## 6. 明细",
        "",
        "| ID | 查询 | 结果数 | 自动 relevance | 人工分 |",
        "|---|---|---:|---:|---:|",
    ]
    for r in payload["results"]:
        qid = str(r["id"])
        rels = r.get("result_count", 0)
        lines.append(
            f"| {qid} | {r['query'][:48]} | {rels} | — | {scores.get(qid, '?')} |"
        )
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"R2 总结: {OUT_MD}")
    print(f"均分: {mean:.2f} | 3分×{len(distribution['3'])} 2分×{len(distribution['2'])} 1分×{len(distribution['1'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
