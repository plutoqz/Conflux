"""Structured LLM evidence review capability (M2)."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from conflux.core.contracts import (
    CapabilityMode,
    CapabilitySpec,
    PluginContext,
    PluginManifest,
    PluginPermission,
    StepResult,
    StepStatus,
)
from conflux.core.executor import sanitize_error
from conflux.sdk.plugin import Capability, Plugin


PROMPT_VERSION = "m2-v1"
REVIEW_BATCH_SIZE = 4
MAX_REVIEW_ATTEMPTS = 2
_REVIEW_CACHE: dict[str, list[dict[str, Any]]] = {}


class ReviewInvocationError(ValueError):
    """A bounded, user-visible failure while obtaining a structured review."""

    def __init__(self, code: str, message: str, *, attempts: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.attempts = attempts


class ReviewItem(BaseModel):
    relevance: Literal["relevant", "partially_relevant", "irrelevant"]
    research_value: Literal[
        "method", "dataset", "background", "counterexample", "survey", "none"
    ]
    evidence_quality: str = Field(min_length=1, max_length=240)
    reasoning: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_deeper_review: bool


class ResearchPlugin(Plugin):
    @property
    def manifest(self) -> PluginManifest:
        review_properties = {
            "index": {"type": "integer"},
            "relevance": {
                "enum": ["relevant", "partially_relevant", "irrelevant", "unreviewed"]
            },
            "research_value": {"type": "string"},
            "evidence_quality": {"type": "string"},
            "reasoning": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "needs_deeper_review": {"type": "boolean"},
            "content_hash": {"type": "string"},
            "profile_version": {"type": "string"},
            "prompt_version": {"type": "string"},
            "model_version": {"type": "string"},
            "uncertainty": {"type": "number"},
            "review_depth": {"type": "string"},
            "next_action": {"type": "string"},
            "review_status": {"type": "string"},
            "candidate_status": {"type": "string"},
            "deep_review_status": {"type": "string"},
            "error_code": {"type": "string"},
            "error_detail": {"type": "string"},
            "deterministic_score": {"type": ["number", "null"]},
            "semantic_score": {"type": ["number", "null"]},
            "retry_count": {"type": "integer"},
        }
        return PluginManifest(
            id="builtin.research",
            version="0.1.0",
            entrypoint="conflux.builtin.research.plugin:plugin",
            capabilities=[
                CapabilitySpec(
                    id="builtin.research.evidence_review",
                    description="LLM semantic review of search results or paper candidates",
                    mode=CapabilityMode.AGENTIC,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "candidates": {"type": "array", "items": {"type": "object"}},
                            "research_context": {"type": "string"},
                            "profile_version": {"type": "string"},
                            "prompt_version": {"type": "string"},
                            "batch": {"type": "boolean", "default": True},
                        },
                        "required": ["query", "candidates"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "reviews": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": review_properties,
                                    "required": list(review_properties),
                                },
                            },
                            "unreviewed_count": {"type": "integer"},
                            "reviewed_count": {"type": "integer"},
                            "cache_key": {"type": "string"},
                            "prompt_version": {"type": "string"},
                            "model_version": {"type": "string"},
                            "profile_version": {"type": "string"},
                        },
                        "required": [
                            "reviews",
                            "unreviewed_count",
                            "reviewed_count",
                            "cache_key",
                            "prompt_version",
                            "model_version",
                            "profile_version",
                        ],
                    },
                )
            ],
            permissions=[PluginPermission.MODEL_INFERENCE],
        )

    def get_capability(self, capability_id: str) -> Capability | None:
        return evidence_review if capability_id == "builtin.research.evidence_review" else None


plugin = ResearchPlugin()


def evidence_review(
    ctx: PluginContext,
    *,
    query: str,
    candidates: list[dict[str, Any]],
    research_context: str = "",
    profile_version: str = "unversioned",
    prompt_version: str = PROMPT_VERSION,
    batch: bool = True,
) -> StepResult:
    """Review candidates semantically; never replace LLM judgment with lexical scoring."""

    model_version = _model_version(ctx)
    cache_key = _cache_key(
        query, candidates, research_context, profile_version, prompt_version, model_version
    )
    if not candidates:
        return _result([], cache_key, profile_version, prompt_version, model_version)

    cached = _REVIEW_CACHE.get(cache_key)
    if cached is not None:
        result = _result(copy.deepcopy(cached), cache_key, profile_version, prompt_version, model_version)
        result.metrics["cache_hit"] = True
        return result

    try:
        model = ctx.model
        if model is None:
            from conflux.model_factory import create_chat_model

            model = create_chat_model(str(ctx.config.get("model_preset") or "cheap"))

        reviews = _batch_review(
            model,
            query,
            candidates,
            research_context,
            ctx,
            profile_version=profile_version,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        _REVIEW_CACHE[cache_key] = copy.deepcopy(reviews)
        return _result(reviews, cache_key, profile_version, prompt_version, model_version)
    except Exception as exc:
        reason = sanitize_error(f"LLM review unavailable: {type(exc).__name__}: {exc}", ctx.secrets)
        reviews = [
            _unreviewed_item(
                index,
                candidate,
                reason,
                profile_version,
                prompt_version,
                model_version,
            )
            for index, candidate in enumerate(candidates)
        ]
        result = _result(reviews, cache_key, profile_version, prompt_version, model_version)
        result.status = StepStatus.UNREVIEWED
        result.error = reason
        return result


def _result(
    reviews: list[dict[str, Any]],
    cache_key: str,
    profile_version: str,
    prompt_version: str,
    model_version: str,
) -> StepResult:
    reviewed = sum(1 for item in reviews if item.get("relevance") != "unreviewed")
    unreviewed = len(reviews) - reviewed
    partial = any(
        item.get("relevance") == "unreviewed"
        or item.get("candidate_status") == "needs_deeper_review"
        for item in reviews
    )
    status = StepStatus.SUCCESS if not reviews or not partial else StepStatus.UNREVIEWED
    return StepResult(
        status=status,
        output={
            "reviews": reviews,
            "reviewed_count": reviewed,
            "unreviewed_count": unreviewed,
            "cache_key": cache_key,
            "prompt_version": prompt_version,
            "model_version": model_version,
            "profile_version": profile_version,
        },
        plugin_id="builtin.research",
        capability_id="builtin.research.evidence_review",
        error=_review_error_summary(reviews),
    )


def _batch_review(
    model: Any,
    query: str,
    candidates: list[dict[str, Any]],
    research_context: str,
    ctx: PluginContext,
    *,
    profile_version: str = "unversioned",
    prompt_version: str = PROMPT_VERSION,
    model_version: str = "unknown",
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for start in range(0, len(candidates), REVIEW_BATCH_SIZE):
        batch = candidates[start : start + REVIEW_BATCH_SIZE]
        try:
            items = _invoke_validated(
                model,
                _build_prompt(query, batch, research_context),
                len(batch),
            )
        except Exception as exc:
            reason, code, attempts = _review_failure(exc)
            enriched.extend(
                _unreviewed_item(
                    start + index,
                    candidate,
                    reason,
                    profile_version,
                    prompt_version,
                    model_version,
                    error_code=code,
                    retry_count=max(0, attempts - 1),
                )
                for index, candidate in enumerate(batch)
            )
            continue

        # The initial review is useful even when the optional deeper pass fails.
        deep_indexes = [
            index
            for index, item in enumerate(items)
            if item.needs_deeper_review or 0.35 <= item.confidence <= 0.7
        ]
        deep_by_index: dict[int, ReviewItem] = {}
        deep_error: tuple[str, str, int] | None = None
        if deep_indexes:
            deep_candidates = [batch[index] for index in deep_indexes]
            try:
                deep_items = _invoke_validated(
                    model,
                    _build_prompt(query, deep_candidates, research_context, deep=True),
                    len(deep_candidates),
                )
                deep_by_index = dict(zip(deep_indexes, deep_items))
            except Exception as exc:
                deep_error = _review_failure(exc)

        for index, candidate in enumerate(batch):
            item = deep_by_index.get(index, items[index])
            payload = _enrich_review(
                item,
                global_index=start + index,
                candidate=candidate,
                profile_version=profile_version,
                prompt_version=prompt_version,
                model_version=model_version,
                review_depth="deep" if index in deep_by_index else "batch",
            )
            if deep_error and index in deep_indexes:
                reason, code, attempts = deep_error
                payload.update({
                    "candidate_status": "needs_deeper_review",
                    "deep_review_status": "unreviewed",
                    "deep_error_code": code,
                    "deep_error_detail": reason,
                    "retry_count": max(0, attempts - 1),
                    "next_action": "Retry deeper semantic review for this candidate.",
                })
            enriched.append(payload)
    return enriched


def _invoke_validated(model: Any, prompt: str, expected: int) -> list[ReviewItem]:
    last_error: Exception | None = None
    for attempt in range(MAX_REVIEW_ATTEMPTS):
        try:
            content = _invoke(model, prompt)
        except Exception as exc:
            last_error = exc
            if attempt + 1 < MAX_REVIEW_ATTEMPTS:
                continue
            code = _classify_review_error(exc)
            raise ReviewInvocationError(
                code,
                f"LLM invocation failed ({code}) after {attempt + 1} attempts: {exc}",
                attempts=attempt + 1,
            ) from exc

        try:
            return _validate_items(content, expected)
        except (ValueError, ValidationError) as first_error:
            repair_prompt = (
                "Repair the following response into the exact requested JSON array. "
                "Do not add prose.\n\nOriginal prompt:\n"
                + prompt
                + "\n\nInvalid response:\n"
                + content[:4000]
            )
            try:
                repaired = _invoke(model, repair_prompt)
                return _validate_items(repaired, expected)
            except Exception as second_error:
                last_error = second_error
                if attempt + 1 < MAX_REVIEW_ATTEMPTS:
                    continue
                code = "schema_repair_failed"
                if isinstance(second_error, ReviewInvocationError):
                    code = second_error.code
                raise ReviewInvocationError(
                    code,
                    f"LLM response failed schema repair: {first_error}; {second_error}",
                    attempts=attempt + 1,
                ) from second_error

    raise ReviewInvocationError(
        "llm_unavailable",
        f"LLM review unavailable: {last_error or 'unknown error'}",
        attempts=MAX_REVIEW_ATTEMPTS,
    )


def _invoke(model: Any, prompt: str) -> str:
    from langchain_core.messages import HumanMessage

    response = model.invoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    return str(content)


def _validate_items(content: str, expected: int) -> list[ReviewItem]:
    parsed = _extract_json_array(content)
    if parsed is None or len(parsed) != expected:
        raise ValueError(f"expected {expected} review items")
    return [ReviewItem.model_validate(item) for item in parsed]


def _build_prompt(
    query: str,
    candidates: list[dict[str, Any]],
    research_context: str,
    *,
    deep: bool = False,
) -> str:
    context = f"\nResearch context: {research_context}" if research_context else ""
    candidate_block = "\n\n".join(
        f"[{index}] {_candidate_text(candidate)[:1200]}"
        for index, candidate in enumerate(candidates)
    )
    depth = "Perform a deeper conflict and evidence-quality review." if deep else "Review as one batch."
    return f"""You evaluate research evidence semantically. {depth}

Query: {query}{context}

Candidates:
{candidate_block}

Return one JSON array item per candidate with exactly these fields:
- relevance: relevant | partially_relevant | irrelevant
- research_value: method | dataset | background | counterexample | survey | none
- evidence_quality: concise description of evidential support
- reasoning: concise semantic justification
- confidence: number from 0 to 1
- needs_deeper_review: boolean

Do not use keyword overlap as the final judgment. Return JSON only."""


def _candidate_text(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("text")
        or " ".join(
            str(candidate.get(key) or "") for key in ("title", "abstract", "snippet", "content")
        )
    ).strip()


def _model_version(ctx: PluginContext) -> str:
    configured = str(ctx.config.get("model_version") or "").strip()
    if configured:
        return configured
    if ctx.model is not None:
        return str(getattr(ctx.model, "model_name", "") or type(ctx.model).__name__)
    try:
        from conflux.config import get

        preset = str(ctx.config.get("model_preset") or "cheap")
        return str(get("models", preset, "model", default=preset))
    except Exception:
        return "unknown"


def _cache_key(
    query: str,
    candidates: list[dict[str, Any]],
    research_context: str,
    profile_version: str,
    prompt_version: str,
    model_version: str,
) -> str:
    payload = {
        "query": query,
        "candidate_hashes": [_hash_text(_candidate_text(item)) for item in candidates],
        "research_context": research_context,
        "profile_version": profile_version,
        "prompt_version": prompt_version,
        "model_version": model_version,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_json_array(text: str) -> list[dict[str, Any]] | None:
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return None
    return value


def _unreviewed_item(
    index: int,
    candidate: dict[str, Any],
    reason: str,
    profile_version: str,
    prompt_version: str,
    model_version: str,
    *,
    error_code: str = "llm_unavailable",
    retry_count: int = 0,
) -> dict[str, Any]:
    return {
        "index": index,
        "relevance": "unreviewed",
        "research_value": "none",
        "evidence_quality": "unreviewed",
        "reasoning": reason,
        "confidence": 0.0,
        "needs_deeper_review": False,
        "content_hash": _hash_text(_candidate_text(candidate)),
        "profile_version": profile_version,
        "prompt_version": prompt_version,
        "model_version": model_version,
        "uncertainty": 1.0,
        "review_depth": "unreviewed",
        "review_status": "unreviewed",
        "candidate_status": "provisional",
        "deep_review_status": "not_requested",
        "error_code": error_code,
        "error_detail": reason,
        "deterministic_score": _candidate_score(candidate),
        "semantic_score": None,
        "retry_count": retry_count,
        "next_action": "Configure a working review model and retry this candidate.",
    }


def _enrich_review(
    item: ReviewItem,
    *,
    global_index: int,
    candidate: dict[str, Any],
    profile_version: str,
    prompt_version: str,
    model_version: str,
    review_depth: str,
) -> dict[str, Any]:
    payload = item.model_dump()
    semantic_score = _semantic_score(item)
    payload.update({
        "index": global_index,
        "content_hash": _hash_text(_candidate_text(candidate)),
        "profile_version": profile_version,
        "prompt_version": prompt_version,
        "model_version": model_version,
        "uncertainty": round(1.0 - item.confidence, 4),
        "review_depth": review_depth,
        "review_status": "reviewed",
        "candidate_status": "reviewed",
        "deep_review_status": "completed" if review_depth == "deep" else "not_requested",
        "error_code": "",
        "error_detail": "",
        "deterministic_score": _candidate_score(candidate),
        "semantic_score": semantic_score,
        "retry_count": 0,
        "next_action": "",
    })
    return payload


def _semantic_score(item: ReviewItem) -> float:
    relevance_weight = {
        "relevant": 0.9,
        "partially_relevant": 0.6,
        "irrelevant": 0.1,
    }
    return round(relevance_weight[item.relevance] * item.confidence, 4)


def _candidate_score(candidate: dict[str, Any]) -> float | None:
    for key in ("deterministic_score", "keyword_score", "score"):
        value = candidate.get(key)
        if value is None or value == "":
            continue
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        if score > 1.0:
            score /= 100.0
        return round(max(0.0, min(1.0, score)), 4)
    return None


def _classify_review_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".casefold()
    if any(term in text for term in ("timeout", "timed out", "deadline")):
        return "llm_timeout"
    if any(term in text for term in ("401", "403", "authentication", "api key", "unauthorized")):
        return "authentication_failed"
    if any(term in text for term in ("429", "rate limit", "too many requests")):
        return "rate_limited"
    if any(term in text for term in ("json", "schema", "expected ")):
        return "schema_invalid"
    return "llm_unavailable"


def _review_failure(exc: Exception) -> tuple[str, str, int]:
    if isinstance(exc, ReviewInvocationError):
        code = exc.code
        attempts = exc.attempts
    else:
        code = _classify_review_error(exc)
        attempts = MAX_REVIEW_ATTEMPTS
    return (
        f"LLM semantic review failed [{code}]: {exc}",
        code,
        attempts,
    )


def _review_error_summary(reviews: list[dict[str, Any]]) -> str:
    errors: list[str] = []
    for item in reviews:
        for key in ("error_code", "deep_error_code"):
            code = str(item.get(key) or "").strip()
            if code and code not in errors:
                errors.append(code)
    return ", ".join(errors)
