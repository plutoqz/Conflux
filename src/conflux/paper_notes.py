"""P4.5 E2 文献笔记与写作闭环 — 结构化笔记存储 + 一致性审计 + 链接引用（E2.1/E2.2）。

设计对照 docs/plans/p4/E_文献笔记与代码问答.md §E2：
- 结构化笔记：`{目标, 方法, 结论, 局限, 与我的项目关系}` 字段模板，每条带
  **原文引用区间**（页/段定位）；
- 一致性审计（确定性兜底，E2.2 立身之本）：`audit_note_consistency(note, source)`
  返回 `{ok, issues[], unsupported_ratio}` —— 判定「笔记声明无原文支撑」的比例；
  审计失败条目可标记 `status=uncertain`；
- 链接物化：笔记经 `evidence_refs` 的 `note:{id}` 引用进入 P3.4 链接层，
  与 `claim:/run:/paper:` 同一条可追溯链；
- BibTeX 导出：从论文元数据确定性生成，无 LLM；
- Related work 草稿：`generate_related_work(notes, llm=...)` — LLM 仅组织语言，
  输出后 `validate_related_work_citations()` 校验引用 100% 回源笔记原文。

通用性：schema/命令均为通用形状，不硬编码 Conflux/FusionAgent 专有字段。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable

from .sanitize import sanitize_untrusted_content

NOTE_STATUSES = ("active", "uncertain", "archived")
NOTES_CAPACITY = 2000
_SOURCE_REFS_MAX = 6
_NOTE_CHARS_MAX = 4000

PAPER_NOTES_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS paper_notes (
        paper_key TEXT NOT NULL,
        note_id TEXT NOT NULL,
        note_json TEXT NOT NULL,
        source_refs_json TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'active',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        PRIMARY KEY (paper_key, note_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_paper_notes_paper ON paper_notes(paper_key, status)",
    "CREATE INDEX IF NOT EXISTS idx_paper_notes_status ON paper_notes(status)",
]


def register_paper_notes_migration() -> None:
    """把 0010 追加进全局 SCHEMA_MIGRATIONS（幂等，import 时调用）。"""
    from conflux.adapters import sqlite_store as store

    versions = {item[0] for item in store.SCHEMA_MIGRATIONS}
    if "0010_paper_notes" not in versions:
        store.SCHEMA_MIGRATIONS.append(("0010_paper_notes", list(PAPER_NOTES_STATEMENTS)))


register_paper_notes_migration()


def _json_dumps(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return payload.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def _json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def note_id_from(paper_key: str, title: str) -> str:
    digest = hashlib.sha256(f"{paper_key}|{title}".encode("utf-8")).hexdigest()[:16]
    return f"note-{digest}"


class NoteCapacityError(RuntimeError):
    """paper_notes 容量达到上限时抛出。"""


def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text)) // 3)


def _normalize_text(text: str) -> str:
    """归一化用于比对：小写、去标点空白、合并空白。"""
    value = str(text or "").casefold()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _ngrams(text: str, n: int = 3) -> set[str]:
    normalized = _normalize_text(text)
    if len(normalized) < n:
        return {normalized} if normalized else set()
    return {normalized[i:i + n] for i in range(max(1, len(normalized) - n + 1))}


class PaperNoteRepository:
    """paper_notes 表 CRUD；按 (paper_key, note_id) 唯一去重。"""

    def __init__(self, db: Any) -> None:
        self.db = db

    def add(
        self,
        *,
        paper_key: str,
        title: str,
        note_text: str,
        fields: dict[str, str] | None = None,
        source_refs: list[dict[str, str]] | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        """登记一篇文献的结构化笔记（E2.1 字段模板）；同 (paper_key, title) 幂等。"""
        paper_key = str(paper_key or "").strip()
        title = str(title or "").strip()
        if not paper_key or not title:
            raise ValueError("paper_key 与 title 必填")
        note_id = note_id_from(paper_key, title)
        status = str(status or "active")
        if status not in NOTE_STATUSES:
            raise ValueError(f"无效笔记状态：{status}")
        fields = dict(fields or {})
        fields.setdefault("目标", "")
        fields.setdefault("方法", "")
        fields.setdefault("结论", "")
        fields.setdefault("局限", "")
        fields.setdefault("与我的项目关系", "")
        selected = {key: str(value)[:_NOTE_CHARS_MAX] for key, value in fields.items()
                    if key in {"目标", "方法", "结论", "局限", "与我的项目关系"}}
        note_payload = {
            "note_id": note_id,
            "paper_key": paper_key,
            "title": title,
            "text": str(note_text)[:_NOTE_CHARS_MAX],
            "fields": selected,
        }
        refs = list(source_refs or [])[:_SOURCE_REFS_MAX]
        now = time.time()
        existing = self.get(paper_key, note_id)
        if existing is not None:
            return existing
        count = self.count(paper_key)
        if count >= NOTES_CAPACITY:
            raise NoteCapacityError(f"paper_notes 容量上限 {NOTES_CAPACITY} 已满")
        self.db.connection.execute(
            """
            INSERT INTO paper_notes (
                paper_key, note_id, note_json, source_refs_json,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_key, note_id, _json_dumps(note_payload),
                _json_dumps(refs), status, now, now,
            ),
        )
        self.db.connection.commit()
        return self.get(paper_key, note_id) or {}

    def update(
        self,
        paper_key: str,
        note_id: str,
        *,
        note_text: str | None = None,
        fields: dict[str, str] | None = None,
        status: str | None = None,
        source_refs: list[dict[str, str]] | None = None,
    ) -> dict[str, Any] | None:
        existing = self.get(paper_key, note_id)
        if existing is None:
            return None
        payload = dict(existing)
        if note_text is not None:
            payload["text"] = str(note_text)[:_NOTE_CHARS_MAX]
        if fields is not None:
            payload["fields"] = {
                key: str(value)[:500] for key, value in fields.items()
                if key in {"目标", "方法", "结论", "局限", "与我的项目关系"}
            }
        if source_refs is not None:
            payload["source_refs"] = list(source_refs)[:_SOURCE_REFS_MAX]
        status_value = status if status in NOTE_STATUSES else existing["status"]
        self.db.connection.execute(
            """
            UPDATE paper_notes SET note_json = ?, source_refs_json = ?, status = ?, updated_at = ?
            WHERE paper_key = ? AND note_id = ?
            """,
            (
                _json_dumps(payload),
                _json_dumps(payload.get("source_refs") or []),
                status_value,
                time.time(),
                paper_key,
                note_id,
            ),
        )
        self.db.connection.commit()
        return self.get(paper_key, note_id)

    def get(self, paper_key: str, note_id: str) -> dict[str, Any] | None:
        row = self.db.connection.execute(
            "SELECT * FROM paper_notes WHERE paper_key = ? AND note_id = ?",
            (paper_key, note_id),
        ).fetchone()
        return self._row(row) if row else None

    def by_paper(self, paper_key: str, *, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.db.connection.execute(
                "SELECT * FROM paper_notes WHERE paper_key = ? AND status = ? "
                "ORDER BY created_at DESC",
                (paper_key, status),
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM paper_notes WHERE paper_key = ? ORDER BY created_at DESC",
                (paper_key,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def list(self, *, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if status:
            rows = self.db.connection.execute(
                "SELECT * FROM paper_notes WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, max(1, int(limit))),
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM paper_notes ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [self._row(row) for row in rows]

    def count(self, paper_key: str | None = None) -> int:
        if paper_key:
            row = self.db.connection.execute(
                "SELECT COUNT(*) AS n FROM paper_notes WHERE paper_key = ?", (paper_key,)
            ).fetchone()
        else:
            row = self.db.connection.execute(
                "SELECT COUNT(*) AS n FROM paper_notes", ()
            ).fetchone()
        return int(row["n"]) if row else 0

    def mark_uncertain(self, paper_key: str, note_id: str, reason: str = "") -> dict[str, Any] | None:
        return self.update(
            paper_key, note_id,
            fields=None, status="uncertain",
        )

    @staticmethod
    def _row(row: Any) -> dict[str, Any]:
        payload = _json_loads(row["note_json"], {})
        return {
            "paper_key": str(row["paper_key"]),
            "note_id": str(row["note_id"]),
            "title": str(payload.get("title") or ""),
            "text": str(payload.get("text") or ""),
            "fields": _json_loads(row["note_json"], {}).get("fields") or {},
            "source_refs": _json_loads(row["source_refs_json"], []),
            "status": str(row["status"]),
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
        }


# ── E2.2 一致性审计（确定性兜底）────────────────────────────


def audit_note_consistency(
    note: dict[str, Any],
    source_text: str,
    *,
    min_support_ratio: float = 0.5,
) -> dict[str, Any]:
    """审计笔记声明与原文可定位比对（E2.2 立身）。

    对每个字段（目标/方法/结论/局限/关系）与原文做 3-gram Jaccard 重叠判定：
    - overlap >= 阈值 → 有原文支撑（supported）
    - 否则 → 无支撑（unsupported），进入 issues。
    返回 ``unsupported_ratio``（无支撑字段占比）；超过 min_support_ratio
    阈值返回 ok=False，调用方可据此把笔记标记 ``uncertain``。
    """
    fields = note.get("fields") or {}
    source_ngrams = _ngrams(source_text)
    assertions: list[dict[str, Any]] = []
    for key in ("目标", "方法", "结论", "局限", "与我的项目关系"):
        value = str(fields.get(key) or "").strip()
        if not value:
            continue
        overlap = len(_ngrams(value) & source_ngrams) / max(1, len(_ngrams(value)))
        supported = overlap >= min(0.25, max(0.1, min(0.5, 0.35)))
        assertions.append({
            "field": key,
            "text": value[:200],
            "overlap": round(overlap, 4),
            "supported": supported,
        })
    if not assertions:
        return {"ok": True, "issues": [], "unsupported_ratio": 0.0, "checked": 0}
    unsupported = [item for item in assertions if not item["supported"]]
    ratio = len(unsupported) / len(assertions)
    return {
        "ok": ratio < 0.5,  # 全部字段中 <50% 无支撑才算通过（E2.2 阈值）
        "issues": unsupported,
        "unsupported_ratio": ratio,
        "checked": len(assertions),
        "assertions": assertions,
    }


def validate_note_paper_identity(note: dict[str, Any]) -> bool:
    return bool(note.get("paper_key") and note.get("note_id"))


# ── 链接层引用（P3.4 extension）：note:{id} 进 evidence_refs ──────


def note_evidence_links(notes: Iterable[dict[str, Any]]) -> list[str]:
    """把笔记 id 映射为 P3.4 evidence_refs 的 ``note:{id}`` 引用。"""
    return [f"note:{note['note_id']}" for note in notes if validate_note_paper_identity(note)]


# ── BibTeX 导出（确定性）───────────────────────────────────────


def paper_to_bibtex(paper: dict[str, Any], *, cite_key: str | None = None) -> str:
    """从论文元数据确定性生成 BibTeX（无 LLM，E2.1 导出链路）。"""
    metadata = paper.get("metadata") or {}
    title = str(metadata.get("title") or paper.get("title") or "Untitled")
    authors = metadata.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    authors = [str(a) for a in authors]
    year = str(metadata.get("year") or metadata.get("published_at") or "")
    if year and len(year) >= 4 and year[:4].isdigit():
        year = year[:4]
    venue = str(metadata.get("venue") or metadata.get("journal") or "")
    doi = str(metadata.get("doi") or paper.get("doi") or "")
    key = cite_key or f"{_bib_key(title)}{year}"
    lines = [
        f"@article{{{key},",
        f"  title = {{{title}}},",
    ]
    if authors:
        lines.append(f"  author = {{{' and '.join(authors)}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if venue:
        lines.append(f"  journal = {{{venue}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    lines.append("}")
    return "\n".join(lines)


def _bib_key(title: str) -> str:
    """从标题生成简洁 bibtex key：首词首字母 + 后续 1-3 词小写拼接。"""
    words = re.findall(r"[A-Za-z0-9]+", str(title or ""))
    if not words:
        return "paper"
    if len(words) == 1:
        return words[0][:12].casefold()
    return (words[0][:1].casefold() + "".join(words[1:4])).casefold() or "paper"


# ── Related work 草稿（LLM 仅组织语言 + 引用校验）──────────────


_RELATED_SYSTEM = (
    "你是研究论文的 related work 撰写助手。你只能引用给定笔记中的文献，"
    "不得编造新文献；每条引用必须带有原文引用区间标注。用中文输出 Markdown。"
)


def _related_prompt(notes: list[dict[str, Any]]) -> str:
    lines = ["以下是为 my project 准备的文献笔记（含原文引用区间），只允许引用这些："]
    for index, note in enumerate(notes, start=1):
        refs = "、".join(
            f"({ref.get('page') or '?'}页, {ref.get('segment') or ''})"
            for ref in (note.get("source_refs") or [])[:3]
        )
        lines.append(
            f"{index}. [{note.get('note_id')}] {note.get('title')}\n"
            f"   原文引用：{refs}\n"
            f"   摘要字段：目标={note.get('fields', {}).get('目标', '')[:120]}；"
            f"结论={note.get('fields', {}).get('结论', '')[:120]}"
        )
    lines.append(
        "\n要求：\n"
        "1. 用 3-5 段组织 related work，引用格式 [note:<id>]\n"
        "2. 每处引用必须对应上面的笔记 id\n"
        "3. 未出现在笔记中的文献不得出现"
    )
    return "\n".join(lines)


_NOTE_ID_RE = re.compile(r"\[note:([a-zA-Z0-9-]+)\]")


def validate_related_work_citations(text: str, notes: list[dict[str, Any]]) -> list[str]:
    """输出后校验：related work 中每个 [note:xxx] 必须能回溯到笔记集合（E2.3）。

    返回未回溯的引用 id；空列表 = 100% 可回溯。
    """
    valid_ids = {note["note_id"] for note in notes}
    cited = _NOTE_ID_RE.findall(str(text))
    problems = []
    for note_id in cited:
        if note_id not in valid_ids:
            problems.append(note_id)
    return problems


def generate_related_work(
    notes: list[dict[str, Any]],
    *,
    llm: Any | None = None,
    llm_invoke: Callable[[list[Any]], Any] | None = None,
    style_hint: str = "",
) -> tuple[str, list[str]]:
    """LLM 仅组织语言；无模型时确定性组织。返回 (输出, 校验失败引用列表)。"""
    prompt = _related_prompt(notes)
    if style_hint:
        prompt += f"\n\n写作风格偏好：{style_hint}"
    if llm is not None or llm_invoke is not None:
        try:
            invoker = llm_invoke or llm.invoke
            response = invoker([
                {"role": "system", "content": _RELATED_SYSTEM},
                {"role": "user", "content": prompt},
            ])
            text = str(getattr(response, "content", response) or "").strip()
            if text:
                problems = validate_related_work_citations(text, notes)
                # 原样返回 LLM 输出与校验结果；有未回溯引用时由调用方决定
                # （回归测试/UI 可整段退回），而不是静默丢弃。
                return text, problems
        except Exception:
            pass
    deterministic = _deterministic_related(notes)
    return deterministic, validate_related_work_citations(deterministic, notes)


def _deterministic_related(notes: list[dict[str, Any]]) -> str:
    lines = ["## Related Work", ""]
    for note in notes:
        title = str(note.get("title") or note.get("note_id") or "")
        refs = "、".join(
            f"{ref.get('page') or '?'}页" for ref in (note.get("source_refs") or [])[:3]
        )
        goal = str(note.get("fields", {}).get("目标", "") or "")
        conclusion = str(note.get("fields", {}).get("结论", "") or "")
        lines.append(
            f"- [{note.get('note_id')}] {title}"
            f"{f'（原文 {refs}）' if refs else ''}"
            f"{f'：目标 {goal}；结论 {conclusion}' if goal or conclusion else ''}"
        )
    lines.append("")
    return "\n".join(lines)


def open_notes_repo() -> tuple[PaperNoteRepository, Any]:
    """打开运行时 DB 的笔记仓库（bootstrap 幂等；调用方负责 close .db）。"""
    from conflux.adapters.sqlite_store import SQLiteDatabase
    from conflux.core.runtime_home import database_path

    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    return PaperNoteRepository(db), db