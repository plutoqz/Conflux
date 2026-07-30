"""Semantic Scholar paper source — title/abstract search via REST API.

Uses the public Semantic Scholar API (no key required at the free tier).
Rate limit: ~1 request/second.  Falls back gracefully on 429/5xx.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from .models import PaperRecord, parse_datetime

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_DETAIL_FIELDS = (
    "title,abstract,authors,year,publicationDate,externalIds,url,"
    "publicationVenue,fieldsOfStudy,citationCount"
)

# Rate limiting
_MIN_INTERVAL_S = 1.0  # 1 req/sec for public API
_last_request_time: float = 0.0


def _rate_limit() -> None:
    """Enforce the 1 req/sec rate limit."""
    global _last_request_time
    now = time.time()
    wait = _MIN_INTERVAL_S - (now - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


def search_semantic_scholar(
    query: str,
    *,
    max_results: int = 20,
    offset: int = 0,
    year_from: int | None = None,
    year_to: int | None = None,
    fields_of_study: list[str] | None = None,
) -> list[PaperRecord]:
    """Search Semantic Scholar by title/abstract keywords.

    Parameters
    ----------
    query: Free-text search query (AND/OR supported).
    max_results: Maximum records to return (1-100).
    offset: Pagination offset.
    year_from: Filter papers published on or after this year.
    year_to: Filter papers published on or before this year.
    fields_of_study: Optional filter, e.g. ['Computer Science'].
    """
    max_results = max(1, min(100, max_results))

    params: dict[str, Any] = {
        "query": query,
        "limit": max_results,
        "offset": offset,
        "fields": S2_DETAIL_FIELDS,
    }
    if year_from:
        params["year"] = f"{year_from}-" + (str(year_to) if year_to else "")
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    url = f"{S2_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    _rate_limit()

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(5)
            return search_semantic_scholar(
                query, max_results=max_results, offset=offset,
                year_from=year_from, year_to=year_to,
                fields_of_study=fields_of_study,
            )
        return []
    except Exception:
        return []

    papers_data = data.get("data") or []
    records: list[PaperRecord] = []
    for p in papers_data:
        records.append(_normalize_s2_paper(p, matched_query=query))

    # Fetch next page if available
    next_offset = data.get("next")
    if next_offset and len(records) < max_results:
        remaining = max_results - len(records)
        try:
            more = search_semantic_scholar(
                query, max_results=remaining, offset=int(next_offset),
                year_from=year_from, year_to=year_to,
                fields_of_study=fields_of_study,
            )
            records.extend(more)
        except Exception:
            pass

    return records


def _normalize_s2_paper(paper: dict[str, Any], *, matched_query: str = "") -> PaperRecord:
    """Convert a Semantic Scholar paper dict into a PaperRecord."""
    paper_id = str(paper.get("paperId") or "")

    external_ids = paper.get("externalIds") or {}
    doi = str(external_ids.get("DOI") or external_ids.get("doi") or "")
    arxiv_id = str(
        external_ids.get("ArXiv")
        or external_ids.get("arXiv")
        or external_ids.get("arxiv")
        or ""
    )

    title = str(paper.get("title") or "")
    abstract = str(paper.get("abstract") or "")

    authors_raw = paper.get("authors") or []
    authors = [str(a.get("name") or "") for a in authors_raw if a.get("name")]

    venue_raw = paper.get("publicationVenue") or paper.get("journal") or {}
    venue = str(venue_raw.get("name") or "")

    year = paper.get("year")
    pub_date = paper.get("publicationDate") or ""
    published_at = parse_datetime(pub_date) if pub_date else None

    s2_url = f"https://api.semanticscholar.org/CorpusID:{paper_id}" if paper_id else ""

    return PaperRecord(
        id=paper_id,
        title=title,
        abstract=abstract,
        authors=authors,
        published_at=published_at,
        source="semantic_scholar",
        url=s2_url,
        pdf_url="",
        doi=doi,
        venue=venue,
        categories=paper.get("fieldsOfStudy") or [],
        matched_queries=[matched_query] if matched_query else [],
        metadata={
            "s2_id": paper_id,
            "arxiv_id": arxiv_id,
            "citation_count": paper.get("citationCount"),
            "year": year,
        },
    )


def resolve_paper_by_doi(doi: str) -> PaperRecord | None:
    """Look up a single paper by DOI via Semantic Scholar."""
    doi = doi.strip()
    if not doi:
        return None

    url = (
        f"{S2_SEARCH_URL}?query=DOI:{urllib.parse.quote(doi)}"
        f"&limit=1&fields={S2_DETAIL_FIELDS}"
    )
    _rate_limit()

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    papers = data.get("data") or []
    if not papers:
        return None
    return _normalize_s2_paper(papers[0])


def check_s2_health() -> bool:
    """Quick health check — returns True if the S2 API is reachable."""
    try:
        url = f"{S2_SEARCH_URL}?query=test&limit=1&fields=title"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except Exception:
        return False
