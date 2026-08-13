"""Local HTTP workbench for inspecting and running Conflux workflows."""

from __future__ import annotations

import argparse
import calendar
import email.utils
import html
import hashlib
import hmac
import json
import mimetypes
import os
import random
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
import markdown

from conflux import config
from conflux.adapters.sqlite_store import (
    JobQueue,
    ProjectPaperStore,
    SearchIntentStore,
    SearchRunStore,
    SQLiteDatabase,
)
from conflux.adapters.evidence_ledger_store import EvidenceLedgerRepository
from conflux.core.runtime_home import database_path
from conflux.knowledge.paper_indexer import promote_inbox
from conflux.knowledge.stats import gather_knowledge_stats
from conflux.paper_ingestion.filters import paper_matches_negative_filter
from conflux.paper_ingestion.inbox_report import write_inbox_artifacts
from conflux.paper_ingestion.pipeline import build_inbox
from conflux.paper_ingestion.scorer import reading_level_for_score
from conflux.projects import (
    P3_PROTOCOL_VERSION,
    EventKind,
    ProjectIntelligence,
    ReviewStatus,
    SnapshotTrigger,
    build_cycle_audit,
    build_snapshot,
    collect_all_events,
    collect_test_events,
    confirm_cycle_summary,
    ingest_events,
    latest_confirmed_summary,
    new_event,
    parse_work_item_ref,
    seed_reviews,
    supersede_document_reviews,
    work_item_projection,
)
from conflux.projects.discovery_service import document_map, scan_project_documents
from conflux.projects.rag_coverage import compute_coverage, index_project_documents
from conflux.project_registry import (
    Milestone,
    ProjectDefinition,
    ProjectPlan,
    ProjectRegistry,
    RefreshPolicy,
    analysis_diff,
    build_evidence_catalog,
    build_plan_prompt,
    charter_draft_prompt,
    discover_plan_documents,
    extract_plan_suggestions,
    monitor_project,
    normalize_plan_analysis,
    public_document_context,
)
from conflux.progress_audit import audit_project, write_progress_artifacts
from conflux.progress_audit.git_inspector import inspect_git_status
from conflux.progress_audit.progress_report import load_snapshot
from conflux.rag.indexer import EmbeddingIndexMismatchError
from conflux.research_profile import ResearchProfile, load_profile
from conflux.workbench.config_store import (
    WORKBENCH_ENV,
    _reload_env,
    build_sanitized_config,
    save_config_field,
    save_workbench_env,
)
from conflux.workbench.jobs import get_job_manager
from conflux.workbench.sessions import build_session_index, get_session_detail


PROJECT_ROOT = config.PROJECT_ROOT
DEFAULT_PROFILE = "profiles/example_gis_agent.yaml"
DEFAULT_FIXTURE = "tests/fixtures/papers/arxiv_sample.json"
DEFAULT_INBOX_DIR = "reports/workbench/papers"
DEFAULT_DOCUMENTS_DIR = "data/documents"
DEFAULT_PROMOTE_DIR = "data/documents/papers"
DEFAULT_PROGRESS_DIR = "reports/workbench/progress"
DEFAULT_PROJECTS_DIR = "projects"
DEFAULT_PROJECT_CACHE_DIR = "reports/workbench/projects"
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


def _nonnegative_env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.environ.get(name) or default))
    except ValueError:
        return default


SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS = _nonnegative_env_float(
    "SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS",
    1.1,
)
SEMANTIC_SCHOLAR_MAX_ATTEMPTS = 3
SEMANTIC_SCHOLAR_MAX_QUERIES = 3
SEMANTIC_SCHOLAR_MAX_PAGES = 3
_SEMANTIC_SCHOLAR_RATE_LOCK = threading.Lock()
_SEMANTIC_SCHOLAR_LAST_REQUEST_AT = 0.0

# Security: initialized from the parent environment and refreshed at startup.
_ACCESS_TOKEN = os.environ.get("CONFLUX_ACCESS_TOKEN", "").strip()

# Cookie name used for browser-based auth when bound to a non-loopback address.
_AUTH_COOKIE = "conflux_token"


def _load_runtime_env() -> None:
    """Load persisted workbench settings only when the server is started."""

    global SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS, _ACCESS_TOKEN

    _reload_env()
    SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS = _nonnegative_env_float(
        "SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS",
        1.1,
    )
    _ACCESS_TOKEN = os.environ.get("CONFLUX_ACCESS_TOKEN", "").strip()


_AUTH_COOKIE_MAX_AGE = 12 * 60 * 60

_TIER_DEFAULT_PRESETS = {
    "quick": "flash",
    "standard": "verifier",
    "deep": "reasoning",
}

_FEATURE_MODEL_FALLBACKS = {
    "profile_optimization": "cheap",
    "paper_review": "cheap",
    "plan_analysis": "reasoning",
    "project_charter": "reasoning",
    # P2 默认配置结论基于 balanced（deepseek-v4-flash-guan、温度 0.25）。
    "research_radar": "balanced",
    "plan_translation": "cheap",
}


def _auth_cookie_value() -> str:
    """Derive a browser session value without exposing the access token."""
    return hashlib.sha256(f"conflux-workbench:{_ACCESS_TOKEN}".encode("utf-8")).hexdigest()


def _resolved_tier_model_config(raw: dict[str, Any], tier: str) -> dict[str, Any]:
    """Resolve the user-facing model for one research depth."""

    models = raw.get("models") or {}
    direct = dict(models.get(tier) or {})
    if direct.get("model"):
        return direct
    profile = ((raw.get("research") or {}).get("profiles") or {}).get(tier) or {}
    preset = str(profile.get("synthesizer_model") or _TIER_DEFAULT_PRESETS[tier])
    return dict(models.get(preset) or {})


def _resolved_feature_model_config(raw: dict[str, Any], feature: str) -> dict[str, Any]:
    models = raw.get("models") or {}
    fallback = _FEATURE_MODEL_FALLBACKS[feature]
    resolved = dict(models.get(fallback) or {})
    resolved.update(dict(models.get(feature) or {}))
    return resolved


# TTL cache for expensive /api/status sub-queries (Chroma audits).  The rest
# of build_status stays fresh so config changes surface immediately; the
# heavy local checks amortize across reloads (P3 §13.1 first-screen target).
_AUDIT_CACHE_LOCK = threading.Lock()
_AUDIT_CACHE: dict[str, tuple[float, Any]] = {}


def _cached_expensive(key: str, ttl_seconds: float, producer: Any) -> Any:
    with _AUDIT_CACHE_LOCK:
        cached = _AUDIT_CACHE.get(key)
        if cached and time.monotonic() - cached[0] < ttl_seconds:
            return cached[1]
    value = producer()
    with _AUDIT_CACHE_LOCK:
        _AUDIT_CACHE[key] = (time.monotonic(), value)
    return value


def _invalidate_expensive_cache(*keys: str) -> None:
    with _AUDIT_CACHE_LOCK:
        for key in keys:
            _AUDIT_CACHE.pop(key, None)


def build_status() -> dict[str, Any]:
    """Return sanitized local workbench status."""

    raw = config.load()
    reasoning = dict(raw.get("models", {}).get("reasoning") or {})
    cheap = dict(raw.get("models", {}).get("cheap") or {})
    tier_models = {
        tier: _sanitize_model_config(
            _resolved_tier_model_config(raw, tier),
            f"CONFLUX_MODELS__{tier.upper()}__API_KEY",
        )
        for tier in ("quick", "standard", "deep")
    }
    feature_models = {
        feature: _sanitize_model_config(
            _resolved_feature_model_config(raw, feature),
            f"CONFLUX_MODELS__{feature.upper()}__API_KEY",
        )
        for feature in _FEATURE_MODEL_FALLBACKS
    }
    embedding = dict(raw.get("embedding") or {})
    web_search = dict(raw.get("web_search") or {})
    web_provider = str(web_search.get("provider") or "duckduckgo").strip().lower()
    web_requires_key = web_provider in {"serpapi", "bing", "google"}
    web_ready = {
        "serpapi": _has_env("SERPAPI_API_KEY"),
        "bing": _has_env("BING_SEARCH_API_KEY"),
        "google": _has_env("GOOGLE_API_KEY") and (_has_env("GOOGLE_CSE_ID") or _has_env("GOOGLE_CX")),
    }.get(web_provider, True)

    return {
        "project_root": str(PROJECT_ROOT),
        "profiles": [_enrich_profile(p) for p in _list_files(PROJECT_ROOT / "profiles", {".yaml", ".yml"})],
        "reports": _list_report_files(PROJECT_ROOT / "reports"),
        "paper_outputs": _list_files(PROJECT_ROOT / "data" / "documents" / "papers", {".md", ".json"}),
        "paper_ingestion_audit": _cached_expensive(
            "paper_ingestion_audit", 30.0, build_paper_ingestion_audit
        ),
        "defaults": {
            "profile": DEFAULT_PROFILE,
            "fixture": DEFAULT_FIXTURE,
            "inbox_dir": DEFAULT_INBOX_DIR,
            "promote_dir": DEFAULT_PROMOTE_DIR,
            "progress_dir": DEFAULT_PROGRESS_DIR,
            "reasoning": _sanitize_model_config(reasoning, "OPENAI_API_KEY"),
            "cheap": _sanitize_model_config(cheap, "OPENAI_API_KEY"),
            "tier_models": tier_models,
            "feature_models": feature_models,
            "embedding": _sanitize_model_config(embedding, "OPENAI_API_KEY"),
            "vector_store": _cached_expensive(
                "vector_store", 30.0, build_vector_store_status
            ),
            "web_search": {
                "provider": web_provider,
                "max_results": int(web_search.get("max_results") or 5),
                "requires_api_key": web_requires_key,
                "ready": web_ready,
            },
        },
        "workbench_env": str(WORKBENCH_ENV) if WORKBENCH_ENV.exists() else "",
        "saved_depth": os.environ.get("CONFLUX_DEPTH", "standard"),
        "p3": {
            "overview_enabled": _p3_overview_enabled(),
            "protocol_version": P3_PROTOCOL_VERSION,
        },
        "credentials": {
            "openai_api_key": _has_env("OPENAI_API_KEY"),
            "reasoning_api_key": _has_env("CONFLUX_MODELS__REASONING__API_KEY"),
            "cheap_api_key": _has_env("CONFLUX_MODELS__CHEAP__API_KEY"),
            "quick_api_key": tier_models["quick"]["api_key_present"],
            "standard_api_key": tier_models["standard"]["api_key_present"],
            "deep_api_key": tier_models["deep"]["api_key_present"],
            "embedding_api_key": _has_env("CONFLUX_EMBEDDING__API_KEY"),
            **{
                f"{feature}_api_key": feature_models[feature]["api_key_present"]
                for feature in _FEATURE_MODEL_FALLBACKS
            },
            "serpapi_api_key": _has_env("SERPAPI_API_KEY"),
            "bing_api_key": _has_env("BING_SEARCH_API_KEY"),
            "google_api_key": _has_env("GOOGLE_API_KEY"),
            "google_cse_id": _has_env("GOOGLE_CSE_ID") or _has_env("GOOGLE_CX"),
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
            raise ValueError("模型没有返回可识别的 JSON。")
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("模型返回的 JSON 格式无效，请重试。") from exc
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的内容不是 JSON 对象。")
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


def _profile_output_needs_revision(source: dict[str, Any], optimized: dict[str, Any]) -> bool:
    """Detect a model response that merely echoes the draft."""

    normalize = lambda value: " ".join(str(value or "").split()).casefold().strip()
    source_description = normalize(source.get("description"))
    optimized_description = normalize(optimized.get("description"))
    source_keywords = {normalize(item) for item in _split_lines(source.get("keywords")) if normalize(item)}
    optimized_keywords = {normalize(item) for item in _split_lines(optimized.get("keywords")) if normalize(item)}
    source_negative = {normalize(item) for item in _split_lines(source.get("negative_keywords")) if normalize(item)}
    optimized_negative = {normalize(item) for item in _split_lines(optimized.get("negative_keywords")) if normalize(item)}
    description_same = bool(source_description) and source_description == optimized_description
    novel_keywords = optimized_keywords - source_keywords
    novel_negative = optimized_negative - source_negative
    return description_same and len(novel_keywords) < 2 and not novel_negative


def optimize_inline_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a reviewable research-profile suggestion without persisting it."""

    keywords = _clean_profile_items(payload.get("keywords"), limit=20)
    fields = _clean_profile_items(payload.get("fields"), limit=8)
    negative_keywords = _clean_profile_items(payload.get("negative_keywords"), limit=16)
    description = str(payload.get("description") or "").strip()[:2400]
    if not keywords and not description:
        return {"ok": False, "error": "请至少填写关键词或研究描述，再进行 AI 优化。"}

    prompt = """你是一位研究生论文检索策略专家。请把用户草拟的研究画像重写为高质量、可审查的论文检索画像。

目标：提高 arXiv 和 Semantic Scholar 的检索精度与召回平衡，避免宽泛关键词独占结果。
要求：
1. fields 保留或补充 1-5 个合适的 arXiv 分类代码（如 cs.AI、cs.CL），不确定时不要臆造。
2. keywords 给出 8-16 个英文检索短语，兼顾研究对象、方法和应用场景；避免只保留 knowledge graph、AI 等过宽词。
3. description 改写为一个边界清楚的中文研究问题，说明研究对象、核心方法、应用场景和关注的证据。
4. negative_keywords 给出 4-12 个英文排除词，用于过滤同名概念和明显无关领域；不要排除可能相关的交叉学科。
5. optimization_notes 用 2-4 条中文短句解释主要改动，便于用户审查。
6. 必须真正重写研究问题：不能逐字复述用户 description，至少补充研究对象、方法、场景和边界中的两个缺失维度。
7. keywords 至少新增两个相对用户草稿的英文检索短语；不要只做大小写、单复数或词序变化。
8. 不要改变用户研究主题，不要添加用户未表达的具体实验结论。

只返回 JSON 对象，不要 Markdown。结构必须为：
{"fields": ["..."], "keywords": ["..."], "description": "...", "negative_keywords": ["..."], "optimization_notes": ["..."]}

用户草稿：
""" + json.dumps({
        "fields": fields,
        "keywords": keywords,
        "description": description,
        "negative_keywords": negative_keywords,
    }, ensure_ascii=False)

    settings = _feature_model_settings("profile_optimization")
    model = settings["model"]
    base_url = settings["base_url"]
    api_key = settings["api_key"]
    result = run_model_probe({
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "prompt": prompt,
        "temperature": 0.2,
        "max_tokens": 1600,
        "timeout": 90,
        "json_mode": True,
    })
    if not result.get("ok"):
        error = str(result.get("error") or "画像优化请求失败。")
        if "API key" in error:
            error = "画像优化需要可用的模型 API Key，请先在“模型与环境”中完成配置。"
        return {"ok": False, "error": error}

    def parse_suggestion(content: str) -> tuple[dict[str, Any], list[str]]:
        suggestion = _parse_json_object(content)
        optimized = {
            "fields": _clean_profile_items(suggestion.get("fields"), limit=5),
            "keywords": _clean_profile_items(suggestion.get("keywords"), limit=16),
            "description": " ".join(str(suggestion.get("description") or "").split())[:1200],
            "negative_keywords": _clean_profile_items(suggestion.get("negative_keywords"), limit=12),
        }
        notes = _clean_profile_items(suggestion.get("optimization_notes"), limit=4, item_limit=180)
        return optimized, notes

    try:
        optimized, notes = parse_suggestion(str(result.get("content") or ""))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    source_profile = {"description": description, "keywords": keywords, "negative_keywords": negative_keywords}
    if _profile_output_needs_revision(source_profile, optimized):
        retry_prompt = prompt + """

上一次建议与用户草稿过于接近，未达到优化目标。请重新生成：研究问题必须换一种明确表述，并至少加入两个新的检索短语（对象、方法、场景或评价维度），同时保留主题边界。只返回完整 JSON。"""
        retry = run_model_probe({
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "prompt": retry_prompt,
            "temperature": 0.35,
            "max_tokens": 1800,
            "timeout": 90,
            "json_mode": True,
        })
        if not retry.get("ok"):
            return {"ok": False, "error": "模型优化幅度不足，强化重写请求未完成，请稍后重试。"}
        try:
            optimized, retry_notes = parse_suggestion(str(retry.get("content") or ""))
            notes = retry_notes or notes
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    if _profile_output_needs_revision(source_profile, optimized):
        return {"ok": False, "error": "模型返回的优化稿仍与原始画像过于接近，请重试或补充研究边界。"}

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




def _apply_llm_reviews_to_inbox(result, reviews: dict[str, dict[str, Any]]) -> None:
    """Apply semantic categories without discarding deterministic candidates on failure."""

    relevance_weight = {"relevant": 0.9, "partially_relevant": 0.6, "irrelevant": 0.1}
    applied = 0
    unreviewed = 0
    deep_review_failures = 0
    changed = False
    for paper, analysis in result.analyzed:
        deterministic_score = float(analysis.relevance_score)
        review = reviews.get(paper.id)
        if not review or review.get("relevance") == "unreviewed":
            unreviewed += 1
            analysis.metadata["deterministic_score"] = deterministic_score
            analysis.metadata["semantic_score"] = None
            analysis.metadata["review_status"] = "unreviewed"
            analysis.metadata["candidate_status"] = str(
                (review or {}).get("candidate_status") or "provisional"
            )
            analysis.metadata["review_error_code"] = str(
                (review or {}).get("error_code") or "llm_unavailable"
            )
            analysis.metadata["review_error"] = str(
                (review or {}).get("error_detail")
                or "LLM semantic review was not completed."
            )
            analysis.metadata["review_next_action"] = str(
                (review or {}).get("next_action")
                or "Configure a working review model and retry this candidate."
            )
            changed = True
            continue
        relevance = str(review.get("relevance") or "irrelevant")
        confidence = max(0.0, min(1.0, float(review.get("confidence") or 0.0)))
        semantic_score = round(relevance_weight.get(relevance, 0.0) * confidence, 4)
        review["semantic_score"] = semantic_score
        review["semantic_score_percent"] = round(semantic_score * 100, 1)
        if relevance == "relevant" and confidence >= 0.75:
            reading_level = "deep"
        elif relevance in {"relevant", "partially_relevant"}:
            reading_level = "skim"
        else:
            reading_level = "skip"

        analysis.metadata["deterministic_score"] = deterministic_score
        analysis.metadata["llm_review"] = dict(review)
        analysis.metadata["semantic_score"] = semantic_score
        analysis.metadata["llm_score"] = round(semantic_score * 100, 1)
        analysis.metadata["llm_reason"] = str(review.get("reasoning") or "")
        analysis.metadata["review_status"] = str(review.get("review_status") or "reviewed")
        analysis.metadata["candidate_status"] = str(review.get("candidate_status") or "reviewed")
        if review.get("deep_review_status") == "unreviewed":
            deep_review_failures += 1
            analysis.metadata["deep_review_error_code"] = str(review.get("deep_error_code") or "")
            analysis.metadata["deep_review_error"] = str(review.get("deep_error_detail") or "")
        analysis.relevance_score = semantic_score
        analysis.reading_level = reading_level  # type: ignore[assignment]
        analysis.citation_value = (
            "high" if reading_level == "deep" else "medium" if reading_level == "skim" else "low"
        )  # type: ignore[assignment]
        applied += 1
        changed = True

    if not changed:
        return
    if applied:
        result.analyzed.sort(key=lambda item: item[1].relevance_score, reverse=True)
    result.stats.update({
        "deep": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "deep"),
        "skim": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "skim"),
        "skip": sum(1 for _, analysis in result.analyzed if analysis.reading_level == "skip"),
        "llm_scored": applied,
        "llm_reviewed": applied,
        "llm_unreviewed": unreviewed,
        "deep_review_failures": deep_review_failures,
    })
    if result.artifacts:
        result.artifacts = write_inbox_artifacts(
            result.profile,
            result.analyzed,
            out_dir=result.artifacts.json_path.parent,
            stats=result.stats,
        )


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
    items = _request_semantic_scholar(url).get("data") or []

    from conflux.paper_ingestion.models import PaperRecord, parse_datetime

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
        pub_date = _s2_str(item, "publicationDate")
        if not pub_date and item.get("year"):
            pub_date = f"{item['year']}-01-01"
        results.append(PaperRecord(
            id=paper_id,
            title=title,
            abstract=abstract,
            authors=authors,
            published_at=parse_datetime(pub_date),
            source="semantic_scholar",
            url=_s2_str(item, "url"),
            pdf_url=pdf_url,
            doi=_s2_str(ext_ids, "DOI"),
            categories=[],
        ))
    return results


def _request_semantic_scholar(url: str) -> dict:
    headers = {"User-Agent": "ConfluxWorkbench/1.0"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(SEMANTIC_SCHOLAR_MAX_ATTEMPTS):
        _wait_for_semantic_scholar_slot()
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == SEMANTIC_SCHOLAR_MAX_ATTEMPTS - 1:
                raise
            delay = _semantic_scholar_retry_delay(exc, attempt)
            time.sleep(delay)

    return {}


def _wait_for_semantic_scholar_slot() -> None:
    global _SEMANTIC_SCHOLAR_LAST_REQUEST_AT

    with _SEMANTIC_SCHOLAR_RATE_LOCK:
        now = time.monotonic()
        remaining = SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS - (
            now - _SEMANTIC_SCHOLAR_LAST_REQUEST_AT
        )
        if remaining > 0:
            time.sleep(remaining)
        _SEMANTIC_SCHOLAR_LAST_REQUEST_AT = time.monotonic()


def _semantic_scholar_retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float:
    retry_after = (exc.headers or {}).get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            retry_at = email.utils.parsedate_to_datetime(retry_after)
            if retry_at is not None:
                return max(0.0, retry_at.timestamp() - time.time())

    base_delay = 2.0 * (2 ** attempt)
    return base_delay + random.uniform(0.0, base_delay * 0.25)


def _s2_str(obj: dict, key: str) -> str:
    val = obj.get(key)
    return str(val).strip() if val else ""


def build_paper_ingestion_audit() -> dict[str, Any]:
    """Compare promotion intent with documents that really exist in Chroma."""

    manifest_path = PROJECT_ROOT / "data" / "documents" / "papers" / "paper_promotion_manifest.json"
    expected_full_text: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for decision in manifest.get("decisions") or []:
                if not isinstance(decision, dict) or decision.get("action") != "full_text":
                    continue
                paper_id = str(decision.get("paper_id") or "").strip()
                if paper_id:
                    expected_full_text[_paper_identity("arxiv", paper_id)] = decision
        except (OSError, json.JSONDecodeError):
            pass

    seen_titles: dict[str, str] = {}
    for key, entry in _load_seen_papers().items():
        if isinstance(entry, dict):
            seen_titles[_canonical_seen_key(key)] = str(entry.get("title") or "")

    aggregates: dict[str, dict[str, Any]] = {}
    available = False
    error = ""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = Path(str(config.get("vector_store", "persist_dir", default="./data/chroma_db")))
        if not persist_dir.is_absolute():
            persist_dir = PROJECT_ROOT / persist_dir
        collection_name = str(config.get("vector_store", "collection_name", default="conflux_docs"))
        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(collection_name)
        payload = collection.get(include=["metadatas"])
        available = True
        for metadata in payload.get("metadatas") or []:
            if not isinstance(metadata, dict):
                continue
            paper_id = str(metadata.get("paper_id") or "").strip()
            if not paper_id:
                continue
            source = _normalized_paper_source(metadata.get("paper_source"), paper_id)
            identity = _paper_identity(source, paper_id)
            item = aggregates.setdefault(identity, {
                "identity": identity,
                "paper_id": paper_id,
                "title": str(metadata.get("paper_title") or seen_titles.get(identity) or ""),
                "summary_chunks": 0,
                "full_text_chunks": 0,
            })
            scope = str(metadata.get("content_scope") or "")
            if scope == "full_text":
                item["full_text_chunks"] += 1
            elif scope == "summary":
                item["summary_chunks"] += 1
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    for identity, decision in expected_full_text.items():
        item = aggregates.setdefault(identity, {
            "identity": identity,
            "paper_id": str(decision.get("paper_id") or identity.partition(":")[2]),
            "title": seen_titles.get(identity, ""),
            "summary_chunks": 0,
            "full_text_chunks": 0,
        })
        item["full_text_expected"] = True

    papers = []
    for identity, item in aggregates.items():
        full_text_chunks = int(item.get("full_text_chunks") or 0)
        summary_chunks = int(item.get("summary_chunks") or 0)
        full_text_expected = bool(item.get("full_text_expected"))
        if full_text_chunks:
            status = "full_text_indexed"
        elif full_text_expected and available:
            status = "full_text_missing"
        elif summary_chunks:
            status = "summary_indexed"
        else:
            status = "not_ingested" if available else "audit_unavailable"
        papers.append({**item, "status": status, "repairable": status == "full_text_missing"})

    papers.sort(key=lambda item: (not item["repairable"], str(item.get("paper_id") or "")))
    return {
        "available": available,
        "error": error,
        "collection": str(config.get("vector_store", "collection_name", default="conflux_docs")),
        "indexed_papers": len([item for item in papers if item["status"] in {"summary_indexed", "full_text_indexed"}]),
        "full_text_indexed": len([item for item in papers if item["status"] == "full_text_indexed"]),
        "summary_only": len([item for item in papers if item["status"] == "summary_indexed"]),
        "expected_full_text": len(expected_full_text),
        "repairable": [item for item in papers if item["repairable"]],
        "papers": papers,
    }


def build_vector_store_status() -> dict[str, Any]:
    persist_dir = Path(str(config.get("vector_store", "persist_dir", default="./data/chroma_db")))
    if not persist_dir.is_absolute():
        persist_dir = PROJECT_ROOT / persist_dir
    active = str(config.get("vector_store", "collection_name", default="conflux_docs"))
    if not persist_dir.exists():
        return {"active": active, "persist_dir": str(persist_dir), "collections": []}

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collections = []
        for item in client.list_collections():
            name = str(item if isinstance(item, str) else item.name)
            collection = client.get_collection(name)
            preview = collection.peek(1)
            embeddings = preview.get("embeddings")
            dimension = len(embeddings[0]) if embeddings is not None and len(embeddings) else None
            metadata = dict(collection.metadata or {})
            collections.append({
                "name": name,
                "active": name == active,
                "count": collection.count(),
                "dimension": dimension,
                "model": str(metadata.get("conflux_embedding_model") or ""),
            })
    except Exception as exc:
        return {
            "active": active,
            "persist_dir": str(persist_dir),
            "collections": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    collections.sort(key=lambda item: (not item["active"], item["name"]))
    return {"active": active, "persist_dir": str(persist_dir), "collections": collections}


def rebuild_knowledge_index(payload: dict[str, Any]) -> dict[str, Any]:
    source_dir = Path(_path_value(payload.get("source_dir"), DEFAULT_DOCUMENTS_DIR))
    if not source_dir.exists():
        return {"ok": False, "error": f"知识文档目录不存在：{source_dir}"}

    try:
        documents = _load_knowledge_documents(source_dir)
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        return {"ok": False, "error": f"知识文档解析失败：{exc}"}
    if not documents:
        return {"ok": False, "error": f"知识文档目录中没有可重建的 Markdown：{source_dir}"}

    current_name = str(config.get("vector_store", "collection_name", default="conflux_docs"))
    model = str(payload.get("embedding_model") or config.get("embedding", "model", default="embedding"))
    model_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-._") or "embedding"
    requested_name = str(payload.get("collection_name") or "").strip()
    new_name = requested_name or f"{current_name}__{model_slug}__{time.strftime('%Y%m%d_%H%M%S')}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,510}[A-Za-z0-9]", new_name):
        return {"ok": False, "error": "Collection 名称只能使用字母、数字、点、下划线和连字符，且长度至少为 3。"}
    if new_name == current_name:
        return {"ok": False, "error": "完整重建必须使用新的 collection 名称，以保留当前旧向量。"}

    status = build_vector_store_status()
    if any(item["name"] == new_name for item in status["collections"]):
        return {"ok": False, "error": f"Collection 已存在：{new_name}"}

    embedding_updates = _embedding_runtime_updates(payload)
    if not embedding_updates.get("CONFLUX_EMBEDDING__API_KEY"):
        return {"ok": False, "error": "完整重建需要 Embedding API Key，请先保存模型配置。"}
    embedding_updates["CONFLUX_VECTOR_STORE__COLLECTION_NAME"] = new_name

    from conflux.rag.indexer import create_vector_store, index_documents

    try:
        with config.override(embedding_updates):
            indexed = index_documents(create_vector_store(), documents)
    except Exception as exc:
        _delete_vector_collection(new_name)
        return {"ok": False, "error": f"完整重建失败：{type(exc).__name__}: {exc}"}

    save_workbench_env(
        embedding_base_url=str(payload.get("embedding_base_url") or "").strip(),
        embedding_api_key=str(payload.get("embedding_api_key") or "").strip(),
        embedding_model=str(payload.get("embedding_model") or "").strip(),
        vector_collection_name=new_name,
    )
    _invalidate_expensive_cache("vector_store", "paper_ingestion_audit")
    return {
        "ok": True,
        "previous_collection": current_name,
        "active_collection": new_name,
        "documents": len(documents),
        "indexed": indexed,
        "vector_store": build_vector_store_status(),
    }


def delete_knowledge_index(payload: dict[str, Any]) -> dict[str, Any]:
    collection_name = str(payload.get("collection_name") or "").strip()
    active = str(config.get("vector_store", "collection_name", default="conflux_docs"))
    if not collection_name:
        return {"ok": False, "error": "collection_name required"}
    if collection_name == active:
        return {"ok": False, "error": "当前正在使用的 collection 不能删除，请先完成一次重建并切换。"}
    status = build_vector_store_status()
    if not any(item["name"] == collection_name for item in status["collections"]):
        return {"ok": False, "error": f"Collection 不存在：{collection_name}"}
    _delete_vector_collection(collection_name)
    _invalidate_expensive_cache("vector_store")
    return {"ok": True, "deleted": collection_name, "vector_store": build_vector_store_status()}


def _load_knowledge_documents(source_dir: Path) -> list[Any]:
    from langchain_core.documents import Document

    documents = []
    for path in sorted(source_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata: dict[str, Any] = {"source": path.relative_to(source_dir).as_posix()}
        content = text
        if text.startswith("---\n"):
            parts = text.split("---\n", 2)
            if len(parts) == 3:
                try:
                    parsed = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as exc:
                    raise ValueError(f"{path}: front matter 不是有效 YAML：{exc}") from exc
                if isinstance(parsed, dict):
                    metadata.update(parsed)
                content = parts[2].lstrip()
        metadata["chunk_id"] = str(metadata.get("chunk_id") or metadata["source"])
        if metadata.get("paper_id"):
            section = str(metadata.get("paper_section") or "")
            scope = "summary" if section == "summary" or metadata["chunk_id"].endswith("#summary") else "full_text"
            metadata["content_scope"] = scope
            metadata["full_text_indexed"] = scope == "full_text"
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _delete_vector_collection(collection_name: str) -> None:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    persist_dir = Path(str(config.get("vector_store", "persist_dir", default="./data/chroma_db")))
    if not persist_dir.is_absolute():
        persist_dir = PROJECT_ROOT / persist_dir
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    names = {str(item if isinstance(item, str) else item.name) for item in client.list_collections()}
    if collection_name in names:
        client.delete_collection(collection_name)


def _seen_entry_should_skip(identity: str, entry: dict[str, Any], audit: dict[str, Any]) -> bool:
    retryable_states = {"full_text_missing", "full_text_failed", "full_text_extracted", "not_ingested"}
    audit_item = next(
        (item for item in audit.get("papers") or [] if item.get("identity") == identity),
        None,
    )
    if audit_item and audit_item.get("status") in retryable_states:
        return False
    return str(entry.get("status") or "inboxed") not in retryable_states


def _discover_unseen_papers(
    profile: ResearchProfile,
    source: str,
    max_results: int,
) -> tuple[list, int]:
    """Fetch fresh online papers, paging past results already shown before."""
    seen_map = _load_seen_papers()
    seen_entries: dict[str, dict[str, Any]] = {}
    for key, value in seen_map.items():
        identity = _canonical_seen_key(key)
        entry = dict(value) if isinstance(value, dict) else {}
        current = seen_entries.get(identity) or {}
        if current.get("status") in {"", "inboxed"} or not current:
            seen_entries[identity] = entry
    audit = build_paper_ingestion_audit()
    collected = []
    collected_ids: set[str] = set()
    skipped_ids: set[str] = set()
    skipped_seen = 0

    def _collect(batch: list) -> None:
        nonlocal skipped_seen
        for paper in batch:
            identity = _paper_identity(source, paper.id)
            if identity in seen_entries and _seen_entry_should_skip(identity, seen_entries[identity], audit):
                if identity not in skipped_ids:
                    skipped_ids.add(identity)
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
        page_size = max(10, min(100, (max_results + len(queries) - 1) // max(1, len(queries))))
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

        queries = [
            " ".join(group)
            for group in profile_keyword_groups(profile, max_queries=SEMANTIC_SCHOLAR_MAX_QUERIES)
        ][:max_results]
        if not queries:
            queries = ["research"]
        page_size = max(1, min(20, (max_results + len(queries) - 1) // len(queries)))
        active = [True] * len(queries)
        for page in range(SEMANTIC_SCHOLAR_MAX_PAGES):
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


def _normalized_paper_source(source: Any, paper_id: str) -> str:
    """Recover arXiv identity from legacy metadata whose source was unknown."""

    normalized = str(source or "").strip().lower()
    if normalized in {"arxiv", "semantic_scholar"}:
        return normalized
    if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", str(paper_id or "").strip()):
        return "arxiv"
    return normalized or "unknown"


def _canonical_seen_key(key: str) -> str:
    source, separator, paper_id = str(key).partition(":")
    if not separator:
        return str(key)
    return _paper_identity(source, paper_id)


def run_paper_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the paper inbox pipeline from UI payload (file-based or inline profile)."""

    source = str(payload.get("source") or "arxiv")
    out_dir = _path_value(payload.get("out_dir"), DEFAULT_INBOX_DIR)
    max_results = max(1, min(500, int(payload.get("max_results") or 50)))
    review_limit = max(1, min(100, int(payload.get("review_limit") or 40)))
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
            return {
                "ok": True,
                "profile_id": profile.id,
                "stats": {
                    "total": 0,
                    "deep": 0,
                    "skim": 0,
                    "skip": 0,
                    "previously_seen": skipped_seen,
                },
                "papers": [],
                "review_status": "not_requested",
                "review_error": "",
                "review_next_action": "",
                "message": "当前检索批次没有新增论文；已见论文不会重复进入收件箱。",
                "markdown_path": "",
                "json_path": "",
            }
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

    # Optional semantic review through the same first-party plugin used by workflows.
    llm_reviews: dict[str, dict[str, Any]] = {}
    review_status = "not_requested"
    review_error = ""
    review_next_action = ""
    if use_llm:
        try:
            from conflux.builtin.paper.plugin import paper_review
            from conflux.sdk.testing import make_plugin_context

            settings = _feature_model_settings("paper_review")
            if not settings["model"] or not settings["api_key"]:
                review_status = "unreviewed"
                review_error = "尚未配置可用的论文语义评审模型。"
                review_next_action = "请配置论文评审模型后重试；确定性候选已保留。"
            else:
                profile_version = hashlib.sha256(
                    json.dumps(result.profile.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()[:16]
                model_updates = {
                    "CONFLUX_MODELS__PAPER_REVIEW__PROVIDER": "openai_compatible",
                    "CONFLUX_MODELS__PAPER_REVIEW__MODEL": settings["model"],
                    "CONFLUX_MODELS__PAPER_REVIEW__BASE_URL": settings["base_url"],
                    "CONFLUX_MODELS__PAPER_REVIEW__API_KEY": settings["api_key"],
                    "CONFLUX_MODELS__PAPER_REVIEW__TEMPERATURE": str(settings["temperature"]),
                }
                review_candidates = [
                    paper.to_dict()
                    for paper, _analysis in result.analyzed[:review_limit]
                ]
                result.stats["llm_review_candidates"] = len(review_candidates)
                result.stats["llm_review_deferred"] = max(0, len(result.analyzed) - len(review_candidates))
                with config.override(model_updates):
                    ctx = make_plugin_context(config={"model_preset": "paper_review"})
                    review_result = paper_review(
                        ctx,
                        papers=review_candidates,
                        profile_id=result.profile.id,
                        profile_version=profile_version,
                        profile_keywords=result.profile.keywords,
                        profile_questions=result.profile.research_questions,
                        profile_fields=result.profile.fields,
                    )
                review_status = review_result.status.value
                review_error = review_result.error
                review_next_action = str(review_result.output.get("next_action") or "")
                for review in review_result.output.get("reviews") or []:
                    paper_id = str(review.get("paper_id") or "")
                    if paper_id:
                        llm_reviews[paper_id] = review
        except Exception as exc:
            review_status = "unreviewed"
            review_error = f"LLM review unavailable: {type(exc).__name__}: {exc}"
            review_next_action = "Configure a working review model and retry unreviewed papers."

    if llm_reviews:
        _apply_llm_reviews_to_inbox(result, llm_reviews)

    artifacts = result.artifacts
    papers_out = []
    for paper, analysis in result.analyzed:
        llm = llm_reviews.get(paper.id) or {}
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
        if llm:
            entry["llm_score"] = llm.get("semantic_score_percent", llm.get("semantic_score"))
            entry["llm_reason"] = llm.get("reasoning", "")
            entry["review_status"] = llm.get("review_status") or llm.get("relevance", "unreviewed")
            entry["relevance"] = llm.get("relevance", "unreviewed")
            entry["candidate_status"] = llm.get("candidate_status", "provisional")
            entry["review_error_code"] = llm.get("error_code", "")
            entry["review_error"] = llm.get("error_detail", "")
            entry["deep_review_status"] = llm.get("deep_review_status", "not_requested")
            entry["review_next_action"] = llm.get("next_action", "")
        papers_out.append(entry)
    papers = papers_out
    return {
        "ok": True,
        "profile_id": result.profile.id,
        "stats": result.stats,
        "papers": papers,
        "review_status": review_status,
        "review_error": review_error,
        "review_next_action": review_next_action,
        "markdown_path": _rel(artifacts.markdown_path) if artifacts else "",
        "json_path": _rel(artifacts.json_path) if artifacts else "",
    }


def save_model_config(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        tier_models = payload.get("tier_models") or {}
        if not isinstance(tier_models, dict):
            return {"ok": False, "error": "tier_models 必须是对象。"}
        feature_models = payload.get("feature_models") or {}
        if not isinstance(feature_models, dict):
            return {"ok": False, "error": "feature_models 必须是对象。"}
        count = save_workbench_env(
            base_url=str(payload.get("base_url") or "").strip(),
            api_key=str(payload.get("api_key") or "").strip(),
            model=str(payload.get("model") or "").strip(),
            tier_models={
                tier: dict(tier_models.get(tier) or {})
                for tier in ("quick", "standard", "deep")
            },
            feature_models={
                feature: dict(feature_models.get(feature) or {})
                for feature in _FEATURE_MODEL_FALLBACKS
            },
            embedding_base_url=str(payload.get("embedding_base_url") or "").strip(),
            embedding_api_key=str(payload.get("embedding_api_key") or "").strip(),
            embedding_model=str(payload.get("embedding_model") or "").strip(),
            web_search_provider=str(payload.get("web_search_provider") or "").strip(),
            serpapi_api_key=str(payload.get("serpapi_api_key") or "").strip(),
            bing_api_key=str(payload.get("bing_api_key") or "").strip(),
            google_api_key=str(payload.get("google_api_key") or "").strip(),
            google_cse_id=str(payload.get("google_cse_id") or "").strip(),
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

    try:
        with config.override(emb_updates):
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
    except EmbeddingIndexMismatchError as exc:
        return {
            "ok": False,
            "error": "embedding_index_mismatch",
            "reason": str(exc),
            "collection_name": exc.collection_name,
            "stored_model": exc.stored_model,
            "current_model": exc.current_model,
            "stored_dimension": exc.stored_dimension,
            "current_dimension": exc.current_dimension,
        }
    actions: dict[str, int] = {}
    for decision in result.decisions:
        actions[decision.action] = actions.get(decision.action, 0) + 1

    artifacts = result.artifacts
    promoted_papers = {
        str(document.metadata.get("paper_id") or "")
        for document in result.documents
        if (document.metadata or {}).get("content_scope") == "summary"
    } - {""}
    report_path = _write_paper_promotion_report(
        result,
        inbox=inbox,
        out_dir=out_dir,
    )
    _update_seen_after_promotion(result, inbox=inbox, indexed=do_index)
    _invalidate_expensive_cache("paper_ingestion_audit", "vector_store")
    return {
        "ok": True,
        "documents": len(result.documents),
        "papers": len(promoted_papers),
        "indexed": result.indexed_count,
        "decisions": actions,
        "documents_dir": _rel(artifacts.documents_dir) if artifacts else "",
        "manifest_path": _rel(artifacts.manifest_path) if artifacts else "",
        "sources_path": _rel(artifacts.sources_path) if artifacts else "",
        "report_path": _rel(report_path),
    }


def _update_seen_after_promotion(result: Any, *, inbox: str, indexed: bool) -> None:
    """Persist actual ingestion outcomes so failed full text remains selectable."""

    try:
        from conflux.knowledge.paper_indexer import load_inbox_payload

        records = {
            str(paper.id): paper
            for paper, _analysis in load_inbox_payload(inbox)
        }
        documents_by_paper: dict[str, list[dict[str, Any]]] = {}
        for document in result.documents:
            metadata = dict(document.metadata or {})
            paper_id = str(metadata.get("paper_id") or "")
            if paper_id:
                documents_by_paper.setdefault(paper_id, []).append(metadata)

        with _SEEN_PAPERS_LOCK:
            seen = _load_seen_papers()
            now = time.strftime("%Y-%m-%dT%H:%M:%S")
            for decision in result.decisions:
                paper_id = str(decision.paper_id or "")
                paper = records.get(paper_id)
                source = str(getattr(paper, "source", "") or "arxiv")
                identity = _paper_identity(source, paper_id)
                documents = documents_by_paper.get(paper_id) or []
                summary = next(
                    (item for item in documents if item.get("content_scope") == "summary"),
                    {},
                )
                full_text = [item for item in documents if item.get("content_scope") == "full_text"]
                if full_text and indexed:
                    status = "full_text_indexed"
                elif full_text:
                    status = "full_text_extracted"
                elif decision.action == "full_text":
                    status = "full_text_missing"
                elif summary and indexed:
                    status = "summary_indexed"
                elif summary:
                    status = "summary_saved"
                elif decision.action == "skip":
                    status = "skipped_by_policy"
                elif decision.action == "metadata_only":
                    status = "metadata_only"
                else:
                    status = "not_ingested"

                aliases = [key for key in seen if _canonical_seen_key(key) == identity] or [identity]
                for key in aliases:
                    entry = dict(seen.get(key) or {})
                    entry.update({
                        "status": status,
                        "at": now,
                        "title": str(getattr(paper, "title", "") or entry.get("title") or "")[:120],
                        "requested_action": str(decision.action or ""),
                        "full_text_status": str(summary.get("full_text_status") or ""),
                    })
                    seen[key] = entry
            _save_seen_papers(seen)
    except Exception:
        # Promotion artifacts remain valid even if the optional history file is unavailable.
        return


def _write_paper_promotion_report(result: Any, *, inbox: str, out_dir: str) -> Path:
    """Write one concise Chinese report for a complete promotion run."""

    report_dir = PROJECT_ROOT / "reports" / "workbench" / "papers"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = report_dir / f"paper_promotion_{stamp}.md"
    counter = 2
    while path.exists():
        path = report_dir / f"paper_promotion_{stamp}-{counter}.md"
        counter += 1
    action_labels = {
        "pinned": "用户强制收录",
        "full_text": "全文策略命中",
        "summary_only": "摘要策略命中",
        "metadata_only": "仅保留元数据",
        "skip": "跳过",
    }
    action_counts: dict[str, int] = {}
    for decision in result.decisions:
        action_counts[decision.action] = action_counts.get(decision.action, 0) + 1

    summaries: dict[str, dict[str, Any]] = {}
    paper_documents: dict[str, list[dict[str, Any]]] = {}
    for document in result.documents:
        metadata = document.metadata or {}
        paper_id = str(metadata.get("paper_id") or "未知 ID")
        paper_documents.setdefault(paper_id, []).append(metadata)
        if metadata.get("content_scope") != "summary":
            continue
        summaries[paper_id] = metadata

    lines = [
        "# 论文入库总结",
        "",
        f"- 入库时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 收件箱：`{_rel(inbox)}`",
        f"- 知识库目录：`{_rel(out_dir)}`",
        f"- 处理论文：{len(result.decisions)} 篇",
        f"- 实际写入：{len(summaries)} 篇",
        f"- 向量索引：{int(result.indexed_count)} 条",
        "",
        "## 处理结果",
        "",
    ]
    for action, count in sorted(action_counts.items()):
        lines.append(f"- {action_labels.get(action, action)}：{count} 篇")
    lines.extend(["", "## 已入库论文", ""])
    if summaries:
        for paper_id, metadata in summaries.items():
            title = str(metadata.get("paper_title") or "未命名论文")
            action = _actual_paper_ingestion_label(metadata, paper_documents.get(paper_id) or [])
            score = float(metadata.get("relevance_score") or 0)
            lines.append(f"- **{title}**（`{paper_id}`，{action}，相关度 {score:.3f}）")
    else:
        lines.append("- 本次没有论文达到知识文档写入条件。")
    lines.extend([
        "",
        "## 说明",
        "",
        "单篇论文的知识文档保存在知识库目录中，供检索和引用使用；研究成果页仅展示本次入库汇总。",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _actual_paper_ingestion_label(summary: dict[str, Any], documents: list[dict[str, Any]]) -> str:
    """Describe what was actually extracted and indexed, not the policy decision."""

    fulltext_docs = [item for item in documents if item.get("content_scope") == "full_text"]
    if any(item.get("full_text_indexed") for item in fulltext_docs):
        return "全文已提取并索引"
    if fulltext_docs or summary.get("full_text_extracted"):
        return "全文已提取，未建立向量索引"
    if summary.get("full_text_requested"):
        status = str(summary.get("full_text_status") or "unknown")
        if summary.get("full_text_downloaded"):
            return f"摘要回退（全文解析失败：{status}）"
        return f"摘要回退（全文未获取：{status}）"
    action = str(summary.get("ingestion_action") or "")
    return "用户强制收录（摘要）" if action == "pinned" else "摘要入库"


def run_model_probe(payload: dict[str, Any]) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completion endpoint."""

    preset = str(payload.get("model_preset") or "reasoning").strip()
    if preset in _FEATURE_MODEL_FALLBACKS:
        defaults = _feature_model_settings(preset)
        default_model = defaults["model"]
        default_base_url = defaults["base_url"]
        default_api_key = defaults["api_key"]
    else:
        default_model = _default_model_name(preset) or _default_model_name("reasoning")
        default_base_url = _default_base_url(preset) or _default_base_url("reasoning")
        default_api_key = _default_api_key(preset) or _default_api_key("reasoning")
    model = str(payload.get("model") or default_model).strip()
    base_url = str(payload.get("base_url") or default_base_url).strip()
    api_key = str(payload.get("api_key") or default_api_key).strip()
    prompt = str(payload.get("prompt") or "Reply with a short readiness check.").strip()
    temperature = float(payload.get("temperature") or 0.2)
    max_tokens = max(1, min(16384, int(payload.get("max_tokens") or 256)))

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
    if payload.get("json_mode"):
        body["response_format"] = {"type": "json_object"}
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
    started = time.perf_counter()
    try:
        from conflux.__main__ import query_command
        from conflux.core.contracts import RunContext

        state = query_command(
            query,
            mode=mode,
            output_dir=output_dir,
            stream_events=False,
            trace_dir=output_dir,
            run_id=run_id,
            run_context=RunContext(
                run_id=run_id,
                thread_id=run_id,
                workspace=str(PROJECT_ROOT),
                config_overrides=updates,
            ),
        )
    except SystemExit as exc:
        return {"ok": False, "run_id": run_id, "exit_code": exc.code, "stdout": ""}
    except Exception as exc:
        return {"ok": False, "run_id": run_id, "error": str(exc), "stdout": ""}

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return {
        "ok": True,
        "run_id": run_id,
        "elapsed_ms": elapsed_ms,
        "stdout": "",
        "final_answer": str(state.get("final_answer") or "")[:4000],
        "artifacts": state.get("_report_artifacts") or {},
    }


def run_progress_audit(payload: dict[str, Any]) -> dict[str, Any]:
    registered_id = str(payload.get("project_id") or "").strip()
    if registered_id:
        project = _project_registry().get(registered_id)
        if project is None:
            return {"ok": False, "error": f"未找到已登记项目：{registered_id}"}
        project_path = Path(project.path)
        audit_id = project.id
        result_dirs = project.result_dirs
        report_dirs = project.report_dirs
        configured_test = project.test_command
        configured_timeout = project.test_timeout_seconds
    else:
        project = None
        profile_path = Path(_path_value(payload.get("profile"), DEFAULT_PROFILE))
        profile = load_profile(profile_path)
        project_value = str(payload.get("project_path") or "").strip()
        if project_value:
            project_path = Path(project_value).expanduser().resolve()
        else:
            projects = profile.normalized_project_paths(profile_path.parent)
            if not projects:
                return {"ok": False, "error": "研究画像未配置项目路径，请先填写本地项目路径。"}
            project_path = projects[0]
        audit_id = profile.id
        result_dirs = ("results", "artifacts", "experiments")
        report_dirs = ("reports",)
        configured_test = ""
        configured_timeout = 120

    output_root = Path(_path_value(payload.get("out_dir"), DEFAULT_PROGRESS_DIR)) / audit_id
    snapshot_path = output_root / "project_snapshot.json"
    baseline = load_snapshot(snapshot_path)
    test_command = str(payload.get("test_command") or configured_test).strip() or None
    timeout = max(1, min(600, int(payload.get("test_timeout") or configured_timeout)))
    report = audit_project(
        project_path,
        baseline=baseline,
        project_id=audit_id,
        test_command=test_command,
        result_dirs=result_dirs,
        report_dirs=report_dirs,
        test_timeout_seconds=timeout,
    )
    artifacts = write_progress_artifacts(report, out_dir=output_root)
    if project is not None:
        _write_project_cache(project.id, monitor_project(
            project,
            audit_root=Path(_path_value(payload.get("out_dir"), DEFAULT_PROGRESS_DIR)),
            check_remote=False,
        ))
    return {
        "ok": True,
        "report": report.to_dict(),
        "markdown_path": str(artifacts.markdown_path),
        "json_path": str(artifacts.json_path),
        "snapshot_path": str(artifacts.snapshot_path),
    }


def build_projects_overview() -> dict[str, Any]:
    loaded = _project_registry().load_all()
    projects = []
    for project in loaded.projects:
        cached = _load_project_cache(project.id)
        if cached and (cached.get("project") or {}).get("path") == project.path:
            overview = monitor_project(
                project,
                audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
                check_remote=False,
            )
            overview["project"] = project.to_dict()
            cached_repository = cached.get("repository") or {}
            local_git = inspect_git_status(project.path)
            repository = overview.get("repository") or {}
            cached_remote_head = cached_repository.get("remote_head") or cached_repository.get("cached_remote_head") or ""
            repository.update({
                "is_repository": local_git.is_repository,
                "root": local_git.root,
                "branch": local_git.branch,
                "head": local_git.head,
                "dirty_files": local_git.dirty_files,
                "checked_at": local_git.checked_at,
                "errors": local_git.errors,
                "upstream": local_git.upstream,
                "ahead": local_git.ahead,
                "behind": local_git.behind,
                "remote_checked": False,
                "remote_head": "",
                "cached_remote_head": cached_remote_head,
                "remote_name": repository.get("remote_name") or cached_repository.get("remote_name") or "",
                "remote_url": repository.get("remote_url") or cached_repository.get("remote_url") or "",
                "remote_default_branch": repository.get("remote_default_branch") or cached_repository.get("remote_default_branch") or "",
                "remote_branch": repository.get("remote_branch") or cached_repository.get("remote_branch") or "",
            })
            if local_git.errors:
                repository["sync_status"] = "error"
            elif not local_git.is_repository:
                repository["sync_status"] = "not_applicable"
            elif local_git.ahead is None or local_git.behind is None:
                repository["sync_status"] = "unknown" if repository.get("remote_name") else "local_only"
            else:
                repository["sync_status"] = local_git.sync_status
            overview["repository"] = repository
            overview["plan_context"] = public_document_context(
                discover_plan_documents(project, max_files=24)
            )
            overview["alerts"] = [
                alert for alert in (overview.get("alerts") or [])
                if str((alert or {}).get("title") or "") not in {
                    "Git 状态读取失败",
                    "存在未提交变更",
                    "缺少项目纲领",
                }
            ]
            if local_git.errors:
                overview["alerts"].append({
                    "severity": "error",
                    "title": "Git 状态读取失败",
                    "detail": local_git.errors[0],
                })
            elif local_git.dirty_files:
                overview["alerts"].append({
                    "severity": "warning",
                    "title": "存在未提交变更",
                    "detail": f"本地工作区有 {len(local_git.dirty_files)} 个未提交文件。",
                })
            if (overview["plan_context"].get("charter") or {}).get("status") == "missing":
                overview["alerts"].append({
                    "severity": "warning",
                    "title": "缺少项目纲领",
                    "detail": "只读监控仍可使用，但智能计划分析的依据不足。可生成 PROJECT.md 草案后人工确认。",
                })
            severities = {alert.get("severity") for alert in overview["alerts"]}
            overview["health"] = (
                "error" if "error" in severities
                else "warning" if "warning" in severities
                else "info" if "info" in severities
                else "ok"
            )
        else:
            overview = monitor_project(
                project,
                audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
                check_remote=False,
            )
        overview["research"] = project.research
        projects.append(overview)
    return {
        "ok": True,
        "projects": projects,
        "registry_errors": loaded.errors,
        "registry_dir": str(PROJECT_ROOT / DEFAULT_PROJECTS_DIR),
        "refresh_mode": "manual",
        "scheduler_active": False,
    }


def refresh_projects(payload: dict[str, Any]) -> dict[str, Any]:
    loaded = _project_registry().load_all()
    project_id = str(payload.get("project_id") or "").strip()
    selected = [project for project in loaded.projects if not project_id or project.id == project_id]
    if project_id and not selected:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    refreshed = []
    for project in selected:
        overview = monitor_project(
            project,
            audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
            check_remote=True,
        )
        _write_project_cache(project.id, overview)
        refreshed.append(overview)
    return {
        "ok": True,
        "projects": refreshed,
        "registry_errors": loaded.errors,
        "refresh_mode": "manual",
        "scheduler_active": False,
    }


def save_registered_project(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    project_id = str(payload.get("id") or "").strip().lower()
    if not project_id:
        project_id = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
        project_id = project_id or f"project-{str(int(time.time()))[-8:]}"
    milestones = []
    for index, item in enumerate(payload.get("milestones") or [], start=1):
        if isinstance(item, dict):
            milestone = Milestone.from_dict(item)
        else:
            milestone = Milestone(id=f"milestone-{index}", title=str(item or "").strip())
        if milestone.title:
            milestone.id = milestone.id or f"milestone-{index}"
            milestones.append(milestone)
    project = ProjectDefinition(
        id=project_id,
        name=name,
        path=str(payload.get("path") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        document_dirs=_split_lines(payload.get("document_dirs")) or ["docs"],
        document_files=_split_lines(payload.get("document_files")) or ["README.md"],
        result_dirs=_split_lines(payload.get("result_dirs")) or ["results", "artifacts", "experiments"],
        report_dirs=_split_lines(payload.get("report_dirs")) or ["reports"],
        test_command=str(payload.get("test_command") or "").strip(),
        plan=ProjectPlan(
            overall_goal=str(payload.get("overall_goal") or "").strip(),
            milestones=milestones,
            next_actions=_split_lines(payload.get("next_actions")),
            source_documents=_split_lines(payload.get("source_documents")),
        ),
        refresh=RefreshPolicy(
            mode="manual",
            schedule_enabled=False,
            interval_minutes=None,
            timezone=str(payload.get("timezone") or "Asia/Shanghai").strip(),
        ),
    )
    path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    if saved is None:
        raise RuntimeError("项目配置已写入，但无法重新读取")
    if _p3_overview_enabled():
        # New page (U1 acceptance): establish the first snapshot immediately.
        p3_result = _refresh_p3_project_local(saved)
        return {
            "ok": True,
            "path": str(path),
            "project_id": saved.id,
            "revision": p3_result["revision"],
            "p3": p3_result,
        }
    overview = monitor_project(
        saved,
        audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
        check_remote=False,
    )
    _write_project_cache(project.id, overview)
    return {"ok": True, "path": str(path), "project": overview}


def suggest_project_plan(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    suggestions = extract_plan_suggestions(project)
    translation = {"requested": bool(payload.get("translate")), "translated": 0, "error": ""}
    if translation["requested"]:
        suggestions, translation = _translate_plan_suggestions(suggestions)
    return {
        "ok": True,
        "project_id": project.id,
        "suggestions": suggestions,
        "translation": translation,
        "message": "候选项不会自动写入权威项目配置，请确认后再编辑 YAML。",
    }


def _plan_analysis_context(project: ProjectDefinition) -> dict[str, Any]:
    context = discover_plan_documents(project)
    configured_sources = {
        str(path).replace("\\", "/").casefold()
        for path in project.plan.source_documents
    }
    if configured_sources:
        context["documents"] = [
            item for item in context.get("documents") or []
            if str(item.get("path") or "").replace("\\", "/").casefold() in configured_sources
            or item.get("kind") == "charter"
        ]
        normalized_warnings = []
        for warning in context.get("warnings") or []:
            normalized = str(warning).replace("\\", "/").casefold()
            if any(path in normalized for path in configured_sources):
                normalized_warnings.append(warning)
            elif "文档总上下文达到上限" in str(warning) and any(
                item.get("truncated") for item in context["documents"]
            ):
                normalized_warnings.append(warning)
        context["warnings"] = normalized_warnings
    return context


def analyze_project_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a reviewable LLM plan analysis without changing project files."""

    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "reason": f"未找到已登记项目：{project_id}", "error": "project_not_found"}

    context = _plan_analysis_context(project)
    public_context = public_document_context(context)
    if not context.get("documents"):
        return {
            "ok": False,
            "reason": "没有找到可供分析的 Markdown 项目文档，请先在项目设置中登记文档目录或根目录文档。",
            "error": json.dumps(public_context.get("warnings") or ["no_readable_documents"], ensure_ascii=False),
            "plan_context": public_context,
        }

    settings = _feature_model_settings("plan_analysis")
    model = settings["model"]
    base_url = settings["base_url"]
    api_key = settings["api_key"]
    if not model or not api_key:
        return {
            "ok": False,
            "reason": "尚未配置可用的计划分析模型，请先到“模型与环境”配置模型名称、URL 和 API Key。",
            "error": "missing_model_or_api_key",
            "plan_context": public_context,
        }

    overview = monitor_project(project, audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR, check_remote=False)
    evidence = build_evidence_catalog(project, overview)
    prompt = build_plan_prompt(project, context, evidence)
    result = run_model_probe({
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "prompt": prompt,
        "temperature": 0.1,
        "max_tokens": 12000,
        "timeout": 240,
        "json_mode": True,
    })
    if not result.get("ok"):
        return _plan_model_error(result, public_context)

    raw_content = str(result.get("content") or "")
    analysis_result = result
    repaired_once = False
    try:
        parsed = _parse_json_object(raw_content)
        analysis = normalize_plan_analysis(
            parsed,
            context=context,
            evidence=evidence,
            model=str(result.get("model") or model),
            code_revision=str((overview.get("repository") or {}).get("head") or ""),
        )
    except ValueError as first_error:
        repair_prompt = prompt + "\n\n上一次输出未通过校验：" + str(first_error) + (
            "\n请修复格式和内容后重新输出完整 JSON。上一次输出：\n" + raw_content[:20_000]
        )
        repaired = run_model_probe({
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "prompt": repair_prompt,
            "temperature": 0.0,
            "max_tokens": 12000,
            "timeout": 240,
            "json_mode": True,
        })
        if not repaired.get("ok"):
            return _plan_model_error(repaired, public_context, prefix="计划结构修复失败")
        try:
            parsed = _parse_json_object(str(repaired.get("content") or ""))
            analysis = normalize_plan_analysis(
                parsed,
                context=context,
                evidence=evidence,
                model=str(repaired.get("model") or model),
                code_revision=str((overview.get("repository") or {}).get("head") or ""),
            )
            analysis_result = repaired
            repaired_once = True
        except ValueError as second_error:
            return {
                "ok": False,
                "reason": "模型返回的计划结构不符合要求，已自动修复一次但仍无法使用。请检查项目文档或稍后重试。",
                "error": f"首次校验：{first_error}\n二次校验：{second_error}",
                "plan_context": public_context,
            }

    analysis["analysis"].update({
        "elapsed_ms": int(analysis_result.get("elapsed_ms") or 0),
        "usage": dict(analysis_result.get("usage") or {}),
        "repaired_once": repaired_once,
        "document_count": len(context.get("documents") or []),
    })
    analysis["diff"] = analysis_diff(project, analysis)
    path = _write_plan_analysis_cache(project.id, analysis)
    return {
        "ok": True,
        "project_id": project.id,
        "plan_context": public_context,
        "analysis": analysis,
        "cache_path": str(path),
        "message": "分析结果仅供审查，尚未修改项目计划。",
    }


def apply_project_plan_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply explicitly selected cached analysis items to authoritative YAML."""

    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    if payload.get("confirmed") is not True:
        return {"ok": False, "error": "写入计划前必须明确确认。"}
    analysis = _load_plan_analysis_cache(project.id)
    if analysis is None:
        return {"ok": False, "error": "计划分析缓存不存在，请重新运行分析。"}
    expected = str(payload.get("generated_at") or "")
    actual_generated = str((analysis.get("analysis") or {}).get("generated_at") or "")
    if not expected or expected != actual_generated:
        return {"ok": False, "error": "计划分析结果已变化，请重新审查后确认。"}

    current_context = _plan_analysis_context(project)
    current_hashes = {
        str(item.get("path")): str(item.get("sha256"))
        for item in current_context.get("documents") or []
    }
    if current_hashes != dict((analysis.get("analysis") or {}).get("source_hashes") or {}):
        return {"ok": False, "error": "项目文档在分析后发生变化，请重新运行计划分析。"}

    selected_ids = {str(value) for value in payload.get("selection_ids") or []}
    if not selected_ids:
        return {"ok": False, "error": "请至少选择一个总体目标、里程碑或后续计划。"}
    edits = payload.get("edits") if isinstance(payload.get("edits"), dict) else {}
    replace_existing = bool(payload.get("replace_existing", False))
    available = {str(item.get("id")): item for item in analysis.get("items") or []}
    unknown = selected_ids - set(available) - {"overall_goal"}
    if unknown:
        return {"ok": False, "error": "部分候选已失效，请重新运行计划分析。"}

    if replace_existing:
        if "overall_goal" in selected_ids:
            project.plan.overall_goal = ""
        project.plan.milestones = []
        project.plan.next_actions = []

    applied = {"overall_goal": 0, "milestones": 0, "next_actions": 0}
    if "overall_goal" in selected_ids:
        suggested = str((analysis.get("overall_goal") or {}).get("summary") or "").strip()
        edited = " ".join(str(edits.get("overall_goal") or suggested).split())[:800]
        if not edited:
            return {"ok": False, "error": "总体目标不能为空。"}
        project.plan.overall_goal = edited
        applied["overall_goal"] = 1

    milestone_titles = {item.title.casefold() for item in project.plan.milestones}
    action_titles = {item.casefold() for item in project.plan.next_actions}
    milestone_ids = {item.id for item in project.plan.milestones}
    chosen_items = [available[item_id] for item_id in selected_ids if item_id in available]
    for item in chosen_items:
        item_id = str(item.get("id"))
        title = " ".join(str(edits.get(item_id) or item.get("title") or "").split())[:500]
        if not title:
            return {"ok": False, "error": "计划标题不能为空。"}
        if item.get("type") == "milestone" and title.casefold() not in milestone_titles:
            base_id = re.sub(r"[^a-z0-9]+", "-", item_id.casefold()).strip("-") or "milestone"
            milestone_id = base_id
            counter = 2
            while milestone_id in milestone_ids:
                milestone_id = f"{base_id}-{counter}"
                counter += 1
            project.plan.milestones.append(Milestone(
                id=milestone_id,
                title=title,
                status=str(item.get("declared_status") or "planned"),
                description=str(item.get("summary") or ""),
                deliverables=list(item.get("acceptance_criteria") or []),
            ))
            milestone_titles.add(title.casefold())
            milestone_ids.add(milestone_id)
            applied["milestones"] += 1
        elif item.get("type") == "next_action" and title.casefold() not in action_titles:
            project.plan.next_actions.append(title)
            action_titles.add(title.casefold())
            applied["next_actions"] += 1
        for source in item.get("source_refs") or []:
            source_path = str(source.get("path") or "")
            if source_path and source_path not in project.plan.source_documents:
                project.plan.source_documents.append(source_path)

    for source in (analysis.get("overall_goal") or {}).get("source_refs") or []:
        if "overall_goal" not in selected_ids:
            break
        source_path = str(source.get("path") or "")
        if source_path and source_path not in project.plan.source_documents:
            project.plan.source_documents.append(source_path)
    project.plan.updated_at = time.strftime("%Y-%m-%d")
    path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    if saved is None:
        raise RuntimeError("项目计划已写入，但无法重新读取")
    overview = monitor_project(saved, audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR, check_remote=False)
    _write_project_cache(project.id, overview)
    return {"ok": True, "path": str(path), "applied": applied, "project": overview}


def generate_project_charter(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate and cache a PROJECT.md draft without writing into the project."""

    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "reason": f"未找到已登记项目：{project_id}", "error": "project_not_found"}
    context = discover_plan_documents(project)
    charter = context.get("charter") or {}
    if str(charter.get("path") or "").casefold() == "project.md":
        return {"ok": False, "reason": "项目中已经存在 PROJECT.md，无需生成新草案。", "error": "project_charter_exists"}
    settings = _feature_model_settings("project_charter")
    model = settings["model"]
    api_key = settings["api_key"]
    if not model or not api_key:
        return {
            "ok": False,
            "reason": "尚未配置可用的纲领生成模型，请先到“模型与环境”完成配置。",
            "error": "missing_model_or_api_key",
        }
    result = run_model_probe({
        "model": model,
        "base_url": settings["base_url"],
        "api_key": api_key,
        "prompt": charter_draft_prompt(project, context),
        "temperature": 0.2,
        "max_tokens": 5200,
        "timeout": 120,
    })
    if not result.get("ok"):
        return _plan_model_error(result, public_document_context(context), prefix="纲领草案生成失败")
    content = str(result.get("content") or "").strip()
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else content
        if content.lstrip().startswith("markdown"):
            content = content.lstrip()[8:].lstrip()
        elif content.lstrip().startswith("md"):
            content = content.lstrip()[2:].lstrip()
    if not content.startswith("#") or len(content) < 120:
        return {"ok": False, "reason": "模型没有返回可用的 PROJECT.md 草案，请稍后重试。", "error": content[:1200]}
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    draft = {
        "project_id": project.id,
        "path": "PROJECT.md",
        "content": content,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "model": str(result.get("model") or model),
        "generated_at": generated_at,
        "source_hashes": {str(item.get("path")): str(item.get("sha256")) for item in context.get("documents") or []},
    }
    path = _write_charter_draft_cache(project.id, draft)
    return {"ok": True, "draft": draft, "cache_path": str(path), "message": "草案尚未写入项目目录。"}


def apply_project_charter(payload: dict[str, Any]) -> dict[str, Any]:
    """Write a previously generated charter only after explicit confirmation."""

    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    if payload.get("confirmed") is not True:
        return {"ok": False, "error": "写入 PROJECT.md 前必须明确确认。"}
    draft = _load_charter_draft_cache(project.id)
    if draft is None:
        return {"ok": False, "error": "纲领草案缓存不存在，请重新生成。"}
    if str(payload.get("sha256") or "") != str(draft.get("sha256") or ""):
        return {"ok": False, "error": "纲领草案已变化，请重新预览后确认。"}
    root = Path(project.path).expanduser().resolve()
    target = (root / "PROJECT.md").resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "PROJECT.md 目标路径无效。"}
    if target.exists() and not bool(payload.get("overwrite", False)):
        return {"ok": False, "error": "PROJECT.md 已存在，未进行覆盖。"}
    content = str(payload.get("content") or draft.get("content") or "").strip()
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != str(draft.get("sha256") or ""):
        return {"ok": False, "error": "草案内容已被修改，请重新生成或按原草案确认。"}
    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    if "PROJECT.md" not in project.document_files:
        project.document_files.insert(0, "PROJECT.md")
    project.metadata["charter"] = {
        "path": "PROJECT.md",
        "generated_by": str(draft.get("model") or ""),
        "generated_at": str(draft.get("generated_at") or ""),
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    config_path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    overview = monitor_project(saved, audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR, check_remote=False) if saved else {}
    if saved:
        _write_project_cache(project.id, overview)
    return {"ok": True, "path": str(target), "config_path": str(config_path), "project": overview}


_persistent_worker_started = False
_persistent_worker_lock = threading.Lock()
_persistent_worker_thread: threading.Thread | None = None


def _research_database() -> SQLiteDatabase:
    db = SQLiteDatabase(database_path()).connect()
    db.bootstrap_schema()
    return db


def _project_research_context_version(project: ProjectDefinition, profile_path: Path) -> str:
    digest = hashlib.sha256()
    payload = project.to_dict(include_source=False)
    research = dict(payload.get("research") or {})
    for key in (
        "schedule_enabled", "interval_minutes", "schedule_timezone",
        "last_run_at", "next_run_at",
    ):
        research.pop(key, None)
    if research:
        payload["research"] = research
    else:
        payload.pop("research", None)
    digest.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    if profile_path.is_file():
        digest.update(profile_path.read_bytes())
    return digest.hexdigest()[:20]


def _resolve_project_profile(project: ProjectDefinition) -> tuple[Path | None, str]:
    if not project.research:
        return None, "项目尚未配置研究画像 (research 段)。请先在项目设置中添加。"
    profile_path = str(project.research.get("profile") or "")
    if not profile_path:
        return None, "未指定研究画像路径。"
    resolved = Path(profile_path)
    if not resolved.is_absolute():
        resolved = Path(project.path).expanduser().resolve() / resolved
    resolved = resolved.resolve()
    if not resolved.exists():
        return None, f"研究画像文件不存在：{resolved}"
    return resolved, ""


def run_project_research_radar(payload: dict[str, Any]) -> dict[str, Any]:
    """Enqueue a durable P2 paper-radar job for the Workbench."""
    project_id = str(payload.get("project_id") or "").strip()
    if not project_id:
        return {"ok": False, "error": "project_id required"}
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"项目未找到：{project_id}"}
    resolved, error = _resolve_project_profile(project)
    if resolved is None:
        return {"ok": False, "error": error}
    context_version = _project_research_context_version(project, resolved)
    db = _research_database()
    try:
        queue = JobQueue(db)
        job = queue.enqueue(
            "paper_radar",
            {
                "project_id": project_id,
                "periodic": False,
                "context_version": context_version,
                "work_item_id": str(payload.get("work_item_id") or ""),
                "gap_source": str(payload.get("gap_source") or ""),
            },
            idempotency_key=f"paper-radar:{project_id}:manual:{time.time_ns()}",
            max_attempts=2,
        )
    finally:
        db.close()
    _start_persistent_worker()
    return {
        "ok": True,
        "project_id": project_id,
        "job_id": job["job_id"],
        "status": job["status"],
        "status_url": f"/api/projects/research/jobs/{job['job_id']}",
    }


def _execute_project_research_radar(payload: dict[str, Any], *, job_id: str = "") -> dict[str, Any]:
    """Execute one claimed paper-radar job and persist its canonical state."""
    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"项目未找到：{project_id}"}
    resolved, error = _resolve_project_profile(project)
    if resolved is None:
        return {"ok": False, "error": error}

    try:
        from conflux.model_factory import create_chat_model
        from conflux.paper_radar.radar import run_paper_radar_from_profile
        from conflux.research_profile import load_profile

        settings = _feature_model_settings("research_radar")
        if not settings["model"] or not settings["api_key"]:
            return {"ok": False, "error": "尚未配置可用的研究雷达模型，请先到“模型与环境”完成配置。"}
        model_updates = {
            "CONFLUX_MODELS__RESEARCH_RADAR__PROVIDER": "openai_compatible",
            "CONFLUX_MODELS__RESEARCH_RADAR__MODEL": settings["model"],
            "CONFLUX_MODELS__RESEARCH_RADAR__BASE_URL": settings["base_url"],
            "CONFLUX_MODELS__RESEARCH_RADAR__API_KEY": settings["api_key"],
            "CONFLUX_MODELS__RESEARCH_RADAR__TEMPERATURE": str(settings["temperature"]),
        }
        profile = load_profile(str(resolved), validate=False)
        db = _research_database()
        try:
            seen_state = ProjectPaperStore(db).seen_statuses(project_id)
        finally:
            db.close()
        with config.override(model_updates):
            review_model = create_chat_model(
                "research_radar",
                max_tokens=4096,
                timeout=120,
                max_retries=0,
            )
            result = run_paper_radar_from_profile(
                project=project,
                profile_path=str(resolved),
                out_dir=str(PROJECT_ROOT / DEFAULT_PROGRESS_DIR / "workbench" / "projects"),
                llm_review=True,
                review_model=review_model,
                seen_state=seen_state,
                persist_seen_file=False,
            )

        all_sources_failed = bool(result.stats.sources_used) and set(result.stats.failed_sources) >= set(
            result.stats.sources_used
        )
        usable = not all_sources_failed and bool(result.links) and bool(result.stats.shortlisted)
        radar_status = (
            "source_failed"
            if all_sources_failed
            else "ready"
            if result.stats.shortlisted
            else "no_candidates"
            if not result.links
            else "no_shortlist"
        )
        radar_reason = (
            "所有已配置论文数据源均执行失败，请检查网络或数据源状态。"
            if all_sources_failed
            else ""
            if result.stats.shortlisted
            else "本轮没有检索到候选论文。"
            if not result.links
            else "本轮候选均未达到精读阈值，已保留供人工审查。"
        )

        cache = {
            "project_id": result.project_id,
            "work_item_id": str(payload.get("work_item_id") or ""),
            "gap_source": str(payload.get("gap_source") or ""),
            "usable": usable,
            "status": radar_status,
            "reason": radar_reason,
            "context": result.context.model_dump(),
            "intents": [i.model_dump() for i in result.intents],
            "queries": [q.model_dump() for q in result.queries],
            "links": [l.model_dump() for l in result.links],
            "suggestions": [s.model_dump() for s in result.suggestions],
            "stats": result.stats.model_dump(),
        }
        cache["stats"]["workbench_status"] = radar_status
        cache["stats"]["workbench_usable"] = usable
        cache["stats"]["workbench_reason"] = radar_reason
        _write_research_cache(project_id, cache, job_id=job_id)

        return {
            "ok": not all_sources_failed,
            "error": radar_reason if all_sources_failed else "",
            "usable": usable,
            "status": radar_status,
            "reason": radar_reason,
            "project_id": result.project_id,
            "intent_count": len(result.intents),
            "query_count": len(result.queries),
            "link_count": len(result.links),
            "candidate_count": len(result.links),
            "shortlisted_count": result.stats.shortlisted,
            "deep_read_count": result.stats.deep_read,
            "saved_count": sum(1 for l in result.links if l.status.value == "saved"),
            "sources": result.stats.sources_used,
            "failed_sources": result.stats.failed_sources,
            "elapsed": round(result.stats.elapsed_seconds, 2),
        }
    except Exception as exc:
        return {"ok": False, "error": f"雷达运行失败：{exc}"}


def get_project_research_status(project_id: str) -> dict[str, Any]:
    """Return persisted research radar results and durable schedule state."""
    cache = _load_research_cache(project_id)
    schedule = _project_research_schedule(project_id)
    active_job = _latest_project_radar_job(project_id, active_only=True)
    reviews = get_evidence_reviews(project_id=project_id).get("reviews", [])
    if cache is None:
        if active_job:
            return {
                "ok": True,
                "project_id": project_id,
                "status": active_job["status"],
                "job": active_job,
                "schedule": schedule,
                "evidence_reviews": reviews,
            }
        return {"ok": False, "error": "尚无雷达运行记录。", "schedule": schedule, "evidence_reviews": reviews}
    return {
        "ok": True,
        "project_id": project_id,
        **cache,
        "job": active_job,
        "schedule": schedule,
        "evidence_reviews": reviews,
    }


def get_evidence_reviews(*, project_id: str = "", status: str | None = "pending") -> dict[str, Any]:
    db = _research_database()
    try:
        reviews = EvidenceLedgerRepository(db).list_reviews(status=status)
    finally:
        db.close()
    if project_id:
        filtered = []
        for review in reviews:
            all_impacts = review.get("impacts") or []
            impacts = [
                item for item in all_impacts
                if str(item.get("project_id") or "") == project_id
            ]
            if impacts or not all_impacts:
                filtered.append({**review, "impacts": impacts})
        reviews = filtered
    return {"ok": True, "reviews": reviews, "count": len(reviews)}


def get_evidence_run(run_id: str) -> dict[str, Any] | None:
    db = _research_database()
    try:
        ledger = EvidenceLedgerRepository(db).run_ledger(run_id)
    finally:
        db.close()
    if not ledger["evidence"] and not ledger["claims"]:
        return None
    return {"ok": True, **ledger}


def resolve_evidence_review(payload: dict[str, Any]) -> dict[str, Any]:
    review_id = str(payload.get("review_id") or "").strip()
    status = str(payload.get("status") or "confirmed").strip()
    if not review_id:
        return {"ok": False, "error": "review_id required"}
    db = _research_database()
    try:
        updated = EvidenceLedgerRepository(db).resolve_review(review_id, status=status)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
    return {"ok": updated, "review_id": review_id, "status": status}


_research_cache: dict[str, dict[str, Any]] = {}


def _write_research_cache(project_id: str, cache: dict[str, Any], *, job_id: str = "") -> None:
    """Compatibility adapter that imports a result-shaped payload into SQLite."""
    _research_cache[project_id] = cache
    db = _research_database()
    try:
        db.connection.execute("BEGIN IMMEDIATE")
        intent_store = SearchIntentStore(db)
        link_store = ProjectPaperStore(db)
        for intent in cache.get("intents") or []:
            item = dict(intent)
            item["project_id"] = project_id
            intent_store.upsert(item, commit=False)
        links = []
        for link in cache.get("links") or []:
            item = dict(link)
            item["project_id"] = project_id
            persisted = link_store.upsert(item, preserve_status=True, commit=False)
            item["status"] = persisted["status"]
            links.append(item)
        payload = dict(cache)
        payload["project_id"] = project_id
        payload["links"] = links
        stats = dict(payload.get("stats") or {})
        stats["run_id"] = str(stats.get("run_id") or cache.get("run_id") or f"workbench-{time.time_ns()}")
        stats["project_id"] = project_id
        payload["stats"] = stats
        SearchRunStore(db).save_result(payload, job_id=job_id, commit=False)
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise
    finally:
        db.close()


def _load_research_cache(project_id: str) -> dict[str, Any] | None:
    db = _research_database()
    try:
        run_store = SearchRunStore(db)
        run = run_store.latest(project_id)
        if run is None:
            return None
        persisted_links = {
            item["paper_key"]: item for item in ProjectPaperStore(db).list(project_id)
        }
        links = []
        for link in run_store.candidates(run["run_id"]):
            identity = link.get("paper_identity") or {}
            canonical_id = str(identity.get("canonical_id") or "").strip()
            if not canonical_id:
                continue
            doi = str(identity.get("doi") or "").strip().casefold()
            key = f"doi:{doi}" if doi else f"{str(identity.get('source') or 'unknown').casefold()}:{canonical_id}"
            if key in persisted_links:
                link["status"] = persisted_links[key]["status"]
            links.append(link)
        stats = run.get("stats") or {}
        return {
            "project_id": project_id,
            "run_id": run["run_id"],
            "usable": bool(stats.get("workbench_usable", bool(links))),
            "status": str(stats.get("workbench_status") or run["status"]),
            "reason": str(stats.get("workbench_reason") or run.get("error") or ""),
            "context": run.get("context") or {},
            "intents": run_store.intents(run["run_id"]),
            "queries": run.get("queries") or [],
            "links": links,
            "suggestions": run.get("suggestions") or [],
            "stats": stats,
        }
    finally:
        db.close()


# ── Phase E: Paper list, actions, and coverage ─────────────────────

def get_project_research_papers(project_id: str) -> dict[str, Any]:
    """Return the paper list with link status for a project's research tab."""
    cache = _load_research_cache(project_id)
    if cache is None:
        return {"ok": False, "error": "尚无雷达运行记录。"}

    links = cache.get("links") or []
    papers: list[dict[str, Any]] = []
    for link in links:
        papers.append({
            "paper_key": link.get("paper_key", ""),
            "paper_id": (link.get("paper_identity") or {}).get("canonical_id", ""),
            "doi": (link.get("paper_identity") or {}).get("doi", ""),
            "source": (link.get("paper_identity") or {}).get("source", ""),
            "status": link.get("status", "discovered"),
            "relevance": link.get("relevance", 0.0),
            "evidence_utility": link.get("evidence_utility", "none"),
            "matched_intent_ids": link.get("matched_intent_ids", []),
        })

    return {
        "ok": True,
        "project_id": project_id,
        "papers": papers,
        "total": len(papers),
        "sources": (cache.get("stats") or {}).get("sources_used", []),
    }


def apply_paper_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply a user action: save, ignore, shortlist, or promote."""
    project_id = str(payload.get("project_id") or "").strip()
    paper_key = str(payload.get("paper_key") or payload.get("paper_id") or "").strip()
    action = str(payload.get("action") or "").strip().lower()

    valid_actions = {"save", "ignore", "shortlist", "promote", "reject"}
    if action not in valid_actions:
        return {"ok": False, "error": f"无效操作：{action}。支持：{', '.join(sorted(valid_actions))}"}

    status_map = {
        "save": "saved", "ignore": "rejected", "shortlist": "shortlisted",
        "promote": "promoted", "reject": "rejected",
    }
    db = _research_database()
    try:
        updated = ProjectPaperStore(db).update_status(
            project_id, paper_key, status_map.get(action, "needs_review")
        )
    finally:
        db.close()
    if not updated:
        return {"ok": False, "error": f"论文身份不存在或不唯一：{paper_key}"}
    _research_cache.pop(project_id, None)
    return {
        "ok": True,
        "project_id": project_id,
        "paper_key": paper_key,
        "action": action,
        "new_status": status_map.get(action),
    }


def get_project_research_job(job_id: str) -> dict[str, Any] | None:
    db = _research_database()
    try:
        return JobQueue(db).get(job_id)
    finally:
        db.close()


def configure_project_research_schedule(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"项目未找到：{project_id}"}
    enabled = bool(payload.get("enabled", False))
    try:
        interval_minutes = max(1, int(payload.get("interval_minutes") or 1440))
    except (TypeError, ValueError):
        return {"ok": False, "error": "interval_minutes 必须是正整数。"}
    original_research = dict(project.research) if project.research is not None else None
    research = dict(project.research or {})
    research["schedule_enabled"] = enabled
    research["interval_minutes"] = interval_minutes
    research["schedule_timezone"] = str(payload.get("timezone") or research.get("schedule_timezone") or "Asia/Shanghai")
    if enabled:
        next_run_at = time.time() + interval_minutes * 60
        research["next_run_at"] = _iso_utc(next_run_at)
        project.research = research
    else:
        research["next_run_at"] = ""
        project.research = research if project.research is not None else None

    if enabled:
        resolved, error = _resolve_project_profile(project)
        if resolved is None:
            project.research = original_research
            return {"ok": False, "error": error}

    source_path = Path(project.source_file) if project.source_file else None
    original_bytes = source_path.read_bytes() if source_path and source_path.is_file() else None
    saved_path: Path | None = None
    db = _research_database()
    try:
        db.connection.execute("BEGIN IMMEDIATE")
        _cancel_project_radar_jobs(project_id, periodic_only=True, db=db, commit=False)
        job = (
            _enqueue_periodic_project_radar(project, next_run_at, db=db, commit=False)
            if enabled else None
        )
        if project.research is not None:
            saved_path = _project_registry().save(project)
        db.connection.commit()
    except Exception as exc:
        db.connection.rollback()
        project.research = original_research
        try:
            if original_bytes is not None and source_path is not None:
                source_path.write_bytes(original_bytes)
            elif saved_path is not None and saved_path.exists():
                saved_path.unlink()
        except OSError:
            pass
        return {"ok": False, "error": f"周期任务保存失败：{exc}"}
    finally:
        db.close()
    if enabled:
        _start_persistent_worker()
    return {"ok": True, "project_id": project_id, "schedule": _project_research_schedule(project_id), "job": job}


def _project_research_schedule(project_id: str) -> dict[str, Any]:
    project = _project_registry().get(project_id)
    research = dict(project.research or {}) if project else {}
    try:
        interval_minutes = max(1, int(research.get("interval_minutes") or 1440))
    except (TypeError, ValueError):
        interval_minutes = 1440
    return {
        "enabled": bool(research.get("schedule_enabled", False)),
        "interval_minutes": interval_minutes,
        "timezone": str(research.get("schedule_timezone") or "Asia/Shanghai"),
        "last_run_at": str(research.get("last_run_at") or ""),
        "next_run_at": str(research.get("next_run_at") or ""),
    }


def _enqueue_periodic_project_radar(
    project: ProjectDefinition,
    scheduled_at: float,
    *,
    db: SQLiteDatabase | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    resolved, error = _resolve_project_profile(project)
    if resolved is None:
        raise ValueError(error)
    context_version = _project_research_context_version(project, resolved)
    key = f"paper-radar:{project.id}:{context_version}:periodic:{int(scheduled_at)}"
    owns_db = db is None
    db = db or _research_database()
    try:
        return JobQueue(db).enqueue(
            "paper_radar",
            {"project_id": project.id, "periodic": True, "context_version": context_version},
            idempotency_key=key,
            scheduled_at=scheduled_at,
            max_attempts=3,
            commit=commit,
        )
    finally:
        if owns_db:
            db.close()


def _cancel_project_radar_jobs(
    project_id: str,
    *,
    periodic_only: bool,
    db: SQLiteDatabase | None = None,
    commit: bool = True,
) -> None:
    owns_db = db is None
    db = db or _research_database()
    try:
        queue = JobQueue(db)
        for job in queue.list(kind="paper_radar", limit=500):
            payload = job.get("payload") or {}
            if payload.get("project_id") != project_id:
                continue
            if periodic_only and not payload.get("periodic"):
                continue
            if job["status"] == "pending":
                queue.cancel(job["job_id"], commit=commit)
    finally:
        if owns_db:
            db.close()


def _latest_project_radar_job(project_id: str, *, active_only: bool = False) -> dict[str, Any] | None:
    db = _research_database()
    try:
        jobs = JobQueue(db).list(kind="paper_radar", limit=200)
    finally:
        db.close()
    for job in reversed(jobs):
        if (job.get("payload") or {}).get("project_id") != project_id:
            continue
        if active_only and job["status"] not in {"pending", "running"}:
            continue
        return job
    return None


def _start_persistent_worker() -> None:
    global _persistent_worker_started, _persistent_worker_thread
    with _persistent_worker_lock:
        if _persistent_worker_thread is not None and _persistent_worker_thread.is_alive():
            return
        _persistent_worker_started = True

    def _loop() -> None:
        worker_id = f"workbench-{os.getpid()}"
        next_reconcile_at = 0.0
        while True:
            try:
                if time.time() >= next_reconcile_at:
                    _reconcile_project_radar_schedules()
                    next_reconcile_at = time.time() + 30.0
                worked = _run_one_persistent_job(worker_id)
                time.sleep(0.2 if worked else 1.0)
            except Exception:
                time.sleep(1.0)

    thread = threading.Thread(target=_loop, daemon=True, name="conflux-persistent-jobs")
    _persistent_worker_thread = thread
    thread.start()


def _reconcile_project_radar_schedules() -> int:
    """Restore a missing periodic job from the YAML schedule authority."""
    projects = _project_registry().load_all().projects
    db = _research_database()
    try:
        jobs = JobQueue(db).list(kind="paper_radar", limit=500)
        active_projects = {
            str((job.get("payload") or {}).get("project_id") or "")
            for job in jobs
            if job["status"] in {"pending", "running"}
            and (job.get("payload") or {}).get("periodic")
        }
        restored = 0
        for project in projects:
            research = dict(project.research or {})
            if not research.get("schedule_enabled") or project.id in active_projects:
                continue
            next_run_text = str(research.get("next_run_at") or "").strip()
            try:
                scheduled_at = float(calendar.timegm(time.strptime(next_run_text, "%Y-%m-%dT%H:%M:%SZ")))
            except (TypeError, ValueError, OverflowError):
                scheduled_at = float(int(time.time() // 60) * 60)
            _enqueue_periodic_project_radar(project, scheduled_at, db=db)
            active_projects.add(project.id)
            restored += 1
        return restored
    finally:
        db.close()


def _run_one_persistent_job(worker_id: str) -> bool:
    db = _research_database()
    try:
        queue = JobQueue(db, lease_seconds=60)
        expired = queue.expire_exhausted(kind="paper_radar")
        job = queue.claim(worker_id, kind="paper_radar")
    finally:
        db.close()
    for expired_job in expired:
        expired_payload = expired_job.get("payload") or {}
        if expired_payload.get("periodic"):
            _advance_project_radar_schedule(str(expired_payload.get("project_id") or ""))
    if job is None:
        return bool(expired)
    stop_heartbeat = threading.Event()

    def _heartbeat() -> None:
        while not stop_heartbeat.wait(20):
            heartbeat_db = _research_database()
            try:
                JobQueue(heartbeat_db, lease_seconds=60).heartbeat(job["job_id"], worker_id)
            finally:
                heartbeat_db.close()

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        result = _execute_project_research_radar(job.get("payload") or {}, job_id=job["job_id"])
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "paper radar failed"))
        complete_db = _research_database()
        try:
            completed = JobQueue(complete_db).complete(job["job_id"], worker_id, result=result)
        finally:
            complete_db.close()
        if completed and (job.get("payload") or {}).get("periodic"):
            _advance_project_radar_schedule(str((job.get("payload") or {}).get("project_id") or ""))
    except Exception as exc:
        fail_db = _research_database()
        try:
            queue = JobQueue(fail_db)
            failed = queue.fail(job["job_id"], worker_id, str(exc), retry_delay=30)
            failed_job = queue.get(job["job_id"]) if failed else None
        finally:
            fail_db.close()
        if (
            failed_job is not None
            and failed_job["status"] == "failed"
            and (job.get("payload") or {}).get("periodic")
        ):
            _advance_project_radar_schedule(str((job.get("payload") or {}).get("project_id") or ""))
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
    return True


def _advance_project_radar_schedule(project_id: str) -> bool:
    project = _project_registry().get(project_id)
    if project is None or not project.research:
        return False
    research = dict(project.research)
    if not research.get("schedule_enabled"):
        return False
    interval_minutes = max(1, int(research.get("interval_minutes") or 1440))
    now = time.time()
    next_run_at = now + interval_minutes * 60
    research["last_run_at"] = _iso_utc(now)
    research["next_run_at"] = _iso_utc(next_run_at)
    original_research = dict(project.research)
    project.research = research
    source_path = Path(project.source_file) if project.source_file else None
    original_bytes = source_path.read_bytes() if source_path and source_path.is_file() else None
    saved_path: Path | None = None
    db = _research_database()
    try:
        db.connection.execute("BEGIN IMMEDIATE")
        _enqueue_periodic_project_radar(project, next_run_at, db=db, commit=False)
        saved_path = _project_registry().save(project)
        db.connection.commit()
        return True
    except Exception:
        db.connection.rollback()
        project.research = original_research
        try:
            if original_bytes is not None and source_path is not None:
                source_path.write_bytes(original_bytes)
            elif saved_path is not None and saved_path.exists():
                saved_path.unlink()
        except OSError:
            pass
        return False
    finally:
        db.close()


def _iso_utc(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


def get_project_research_coverage(project_id: str) -> dict[str, Any]:
    """Return coverage matrix: intent × evidence utility."""
    cache = _load_research_cache(project_id)
    if cache is None:
        return {"ok": False, "error": "尚无雷达运行记录。"}

    links = cache.get("links") or []
    intents = cache.get("intents") or []

    rows: dict[str, int] = {}
    for link in links:
        utility = link.get("evidence_utility", "none")
        if utility == "none":
            continue
        for iid in link.get("matched_intent_ids", []):
            key = f"{iid[:8]}×{utility}"
            rows[key] = rows.get(key, 0) + 1

    return {
        "ok": True,
        "project_id": project_id,
        "intent_count": len(intents),
        "coverage": [{"key": k, "count": v} for k, v in sorted(rows.items())],
        "total_links": len(links),
        "covered_papers": len({
            (link.get("paper_identity") or {}).get("canonical_id", "")
            for link in links if link.get("evidence_utility") != "none"
        }),
    }


def _plan_model_error(result: dict[str, Any], plan_context: dict[str, Any], *, prefix: str = "计划分析失败") -> dict[str, Any]:
    detail = str(result.get("error") or "模型调用失败")
    status = int(result.get("status") or 0)
    if status == 429 or "429" in detail or "rate limit" in detail.casefold():
        reason = "搜索或分析请求过于频繁，已被模型服务限流，建议稍后再试。"
    elif "API key" in detail or "401" in detail or status == 401:
        reason = "模型凭证无效或已失效，请到“模型与环境”检查 API Key。"
    elif status >= 500:
        reason = "模型服务暂时不可用，建议稍后重试或切换已配置的模型 URL。"
    else:
        reason = f"{prefix}，请检查模型配置和网络连接后重试。"
    return {"ok": False, "reason": reason, "error": detail, "plan_context": plan_context}


def _translate_plan_suggestions(suggestions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Translate English plan candidates in one reviewable model request."""

    pending = [
        {"index": index, "title": str(item.get("title") or "")[:300]}
        for index, item in enumerate(suggestions)
        if item.get("title") and not re.search(r"[\u3400-\u9fff]", str(item.get("title")))
    ][:40]
    if not pending:
        return suggestions, {"requested": True, "translated": 0, "error": ""}

    prompt = """你是研究项目计划翻译助手。请把以下英文项目目标、里程碑或后续计划准确翻译成简体中文。
要求：保留文件名、命令、模型名和技术缩写；不要补充原文没有的结论；使用适合作为项目计划条目的简洁表达。
只返回 JSON 对象，结构为：{"translations":[{"index":0,"title":"中文"}]}。

待翻译内容：
""" + json.dumps(pending, ensure_ascii=False)
    settings = _feature_model_settings("plan_translation")
    result = run_model_probe({
        "model": settings["model"],
        "base_url": settings["base_url"],
        "api_key": settings["api_key"],
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": 3200,
        "timeout": 90,
        "json_mode": True,
    })
    if not result.get("ok"):
        error = str(result.get("error") or "翻译模型不可用")
        if "API key" in error:
            error = "未配置可用的翻译模型凭证，候选已保留原文。"
        return suggestions, {"requested": True, "translated": 0, "error": error}

    try:
        payload = _parse_json_object(str(result.get("content") or ""))
    except ValueError as exc:
        return suggestions, {"requested": True, "translated": 0, "error": str(exc)}
    translations = payload.get("translations") or []
    translated_count = 0
    values = [dict(item) for item in suggestions]
    for item in translations:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        title = " ".join(str(item.get("title") or "").split())[:300]
        if not (0 <= index < len(values)) or not title:
            continue
        original = str(values[index].get("title") or "")
        values[index]["original_title"] = original
        values[index]["title"] = title
        translated_count += 1
    return values, {"requested": True, "translated": translated_count, "error": ""}


def update_registered_project_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Update editable project settings while preserving its plan and schedule."""

    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}

    name = str(payload.get("name") or "").strip()
    path_value = str(payload.get("path") or "").strip()
    if not name or not path_value:
        return {"ok": False, "error": "项目名称和本地目录不能为空。"}
    project.name = name
    project.path = path_value
    project.description = str(payload.get("description") or "").strip()
    project.test_command = str(payload.get("test_command") or "").strip()
    project.document_dirs = _split_lines(payload.get("document_dirs")) or ["docs"]
    project.document_files = _split_lines(payload.get("document_files")) or ["README.md"]
    project.result_dirs = _split_lines(payload.get("result_dirs")) or ["results", "artifacts", "experiments"]
    project.report_dirs = _split_lines(payload.get("report_dirs")) or ["reports"]

    config_path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    if saved is None:
        raise RuntimeError("项目配置已写入，但无法重新读取")
    overview = monitor_project(
        saved,
        audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
        check_remote=False,
    )
    _write_project_cache(project.id, overview)
    return {"ok": True, "path": str(config_path), "project": overview}


def apply_project_plan_suggestions(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}

    selections = payload.get("selections") or []
    if not isinstance(selections, list) or not selections:
        return {"ok": False, "error": "请至少选择一个计划候选。"}
    if len(selections) > 40:
        return {"ok": False, "error": "单次最多确认 40 个计划候选。"}

    available = {
        (str(item.get("source_path") or ""), int(item.get("line") or 0))
        for item in extract_plan_suggestions(project)
    }
    normalized = []
    for item in selections:
        if not isinstance(item, dict):
            continue
        type_ = str(item.get("type") or "").strip()
        title = " ".join(str(item.get("title") or "").split())[:500]
        source_path = str(item.get("source_path") or "").strip()
        try:
            line = int(item.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        if type_ not in {"overall_goal", "milestone", "next_action"}:
            return {"ok": False, "error": f"不支持的候选类型：{type_}"}
        if not title:
            return {"ok": False, "error": "候选内容不能为空。"}
        if (source_path, line) not in available:
            return {"ok": False, "error": f"候选来源已变化，请重新提取：{source_path}:{line}"}
        normalized.append((type_, title, source_path))

    overall_goals = [title for type_, title, _ in normalized if type_ == "overall_goal"]
    if len(overall_goals) > 1:
        return {"ok": False, "error": "总体目标只能选择一项。"}

    applied = {"overall_goal": 0, "milestones": 0, "next_actions": 0}
    if overall_goals:
        project.plan.overall_goal = overall_goals[0]
        applied["overall_goal"] = 1

    existing_milestones = {item.title.casefold() for item in project.plan.milestones}
    existing_actions = {item.casefold() for item in project.plan.next_actions}
    existing_ids = {item.id for item in project.plan.milestones}
    for type_, title, _ in normalized:
        if type_ == "milestone" and title.casefold() not in existing_milestones:
            base_id = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "milestone"
            milestone_id = base_id
            counter = 2
            while milestone_id in existing_ids:
                milestone_id = f"{base_id}-{counter}"
                counter += 1
            project.plan.milestones.append(Milestone(id=milestone_id, title=title, status="planned"))
            existing_milestones.add(title.casefold())
            existing_ids.add(milestone_id)
            applied["milestones"] += 1
        elif type_ == "next_action" and title.casefold() not in existing_actions:
            project.plan.next_actions.append(title)
            existing_actions.add(title.casefold())
            applied["next_actions"] += 1

    for _, _, source_path in normalized:
        if source_path not in project.plan.source_documents:
            project.plan.source_documents.append(source_path)
    project.plan.updated_at = time.strftime("%Y-%m-%d")
    path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    if saved is None:
        raise RuntimeError("项目计划已写入，但无法重新读取")
    overview = monitor_project(
        saved,
        audit_root=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
        check_remote=False,
    )
    _write_project_cache(project.id, overview)
    return {
        "ok": True,
        "path": str(path),
        "applied": applied,
        "project": overview,
    }


def _project_registry() -> ProjectRegistry:
    return ProjectRegistry(PROJECT_ROOT / DEFAULT_PROJECTS_DIR, base_dir=PROJECT_ROOT)


def _project_cache_path(project_id: str) -> Path:
    safe_id = re.sub(r"[^a-z0-9-]", "", str(project_id).casefold())
    if not safe_id:
        raise ValueError("项目 ID 无效")
    return PROJECT_ROOT / DEFAULT_PROJECT_CACHE_DIR / f"{safe_id}.json"


def _load_project_cache(project_id: str) -> dict[str, Any] | None:
    path = _project_cache_path(project_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_project_cache(project_id: str, payload: dict[str, Any]) -> Path:
    path = _project_cache_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _project_analysis_dir(project_id: str) -> Path:
    safe_id = re.sub(r"[^a-z0-9-]", "", str(project_id).casefold())
    if not safe_id:
        raise ValueError("项目 ID 无效")
    return PROJECT_ROOT / DEFAULT_PROJECT_CACHE_DIR / safe_id


def _write_plan_analysis_cache(project_id: str, payload: dict[str, Any]) -> Path:
    path = _project_analysis_dir(project_id) / "plan_analysis.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_plan_analysis_cache(project_id: str) -> dict[str, Any] | None:
    path = _project_analysis_dir(project_id) / "plan_analysis.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_charter_draft_cache(project_id: str, payload: dict[str, Any]) -> Path:
    path = _project_analysis_dir(project_id) / "charter_draft.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_charter_draft_cache(project_id: str) -> dict[str, Any] | None:
    path = _project_analysis_dir(project_id) / "charter_draft.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


# ── P3.3 snapshot-driven project page (plan §7/§11.5) ────────────────────
#
# Every GET below reads only the registry YAML and materialized SQLite state.
# No monitor_project, no model, no tests, no remote calls on page reads
# (plan §P3.3 acceptance).  Refresh is an explicit local POST.


def _p3_overview_enabled() -> bool:
    """Feature flag; set CONFLUX_P3_OVERVIEW=0 to roll back to the legacy page."""
    return os.environ.get("CONFLUX_P3_OVERVIEW", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }


def _project_intelligence() -> ProjectIntelligence:
    """Fresh per-call connection — same threading pattern as _research_database."""
    db = _research_database()
    intelligence = ProjectIntelligence(db)
    intelligence.ensure_schema()
    return intelligence


def _p3_project_or_none(project_id: str) -> ProjectDefinition | None:
    return _project_registry().get(project_id)


def build_p3_projects() -> dict[str, Any]:
    """P3.3 project list — registry + materialized snapshot, zero scanning."""
    loaded = _project_registry().load_all()
    intelligence = _project_intelligence()
    projects = []
    try:
        for project in loaded.projects:
            current = intelligence.snapshots.current(project.id)
            pending = intelligence.reviews.list(project.id, status="pending")
            knowledge = (current or {}).get("knowledge_state") or {}
            projects.append({
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "enabled": project.enabled,
                "revision": (current or {}).get("revision", 0),
                "snapshot_id": (current or {}).get("snapshot_id", ""),
                "updated_at": (current or {}).get("updated_at", 0.0),
                "health": (current or {}).get("health", "unknown"),
                "pending_reviews": len(pending),
                "documents_total": int((knowledge.get("documents") or {}).get("total") or 0),
            })
        return {
            "ok": True,
            "projects": projects,
            "registry_errors": loaded.errors,
            "registry_dir": str(PROJECT_ROOT / DEFAULT_PROJECTS_DIR),
            "protocol_version": P3_PROTOCOL_VERSION,
        }
    finally:
        intelligence.db.close()


def _unified_reviews(
    project_id: str,
    intelligence: ProjectIntelligence,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Unified inbox: project_reviews + bridged Evidence Ledger reviews."""
    merged: list[dict[str, Any]] = []
    for review in intelligence.reviews.list(project_id, status=status):
        merged.append({
            "review_id": review.review_id,
            "source": "project",
            "project_id": review.project_id,
            "kind": review.kind.value,
            "priority": review.priority,
            "status": review.status.value,
            "summary": review.summary,
            "impact_refs": review.impact_refs,
            "evidence_refs": review.evidence_refs,
            "proposed_action": review.proposed_action,
            "input_snapshot_id": review.input_snapshot_id,
            "created_at": review.created_at,
            "resolved_at": review.resolved_at,
        })
    try:
        evidence = get_evidence_reviews(project_id=project_id, status=status)
    except Exception:
        evidence = {"ok": False, "reviews": []}
    # Map ledger impacts (claims) to the work items whose evidence refs
    # reference those claims (P3.4: evidence ledger -> work items).
    claim_to_item: dict[str, tuple[str, str]] = {}
    current = intelligence.snapshots.current(project_id)
    for item in (current or {}).get("work_items") or []:
        for ref in (item.get("evidence_refs") or []):
            if ref.startswith("claim:"):
                claim_id = ref[len("claim:"):].split(":", 1)[0]
                claim_to_item[claim_id] = (
                    str(item.get("work_item_id") or ""),
                    str(item.get("title") or ""),
                )
    for review in (evidence or {}).get("reviews") or []:
        rid = str(review.get("review_id") or "")
        if not rid:
            continue
        linked_items: set[tuple[str, str]] = set()
        for impact in (review.get("impacts") or []):
            if str(impact.get("target_kind") or "") != "claim":
                continue
            target = str(impact.get("target_id") or "")
            if target in claim_to_item:
                linked_items.add(claim_to_item[target])
        merged.append({
            "review_id": f"ev:{rid}",
            "source": "evidence_ledger",
            "project_id": project_id,
            "kind": "evidence_change",
            "priority": 65,
            "status": str(review.get("status") or "pending"),
            "summary": f"证据来源变化：{str(review.get('source_identity') or '未知来源')}",
            "impact_refs": [
                str(item.get("target_id") or "") for item in (review.get("impacts") or [])
            ],
            "evidence_refs": [],
            "proposed_action": "复核来源变化对 claim/报告的影响，确认或忽略",
            "input_snapshot_id": "",
            "created_at": 0.0,
            "resolved_at": 0.0,
            "work_items": [
                {"work_item_id": item_id, "title": title}
                for item_id, title in sorted(linked_items)
            ],
            "detail": {
                "source_identity": review.get("source_identity"),
                "reason": review.get("reason"),
                "impacts": review.get("impacts"),
            },
        })
    merged.sort(key=lambda item: (-int(item["priority"]), -(item["created_at"] or 0)))
    return merged


def _p3_radar_summary(project_id: str) -> dict[str, Any]:
    cache = _load_research_cache(project_id)
    job = _latest_project_radar_job(project_id, active_only=False)
    schedule = _project_research_schedule(project_id)
    links = (cache or {}).get("links") or []
    saved = sum(1 for link in links if str(link.get("status") or "") == "saved")
    shortlisted = sum(1 for link in links if str(link.get("status") or "") == "shortlisted")
    return {
        "status": str((cache or {}).get("status") or "not_run"),
        "usable": bool((cache or {}).get("usable")),
        "reason": str((cache or {}).get("reason") or ""),
        "intents": len((cache or {}).get("intents") or []),
        "queries": len((cache or {}).get("queries") or []),
        "candidates": len(links),
        "shortlisted": shortlisted,
        "saved": saved,
        "suggestions": len((cache or {}).get("suggestions") or []),
        "job": {
            "job_id": job["job_id"],
            "status": job["status"],
        } if job else None,
        "schedule_enabled": bool((schedule or {}).get("enabled")),
    }


def build_p3_activity(project_id: str, intelligence: ProjectIntelligence) -> dict[str, Any]:
    """Unified runs for the 活动与运行 view (query jobs + radar + events)."""
    try:
        jobs = get_job_manager().list(limit=50, project_id=project_id)
    except Exception:
        jobs = []
    radar_job = _latest_project_radar_job(project_id, active_only=False)
    snapshot = intelligence.snapshots.current(project_id)
    return {
        "jobs": jobs,
        "radar_job": {
            "job_id": radar_job["job_id"],
            "status": radar_job["status"],
        } if radar_job else None,
        "events": intelligence.events.list(project_id, limit=50),
        "runs": (snapshot or {}).get("run_state", {}).get("runs", []) if snapshot else [],
        "git": (snapshot or {}).get("git_state", {}) if snapshot else {},
    }


# ── P3.5 cycle audit ─────────────────────────────────────────────────


def _p3_legacy_audit_dir(project_id: str) -> Path:
    """Where the legacy directory-scan audit wrote its project_snapshot.json."""
    return PROJECT_ROOT / DEFAULT_PROGRESS_DIR / project_id


def _cycle_summary_light(confirmed: dict[str, Any] | None) -> dict[str, Any] | None:
    if not confirmed:
        return None
    summary = confirmed.get("summary") or {}
    return {
        "summary_id": confirmed.get("summary_id", ""),
        "baseline_revision": confirmed.get("baseline_revision", 0),
        "current_revision": confirmed.get("current_revision", 0),
        "confirmed_at": confirmed.get("confirmed_at", 0.0),
        "period": summary.get("period", ""),
        "real_progress": len(summary.get("real_progress") or []),
        "failed_experiments": len(summary.get("failed_experiments") or []),
        "risks": len(summary.get("risks") or []),
        "next_cycle_candidates": len(summary.get("next_cycle_candidates") or []),
    }


def _p3_audit_payload(project_id: str, intelligence: ProjectIntelligence) -> dict[str, Any]:
    """Read-only audit payload: draft comparison + confirmed summary + revisions."""
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    draft = build_cycle_audit(
        intelligence,
        project,
        legacy_out_dir=_p3_legacy_audit_dir(project_id),
    )
    confirmed = latest_confirmed_summary(intelligence, project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "draft": draft,
        "confirmed_latest": confirmed,
        "confirmed_light": _cycle_summary_light(confirmed),
        "revisions": intelligence.snapshots.list_revisions(project_id, limit=20),
    }


def build_p3_audit(project_id: str) -> dict[str, Any]:
    """GET /api/v1/projects/{id}/audit — snapshot-driven read, no side effects."""
    intelligence = _project_intelligence()
    try:
        return _p3_audit_payload(project_id, intelligence)
    finally:
        intelligence.db.close()


def run_p3_audit(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST /api/v1/projects/{id}/audit — collect + optional test + compare.

    Local observation only (no remote checks, no model); the configured test
    command runs once per distinct (command, head, status) outcome and is
    skipped when the project has no test command.
    """
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    intelligence = _project_intelligence()
    try:
        events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
        if bool(payload.get("run_tests", True)) and (project.test_command or "").strip():
            events.extend(collect_test_events(project))
        added = ingest_events(intelligence, events)
        if added or intelligence.snapshots.latest(project_id) is None:
            build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
        result = _p3_audit_payload(project_id, intelligence)
        result["new_events"] = added
        return result
    finally:
        intelligence.db.close()


def confirm_p3_audit(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST /api/v1/projects/{id}/audit/confirm — persist the confirmed summary.

    The current revision becomes the next audit's baseline (plan §6.3).
    Artifacts are exported as Markdown/JSON next to the legacy audit outputs.
    """
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    intelligence = _project_intelligence()
    try:
        baseline_raw = payload.get("baseline_revision")
        current_raw = payload.get("current_revision")
        return confirm_cycle_summary(
            intelligence,
            project,
            baseline_revision=int(baseline_raw) if baseline_raw not in (None, "") else None,
            current_revision=int(current_raw) if current_raw not in (None, "") else None,
            legacy_out_dir=_p3_legacy_audit_dir(project_id),
            out_dir=PROJECT_ROOT / DEFAULT_PROGRESS_DIR,
        )
    finally:
        intelligence.db.close()


def build_p3_project_state(project_id: str) -> dict[str, Any]:
    """Page payload: one materialized read (snapshot + documents + inbox)."""
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    intelligence = _project_intelligence()
    try:
        current = intelligence.snapshots.current(project_id)
        return {
            "ok": True,
            "project_id": project_id,
            "project": project.to_dict(include_source=False),
            "snapshot": current,
            "documents": document_map(intelligence, project_id) if current else None,
            "reviews": _unified_reviews(project_id, intelligence, status=None),
            "activity": build_p3_activity(project_id, intelligence),
            "radar": _p3_radar_summary(project_id),
            "revisions": intelligence.snapshots.list_revisions(project_id, limit=20),
            "audit": _cycle_summary_light(
                latest_confirmed_summary(intelligence, project_id)
            ),
            "protocol_version": P3_PROTOCOL_VERSION,
        }
    finally:
        intelligence.db.close()


def _refresh_p3_project_local(project: ProjectDefinition, *, force: bool = False) -> dict[str, Any]:
    """Shared local refresh: collect + discover + seed reviews + snapshot.

    No remote checks and no model calls (plan §P3.3 acceptance).  Used by the
    explicit refresh route and by project registration (U1: the first
    snapshot exists as soon as the project is saved).
    """
    intelligence = _project_intelligence()
    try:
        previous = intelligence.snapshots.latest(project.id)
        events = collect_all_events(project, intelligence.db, since=0.0, check_remote=False)
        added = ingest_events(intelligence, events)
        discovery = scan_project_documents(intelligence, project, force=force)
        try:
            rag = compute_coverage(intelligence, project)
        except Exception as exc:
            rag = {"error": str(exc), "by_document": {}}
        seeded = seed_reviews(
            intelligence,
            project,
            input_snapshot_id=previous.snapshot_id if previous else "",
            rag=rag,
        )
        snapshot = build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL, rag=rag)
        return {
            "ok": True,
            "project_id": project.id,
            "snapshot_id": snapshot.snapshot_id,
            "revision": snapshot.revision,
            "new_events": added,
            "discovery": {key: value for key, value in discovery.items() if key != "project_id"},
            "reviews_added": len(seeded),
            "health": snapshot.health,
            "pending_reviews": snapshot.summary.get("pending_review_count", 0),
            "rag": {
                "indexed": rag.get("indexed", 0),
                "stale": rag.get("stale", 0),
                "missing": rag.get("missing", 0),
            },
        }
    finally:
        intelligence.db.close()


def refresh_p3_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """User-triggered local check: collect + discover + seed reviews + snapshot.

    No remote checks and no model calls (plan §P3.3 acceptance).
    """
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    return _refresh_p3_project_local(project, force=bool(payload.get("force")))


def build_p3_documents(project_id: str) -> dict[str, Any]:
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    intelligence = _project_intelligence()
    try:
        return {"ok": True, **document_map(intelligence, project_id)}
    finally:
        intelligence.db.close()


def set_p3_document_authority(
    project_id: str,
    document_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    authority = str(payload.get("authority") or "").strip()
    if authority not in {"candidate", "confirmed", "excluded"}:
        return {"ok": False, "error": f"无效 authority：{authority}"}
    intelligence = _project_intelligence()
    try:
        document = intelligence.documents.get(document_id)
        if document is None or document.project_id != project_id:
            return {"ok": False, "error": f"文档不存在：{document_id}"}
        if authority == "confirmed":
            document.metadata["confirmed_hash"] = document.content_hash
            intelligence.documents.upsert(document)
        intelligence.documents.set_authority(document_id, authority)
        superseded = supersede_document_reviews(intelligence, project_id, document_id)
        intelligence.events.append(new_event(
            project_id,
            EventKind.REVIEW_RESOLVED,
            payload={
                "document_id": document_id,
                "authority": authority,
                "path": document.path,
            },
            dedup_key=f"doc-authority-{document_id}-{authority}-{document.content_hash[:12]}",
        ))
        project = _p3_project_or_none(project_id)
        build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
        return {
            "ok": True,
            "document_id": document_id,
            "authority": authority,
            "superseded": superseded,
        }
    finally:
        intelligence.db.close()


def build_p3_work_items(project_id: str) -> dict[str, Any]:
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    return {"ok": True, "project_id": project_id, "items": work_item_projection(project)}


def confirm_p3_work_item(
    project_id: str,
    work_item_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Write a user-confirmed declared status back to the project YAML (P3 §9.4)."""
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    ref = parse_work_item_ref(project_id, work_item_id)
    if ref is None:
        return {"ok": False, "error": f"无效工作项：{work_item_id}"}
    kind, index = ref
    declared_status = str(payload.get("declared_status") or "").strip()
    if declared_status not in {"planned", "in_progress", "completed", "blocked"}:
        return {"ok": False, "error": f"无效人工状态：{declared_status}"}
    if kind == "goal":
        return {"ok": False, "error": "总体目标没有状态字段，请通过里程碑或行动管理进度。"}
    title = ""
    if kind == "ms":
        milestones = project.plan.milestones
        if index >= len(milestones):
            return {"ok": False, "error": "里程碑不存在或计划已变化，请刷新后重试。"}
        milestone = milestones[index]
        milestone.status = declared_status  # type: ignore[assignment]
        title = milestone.title
    else:  # act: next_actions is a plain list; only completion is persisted.
        actions = project.plan.next_actions
        if index >= len(actions):
            return {"ok": False, "error": "行动不存在或计划已变化，请刷新后重试。"}
        title = actions[index]
        if declared_status == "completed":
            actions.pop(index)
        declared_status = "completed" if declared_status == "completed" else "planned"
    project.plan.updated_at = _iso_utc(time.time())
    _project_registry().save(project)
    saved = _project_registry().get(project_id)
    if saved is None:
        raise RuntimeError("项目配置已写入，但无法重新读取")
    intelligence = _project_intelligence()
    try:
        intelligence.events.append(new_event(
            project_id,
            EventKind.WORK_ITEM_CONFIRMED,
            payload={
                "work_item_id": work_item_id,
                "title": title,
                "declared_status": declared_status,
            },
            dedup_key=f"wi-confirm-{work_item_id}-{declared_status}",
        ))
        snapshot = build_snapshot(intelligence, saved, trigger=SnapshotTrigger.MANUAL)
        return {
            "ok": True,
            "work_item_id": work_item_id,
            "declared_status": declared_status,
            "revision": snapshot.revision,
            "items": work_item_projection(saved),
        }
    finally:
        intelligence.db.close()


def resolve_p3_review(project_id: str, review_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "").strip()
    if status not in {"confirmed", "dismissed"}:
        return {"ok": False, "error": f"无效处理结果：{status}"}
    if review_id.startswith("ev:"):
        result = resolve_evidence_review({"review_id": review_id[3:], "status": status})
        if not result.get("ok"):
            return result
        return {"ok": True, "review_id": review_id, "status": status, "source": "evidence_ledger"}
    intelligence = _project_intelligence()
    try:
        review = next(
            (item for item in intelligence.reviews.list(project_id) if item.review_id == review_id),
            None,
        )
        if review is None:
            return {"ok": False, "error": f"复核项不存在：{review_id}"}
        if status == "confirmed" and review.kind.value == "document_authority":
            document_id = (review.impact_refs or [""])[0]
            document = intelligence.documents.get(document_id) if document_id else None
            if document is not None:
                document.metadata["confirmed_hash"] = document.content_hash
                intelligence.documents.upsert(document)
                intelligence.documents.set_authority(document_id, "confirmed")
                supersede_document_reviews(intelligence, project_id, document_id)
        if status == "confirmed" and review.kind.value == "branch_divergence":
            # Confirming a branch-suggest review links the current branch to
            # the work item (persisted on the store row; YAML stays untouched).
            work_item_id = (review.impact_refs or [""])[0]
            if work_item_id:
                branch = ""
                for event in reversed(intelligence.events.list(project_id, limit=200)):
                    if str(event.get("kind") or "") == "git.head_changed":
                        branch = str((event.get("payload") or {}).get("branch") or "")
                        break
                item = intelligence.work_items.get(work_item_id)
                if item is not None and branch:
                    item.linked_branch = branch
                    intelligence.work_items.upsert(item)
        intelligence.reviews.resolve(review_id, status)
        intelligence.events.append(new_event(
            project_id,
            EventKind.REVIEW_RESOLVED,
            payload={"review_id": review_id, "status": status, "kind": review.kind.value},
            dedup_key=f"review-resolve-{review_id}-{status}",
        ))
        project = _p3_project_or_none(project_id)
        build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL)
        return {"ok": True, "review_id": review_id, "status": status}
    finally:
        intelligence.db.close()


def index_p3_project_knowledge(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Index confirmed project documents into the knowledge base (P3 §10.3)."""
    project = _p3_project_or_none(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    document_ids = [str(item) for item in (payload.get("document_ids") or [])] or None
    intelligence = _project_intelligence()
    try:
        result = index_project_documents(intelligence, project, document_ids=document_ids)
        if result.get("ok"):
            intelligence.events.append(new_event(
                project_id,
                EventKind.KNOWLEDGE_INDEX_CHANGED,
                payload={
                    "documents": int(result.get("documents") or 0),
                    "indexed": int(result.get("indexed") or 0),
                    "index_version": "project-doc-20260813",
                },
                dedup_key=f"knowledge-index-{project_id}-{int(time.time())}",
            ))
            rag = compute_coverage(intelligence, project)
            seed_reviews(intelligence, project, rag=rag)
            build_snapshot(intelligence, project, trigger=SnapshotTrigger.MANUAL, rag=rag)
            result["rag"] = {
                "indexed": rag.get("indexed", 0),
                "stale": rag.get("stale", 0),
                "missing": rag.get("missing", 0),
            }
        return result
    finally:
        intelligence.db.close()


def save_p3_project_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Settings dialog save: YAML write + local P3 refresh (no sync monitor scan)."""
    project_id = str(payload.get("project_id") or "").strip()
    project = _project_registry().get(project_id)
    if project is None:
        return {"ok": False, "error": f"未找到已登记项目：{project_id}"}
    name = str(payload.get("name") or "").strip()
    path_value = str(payload.get("path") or "").strip()
    if not name or not path_value:
        return {"ok": False, "error": "项目名称和本地目录不能为空。"}
    project.name = name
    project.path = path_value
    project.description = str(payload.get("description") or "").strip()
    project.test_command = str(payload.get("test_command") or "").strip()
    project.document_dirs = _split_lines(payload.get("document_dirs")) or ["docs"]
    project.document_files = _split_lines(payload.get("document_files")) or ["README.md"]
    project.result_dirs = _split_lines(payload.get("result_dirs")) or ["results", "artifacts", "experiments"]
    project.report_dirs = _split_lines(payload.get("report_dirs")) or ["reports"]
    config_path = _project_registry().save(project)
    saved = _project_registry().get(project.id)
    if saved is None:
        raise RuntimeError("项目配置已写入，但无法重新读取")
    intelligence = _project_intelligence()
    try:
        events = collect_all_events(saved, intelligence.db, since=0.0, check_remote=False)
        ingest_events(intelligence, events)
        scan_project_documents(intelligence, saved)
        rag = compute_coverage(intelligence, saved)
        seed_reviews(intelligence, saved, rag=rag)
        snapshot = build_snapshot(intelligence, saved, trigger=SnapshotTrigger.MANUAL, rag=rag)
    finally:
        intelligence.db.close()
    return {"ok": True, "path": str(config_path), "revision": snapshot.revision}


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
        if parsed.path == "/api/v1/projects":
            self._send_json(build_p3_projects(), headers={"Cache-Control": "no-store"})
            return
        if parsed.path.startswith("/api/v1/projects/"):
            self._route_p3_get(parsed)
            return
        if parsed.path == "/api/projects":
            self._send_json(build_projects_overview(), headers={"Cache-Control": "no-store"})
            return
        if parsed.path == "/api/knowledge/stats":
            self._send_json(gather_knowledge_stats(PROJECT_ROOT))
            return
        if parsed.path == "/api/config":
            self._send_json(build_sanitized_config())
            return
        if parsed.path == "/api/config/save":
            payload = self._read_json_body()
            result = save_config_field(
                str(payload.get("path") or ""),
                payload.get("value"),
            )
            self._send_json(result)
            return
        if parsed.path == "/api/file":
            params = urllib.parse.parse_qs(parsed.query)
            self._send_file(params.get("path", [""])[0])
            return
        if parsed.path == "/api/markdown":
            params = urllib.parse.parse_qs(parsed.query)
            rendered = render_markdown_preview(params.get("path", [""])[0])
            if rendered is None:
                self.send_error(404)
            else:
                self._send_text(rendered, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/projects/research/status":
            params = urllib.parse.parse_qs(parsed.query)
            project_id = params.get("project_id", [""])[0]
            if not project_id:
                self._send_json({"ok": False, "error": "project_id required"}, status=400)
            else:
                self._send_json(get_project_research_status(project_id))
            return
        if parsed.path == "/api/projects/research/papers":
            params = urllib.parse.parse_qs(parsed.query)
            project_id = params.get("project_id", [""])[0]
            if not project_id:
                self._send_json({"ok": False, "error": "project_id required"}, status=400)
            else:
                self._send_json(get_project_research_papers(project_id))
            return
        if parsed.path == "/api/projects/research/coverage":
            params = urllib.parse.parse_qs(parsed.query)
            project_id = params.get("project_id", [""])[0]
            if not project_id:
                self._send_json({"ok": False, "error": "project_id required"}, status=400)
            else:
                self._send_json(get_project_research_coverage(project_id))
            return
        if parsed.path == "/api/evidence/reviews":
            params = urllib.parse.parse_qs(parsed.query)
            project_id = params.get("project_id", [""])[0]
            status_value = params.get("status", ["pending"])[0]
            status = None if status_value == "all" else status_value
            self._send_json(get_evidence_reviews(project_id=project_id, status=status))
            return
        if parsed.path.startswith("/api/evidence/runs/"):
            run_id = parsed.path[len("/api/evidence/runs/"):]
            ledger = get_evidence_run(run_id)
            if ledger is None:
                self.send_error(404)
            else:
                self._send_json(ledger)
            return
        if parsed.path.startswith("/api/projects/research/jobs/"):
            job_id = parsed.path[len("/api/projects/research/jobs/"):]
            job = get_project_research_job(job_id)
            if job is None:
                self.send_error(404)
            else:
                self._send_json({"ok": True, **job}, headers={"Cache-Control": "no-store"})
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
            if parsed.path.startswith("/api/v1/projects/"):
                self._route_p3_post(parsed, payload)
                return
            if parsed.path == "/api/papers/inbox":
                self._send_json(run_paper_inbox(payload))
                return
            if parsed.path == "/api/papers/promote":
                self._send_json(run_paper_promotion(payload))
                return
            if parsed.path == "/api/knowledge/index/rebuild":
                self._send_json(rebuild_knowledge_index(payload))
                return
            if parsed.path == "/api/knowledge/index/delete":
                self._send_json(delete_knowledge_index(payload))
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
            if parsed.path == "/api/progress/audit":
                self._send_json(run_progress_audit(payload))
                return
            if parsed.path == "/api/projects/save":
                self._send_json(save_registered_project(payload))
                return
            if parsed.path == "/api/projects/settings":
                self._send_json(update_registered_project_settings(payload))
                return
            if parsed.path == "/api/projects/refresh":
                self._send_json(refresh_projects(payload))
                return
            if parsed.path == "/api/projects/plan-suggestions":
                self._send_json(suggest_project_plan(payload))
                return
            if parsed.path == "/api/projects/plan-suggestions/apply":
                self._send_json(apply_project_plan_suggestions(payload))
                return
            if parsed.path == "/api/projects/plan-analysis":
                self._send_json(analyze_project_plan(payload))
                return
            if parsed.path == "/api/projects/plan-analysis/apply":
                self._send_json(apply_project_plan_analysis(payload))
                return
            if parsed.path == "/api/projects/charter/generate":
                self._send_json(generate_project_charter(payload))
                return
            if parsed.path == "/api/projects/charter/apply":
                self._send_json(apply_project_charter(payload))
                return
            if parsed.path == "/api/projects/research/run":
                self._send_json(run_project_research_radar(payload))
                return
            if parsed.path == "/api/projects/research/schedule":
                self._send_json(configure_project_research_schedule(payload))
                return
            if parsed.path == "/api/projects/research/papers/action":
                self._send_json(apply_paper_action(payload))
                return
            if parsed.path == "/api/evidence/reviews/resolve":
                result = resolve_evidence_review(payload)
                self._send_json(result, status=200 if result.get("ok") else 400)
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
                elif job["status"] not in ("pending", "running") or not mgr.cancel(
                    run_id,
                    reason=str(payload.get("reason") or "user"),
                ):
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

    def _route_p3_get(self, parsed: urllib.parse.ParseResult) -> None:
        """GET /api/v1/projects/{id}/... — snapshot-driven reads only."""
        parts = parsed.path[len("/api/v1/projects/"):].strip("/").split("/")
        project_id = parts[0] if parts else ""
        if not project_id:
            self.send_error(404)
            return
        if len(parts) == 2 and parts[1] == "state":
            result = build_p3_project_state(project_id)
            self._send_json(result, status=200 if result.get("ok") else 404,
                            headers={"Cache-Control": "no-store"})
            return
        if len(parts) == 2 and parts[1] == "documents":
            result = build_p3_documents(project_id)
            self._send_json(result, status=200 if result.get("ok") else 404)
            return
        if len(parts) == 2 and parts[1] == "work-items":
            result = build_p3_work_items(project_id)
            self._send_json(result, status=200 if result.get("ok") else 404)
            return
        if len(parts) == 2 and parts[1] == "reviews":
            project = _p3_project_or_none(project_id)
            if project is None:
                self._send_json({"ok": False, "error": f"未找到已登记项目：{project_id}"}, status=404)
                return
            intelligence = _project_intelligence()
            try:
                reviews = _unified_reviews(project_id, intelligence, status=None)
            finally:
                intelligence.db.close()
            pending = [item for item in reviews if item["status"] == "pending"]
            self._send_json({"ok": True, "reviews": reviews, "pending": pending,
                             "count": len(pending)})
            return
        if len(parts) == 2 and parts[1] == "activity":
            project = _p3_project_or_none(project_id)
            if project is None:
                self._send_json({"ok": False, "error": f"未找到已登记项目：{project_id}"}, status=404)
                return
            intelligence = _project_intelligence()
            try:
                self._send_json({"ok": True, **build_p3_activity(project_id, intelligence)})
            finally:
                intelligence.db.close()
            return
        if len(parts) == 2 and parts[1] == "audit":
            result = build_p3_audit(project_id)
            self._send_json(result, status=200 if result.get("ok") else 404)
            return
        if len(parts) == 2 and parts[1] == "events":
            self._send_project_sse(project_id)
            return
        self.send_error(404)

    def _route_p3_post(self, parsed: urllib.parse.ParseResult, payload: dict[str, Any]) -> None:
        """POST /api/v1/projects/{id}/... — explicit user actions."""
        parts = parsed.path[len("/api/v1/projects/"):].strip("/").split("/")
        project_id = parts[0] if parts else ""
        if not project_id:
            self.send_error(404)
            return
        if len(parts) == 2 and parts[1] == "refresh":
            result = refresh_p3_project(project_id, payload)
            self._send_json(result, status=200 if result.get("ok") else 404)
            return
        if len(parts) == 2 and parts[1] == "settings":
            result = save_p3_project_settings(payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        if len(parts) == 3 and parts[1] == "knowledge" and parts[2] == "index":
            result = index_p3_project_knowledge(project_id, payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        if len(parts) == 4 and parts[1] == "documents" and parts[3] == "authority":
            result = set_p3_document_authority(project_id, parts[2], payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        if len(parts) == 4 and parts[1] == "work-items" and parts[3] == "confirm":
            result = confirm_p3_work_item(project_id, parts[2], payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        if len(parts) == 4 and parts[1] == "reviews" and parts[3] == "resolve":
            result = resolve_p3_review(project_id, parts[2], payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        if len(parts) == 2 and parts[1] == "audit":
            result = run_p3_audit(project_id, payload)
            self._send_json(result, status=200 if result.get("ok") else 404)
            return
        if len(parts) == 3 and parts[1] == "audit" and parts[2] == "confirm":
            result = confirm_p3_audit(project_id, payload)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return
        self.send_error(404)

    def _send_project_sse(self, project_id: str) -> None:
        """Stream P3 project events with the event id as the reconnection cursor."""
        intelligence = _project_intelligence()
        try:
            if _p3_project_or_none(project_id) is None:
                self.send_error(404)
                return
            last_id = self.headers.get("Last-Event-ID", "")
            cursor = int(last_id) if last_id.isdigit() else 0

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Content-Security-Policy", CSP_HEADER)
            self.end_headers()
            last_keepalive = time.monotonic()
            while True:
                batch = intelligence.events.list(project_id, after_event_id=cursor, limit=200)
                for event in batch:
                    event_id = int(event["event_id"])
                    data = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"id: {event_id}\ndata: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    cursor = event_id
                if not batch and time.monotonic() - last_keepalive >= 25.0:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    last_keepalive = time.monotonic()
                if not batch:
                    time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            intelligence.db.close()

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
        """Stream persisted SSE events using the database event id as cursor.

        Supports Last-Event-ID for reconnection.
        """
        mgr = get_job_manager()
        if mgr.get(run_id) is None:
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
        terminal_statuses = {
            "completed",
            "completed_with_warnings",
            "completed_diagnostic",
            "timed_out_with_report",
            "timed_out",
            "cancelled",
            "failed",
        }
        last_keepalive = time.monotonic()
        try:
            while True:
                batch = mgr.events(run_id, after_id=cursor)
                for event in batch:
                    event_id = int(event["event_id"])
                    data = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"id: {event_id}\ndata: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    cursor = event_id
                job = mgr.get(run_id)
                if not batch and job and job.get("status") in terminal_statuses:
                    self.wfile.write(b"event: done\ndata: {}\n\n")
                    self.wfile.flush()
                    return
                if not batch and time.monotonic() - last_keepalive >= 25.0:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    last_keepalive = time.monotonic()
                if not batch:
                    time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def main(argv: list[str] | None = None) -> None:
    _load_runtime_env()
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
    _start_persistent_worker()
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


def _list_report_files(root: Path) -> list[dict[str, Any]]:
    """列出最终报告，排除中间产物。"""
    query_root = root / "workbench" / "query"
    if not root.exists():
        return []
    INTERMEDIATE_SUFFIXES = (".draft.md", ".verified.md", ".audit.md", ".sources.md", ".diagnostic.md")
    files = []
    candidates = list(root.glob("*.md"))
    if query_root.exists():
        candidates.extend(query_root.rglob("*.md"))
    for path in sorted(candidates):
        if not path.is_file():
            continue
        try:
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
        except ValueError:
            continue
        name_lower = path.name.lower()
        if name_lower.endswith(INTERMEDIATE_SUFFIXES):
            continue
        files.append({
            "path": _rel(path),
            "name": path.name,
            "size": path.stat().st_size,
            "modified": int(path.stat().st_mtime),
        })
    return files


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
    return files


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


def _save_seen_papers(seen: dict[str, Any]) -> None:
    SEEN_PAPERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = SEEN_PAPERS_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(SEEN_PAPERS_PATH)


def _mark_papers_seen(papers: list, source: str) -> None:
    with _SEEN_PAPERS_LOCK:
        seen = _load_seen_papers()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for p in papers:
            key = _paper_identity(source, p.id)
            if key not in seen:
                seen[key] = {"status": "inboxed", "at": now, "title": (p.title or "")[:120]}
        try:
            _save_seen_papers(seen)
        except Exception:
            pass


def _enrich_profile(entry: dict) -> dict:
    try:
        yaml_path = PROJECT_ROOT / entry["path"]
        profile = load_profile(yaml_path, validate=False)
        entry["display"] = profile.name or Path(entry["path"]).stem
        entry["profile_id"] = profile.id
        entry["project_paths"] = [
            str(path) for path in profile.normalized_project_paths(yaml_path.parent)
        ]
        return entry
    except Exception:
        pass
    entry["display"] = re.sub(r"[_-]+", " ", Path(entry["path"]).stem).strip() or entry["path"]
    entry["project_paths"] = []
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
        "api_key_present": bool(
            cfg.get("api_key")
            or os.environ.get(fallback_env)
            or os.environ.get("OPENAI_API_KEY")
        ),
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


def _feature_model_settings(feature: str) -> dict[str, Any]:
    fallback = _FEATURE_MODEL_FALLBACKS[feature]
    raw = config.load()
    cfg = _resolved_feature_model_config(raw, feature)
    return {
        "model": str(cfg.get("model") or _default_model_name(fallback)).strip(),
        "base_url": str(cfg.get("base_url") or _default_base_url(fallback)).strip(),
        "api_key": str(
            cfg.get("api_key")
            or os.environ.get(f"CONFLUX_MODELS__{feature.upper()}__API_KEY")
            or _default_api_key(fallback)
        ).strip(),
        "temperature": float(cfg.get("temperature") if cfg.get("temperature") is not None else 0.2),
    }


def _path_value(value: Any, default: str) -> str:
    text = str(value or default).strip()
    path = Path(text).expanduser()
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)


def _optional_path(value: Any) -> str | None:
    text = str(value or "").strip()
    return _path_value(text, text) if text else None


def _embedding_runtime_updates(payload: dict[str, Any]) -> dict[str, str]:
    raw = config.load()
    embedding = raw.get("embedding") or {}
    reasoning = (raw.get("models") or {}).get("reasoning") or {}
    api_key = str(
        payload.get("embedding_api_key")
        or os.environ.get("CONFLUX_EMBEDDING__API_KEY")
        or embedding.get("api_key")
        or os.environ.get("OPENAI_API_KEY")
        or reasoning.get("api_key")
        or ""
    ).strip()
    base_url = str(
        payload.get("embedding_base_url")
        or os.environ.get("CONFLUX_EMBEDDING__BASE_URL")
        or embedding.get("base_url")
        or reasoning.get("base_url")
        or ""
    ).strip()
    model = str(
        payload.get("embedding_model")
        or os.environ.get("CONFLUX_EMBEDDING__MODEL")
        or embedding.get("model")
        or ""
    ).strip()
    updates = {}
    if api_key:
        updates["CONFLUX_EMBEDDING__API_KEY"] = api_key
    if base_url:
        updates["CONFLUX_EMBEDDING__BASE_URL"] = base_url
    if model:
        updates["CONFLUX_EMBEDDING__MODEL"] = model
    return updates


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

    depth = str(payload.get("depth") or "standard").strip().lower()
    if depth not in {"quick", "standard", "deep"}:
        depth = "standard"
    preset = depth.upper()
    updates[f"CONFLUX_MODELS__{preset}__PROVIDER"] = "openai_compatible"
    if base_url:
        updates[f"CONFLUX_MODELS__{preset}__BASE_URL"] = base_url
    if api_key:
        updates[f"CONFLUX_MODELS__{preset}__API_KEY"] = api_key
    if model:
        updates[f"CONFLUX_MODELS__{preset}__MODEL"] = model
    for role in ("PLANNER", "ANALYST", "RERANKER", "SYNTHESIZER", "VERIFIER"):
        updates[f"CONFLUX_RESEARCH__PROFILES__{preset}__{role}_MODEL"] = depth
    if embedding_base_url or base_url:
        updates["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url or base_url
    if embedding_api_key or api_key:
        updates["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key or api_key
    if embedding_model:
        updates["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    updates["CONFLUX_RESEARCH__DEPTH"] = depth
    if depth == "quick":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "1"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "false"
        updates["CONFLUX_RETRIEVAL__TOP_K"] = "3"
        updates["CONFLUX_RETRIEVAL__FINAL_K"] = "3"
    elif depth == "deep":
        updates["CONFLUX_AGENT__MAX_ITERATIONS"] = "5"
        updates["CONFLUX_RESEARCH__ENABLE_L4"] = "true"
        updates["CONFLUX_RESEARCH__MAX_DEEP_QUESTIONS"] = "5"
    return updates


def render_markdown_preview(requested_path: str) -> str | None:
    """Render an allowed Markdown file into an isolated, readable HTML page."""

    path = _safe_read_path(requested_path)
    if path is None or not path.is_file() or path.suffix.casefold() not in {".md", ".markdown"}:
        return None
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    body = markdown.markdown(
        html.escape(source),
        extensions=["extra", "sane_lists", "tables", "fenced_code"],
        output_format="html5",
    )
    title = html.escape(path.name)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{max-width:860px;margin:0 auto;padding:32px 36px 64px;color:#17201e;background:#fff;font:15px/1.75 Inter,system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
h1,h2,h3,h4{{margin:1.6em 0 .55em;line-height:1.35;letter-spacing:0;color:#0c485e}}h1{{margin-top:0;font-size:28px}}h2{{padding-bottom:6px;border-bottom:1px solid #d5e0dc;font-size:21px}}h3{{font-size:17px}}p,ul,ol,blockquote,pre,table{{margin:.8em 0}}a{{color:#055a5b;text-underline-offset:3px}}code{{padding:2px 5px;border-radius:4px;background:#f3f7f5;font:13px/1.6 "Cascadia Code",Consolas,monospace}}pre{{overflow:auto;padding:14px;border:1px solid #d5e0dc;border-radius:6px;background:#f7f9f8}}pre code{{padding:0;background:transparent}}blockquote{{margin-inline:0;padding:10px 16px;border:1px solid #b8cbc4;border-radius:6px;background:#f3f7f5;color:#344d45}}table{{width:100%;border-collapse:collapse}}th,td{{padding:8px 10px;border:1px solid #d5e0dc;text-align:left;vertical-align:top}}th{{background:#f3f7f5}}img{{max-width:100%;height:auto}}hr{{border:0;border-top:1px solid #d5e0dc}}@media(max-width:640px){{body{{padding:22px 18px 48px;font-size:14px}}h1{{font-size:23px}}h2{{font-size:19px}}}}
</style></head><body>{body}</body></html>"""


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
