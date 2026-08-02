"""生成 R2 Web 搜索质量人工标注清单。

对 data/web_eval_queries.yaml 中每条查询运行一次 web 搜索，
把每条 [Fetched N] 结果的标题/URL/相关性提取为标注表格，
供人工按 1-3 分评定相关性（1=不相关, 2=部分相关, 3=高度相关）。

用法:
    python scripts/gen_web_annotations.py
    输出: reports/eval/web/web_search_annotations.md
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FETCHED_RE = re.compile(
    r"^\[Fetched (\d+)\] \[Web:([^\]]*)\] relevance=([\d.]+) kind=(\S+) (.+)$"
)


def extract_results(raw: str) -> list[dict]:
    results = []
    for line in raw.split("\n"):
        m = FETCHED_RE.match(line.strip())
        if m:
            results.append({
                "index": int(m.group(1)),
                "url": m.group(2),
                "relevance": float(m.group(3)),
                "kind": m.group(4),
                "title": m.group(5).strip(),
            })
    return results


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.workbench", override=False)

    from conflux.config import load as load_config
    from conflux.research_modes import resolve_research_profile
    from conflux.tools.web import create_web_tool

    load_config()
    profile = resolve_research_profile("standard")
    tool = create_web_tool(profile)

    queries = yaml.safe_load((ROOT / "data/web_eval_queries.yaml").read_text(encoding="utf-8"))

    out_lines = [
        "# R2 Web Search Quality — 人工标注清单",
        "",
        "> 生成时间：实时运行  |  深度：standard  |  来源：`scripts/gen_web_annotations.py`",
        "",
        "## 标注说明",
        "",
        "对每条查询的检索结果整体评定 **结果相关性（1-3 分）**：",
        "",
        "- **3 分**：结果直接命中查询意图，能支撑回答（标题/正文与主题强相关，时效合理）。",
        "- **2 分**：结果部分相关，只有一部分内容能支撑回答，或主题沾边但不够直接。",
        "- **1 分**：结果与查询无关，或几乎无法支撑回答（含失败/空结果）。",
        "",
        "在下方表格 `评分` 列填入 1/2/3，`备注` 列可写简要理由（可选）。",
        "",
        "| ID | 查询 | 检索结果 | 评分 | 备注 |",
        "|---|---|---|---|---|",
    ]

    for item in queries:
        qid = item["id"]
        query = item["query"]
        print(f"  [{qid}] {query[:50]} ... ", flush=True)
        raw = tool.invoke({"query": query})
        results = extract_results(str(raw))
        if not results:
            out_lines.append(f"| {qid} | {query} | _无结果_ | | |")
            print("  no results")
            continue
        cell_lines = []
        for r in results:
            title = r["title"][:70]
            cell_lines.append(
                f"{r['index']}. [{title}]({r['url']}) <br>relevance={r['relevance']:.2f}, kind={r['kind']}"
            )
        cell = "<br>".join(cell_lines)
        out_lines.append(f"| {qid} | {query} | {cell} | | |")
        print(f"  {len(results)} results")

    out_path = ROOT / "reports" / "eval" / "web" / "web_search_annotations.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"\n标注清单: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
