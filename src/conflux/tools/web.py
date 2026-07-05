"""Web search tool wrapped as a LangChain tool for source agents."""

from __future__ import annotations

import asyncio
import os
import re
from urllib.parse import urlparse

from langchain_core.tools import tool

from ..config import get
from ..query_planner import (
    DOMAIN_PRIORITY,
    LOW_QUALITY_DOMAINS,
    entity_score,
    extract_entities,
    important_terms,
    overlap_score,
    plan_queries,
)
from ..source_status import AgentClaim, SourceResult


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

    try:
        results = _search_with_plan(str(provider), plan.subqueries, max_results)
    except Exception as exc:
        return SourceResult(
            source="Web",
            status="failed",
            detail=str(provider),
            error=f"{type(exc).__name__}: {exc}",
            content="Web search failed.",
        ).to_tool_text()

    if not results:
        return SourceResult(
            source="Web",
            status="no_evidence",
            detail=str(provider),
            error="No web search results were found.",
            content="No web search results were found.",
            metadata={"query_plan": plan.to_dict(), "result_count": 0},
        ).to_tool_text()

    failed_results = [item for item in results if item.get("status") == "failed" or not item.get("url")]
    if len(failed_results) == len(results):
        error = "; ".join(str(item.get("snippet") or item.get("title") or "") for item in failed_results)
        return SourceResult(
            source="Web",
            status="failed",
            detail=str(provider),
            error=error or "Web search is unavailable.",
            content=error or "Web search is unavailable.",
            metadata={"query_plan": plan.to_dict(), "result_count": len(results)},
        ).to_tool_text()

    kept_results, filtered_results = _filter_web_results(query, results)
    if not kept_results:
        return SourceResult(
            source="Web",
            status="no_evidence",
            detail=str(provider),
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
        })
        claim_text = _claim_from_web_result(title, snippet)
        if claim_text:
            claims.append(AgentClaim(
                claim=claim_text,
                source="Web",
                evidence_refs=[evidence_ref],
                confidence=confidence,
                limitations=[limitation],
            ))

    return SourceResult(
        source="Web",
        status=status,
        detail=str(provider),
        content="\n".join(parts),
        claims=claims,
        metadata={
            "query_plan": plan.to_dict(),
            "result_count": len(results),
            "kept_count": len(kept_results),
            "filtered_count": len(filtered_results),
            "filtered_domains": sorted({_domain(item.get("url", "")) for item in filtered_results if item.get("url")}),
            "top_relevance_score": top_score,
            "citations": citations,
            "filtered_results": _filtered_results_metadata(filtered_results),
        },
    ).to_tool_text()


def _claim_from_web_result(title: str, snippet: str, max_length: int = 220) -> str:
    text = f"{title}: {snippet}".strip(": ")
    return text[:max_length]


def _search_with_plan(provider: str, subqueries: list[str], max_results: int) -> list[dict]:
    results: list[dict] = []
    seen = set()
    per_query = max(2, max_results)
    for subquery in subqueries:
        if provider == "serpapi":
            batch = asyncio.run(_search_serpapi(subquery, max_results=per_query))
        else:
            batch = _search_duckduckgo(subquery, max_results=per_query)
        for item in batch:
            url = str(item.get("url") or "")
            key = url or f"{item.get('title', '')}|{item.get('snippet', '')}"
            if key in seen:
                continue
            seen.add(key)
            enriched = dict(item)
            enriched.setdefault("matched_query", subquery)
            results.append(enriched)
        if len(results) >= max_results * 2:
            break
    return results


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
