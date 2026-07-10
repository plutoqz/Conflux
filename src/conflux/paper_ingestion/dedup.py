"""Deterministic paper deduplication."""

from __future__ import annotations

import re

from .models import PaperRecord


def deduplicate_papers(papers: list[PaperRecord]) -> list[PaperRecord]:
    """Deduplicate papers by DOI, source ID, or normalized title."""

    merged: list[PaperRecord] = []
    by_key: dict[str, PaperRecord] = {}
    for paper in papers:
        key = _dedup_key(paper)
        if not key:
            merged.append(paper)
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = paper
            merged.append(paper)
        else:
            _merge_into(existing, paper)
    return merged


def _dedup_key(paper: PaperRecord) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.source and paper.id:
        source = paper.source.lower()
        paper_id = _normalize_source_id(source, paper.id)
        return f"{source}:{paper_id.lower()}"
    title = _normalize_title(paper.title)
    return f"title:{title}" if title else ""


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _normalize_source_id(source: str, paper_id: str) -> str:
    text = paper_id.strip()
    if source == "arxiv":
        if "/abs/" in text:
            text = text.rsplit("/abs/", 1)[1]
        if "/pdf/" in text:
            text = text.rsplit("/pdf/", 1)[1]
        if text.endswith(".pdf"):
            text = text[:-4]
    return text


def _merge_into(target: PaperRecord, incoming: PaperRecord) -> None:
    if not target.abstract and incoming.abstract:
        target.abstract = incoming.abstract
    if not target.url and incoming.url:
        target.url = incoming.url
    if not target.pdf_url and incoming.pdf_url:
        target.pdf_url = incoming.pdf_url
    if not target.venue and incoming.venue:
        target.venue = incoming.venue
    for author in incoming.authors:
        if author not in target.authors:
            target.authors.append(author)
    for category in incoming.categories:
        if category not in target.categories:
            target.categories.append(category)
    for query in incoming.matched_queries:
        if query not in target.matched_queries:
            target.matched_queries.append(query)
    target.metadata.update({k: v for k, v in incoming.metadata.items() if k not in target.metadata})
