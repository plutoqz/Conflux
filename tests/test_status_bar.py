"""C 阶段 — Agent 状态栏测试。

覆盖 status_bar 的两句注入格式、预算 <30% 告警、token budget 读取
与 KV Cache 友好性（不修改系统提示模板本身，仅尾部追加）。
"""

from __future__ import annotations

import time

from conflux.graph_v2 import BUDGET_WARNING_LINE, status_bar


class _FakeBudget:
    def __init__(self, used: int, limit: int):
        self.telemetry = {"charged_tokens": used, "limit_tokens": limit}


class _FakeModel:
    def __init__(self, budget=None):
        self._budget = budget


def _state(stage: str = "decompose", *, started_ago: float = 0.0, deadline_in: float | None = None) -> dict:
    return {
        "_pipeline_stage": stage,
        "_started_at": time.time() - started_ago,
        "_deadline_at": time.time() + deadline_in if deadline_in is not None else None,
    }


class TestStatusBarFormat:
    def test_returns_empty_without_deadline_or_budget(self):
        assert status_bar(_state(deadline_in=None)) == ""

    def test_emits_two_lines_with_stage_and_budget(self):
        text = status_bar(_state("decompose", deadline_in=300))
        lines = [line for line in text.splitlines() if line]
        assert 'stage: "decompose query"' in lines[0]
        assert lines[1].startswith('budget: "remaining ~')
        assert "s" in lines[1]

    def test_generate_stage_includes_section_progress(self):
        text = status_bar(
            _state("generate", deadline_in=300),
            section_index=2,
            section_total=4,
        )
        assert 'stage: "generate section 2/4"' in text

    def test_stage_label_fallback_for_unknown_stage(self):
        text = status_bar(_state("some_stage", deadline_in=60))
        assert 'stage: "some_stage"' in text

    def test_does_not_modify_template_when_no_status(self):
        # KV Cache 友好：无预算信息时返回空串，不污染系统提示。
        assert status_bar(_state(deadline_in=None)) == ""


class TestBudgetWarning:
    def test_no_warning_when_budget_above_30_percent(self):
        text = status_bar(_state("audit", started_ago=10, deadline_in=290))
        assert BUDGET_WARNING_LINE not in text

    def test_warning_when_time_budget_below_30_percent(self):
        text = status_bar(_state("audit", started_ago=280, deadline_in=20))
        assert BUDGET_WARNING_LINE in text

    def test_warning_when_token_budget_below_30_percent(self):
        model = _FakeModel(_FakeBudget(used=8_000, limit=10_000))
        text = status_bar(_state("synthesize", deadline_in=None), model)
        assert "tokens left" in text
        assert BUDGET_WARNING_LINE in text

    def test_no_warning_when_token_budget_healthy(self):
        model = _FakeModel(_FakeBudget(used=2_000, limit=10_000))
        text = status_bar(_state("synthesize", deadline_in=None), model)
        assert "8000 tokens left" in text
        assert BUDGET_WARNING_LINE not in text


class TestTokenBudgetReading:
    def test_token_line_includes_remaining(self):
        model = _FakeModel(_FakeBudget(used=4_000, limit=10_000))
        text = status_bar(_state("generate", deadline_in=120), model)
        assert "6000 tokens left" in text

    def test_missing_budget_object_is_ignored(self):
        text = status_bar(_state("generate", deadline_in=120), _FakeModel(None))
        assert "tokens" not in text
        assert 'budget: "remaining ~' in text

    def test_broken_budget_object_is_ignored(self):
        class _Broken:
            _budget = object()  # no telemetry

        text = status_bar(_state("generate", deadline_in=120), _Broken())
        assert "tokens" not in text
