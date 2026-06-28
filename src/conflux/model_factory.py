"""Model Factory — 基于 LangChain BaseChatModel 接口的通用模型工厂

所有 Provider 对上层透明，Agent 代码只依赖 BaseChatModel 和 Embeddings 接口。

默认 API-first：通过 OpenAI 兼容 API、Anthropic、Groq 等远程 API 调用模型。
支持通过 config 自定义 base_url、api_key，也支持环境变量注入。
"""

import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from . import config


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


def _chat_openai(cfg: dict, base_url: str | None = None) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    kwargs = dict(
        model=cfg["model"],
        temperature=cfg.get("temperature", 0.3),
        max_tokens=cfg.get("max_tokens", 4096),
    )
    url = _resolve(cfg, "base_url", default=base_url)
    if url:
        kwargs["base_url"] = url
    key = _resolve(cfg, "api_key", "OPENAI_API_KEY")
    if key:
        kwargs["api_key"] = key

    return ChatOpenAI(**kwargs)


def validate_runtime_credentials() -> list[str]:
    """返回 API-first 真实运行缺失的关键凭据说明。"""
    problems = []
    for preset in ("reasoning", "cheap"):
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


def create_chat_model(preset: str = "reasoning") -> BaseChatModel:
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
        return _chat_openai(cfg)
    elif provider == "openai_compatible":
        if not _resolve(cfg, "base_url"):
            raise ValueError("openai_compatible requires base_url in config")
        return _chat_openai(cfg)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = dict(
            model=cfg["model"],
            temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 4096),
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
            max_tokens=cfg.get("max_tokens", 4096),
        )
        key = _resolve(cfg, "api_key", "GROQ_API_KEY")
        if key:
            kwargs["api_key"] = key
        base_url = _resolve(cfg, "base_url")
        if base_url:
            kwargs["base_url"] = base_url
        return ChatGroq(**kwargs)
    elif provider == "deepseek":
        return _chat_openai(cfg, base_url="https://api.deepseek.com/v1")
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
