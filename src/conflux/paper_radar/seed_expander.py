"""P2.6 citation seed expansion — grow the candidate pool from known papers.

Seeds are globally-ingested papers (``papers`` table) plus user-confirmed
links; each seed's references and citations are fetched from Semantic Scholar
up to ``citation_seed_hop`` hops, bounded by ``citation_seed_budget`` API
calls.  Already-ingested and already-seen papers are excluded, so the seeds
only bring in papers the user has not seen before.

Semantic Scholar Graph API accepts external ids as ``paper_id``:
``arXiv:<id>``, ``DOI:<doi>``, ``CorpusID:<id>`` — this lets us query with
the keys we already store in ``papers.paper_key``.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from conflux.core.p2_contracts import ProjectResearchConfig
from conflux.paper_ingestion.models import PaperRecord
from conflux.paper_ingestion.semantic_scholar_source import (
    S2_DETAIL_FIELDS,
    _normalize_s2_paper,
)
from conflux.research_profile.models import ResearchProfile

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper"

# Public API rate limit: ~1 request/second.
_MIN_INTERVAL_S = 1.0
_last_request_time: float = 0.0


def _rate_limit() -> None:
    global _last_request_time
    now = time.time()
    wait = _MIN_INTERVAL_S - (now - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


def _s2_id_from_paper_key(paper_key: str) -> str | None:
    """Map a global paper_key ('arxiv:...' / 'doi:...') to an S2 external id."""
    paper_key = str(paper_key or "").strip()
    if not paper_key:
        return None
    if paper_key.startswith("arxiv:"):
        value = paper_key[len("arxiv:"):].strip()
        return f"arXiv:{value}" if value else None
    if paper_key.startswith("doi:"):
        value = paper_key[len("doi:"):].strip()
        return f"DOI:{value}" if value else None
    return None


def _fetch_relations(s2_id: str, relation: str, limit: int) -> list[dict[str, Any]]:
    """Fetch one page of references/citations for an S2 paper id."""
    params = urllib.parse.urlencode({
        "fields": S2_DETAIL_FIELDS,
        "limit": min(100, max(1, limit)),
    })
    url = f"{S2_BASE}/{urllib.parse.quote(s2_id, safe='')}/{relation}?{params}"
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return data.get("data") or []


def _relation_paper(entry: dict[str, Any], relation: str) -> dict[str, Any] | None:
    """Extract the paper payload from a references/citations entry."""
    if relation == "references":
        return entry.get("citedPaper")
    if relation == "citations":
        return entry.get("citingPaper")
    return None


def collect_citation_seeds(
    db: Any,
    *,
    profile: ResearchProfile,
    config: ProjectResearchConfig,
    seen_keys: set[str] | None = None,
) -> list[PaperRecord]:
    """Expand known papers into new candidates via citation references/citations.

    Returns new PaperRecords (matched_query="citation_seed") that are not
    already ingested and not in the seen set.  ``None`` when no seeds exist
    (empty or all-seen seed set) — the radar uses this to record
    ``no_citation_seeds``.  Empty list when disabled or the API budget is
    exhausted.
    """
    if not config.citation_seed_enabled:
        return []
    from conflux.adapters.sqlite_store import list_ingested_paper_keys

    ingested = list_ingested_paper_keys(db)
    if not ingested:
        return None
    seen_keys = seen_keys or set()

    seeds: list[str] = []
    for key in sorted(ingested):
        s2_id = _s2_id_from_paper_key(key)
        if s2_id:
            seeds.append(s2_id)

    budget_remaining = max(1, config.citation_seed_budget)
    hop_limit = max(1, config.citation_seed_hop)
    per_paper = max(1, config.citation_seed_per_paper)

    collected: dict[str, dict[str, Any]] = {}
    queue: list[tuple[str, int]] = [(seed, 0) for seed in seeds]
    visited: set[str] = set()

    while queue and budget_remaining > 0:
        s2_id, hop = queue.pop(0)
        if hop >= hop_limit or s2_id in visited:
            continue
        visited.add(s2_id)
        for relation in ("references", "citations"):
            if budget_remaining <= 0:
                break
            budget_remaining -= 1
            entries = _fetch_relations(s2_id, relation, per_paper)
            for entry in entries:
                paper = _relation_paper(entry, relation)
                if not paper:
                    continue
                paper_id = str(paper.get("paperId") or "")
                if not paper_id:
                    continue
                collected.setdefault(paper_id, paper)
                if hop + 1 < hop_limit:
                    queue.append((f"CorpusID:{paper_id}", hop + 1))

    records: list[PaperRecord] = []
    for paper_id, payload in collected.items():
        paper = _normalize_s2_paper(payload, matched_query="citation_seed")
        # Prefer the arXiv identity when present so ingested/seen exclusion
        # matches the global key convention ('arxiv:<id>' / 'doi:<doi>').
        meta = paper.metadata or {}
        arxiv_id = str(meta.get("arxiv_id") or "").strip()
        if arxiv_id:
            key = f"arxiv:{arxiv_id}"
        elif paper.doi:
            key = f"doi:{paper.doi.strip().casefold()}"
        else:
            key = f"{paper.source}:{paper.id}"
        if key in ingested or key in seen_keys:
            continue
        records.append(paper)
    if not records:
        # Seeds existed but every expandable paper was already ingested or
        # seen — nothing new this round.  Returning [] (not None) keeps the
        # "no seeds at all" signal distinct from "seeds fully consumed".
        return []
    return records
