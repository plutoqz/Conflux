"""P4-B 多模型评审团测试（对照 docs/plans/p4/B_多模型评审团.md B1–B5 验收表）。

覆盖：协议解析（B1）、异构 roster 校验（B1）、成员 max_tokens 减半与 quick 档
无 panel 模型（B2）、分歧三态与白名单校验与互不可见与裁判约束（B3）、
verification 挂载 + 确定性优先 panel 版本断言 + quick 零回归（B4）、
model_calls 硬上限与耗尽降级（B5）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.graph_v2 import (  # noqa: E402
    _new_state,
    verification_node,
)
from conflux.panel import run_panel  # noqa: E402
from conflux.research_modes import (  # noqa: E402
    resolve_research_profile,
    validate_research_model_profiles,
)
from conflux.research_protocol import BudgetState, EvidenceLedger  # noqa: E402


class _PanelModel:
    """Fake member model：记录收到的消息，返回固定 JSON payload。"""

    def __init__(self, payload: dict, *, label: str = ""):
        self.payload = payload
        self.label = label
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        return SimpleNamespace(content=json.dumps(self.payload))


def _members(*specs):
    return [(label, model) for label, model in specs]


def _snapshot() -> dict:
    return {
        "claims": [
            {
                "claim_id": "run-panel:claim:sq-1:01",
                "claim": "atomic claim",
                "evidence_ids": [],
            },
        ],
        "ledger_snapshot": {"snapshot_id": "run-panel:snapshot-1", "records": []},
    }


def _check(verdict: str, confidence: float, reason: str = "") -> dict:
    return {
        "checks": [{
            "claim_id": "run-panel:claim:sq-1:01",
            "claim": "atomic claim",
            "verdict": verdict,
            "confidence": confidence,
            "evidence_ids": [],
            "reason": reason,
        }],
    }


# ============================================================
# B1 协议解析 + 异构校验
# ============================================================

class TestPanelConfig:
    def test_quick_depth_forces_panel_off(self):
        assert resolve_research_profile("quick").panel_enabled is False
        assert resolve_research_profile("standard").panel_enabled is True
        assert resolve_research_profile("deep").panel_enabled is True

    def test_profile_parses_roster_and_referee(self):
        standard = resolve_research_profile("standard")
        # v1.1 真异构 roster：verification 强+中 2 成员；referee 最强模型
        assert standard.panel_members("verification") == ["ds_strong", "mimo"]
        assert standard.panel_referee == "ds_strong"
        deep = resolve_research_profile("deep")
        assert deep.panel_members("arbitration") == ["ds_strong", "mimo", "qwen_weak"]

    def test_default_config_passes_validation(self):
        assert validate_research_model_profiles() == []

    def test_heterogeneous_roster_rejects_same_preset(self, monkeypatch):
        import conflux.research_modes as rm
        from conflux import config

        real_get = config.get
        fake_panel = {
            "enabled_by_depth": {"quick": False, "standard": True, "deep": True},
            "roster": {"verification": ["flash", "flash"]},  # 同一 preset 伪多样性
            "referee": "balanced",
            "quorum": "majority",
        }

        def patched_get(*path, default=None):
            if path[:2] == ("research", "panel"):
                return fake_panel
            return real_get(*path, default=default)

        monkeypatch.setattr(rm, "get", patched_get)
        problems = validate_research_model_profiles()
        assert any("必须来自不同 preset" in problem for problem in problems)

    def test_heterogeneous_roster_rejects_same_resolved_model(self, monkeypatch):
        """v1.1：preset 不同但解析后 (provider, model) 相同 → 伪多样性被拒。"""
        import conflux.research_modes as rm
        from conflux import config

        real_get = config.get
        fake_panel = {
            "enabled_by_depth": {"quick": False, "standard": True, "deep": True},
            "roster": {"verification": ["flash", "balanced"]},  # 不同 preset
            "referee": "balanced",
            "quorum": "majority",
        }
        # flash/balanced 都指向同一模型（历史伪多样性场景）
        fake_models = {
            "flash": {"provider": "openai_compatible", "model": "same-model-x"},
            "balanced": {"provider": "openai_compatible", "model": "same-model-x"},
        }

        def patched_get(*path, default=None):
            if path[:2] == ("research", "panel"):
                return fake_panel
            if path[:1] == ("models",) and len(path) == 2:
                return fake_models.get(path[1], default)
            return real_get(*path, default=default)

        monkeypatch.setattr(rm, "get", patched_get)
        problems = validate_research_model_profiles()
        assert any("(provider, model) 必须互异" in problem for problem in problems)

    def test_unsupported_quorum_rejected(self, monkeypatch):
        import conflux.research_modes as rm
        from conflux import config

        real_get = config.get
        fake_panel = {
            "enabled_by_depth": {"quick": False, "standard": True, "deep": True},
            "roster": {"verification": ["verifier", "balanced"]},
            "referee": "balanced",
            "quorum": "unanimous",
        }

        def patched_get(*path, default=None):
            if path[:2] == ("research", "panel"):
                return fake_panel
            return real_get(*path, default=default)

        monkeypatch.setattr(rm, "get", patched_get)
        problems = validate_research_model_profiles()
        assert any("quorum" in problem for problem in problems)


# ============================================================
# B2 模型层
# ============================================================

class TestPanelModelConstruction:
    def _fake_construction_models(self, monkeypatch):
        """构造层测试只验证 roster/token 派生，不构造真实 ChatOpenAI 客户端。

        真实客户端在无 API key 的环境（CI、干净 checkout）会在构造期抛
        OpenAIError；用 max_tokens 占位对象替换 create_chat_model，断言仍然
        覆盖 create_research_models 的成员数、标签与 max_tokens 减半逻辑。
        """
        from conflux import model_factory

        monkeypatch.setattr(
            model_factory,
            "create_chat_model",
            lambda _preset, **kwargs: SimpleNamespace(
                max_tokens=kwargs.get("max_tokens"),
            ),
        )
        return model_factory

    def test_quick_creates_no_panel_models(self, monkeypatch):
        model_factory = self._fake_construction_models(monkeypatch)
        _, diagnostics = model_factory.create_research_models("quick")
        assert diagnostics.get("panel_models") == {}

    def test_deep_member_max_tokens_halved(self, monkeypatch):
        model_factory = self._fake_construction_models(monkeypatch)
        profile = resolve_research_profile("deep")
        _, diagnostics = model_factory.create_research_models("deep")
        panel = diagnostics.get("panel_models") or {}
        verification = panel.get("verification") or {}
        members = verification.get("members") or []
        assert len(members) == 2
        expected = max(300, profile.verifier_max_tokens // 2)
        assert [label for label, _member in members] == profile.panel_members("verification")
        assert all(member.max_tokens == expected for _label, member in members)
        assert verification.get("referee") is not None
        assert verification["referee"].max_tokens == expected
        # deep 档第二判断点（arbitration）成员来自 reasoning + flash
        arbitration = panel.get("arbitration") or {}
        arbitration_members = arbitration.get("members") or []
        assert [label for label, _member in arbitration_members] == profile.panel_members("arbitration")

    def test_standard_and_deep_factory_panels_run_through_verification(
        self,
        monkeypatch,
    ):
        import conflux.model_factory as model_factory

        class FactoryPanelModel(_PanelModel):
            def __init__(self, *, max_tokens: int):
                super().__init__(_check("supports", 0.9))
                self.max_tokens = max_tokens

            def invoke(self, messages, **_kwargs):
                return super().invoke(messages)

        monkeypatch.setattr(
            model_factory,
            "create_chat_model",
            lambda _preset, **kwargs: FactoryPanelModel(max_tokens=kwargs["max_tokens"]),
        )

        for depth in ("standard", "deep"):
            models, diagnostics = model_factory.create_research_models(depth)
            result = verification_node(
                _panel_triggered_state(depth=depth),
                models["verifier"],
                panel=diagnostics["panel_models"]["verification"],
            )
            verification = result["_claim_records"][0]["verification_result"]
            # P2.4 触发后成员全票 supports；B4.3 确定性优先：uncertain 不被
            # supports 推翻，但 panel sidecar 与成员票完整保留。
            assert verification["verdict"] == "uncertain"
            assert verification["verifier_version"] == "rules-v1"
            assert verification.get("model_verdict") == "supports"
            assert len(verification["panel"]["members"]) == 2


# ============================================================
# B3 分歧规则 / 白名单 / 互不可见 / 裁判约束
# ============================================================

class TestRunPanel:
    def test_unanimous_keeps_confidence(self):
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"
        assert check["confidence"] == 0.9
        assert review.result.get("dissent") == []

    def test_majority_drops_one_notch_and_records_dissent(self):
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
                ("c", _PanelModel(_check("insufficient", 0.8, reason="异议原文"))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"
        assert check["confidence"] == 0.8  # 0.9 降一级
        dissent = review.result["dissent"]
        assert len(dissent) == 1
        assert dissent[0]["member"] == "c"
        assert dissent[0]["reason"] == "异议原文"

    def test_split_is_uncertain_and_keeps_all_opinions(self):
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9, reason="opinion-a"))),
                ("b", _PanelModel(_check("contradicts", 0.9, reason="opinion-b"))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "uncertain"
        assert check["confidence"] == 0.0
        assert {vote["member"] for vote in check["panel_votes"]} == {"a", "b"}
        assert {vote["reason"] for vote in check["panel_votes"]} == {"opinion-a", "opinion-b"}

    def test_verdict_whitelist_rejects_unknown_verdict(self):
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("hallucinated", 0.9))),
            ),
            input_snapshot=_snapshot(),
        )
        # 非法 verdict 视为弃权票（权重 0）→ 唯一表态者胜出（v1.2 强制表态）
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"
        assert {vote["verdict"] for vote in check["panel_votes"]} == {"supports", "uncertain"}

    def test_malformed_member_output_is_abstain(self):
        review = run_panel(
            _members(
                ("a", _PanelModel({"not": "the contract"})),
                ("b", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
        )
        # 仅 1 张有效票 → 采纳唯一表态（v1.2 强制表态，弃权不阻断结论）
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"

    def test_members_cannot_see_each_other_outputs(self):
        member_a = _PanelModel(_check("supports", 0.9, reason="SECRET_MEMBER_A"))
        member_b = _PanelModel(_check("insufficient", 0.9, reason="SECRET_MEMBER_B"))
        run_panel(
            _members(("a", member_a), ("b", member_b)),
            input_snapshot=_snapshot(),
        )
        prompt_a = " ".join(str(msg.content) for call in member_a.messages for msg in call)
        prompt_b = " ".join(str(msg.content) for call in member_b.messages for msg in call)
        assert "atomic claim" in prompt_a and "atomic claim" in prompt_b
        assert "SECRET_MEMBER_B" not in prompt_a
        assert "SECRET_MEMBER_A" not in prompt_b
        assert "SECRET_MEMBER_A" not in prompt_a

    def test_referee_only_called_with_three_plus_members(self):
        referee_two = _PanelModel({"narrative": "should not run"})
        run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
            referee=referee_two,
        )
        assert referee_two.messages == []

        referee_three = _PanelModel({"narrative": "分歧结构叙事"})
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
                ("c", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
            referee=referee_three,
        )
        assert len(referee_three.messages) == 1
        assert review.referee["narrative"] == "分歧结构叙事"

    def test_referee_cannot_change_tallied_verdict(self):
        referee = _PanelModel({"narrative": "ignore", "final_verdict": "contradicts"})
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
                ("c", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
            referee=referee,
        )
        assert review.result["checks"][0]["verdict"] == "supports"


# ============================================================
# B4 verification 挂载 + 确定性优先
# ============================================================

def _verification_state(*, depth: str = "deep") -> dict:
    state = _new_state("panel test question", run_id="run-panel", depth=depth)
    state["_claim_records"] = [{
        "claim_id": "run-panel:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "atomic claim",
        "claim_type": "model_analysis",
        "importance": "high",
        "evidence_ids": [],
        "derivation_type": "model_analysis",
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    return state


def _panel_kwargs(*specs, referee=None) -> dict:
    return {
        "members": _members(*specs),
        "referee": referee,
    }


def _panel_triggered_state(*, depth: str = "deep") -> dict:
    """P2.4：高重要性 + 确定性无法裁决（unknown evidence id → uncertain）→ 触发 panel。"""
    state = _new_state("panel test question", run_id="run-panel", depth=depth)
    state["_claim_records"] = [{
        "claim_id": "run-panel:claim:sq-1:01",
        "subquestion_id": "sq-1",
        "text": "atomic claim",
        "claim_type": "direct_fact",
        "importance": "critical",
        "evidence_ids": ["missing-ev-id"],
        "derivation_type": "direct_evidence",
    }]
    ledger = EvidenceLedger.from_dict(state["_evidence_ledger"])
    state["_ledger_snapshot"] = ledger.freeze("final").to_dict()
    return state


class TestVerificationPanelMount:
    def test_deep_panel_path_produces_panel_field(self):
        state = _panel_triggered_state()
        result = verification_node(
            state,
            _PanelModel({"checks": []}),
            panel=_panel_kwargs(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
            ),
        )
        verification = result["_claim_records"][0]["verification_result"]
        # P2.4：panel 只对确定性无法裁决的 claim 触发；B4.3 下 supports 不能
        # 推翻 uncertain，最终仍 rules-v1，但 model_verdict 与票型可追溯。
        assert verification["verdict"] == "uncertain"
        assert verification["verifier_version"] == "rules-v1"
        assert verification.get("model_verdict") == "supports"
        panel = verification["panel"]
        assert len(panel["members"]) == 2
        assert panel["dissent"] == []
        assert panel["referee"] is None
        # JudgmentRecord payload 同样携带 panel sidecar（可追溯）
        judgment = result["_evidence_ledger"]["judgments"][0]
        assert "panel" in judgment["payload"]

    def test_panel_supports_cannot_override_deterministic_uncertain(self):
        state = _panel_triggered_state()
        result = verification_node(
            state,
            _PanelModel({"checks": []}),
            panel=_panel_kwargs(
                ("a", _PanelModel(_check("supports", 1.0))),
                ("b", _PanelModel(_check("supports", 1.0))),
            ),
        )
        verification = result["_claim_records"][0]["verification_result"]
        # 确定性裁决优先：panel 全票 supports 也不能推翻 uncertain
        assert verification["verdict"] == "uncertain"
        assert verification["verifier_version"] == "rules-v1"
        assert verification.get("model_verdict") == "supports"

    def test_deterministically_adjudicated_claims_skip_panel(self):
        """P2.4：确定性可裁决或低重要性的 claim 不触发 panel，零成员调用。"""
        state = _verification_state()  # model_analysis → deterministic supports
        result = verification_node(
            state,
            _PanelModel({"checks": []}),
            panel=_panel_kwargs(
                ("a", _PanelModel(_check("supports", 1.0))),
                ("b", _PanelModel(_check("supports", 1.0))),
            ),
        )
        verification = result["_claim_records"][0]["verification_result"]
        assert verification["verdict"] == "supports"
        assert verification["verifier_version"] == "rules-v1"
        assert "panel" not in verification
        trace = result["_model_verification"]["panel"]["trigger_trace"]
        assert trace[0]["panel_triggered"] is False
        assert trace[0]["reason"] == "panel_skipped:deterministic_adjudicated"
        assert result["_model_verification"]["panel"]["members"] == []

        # 低重要性 + 确定性无法裁决 → 同样跳过（low_importance）
        low_state = _panel_triggered_state()
        low_state["_claim_records"][0]["importance"] = "medium"
        low_result = verification_node(
            low_state,
            _PanelModel({"checks": []}),
            panel=_panel_kwargs(
                ("a", _PanelModel(_check("supports", 1.0))),
                ("b", _PanelModel(_check("supports", 1.0))),
            ),
        )
        low_trace = low_result["_model_verification"]["panel"]["trigger_trace"]
        assert low_trace[0]["panel_triggered"] is False
        assert low_trace[0]["reason"] == "panel_skipped:low_importance"

    def test_quick_single_verifier_path_unchanged(self):
        state = _verification_state()
        result = verification_node(
            state,
            _PanelModel(_check("supports", 0.9)),
        )
        verification = result["_claim_records"][0]["verification_result"]
        assert verification["verdict"] == "supports"
        assert "panel" not in verification


# ============================================================
# B5 预算硬上限与耗尽降级
# ============================================================

class TestPanelBudget:
    def test_panel_calls_never_exceed_model_calls_limit(self):
        budget = BudgetState.for_depth("deep")
        budget.hard_limits["model_calls"] = 10
        budget.model_calls = 8  # 只剩 2 次额度
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.9))),
                ("b", _PanelModel(_check("supports", 0.9))),
                ("c", _PanelModel(_check("supports", 0.9))),
            ),
            input_snapshot=_snapshot(),
            referee=_PanelModel({"narrative": "no budget"}),
            budget_state=budget,
        )
        assert budget.model_calls <= budget.hard_limits["model_calls"]
        assert budget.model_calls == 10
        assert any("panel_member_dropped" in reason for reason in budget.dropped_reasons)
        # 恰好 2 名成员执行 → 仍走多数票路径
        assert review.result["checks"][0]["verdict"] == "supports"

    def test_budget_exhausted_degrades_to_deterministic_fallback(self):
        budget = BudgetState.for_depth("deep")
        budget.hard_limits["model_calls"] = 4
        budget.model_calls = 4  # 额度已尽
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 1.0))),
                ("b", _PanelModel(_check("supports", 1.0))),
            ),
            input_snapshot=_snapshot(),
            budget_state=budget,
        )
        assert review.result == {}
        assert any("panel_budget_exhausted" in reason for reason in budget.degradation_reasons)

    def test_verification_falls_back_to_deterministic_when_panel_degrades(self):
        state = _verification_state()
        budget = BudgetState.for_depth("deep")
        # BudgetState 语义：hard_limits 为 0 表示不限制；用满额度模拟耗尽。
        budget.hard_limits["model_calls"] = 4
        budget.model_calls = 4
        state["_budget_state"] = budget.to_dict()
        result = verification_node(
            state,
            _PanelModel({"checks": []}),
            panel=_panel_kwargs(
                ("a", _PanelModel(_check("supports", 1.0))),
                ("b", _PanelModel(_check("supports", 1.0))),
            ),
        )
        verification = result["_claim_records"][0]["verification_result"]
        assert verification["verdict"] == "supports"  # model_analysis 确定性放行
        assert verification["verifier_version"] == "rules-v1"


# ============================================================
# B3.1 arbitration 判断点（v1.1）
# ============================================================

class TestArbitrationPanel:
    def _arb_state(self) -> dict:
        state = _new_state("arbitration panel test")
        state["_run_id"] = "r-arb"
        state["_sub_questions"] = [
            {"id": "sq-1", "question": "q1", "importance": "high"},
            {"id": "sq-2", "question": "q2", "importance": "medium"},
        ]
        state["_ledger_snapshot"] = {
            "snapshot_id": "s1",
            "records": [{"evidence_id": "e1", "claim": "c", "source_identity": "src", "evidence_class": "x"}],
        }
        return state

    def _judgments(self, verdict_by_sq: dict, proposals: list | None = None) -> dict:
        return {
            "judgments": [
                {"subquestion_id": sq, "verdict": v, "reason": "r", "confidence": 0.8}
                for sq, v in verdict_by_sq.items()
            ],
            "action_proposals": proposals or [],
        }

    def test_arbitration_majority_and_proposal_majority(self):
        from conflux.graph_v2 import arbitration_node

        state = self._arb_state()
        panel = {
            "members": [
                ("ds_strong", _PanelModel(self._judgments({"sq-1": "gap", "sq-2": "covered"},
                                                          [{"subquestion_id": "sq-1", "source": "RAG", "query": "q?", "trigger": "no_evidence"}]))),
                ("mimo", _PanelModel(self._judgments({"sq-1": "gap", "sq-2": "uncertain"},
                                                     [{"subquestion_id": "sq-1", "source": "RAG", "query": "q?", "trigger": "no_evidence"}]))),
                ("qwen_weak", _PanelModel(self._judgments({"sq-1": "covered", "sq-2": "covered"}, []))),
            ],
            "referee": None,
        }
        out = arbitration_node(state, None, panel=panel)
        arb = out["_model_arbitration"]
        assert arb["status"] == "completed"
        js = {j["subquestion_id"]: j["verdict"] for j in arb["judgments"]}
        assert js == {"sq-1": "gap", "sq-2": "covered"}, js  # 2/3 多数
        # action_proposals 仅采纳 2 名成员共同提出的 sq-1（多数制）
        assert len(arb["action_proposals"]) == 1
        assert arb["action_proposals"][0]["subquestion_id"] == "sq-1"
        assert arb["action_proposals"][0]["members"] == ["ds_strong", "mimo"]
        assert "panel" in arb

    def test_arbitration_single_member_proposal_not_adopted(self):
        from conflux.graph_v2 import arbitration_node

        state = self._arb_state()
        panel = {
            "members": [
                ("ds_strong", _PanelModel(self._judgments({"sq-1": "gap"}, [{"subquestion_id": "sq-1", "source": "Web", "query": "w?", "trigger": "no_evidence"}]))),
                ("mimo", _PanelModel(self._judgments({"sq-1": "covered"}, []))),
                ("qwen_weak", _PanelModel(self._judgments({"sq-1": "gap"}, []))),
            ],
            "referee": None,
        }
        out = arbitration_node(state, None, panel=panel)
        arb = out["_model_arbitration"]
        js = {j["subquestion_id"]: j["verdict"] for j in arb["judgments"]}
        assert js == {"sq-1": "gap"}  # 2/3
        # Web 提案只有 ds_strong 提出（1/3），不采纳，避免噪声消耗检索预算
        assert arb["action_proposals"] == []

    def test_arbitration_no_panel_regression_single_model(self):
        from conflux.graph_v2 import arbitration_node

        state = self._arb_state()
        out = arbitration_node(state, None, panel=None)
        arb = out["_model_arbitration"]
        assert arb["status"] == "unavailable"  # 无 model 且无 panel → 空

    def test_arbitration_whitelist_filters_invalid_proposals(self):
        from conflux.graph_v2 import arbitration_node

        state = self._arb_state()
        panel = {
            "members": [
                ("ds_strong", _PanelModel(self._judgments({"sq-1": "gap"},
                                                          [{"subquestion_id": "sq-1", "source": "RAG", "query": "q?", "trigger": "no_evidence"},
                                                           {"subquestion_id": "sq-1", "source": "Bogus", "query": "x", "trigger": "bad"}]))),
                ("mimo", _PanelModel(self._judgments({"sq-1": "gap"},
                                                     [{"subquestion_id": "sq-1", "source": "RAG", "query": "q?", "trigger": "no_evidence"}]))),
            ],
            "referee": None,
        }
        out = arbitration_node(state, None, panel=panel)
        arb = out["_model_arbitration"]
        # 白名单校验：Bogus/bad 提案被拒；RAG 提案 2/2 成员 → 采纳
        assert len(arb["action_proposals"]) == 1
        assert arb["action_proposals"][0]["source"] == "RAG"


class TestJsonTolerance:
    def test_truncated_json_repaired(self):
        from conflux.panel import _extract_json
        # mimo 截断 JSON 场景
        payload = _extract_json('{"checks": [{"claim_id": "c1", "verdict": "contradicts", "confidence": 1.0')
        assert payload == {"checks": [{"claim_id": "c1", "verdict": "contradicts", "confidence": 1.0}]}

    def test_markdown_fence_stripped(self):
        from conflux.panel import _extract_json
        payload = _extract_json('```json\n{"checks": [{"claim_id": "c1", "verdict": "supports"}]}\n```')
        assert payload.get("checks")[0]["verdict"] == "supports"

    def test_think_block_stripped_then_repaired(self):
        from conflux.panel import _extract_json
        payload = _extract_json('<think>reasoning...</think>\n{"checks": [{"claim_id": "c1", "verdict": "uncertain"')
        assert payload.get("checks")[0]["verdict"] == "uncertain"

    def test_garbage_returns_empty(self):
        from conflux.panel import _extract_json
        assert _extract_json("no json here") == {}


class TestWeightedStance:
    """v1.2 强制表态协议：uncertain 必须带 likely_verdict 才计票（权重减半）。"""

    def _uncertain_check(self, likely: str, confidence: float) -> dict:
        return {
            "checks": [{
                "claim_id": "run-panel:claim:sq-1:01",
                "claim": "atomic claim",
                "verdict": "uncertain",
                "likely_verdict": likely,
                "confidence": confidence,
                "evidence_ids": [],
                "reason": "unsure but leaning",
            }],
        }

    def test_uncertain_with_likely_verdict_joins_tally_half_weight(self):
        # supports 0.8 直接表态 vs uncertain(lean contradicts) 0.9 → 0.45 加权
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.8))),
                ("b", _PanelModel(self._uncertain_check("contradicts", 0.9))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"  # 0.8 > 0.45

    def test_uncertain_without_likely_verdict_is_abstain(self):
        # 纯 uncertain（无 likely_verdict）→ 弃权，唯一表态者胜出
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("insufficient", 0.7))),
                ("b", _PanelModel({"checks": [{
                    "claim_id": "run-panel:claim:sq-1:01",
                    "claim": "atomic claim",
                    "verdict": "uncertain",
                    "confidence": 0.9,
                    "evidence_ids": [],
                }]})),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "insufficient"

    def test_likely_verdict_winner_marks_dissent(self):
        # a: supports 0.6；b: uncertain(lean insufficient) 0.9 → 0.45；c: supports 0.7
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.6))),
                ("b", _PanelModel(self._uncertain_check("insufficient", 0.9))),
                ("c", _PanelModel(_check("supports", 0.7))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "supports"  # 1.3 > 0.45
        dissent = review.result["dissent"]
        assert len(dissent) == 1
        assert dissent[0]["member"] == "b"
        assert dissent[0]["likely_verdict"] == "insufficient"

    def test_weighted_tie_stays_uncertain(self):
        # supports 0.5 vs uncertain(lean contradicts) 0.9→0.45 不相上下不触发；
        # 用支持 0.5 vs 0.5 直接平局验证
        review = run_panel(
            _members(
                ("a", _PanelModel(_check("supports", 0.5))),
                ("b", _PanelModel(_check("contradicts", 0.5))),
            ),
            input_snapshot=_snapshot(),
        )
        check = review.result["checks"][0]
        assert check["verdict"] == "uncertain"
