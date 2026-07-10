"""arXiv query building and record normalization."""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from conflux.research_profile import ResearchProfile

from .models import PaperRecord, parse_datetime


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def build_arxiv_query(keywords: list[str], categories: list[str] | None = None) -> str:
    """Build a compact arXiv search query from keywords and optional categories."""

    keyword_terms = [f'all:"{keyword}"' for keyword in keywords if keyword.strip()]
    category_terms = [f"cat:{category}" for category in (categories or []) if category.strip()]
    terms = keyword_terms + category_terms
    return " OR ".join(terms) if terms else "all:research"


def profile_arxiv_queries(profile: ResearchProfile, *, max_queries: int = 5) -> list[str]:
    """Derive arXiv query strings from a research profile."""

    queries = []
    for keyword in profile.keywords[:max_queries]:
        queries.append(build_arxiv_query([keyword]))
    return queries or [build_arxiv_query(profile.fields[:1])]


def normalize_arxiv_entry(entry: dict[str, Any]) -> PaperRecord:
    """Normalize an arXiv API-like dictionary into `PaperRecord`."""

    paper_id = _arxiv_id(str(entry.get("id") or entry.get("arxiv_id") or ""))
    links = entry.get("links") or []
    url = str(entry.get("url") or entry.get("id") or "")
    pdf_url = str(entry.get("pdf_url") or "")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            href = str(link.get("href") or "")
            title = str(link.get("title") or "").lower()
            link_type = str(link.get("type") or "").lower()
            if not pdf_url and (title == "pdf" or link_type == "application/pdf"):
                pdf_url = href
            if not url and href:
                url = href

    categories = entry.get("categories") or entry.get("category") or entry.get("primary_category")
    return PaperRecord(
        id=paper_id,
        title=_clean_text(str(entry.get("title") or "")),
        abstract=_clean_text(str(entry.get("summary") or entry.get("abstract") or "")),
        authors=_authors(entry.get("authors")),
        published_at=parse_datetime(entry.get("published") or entry.get("published_at")),
        source="arxiv",
        url=url,
        pdf_url=pdf_url,
        doi=str(entry.get("doi") or ""),
        categories=_string_list(categories),
        matched_queries=_string_list(entry.get("matched_queries")),
        metadata={"raw_id": entry.get("id", "")},
    )


def search_arxiv(query: str, *, max_results: int = 10) -> list[PaperRecord]:
    """Run a real arXiv API search. This is intentionally not used by offline tests."""

    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    with urllib.request.urlopen(f"{ARXIV_API_URL}?{params}", timeout=30) as response:
        feed = response.read()
    return parse_arxiv_feed(feed, matched_query=query)


def parse_arxiv_feed(feed_xml: bytes | str, *, matched_query: str = "") -> list[PaperRecord]:
    """Parse an arXiv Atom feed into paper records."""

    root = ET.fromstring(feed_xml)
    records = []
    for entry in root.findall(f"{ATOM}entry"):
        payload = {
            "id": _text(entry.find(f"{ATOM}id")),
            "title": _text(entry.find(f"{ATOM}title")),
            "summary": _text(entry.find(f"{ATOM}summary")),
            "published": _text(entry.find(f"{ATOM}published")),
            "authors": [_text(author.find(f"{ATOM}name")) for author in entry.findall(f"{ATOM}author")],
            "doi": _text(entry.find(f"{ARXIV}doi")),
            "categories": [node.attrib.get("term", "") for node in entry.findall(f"{ATOM}category")],
            "links": [dict(node.attrib) for node in entry.findall(f"{ATOM}link")],
            "matched_queries": [matched_query] if matched_query else [],
        }
        records.append(normalize_arxiv_entry(payload))
    return records


def _arxiv_id(value: str) -> str:
    text = value.strip()
    if "/abs/" in text:
        text = text.rsplit("/abs/", 1)[1]
    if "/pdf/" in text:
        text = text.rsplit("/pdf/", 1)[1]
    if text.endswith(".pdf"):
        text = text[:-4]
    return text


def _authors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    authors = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("name") or "").strip()
        else:
            text = str(item).strip()
        if text:
            authors.append(text)
    return authors


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_string_list(item))
        return result
    text = str(value).strip()
    return [text] if text else []


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _text(node) -> str:
    return "" if node is None or node.text is None else node.text.strip()
