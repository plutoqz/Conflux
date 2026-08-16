"""P4.5 E2 文献笔记与写作闭环测试（对照 E2.1–E2.3 验收表）。

覆盖：E2.1 结构化笔记（字段模板/幂等/状态）、E2.2 一致性审计
（有支撑/无支撑判定 + uncertain 标记）、E2.3 related work 引用
100% 可回溯（validate_related_work_citations）、BibTeX 确定性导出、
链接层 note:{id} evidence refs 接物化。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import conflux.paper_notes as notes_mod  # noqa: E402
from conflux.paper_notes import (  # noqa: E402
    NOTE_STATUSES,
    NoteCapacityError,
    PaperNoteRepository,
    audit_note_consistency,
    generate_related_work,
    note_evidence_links,
    note_id_from,
    paper_to_bibtex,
    validate_related_work_citations,
)


class _DB:
    """内存 SQLite，schema 走 0010 migration 语句。"""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        for statement in notes_mod.PAPER_NOTES_STATEMENTS:
            self.connection.execute(statement)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


@pytest.fixture()
def repo():
    db = _DB()
    yield PaperNoteRepository(db)
    db.close()


# ============================================================
# E2.1 结构化笔记
# ============================================================

class TestNotes:
    def test_add_round_trip(self, repo):
        entry = repo.add(
            paper_key="arxiv:2606.08661",
            title="Retrieval-Augmented Generation for Knowledge-Intensive Tasks",
            note_text="这篇综述梳理了 RAG 在知识密集型任务的架构演进。",
            fields={
                "目标": "梳理 RAG 的三个消融组件",
                "方法": "检索器 + 生成器联合训练",
                "结论": "RAG 优于非增强基线",
                "局限": "合成设置",
                "与我的项目关系": "可复用于检索链路",
            },
            source_refs=[{"page": "1", "segment": "引言"}],
        )
        assert entry["note_id"].startswith("note-")
        assert entry["paper_key"] == "arxiv:2606.08661"
        assert entry["fields"]["目标"] == "梳理 RAG 的三个消融组件"
        assert entry["status"] == "active"

    def test_add_idempotent_by_title(self, repo):
        first = repo.add(paper_key="p1", title="相同标题", note_text="a")
        second = repo.add(paper_key="p1", title="相同标题", note_text="a")
        assert first["note_id"] == second["note_id"]
        assert repo.count("p1") == 1

    def test_validation_status(self, repo):
        with pytest.raises(ValueError):
            repo.add(paper_key="p1", title="x", note_text="t", status="bad")

    def test_update_and_mark_uncertain(self, repo):
        entry = repo.add(paper_key="p1", title="t", note_text="x")
        updated = repo.mark_uncertain("p1", entry["note_id"])
        assert updated["status"] == "uncertain"

    def test_capacity_limit(self, repo):
        # 上限 2000 太高没法全填；用 monkeypatch 检查上限抛错路径
        notes_mod.NOTES_CAPACITY = 1
        repo.add(paper_key="p1", title="a", note_text="x")
        with pytest.raises(NoteCapacityError):
            repo.add(paper_key="p1", title="b", note_text="y")
        notes_mod.NOTES_CAPACITY = 2000

    def test_note_id_deterministic(self):
        assert note_id_from("pk", "title") == note_id_from("pk", "title")
        assert note_id_from("pk", "title") != note_id_from("pk", "other")


# ============================================================
# E2.2 一致性审计
# ============================================================

class TestConsistency:
    _SOURCE = (
        "We introduce a retrieval-augmented generation (RAG) framework that "
        "combines a dense retriever with a sequence-to-sequence generator. "
        "Experiments show the retriever substantially improves answer "
        "accuracy on knowledge-intensive tasks, while the generator alone "
        "underperforms on out-of-domain queries. Limitations include "
        "synthetic evaluation settings and fixed corpora."
    )

    def test_original_backed_fields_supported(self):
        note = {
            "fields": {
                "目标": "combines dense retriever with seq2seq generator",
                "方法": "dense retriever generator",
                "结论": "retriever improves accuracy",
                "局限": "synthetic evaluation",
                "与我的项目关系": "retrieverarchitecture",
            }
        }
        result = audit_note_consistency(note, self._SOURCE)
        assert result["ok"] is True
        assert result["unsupported_ratio"] == 0.0

    def test_fabricated_field_flagged(self):
        note = {
            "fields": {
                "目标": "研究量子纠错在容错计算中的应用与拓扑保护",
                "方法": "基于表面码和魔法的分布式量子网络",
                "结论": "retriever improves accuracy",
            }
        }
        # 目标/方法均为无原文支撑的编造（≥50% 无支撑 → 整体拒绝）。
        result = audit_note_consistency(note, self._SOURCE)
        assert result["ok"] is False
        assert any(item["field"] == "目标" for item in result["issues"])
        assert result["unsupported_ratio"] >= 0.5

    def test_empty_note_passes(self):
        result = audit_note_consistency({"fields": {}}, self._SOURCE)
        assert result["ok"] is True
        assert result["checked"] == 0


# ============================================================
# E2.3 related work 引用可回溯
# ============================================================

class TestRelatedWork:
    def _notes(self):
        return [
            {
                "note_id": "note-abc",
                "title": "RAG Survey",
                "fields": {"目标": "survey", "结论": "rag works"},
                "source_refs": [{"page": "1"}],
            },
            {
                "note_id": "note-def",
                "title": "Dense Retrieval",
                "fields": {"目标": "dense retriever"},
                "source_refs": [{"page": "3"}],
            },
        ]

    def test_valid_citations_pass(self):
        notes = self._notes()
        text = "综述 [note:note-abc] 与稠密检索 [note:note-def] 显示高效。"
        assert validate_related_work_citations(text, notes) == []

    def test_fabricated_citation_flagged(self):
        notes = self._notes()
        text = "相关工作 [note:note-abc] 和 [note:note-zzz] 显示差异。"
        problems = validate_related_work_citations(text, notes)
        assert problems == ["note-zzz"]

    def test_deterministic_related_uses_note_ids(self):
        notes = self._notes()
        text, problems = notes_mod.generate_related_work(notes)
        assert problems == []
        assert "[note:note-abc]" in text or "note-abc" in text

    def test_fake_llm_output_rejected(self):
        notes = self._notes()

        class _Fake:
            def invoke(self, messages):
                return type("R", (), {"content": "相关工作 [note:note-zzz] 重要。"})()

        _, problems = notes_mod.generate_related_work(notes, llm=_Fake())
        assert "note-zzz" in problems


# ============================================================
# 链接引用 + BibTeX
# ============================================================

class TestLinksAndBibTeX:
    def test_note_evidence_links_format(self):
        notes = [{"paper_key": "p1", "note_id": "note-x"}, {"paper_key": "p2", "note_id": "note-y"}]
        assert note_evidence_links(notes) == ["note:note-x", "note:note-y"]

    def test_bibtex_deterministic(self):
        paper = {
            "metadata": {
                "title": "RetrievalAugmented Generation for Knowledge-Intensive NLP",
                "authors": ["Lewis, Patrick", "Perez, Ethan"],
                "year": "2020",
                "venue": "NeurIPS",
                "doi": "10.5555/3495724.3495731",
            }
        }
        bib = paper_to_bibtex(paper)
        assert bib.startswith("@article{")
        assert "Lewis, Patrick and Perez, Ethan" in bib
        assert "year = {2020}" in bib
        assert "doi" in bib

    def test_bibtex_minimal(self):
        bib = paper_to_bibtex({"metadata": {"title": "A Paper"}})
        assert bib.startswith("@article{apaper")
        assert "title = {A Paper}" in bib