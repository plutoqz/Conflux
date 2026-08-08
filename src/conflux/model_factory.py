"""Model Factory — 基于 LangChain BaseChatModel 接口的通用模型工厂

所有 Provider 对上层透明，Agent 代码只依赖 BaseChatModel 和 Embeddings 接口。

默认 API-first：通过 OpenAI 兼容 API、Anthropic、Groq 等远程 API 调用模型。
支持通过 config 自定义 base_url、api_key，也支持环境变量注入。
"""

import os
import queue
import threading
import time
from collections.abc import Mapping, Sequence
from math import ceil
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from . import config


class RunDeadlineExceeded(TimeoutError):
    """Raised when a model call would consume the run's commit reserve."""


class BoundedChatModel:
    """Proxy a chat model with a hard wall-clock boundary per invocation."""

    def __init__(
        self,
        model: Any,
        timeout_seconds: float,
        *,
        deadline_at: float | None = None,
        commit_reserve_seconds: float = 0.0,
        role: str = "model",
    ) -> None:
        self._model = model
        self._timeout_seconds = max(0.001, float(timeout_seconds))
        self._deadline_at = float(deadline_at) if deadline_at else None
        self._commit_reserve_seconds = max(0.0, float(commit_reserve_seconds))
        self._role = role

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "BoundedChatModel":
        return BoundedChatModel(
            self._model.bind_tools(tools, **kwargs),
            self._timeout_seconds,
            deadline_at=self._deadline_at,
            commit_reserve_seconds=self._commit_reserve_seconds,
            role=self._role,
        )

    def with_commit_reserve(
        self,
        commit_reserve_seconds: float,
        *,
        role: str | None = None,
    ) -> "BoundedChatModel":
        return BoundedChatModel(
            self._model,
            self._timeout_seconds,
            deadline_at=self._deadline_at,
            commit_reserve_seconds=commit_reserve_seconds,
            role=role or self._role,
        )

    def with_max_tokens(
        self,
        max_tokens: int,
        *,
        role: str | None = None,
    ) -> "BoundedChatModel":
        inner = self._model
        binder = getattr(inner, "bind", None)
        if callable(binder):
            inner = binder(max_tokens=max(1, int(max_tokens)))
        return BoundedChatModel(
            inner,
            self._timeout_seconds,
            deadline_at=self._deadline_at,
            commit_reserve_seconds=self._commit_reserve_seconds,
            role=role or self._role,
        )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        call_timeout = self._timeout_seconds
        if self._deadline_at is not None:
            available = self._deadline_at - time.time() - self._commit_reserve_seconds
            if available <= 0:
                raise RunDeadlineExceeded(
                    f"run deadline reserve reached before {self._role} call"
                )
            call_timeout = min(call_timeout, available)
        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
        invocation_kwargs = dict(kwargs)
        configured_timeout = invocation_kwargs.get("timeout")
        try:
            if configured_timeout is not None:
                call_timeout = min(call_timeout, float(configured_timeout))
        except (TypeError, ValueError):
            pass
        invocation_kwargs["timeout"] = call_timeout

        def run() -> None:
            try:
                result_queue.put((True, self._model.invoke(*args, **invocation_kwargs)))
            except BaseException as exc:
                result_queue.put((False, exc))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            succeeded, payload = result_queue.get(timeout=call_timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                f"{self._role} invocation exceeded {call_timeout:g}s run-aware hard deadline"
            ) from exc
        if not succeeded:
            raise payload
        return payload


class ResearchTokenBudget:
    """Thread-safe shared token allowance for one research run."""

    def __init__(self, limit: int) -> None:
        self.limit = max(1, int(limit))
        self.used = 0
        self.actual_used = 0
        self.reserved = 0
        self._lock = threading.Lock()
        self.telemetry: dict[str, Any] = {
            "limit_tokens": self.limit,
            "charged_tokens": 0,
            "actual_tokens": 0,
            "reserved_tokens": 0,
            "call_count": 0,
            "rejected_calls": 0,
            "failed_calls": 0,
            "preserve_clamps": 0,
            "roles": {},
        }

    def reserve(
        self,
        required: int = 1,
        *,
        preserve: int = 0,
        role: str = "model",
    ) -> int:
        with self._lock:
            required = max(1, int(required))
            preserve = max(0, int(preserve))
            if self.used + self.reserved + required + preserve > self.limit:
                self.telemetry["rejected_calls"] += 1
                role_stats = self._role_stats(role)
                role_stats["rejected_calls"] += 1
                role_stats["last_rejected_required_tokens"] = required
                role_stats["last_rejected_preserve_tokens"] = preserve
                role_stats["last_rejected_charged_tokens"] = self.used
                raise RuntimeError(
                    f"research token budget exhausted: {self.used}/{self.limit}; "
                    f"in-flight reservations {self.reserved}; next call reserves "
                    f"{required} tokens with {preserve} preserved downstream"
                )
            self.reserved += required
            self.telemetry["reserved_tokens"] = self.reserved
            return required

    def release(self, reservation: int) -> None:
        with self._lock:
            self.reserved = max(0, self.reserved - max(0, int(reservation)))
            self.telemetry["reserved_tokens"] = self.reserved

    def ensure_available(self, required: int = 1) -> None:
        """Compatibility check for callers that do not execute a model call."""

        reservation = self.reserve(required)
        self.release(reservation)

    def record(
        self,
        response: Any,
        *,
        reservation: int = 0,
        preserve: int = 0,
        role: str = "model",
        estimated_input: int = 0,
        elapsed_ms: float = 0.0,
    ) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        metadata = getattr(response, "response_metadata", None) or {}
        token_usage = metadata.get("token_usage") or metadata.get("usage") or {}
        total = usage.get("total_tokens") or token_usage.get("total_tokens")
        try:
            consumed = max(0, int(total or 0))
        except (TypeError, ValueError):
            consumed = 0
        with self._lock:
            self.reserved = max(0, self.reserved - max(0, int(reservation)))
            self.actual_used += consumed
            maximum_charge = max(
                0,
                self.limit - self.used - self.reserved - max(0, int(preserve)),
            )
            charged = min(consumed, maximum_charge)
            if charged < consumed:
                self.telemetry["preserve_clamps"] += 1
            self.used += charged
            self.telemetry.update({
                "charged_tokens": self.used,
                "actual_tokens": self.actual_used,
                "reserved_tokens": self.reserved,
                "call_count": int(self.telemetry["call_count"]) + 1,
            })
            role_stats = self._role_stats(role)
            role_stats["call_count"] += 1
            role_stats["estimated_input_tokens"] += max(0, int(estimated_input))
            role_stats["actual_tokens"] += consumed
            role_stats["charged_tokens"] += charged
            role_stats["elapsed_ms"] = round(
                float(role_stats["elapsed_ms"]) + max(0.0, float(elapsed_ms)),
                2,
            )

    def record_failure(
        self,
        *,
        reservation: int,
        role: str,
        elapsed_ms: float,
    ) -> None:
        with self._lock:
            self.reserved = max(0, self.reserved - max(0, int(reservation)))
            self.telemetry["reserved_tokens"] = self.reserved
            self.telemetry["failed_calls"] += 1
            role_stats = self._role_stats(role)
            role_stats["failed_calls"] += 1
            role_stats["elapsed_ms"] = round(
                float(role_stats["elapsed_ms"]) + max(0.0, float(elapsed_ms)),
                2,
            )

    def _role_stats(self, role: str) -> dict[str, int | float]:
        roles = self.telemetry["roles"]
        key = str(role or "model")
        if key not in roles:
            roles[key] = {
                "call_count": 0,
                "rejected_calls": 0,
                "failed_calls": 0,
                "estimated_input_tokens": 0,
                "actual_tokens": 0,
                "charged_tokens": 0,
                "elapsed_ms": 0.0,
                "last_rejected_required_tokens": 0,
                "last_rejected_preserve_tokens": 0,
                "last_rejected_charged_tokens": 0,
            }
        return roles[key]


class BudgetedChatModel:
    """Share one enforceable token budget across all role models in a run."""

    def __init__(
        self,
        model: Any,
        budget: ResearchTokenBudget,
        *,
        output_reserve: int = 0,
        role: str = "model",
        downstream_reserve: int = 0,
    ) -> None:
        self._model = model
        self._budget = budget
        self._output_reserve = max(0, int(output_reserve))
        self._role = role
        self._downstream_reserve = max(0, int(downstream_reserve))
        self.last_reservation: dict[str, int | str] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "BudgetedChatModel":
        return BudgetedChatModel(
            self._model.bind_tools(tools, **kwargs),
            self._budget,
            output_reserve=self._output_reserve,
            role=self._role,
            downstream_reserve=self._downstream_reserve,
        )

    def with_downstream_reserve(
        self,
        downstream_reserve: int,
        *,
        role: str | None = None,
    ) -> "BudgetedChatModel":
        """Clone the proxy with a stage-specific downstream token floor."""

        return BudgetedChatModel(
            self._model,
            self._budget,
            output_reserve=self._output_reserve,
            role=role or self._role,
            downstream_reserve=downstream_reserve,
        )

    def with_stage_policy(
        self,
        *,
        downstream_reserve: int | None = None,
        commit_reserve_seconds: float | None = None,
        max_output_tokens: int | None = None,
        role: str | None = None,
    ) -> "BudgetedChatModel":
        inner = self._model
        if commit_reserve_seconds is not None and hasattr(inner, "with_commit_reserve"):
            inner = inner.with_commit_reserve(
                commit_reserve_seconds,
                role=role or self._role,
            )
        if max_output_tokens is not None and hasattr(inner, "with_max_tokens"):
            inner = inner.with_max_tokens(max_output_tokens, role=role or self._role)
        return BudgetedChatModel(
            inner,
            self._budget,
            output_reserve=(
                self._output_reserve
                if max_output_tokens is None
                else min(self._output_reserve, max(1, int(max_output_tokens)))
            ),
            role=role or self._role,
            downstream_reserve=(
                self._downstream_reserve
                if downstream_reserve is None
                else downstream_reserve
            ),
        )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        estimated_input = _estimate_input_tokens(args, kwargs)
        required = self._output_reserve + estimated_input
        self.last_reservation = {
            "role": self._role,
            "estimated_input_tokens": estimated_input,
            "output_reserve_tokens": self._output_reserve,
            "required_tokens": required,
        }
        reservation = self._budget.reserve(
            required,
            preserve=self._downstream_reserve,
            role=self._role,
        )
        started_at = time.perf_counter()
        try:
            response = self._model.invoke(*args, **kwargs)
        except BaseException:
            self._budget.record_failure(
                reservation=reservation,
                role=self._role,
                elapsed_ms=(time.perf_counter() - started_at) * 1000,
            )
            raise
        self._budget.record(
            response,
            reservation=reservation,
            preserve=self._downstream_reserve,
            role=self._role,
            estimated_input=estimated_input,
            elapsed_ms=(time.perf_counter() - started_at) * 1000,
        )
        return response


MAX_ESTIMATED_INPUT_TOKENS = 32_000


def _estimate_input_tokens(args: tuple[Any, ...], kwargs: dict[str, Any]) -> int:
    messages = args[0] if args else kwargs.get("input") or kwargs.get("messages") or []
    if not isinstance(messages, (list, tuple)):
        messages = [messages]
    characters = 0
    for message in messages:
        content = getattr(message, "content", message)
        characters += _structured_text_length(content)
    # Mixed Chinese/English prompts typically fall between 1.5 and 4 chars per
    # token. Three is conservative enough to prevent a final-call overshoot
    # without discarding most of the useful Standard-mode budget.
    # Chinese commonly approaches one token per character. Dividing by 1.5
    # remains conservative for mixed Chinese/English prompts without restoring
    # the runaway reservations that the hard cap prevents.
    return min(MAX_ESTIMATED_INPUT_TOKENS, max(1, ceil(characters / 1.5)))


def _structured_text_length(value: Any, *, depth: int = 0) -> int:
    """Count user-visible text without expanding arbitrary object reprs."""

    if value is None or depth > 8:
        return 0
    if isinstance(value, str):
        return len(value)
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, Mapping):
        return sum(
            len(str(key)) + _structured_text_length(item, depth=depth + 1)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return sum(_structured_text_length(item, depth=depth + 1) for item in value)
    if isinstance(value, (int, float, bool)):
        return len(str(value))
    nested = getattr(value, "content", None)
    if nested is not None and nested is not value:
        return _structured_text_length(nested, depth=depth + 1)
    return 0


def _resolve(cfg: dict, key: str, env_var: str | None = None, default=None):
    """解析配置值：config 字段 > 环境变量 > 默认值"""
    val = cfg.get(key)
    if val is not None and val != "":
        return val
    if env_var:
        val = os.environ.get(env_var)
        if val is not None and val != "":
            return val
    return default


def _chat_openai(
    cfg: dict,
    base_url: str | None = None,
    *,
    max_tokens: int | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    temperature_override: float | None = None,
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    kwargs = dict(
        model=cfg["model"],
        temperature=(
            temperature_override
            if temperature_override is not None
            else cfg.get("temperature", 0.3)
        ),
        max_tokens=max_tokens if max_tokens is not None else cfg.get("max_tokens", 4096),
        timeout=timeout if timeout is not None else cfg.get("timeout", 60),
        max_retries=max_retries if max_retries is not None else cfg.get("max_retries", 1),
    )
    url = _resolve(cfg, "base_url", default=base_url)
    if url:
        kwargs["base_url"] = url
    key = _resolve(cfg, "api_key", "OPENAI_API_KEY")
    if key:
        kwargs["api_key"] = key
    extra_body = cfg.get("extra_body")
    if isinstance(extra_body, dict) and extra_body:
        kwargs["extra_body"] = dict(extra_body)

    return ChatOpenAI(**kwargs)


def validate_runtime_credentials(
    depth: str | None = None,
    *,
    include_legacy_presets: bool = False,
) -> list[str]:
    """返回 API-first 真实运行缺失的关键凭据说明。"""
    from .research_modes import resolve_research_profile

    problems = []
    required_presets = list(resolve_research_profile(depth).model_presets)
    if include_legacy_presets:
        required_presets = list(dict.fromkeys(("reasoning", "cheap", *required_presets)))
    for preset in required_presets:
        cfg = config.get("models", preset)
        if not cfg:
            problems.append(f"缺少 models.{preset} 配置")
            continue
        provider = cfg.get("provider")
        if provider in ("openai", "openai_compatible", "deepseek") and not _resolve(cfg, "api_key", "OPENAI_API_KEY"):
            problems.append(f"models.{preset}.api_key 或 OPENAI_API_KEY 未设置")
        if provider == "anthropic" and not _resolve(cfg, "api_key", "ANTHROPIC_API_KEY"):
            problems.append(f"models.{preset}.api_key 或 ANTHROPIC_API_KEY 未设置")
        if provider == "groq" and not _resolve(cfg, "api_key", "GROQ_API_KEY"):
            problems.append(f"models.{preset}.api_key 或 GROQ_API_KEY 未设置")
        if provider == "ollama":
            problems.append(f"models.{preset}.provider=ollama 是可选本地扩展；默认真实运行请配置 API provider")

    emb_cfg = config.get("embedding")
    if not emb_cfg:
        problems.append("缺少 embedding 配置")
    elif emb_cfg.get("provider") in ("openai", "openai_compatible") and not _resolve(emb_cfg, "api_key", "OPENAI_API_KEY"):
        problems.append("embedding.api_key 或 OPENAI_API_KEY 未设置")
    elif emb_cfg.get("provider") == "ollama":
        problems.append("embedding.provider=ollama 是可选本地扩展；默认真实运行请配置 API embedding provider")

    return problems


def create_research_models(
    depth: str | None = None,
    *,
    deadline_at: float | None = None,
    commit_reserve_seconds: float | None = None,
    preserve_stage_budgets: bool = False,
) -> tuple[dict[str, BaseChatModel], dict]:
    """Create the role models selected by one P1 research profile."""

    from .research_modes import research_model_diagnostics, resolve_research_profile

    profile = resolve_research_profile(depth)
    presets = {
        "planner": profile.planner_model,
        "analyst": profile.analyst_model,
        "reranker": profile.reranker_model,
        "synthesizer": profile.synthesizer_model,
        "verifier": profile.verifier_model,
    }
    budget = ResearchTokenBudget(profile.token_budget)
    reserve = (
        profile.commit_reserve_seconds
        if commit_reserve_seconds is None
        else max(0.0, float(commit_reserve_seconds))
    )
    stage = profile.stage_budgets
    downstream_reserves = {
        "planner": stage["retrieval"] + stage["analysis"] + stage["synthesis"] + stage["verification"] + stage["commit"],
        "reranker": stage["analysis"] + stage["synthesis"] + stage["verification"] + stage["commit"],
        "analyst": stage["synthesis"] + stage["verification"] + stage["commit"],
        "synthesizer": stage["verification"] + stage["commit"],
        "verifier": stage["commit"],
    }
    role_reserves = downstream_reserves if preserve_stage_budgets else {
        role: reserve for role in presets
    }
    planner_reserve_reclaimed = 0.0
    final_token_reserve = min(
        max(profile.synthesizer_max_tokens * 2 + profile.verifier_max_tokens + 20_000, 24_000),
        int(profile.token_budget * 0.45),
    )
    role_token_reserves = {
        "planner": final_token_reserve,
        "reranker": final_token_reserve,
        "analyst": final_token_reserve,
        "synthesizer": min(
            profile.verifier_max_tokens + 12_000,
            int(profile.token_budget * 0.18),
        ),
        "verifier": 0,
    } if preserve_stage_budgets else {role: 0 for role in presets}
    models = {
        role: BudgetedChatModel(
            BoundedChatModel(
                create_chat_model(
                    preset,
                    max_tokens=profile.role_max_tokens[role],
                    timeout=profile.role_timeout_seconds[role],
                    max_retries=profile.max_retries,
                ),
                profile.role_timeout_seconds[role],
                deadline_at=deadline_at,
                commit_reserve_seconds=role_reserves[role],
                role=role,
            ),
            budget,
            output_reserve=profile.role_max_tokens[role],
            role=role,
            downstream_reserve=role_token_reserves[role],
        )
        for role, preset in presets.items()
    }
    if preserve_stage_budgets and deadline_at is not None:
        remaining = max(0.0, float(deadline_at) - time.time())
        planner_window = min(
            float(stage["planning"]),
            float(profile.role_timeout_seconds["planner"]),
        )
        available = remaining - float(role_reserves["planner"])
        if available < planner_window - 1.0:
            adjusted = max(0.0, remaining - planner_window - 1.0)
            planner_reserve_reclaimed = float(role_reserves["planner"]) - adjusted
            role_reserves["planner"] = adjusted
            models["planner"] = models["planner"].with_stage_policy(
                commit_reserve_seconds=adjusted,
                role="planner",
            )
    diagnostics = research_model_diagnostics(profile.depth)
    diagnostics["role_downstream_reserve_seconds"] = role_reserves
    diagnostics["planner_reserve_reclaimed_seconds"] = round(
        max(0.0, planner_reserve_reclaimed), 3
    )
    diagnostics["role_downstream_reserve_tokens"] = role_token_reserves
    diagnostics["max_estimated_input_tokens"] = MAX_ESTIMATED_INPUT_TOKENS
    diagnostics["token_budget_runtime"] = budget.telemetry
    return models, diagnostics


def validate_embedding_credentials() -> list[str]:
    """返回构建 RAG 索引所需 embedding 凭据的缺失说明。"""

    problems = []
    emb_cfg = config.get("embedding")
    if not emb_cfg:
        return ["缺少 embedding 配置"]
    provider = emb_cfg.get("provider")
    if provider in ("openai", "openai_compatible") and not _resolve(emb_cfg, "api_key", "OPENAI_API_KEY"):
        problems.append("embedding.api_key 或 OPENAI_API_KEY 未设置")
    elif provider == "ollama":
        problems.append("embedding.provider=ollama 是可选本地扩展；默认真实运行请配置 API embedding provider")
    return problems


def create_chat_model(
    preset: str = "reasoning",
    *,
    max_tokens: int | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """根据 config 中的 preset 创建 ChatModel

    preset:
      - "reasoning"      → Agent Think 步骤
      - "cheap"           → 意图分类、简单任务

    每个 preset 的 config 支持可选字段：
      - base_url   → 自定义 API 地址
      - api_key    → API key（优先级高于环境变量）
    """
    cfg = config.get("models", preset)
    if cfg is None:
        raise ValueError(f"Unknown model preset: {preset}")

    provider = cfg["provider"]

    if provider == "openai":
        return _chat_openai(
            cfg,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            temperature_override=temperature,
        )
    elif provider == "openai_compatible":
        if not _resolve(cfg, "base_url"):
            raise ValueError("openai_compatible requires base_url in config")
        return _chat_openai(
            cfg,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            temperature_override=temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = dict(
            model=cfg["model"],
            temperature=cfg.get("temperature", 0.3),
            max_tokens=max_tokens if max_tokens is not None else cfg.get("max_tokens", 4096),
            timeout=timeout if timeout is not None else cfg.get("timeout", 60),
            max_retries=max_retries if max_retries is not None else cfg.get("max_retries", 1),
        )
        key = _resolve(cfg, "api_key", "ANTHROPIC_API_KEY")
        if key:
            kwargs["api_key"] = key
        base_url = _resolve(cfg, "base_url")
        if base_url:
            kwargs["base_url"] = base_url
        return ChatAnthropic(**kwargs)
    elif provider == "groq":
        from langchain_groq import ChatGroq
        kwargs = dict(
            model=cfg["model"],
            temperature=cfg.get("temperature", 0.3),
            max_tokens=max_tokens if max_tokens is not None else cfg.get("max_tokens", 4096),
            timeout=timeout if timeout is not None else cfg.get("timeout", 60),
            max_retries=max_retries if max_retries is not None else cfg.get("max_retries", 1),
        )
        key = _resolve(cfg, "api_key", "GROQ_API_KEY")
        if key:
            kwargs["api_key"] = key
        base_url = _resolve(cfg, "base_url")
        if base_url:
            kwargs["base_url"] = base_url
        return ChatGroq(**kwargs)
    elif provider == "deepseek":
        return _chat_openai(
            cfg,
            base_url="https://api.deepseek.com/v1",
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=cfg["model"],
            temperature=cfg.get("temperature", 0.3),
        )
    else:
        raise ValueError(f"Unsupported chat model provider: {provider}")


def create_embedding_model() -> Embeddings:
    """根据 config 创建 Embedding 模型，默认使用 API embedding provider。"""
    cfg = config.get("embedding")
    provider = cfg["provider"]
    model = cfg["model"]

    if provider in ("openai", "openai_compatible"):
        from langchain_openai import OpenAIEmbeddings
        kwargs = dict(model=model)
        url = _resolve(cfg, "base_url")
        if url:
            kwargs["base_url"] = url
        key = _resolve(cfg, "api_key", "OPENAI_API_KEY")
        if key:
            kwargs["api_key"] = key
        # dmxapi / openai_compatible adapters reject tiktoken token-id input;
        # disable tiktoken so the wrapper sends plain text lists instead.
        # dmxapi also enforces a ≤20 batch-size limit on embeddings.
        if provider == "openai_compatible":
            kwargs["tiktoken_enabled"] = False
            kwargs["check_embedding_ctx_length"] = False
            kwargs["chunk_size"] = 10
        return OpenAIEmbeddings(**kwargs)
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=model)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
