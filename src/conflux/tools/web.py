"""Web 搜索工具 — 封装为 LangChain Tool，供 Agent 调用"""

from langchain_core.tools import tool

from ..config import get
from ..source_status import SourceResult


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo 搜索（免费，无需 API key）"""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
                for r in results
            ]
    except ImportError:
        return [{"title": "错误", "snippet": "ddgs 未安装", "url": "", "status": "failed"}]
    except Exception as e:
        # DDG 后端（Bing）经常超时或被反爬阻断，捕获所有异常
        return [{"title": "搜索暂时不可用", "snippet": f"DuckDuckGo 搜索失败 ({type(e).__name__})。", "url": "", "status": "failed"}]


async def _search_serpapi(query: str, max_results: int = 5) -> list[dict]:
    """SerpAPI 搜索（需要 API key，质量更高）"""
    import os
    api_key = os.environ.get("SERPAPI_API_KEY", "")
    if not api_key:
        return [{"title": "错误", "snippet": "SERPAPI_API_KEY 未设置", "url": "", "status": "failed"}]

    import aiohttp
    params = {"q": query, "api_key": api_key, "num": max_results, "engine": "google"}
    async with aiohttp.ClientSession() as session:
        async with session.get("https://serpapi.com/search", params=params) as resp:
            data = await resp.json()
    results = []
    for r in data.get("organic_results", [])[:max_results]:
        results.append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "url": r.get("link", ""),
        })
    return results


@tool
def search_web(query: str) -> str:
    """在互联网上搜索与 query 相关的最新信息。
    返回网页标题、摘要和 URL。
    适用于：需要查找实时信息、新闻、最新研究等本地知识库未覆盖的内容。
    """
    provider = get("web_search", "provider", default="duckduckgo")
    max_results = get("web_search", "max_results", default=5)

    try:
        if provider == "serpapi":
            import asyncio
            results = asyncio.run(_search_serpapi(query, max_results=max_results))
        else:
            results = _search_duckduckgo(query, max_results=max_results)
    except Exception as exc:
        return SourceResult(
            source="Web",
            status="failed",
            detail=str(provider),
            error=f"{type(exc).__name__}: {exc}",
            content="互联网检索失败。",
        ).to_tool_text()

    if not results:
        return SourceResult(
            source="Web",
            status="failed",
            detail=str(provider),
            error="未找到相关网络搜索结果。",
            content="未找到相关网络搜索结果。",
        ).to_tool_text()

    failed_results = [r for r in results if r.get("status") == "failed" or not r.get("url")]
    if len(failed_results) == len(results):
        error = "; ".join(r.get("snippet", r.get("title", "")) for r in failed_results)
        return SourceResult(
            source="Web",
            status="failed",
            detail=str(provider),
            error=error or "互联网检索不可用。",
            content=error or "互联网检索不可用。",
        ).to_tool_text()

    parts = []
    for i, r in enumerate(results):
        parts.append(
            f"[结果 {i+1}] {r['title']}\n{r['snippet']}\n{r['url']}\n"
        )
    content = "\n".join(parts)
    return SourceResult(
        source="Web",
        status="success",
        detail=str(provider),
        content=content,
        metadata={"result_count": len(results)},
    ).to_tool_text()
