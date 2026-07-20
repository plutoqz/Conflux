"""Ephemeral full-text corpus used only inside one research run."""

from __future__ import annotations

import re
import threading
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class RunCorpusChunk:
    id: str
    text: str
    title: str
    url: str
    paper_id: str
    content_hash: str
    content_kind: str
    chunk_index: int
    provider_source: str
    evidence_class: str
    published_at: str = ""
    retrieved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunScopedCorpusProvider:
    """Bounded in-memory corpus; it never writes to the user's permanent index."""

    def __init__(
        self,
        run_id: str = "",
        *,
        max_documents: int = 24,
        max_chunks: int = 240,
        chunk_chars: int = 1400,
        overlap_chars: int = 180,
    ) -> None:
        self.run_id = str(run_id or "ephemeral")
        self.max_documents = max(1, int(max_documents))
        self.max_chunks = max(1, int(max_chunks))
        self.chunk_chars = max(300, int(chunk_chars))
        self.overlap_chars = max(0, min(int(overlap_chars), self.chunk_chars // 2))
        self._chunks: dict[str, RunCorpusChunk] = {}
        self._documents: set[str] = set()
        self._fetch_cache: dict[str, Any] = {}
        self._fetching: set[str] = set()
        self._fetch_condition = threading.Condition()

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def fetch_once(self, identity: str, fetcher: Any) -> Any:
        """Run one fetch/parse operation per document identity within this run."""

        key = str(identity or "").strip().casefold()
        if not key:
            return fetcher()
        with self._fetch_condition:
            while key in self._fetching:
                self._fetch_condition.wait()
            if key in self._fetch_cache:
                return self._fetch_cache[key]
            self._fetching.add(key)
        try:
            value = fetcher()
        except BaseException:
            with self._fetch_condition:
                self._fetching.discard(key)
                self._fetch_condition.notify_all()
            raise
        with self._fetch_condition:
            self._fetch_cache[key] = value
            self._fetching.discard(key)
            self._fetch_condition.notify_all()
        return value

    def ingest(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ingest one successfully fetched academic/official full body."""

        fetched = result.get("fetch")
        text = str(getattr(fetched, "text", "") or "").strip()
        status = str(getattr(fetched, "status", "") or "")
        content_kind = str(getattr(fetched, "content_kind", "") or "")
        evidence_class = str(result.get("evidence_class") or "")
        academic = evidence_class in {"peer_reviewed", "preprint", "authoritative_document"}
        if status != "success" or content_kind == "abstract" or not academic or len(text) < 300:
            return {"status": "skipped", "reason": "not a fetched high-value full body", "chunk_count": 0}
        url = str(getattr(fetched, "final_url", "") or result.get("url") or "").strip()
        content_hash = str(getattr(fetched, "content_hash", "") or sha256(text.encode("utf-8")).hexdigest())
        identity = str(result.get("paper_id") or url or content_hash).casefold()
        if identity in self._documents:
            return {"status": "duplicate", "identity": identity, "chunk_count": 0}
        if len(self._documents) >= self.max_documents:
            return {"status": "capacity", "reason": "document limit reached", "chunk_count": 0}

        chunks = _chunk_text(text, self.chunk_chars, self.overlap_chars)
        available = max(0, self.max_chunks - len(self._chunks))
        chunks = chunks[:available]
        title = str(getattr(fetched, "title", "") or result.get("title") or "").strip()
        added = 0
        for index, chunk_text in enumerate(chunks):
            chunk_id = f"run:{self.run_id}:{content_hash[:16]}:{index}"
            if chunk_id in self._chunks:
                continue
            self._chunks[chunk_id] = RunCorpusChunk(
                id=chunk_id,
                text=chunk_text,
                title=title,
                url=url,
                paper_id=str(result.get("paper_id") or ""),
                content_hash=content_hash,
                content_kind=content_kind or "body",
                chunk_index=index,
                provider_source=str(result.get("provider_source") or "web"),
                evidence_class=evidence_class or "authoritative_document",
                published_at=str(getattr(fetched, "published_at", "") or ""),
                retrieved_at=str(getattr(fetched, "retrieved_at", "") or ""),
            )
            added += 1
        if added:
            self._documents.add(identity)
        return {"status": "indexed" if added else "capacity", "identity": identity, "chunk_count": added}

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Rank prior run chunks lexically with document diversity."""

        query_terms = _tokens(query)
        if not query_terms:
            return []
        ranked: list[tuple[float, RunCorpusChunk]] = []
        for chunk in self._chunks.values():
            text_terms = _tokens(chunk.title + " " + chunk.text)
            overlap = len(query_terms & text_terms) / max(1, len(query_terms))
            phrase = 1.0 if str(query).casefold() in chunk.text.casefold() else 0.0
            authority = 1.0 if chunk.evidence_class in {"peer_reviewed", "authoritative_document"} else 0.75
            score = (0.72 * overlap) + (0.12 * phrase) + (0.16 * authority)
            if score >= 0.22:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        selected: list[dict[str, Any]] = []
        per_document: dict[str, int] = {}
        for score, chunk in ranked:
            identity = chunk.paper_id or chunk.url or chunk.content_hash
            if per_document.get(identity, 0) >= 2:
                continue
            selected.append({**chunk.to_dict(), "score": round(score, 4), "run_scoped": True})
            per_document[identity] = per_document.get(identity, 0) + 1
            if len(selected) >= max(1, int(limit)):
                break
        return selected

    def diagnostics(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "storage": "memory",
            "persistent": False,
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "fetch_cache_count": len(self._fetch_cache),
            "max_documents": self.max_documents,
            "max_chunks": self.max_chunks,
        }


def _chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", str(text or ""))
    paragraphs = [re.sub(r"\s+", " ", item).strip() for item in re.split(r"\n{2,}", normalized) if item.strip()]
    if not paragraphs:
        paragraphs = [re.sub(r"\s+", " ", normalized).strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= chunk_chars:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        carry = buffer[-overlap_chars:] if buffer and overlap_chars else ""
        buffer = f"{carry} {paragraph}".strip()
        while len(buffer) > chunk_chars:
            split = buffer.rfind(" ", 0, chunk_chars)
            split = split if split >= chunk_chars // 2 else chunk_chars
            chunks.append(buffer[:split].strip())
            start = max(0, split - overlap_chars)
            buffer = buffer[start:].strip()
    if buffer:
        chunks.append(buffer)
    return [item for item in chunks if len(item) >= 120]


def _tokens(text: str) -> set[str]:
    value = str(text or "").casefold()
    latin = re.findall(r"[a-z][a-z0-9_.+-]{1,}", value)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,6}", value)
    return set(latin + chinese)
