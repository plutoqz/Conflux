"""P4.5 E2 closure runner — literature notes + writing loop（E2.1–E2.3 闭环）。

对真实 SQLite runtime DB 驱动 E2 验收链：
    登记结构化笔记（字段模板） → 一致性审计（unsupported 比例）
    → BibTeX 导出 → related work 草稿引用校验（100% 可回溯）。

每步 failure 记录到 report；最后写 JSON 到 reports/evaluation/p4/。

用法：
    python scripts/p4_e2_closure.py [--out reports/evaluation/p4]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.adapters.sqlite_store import SQLiteDatabase  # noqa: E402
from conflux.core.runtime_home import database_path  # noqa: E402
from conflux.paper_notes import (  # noqa: E402
    PaperNoteRepository,
    audit_note_consistency,
    generate_related_work,
    note_evidence_links,
    paper_to_bibtex,
    validate_related_work_citations,
)

_SOURCE = (
    "We propose a retrieval-augmented generation (RAG) framework that "
    "combines a dense retriever with a sequence-to-sequence generator. "
    "Our experiments on knowledge-intensive tasks show the retriever "
    "substantially improves answer accuracy and reduces hallucination, "
    "while the generator alone underperforms on out-of-domain queries. "
    "We evaluate on Natural Questions and MS MARCO. Limitations include "
    "synthetic settings and fixed corpora."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "evaluation" / "p4"))
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    repo = PaperNoteRepository(db)

    steps: list[dict[str, Any]] = []
    failures: list[str] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        steps.append({"name": name, "ok": ok, "detail": detail, "at": time.time()})
        print(f"[e2] {'PASS' if ok else 'FAIL'} {name} {detail}")
        if not ok:
            failures.append(f"{name}: {detail}")

    try:
        # E2.1: 结构化笔记（字段模板 + 原文引用区间）
        stamp = int(time.time()) % 100000
        paper_key = f"closure:{stamp}"
        note = repo.add(
            paper_key=paper_key,
            title="Retrieval-Augmented Generation for Knowledge-Intensive NLP",
            note_text="RAG 把检索器与生成器联合，显著提升知识密集问答。",
            fields={
                "目标": "combines dense retriever with seq2seq generator",
                "方法": "dense retriever generator 25 tasks",
                "结论": "retriever improves answer accuracy hallucination",
                "局限": "synthetic settings fixed corpora",
                "与我的项目关系": "retriever architecture",
            },
            source_refs=[{"page": "1", "segment": "abstract"},
                         {"page": "2", "segment": "method"}],
        )
        record("E2.1 结构化笔记登记", note["note_id"].startswith("note-"),
               f"id={note['note_id']}")
        assert note["fields"]["目标"] == "combines dense retriever with seq2seq generator"

        # E2.2: 一致性审计（字段有原文支撑）
        audit = audit_note_consistency(note, _SOURCE)
        record("E2.2 一致性审计有支撑", audit["ok"] is True,
               f"unsupported_ratio={audit['unsupported_ratio']}")
        # 编造断言应被审计拒绝
        forged = dict(note)
        forged["fields"] = {
            "目标": "量子纠错在容错计算中的拓扑保护方案",
            "方法": "表面码与魔术态的分布式网络",
            "结论": "retriever improves answer accuracy",
        }
        forged_audit = audit_note_consistency(forged, _SOURCE)
        record("E2.2 编造断言被拒绝", forged_audit["ok"] is False,
               f"unsupported_ratio={forged_audit['unsupported_ratio']}")

        # E2.1: BibTeX 确定性导出
        bib = paper_to_bibtex(
            {"metadata": {
                "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP",
                "authors": ["Lewis, Patrick", "Perez, Ethan"],
                "year": "2020",
                "venue": "NeurIPS",
            }}
        )
        record("E2.1 BibTeX 确定性导出", bib.startswith("@article{") and "2020" in bib)
        assert "Lewis, Patrick and Perez, Ethan" in bib

        # E2.3: related work 引用 100% 可回溯（确定性 + 校验）
        rw_notes = [
            note,
            {
                "note_id": "note-second",
                "title": "Dense Passage Retrieval",
                "fields": {"目标": "dense retriever"},
                "source_refs": [{"page": "1"}],
            },
        ]
        draft, problems = generate_related_work(rw_notes)
        record("E2.3 related work 可回溯", problems == [],
               f"problems={problems} refs_ok={validate_related_work_citations(draft, rw_notes) == []}")
        assert f"{note['note_id']}" in draft

        # 链接层 note:{id} evidence refs
        links = note_evidence_links([note, {"paper_key": "x", "note_id": "note-y"}])
        record("E2 链接 note:{id} refs", links == [f"note:{note['note_id']}", "note:note-y"],
               f"links={links}")

        # 全量读取回归
        all_notes = repo.list()
        record("E2 笔记列表读取", any(n["note_id"] == note["note_id"] for n in all_notes),
               f"total={len(all_notes)}")

        # 清理：删除测试笔记（保持库干净）
        db.connection.execute(
            "DELETE FROM paper_notes WHERE paper_key = ?", (paper_key,)
        )
        db.connection.commit()

    finally:
        db.close()

    payload = {
        "ok": not failures,
        "evaluation": "p4/e2_closure",
        "steps": steps,
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    report = out_dir / f"p4_e2_closure_{time.strftime('%Y%m%d')}.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[e2] 闭环报告：{report}")
    return 0 if not failures else 2


def text(value: str) -> None:
    """仅为保证 value 无语法错误被引用。"""
    if not isinstance(value, str):
        raise TypeError("expected str")


if __name__ == "__main__":
    raise SystemExit(main())