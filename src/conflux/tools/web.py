"""Web search tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from typing import Callable
from urllib.parse import urlparse

from langchain_core.tools import tool

from ..config import get
from ..query_planner import (
    DOMAIN_PRIORITY,
    LOW_QUALITY_DOMAINS,
    entity_score,
    extract_entities,
    important_terms,
    is_academic_query,
    is_temporal_query,
    overlap_score,
    plan_queries,
    rewrite_queries,
    standard_identifiers,
    temporal_years,
)
from ..research_modes import ResearchModeProfile
from ..run_corpus import RunScopedCorpusProvider
from ..source_status import AgentClaim, SourceResult


_REQUEST_TIMEOUT_SECONDS: ContextVar[float | None] = ContextVar(
    "conflux_web_request_timeout_seconds",
    default=None,
)


_TOPIC_ANCHOR_FAMILIES = (
    (
        "地理处理", "地理空间", "空间分析", "geoprocessing", "geospatial",
        "geographic information system", "spatial analysis", "autonomous gis", "gis agent",
    ),
)


@dataclass(frozen=True)
class SearchProvider:
    """Small adapter boundary for a web search provider."""

    name: str
    search: Callable[[str, int], list[dict]]
    credential_env: tuple[str, ...] = ()

    def available(self) -> bool:
        return not self.credential_env or all(os.environ.get(key, "").strip() for key in self.credential_env)


@dataclass(frozen=True)
class FetchedContent:
    """Normalized body content acquired from one discovered URL."""

    url: str
    final_url: str
    title: str
    text: str
    content_type: str
    content_kind: str
    status: str
    published_at: str = ""
    retrieved_at: str = ""
    content_hash: str = ""
    error: str = ""
    prompt_injection_detected: bool = False

    @property
    def usable(self) -> bool:
        return self.status in {"success", "abstract_only"} and bool(self.text.strip())


class _HTMLContentExtractor(HTMLParser):
    """Extract readable body text and basic publication metadata."""

    _SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "form"}
    _BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "article", "section", "td", "th", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buffer: list[str] = []
        self._skip_depth = 0
        self._title_depth = 0
        self.title = ""
        self.published_at = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        if lowered in self._SKIP_TAGS:
            self._skip_depth += 1
        if lowered == "title":
            self._title_depth += 1
        if lowered == "meta":
            values = {str(key).casefold(): str(value or "") for key, value in attrs}
            name = (values.get("property") or values.get("name") or "").casefold()
            if name in {"article:published_time", "date", "datepublished", "dc.date", "dc.date.issued"}:
                self.published_at = values.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in self._BLOCK_TAGS:
            self._flush()
        if lowered == "title" and self._title_depth:
            self._title_depth -= 1
        if lowered in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._title_depth:
            if not self.title:
                self.title = text
            return
        self._buffer.append(text)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", " ".join(self._buffer)).strip()
        self._buffer.clear()
        if len(text) >= 20 and (not self.blocks or self.blocks[-1] != text):
            self.blocks.append(text)


def _search_bing(query: str, max_results: int = 5) -> list[dict]:
    """Search Bing through the authorized Web Search API."""

    api_key = os.environ.get("BING_SEARCH_API_KEY", "").strip()
    if not api_key:
        return [{"title": "Search unavailable", "snippet": "BING_SEARCH_API_KEY is not set", "url": "", "status": "failed"}]
    params = urllib.parse.urlencode({
        "q": query,
        "count": max_results,
        "textDecorations": "false",
        "textFormat": "Raw",
    })
    request = urllib.request.Request(
        f"https://api.bing.microsoft.com/v7.0/search?{params}",
        headers={"Ocp-Apim-Subscription-Key": api_key, "User-Agent": "Conflux/0.1 research-assistant"},
    )
    with urllib.request.urlopen(request, timeout=_bounded_http_timeout(10)) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [
        {
            "title": item.get("name", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("url", ""),
            "provider_source": "bing",
        }
        for item in ((payload.get("webPages") or {}).get("value") or [])[:max_results]
    ]


def _search_google(query: str, max_results: int = 5) -> list[dict]:
    """Search Google through the authorized Programmable Search API."""

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    cx = (os.environ.get("GOOGLE_CSE_ID", "") or os.environ.get("GOOGLE_CX", "")).strip()
    if not api_key or not cx:
        return [{"title": "Search unavailable", "snippet": "GOOGLE_API_KEY or GOOGLE_CSE_ID is not set", "url": "", "status": "failed"}]
    params = urllib.parse.urlencode({"key": api_key, "cx": cx, "q": query, "num": min(10, max_results)})
    request = urllib.request.Request(
        f"https://www.googleapis.com/customsearch/v1?{params}",
        headers={"User-Agent": "Conflux/0.1 research-assistant"},
    )
    with urllib.request.urlopen(request, timeout=_bounded_http_timeout(10)) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "provider_source": "google",
        }
        for item in (payload.get("items") or [])[:max_results]
    ]


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo through ddgs. It is free but can be rate limited."""

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": result.get("title", ""),
                "snippet": result.get("body", ""),
                "url": result.get("href", ""),
            }
            for result in results
        ]
    except ImportError:
        return [{"title": "Search unavailable", "snippet": "ddgs is not installed", "url": "", "status": "failed"}]
    except Exception as exc:
        return [{
            "title": "Search unavailable",
            "snippet": f"DuckDuckGo search failed ({type(exc).__name__})",
            "url": "",
            "status": "failed",
        }]


async def _search_serpapi(query: str, max_results: int = 5) -> list[dict]:
    """Search SerpAPI when SERPAPI_API_KEY is configured."""

    api_key = os.environ.get("SERPAPI_API_KEY", "")
    if not api_key:
        return [{"title": "Search unavailable", "snippet": "SERPAPI_API_KEY is not set", "url": "", "status": "failed"}]

    import aiohttp

    params = {"q": query, "api_key": api_key, "num": max_results, "engine": "google"}
    timeout = aiohttp.ClientTimeout(total=_bounded_http_timeout(10))
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get("https://serpapi.com/search", params=params) as resp:
            data = await resp.json()

    results = []
    for result in data.get("organic_results", [])[:max_results]:
        results.append({
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "url": result.get("link", ""),
        })
    return results


@tool
def search_web(query: str) -> str:
    """Search the public web, fetch result bodies, and return citeable evidence."""

    return _search_web(query)


def create_web_tool(
    research_profile: ResearchModeProfile,
    *,
    run_id: str = "",
    corpus_provider: RunScopedCorpusProvider | None = None,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
):
    """Create a Web tool whose search/fetch budget follows one research depth."""

    run_corpus = corpus_provider or RunScopedCorpusProvider(
        run_id=run_id,
        max_documents=max(8, research_profile.web_fetch_attempts * 2),
        max_chunks=max(80, research_profile.web_fetch_attempts * 24),
    )

    generalization = get(
        "research", "generalization", research_profile.depth, default={}
    ) or {}
    if not isinstance(generalization, dict):
        generalization = {}
    hard_fetch_limit = max(
        research_profile.web_fetch_limit,
        int(generalization.get("max_web_fetches") or research_profile.web_fetch_limit),
    )
    hard_fetch_attempts = max(
        hard_fetch_limit,
        research_profile.web_fetch_attempts,
        int(
            generalization.get("max_web_fetch_attempts")
            or research_profile.web_fetch_attempts
        ),
    )

    @tool("search_web")
    def profiled_search_web(
        query: str,
        max_results: int | None = None,
        max_subqueries: int | None = None,
        fetch_limit: int | None = None,
        fetch_attempts: int | None = None,
        rewrite_attempts: int | None = None,
    ) -> str:
        """Search the public web, fetch result bodies, and return citeable evidence."""

        if not _deadline_has_time(deadline_at, commit_reserve_seconds):
            return SourceResult(
                source="Web",
                status="fallback",
                detail="run deadline",
                error="Run deadline reserve reached before Web research started.",
                content="Web research was skipped to preserve report commit time.",
            ).to_tool_text()

        resolved_fetch_limit = min(
            hard_fetch_limit,
            max(1, int(fetch_limit or research_profile.web_fetch_limit)),
        )
        resolved_fetch_attempts = min(
            hard_fetch_attempts,
            max(
                resolved_fetch_limit,
                int(fetch_attempts or research_profile.web_fetch_attempts),
            ),
        )
        search_kwargs = {
            "max_results": max(
                1,
                min(
                    max(research_profile.web_max_results, 10),
                    int(max_results or research_profile.web_max_results),
                ),
            ),
            "max_subqueries": max(
                1,
                min(
                    max(research_profile.web_max_subqueries, 12),
                    int(max_subqueries or research_profile.web_max_subqueries),
                ),
            ),
            "fetch_limit": resolved_fetch_limit,
            "fetch_attempts": resolved_fetch_attempts,
            "rewrite_attempts": max(
                0,
                min(
                    research_profile.max_query_rewrites,
                    int(
                        rewrite_attempts
                        if rewrite_attempts is not None
                        else research_profile.max_query_rewrites
                    ),
                ),
            ),
            "corpus_provider": run_corpus,
        }
        if deadline_at:
            search_kwargs.update({
                "deadline_at": deadline_at,
                "commit_reserve_seconds": commit_reserve_seconds,
            })
        token = None
        if deadline_at:
            token = _REQUEST_TIMEOUT_SECONDS.set(
                _deadline_call_timeout(deadline_at, commit_reserve_seconds, 12)
            )
        try:
            return _search_web(query, **search_kwargs)
        finally:
            if token is not None:
                _REQUEST_TIMEOUT_SECONDS.reset(token)

    return profiled_search_web


def _search_web(
    query: str,
    *,
    max_results: int | None = None,
    max_subqueries: int | None = None,
    fetch_limit: int | None = None,
    fetch_attempts: int | None = None,
    rewrite_attempts: int | None = None,
    corpus_provider: RunScopedCorpusProvider | None = None,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
) -> str:
    """Execute Web research with optional run-scoped budget overrides."""

    if not _deadline_has_time(deadline_at, commit_reserve_seconds):
        return SourceResult(
            source="Web",
            status="fallback",
            detail="run deadline",
            error="Run deadline reserve reached.",
            content="Web research stopped before starting another request.",
        ).to_tool_text()
    provider = get("web_search", "provider", default="duckduckgo")
    max_results = max(1, int(
        max_results if max_results is not None else get("web_search", "max_results", default=5)
    ))
    max_subqueries = max(1, int(
        max_subqueries if max_subqueries is not None else get("web_search", "max_subqueries", default=6)
    ))
    plan = plan_queries(query, target="web", max_subqueries=max_subqueries)
    retry_queries: list[str] = []
    preferred_provider = str(provider)
    provider_trace: list[dict] = []
    used_providers: list[str] = []
    search_errors: list[str] = []
    scoped_matches = corpus_provider.search(query, limit=fetch_limit or 5) if corpus_provider else []

    academic_results: list[dict] = []
    if is_academic_query(query):
        try:
            academic_queries = _academic_query_variants([
                item for item in [*(plan.bilingual_queries or []), query]
                if str(item).strip()
            ])[:2]
            academic_results = _search_academic_sources(academic_queries, max_results=max_results)
        except Exception as exc:
            search_errors.append(f"{type(exc).__name__}: {exc}")
    results = _merge_web_results(_official_seed_results(query), academic_results)
    # Scholarly APIs are discovery channels, not a substitute for general Web
    # retrieval. They often return relevant titles whose landing pages cannot be
    # fetched, while official documentation or repositories remain accessible.
    general_queries = plan.subqueries
    official_status_query = bool(standard_identifiers(query)) or bool(re.search(
        r"\b(?:nist|nccoe|cisa|nsa|fips)\b",
        query,
        re.IGNORECASE,
    ))
    if academic_results and not official_status_query:
        general_queries = list(dict.fromkeys([
            *((plan.bilingual_queries or [])[:1]),
            query.strip(),
        ]))[:2]
    try:
        general_results, provider_trace, used_providers = _search_cascade(
            general_queries,
            max_results,
            preferred=preferred_provider,
            required_results=max(1, min(2, max_results)),
            deadline_at=deadline_at,
            commit_reserve_seconds=commit_reserve_seconds,
        )
        results = _merge_web_results(results, general_results)
    except Exception as exc:
        search_errors.append(f"{type(exc).__name__}: {exc}")
    if not results and search_errors:
        error = "; ".join(search_errors)
        if scoped_matches:
            return _run_corpus_source_result(query, scoped_matches, corpus_provider, error=error).to_tool_text()
        return SourceResult(
            source="Web",
            status="failed",
            detail=preferred_provider,
            error=error,
            content="Web search failed.",
        ).to_tool_text()

    if not results:
        if scoped_matches:
            return _run_corpus_source_result(query, scoped_matches, corpus_provider).to_tool_text()
        return SourceResult(
            source="Web",
            status="no_evidence",
            detail=preferred_provider,
            error="No web search results were found.",
            content="No web search results were found.",
            metadata={
                "query_plan": plan.to_dict(),
                "result_count": 0,
                "provider_trace": provider_trace,
                "provider_chain": used_providers,
            },
        ).to_tool_text()

    failed_results = [item for item in results if item.get("status") == "failed" or not item.get("url")]
    if len(failed_results) == len(results):
        error = "; ".join(str(item.get("snippet") or item.get("title") or "") for item in failed_results)
        if scoped_matches:
            return _run_corpus_source_result(query, scoped_matches, corpus_provider, error=error).to_tool_text()
        return SourceResult(
            source="Web",
            status="failed",
            detail=preferred_provider,
            error=error or "Web search is unavailable.",
            content=error or "Web search is unavailable.",
            metadata={
                "query_plan": plan.to_dict(),
                "result_count": len(results),
                "provider_trace": provider_trace,
                "provider_chain": used_providers,
            },
        ).to_tool_text()

    kept_results, filtered_results = _filter_web_results(query, results)
    # A provider may return URLs that all fail semantic/domain filtering. Try
    # an unused configured provider before spending rewrite attempts on the
    # same backend.
    if not kept_results:
        try:
            fallback_results, fallback_trace, fallback_used = _search_cascade(
                general_queries,
                max_results,
                preferred=preferred_provider,
                excluded=set(used_providers),
                required_results=max(1, min(2, max_results)),
                deadline_at=deadline_at,
                commit_reserve_seconds=commit_reserve_seconds,
            )
        except Exception as exc:
            fallback_results, fallback_trace, fallback_used = [], [], []
            search_errors.append(f"{type(exc).__name__}: {exc}")
        provider_trace.extend(fallback_trace)
        used_providers.extend(item for item in fallback_used if item not in used_providers)
        if fallback_results:
            results = _merge_web_results(results, fallback_results)
            kept_results, filtered_results = _filter_web_results(query, results)
    rewrite_attempts = max(0, int(
        rewrite_attempts
        if rewrite_attempts is not None
        else get("research", "max_rewrite_attempts", default=1)
    ))
    for attempt in range(1, rewrite_attempts + 1):
        if not _deadline_has_time(deadline_at, commit_reserve_seconds):
            break
        top_attempt = kept_results[0].get("_score", 0.0) if kept_results else 0.0
        if kept_results and top_attempt >= 0.55:
            break
        rewritten = rewrite_queries(query, target="web", attempt=attempt)
        retry_queries.extend(rewritten)
        try:
            retry_results, retry_trace, retry_used = _search_cascade(
                rewritten,
                max_results,
                preferred=preferred_provider,
                excluded=set(used_providers),
                required_results=max(1, min(2, max_results)),
                deadline_at=deadline_at,
                commit_reserve_seconds=commit_reserve_seconds,
            )
            provider_trace.extend(retry_trace)
            used_providers.extend(item for item in retry_used if item not in used_providers)
        except Exception:
            break
        results = _merge_web_results(results, retry_results)
        kept_results, filtered_results = _filter_web_results(query, results)
    if not kept_results:
        if scoped_matches:
            return _run_corpus_source_result(query, scoped_matches, corpus_provider).to_tool_text()
        return SourceResult(
            source="Web",
            status="no_evidence",
            detail=preferred_provider,
            error="Web search ran, but all results were off-topic or low quality.",
            content="Web search returned results, but none passed relevance and quality filtering.",
            metadata={
                "query_plan": plan.to_dict(),
                "result_count": len(results),
                "kept_count": 0,
                "filtered_count": len(filtered_results),
                "filtered_domains": sorted({_domain(item.get("url", "")) for item in filtered_results if item.get("url")}),
                "top_relevance_score": max((item.get("_score", 0.0) for item in filtered_results), default=0.0),
                "filtered_results": _filtered_results_metadata(filtered_results),
                "provider_trace": provider_trace,
                "provider_chain": used_providers,
            },
        ).to_tool_text()

    fetch_limit = max(1, int(
        fetch_limit
        if fetch_limit is not None
        else get("web_search", "max_fetched_results", default=5)
    ))
    max_fetch_attempts = max(fetch_limit, int(
        fetch_attempts
        if fetch_attempts is not None
        else get("web_search", "max_fetch_attempts", default=8)
    ))
    fetched_results, selected_results = _fetch_with_backfill(
        query,
        kept_results,
        target_limit=fetch_limit,
        attempt_limit=max_fetch_attempts,
        corpus_provider=corpus_provider,
        deadline_at=deadline_at,
        commit_reserve_seconds=commit_reserve_seconds,
    )
    usable_results = _rerank_fetched_results(
        query,
        [item for item in fetched_results if item["fetch"].usable],
    )
    corpus_ingest_trace = [corpus_provider.ingest(item) for item in usable_results] if corpus_provider else []
    if corpus_provider:
        scoped_matches = corpus_provider.search(query, limit=max(2, fetch_limit))
    fetch_trace = [
        {
            "url": item["fetch"].url,
            "final_url": item["fetch"].final_url,
            "status": item["fetch"].status,
            "content_type": item["fetch"].content_type,
            "content_kind": item["fetch"].content_kind,
            "content_hash": item["fetch"].content_hash,
            "published_at": item["fetch"].published_at or str(item.get("published_at") or ""),
            "retrieved_at": item["fetch"].retrieved_at,
            "prompt_injection_detected": item["fetch"].prompt_injection_detected,
            "matched_query": item.get("matched_query", ""),
            "matched_queries": item.get("matched_queries", []),
            "freshness_score": item.get("_freshness", 0.0),
            "final_score": item.get("_final_score", item.get("_score", 0.0)),
            "error": item["fetch"].error,
        }
        for item in fetched_results
    ]
    if not usable_results:
        if scoped_matches:
            return _run_corpus_source_result(query, scoped_matches, corpus_provider).to_tool_text()
        return SourceResult(
            source="Web",
            status="no_evidence",
            detail=f"{preferred_provider} search discovery + body fetch",
            error="Search found URLs, but no page/PDF body could be acquired as evidence.",
            content="Web search discovered candidate URLs, but none yielded citeable body content.",
            metadata={
                "query_plan": plan.to_dict(),
                "retry_queries": retry_queries,
                "result_count": len(results),
                "kept_count": len(kept_results),
                "fetched_count": 0,
                "discovered_results": _filtered_results_metadata(kept_results),
                "fetch_trace": fetch_trace,
                "provider_trace": provider_trace,
                "provider_chain": used_providers,
            },
        ).to_tool_text()

    top_score = max(float(item.get("_final_score", item.get("_score", 0.0))) for item in usable_results)
    status = "success" if top_score >= 0.55 else "low_relevance"
    confidence = 0.78 if status == "success" else 0.52
    reported_results = _reported_web_results(usable_results, status)

    parts: list[str] = []
    claims: list[AgentClaim] = []
    citations: list[dict] = []
    for i, result in enumerate(reported_results):
        fetched: FetchedContent = result["fetch"]
        title = fetched.title or str(result.get("title") or "")
        raw_url = fetched.final_url or str(result.get("url") or "")
        url = _result_identity({"url": raw_url}) if raw_url else ""
        evidence_class = _web_evidence_class(result, url)
        paper_id = str(result.get("paper_id") or _web_paper_id(url))
        evidence_ref = f"[Web:{url}]" if url else f"[Web:result-{i + 1}]"
        matched_query = str(result.get("matched_query") or "").strip()
        quote_query = "\n".join(dict.fromkeys(item for item in (query, matched_query) if item))
        quote = _claim_from_web_content(quote_query, fetched.text)
        content_preview = fetched.text[:1800]
        final_score = float(result.get("_final_score", result.get("_score", 0.0)))
        parts.append(
            f"[Fetched {i + 1}] {evidence_ref} relevance={final_score:.2f} "
            f"kind={fetched.content_kind} {title}\n{content_preview}\n{url}\n"
        )
        citations.append({
            "ref": evidence_ref,
            "title": title,
            "url": url,
            "domain": _domain(url),
            "relevance_score": final_score,
            "score_breakdown": result.get("_breakdown", {}),
            "matched_query": result.get("matched_query", ""),
            "matched_queries": result.get("matched_queries", []),
            "paper_id": paper_id,
            "evidence_class": evidence_class,
            "provider_source": result.get("provider_source", provider),
            "quote": quote,
            "content_type": fetched.content_type,
            "content_kind": fetched.content_kind,
            "content_hash": fetched.content_hash,
            "published_at": fetched.published_at,
            "retrieved_at": fetched.retrieved_at,
            "prompt_injection_detected": fetched.prompt_injection_detected,
        })
        claim_text = quote
        if claim_text:
            limitation = (
                "academic abstract only; inspect full paper for claims beyond the abstract"
                if fetched.status == "abstract_only"
                else "fetched web body; verify date and scope for high-stakes claims"
            )
            if fetched.prompt_injection_detected:
                limitation += "; instruction-like page content was removed"
            claims.append(AgentClaim(
                claim=claim_text,
                source="Web",
                verbatim_quote=claim_text[:800],
                paper_id=paper_id,
                paper_section="abstract" if fetched.status == "abstract_only" else "body",
                relevance=final_score,
                research_type="academic" if evidence_class in {"peer_reviewed", "preprint"} else "web",
                metric=_extract_metric(claim_text),
                evidence_refs=[evidence_ref],
                confidence=confidence,
                limitations=[limitation],
                evidence_class=evidence_class,
                document_title=title,
                url=url,
                published_at=fetched.published_at or str(result.get("published_at") or ""),
                retrieved_at=fetched.retrieved_at,
                content_hash=fetched.content_hash,
                content_kind=fetched.content_kind,
                directness=0.65 if fetched.status == "abstract_only" else 0.9,
                authority=_authority_for_web_class(evidence_class),
                relationship="supports",
            ))

    scoped_claims, scoped_parts = _run_corpus_claims(query, scoped_matches)
    seen_scoped = {
        (claim.content_hash, claim.paper_section, re.sub(r"\s+", " ", claim.claim).casefold())
        for claim in claims
    }
    for claim in scoped_claims:
        key = (claim.content_hash, claim.paper_section, re.sub(r"\s+", " ", claim.claim).casefold())
        if key not in seen_scoped:
            seen_scoped.add(key)
            claims.append(claim)
    parts.extend(scoped_parts)

    return SourceResult(
        source="Web",
        status=status,
        detail=f"{preferred_provider} search discovery + body fetch",
        content="\n".join(parts),
        evidence_class=_strongest_evidence_class(claims),
        claims=claims,
        metadata={
            "query_plan": plan.to_dict(),
            "retry_queries": retry_queries,
            "result_count": len(results),
            "kept_count": len(reported_results),
            "discovered_count": len(kept_results),
            "selected_for_fetch": _filtered_results_metadata(selected_results),
            "fetched_count": len(usable_results),
            "filtered_count": len(filtered_results),
            "filtered_domains": sorted({_domain(item.get("url", "")) for item in filtered_results if item.get("url")}),
            "top_relevance_score": top_score,
            "citations": citations,
            "fetch_trace": fetch_trace,
            "filtered_results": _filtered_results_metadata(filtered_results),
            "provider_trace": provider_trace,
            "provider_chain": used_providers,
            "search_errors": search_errors,
            "run_scoped_corpus": corpus_provider.diagnostics() if corpus_provider else {},
            "run_scoped_ingest": corpus_ingest_trace,
            "run_scoped_match_count": len(scoped_matches),
        },
    ).to_tool_text()


def _run_corpus_source_result(
    query: str,
    matches: list[dict],
    provider: RunScopedCorpusProvider | None,
    *,
    error: str = "",
) -> SourceResult:
    claims, parts = _run_corpus_claims(query, matches)
    return SourceResult(
        source="Web",
        status="success" if claims else "no_evidence",
        detail="run-scoped full-text corpus",
        error=error,
        content="\n".join(parts) or "No relevant run-scoped full-text chunks were found.",
        claims=claims,
        evidence_class=_strongest_evidence_class(claims),
        metadata={
            "run_scoped_only": True,
            "run_scoped_match_count": len(matches),
            "run_scoped_corpus": provider.diagnostics() if provider else {},
        },
    )


def _run_corpus_claims(query: str, matches: list[dict]) -> tuple[list[AgentClaim], list[str]]:
    claims: list[AgentClaim] = []
    parts: list[str] = []
    for index, item in enumerate(matches):
        text = str(item.get("text") or "").strip()
        quote = _claim_from_web_content(query, text)
        if not quote:
            continue
        url = str(item.get("url") or "").strip()
        chunk_id = str(item.get("id") or f"chunk-{index + 1}")
        evidence_ref = f"[Web:{url}#run-scoped-{item.get('chunk_index', index)}]" if url else f"[Web:run-scoped:{chunk_id}]"
        score = float(item.get("score") or 0.0)
        claims.append(AgentClaim(
            claim=quote,
            source="Web",
            verbatim_quote=quote[:800],
            paper_id=str(item.get("paper_id") or ""),
            paper_section=f"run_scoped_chunk_{item.get('chunk_index', index)}",
            relevance=score,
            research_type="academic" if item.get("evidence_class") in {"peer_reviewed", "preprint"} else "web",
            metric=_extract_metric(quote),
            evidence_refs=[evidence_ref],
            confidence=0.76,
            limitations=["ephemeral full-text chunk retained only for this run"],
            evidence_class=str(item.get("evidence_class") or "authoritative_document"),
            document_title=str(item.get("title") or ""),
            url=url,
            published_at=str(item.get("published_at") or ""),
            retrieved_at=str(item.get("retrieved_at") or ""),
            content_hash=str(item.get("content_hash") or ""),
            content_kind="run_scoped_fulltext",
            directness=0.9,
            authority=_authority_for_web_class(str(item.get("evidence_class") or "")),
            relationship="supports",
        ))
        parts.append(
            f"[RunScoped {index + 1}] {evidence_ref} relevance={score:.2f} "
            f"{item.get('title') or ''}\n{text[:1800]}\n{url}\n"
        )
    return claims, parts


def _claim_from_web_result(title: str, snippet: str, max_length: int = 220) -> str:
    for raw in re.split(r"(?<=[。.!?])\s*", snippet.strip()):
        cleaned = re.sub(r"\s+", " ", raw).strip()
        if len(cleaned) >= 20:
            return cleaned[:max_length]
    return ""


def _official_seed_results(query: str) -> list[dict]:
    """Resolve a few canonical primary documents before provider ranking."""

    lowered = str(query or "").casefold()
    results: list[dict] = []

    def add(*, title: str, snippet: str, url: str, matched_query: str) -> None:
        results.append({
            "title": title,
            "snippet": snippet,
            "url": url,
            "matched_query": matched_query,
            "matched_queries": [matched_query],
            "provider_source": "official_seed",
            "evidence_class": "authoritative_document",
        })

    identifiers = set(standard_identifiers(query))
    if identifiers.intersection({"FIPS 203", "FIPS 204", "FIPS 205"}):
        add(
            title="NIST Approves Three FIPS for Post-Quantum Cryptography",
            snippet="NIST approved FIPS 203, FIPS 204, and FIPS 205 on August 13, 2024.",
            url="https://csrc.nist.gov/News/2024/postquantum-cryptography-fips-approved",
            matched_query="site:csrc.nist.gov FIPS 203 FIPS 204 FIPS 205 approved",
        )
    if "FIPS 206" in identifiers or any(marker in lowered for marker in ("fips 206", "fn-dsa", "falcon")):
        add(
            title="FIPS 206 Status Update",
            snippet="NIST expects to release an Initial Public Draft soon; the draft is awaiting approval.",
            url=(
                "https://csrc.nist.gov/csrc/media/presentations/2025/"
                "fips-206-fn-dsa-(falcon)/images-media/fips_206-perlner_2.1.pdf"
            ),
            matched_query="site:csrc.nist.gov FIPS 206 FN-DSA Initial Public Draft soon",
        )
    if "hqc" in lowered and any(marker in lowered for marker in ("nist", "pqc", "后量子")):
        add(
            title="HQC Announced as a 4th Round Selection",
            snippet="NIST selected HQC for standardization on March 11, 2025.",
            url="https://csrc.nist.gov/News/2025/hqc-announced-as-a-4th-round-selection",
            matched_query="site:csrc.nist.gov NIST HQC fourth round selection",
        )
    pqc_migration = any(marker in lowered for marker in ("pqc", "post-quantum", "后量子")) and any(
        marker in lowered for marker in ("migration", "迁移", "roadmap", "路线图", "nccoe")
    )
    if pqc_migration:
        add(
            title="SP 1800-38 Migration to Post-Quantum Cryptography",
            snippet="NCCoE practice guide covering cryptographic discovery, interoperability, and PQC migration.",
            url="https://csrc.nist.gov/pubs/sp/1800/38/iprd-(1)",
            matched_query="site:nccoe.nist.gov SP 1800-38 post-quantum cryptography migration practice guide",
        )
        add(
            title="Quantum-Readiness: Migration to Post-Quantum Cryptography",
            snippet=(
                "CISA, NSA, and NIST urge organizations to create quantum-readiness roadmaps, "
                "inventory cryptography, assess risk, and engage vendors."
            ),
            url="https://www.nccoe.nist.gov/sites/default/files/2023-08/quantum-readiness-fact-sheet.pdf",
            matched_query="site:nccoe.nist.gov CISA NSA NIST quantum readiness fact sheet",
        )
    return results


def _claim_from_web_content(query: str, text: str, max_length: int = 500) -> str:
    """Select the most query-relevant factual sentence from fetched content."""

    query_terms = important_terms(query)
    query_entities = extract_entities(query)
    temporal = is_temporal_query(query)
    decision_pattern = re.compile(
        r"\b(select(?:ed|ion)?|publish(?:ed|es)?|release(?:d|s)?|announce(?:d|s)?|"
        r"decid(?:e|ed)|final(?:ized)?|draft|withdrawn|effective|deadline|urge(?:d|s)?|"
        r"encourage(?:d|s)?|recommend(?:ed|s)?|should|must|establish|conduct|engage)\b|"
        r"选定|入选|发布|最终版|草案|生效|截止|敦促|建议|应当|必须|建立|开展",
        re.IGNORECASE,
    )
    context_pattern = re.compile(
        r"\b(standardiz(?:e|ed|ation)|roadmap|migration|guidance|recommendation)\b|"
        r"标准化|路线图|迁移|指南|建议",
        re.IGNORECASE,
    )
    event_pattern = re.compile(r"\b(conference|seminar|webinar|workshop|agenda|event)\b|会议|研讨会|活动", re.IGNORECASE)
    guidance_pattern = re.compile(
        r"\b(roadmaps?|inventor(?:y|ies)|risk assessments?|vendors?|prioriti[sz](?:e|ed|ation)|"
        r"timelines?|project management|supply chain)\b|路线图|清单|风险评估|供应商|优先级|时间表|供应链",
        re.IGNORECASE,
    )
    guidance_query = bool(re.search(r"guidance|roadmap|migration|指南|指导|路线图|迁移", query, re.IGNORECASE))
    status_query = bool(re.search(
        r"status|latest|draft|final|as of|状态|最新|草案|最终|截至",
        query,
        re.IGNORECASE,
    ))
    status_detail_pattern = re.compile(
        r"\b(expect(?:ed)? to release|awaiting approval|in development|initial public draft|"
        r"will be published|not yet (?:released|published)|remains? (?:a )?draft)\b|"
        r"预计发布|等待批准|仍在制定|尚未发布|初始公开草案",
        re.IGNORECASE,
    )
    boilerplate_pattern = re.compile(
        r"TLP:CLEAR|central@|@CISA|BACKGROUND|contact us|follow us|"
        r"estimated time|software requirements|purchase options?|sales team|"
        r"call (?:us|esri)|chat online|contact form|select a different location|"
        r"skip to main content|table of contents|this video was created",
        re.IGNORECASE,
    )
    target_years = {str(year) for year in temporal_years(query)} if temporal else set()
    candidates: list[tuple[float, str]] = []
    reflowed = _reflow_web_text(str(text or ""))
    if status_query:
        status_candidates: list[tuple[float, str]] = []
        for match in status_detail_pattern.finditer(reflowed):
            start = max(0, match.start() - 220)
            for identifier in standard_identifiers(query):
                identifier_start = reflowed.casefold().rfind(
                    identifier.casefold(),
                    max(0, match.start() - 320),
                    match.start(),
                )
                if identifier_start >= 0:
                    start = identifier_start
                    break
            end = min(len(reflowed), match.end() + 180)
            excerpt = re.sub(r"\s+", " ", reflowed[start:end]).strip(" -*\t")
            if len(excerpt) < 35:
                continue
            score = (0.6 * entity_score(query_entities, excerpt)) + (0.4 * overlap_score(query_terms, excerpt))
            status_candidates.append((score, excerpt))
        if status_candidates:
            status_candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
            return status_candidates[0][1][:max_length]
    for raw in re.split(r"(?<=[。.!?])\s+|\n{2,}", reflowed):
        sentence = re.sub(r"\s+", " ", raw).strip(" -*\t")
        if len(sentence) < 35 or len(sentence) > 1000:
            continue
        lexical = overlap_score(query_terms, sentence)
        entity = entity_score(query_entities, sentence)
        specificity = 0.15 if re.search(
            r"\b\d+(?:\.\d+)?%?\b|研究|结果|表明|发现|限制|挑战|limitation|result|found|show",
            sentence,
            re.IGNORECASE,
        ) else 0.0
        status_bonus = (
            0.45
            if (status_query or guidance_query) and decision_pattern.search(sentence)
            else 0.18
            if (status_query or guidance_query) and context_pattern.search(sentence)
            else 0.0
        )
        status_detail_bonus = 0.55 if status_query and status_detail_pattern.search(sentence) else 0.0
        freshness_bonus = 0.12 if target_years and any(year in sentence for year in target_years) else 0.0
        event_penalty = 0.28 if event_pattern.search(sentence) else 0.0
        guidance_hits = len({match.casefold() for match in guidance_pattern.findall(sentence)})
        guidance_bonus = min(0.4, 0.1 * guidance_hits) if guidance_query else 0.0
        boilerplate_penalty = 0.9 if boilerplate_pattern.search(sentence) else 0.0
        length_penalty = 0.18 if len(sentence) > max_length else 0.0
        score = (
            (0.55 * lexical)
            + (0.25 * entity)
            + specificity
            + status_bonus
            + status_detail_bonus
            + freshness_bonus
            + guidance_bonus
            - event_penalty
            - boilerplate_penalty
            - length_penalty
        )
        candidates.append((score, sentence))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return candidates[0][1][:max_length]


def _reflow_web_text(text: str) -> str:
    """Repair PDF line wrapping without collapsing page/paragraph breaks."""

    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[A-Za-z])", "", value)
    value = re.sub(r"(?<!\n)\n(?!\n)", " ", value)
    return re.sub(r"[ \t]+", " ", value)


def _authority_for_web_class(evidence_class: str) -> float:
    return {
        "peer_reviewed": 0.9,
        "authoritative_document": 0.88,
        "preprint": 0.72,
        "community_content": 0.45,
    }.get(evidence_class, 0.45)


def _search_academic_sources(query: str | list[str], max_results: int) -> list[dict]:
    """Query public scholarly APIs concurrently and tolerate per-provider failure."""

    queries = [query] if isinstance(query, str) else query
    queries = list(dict.fromkeys(str(item).strip() for item in queries if str(item).strip()))[:2]
    providers = (
        _search_semantic_scholar,
        _search_openalex,
        _search_crossref,
        _search_arxiv,
    )
    batches: list[list[dict]] = []
    with ThreadPoolExecutor(max_workers=len(providers) * len(queries)) as executor:
        futures = [
            (academic_query, executor.submit(provider, academic_query, max_results))
            for academic_query in queries
            for provider in providers
        ]
        for academic_query, future in futures:
            try:
                batches.append([
                    {
                        **item,
                        "matched_query": academic_query,
                        "matched_queries": [academic_query],
                    }
                    for item in future.result()
                ])
            except Exception:
                continue
    results: list[dict] = []
    for index in range(max_results):
        results.extend(batch[index] for batch in batches if index < len(batch))
    return _merge_web_results([], results)[: max_results * 3]


def _academic_query_variants(queries: list[str]) -> list[str]:
    """Normalize bilingual plans into concise scholarly API queries."""

    variants = []
    combined = " ".join(str(query).casefold() for query in queries)
    geospatial = any(
        term in combined
        for term in ("geoprocessing", "geospatial", "spatial data", "geoai", "gis", "地理处理", "地理空间", "地理数据")
    )
    data_intent = any(
        term in combined
        for term in ("采集", "清洗", "配准", "融合", "质量控制", "preprocessing", "registration", "fusion")
    )
    method_intent = any(
        term in combined
        for term in ("规则", "机器学习", "深度学习", "llm", "agent", "算法", "algorithm")
    )
    system_intent = any(term in combined for term in (
        "工作流", "编排", "云原生", "serverless", "orchestration", "cloud-native", "arcgis", "modelbuilder", "fme", "airflow",
    ))
    evaluation_intent = any(
        term in combined
        for term in ("基准", "评估", "局限", "边界", "benchmark", "evaluation", "limitation")
    )
    generic_method_intent = any(term in combined for term in ("方法", "method")) and not (
        data_intent or system_intent or evaluation_intent
    )
    if geospatial and data_intent:
        variants.append(
            "geospatial data acquisition preprocessing registration fusion quality control automation"
        )
    if geospatial and (method_intent or generic_method_intent):
        method_terms = ["geospatial", "automation"]
        if any(term in combined for term in ("规则", "rule engine", "rule-based")):
            method_terms.extend(["rule", "based"])
        if any(term in combined for term in ("机器学习", "machine learning")):
            method_terms.extend(["machine", "learning"])
        if any(term in combined for term in ("深度学习", "deep learning")):
            method_terms.extend(["deep", "learning"])
        if any(term in combined for term in ("llm", "large language model", "agent", "智能体")):
            method_terms.extend(["llm", "agents"])
        if len(method_terms) == 2:
            method_terms.extend(["algorithms", "methods"])
        variants.append(" ".join(dict.fromkeys([*method_terms, "review"])))
    if geospatial and system_intent:
        variants.append(
            "geoprocessing workflow automation cloud platform orchestration"
        )
    if geospatial and evaluation_intent:
        variants.append(
            "geoprocessing automation benchmark evaluation limitations review"
        )
    if geospatial and not variants:
        variants.append("geoprocessing automation methods review")
    for query in queries:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9.+-]*", str(query))
        normalized = " ".join(dict.fromkeys(token.casefold() for token in tokens))
        value = normalized or str(query).strip()
        if value and value not in variants:
            variants.append(value)
    return variants


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Conflux/0.1 research-assistant"})
    with urllib.request.urlopen(request, timeout=_bounded_http_timeout(8)) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Conflux/0.1 research-assistant"})
    with urllib.request.urlopen(request, timeout=_bounded_http_timeout(8)) as response:
        return response.read().decode("utf-8")


def _search_semantic_scholar(query: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,url,externalIds,year,venue,publicationTypes",
    })
    payload = _fetch_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{params}")
    results = []
    for item in payload.get("data") or []:
        external = item.get("externalIds") or {}
        paper_id = external.get("DOI") or external.get("ArXiv") or item.get("paperId") or ""
        publication_types = item.get("publicationTypes") or []
        evidence_class = (
            "preprint" if external.get("ArXiv") and not publication_types
            else "peer_reviewed" if publication_types else "community_content"
        )
        results.append({
            "title": item.get("title") or "",
            "snippet": item.get("abstract") or "",
            "url": item.get("url") or "",
            "paper_id": paper_id,
            "evidence_class": evidence_class,
            "provider_source": "semantic_scholar",
            "published_at": str(item.get("year") or ""),
        })
    return results


def _search_serpapi_sync(query: str, max_results: int = 5) -> list[dict]:
    return asyncio.run(_search_serpapi(query, max_results=max_results))


def _provider(name: str) -> SearchProvider | None:
    normalized = {
        "ddgs": "duckduckgo",
        "duckduckgo": "duckduckgo",
        "bing_api": "bing",
        "google_cse": "google",
        "serp": "serpapi",
    }.get(name.casefold(), name.casefold())
    providers = {
        "duckduckgo": SearchProvider("duckduckgo", _search_duckduckgo),
        "bing": SearchProvider("bing", _search_bing, ("BING_SEARCH_API_KEY",)),
        "google": SearchProvider("google", _search_google, ("GOOGLE_API_KEY",)),
        "serpapi": SearchProvider("serpapi", _search_serpapi_sync, ("SERPAPI_API_KEY",)),
    }
    # Google requires both credentials; handle the second one here so an
    # incomplete configuration is represented as an explicit skipped provider.
    if normalized == "google":
        cx = (os.environ.get("GOOGLE_CSE_ID", "") or os.environ.get("GOOGLE_CX", "")).strip()
        if not cx:
            return SearchProvider("google", _search_google, ("GOOGLE_API_KEY", "GOOGLE_CSE_ID"))
    return providers.get(normalized)


def _provider_chain(preferred: str) -> list[str]:
    configured = get("web_search", "fallback_providers", default=None)
    if isinstance(configured, str):
        configured = [item.strip() for item in configured.split(",") if item.strip()]
    if not isinstance(configured, (list, tuple)) or not configured:
        configured = ["duckduckgo", "bing", "google", "serpapi"]
    values = [preferred, *[str(item) for item in configured]]
    result: list[str] = []
    for value in values:
        normalized = {
            "ddgs": "duckduckgo",
            "bing_api": "bing",
            "google_cse": "google",
            "serp": "serpapi",
        }.get(value.casefold(), value.casefold())
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _valid_provider_results(results: list[dict]) -> list[dict]:
    return [
        item for item in results
        if item.get("status") != "failed" and str(item.get("url") or "").strip()
    ]


def fetch_url_content(
    url: str,
    *,
    title_hint: str = "",
    timeout_seconds: float | None = None,
) -> FetchedContent:
    """Fetch one HTML/PDF URL and normalize it into citeable body text."""

    retrieved_at = datetime.now(timezone.utc).isoformat()
    timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else get("web_search", "fetch_timeout_seconds", default=12)
    )
    max_bytes = int(get("web_search", "max_fetch_bytes", default=5 * 1024 * 1024))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Conflux/0.1 research-assistant",
            "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = str(response.geturl() or url)
            content_type = str(response.headers.get_content_type() or "application/octet-stream").casefold()
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(max_bytes + 1)
    except Exception as exc:
        return FetchedContent(
            url=url,
            final_url=url,
            title=title_hint,
            text="",
            content_type="",
            content_kind="unfetched",
            status="failed",
            retrieved_at=retrieved_at,
            error=f"{type(exc).__name__}: {exc}",
        )

    if len(raw) > max_bytes:
        return FetchedContent(
            url=url,
            final_url=final_url,
            title=title_hint,
            text="",
            content_type=content_type,
            content_kind="unfetched",
            status="too_large",
            retrieved_at=retrieved_at,
            error=f"Response exceeded {max_bytes} bytes.",
        )

    if content_type == "application/pdf" or final_url.casefold().endswith(".pdf"):
        title, text, published_at, error = _extract_pdf_body(raw, title_hint=title_hint)
        content_kind = "pdf"
    elif content_type in {"text/html", "application/xhtml+xml"} or b"<html" in raw[:1000].casefold():
        title, text, published_at, error = _extract_html_body(raw, charset=charset, title_hint=title_hint)
        content_kind = "html"
    elif content_type.startswith("text/"):
        title = title_hint
        text = raw.decode(charset, errors="replace")
        published_at = ""
        error = ""
        content_kind = "text"
    else:
        return FetchedContent(
            url=url,
            final_url=final_url,
            title=title_hint,
            text="",
            content_type=content_type,
            content_kind="unsupported",
            status="unsupported",
            retrieved_at=retrieved_at,
            error=f"Unsupported content type: {content_type}",
        )

    sanitized, injection_detected = _sanitize_untrusted_content(text)
    if len(sanitized) < 80:
        return FetchedContent(
            url=url,
            final_url=final_url,
            title=title or title_hint,
            text=sanitized,
            content_type=content_type,
            content_kind=content_kind,
            status="too_short",
            published_at=published_at,
            retrieved_at=retrieved_at,
            content_hash=sha256(sanitized.encode("utf-8")).hexdigest() if sanitized else "",
            error=error or "Extracted body text is too short for evidence.",
            prompt_injection_detected=injection_detected,
        )
    return FetchedContent(
        url=url,
        final_url=final_url,
        title=title or title_hint,
        text=sanitized,
        content_type=content_type,
        content_kind=content_kind,
        status="success",
        published_at=published_at,
        retrieved_at=retrieved_at,
        content_hash=sha256(sanitized.encode("utf-8")).hexdigest(),
        error=error,
        prompt_injection_detected=injection_detected,
    )


def _extract_html_body(raw: bytes, *, charset: str, title_hint: str) -> tuple[str, str, str, str]:
    try:
        markup = raw.decode(charset, errors="replace")
    except LookupError:
        markup = raw.decode("utf-8", errors="replace")
    parser = _HTMLContentExtractor()
    try:
        parser.feed(markup)
        parser.close()
    except Exception as exc:
        return title_hint, "", "", f"HTMLParserError: {exc}"
    return parser.title or title_hint, "\n\n".join(parser.blocks), parser.published_at, ""


def _extract_pdf_body(raw: bytes, *, title_hint: str) -> tuple[str, str, str, str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        max_pages = int(get("web_search", "max_pdf_pages", default=30))
        pages = [page.extract_text() or "" for page in reader.pages[:max_pages]]
        text = "\n\n".join(part.strip() for part in pages if part.strip())
        metadata = reader.metadata or {}
        title = str(getattr(metadata, "title", "") or metadata.get("/Title", "") or title_hint)
        published_at = str(metadata.get("/CreationDate", "") or "")
        return title, text, published_at, "" if text else "PDF has no extractable text."
    except Exception as exc:
        return title_hint, "", "", f"PDFExtractionError: {exc}"


def _sanitize_untrusted_content(text: str) -> tuple[str, bool]:
    """Remove instruction-like lines while preserving factual body content."""

    patterns = (
        r"ignore (?:all |any )?(?:previous|prior) instructions",
        r"system prompt",
        r"developer message",
        r"reveal (?:your |the )?(?:prompt|secret|api key)",
        r"忽略(?:以上|之前|所有)指令",
        r"系统提示词",
        r"开发者消息",
        r"泄露.*(?:密钥|提示词)",
    )
    kept = []
    detected = False
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
            detected = True
            continue
        kept.append(line)
    return "\n".join(kept), detected


def _fetch_web_results(
    results: list[dict],
    *,
    corpus_provider: RunScopedCorpusProvider | None = None,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
) -> list[dict]:
    """Fetch discovered results concurrently and retain explicit failures."""

    limit = max(1, int(get("web_search", "max_fetched_results", default=5)))
    selected = results[:limit]
    if not bool(get("web_search", "fetch_content", default=True)):
        return [{**item, "fetch": FetchedContent(
            url=str(item.get("url") or ""),
            final_url=str(item.get("url") or ""),
            title=str(item.get("title") or ""),
            text="",
            content_type="",
            content_kind="unfetched",
            status="disabled",
            error="Web body fetching is disabled.",
        )} for item in selected]

    with ThreadPoolExecutor(max_workers=min(4, len(selected) or 1)) as executor:
        def fetch(item: dict) -> FetchedContent:
            timeout = _deadline_call_timeout(
                deadline_at,
                commit_reserve_seconds,
                float(get("web_search", "fetch_timeout_seconds", default=12)),
            )
            if timeout <= 0:
                return FetchedContent(
                    url=str(item.get("url") or ""),
                    final_url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    text="",
                    content_type="",
                    content_kind="unfetched",
                    status="failed",
                    error="Run deadline reserve reached before fetch.",
                )
            invoke = lambda: fetch_url_content(
                str(item.get("url") or ""),
                title_hint=str(item.get("title") or ""),
                timeout_seconds=timeout,
            )
            if corpus_provider is None:
                return invoke()
            return corpus_provider.fetch_once(_result_identity(item), invoke)

        futures = [executor.submit(fetch, item) for item in selected]
        fetched = []
        for item, future in zip(selected, futures):
            try:
                content = future.result()
            except Exception as exc:
                content = FetchedContent(
                    url=str(item.get("url") or ""),
                    final_url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    text="",
                    content_type="",
                    content_kind="unfetched",
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
            if not content.usable and _is_academic_abstract(item):
                abstract = str(item.get("snippet") or "").strip()
                sanitized, injection_detected = _sanitize_untrusted_content(abstract)
                content = FetchedContent(
                    url=str(item.get("url") or ""),
                    final_url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    text=sanitized,
                    content_type="application/vnd.conflux.academic-abstract",
                    content_kind="abstract",
                    status="abstract_only",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    content_hash=sha256(sanitized.encode("utf-8")).hexdigest(),
                    error=content.error,
                    prompt_injection_detected=injection_detected,
                )
            fetched.append({**item, "fetch": content})
    return fetched


def _fetch_with_backfill(
    query: str,
    results: list[dict],
    *,
    target_limit: int,
    attempt_limit: int,
    corpus_provider: RunScopedCorpusProvider | None = None,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
) -> tuple[list[dict], list[dict]]:
    """Fetch a bounded candidate set and replace inaccessible pages."""

    target_limit = max(1, int(target_limit))
    attempt_limit = max(target_limit, int(attempt_limit))
    selected = _select_results_for_fetch(query, results, min(target_limit, attempt_limit))
    def fetch_batch(items: list[dict]) -> list[dict]:
        kwargs = {}
        if corpus_provider is not None:
            kwargs["corpus_provider"] = corpus_provider
        if deadline_at:
            kwargs.update({
                "deadline_at": deadline_at,
                "commit_reserve_seconds": commit_reserve_seconds,
            })
        return _fetch_web_results(items, **kwargs)

    fetched = fetch_batch(selected)
    usable_count = sum(1 for item in fetched if item["fetch"].usable)
    attempted_urls = {_result_identity(item) for item in selected}

    while usable_count < target_limit and len(selected) < attempt_limit:
        if not _deadline_has_time(deadline_at, commit_reserve_seconds):
            break
        remaining = [
            item
            for item in results
            if _result_identity(item) not in attempted_urls
        ]
        if not remaining:
            break
        budget = min(attempt_limit - len(selected), target_limit - usable_count)
        extra = _select_results_for_fetch(query, remaining, budget)
        if not extra:
            break
        extra_fetched = fetch_batch(extra)
        selected.extend(extra)
        fetched.extend(extra_fetched)
        attempted_urls.update(_result_identity(item) for item in extra)
        new_usable = sum(1 for item in extra_fetched if item["fetch"].usable)
        usable_count += new_usable
        if not extra_fetched:
            break
    return fetched, selected


def _select_results_for_fetch(query: str, results: list[dict], limit: int) -> list[dict]:
    """Preserve official query dimensions before filling the fetch budget."""

    limit = max(1, int(limit))
    if not is_temporal_query(query):
        return results[:limit]

    ordered = sorted(results, key=lambda item: _fetch_candidate_rank(query, item), reverse=True)
    selected: list[dict] = []
    seen_urls: set[str] = set()

    def add(item: dict) -> None:
        url = str(item.get("url") or "").strip()
        identity = _result_identity(item)
        if url and identity not in seen_urls and len(selected) < limit:
            selected.append(item)
            seen_urls.add(identity)

    # Canonical primary documents are resolved independently of the search
    # provider. Preserve them before generic targeted queries consume the
    # bounded fetch budget.
    for item in ordered:
        if str(item.get("provider_source") or "").casefold() == "official_seed":
            add(item)

    targeted_queries: list[str] = []
    for item in ordered:
        for matched in item.get("matched_queries") or [item.get("matched_query", "")]:
            matched = str(matched or "")
            if matched.casefold().startswith("site:") and matched not in targeted_queries:
                targeted_queries.append(matched)
    for matched in targeted_queries:
        candidate = next(
            (
                item
                for item in ordered
                if matched in (item.get("matched_queries") or [item.get("matched_query", "")])
            ),
            None,
        )
        if candidate is not None:
            add(candidate)
    for item in ordered:
        add(item)
    return selected


def _rerank_fetched_results(query: str, results: list[dict]) -> list[dict]:
    reranked = []
    temporal = is_temporal_query(query)
    for item in results:
        fetched: FetchedContent = item["fetch"]
        date_text = " ".join([
            fetched.published_at,
            str(item.get("published_at") or ""),
            fetched.title,
            str(item.get("title") or ""),
            str(item.get("snippet") or ""),
            str(item.get("url") or ""),
        ])
        freshness = _temporal_relevance(query, date_text)
        base = float(item.get("_score", 0.0))
        official = 1.0 if _domain_quality(_domain(fetched.final_url or fetched.url)) >= 0.8 else 0.0
        final_score = (0.75 * base) + (0.2 * freshness) + (0.05 * official) if temporal else base
        breakdown = dict(item.get("_breakdown") or {})
        breakdown["fetched_freshness"] = round(freshness, 3)
        reranked.append({
            **item,
            "_freshness": round(freshness, 3),
            "_final_score": round(max(0.0, min(1.0, final_score)), 3),
            "_breakdown": breakdown,
        })
    return sorted(reranked, key=lambda item: item.get("_final_score", 0.0), reverse=True)


def _reported_web_results(results: list[dict], status: str) -> list[dict]:
    if status != "success":
        return results
    return [
        item for item in results
        if float(item.get("_final_score", item.get("_score", 0.0))) >= 0.55
    ]


def _fetch_candidate_rank(query: str, item: dict) -> float:
    domain = _domain(str(item.get("url") or ""))
    official = 1.0 if _domain_quality(domain) >= 0.8 else 0.0
    targeted = 1.0 if any(
        str(value or "").casefold().startswith("site:")
        for value in (item.get("matched_queries") or [item.get("matched_query", "")])
    ) else 0.0
    discovery_text = _result_discovery_text(item)
    focused_specificity = 0.0
    has_focused_standard = False
    focused_standard_match = 0.0
    for matched in item.get("matched_queries") or [item.get("matched_query", "")]:
        matched = str(matched or "")
        if not matched:
            continue
        lexical = overlap_score(important_terms(matched), discovery_text)
        entity = entity_score(extract_entities(matched), discovery_text)
        focused_specificity = max(focused_specificity, (0.55 * entity) + (0.45 * lexical))
        standards = standard_identifiers(matched)
        if standards:
            has_focused_standard = True
            if any(item.casefold() in discovery_text.casefold() for item in standards):
                focused_standard_match = 1.0
    return (
        float(item.get("_score", 0.0))
        + (0.18 * _temporal_relevance(query, _result_discovery_text(item)))
        + (0.08 * official)
        + (0.04 * targeted)
        + (0.18 * focused_specificity)
        + (0.12 * focused_standard_match)
        - (0.06 if has_focused_standard and not focused_standard_match else 0.0)
    )


def _is_academic_abstract(result: dict) -> bool:
    provider = str(result.get("provider_source") or "").casefold()
    evidence_class = str(result.get("evidence_class") or "").casefold()
    return (
        provider in {"semantic_scholar", "openalex", "crossref", "arxiv"}
        and evidence_class in {"peer_reviewed", "preprint"}
        and len(str(result.get("snippet") or "").strip()) >= 120
    )


def _search_cascade(
    subqueries: list[str],
    max_results: int,
    *,
    preferred: str,
    excluded: set[str] | None = None,
    required_results: int = 2,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
) -> tuple[list[dict], list[dict], list[str]]:
    """Run configured providers in order and retain an auditable trace."""

    results: list[dict] = []
    trace: list[dict] = []
    used: list[str] = []
    excluded = excluded or set()
    for name in _provider_chain(preferred):
        if not _deadline_has_time(deadline_at, commit_reserve_seconds):
            trace.append({"provider": name, "status": "skipped_deadline", "result_count": 0})
            break
        if name in excluded:
            continue
        provider = _provider(name)
        if provider is None:
            trace.append({"provider": name, "status": "unsupported", "result_count": 0})
            continue
        if not provider.available():
            trace.append({
                "provider": name,
                "status": "skipped_missing_credentials",
                "result_count": 0,
                "required_env": list(provider.credential_env),
            })
            continue
        try:
            batch = _search_with_plan(
                name,
                subqueries,
                max_results,
                deadline_at=deadline_at,
                commit_reserve_seconds=commit_reserve_seconds,
            )
            used.append(name)
            results = _merge_web_results(results, batch)
            valid_count = len(_valid_provider_results(batch))
            trace.append({
                "provider": name,
                "status": "success" if valid_count else "no_results",
                "result_count": valid_count,
            })
            if len(_valid_provider_results(results)) >= required_results:
                break
        except Exception as exc:
            used.append(name)
            trace.append({
                "provider": name,
                "status": "failed",
                "result_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return results, trace, used


def _search_openalex(query: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({"search": query, "per-page": max_results})
    payload = _fetch_json(f"https://api.openalex.org/works?{params}")
    results = []
    for item in payload.get("results") or []:
        doi = item.get("doi") or ""
        results.append({
            "title": item.get("display_name") or "",
            "snippet": _openalex_abstract(item.get("abstract_inverted_index") or {}),
            "url": doi or item.get("id") or "",
            "paper_id": doi or item.get("id") or "",
            "evidence_class": "peer_reviewed" if item.get("type") in {"article", "review", "book-chapter"} else "community_content",
            "provider_source": "openalex",
            "published_at": str(item.get("publication_year") or ""),
        })
    return results


def _openalex_abstract(index: dict) -> str:
    positions = []
    for word, offsets in index.items():
        positions.extend((int(offset), str(word)) for offset in offsets)
    return " ".join(word for _, word in sorted(positions))


def _search_crossref(query: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "rows": max_results})
    payload = _fetch_json(f"https://api.crossref.org/works?{params}")
    results = []
    for item in ((payload.get("message") or {}).get("items") or []):
        title = (item.get("title") or [""])[0]
        abstract = re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
        doi = str(item.get("DOI") or "")
        date_parts = ((item.get("published") or item.get("issued") or {}).get("date-parts") or [[]])[0]
        results.append({
            "title": title,
            "snippet": re.sub(r"\s+", " ", abstract).strip(),
            "url": str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
            "paper_id": f"doi:{doi}" if doi else "",
            "evidence_class": "peer_reviewed" if item.get("type") in {"journal-article", "proceedings-article"} else "authoritative_document",
            "provider_source": "crossref",
            "published_at": "-".join(str(value) for value in date_parts),
        })
    return results


def _search_arxiv(query: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({"search_query": f"all:{query}", "start": 0, "max_results": max_results})
    root = ET.fromstring(_fetch_text(f"https://export.arxiv.org/api/query?{params}"))
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", namespace):
        url = str(entry.findtext("atom:id", default="", namespaces=namespace))
        paper_id = _web_paper_id(url)
        arxiv_id = paper_id.removeprefix("arxiv:")
        fetch_url = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else url
        results.append({
            "title": re.sub(r"\s+", " ", entry.findtext("atom:title", default="", namespaces=namespace)).strip(),
            "snippet": re.sub(r"\s+", " ", entry.findtext("atom:summary", default="", namespaces=namespace)).strip(),
            "url": fetch_url,
            "paper_id": paper_id,
            "evidence_class": "preprint",
            "provider_source": "arxiv",
            "published_at": str(entry.findtext("atom:published", default="", namespaces=namespace)),
        })
    return results


def _search_with_plan(
    provider: str,
    subqueries: list[str],
    max_results: int,
    *,
    deadline_at: float | None = None,
    commit_reserve_seconds: float = 20.0,
) -> list[dict]:
    results: list[dict] = []
    positions: dict[str, int] = {}
    per_query = max(2, max_results)
    adapter = _provider(provider)
    if adapter is None:
        raise ValueError(f"Unsupported web search provider: {provider}")

    def run(item: tuple[int, str]) -> tuple[int, str, list[dict], Exception | None]:
        query_index, subquery = item
        if not _deadline_has_time(deadline_at, commit_reserve_seconds):
            return query_index, subquery, [], TimeoutError("run deadline reserve reached")
        token = None
        if deadline_at:
            token = _REQUEST_TIMEOUT_SECONDS.set(
                _deadline_call_timeout(deadline_at, commit_reserve_seconds, 10)
            )
        try:
            batch = adapter.search(subquery, per_query)
        except Exception as exc:
            return query_index, subquery, [], exc
        finally:
            if token is not None:
                _REQUEST_TIMEOUT_SECONDS.reset(token)
        return query_index, subquery, batch, None

    workers = max(1, min(int(get("web_search", "max_parallel_queries", default=3)), len(subqueries) or 1))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        batches = list(executor.map(run, enumerate(subqueries)))

    errors: list[Exception] = []
    for query_index, subquery, batch, error in batches:
        if error is not None:
            errors.append(error)
            continue
        for item in batch:
            url = str(item.get("url") or "").strip()
            key = _result_identity(item)
            if key in positions:
                existing = results[positions[key]]
                matched_queries = list(existing.get("matched_queries") or [existing.get("matched_query", "")])
                if subquery not in matched_queries:
                    matched_queries.append(subquery)
                existing["matched_queries"] = [value for value in matched_queries if value]
                continue
            enriched = dict(item)
            enriched["url"] = url
            enriched.setdefault("matched_query", subquery)
            enriched.setdefault("matched_queries", [subquery])
            enriched.setdefault("query_index", query_index)
            enriched.setdefault("provider_source", adapter.name)
            positions[key] = len(results)
            results.append(enriched)
    if not results and errors:
        raise errors[0]
    return results


def _deadline_call_timeout(
    deadline_at: float | None,
    commit_reserve_seconds: float,
    role_timeout: float,
) -> float:
    if not deadline_at:
        return max(0.001, float(role_timeout))
    remaining = float(deadline_at) - time.time() - max(0.0, float(commit_reserve_seconds))
    return max(0.0, min(float(role_timeout), remaining))


def _bounded_http_timeout(default: float) -> float:
    configured = _REQUEST_TIMEOUT_SECONDS.get()
    if configured is None:
        return max(0.001, float(default))
    return max(0.001, min(float(default), configured))


def _deadline_has_time(
    deadline_at: float | None,
    commit_reserve_seconds: float,
) -> bool:
    return _deadline_call_timeout(deadline_at, commit_reserve_seconds, 1.0) > 0


def _merge_web_results(existing: list[dict], additional: list[dict]) -> list[dict]:
    merged = []
    positions: dict[str, int] = {}
    for item in [*existing, *additional]:
        key = _result_identity(item)
        if key in positions:
            target = merged[positions[key]]
            matched_queries = list(target.get("matched_queries") or [target.get("matched_query", "")])
            for value in item.get("matched_queries") or [item.get("matched_query", "")]:
                if value and value not in matched_queries:
                    matched_queries.append(value)
            target["matched_queries"] = [value for value in matched_queries if value]
            continue
        positions[key] = len(merged)
        merged.append(dict(item))
    return merged


def _web_evidence_class(result: dict, url: str) -> str:
    declared = str(result.get("evidence_class") or "")
    if declared in {"peer_reviewed", "preprint", "authoritative_document", "community_content"}:
        return declared
    domain = _domain(url)
    if domain == "arxiv.org" or domain.endswith(".arxiv.org"):
        return "preprint"
    if domain in {
        "doi.org",
        "link.springer.com",
        "sciencedirect.com",
        "ieee.org",
        "acm.org",
    } or any(domain.endswith(f".{item}") for item in ("semanticscholar.org", "springer.com", "ieee.org", "acm.org")):
        return "peer_reviewed"
    if domain.endswith(".gov") or domain.endswith(".edu") or domain in {
        "nist.gov", "usgs.gov", "opengeospatial.org", "ogc.org", "crossref.org", "openalex.org",
        "semanticscholar.org",
    }:
        return "authoritative_document"
    return "community_content"


def _web_paper_id(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if parsed.netloc.lower().endswith("doi.org"):
        return f"doi:{path.lstrip('/')}"
    if parsed.netloc.lower().endswith("arxiv.org"):
        value = re.sub(r"^/(abs|pdf)/", "", path)
        value = re.sub(r"\.pdf$", "", value)
        return f"arxiv:{value}"
    return url.rstrip("/")


def _strongest_evidence_class(claims: list[AgentClaim]) -> str:
    rank = {"peer_reviewed": 5, "authoritative_document": 4, "preprint": 3, "community_content": 2, "model_inference": 1}
    if not claims:
        return "community_content"
    return max((claim.evidence_class for claim in claims), key=lambda value: rank.get(value, 0))


def _extract_metric(text: str) -> str:
    match = re.search(r"\b\d+(?:\.\d+)?\s*(?:%|m|cm|mm|km|s|ms|hours?|days?)\b", text, re.IGNORECASE)
    return match.group(0) if match else ""


def _filter_web_results(query: str, results: list[dict]) -> tuple[list[dict], list[dict]]:
    scored = []
    filtered = []
    for result in results:
        url = str(result.get("url") or "")
        title = str(result.get("title") or "")
        snippet = str(result.get("snippet") or "")
        if result.get("status") == "failed" or not url:
            filtered.append({**result, "_score": 0.0, "_filter_reason": "search_failed_or_missing_url"})
            continue
        domain = _domain(url)
        query_variants = list(dict.fromkeys(
            str(item).strip()
            for item in (
                query,
                *(result.get("matched_queries") or [result.get("matched_query", "")]),
            )
            if str(item).strip()
        ))
        text = f"{title}\n{snippet}\n{domain}\n{result.get('published_at') or ''}"
        domain_quality = _domain_quality(domain)
        entity, lexical = max(
            (
                entity_score(extract_entities(variant), text),
                overlap_score(important_terms(variant), text),
            )
            for variant in query_variants
        )
        specificity = _snippet_specificity(title, snippet)
        spam_penalty = _spam_penalty(domain, title, snippet)
        base_score = (0.35 * entity) + (0.25 * lexical) + (0.25 * domain_quality) + (0.15 * specificity) - spam_penalty
        freshness = _temporal_relevance(query, text)
        if is_temporal_query(query):
            official = 1.0 if domain_quality >= 0.8 else 0.0
            score = (0.78 * base_score) + (0.17 * freshness) + (0.05 * official)
        else:
            score = base_score
        score = round(max(0.0, min(1.0, score)), 3)
        enriched = {
            **result,
            "_score": score,
            "_breakdown": {
                "entity_match": round(entity, 3),
                "lexical_overlap": round(lexical, 3),
                "domain_authority": round(domain_quality, 3),
                "snippet_specificity": round(specificity, 3),
                "freshness": round(freshness, 3),
                "spam_penalty": round(spam_penalty, 3),
            },
        }
        topic_anchor = _topic_anchor_match(query_variants, text)
        enriched["_breakdown"]["topic_anchor"] = None if topic_anchor is None else int(topic_anchor)
        if topic_anchor is False:
            enriched["_filter_reason"] = "missing_topic_anchor"
            filtered.append(enriched)
        elif score >= 0.35:
            scored.append(enriched)
        else:
            enriched["_filter_reason"] = "low_relevance_or_low_quality"
            filtered.append(enriched)

    scored.sort(key=lambda item: item["_score"], reverse=True)
    filtered.sort(key=lambda item: item.get("_score", 0.0), reverse=True)
    return scored, filtered


def _topic_anchor_match(query_variants: list[str], text: str) -> bool | None:
    """Require an explicit domain anchor only when the query names that domain."""

    query_text = "\n".join(query_variants).casefold()
    candidate = text.casefold()
    for family in _TOPIC_ANCHOR_FAMILIES:
        query_has_family = any(_contains_topic_alias(query_text, alias) for alias in family)
        if query_has_family:
            return any(_contains_topic_alias(candidate, alias) for alias in family)
    return None


def _contains_topic_alias(text: str, alias: str) -> bool:
    if alias == "gis agent":
        return bool(re.search(r"\bgis\b", text))
    return alias in text


def _result_discovery_text(result: dict) -> str:
    return "\n".join([
        str(result.get("title") or ""),
        str(result.get("snippet") or ""),
        str(result.get("url") or ""),
        str(result.get("published_at") or ""),
    ])


def _result_identity(result: dict) -> str:
    url = str(result.get("url") or "").strip()
    if not url:
        return f"{result.get('title', '')}|{result.get('snippet', '')}"
    parsed = urllib.parse.urlsplit(url)
    tracking_keys = {
        "_hsenc", "_hsmi", "bxid", "cndid", "esrc", "fbclid", "gclid", "mbid",
        "ref", "source", "stream", "trk", "ver",
    }
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in tracking_keys
    ]
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), path, urllib.parse.urlencode(query), ""))


def _temporal_relevance(query: str, text: str) -> float:
    if not is_temporal_query(query):
        return 0.0
    target = temporal_years(query)[0]
    years = [int(value) for value in re.findall(r"\b(20\d{2})\b", str(text or ""))]
    eligible = [year for year in years if year <= target]
    if not eligible:
        return 0.15
    delta = target - max(eligible)
    return {0: 1.0, 1: 0.9, 2: 0.65, 3: 0.35}.get(delta, 0.1)


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _domain_quality(domain: str) -> float:
    if not domain:
        return 0.0
    if domain in LOW_QUALITY_DOMAINS or any(domain.endswith(f".{item}") for item in LOW_QUALITY_DOMAINS):
        return 0.0
    if domain in DOMAIN_PRIORITY:
        return DOMAIN_PRIORITY[domain]
    for suffix, quality in DOMAIN_PRIORITY.items():
        if domain.endswith(f".{suffix}"):
            return quality
    if any(token in domain for token in ("gov", "edu", "org")):
        return 0.55
    return 0.35


def _snippet_specificity(title: str, snippet: str) -> float:
    text = f"{title} {snippet}".strip()
    if not text:
        return 0.0
    score = 0.2
    if len(text) >= 80:
        score += 0.25
    if re_search(r"\b(standard|fips|arcgis|gis|geospatial|paper|doi|nist|ogc|GeoSPARQL)\b", text):
        score += 0.25
    if re_search(r"\b(20\d{2}|19\d{2})\b", text):
        score += 0.1
    if ":" in title or "-" in title:
        score += 0.1
    return min(1.0, score)


def _spam_penalty(domain: str, title: str, snippet: str) -> float:
    text = f"{domain} {title} {snippet}".lower()
    penalty = 0.0
    if domain in LOW_QUALITY_DOMAINS or any(domain.endswith(f".{item}") for item in LOW_QUALITY_DOMAINS):
        penalty += 0.55
    if any(term in text for term in ("instagram", "slideshare", "login", "sign up", "pinterest", "scribd")):
        penalty += 0.25
    if len(snippet.strip()) < 30:
        penalty += 0.15
    return penalty


def re_search(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def _filtered_results_metadata(results: list[dict]) -> list[dict]:
    payload = []
    for item in results[:10]:
        payload.append({
            "title": str(item.get("title") or "")[:120],
            "url": str(item.get("url") or ""),
            "domain": _domain(str(item.get("url") or "")),
            "score": item.get("_score", 0.0),
            "final_score": item.get("_final_score", item.get("_score", 0.0)),
            "matched_query": item.get("matched_query", ""),
            "matched_queries": item.get("matched_queries", []),
            "reason": item.get("_filter_reason", ""),
            "breakdown": item.get("_breakdown", {}),
        })
    return payload
