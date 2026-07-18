"""Web search tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

import asyncio
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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
    overlap_score,
    plan_queries,
    rewrite_queries,
)
from ..source_status import AgentClaim, SourceResult


@dataclass(frozen=True)
class SearchProvider:
    """Small adapter boundary for a web search provider."""

    name: str
    search: Callable[[str, int], list[dict]]
    credential_env: tuple[str, ...] = ()

    def available(self) -> bool:
        return not self.credential_env or all(os.environ.get(key, "").strip() for key in self.credential_env)


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
    with urllib.request.urlopen(request, timeout=10) as response:
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
    with urllib.request.urlopen(request, timeout=10) as response:
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
    async with aiohttp.ClientSession() as session:
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
    """Search the public web and return snippet-level URL evidence."""

    provider = get("web_search", "provider", default="duckduckgo")
    max_results = int(get("web_search", "max_results", default=5))
    plan = plan_queries(query, target="web")
    retry_queries: list[str] = []
    preferred_provider = str(provider)
    provider_trace: list[dict] = []
    used_providers: list[str] = []

    try:
        results, provider_trace, used_providers = _search_cascade(
            plan.subqueries,
            max_results,
            preferred=preferred_provider,
            required_results=max(1, min(2, max_results)),
        )
        if is_academic_query(query):
            academic_results = _search_academic_sources(query, max_results=max_results)
            results = _merge_web_results(academic_results, results)
    except Exception as exc:
        return SourceResult(
            source="Web",
            status="failed",
            detail=preferred_provider,
            error=f"{type(exc).__name__}: {exc}",
            content="Web search failed.",
        ).to_tool_text()

    if not results:
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
    if len(kept_results) < 2 or (kept_results and kept_results[0].get("_score", 0.0) < 0.55):
        fallback_results, fallback_trace, fallback_used = _search_cascade(
            plan.subqueries,
            max_results,
            preferred=preferred_provider,
            excluded=set(used_providers),
            required_results=max(1, min(2, max_results)),
        )
        provider_trace.extend(fallback_trace)
        used_providers.extend(item for item in fallback_used if item not in used_providers)
        if fallback_results:
            results = _merge_web_results(results, fallback_results)
            kept_results, filtered_results = _filter_web_results(query, results)
    for attempt in range(1, int(get("research", "max_rewrite_attempts", default=1)) + 1):
        top_attempt = kept_results[0].get("_score", 0.0) if kept_results else 0.0
        if len(kept_results) >= 2 and top_attempt >= 0.55:
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
            )
            provider_trace.extend(retry_trace)
            used_providers.extend(item for item in retry_used if item not in used_providers)
        except Exception:
            break
        results = _merge_web_results(results, retry_results)
        kept_results, filtered_results = _filter_web_results(query, results)
    if not kept_results:
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

    top_score = kept_results[0].get("_score", 0.0)
    status = "success" if len(kept_results) >= 2 and top_score >= 0.55 else "low_relevance"
    confidence = 0.72 if status == "success" else 0.45
    limitation = "web snippet evidence; inspect URL for high-stakes claims"
    if status == "low_relevance":
        limitation = "weak web snippet evidence; inspect source before relying on it"

    parts: list[str] = []
    claims: list[AgentClaim] = []
    citations: list[dict] = []
    for i, result in enumerate(kept_results):
        title = str(result.get("title") or "")
        snippet = str(result.get("snippet") or "")
        url = str(result.get("url") or "")
        evidence_class = _web_evidence_class(result, url)
        paper_id = str(result.get("paper_id") or _web_paper_id(url))
        evidence_ref = f"[Web:{url}]" if url else f"[Web:result-{i + 1}]"
        parts.append(f"[Result {i + 1}] relevance={result.get('_score', 0.0):.2f} {title}\n{snippet}\n{url}\n")
        citations.append({
            "ref": evidence_ref,
            "title": title,
            "url": url,
            "snippet": snippet,
            "domain": _domain(url),
            "relevance_score": result.get("_score", 0.0),
            "score_breakdown": result.get("_breakdown", {}),
            "paper_id": paper_id,
            "evidence_class": evidence_class,
            "provider_source": result.get("provider_source", provider),
        })
        claim_text = _claim_from_web_result(title, snippet)
        if claim_text:
            claims.append(AgentClaim(
                claim=claim_text,
                source="Web",
                verbatim_quote=snippet[:500],
                paper_id=paper_id,
                paper_section="abstract" if evidence_class in {"peer_reviewed", "preprint"} else "snippet",
                relevance=float(result.get("_score", 0.0)),
                research_type="academic" if evidence_class in {"peer_reviewed", "preprint"} else "web",
                metric=_extract_metric(claim_text),
                evidence_refs=[evidence_ref],
                confidence=confidence,
                limitations=[limitation],
                evidence_class=evidence_class,
            ))

    return SourceResult(
        source="Web",
        status=status,
        detail=preferred_provider,
        content="\n".join(parts),
        evidence_class=_strongest_evidence_class(claims),
        claims=claims,
        metadata={
            "query_plan": plan.to_dict(),
            "retry_queries": retry_queries,
            "result_count": len(results),
            "kept_count": len(kept_results),
            "filtered_count": len(filtered_results),
            "filtered_domains": sorted({_domain(item.get("url", "")) for item in filtered_results if item.get("url")}),
            "top_relevance_score": top_score,
            "citations": citations,
            "filtered_results": _filtered_results_metadata(filtered_results),
            "provider_trace": provider_trace,
            "provider_chain": used_providers,
        },
    ).to_tool_text()


def _claim_from_web_result(title: str, snippet: str, max_length: int = 220) -> str:
    for raw in re.split(r"(?<=[。.!?])\s*", snippet.strip()):
        cleaned = re.sub(r"\s+", " ", raw).strip()
        if len(cleaned) >= 20:
            return cleaned[:max_length]
    return ""


def _search_academic_sources(query: str, max_results: int) -> list[dict]:
    """Query public scholarly APIs concurrently and tolerate per-provider failure."""

    providers = (
        _search_semantic_scholar,
        _search_openalex,
        _search_crossref,
        _search_arxiv,
    )
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = [executor.submit(provider, query, max_results) for provider in providers]
        for future in futures:
            try:
                results.extend(future.result())
            except Exception:
                continue
    return _merge_web_results([], results)[: max_results * 3]


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Conflux/0.1 research-assistant"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Conflux/0.1 research-assistant"})
    with urllib.request.urlopen(request, timeout=8) as response:
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


def _search_cascade(
    subqueries: list[str],
    max_results: int,
    *,
    preferred: str,
    excluded: set[str] | None = None,
    required_results: int = 2,
) -> tuple[list[dict], list[dict], list[str]]:
    """Run configured providers in order and retain an auditable trace."""

    results: list[dict] = []
    trace: list[dict] = []
    used: list[str] = []
    excluded = excluded or set()
    for name in _provider_chain(preferred):
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
            batch = _search_with_plan(name, subqueries, max_results)
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
        results.append({
            "title": title,
            "snippet": re.sub(r"\s+", " ", abstract).strip(),
            "url": str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
            "paper_id": f"doi:{doi}" if doi else "",
            "evidence_class": "peer_reviewed" if item.get("type") in {"journal-article", "proceedings-article"} else "authoritative_document",
            "provider_source": "crossref",
        })
    return results


def _search_arxiv(query: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({"search_query": f"all:{query}", "start": 0, "max_results": max_results})
    root = ET.fromstring(_fetch_text(f"https://export.arxiv.org/api/query?{params}"))
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", namespace):
        url = str(entry.findtext("atom:id", default="", namespaces=namespace))
        results.append({
            "title": re.sub(r"\s+", " ", entry.findtext("atom:title", default="", namespaces=namespace)).strip(),
            "snippet": re.sub(r"\s+", " ", entry.findtext("atom:summary", default="", namespaces=namespace)).strip(),
            "url": url,
            "paper_id": _web_paper_id(url),
            "evidence_class": "preprint",
            "provider_source": "arxiv",
        })
    return results


def _search_with_plan(provider: str, subqueries: list[str], max_results: int) -> list[dict]:
    results: list[dict] = []
    seen = set()
    per_query = max(2, max_results)
    for subquery in subqueries:
        adapter = _provider(provider)
        if adapter is None:
            raise ValueError(f"Unsupported web search provider: {provider}")
        batch = adapter.search(subquery, per_query)
        for item in batch:
            url = str(item.get("url") or "")
            key = url or f"{item.get('title', '')}|{item.get('snippet', '')}"
            if key in seen:
                continue
            seen.add(key)
            enriched = dict(item)
            enriched.setdefault("matched_query", subquery)
            enriched.setdefault("provider_source", adapter.name)
            results.append(enriched)
        if len(results) >= max_results * 2:
            break
    return results


def _merge_web_results(existing: list[dict], additional: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for item in [*existing, *additional]:
        key = str(item.get("url") or f"{item.get('title', '')}|{item.get('snippet', '')}")
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
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
    query_terms = important_terms(query)
    query_entities = extract_entities(query)
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
        text = f"{title}\n{snippet}\n{domain}"
        domain_quality = _domain_quality(domain)
        lexical = overlap_score(query_terms, text)
        entity = entity_score(query_entities, text)
        specificity = _snippet_specificity(title, snippet)
        spam_penalty = _spam_penalty(domain, title, snippet)
        score = (0.35 * entity) + (0.25 * lexical) + (0.25 * domain_quality) + (0.15 * specificity) - spam_penalty
        score = round(max(0.0, min(1.0, score)), 3)
        enriched = {
            **result,
            "_score": score,
            "_breakdown": {
                "entity_match": round(entity, 3),
                "lexical_overlap": round(lexical, 3),
                "domain_authority": round(domain_quality, 3),
                "snippet_specificity": round(specificity, 3),
                "spam_penalty": round(spam_penalty, 3),
            },
        }
        if score >= 0.35:
            scored.append(enriched)
        else:
            enriched["_filter_reason"] = "low_relevance_or_low_quality"
            filtered.append(enriched)

    scored.sort(key=lambda item: item["_score"], reverse=True)
    filtered.sort(key=lambda item: item.get("_score", 0.0), reverse=True)
    return scored, filtered


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
            "reason": item.get("_filter_reason", ""),
            "breakdown": item.get("_breakdown", {}),
        })
    return payload
