"""成本追踪模块（§8 成本追踪体系）

CostLedger 记录每次 LLM 调用的 token 消耗和费用，支持按阶段汇总。
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Literal


# 各模型定价 ($/1M tokens)，价格可能变动，以 API 官网为准
PRICING = {
    # Anthropic (per 1M tokens)
    "claude-sonnet-4-20250514":  {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5":         {"input": 0.8, "output": 4.0},
    # OpenAI (per 1M tokens)
    "gpt-4o":                    {"input": 2.5, "output": 10.0},
    "gpt-4o-mini":               {"input": 0.15, "output": 0.6},
    # DeepSeek (per 1M tokens, approximate)
    "deepseek-v3":               {"input": 0.27, "output": 1.1},
    "deepseek-v4-flash":         {"input": 0.1, "output": 0.4},
    "deepseek-v4-pro":           {"input": 1.0, "output": 4.0},
    "MiniMax-M3":                {"input": 0.5, "output": 2.0},
    "gemini-3.5-flash":          {"input": 0.2, "output": 0.8},
    "qwen3.7-plus":              {"input": 0.6, "output": 2.4},
    # Unknown fallback
    "default":                   {"input": 1.0, "output": 5.0},
}


@dataclass
class LLMCall:
    """单次 LLM 调用记录"""
    model: str
    stage: str                   # 阶段：intent/rag_agent/web_agent/model_agent/arbitrate/synthesize/factcheck/reflexion
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CostLedger:
    """全链路成本账本"""
    calls: list[LLMCall] = field(default_factory=list)

    def record(self, model: str, stage: str, tokens_in: int, tokens_out: int, latency_ms: float = 0):
        """记录一次 LLM 调用"""
        pricing = PRICING.get(model, PRICING["default"])
        cost = (tokens_in / 1_000_000) * pricing["input"] + \
               (tokens_out / 1_000_000) * pricing["output"]
        self.calls.append(LLMCall(
            model=model,
            stage=stage,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost, 6),
            latency_ms=latency_ms,
        ))

    def total_cost(self) -> float:
        return round(sum(c.cost_usd for c in self.calls), 4)

    def total_tokens(self) -> tuple[int, int]:
        """返回 (total_in, total_out)"""
        return (
            sum(c.tokens_in for c in self.calls),
            sum(c.tokens_out for c in self.calls),
        )

    def breakdown_by_stage(self) -> dict[str, float]:
        """按阶段汇总成本"""
        stages: dict[str, float] = {}
        for c in self.calls:
            stages[c.stage] = stages.get(c.stage, 0) + c.cost_usd
        return {k: round(v, 4) for k, v in stages.items()}

    def summary(self) -> dict:
        """生成可打印的成本摘要"""
        total_in, total_out = self.total_tokens()
        return {
            "total_cost_usd": self.total_cost(),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_calls": len(self.calls),
            "breakdown": self.breakdown_by_stage(),
        }

    def reset(self):
        self.calls.clear()
