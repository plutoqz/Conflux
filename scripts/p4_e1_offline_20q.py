"""P4.4 E1 离线评测 — 20 问函数级命中率 + 引用可回溯性（E1.1/E1.2 验收）。

对自身仓库（Conflux src）建 AST 代码索引，然后跑 20 个构造问题：
- 每个问题的 answer 必须命中（gold 符号存在于 hits 或调用链中）且
  引用 100% 为 ``code:{path}#L{行号}``。

Usage:
    python scripts/p4_e1_offline_eval.py [--out reports/evaluation/p4]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.code_qa import index_project_code, answer_code_question  # noqa: E402


# (问题, 期望符号 gzip) —— 20 问覆盖：函数、类方法、调用链、失败回退等。
_GOLD_QUESTIONS: list[tuple[str, str]] = [
    ("创建向量存储的函数叫什么", "create_vector_store"),
    ("如何把一个论文收件箱提升为知识文档", "promote_inbox"),
    ("计算 RAG 覆盖度（indexed/stale/missing）的入口", "compute_coverage"),
    ("把已确认项目文档索引进知识库的函数", "index_project_documents"),
    ("运行实验测试命令并采集结果的函数", "inspect_tests"),
    ("确认周期审计摘要并把当前修订成为新基线的", "confirm_cycle_summary"),
    ("构建周期审计草稿比较器的函数", "build_cycle_audit"),
    ("登记用户记忆的超类方法 add 在哪个仓库类", "UserMemoryRepository"),
    ("把记忆条目组装成注入前缀的函数", "build_memory_banner"),
    ("运行评审团并行调用的入口", "run_panel"),
    ("解析项目文档分类规则在哪里", "classify"),
    ("论文收件处理的去重函数", "dedup"),
    ("从 PDF 提取文本的函数", "extract_pdf_text"),
    ("计算生成 token 计数的", "_count_tokens"),
    ("把事件写入本地 event store 的方法", "append"),
    ("推导分支关联工作项的确定性逻辑", "persist_links"),
    ("构建周期审计 Markdown 导出的", "build_cycle_markdown"),
    ("扫描研发项目结果文件并把结果注册成实验的", "auto_scan_result_files"),
    ("把导师周报导出为 Markdown 的函数", "export_mentor_report_markdown"),
    ("证据链里写入最终状态的便捷入口", "persist_final_state"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p4"))
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from conflux.project_registry import ProjectDefinition

    project = ProjectDefinition(id="conflux-self", name="Conflux", path=str(PROJECT_ROOT))
    started = time.perf_counter()
    index_result = index_project_code(None, project, root_dir=str(PROJECT_ROOT / "src"))
    if not index_result.get("ok"):
        print(f"[e1] 索引失败：{index_result.get('error')}")
        return 1
    print(f"[e1] 索引：{index_result.get('symbols')} 个代码块（{index_result.get('files')} 文件）")

    hits = traceable = 0
    rows: list[dict] = []
    for question, gold in _GOLD_QUESTIONS:
        result = answer_code_question(question, project_id="conflux-self", top_k=5)
        refs = result.get("refs") or []
        # 命中：gold 作为符号名子串出现（如 append ⊂ EventStore.append 即为命中），
        # 或在路径/调用链中出现。
        hit_names = {h.get("symbol", "").rsplit("#", 1)[-1] for h in result.get("hits", [])}
        path_names = {f"{h.get('path', '')}#{h.get('symbol', '').rsplit('#', 1)[-1]}" for h in result.get("hits", [])}
        chain_names = {e.get("qname", "") for e in result.get("call_chain", [])}
        ok = any(gold == name or gold in name for name in hit_names)
        ok = ok or any(gold in name for name in chain_names)
        ok = ok or any(gold in ref for ref in refs)
        if ok:
            hits += 1
        traceable_ok = bool(refs) and all(r.startswith("code:") and "#L" in r for r in refs)
        if traceable_ok:
            traceable += 1
        rows.append({
            "question": question,
            "gold": gold,
            "ok": ok,
            "traceable": traceable_ok,
            "hits": result.get("hits", [])[:3],
            "refs": refs,
        })

    hit_rate = hits / len(_GOLD_QUESTIONS)
    traceable_rate = traceable / len(_GOLD_QUESTIONS)
    payload = {
        "ok": hit_rate >= 0.6 and traceable_rate == 1.0,
        "evaluation": "p4/e1_offline_20q",
        "questions": len(_GOLD_QUESTIONS),
        "hit_rate": hit_rate,
        "traceable_rate": traceable_rate,
        "rows": rows,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    report = out_dir / "p4_e1_offline_20q.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[e1] 命中率 {hit_rate:.2%}；可回溯率 {traceable_rate:.2%}；报告 {report}")
    return 0 if hit_rate >= 0.6 and traceable_rate == 1.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())