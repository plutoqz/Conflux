"""Local HTTP workbench for inspecting and running Conflux workflows."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any

import yaml

from conflux import config
from conflux.knowledge.paper_indexer import promote_inbox
from conflux.knowledge.stats import gather_knowledge_stats
from conflux.paper_ingestion.filters import paper_matches_negative_filter
from conflux.paper_ingestion.inbox_report import write_inbox_artifacts
from conflux.paper_ingestion.pipeline import build_inbox
from conflux.paper_ingestion.scorer import reading_level_for_score
from conflux.research_profile import ResearchProfile, load_profile
from conflux.workbench.config_store import (
    WORKBENCH_ENV,
    _reload_env,
    build_sanitized_config,
    save_workbench_env,
)
from conflux.workbench.jobs import get_job_manager, _EXECUTION_LOCK
from conflux.workbench.sessions import build_session_index, get_session_detail


PROJECT_ROOT = config.PROJECT_ROOT
DEFAULT_PROFILE = "profiles/example_gis_agent.yaml"
DEFAULT_FIXTURE = "tests/fixtures/papers/arxiv_sample.json"
DEFAULT_INBOX_DIR = "reports/workbench/papers"
DEFAULT_PROMOTE_DIR = "data/documents/papers"
WORKBENCH_ENV = WORKBENCH_ENV  # re-export from config_store (already imported above)

# Content-Security-Policy for the workbench SPA
CSP_HEADER = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "  # lucide injects inline SVGs
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "frame-src 'self'; "
    "connect-src 'self'; "
    "font-src 'self'; "
)

_reload_env()

# Security: access token for non-loopback binds (empty = loopback-only)
# Must be read AFTER _reload_env so .env.workbench values are visible.
_ACCESS_TOKEN = os.environ.get("CONFLUX_ACCESS_TOKEN", "").strip()

# Cookie name used for browser-based auth when bound to a non-loopback address.
_AUTH_COOKIE = "conflux_token"
_AUTH_COOKIE_MAX_AGE = 12 * 60 * 60


def _auth_cookie_value() -> str:
    """Derive a browser session value without exposing the access token."""
    return hashlib.sha256(f"conflux-workbench:{_ACCESS_TOKEN}".encode("utf-8")).hexdigest()


def build_status() -> dict[str, Any]:
    """Return sanitized local workbench status."""

    raw = config.load()
    reasoning = dict(raw.get("models", {}).get("reasoning") or {})
    cheap = dict(raw.get("models", {}).get("cheap") or {})
    embedding = dict(raw.get("embedding") or {})

    return {
        "project_root": str(PROJECT_ROOT),
        "profiles": [_enrich_profile(p) for p in _list_files(PROJECT_ROOT / "profiles", {".yaml", ".yml"})],
        "reports": _list_files(PROJECT_ROOT / "reports", {".md", ".html", ".json"}),
        "paper_outputs": _list_files(PROJECT_ROOT / "data" / "documents" / "papers", {".md", ".json"}),
        "defaults": {
            "profile": DEFAULT_PROFILE,
            "fixture": DEFAULT_FIXTURE,
            "inbox_dir": DEFAULT_INBOX_DIR,
            "promote_dir": DEFAULT_PROMOTE_DIR,
            "reasoning": _sanitize_model_config(reasoning, "OPENAI_API_KEY"),
            "cheap": _sanitize_model_config(cheap, "OPENAI_API_KEY"),
            "embedding": _sanitize_model_config(embedding, "OPENAI_API_KEY"),
        },
        "workbench_env": str(WORKBENCH_ENV) if WORKBENCH_ENV.exists() else "",
        "saved_depth": os.environ.get("CONFLUX_DEPTH", "standard"),
        "credentials": {
            "openai_api_key": _has_env("OPENAI_API_KEY"),
            "reasoning_api_key": _has_env("CONFLUX_MODELS__REASONING__API_KEY"),
            "cheap_api_key": _has_env("CONFLUX_MODELS__CHEAP__API_KEY"),
            "embedding_api_key": _has_env("CONFLUX_EMBEDDING__API_KEY"),
            "serpapi_api_key": _has_env("SERPAPI_API_KEY"),
        },
    }


def _split_lines(value: Any) -> list[str]:
    """Split multi-line or comma-delimited text into a cleaned keyword list."""

    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value)
    items = [item.strip() for line in text.splitlines() for item in line.split(",")]
    return [item for item in items if item]


def _profile_from_form(payload: dict[str, Any]) -> ResearchProfile:
    """Build a temporary ResearchProfile from inline form fields."""

    keywords = _split_lines(payload.get("keywords") or "")
    description = str(payload.get("description") or "").strip()
    fields = _split_lines(payload.get("fields") or "")
    negative_keywords = _split_lines(payload.get("negative_keywords") or "")
    name = str(payload.get("profile_name") or "临时画像").strip() or "临时画像"
    pf_id = "wb-" + name.lower().replace(" ", "-")
    questions = [description] if description else []
    if not fields:
        fields = ["cs.AI"]
    return ResearchProfile(
        id=pf_id,
        name=name,
        fields=fields,
        research_questions=questions,
        keywords=keywords,
        negative_keywords=negative_keywords,
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    """Extract a JSON object from an OpenAI-compatible model response."""

    text = str(content or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:].lstrip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("模型没有返回可识别的画像 JSON。")
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("模型返回的画像格式无效，请重试。") from exc
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的画像不是 JSON 对象。")
    return parsed


def _clean_profile_items(value: Any, *, limit: int, item_limit: int = 120) -> list[str]:
    """Normalize and cap model-provided profile list values."""

    items = _split_lines(value)
    clean: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = " ".join(item.split())[:item_limit].strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            clean.append(normalized)
        if len(clean) >= limit:
            break
    return clean


def optimize_inline_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a reviewable research-profile suggestion without persisting it."""

    keywords = _clean_profile_items(payload.get("keywords"), limit=20)
    fields = _clean_profile_items(payload.get("fields"), limit=8)
    negative_keywords = _clean_profile_items(payload.get("negative_keywords"), limit=16)
    description = str(payload.get("description") or "").strip()[:2400]
    if not keywords and not description:
        return {"ok": False, "error": "请至少填写关键词或研究描述，再进行 AI 优化。"}

    prompt = """你是一位研究生论文检索策略专家。请把用户草拟的研究画像优化为高质量、可审查的论文检索画像。

目标：提高 arXiv 和 Semantic Scholar 的检索精度与召回平衡，避免宽泛关键词独占结果。
要求：
1. fields 保留或补充 1-5 个合适的 arXiv 分类代码（如 cs.AI、cs.CL），不确定时不要臆造。
2. keywords 给出 8-16 个英文检索短语，兼顾研究对象、方法和应用场景；避免只保留 knowledge graph、AI 等过宽词。
3. description 改写为一个边界清楚的中文研究问题，说明研究对象、核心方法、应用场景和关注的证据。
4. negative_keywords 给出 4-12 个英文排除词，用于过滤同名概念和明显无关领域；不要排除可能相关的交叉学科。
5. optimization_notes 用 2-4 条中文短句解释主要改动，便于用户审查。
6. 不要改变用户研究主题，不要添加用户未表达的具体实验结论。

只返回 JSON 对象，不要 Markdown。结构必须为：
{"fields": ["..."], "keywords": ["..."], "description": "...", "negative_keywords": ["..."], "optimization_notes": ["..."]}

用户草稿：
""" + json.dumps({
        "fields": fields,
        "keywords": keywords,
        "description": description,
        "negative_keywords": negative_keywords,
    }, ensure_ascii=False)

    model = str(payload.get("model") or _default_model_name("cheap") or _default_model_name("reasoning")).strip()
    base_url = str(payload.get("base_url") or _default_base_url("cheap") or _default_base_url("reasoning")).strip()
    api_key = str(payload.get("api_key") or _default_api_key("cheap") or _default_api_key("reasoning")).strip()
    result = run_model_probe({
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "prompt": prompt,
        "temperature": 0.2,
        "max_tokens": 1600,
        "timeout": 90,
    })
    if not result.get("ok"):
        error = str(result.get("error") or "画像优化请求失败。")
        if "API key" in error:
            error = "画像优化需要可用的模型 API Key，请先在“模型与环境”中完成配置。"
        return {"ok": False, "error": error}

    try:
        suggestion = _parse_json_object(str(result.get("content") or ""))
        optimized = {
            "fields": _clean_profile_items(suggestion.get("fields"), limit=5),
            "keywords": _clean_profile_items(suggestion.get("keywords"), limit=16),
            "description": " ".join(str(suggestion.get("description") or "").split())[:1200],
            "negative_keywords": _clean_profile_items(suggestion.get("negative_keywords"), limit=12),
        }
        notes = _clean_profile_items(suggestion.get("optimization_notes"), limit=4, item_limit=180)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    if not optimized["keywords"] or not optimized["description"]:
        return {"ok": False, "error": "模型返回的建议缺少关键词或研究问题，请重试。"}
    if not optimized["fields"]:
        optimized["fields"] = fields or ["cs.AI"]

    return {
        "ok": True,
        "profile": optimized,
        "notes": notes,
        "model": result.get("model") or model,
    }


def _llm_rerank_papers(
    papers: list,
    profile,
    *,
    base_url: str = "",
    api_key: str = "",
    model: str = "",
) -> list[tuple]:
    """Batch-evaluate paper relevance using an LLM. Returns [(paper, llm_score, reason), ...]."""

    if not papers or not api_key or not base_url:
        return [(p, None, "") for p in papers]

    # Build prompt
    lines = [
        "你是一位研究论文评审员。根据以下研究画像，评估每篇论文的相关性（0-100 分）。",
        "评分标尺：85-100 为研究对象、方法和场景都直接相关，值得精读；70-84 为较强相关；45-69 为部分相关；0-44 为弱相关或无关。",
        "不要因为只命中一个宽泛词就给高分。",
        "",
        "研究画像：",
        f"  领域：{', '.join(profile.fields) if profile.fields else '未指定'}",
        f"  关键词：{', '.join(profile.keywords) if profile.keywords else '未指定'}",
        f"  排除方向：{', '.join(profile.negative_keywords) if profile.negative_keywords else '未指定'}",
    ]
    if profile.research_questions:
        questions = "；".join(question[:300] for question in profile.research_questions[:3])
        lines.append(f"  研究方向：{questions}")
    lines.append("")
    lines.append("待评估论文：")
    for i, paper in enumerate(papers):
        title = (paper.title or "")[:200]
        abstract = (paper.abstract or "")[:500]
        lines.append(f"[{i+1}] 标题：{title}")
        lines.append(f"    摘要：{abstract}")
        lines.append("")
    lines.append("请以 JSON 数组格式返回评估结果，每个元素包含 id（论文编号）、score（0-100 整数）、reason（一句话中文理由）。只返回 JSON，不要其他内容。")
    prompt = "\n".join(lines)

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return [(p, None, "") for p in papers]

    content = ""
    choices = payload.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""

    # Parse JSON from response
    try:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        rankings = json.loads(content)
    except Exception:
        return [(p, None, "") for p in papers]

    # Map scores back to papers
    score_map = {}
    for item in rankings:
        if isinstance(item, dict):
            pid = item.get("id")
            if pid is not None:
                try:
                    score = float(item.get("score", 50))
                    numeric_id = int(pid)
                except (TypeError, ValueError):
                    continue
                if 0 <= score <= 100:
                    score_map[numeric_id] = (score, str(item.get("reason", ""))[:180])

    result = []
    for i, paper in enumerate(papers):
        llm = score_map.get(i + 1)
        if llm:
            result.append((paper, llm[0], llm[1]))
        else:
            result.append((paper, None, ""))
    return result


def _apply_llm_scores_to_inbox(result, llm_scores: dict[str, dict[str, Any]]) -> None:
    """Blend AI judgments into final scores and persist updated inbox artifacts."""

    applied = 0
    for paper, analysis in result.analyzed:
        llm = llm_scores.get(paper.id)
        if not llm:
            continue
        try:
            llm_raw = float(llm.get("score"))
        except (TypeError, ValueError):
            continue
        if not 0 <= llm_raw <= 100:
            continue

        deterministic_score = float(analysis.relevance_score)
        llm_normalized = llm_raw / 100.0
        combined_score = 0.5 * deterministic_score + 0.5 * llm_normalized
        if deterministic_score >= 0.60 and llm_normalized >= 0.75:
            combined_score += 0.04
        combined_score = round(max(0.0, min(1.0, combined_score)), 3)
        reading_level = reading_level_for_score(combined_score)
        if reading_level == "deep" and deterministic_score < 0.25:
            reading_level = "skim"

        analysis.metadata["deterministic_score"] = deterministic_score
        analysis.metadata["llm_score"] = llm_raw
        analysis.metadata["llm_reason"] = str(llm.get("reason") or "")
        reasons = list(analysis.metadata.get("score_reasons") or [])
        reasons.append(f"AI relevance: {llm_raw:.0f}/100")
        if llm.get("reason"):
            reasons.append(f"AI assessment: {str(llm['reason'])[:180]}")
        analysis.metadata["score_reasons"] = reasons
        analysis.relevance_score = combined_score
        analysis.reading_level = reading_level  # type: ignore[assignment]
        analysis.citation_value = (
            "high" if reading_level == "deep" else "medium" if reading_level == "skim" else "low"
        )  # type: ignore[assignment]
        applied += 1

    if not applied:
        return
    result.analyzed.sort(key=lambda item: item[1].relevance_score, reverse=True)
    result.stats.update({
        "deep": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "deep"),
        "skim": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "skim"),
        "skip": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "skip"),
        "llm_scored": applied,
    })
    if result.artifacts:
        result.artifacts = write_inbox_artifacts(
            result.profile,
            result.analyzed,
            out_dir=result.artifacts.json_path.parent,
            stats=result.stats,
        )


def _search_semantic_scholar(query: str, max_results: int = 10, offset: int = 0) -> list:
    """Search Semantic Scholar API, return list of PaperRecord."""

    if not query.strip():
        return []

    params = urllib.parse.urlencode({
        "query": query,
        "limit": max_results,
        "offset": max(0, offset),
        "fields": "title,abstract,year,authors,externalIds,url,openAccessPdf,publicationDate",
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ConfluxWorkbench/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            items = json.loads(resp.read().decode("utf-8")).get("data") or []
    except Exception:
        return []

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = _s2_str(item, "paperId")
        title = _s2_str(item, "title")
        abstract = _s2_str(item, "abstract")
        ext_ids = item.get("externalIds") or {}
        arxiv_id = _s2_str(ext_ids, "ArXiv")
        pdf_url = ""
        oa = item.get("openAccessPdf") or {}
        if isinstance(oa, dict):
            pdf_url = _s2_str(oa, "url")
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        authors = []
        for author in (item.get("authors") or []):
            if isinstance(author, dict):
                authors.append(_s2_str(author, "name"))
        pub_date = _s2_str(item, "publicationDate") or str(item.get("year") or "")
        from conflux.paper_ingestion.models import PaperRecord
        results.append(PaperRecord(
            id=paper_id,
            title=title,
            abstract=abstract,
            authors=authors,
            published_at=pub_date if pub_date else None,
            source="semantic_scholar",
            url=_s2_str(item, "url"),
            pdf_url=pdf_url,
            doi=_s2_str(ext_ids, "DOI"),
            categories=[],
        ))
    return results


def _s2_str(obj: dict, key: str) -> str:
    val = obj.get(key)
    return str(val).strip() if val else ""


def _discover_unseen_papers(
    profile: ResearchProfile,
    source: str,
    max_results: int,
) -> tuple[list, int]:
    """Fetch fresh online papers, paging past results already shown before."""
    seen_map = _load_seen_papers()
    seen_identities = {_canonical_seen_key(key) for key in seen_map}
    collected = []
    collected_ids: set[str] = set()
    skipped_seen = 0

    def _collect(batch: list) -> None:
        nonlocal skipped_seen
        for paper in batch:
            identity = _paper_identity(source, paper.id)
            if identity in seen_identities:
                skipped_seen += 1
                continue
            if identity in collected_ids:
                continue
            if paper_matches_negative_filter(paper, profile):
                continue
            collected_ids.add(identity)
            collected.append(paper)

    if source == "arxiv":
        from conflux.paper_ingestion.arxiv_source import profile_arxiv_queries, search_arxiv

        queries = profile_arxiv_queries(profile)[:max_results]
        page_size = max(1, min(20, (max_results + len(queries) - 1) // max(1, len(queries))))
        active = [True] * len(queries)
        request_count = 0
        first_error = None
        for page in range(5):
            for index, query in enumerate(queries):
                if not active[index]:
                    continue
                if request_count:
                    time.sleep(3.2)
                request_count += 1
                try:
                    batch = search_arxiv(query, max_results=page_size, start=page * page_size)
                except Exception as exc:
                    first_error = first_error or exc
                    active[index] = False
                    continue
                if not batch:
                    active[index] = False
                    continue
                _collect(batch)
                if len(batch) < page_size:
                    active[index] = False
            if len(collected) >= max_results:
                return collected[:max_results], skipped_seen
            if not any(active):
                break
        if not collected and first_error is not None:
            raise first_error
    elif source == "semantic_scholar":
        from conflux.paper_ingestion.arxiv_source import profile_keyword_groups

        queries = [" ".join(group) for group in profile_keyword_groups(profile)][:max_results]
        if not queries:
            queries = ["research"]
        page_size = max(1, min(20, (max_results + len(queries) - 1) // len(queries)))
        active = [True] * len(queries)
        for page in range(5):
            for index, query in enumerate(queries):
                if not active[index]:
                    continue
                batch = _search_semantic_scholar(
                    query,
                    max_results=page_size,
                    offset=page * page_size,
                )
                if not batch:
                    active[index] = False
                    continue
                _collect(batch)
                if len(batch) < page_size:
                    active[index] = False
            if len(collected) >= max_results:
                return collected[:max_results], skipped_seen
            if not any(active):
                break
    else:
        raise ValueError(f"Unsupported online paper source: {source}")

    return collected[:max_results], skipped_seen


def _paper_identity(source: str, paper_id: str) -> str:
    normalized_id = str(paper_id or "").strip()
    if source == "arxiv":
        normalized_id = re.sub(r"v\d+$", "", normalized_id, flags=re.IGNORECASE)
    return f"{source}:{normalized_id}"


def _canonical_seen_key(key: str) -> str:
    source, separator, paper_id = str(key).partition(":")
    if not separator:
        return str(key)
    return _paper_identity(source, paper_id)


def run_paper_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the paper inbox pipeline from UI payload (file-based or inline profile)."""

    source = str(payload.get("source") or "arxiv")
    out_dir = _path_value(payload.get("out_dir"), DEFAULT_INBOX_DIR)
    max_results = max(1, min(100, int(payload.get("max_results") or 10)))
    use_llm = bool(payload.get("use_llm_scoring"))
    inline_mode = str(payload.get("profile_mode") or "file") == "inline"

    if inline_mode:
        profile = _profile_from_form(payload)
    else:
        profile_path = _path_value(payload.get("profile"), DEFAULT_PROFILE)
        profile = load_profile(profile_path)

    skipped_seen = 0
    if source in ("arxiv", "semantic_scholar"):
        try:
            papers, skipped_seen = _discover_unseen_papers(profile, source, max_results)
        except Exception as exc:
            return {"ok": False, "error": f"{source} 搜索失败：{exc}"}
        if not papers:
            return {"ok": False, "error": "当前检索范围内没有新的论文，请调整画像关键词或稍后重试。"}
        result = build_inbox(profile, papers, out_dir=out_dir)
        result.stats["previously_seen"] = skipped_seen
        _mark_papers_seen(papers, source)
    elif source == "fixture":
        from conflux.paper_ingestion.fixtures import load_paper_fixture

        fixture = _path_value(payload.get("fixture"), DEFAULT_FIXTURE)
        papers = load_paper_fixture(fixture)
        result = build_inbox(profile, papers, out_dir=out_dir)
    else:
        return {"ok": False, "error": f"不支持的论文来源：{source}"}

    # Optional LLM reranking, blended back into final reading levels and artifacts.
    llm_scores = {}
    if use_llm:
        try:
            raw_cfg = config.load()
            mcfg = (raw_cfg.get("models") or {}).get("cheap") or (raw_cfg.get("models") or {}).get("reasoning") or {}
            ak = mcfg.get("api_key") or _default_api_key("cheap") or _default_api_key("reasoning")
            bu = mcfg.get("base_url") or ""
            md = mcfg.get("model") or ""
            raw_papers = [pa[0] for pa in result.analyzed]
            ranked = _llm_rerank_papers(raw_papers, result.profile, base_url=bu, api_key=ak, model=md)
            for paper, llm_score, reason in ranked:
                if llm_score is not None:
                    llm_scores[paper.id] = {"score": llm_score, "reason": reason}
        except Exception:
            pass

    if llm_scores:
        _apply_llm_scores_to_inbox(result, llm_scores)

    artifacts = result.artifacts
    papers_out = []
    for paper, analysis in result.analyzed:
        llm = llm_scores.get(paper.id) or {}
        deterministic_score = analysis.metadata.get("deterministic_score", analysis.relevance_score)
        entry = {
            "id": paper.id,
            "title": paper.title,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "score": analysis.relevance_score,
            "keyword_score": deterministic_score,
            "reading_level": analysis.reading_level,
            "citation_value": analysis.citation_value,
            "reasons": analysis.metadata.get("score_reasons") or [],
        }
        if llm.get("score") is not None:
            entry["llm_score"] = llm["score"]
            entry["llm_reason"] = llm.get("reason", "")
        papers_out.append(entry)
    papers = papers_out
    return {
        "ok": True,
        "profile_id": result.profile.id,
        "stats": result.stats,
        "papers": papers,
        "markdown_path": _rel(artifacts.markdown_path) if artifacts else "",
        "json_path": _rel(artifacts.json_path) if artifacts else "",
    }


def save_model_config(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        count = save_workbench_env(
            base_url=str(payload.get("base_url") or "").strip(),
            api_key=str(payload.get("api_key") or "").strip(),
            model=str(payload.get("model") or "").strip(),
            embedding_base_url=str(payload.get("embedding_base_url") or "").strip(),
            embedding_api_key=str(payload.get("embedding_api_key") or "").strip(),
            embedding_model=str(payload.get("embedding_model") or "").strip(),
            depth=str(payload.get("depth") or "standard").strip(),
        )
        return {"ok": True, "saved": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _save_inline_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Save the inline profile form data as a YAML file in profiles/."""

    name = str(payload.get("profile_name") or "").strip()
    keywords = str(payload.get("keywords") or "").strip()
    description = str(payload.get("description") or "").strip()
    fields = str(payload.get("fields") or "").strip()
    negative_keywords = str(payload.get("negative_keywords") or "").strip()
    if not name:
        return {"ok": False, "error": "请输入画像名称。"}
    if not keywords and not description:
        return {"ok": False, "error": "请至少填写关键词或研究描述。"}

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    if not safe_name or not re.match(r"[A-Za-z0-9]", safe_name):
        safe_name = "profile_" + str(int(time.time()))[-8:]
    filename = f"{safe_name}.yaml"
    profiles_dir = PROJECT_ROOT / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    kw_list = _split_lines(keywords)
    f_list = _split_lines(fields) if fields else ["cs.AI"]
    q_list = [description] if description else []
    profile_payload = {
        "id": safe_name,
        "name": name,
        "fields": f_list,
        "research_questions": q_list,
        "keywords": kw_list,
        "negative_keywords": _split_lines(negative_keywords),
        "target_venues": [],
        "tracked_scholars": [],
        "project_paths": [],
        "document_paths": [],
        "paper_sources": ["arxiv"],
        "report_cadence": "weekly",
    }

    try:
        out_path = profiles_dir / filename
        yaml_text = yaml.safe_dump(profile_payload, allow_unicode=True, sort_keys=False)
        out_path.write_text(f"# Conflux Research Profile: {name}\n{yaml_text}", encoding="utf-8")
        return {"ok": True, "path": str(out_path), "name": filename}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_paper_promotion(payload: dict[str, Any]) -> dict[str, Any]:
    """Promote paper inbox JSON into knowledge documents."""

    inbox = _path_value(payload.get("inbox"), f"{DEFAULT_INBOX_DIR}/paper_inbox.json")
    out_dir = _path_value(payload.get("out_dir"), DEFAULT_PROMOTE_DIR)
    pinned = payload.get("pin") or []
    if isinstance(pinned, str):
        pinned = [item.strip() for item in pinned.splitlines() if item.strip()]
    do_index = bool(payload.get("index"))

    # Set up embedding env overrides for indexing
    emb_updates = {}
    if do_index:
        # Resolve embedding key from multiple sources
        emb_key = str(payload.get("embedding_api_key") or "").strip()
        if not emb_key:
            emb_key = os.environ.get("CONFLUX_EMBEDDING__API_KEY") or ""
        if not emb_key:
            emb_key = os.environ.get("OPENAI_API_KEY") or ""
        if not emb_key:
            emb_key = os.environ.get("CONFLUX_MODELS__REASONING__API_KEY") or ""
        if not emb_key:
            from conflux import config as cfg_mod
            raw = cfg_mod.load()
            emb_cfg = raw.get("embedding") or {}
            emb_key = emb_cfg.get("api_key") or ""
            if not emb_key:
                rsn_cfg = (raw.get("models") or {}).get("reasoning") or {}
                emb_key = rsn_cfg.get("api_key") or ""

        # Resolve embedding base URL from multiple sources
        emb_base = str(payload.get("embedding_base_url") or "").strip()
        if not emb_base:
            emb_base = os.environ.get("CONFLUX_EMBEDDING__BASE_URL") or ""
        if not emb_base:
            emb_base = os.environ.get("CONFLUX_MODELS__REASONING__BASE_URL") or ""
        if not emb_base:
            from conflux import config as cfg_mod2
            raw2 = cfg_mod2.load()
            emb_cfg2 = raw2.get("embedding") or {}
            emb_base = emb_cfg2.get("base_url") or ""
            if not emb_base:
                rsn_cfg2 = (raw2.get("models") or {}).get("reasoning") or {}
                emb_base = rsn_cfg2.get("base_url") or ""

        if not emb_key:
            return {"ok": False, "error": "索引到 Chroma 需要 Embedding API Key，但未在任何配置源中找到。请在模型配置页填写 API Key 并点「保存配置」。"}

        emb_updates["CONFLUX_EMBEDDING__API_KEY"] = emb_key
        emb_updates["OPENAI_API_KEY"] = emb_key
        if emb_base:
            emb_updates["CONFLUX_EMBEDDING__BASE_URL"] = emb_base

        emb_model = str(payload.get("embedding_model") or "").strip()
        if emb_model:
            emb_updates["CONFLUX_EMBEDDING__MODEL"] = emb_model

    with _temporary_env(emb_updates):
        result = promote_inbox(
            inbox,
            out_dir=out_dir,
            policy_name=str(payload.get("policy") or "default"),
            allow_full_text=bool(payload.get("full_text")),
            pinned_ids=list(pinned),
            index=do_index,
            pdf_dir=_optional_path(payload.get("pdf_dir")),
            download_pdfs=bool(payload.get("download_pdfs")),
        )
    actions: dict[str, int] = {}
    for decision in result.decisions:
        actions[decision.action] = actions.get(decision.action, 0) + 1

    artifacts = result.artifacts
    return {
        "ok": True,
        "documents": len(result.documents),
        "indexed": result.indexed_count,
        "decisions": actions,
        "documents_dir": _rel(artifacts.documents_dir) if artifacts else "",
        "manifest_path": _rel(artifacts.manifest_path) if artifacts else "",
        "sources_path": _rel(artifacts.sources_path) if artifacts else "",
    }


def run_model_probe(payload: dict[str, Any]) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completion endpoint."""

    model = str(payload.get("model") or _default_model_name("reasoning")).strip()
    base_url = str(payload.get("base_url") or _default_base_url("reasoning")).strip()
    api_key = str(payload.get("api_key") or _default_api_key("reasoning")).strip()
    prompt = str(payload.get("prompt") or "Reply with a short readiness check.").strip()
    temperature = float(payload.get("temperature") or 0.2)
    max_tokens = max(1, min(4096, int(payload.get("max_tokens") or 256)))

    if not model:
        return {"ok": False, "error": "Model name is required."}
    if not base_url:
        return {"ok": False, "error": "Base URL is required."}
    if not api_key:
        return {"ok": False, "error": "API key is required or must be present in local environment."}

    endpoint = _chat_endpoint(base_url)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=int(payload.get("timeout") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        return {"ok": False, "status": exc.code, "error": detail}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    choices = response_payload.get("choices") or []
    content = ""
    if choices:
        message = choices[0].get("message") or {}
        content = str(
            message.get("content")
            or message.get("reasoning_content")
            or choices[0].get("text")
            or ""
        )
    return {
        "ok": True,
        "model": response_payload.get("model") or model,
        "endpoint": endpoint,
        "elapsed_ms": elapsed_ms,
        "content": content,
        "usage": response_payload.get("usage") or {},
    }


def run_query(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a real Conflux query with temporary model overrides."""

    query = str(payload.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required."}

    updates = _model_env_updates(payload)
    output_dir = _path_value(payload.get("output_dir"), "reports/workbench/query")
    mode = str(payload.get("mode") or "phase2")
    from conflux.trace import new_run_id
    run_id = new_run_id()
    stream = io.StringIO()
    started = time.perf_counter()
    with _EXECUTION_LOCK, _temporary_env(updates), contextlib.redirect_stdout(stream):
        try:
            from conflux.__main__ import query_command

            state = query_command(
                query,
                mode=mode,
                output_dir=output_dir,
                stream_events=False,
                trace_dir=output_dir,
                run_id=run_id,
            )
        except SystemExit as exc:
            return {"ok": False, "run_id": run_id, "exit_code": exc.code, "stdout": stream.getvalue()}
        except Exception as exc:
            return {"ok": False, "run_id": run_id, "error": str(exc), "stdout": stream.getvalue()}

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return {
        "ok": True,
        "run_id": run_id,
        "elapsed_ms": elapsed_ms,
        "stdout": stream.getvalue()[-6000:],
        "final_answer": str(state.get("final_answer") or "")[:4000],
    }


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ConfluxWorkbench/0.1"

    # -- static assets (no auth needed so the SPA can load in a browser) --
    _STATIC_PATHS = {"/", "/app.css", "/app.js", "/lucide.min.js"}

    def _auth_required(self) -> bool:
        return self.client_address[0] not in ("127.0.0.1", "::1", "localhost") and bool(_ACCESS_TOKEN)

    def _authorize(self) -> bool:
        """Check the access token when the server is bound to a non-loopback address.

        Loopback requests (127.0.0.1, ::1, localhost) and empty-token configs
        are always allowed.  Non-loopback requests require a Bearer token or
        the ``conflux_token`` cookie.
        """
        if not self._auth_required():
            return True

        # Bearer header
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and hmac.compare_digest(auth[7:], _ACCESS_TOKEN):
            return True

        # HttpOnly cookie (set via /api/login)
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            session = cookies.get(_AUTH_COOKIE)
            if session and hmac.compare_digest(session.value, _auth_cookie_value()):
                return True
        except CookieError:
            pass

        return False

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        # Static assets are public so the SPA can load in a browser
        if parsed.path in self._STATIC_PATHS:
            if parsed.path == "/":
                self._send_file("src/conflux/workbench/static/index.html")
            elif parsed.path == "/app.css":
                self._send_file("src/conflux/workbench/static/app.css")
            elif parsed.path == "/app.js":
                self._send_file("src/conflux/workbench/static/app.js")
            elif parsed.path == "/lucide.min.js":
                self._send_file("src/conflux/workbench/static/lucide.min.js")
            return
        if parsed.path == "/api/auth/status":
            self._send_json({
                "ok": True,
                "required": self._auth_required(),
                "authenticated": self._authorize(),
            }, headers={"Cache-Control": "no-store"})
            return
        if not self._authorize():
            self._send_json({"ok": False, "error": "authentication required"}, status=401)
            return
        if parsed.path == "/api/status":
            self._send_json(build_status())
            return
        if parsed.path == "/api/knowledge/stats":
            self._send_json(gather_knowledge_stats(PROJECT_ROOT))
            return
        if parsed.path == "/api/config":
            self._send_json(build_sanitized_config())
            return
        if parsed.path == "/api/file":
            params = urllib.parse.parse_qs(parsed.query)
            self._send_file(params.get("path", [""])[0])
            return
        if parsed.path == "/api/sessions":
            self._send_json(build_session_index())
            return
        if parsed.path.startswith("/api/sessions/"):
            run_id = parsed.path[len("/api/sessions/"):]
            detail = get_session_detail(run_id)
            if detail is None:
                self.send_error(404)
                return
            self._send_json(detail)
            return
        # Async job routes
        if parsed.path == "/api/query/jobs":
            mgr = get_job_manager()
            self._send_json(mgr.list())
            return
        if parsed.path.startswith("/api/query/jobs/") and parsed.path.endswith("/events"):
            # SSE stream: /api/query/jobs/{run_id}/events
            run_id = parsed.path[len("/api/query/jobs/"):-len("/events")]
            self._send_sse(run_id)
            return
        if parsed.path.startswith("/api/query/jobs/"):
            # Status: /api/query/jobs/{run_id}
            run_id = parsed.path[len("/api/query/jobs/"):]
            mgr = get_job_manager()
            job = mgr.get(run_id)
            if job is None:
                self.send_error(404)
                return
            self._send_json(job)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/login":
            try:
                payload = self._read_json()
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                self._send_json({"ok": False, "error": "invalid login payload"}, status=400)
                return
            token = str(payload.get("token") or "")
            if self._auth_required() and not hmac.compare_digest(token, _ACCESS_TOKEN):
                self._send_json({"ok": False, "error": "访问令牌不正确"}, status=401)
                return
            self._send_json(
                {"ok": True, "authenticated": True},
                headers={
                    "Cache-Control": "no-store",
                    "Set-Cookie": self._auth_cookie_header(),
                },
            )
            return
        if not self._authorize():
            self._send_json({"ok": False, "error": "authentication required"}, status=401)
            return
        try:
            payload = self._read_json()
            if parsed.path == "/api/logout":
                self._send_json(
                    {"ok": True, "authenticated": False},
                    headers={
                        "Cache-Control": "no-store",
                        "Set-Cookie": self._auth_cookie_header(clear=True),
                    },
                )
                return
            if parsed.path == "/api/papers/inbox":
                self._send_json(run_paper_inbox(payload))
                return
            if parsed.path == "/api/papers/promote":
                self._send_json(run_paper_promotion(payload))
                return
            if parsed.path == "/api/model/test":
                self._send_json(run_model_probe(payload))
                return
            if parsed.path == "/api/model/save":
                self._send_json(save_model_config(payload))
                return
            if parsed.path == "/api/profile/save":
                self._send_json(_save_inline_profile(payload))
                return
            if parsed.path == "/api/profile/optimize":
                self._send_json(optimize_inline_profile(payload))
                return
            if parsed.path == "/api/query/run":
                self._send_json(run_query(payload))
                return
            # Async job submit
            if parsed.path == "/api/query/jobs":
                query = str(payload.get("query") or "").strip()
                if not query:
                    self._send_json({"ok": False, "error": "query required"}, status=400)
                    return
                mgr = get_job_manager()
                try:
                    result = mgr.submit(query, payload)
                except RuntimeError as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=503)
                    return
                self._send_json(result, status=202)
                return
            # Async job cancel
            if parsed.path.startswith("/api/query/jobs/") and parsed.path.endswith("/cancel"):
                run_id = parsed.path[len("/api/query/jobs/"):-len("/cancel")]
                mgr = get_job_manager()
                job = mgr.get(run_id)
                if job is None:
                    self._send_json({"ok": False, "error": "任务不存在"}, status=404)
                elif job["status"] not in ("pending", "running") or not mgr.cancel(run_id):
                    current = mgr.get(run_id) or job
                    self._send_json({
                        "ok": False,
                        "run_id": run_id,
                        "status": current["status"],
                        "error": f"任务已处于终态：{current['status']}",
                    }, status=409)
                else:
                    self._send_json({
                        "ok": True,
                        "run_id": run_id,
                        "cancel_requested": True,
                        "status": job["status"],
                    }, status=202)
                return
            self.send_error(404)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[workbench] {self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth_cookie_header(self, *, clear: bool = False) -> str:
        value = "" if clear else _auth_cookie_value()
        max_age = 0 if clear else _AUTH_COOKIE_MAX_AGE
        parts = [
            f"{_AUTH_COOKIE}={value}",
            "Path=/",
            f"Max-Age={max_age}",
            "HttpOnly",
            "SameSite=Strict",
        ]
        if self.headers.get("X-Forwarded-Proto", "").lower() == "https":
            parts.append("Secure")
        return "; ".join(parts)

    def _send_text(self, text: str, content_type: str) -> None:
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, requested_path: str) -> None:
        path = _safe_read_path(requested_path)
        if path is None or not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "text/plain"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_sse(self, run_id: str) -> None:
        """Stream SSE events from a job's append-only event log.

        Supports Last-Event-ID for reconnection.
        """
        mgr = get_job_manager()
        log = mgr.event_log(run_id)
        if log is None:
            self.send_error(404)
            return
        # Parse Last-Event-ID for reconnection cursor
        last_id = self.headers.get("Last-Event-ID", "")
        cursor = int(last_id) if last_id.isdigit() else 0

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self.end_headers()
        try:
            while True:
                batch, next_cursor, closed = log.read_from(cursor, timeout=25.0)
                start_cursor = cursor
                for offset, event in enumerate(batch):
                    if event is None:
                        self.wfile.write(b"event: done\ndata: {}\n\n")
                        self.wfile.flush()
                        return
                    event_id = start_cursor + offset + 1
                    data = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"id: {event_id}\ndata: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                cursor = next_cursor
                if closed and not batch:
                    self.wfile.write(b"event: done\ndata: {}\n\n")
                    self.wfile.flush()
                    return
                if not batch:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Conflux local research workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-file", help="Optional file for workbench stdout/stderr")
    parser.add_argument("--daemon", action="store_true", help="Start the workbench in a detached background process")
    parser.add_argument("--pid-file", default="reports/workbench-server.pid", help="PID file used with --daemon")
    args = parser.parse_args(argv)

    # Guard: refuse non-loopback binds without an access token (before daemon fork)
    if args.host not in ("127.0.0.1", "localhost", "::1") and not _ACCESS_TOKEN:
        print("Error: binding to non-loopback address requires CONFLUX_ACCESS_TOKEN.", file=sys.stderr)
        print("Set the environment variable and restart, or bind to 127.0.0.1.", file=sys.stderr)
        sys.exit(77)

    if args.daemon:
        port = _available_port(args.host, args.port)
        log_file = args.log_file or str(PROJECT_ROOT / "reports" / "workbench-server.log")
        pid_file = Path(args.pid_file)
        if not pid_file.is_absolute():
            pid_file = PROJECT_ROOT / pid_file
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        child_args = [
            sys.executable,
            "-m",
            "conflux.workbench",
            "--host",
            args.host,
            "--port",
            str(port),
            "--log-file",
            log_file,
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            child_args,
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        print(f"Conflux workbench started: http://{args.host}:{port}")
        print(f"PID file: {pid_file}")
        print(f"Log file: {log_file}")
        return

    log_handle = None
    if args.log_file:
        log_path = Path(args.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        sys.stdout = log_handle
        sys.stderr = log_handle

    port = _available_port(args.host, args.port)
    server = ThreadingHTTPServer((args.host, port), WorkbenchHandler)
    print(f"Conflux workbench: http://{args.host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Conflux workbench.", flush=True)
    finally:
        server.server_close()
        if log_handle:
            log_handle.close()


def _available_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No available port near {preferred}.")


def _list_files(root: Path, suffixes: set[str]) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in suffixes:
            try:
                if any(part.startswith(".") for part in path.relative_to(root).parts):
                    continue
            except ValueError:
                continue
            files.append({
                "path": _rel(path),
                "name": path.name,
                "size": path.stat().st_size,
                "modified": int(path.stat().st_mtime),
            })
    return files[-80:]


SEEN_PAPERS_PATH = PROJECT_ROOT / "reports" / "workbench" / ".seen_papers.json"
_SEEN_PAPERS_LOCK = threading.Lock()


def _load_seen_papers() -> dict:
    if SEEN_PAPERS_PATH.exists():
        try:
            return json.loads(SEEN_PAPERS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    # One-time migration for workbenches created before seen-paper tracking.
    seen: dict[str, dict[str, str]] = {}
    reports_root = PROJECT_ROOT / "reports"
    for inbox_path in reports_root.rglob("paper_inbox.json") if reports_root.exists() else []:
        try:
            payload = json.loads(inbox_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        recorded_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(inbox_path.stat().st_mtime))
        for item in payload.get("papers") or []:
            paper = item.get("paper") if isinstance(item, dict) else None
            if not isinstance(paper, dict):
                continue
            paper_id = str(paper.get("id") or "").strip()
            source = str(paper.get("source") or "").strip()
            if not paper_id or source not in ("arxiv", "semantic_scholar"):
                continue
            seen[f"{source}:{paper_id}"] = {
                "status": "inboxed",
                "at": recorded_at,
                "title": str(paper.get("title") or "")[:120],
            }
    return seen


def _mark_papers_seen(papers: list, source: str) -> None:
    with _SEEN_PAPERS_LOCK:
        seen = _load_seen_papers()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for p in papers:
            key = _paper_identity(source, p.id)
            if key not in seen:
                seen[key] = {"status": "inboxed", "at": now, "title": (p.title or "")[:120]}
        try:
            SEEN_PAPERS_PATH.parent.mkdir(parents=True, exist_ok=True)
            temp_path = SEEN_PAPERS_PATH.with_suffix(".tmp")
            temp_path.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(SEEN_PAPERS_PATH)
        except Exception:
            pass


def _enrich_profile(entry: dict) -> dict:
    try:
        yaml_path = PROJECT_ROOT / entry["path"]
        for line in yaml_path.read_text(encoding="utf-8").splitlines()[:20]:
            line = line.strip()
            if line.startswith("name:"):
                entry["display"] = line[5:].strip().strip('"').strip("'")
                return entry
    except Exception:
        pass
    entry["display"] = re.sub(r"[_-]+", " ", Path(entry["path"]).stem).strip() or entry["path"]
    return entry


def _profile_display_name(rel_path: str) -> str:
    """Extract the human-readable name from a profile YAML file."""

    try:
        yaml_path = PROJECT_ROOT / rel_path
        for line in yaml_path.read_text(encoding="utf-8").splitlines()[:20]:
            line = line.strip()
            if line.startswith("name:"):
                return line[5:].strip().strip('"').strip("'")
    except Exception:
        pass
    # Fallback: strip .yaml and path prefix
    name = Path(rel_path).stem
    name = re.sub(r"[_-]+", " ", name).strip()
    return name or rel_path


def _sanitize_model_config(cfg: dict[str, Any], fallback_env: str) -> dict[str, Any]:
    return {
        "provider": cfg.get("provider", "openai_compatible"),
        "model": cfg.get("model", ""),
        "base_url": cfg.get("base_url", ""),
        "temperature": cfg.get("temperature", 0.2),
        "api_key_present": bool(cfg.get("api_key") or os.environ.get(fallback_env)),
    }


def _has_env(name: str) -> bool:
    return bool(os.environ.get(name))


def _default_model_name(preset: str) -> str:
    raw = config.load()
    return str(((raw.get("models") or {}).get(preset) or {}).get("model") or "")


def _default_base_url(preset: str) -> str:
    raw = config.load()
    return str(((raw.get("models") or {}).get(preset) or {}).get("base_url") or "https://api.openai.com/v1")


def _default_api_key(preset: str) -> str:
    name = f"CONFLUX_MODELS__{preset.upper()}__API_KEY"
    return os.environ.get(name) or os.environ.get("OPENAI_API_KEY") or ""


def _path_value(value: Any, default: str) -> str:
    text = str(value or default).strip()
    path = Path(text).expanduser()
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)


def _optional_path(value: Any) -> str | None:
    text = str(value or "").strip()
    return _path_value(text, text) if text else None


def _rel(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _chat_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _model_env_updates(payload: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    base_url = str(payload.get("base_url") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    embedding_base_url = str(payload.get("embedding_base_url") or "").strip()
    embedding_api_key = str(payload.get("embedding_api_key") or "").strip()
    embedding_model = str(payload.get("embedding_model") or "").strip()

    for preset in ("REASONING", "CHEAP"):
        updates[f"CONFLUX_MODELS__{preset}__PROVIDER"] = "openai_compatible"
        if base_url:
            updates[f"CONFLUX_MODELS__{preset}__BASE_URL"] = base_url
        if api_key:
            updates[f"CONFLUX_MODELS__{preset}__API_KEY"] = api_key
        if model:
            updates[f"CONFLUX_MODELS__{preset}__MODEL"] = model
    if embedding_base_url or base_url:
        updates["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url or base_url
    if embedding_api_key or api_key:
        updates["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key or api_key
    if embedding_model:
        updates["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    depth = str(payload.get("depth") or "standard").strip()
    if depth == "quick":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "1"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "false"
        updates["CONFLUX_RETRIEVAL__TOP_K"] = "3"
        updates["CONFLUX_RETRIEVAL__FINAL_K"] = "3"
    elif depth == "deep":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "5"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "true"
        updates["CONFLUX_RESEARCH__MAX_DEEP_QUESTIONS"] = "5"
        updates["CONFLUX_RETRIEVAL__TOP_K"] = "15"
        updates["CONFLUX_RETRIEVAL__FINAL_K"] = "10"
    return updates


@contextlib.contextmanager
def _temporary_env(updates: dict[str, str]):
    old_values = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value:
                os.environ[key] = value
        config._config = None  # type: ignore[attr-defined]
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config._config = None  # type: ignore[attr-defined]


def _safe_read_path(requested_path: str) -> Path | None:
    if not requested_path:
        return None
    path = Path(requested_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        resolved = path.resolve()
    except OSError:
        return None
    allowed = [
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "data" / "documents" / "papers",
        PROJECT_ROOT / "profiles",
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "tests" / "fixtures" / "papers",
        PROJECT_ROOT / "src" / "conflux" / "workbench" / "static",
    ]
    for root in allowed:
        try:
            resolved.relative_to(root.resolve())
            if resolved.name.lower() in {".env", "config.yaml"}:
                return None
            return resolved
        except ValueError:
            continue
    return None
