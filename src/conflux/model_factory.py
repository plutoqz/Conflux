"""Model Factory — 基于 LangChain BaseChatModel 接口的通用模型工厂

所有 Provider 对上层透明，Agent 代码只依赖 BaseChatModel 和 Embeddings 接口。

默认 API-first：通过 OpenAI 兼容 API、Anthropic、Groq 等远程 API 调用模型。
支持通过 config 自定义 base_url、api_key，也支持环境变量注入。
"""

import os
import queue
import threading
from math import ceil
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from . import config


class BoundedChatModel:
    """Proxy a chat model with a hard wall-clock boundary per invocation."""

    def __init__(self, model: Any, timeout_seconds: float) -> None:
        self._model = model
        self._timeout_seconds = max(0.001, float(timeout_seconds))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "BoundedChatModel":
        return BoundedChatModel(
            self._model.bind_tools(tools, **kwargs),
            self._timeout_seconds,
        )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def run() -> None:
            try:
                result_queue.put((True, self._model.invoke(*args, **kwargs)))
            except BaseException as exc:
                result_queue.put((False, exc))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            succeeded, payload = result_queue.get(timeout=self._timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError(
                f"model invocation exceeded {self._timeout_seconds:g}s hard deadline"
            ) from exc
        if not succeeded:
            raise payload
        return payload


class ResearchTokenBudget:
    """Thread-safe shared token allowance for one research run."""

    def __init__(self, limit: int) -> None:
        self.limit = max(1, int(limit))
        self.used = 0
        self._lock = threading.Lock()

    def ensure_available(self, required: int = 1) -> None:
        with self._lock:
            required = max(1, int(required))
            if self.used + required > self.limit:
                raise RuntimeError(
                    f"research token budget exhausted: {self.used}/{self.limit}; "
                    f"next call reserves {required} tokens"
                )

    def record(self, response: Any) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        metadata = getattr(response, "response_metadata", None) or {}
        token_usage = metadata.get("token_usage") or metadata.get("usage") or {}
        total = usage.get("total_tokens") or token_usage.get("total_tokens")
        try:
            consumed = max(0, int(total or 0))
        except (TypeError, ValueError):
            consumed = 0
        if consumed:
            with self._lock:
                self.used += consumed


class BudgetedChatModel:
    """Share one enforceable token budget across all role models in a run."""

    def __init__(self, model: Any, budget: ResearchTokenBudget, *, output_reserve: int = 0) -> None:
        self._model = model
        self._budget = budget
        self._output_reserve = max(0, int(output_reserve))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "BudgetedChatModel":
        return BudgetedChatModel(
            self._model.bind_tools(tools, **kwargs),
            self._budget,
            output_reserve=self._output_reserve,
        )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        self._budget.ensure_available(self._output_reserve + _estimate_input_tokens(args, kwargs))
        response = self._model.invoke(*args, **kwargs)
        self._budget.record(response)
        return response


def _estimate_input_tokens(args: tuple[Any, ...], kwargs: dict[str, Any]) -> int:
    messages = args[0] if args else kwargs.get("input") or kwargs.get("messages") or []
    if not isinstance(messages, (list, tuple)):
        messages = [messages]
    characters = 0
    for message in messages:
        content = getattr(message, "content", message)
        characters += len(str(content or ""))
    # Mixed Chinese/English prompts typically fall between 1.5 and 4 chars per
    # token. Three is conservative enough to prevent a final-call overshoot
    # without discarding most of the useful Standard-mode budget.
    return max(1, ceil(characters / 3))


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
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    kwargs = dict(
        model=cfg["model"],
        temperature=cfg.get("temperature", 0.3),
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


def create_research_models(depth: str | None = None) -> tuple[dict[str, BaseChatModel], dict]:
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
    models = {
        role: BudgetedChatModel(
            BoundedChatModel(
                create_chat_model(
                    preset,
                    max_tokens=profile.role_max_tokens[role],
                    timeout=profile.model_timeout_seconds,
                    max_retries=profile.max_retries,
                ),
                profile.model_timeout_seconds,
            ),
            budget,
            output_reserve=profile.role_max_tokens[role],
        )
        for role, preset in presets.items()
    }
    return models, research_model_diagnostics(profile.depth)


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
        )
    elif provider == "openai_compatible":
        if not _resolve(cfg, "base_url"):
            raise ValueError("openai_compatible requires base_url in config")
        return _chat_openai(
            cfg,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
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
        return OpenAIEmbeddings(**kwargs)
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=model)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
