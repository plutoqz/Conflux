"""P4-B 多模型评审团（panel）：单轮独立评审 + 确定性分歧规则 + 裁判叙事。

协议（对照 docs/plans/p4/B_多模型评审团.md §3）：
- 输入为不可变 input_snapshot；成员并行单轮调用，互不可见彼此输出（无多轮辩论）。
- 成员输出 JSON 契约 + verdict 白名单校验；非法/解析失败视为弃权。
- 分歧规则由**确定性代码**汇总（裁判与模型都不能推翻票数结论）：
    - 全一致          → 维持成员置信度均值；
    - 多数 vs 少数    → 置信降一级，异议原文进 dissent sidecar；
    - 均分/不可调和   → verdict=uncertain，保留全部成员意见。
- 裁判（referee）仅在成员数 ≥ 3 时调用一次：产出分歧结构与理由的叙事摘要，
  记入 sidecar；其输出不改变确定性汇总结果。
- 预算：每成员/裁判调用前 reserve("model_calls") 1 次；成员执行不足 2 人时
  整体降级返回空 payload（由调用方走确定性兜底）。

通用性：模型实例与 preset 全部由调用方（config 驱动）传入，模块不硬编码厂商/型号。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import re
import time
from typing import Any, Sequence

from langchain_core.messages import HumanMessage, SystemMessage

from .research_prompts import (
    PANEL_ARBITRATION_MEMBER_PROMPT,
    PANEL_ARBITRATION_MEMBER_SYSTEM,
    PANEL_MEMBER_PROMPT,
    PANEL_MEMBER_SYSTEM,
    REFEREE_SYSTEM,
)
from .research_protocol import BudgetState

VERIFICATION_VERDICTS = ("supports", "contradicts", "insufficient", "uncertain")
ARBITRATION_VERDICTS = ("covered", "gap", "conflict", "uncertain")

# 角色差异化 persona：按成员序号轮换，防止提示词同质性。
PANEL_PERSONAS = (
    "strict critic: assume every claim is wrong until the evidence forces otherwise",
    "domain pragmatist: judge what the evidence can practically support",
    "risk sensitive: a wrong supports verdict is far worse than a missed one",
)

_CONFIDENCE_NOTCHES = (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)


@dataclass
class PanelReview:
    """One panel run over an immutable input snapshot."""

    input_snapshot: dict[str, Any]
    members: list[dict[str, Any]] = field(default_factory=list)
    referee: dict[str, Any] | None = None
    result: dict[str, Any] = field(default_factory=dict)
    # P2.4：成员失败/弃权显式进 trace（不再静默丢弃）。
    failures: list[dict[str, Any]] = field(default_factory=list)


def _extract_json(content: str) -> dict[str, Any]:
    """容错 JSON 提取：剥 think 块与 markdown fence；截断/坏 JSON 用
    json_repair 修复后解析（2026-08-14 真实三模型 A/B 暴露：mimo 输出
    截断 JSON、qwen 偶发空响应，缺容错会整员弃权导致评审团全 uncertain）。
    """
    text = re.sub(r"<think>.*?</think>", "", str(content or ""), flags=re.DOTALL)
    start = text.find("{")
    if start < 0:
        return {}
    candidate = text[start:]
    try:
        return json.loads(candidate)
    except Exception:
        pass
    try:
        from json_repair import repair_json

        repaired = repair_json(candidate)
        if isinstance(repaired, str):
            return json.loads(repaired)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass
    return {}


def _invoke_member(
    model: Any,
    system: str,
    prompt: str,
    budget_state: BudgetState | None,
    *,
    role: str,
) -> dict[str, Any] | None:
    """One member call with model_calls 预扣；耗尽返回 None（弃权）。"""

    if model is None:
        return None
    messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
    if budget_state is not None:
        if not budget_state.reserve("model_calls", reason=f"panel_budget_exhausted:{role}"):
            budget_state.add_drop(f"panel_member_dropped:{role}")
            return None
    started = time.perf_counter()
    try:
        response = model.invoke(messages)
    except BaseException:
        # 一次重试吸收瞬时故障/限流抖动（2026-08-14 A/B 教训：qwen 偶发空响应）
        try:
            response = model.invoke(messages)
        except BaseException:
            if budget_state is not None:
                budget_state.record_usage(None, elapsed_ms=(time.perf_counter() - started) * 1000)
            return None
    if budget_state is not None:
        budget_state.record_usage(response, elapsed_ms=(time.perf_counter() - started) * 1000)
    content = str(response.content) if hasattr(response, "content") else str(response)
    return _extract_json(content)


def _item_key(item: dict[str, Any], index: int) -> str:
    for key in ("claim_id", "subquestion_id", "claim"):
        value = str(item.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return f"index:{index}"


def _drop_one_notch(confidence: float) -> float:
    """置信度降一级：取严格低于当前值的最高档位（0.0 已到底则维持 0.0）。"""

    value = max(0.0, min(1.0, float(confidence or 0.0)))
    lower = [notch for notch in _CONFIDENCE_NOTCHES if notch < value]
    return max(lower) if lower else 0.0


def _aggregate_checks(
    member_outputs: Sequence[tuple[str, str, dict[str, Any]]],
    verdict_whitelist: Sequence[str],
    *,
    items_key: str = "checks",
) -> dict[str, Any]:
    """确定性分歧规则：按条目聚合成员票数，产出 checks + dissent sidecar。

    items_key: 成员输出中待聚合条目的键（verification="checks"、
    arbitration="judgments"）。
    """

    allowed = set(verdict_whitelist)
    votes: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for label, persona, payload in member_outputs:
        items = payload.get(items_key) or []
        if not isinstance(items, list):
            items = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            verdict = str(item.get("verdict") or "")
            if verdict not in allowed:
                verdict = "uncertain"
            key = _item_key(item, index)
            if key not in votes:
                votes[key] = []
                order.append(key)
            votes[key].append({
                "member": label,
                "persona": persona,
                "verdict": verdict,
                "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0.0))),
                "likely_verdict": str(item.get("likely_verdict") or ""),
                "reason": str(item.get("reason") or ""),
                "evidence_ids": [str(value) for value in item.get("evidence_ids") or []],
                "item": item,
            })

    checks: list[dict[str, Any]] = []
    dissent: list[dict[str, Any]] = []
    for key in order:
        opinions = votes[key]
        # v1.2 加权表态：uncertain 票必须带 likely_verdict 才计票（权重减半，
        # 表示"不确定但仍表态"）；纯 uncertain 视为弃权（权重 0）。最终取
        # 置信度加权最高的 verdict，平局/全弃权 → uncertain。
        tally: dict[str, float] = {}
        weighted: list[tuple[str, float]] = []
        for opinion in opinions:
            verdict = opinion["verdict"]
            weight = opinion["confidence"]
            if verdict == "uncertain":
                likely = str(opinion.get("likely_verdict") or "")
                if likely in allowed and likely != "uncertain":
                    verdict, weight = likely, weight * 0.5
                else:
                    weight = 0.0
            if weight > 0:
                tally[verdict] = tally.get(verdict, 0.0) + weight
                weighted.append((verdict, weight))
        claim_dissent = 0
        if not tally:
            # 全部弃权/损坏输出：宁可待核验也不误判（安全方向）。
            final_verdict, confidence = "uncertain", 0.0
        else:
            winner, winner_weight = max(tally.items(), key=lambda kv: kv[1])
            runner_up = max(
                (w for v, w in tally.items() if v != winner),
                default=0.0,
            )
            if winner_weight <= runner_up or winner_weight == 0.0:
                # 平局（含 0.5 折半导致的并列）：保留全部意见，判待核验。
                final_verdict, confidence = "uncertain", 0.0
            else:
                final_verdict = winner
                if len(tally) == 1:
                    confidence = sum(o["confidence"] for o in opinions) / len(opinions)
                else:
                    winners = [o for o in opinions
                               if (o["verdict"] == winner)
                               or (o["verdict"] == "uncertain"
                                   and str(o.get("likely_verdict") or "") == winner)]
                    mean_confidence = sum(o["confidence"] for o in winners) / len(winners)
                    confidence = _drop_one_notch(mean_confidence)
                for opinion in opinions:
                    mapped = opinion["verdict"]
                    if mapped == "uncertain":
                        likely = str(opinion.get("likely_verdict") or "")
                        mapped = likely if likely in allowed else "uncertain"
                    if mapped != final_verdict:
                        dissent.append({
                            "claim_ref": key,
                            "member": opinion["member"],
                            "verdict": opinion["verdict"],
                            "likely_verdict": opinion.get("likely_verdict"),
                            "reason": opinion["reason"],
                        })
                        claim_dissent += 1
        winner_opinions = [
            o for o in opinions
            if o["verdict"] == final_verdict
            or (o["verdict"] == "uncertain"
                and str(o.get("likely_verdict") or "") == final_verdict)
        ]
        evidence_ids: list[str] = []
        for opinion in winner_opinions:
            for value in opinion["evidence_ids"]:
                if value not in evidence_ids:
                    evidence_ids.append(value)
        base_item = next(
            (o["item"] for o in winner_opinions), opinions[0]["item"]
        )
        check = {
            **{k: v for k, v in base_item.items() if k not in {"verdict", "confidence", "reason", "evidence_ids"}},
            "verdict": final_verdict,
            "confidence": round(confidence, 3),
            "reason": (
                f"panel consensus ({len(winner_opinions)}/{len(opinions)})"
                + ("; dissent recorded" if claim_dissent else "")
            ),
            "evidence_ids": evidence_ids,
            "panel_votes": [{
                "member": o["member"],
                "persona": o["persona"],
                "verdict": o["verdict"],
                "likely_verdict": o.get("likely_verdict") or None,
                "confidence": o["confidence"],
                "reason": o["reason"],
            } for o in opinions],
        }
        checks.append(check)
    return {"checks": checks, "dissent": dissent}


def run_panel(
    members: Sequence[tuple[str, Any]],
    *,
    input_snapshot: dict[str, Any],
    referee: Any = None,
    budget_state: BudgetState | None = None,
    verdict_whitelist: Sequence[str] | None = None,
    judgment_point: str = "verification",
) -> PanelReview:
    """执行一次单轮独立评审。

    members: [(label, model), ...]，persona 按序号轮换。
    judgment_point: "verification"（claims 输入）或 "arbitration"
    （subquestions 输入；judgments 按多数票聚合 + action_proposals 按
    (subquestion_id, source) 多数采纳）。
    verdict_whitelist 缺省按 judgment_point 自动选择。
    返回 PanelReview；成员执行不足 2 人时 result 为空（调用方确定性兜底）。
    """

    if verdict_whitelist is None:
        verdict_whitelist = (
            ARBITRATION_VERDICTS if judgment_point == "arbitration" else VERIFICATION_VERDICTS
        )
    if judgment_point == "arbitration":
        return _run_arbitration_panel(
            members,
            input_snapshot=input_snapshot,
            referee=referee,
            budget_state=budget_state,
            verdict_whitelist=verdict_whitelist,
        )
    return _run_verification_panel(
        members,
        input_snapshot=input_snapshot,
        referee=referee,
        budget_state=budget_state,
        verdict_whitelist=verdict_whitelist,
    )


def _run_verification_panel(
    members: Sequence[tuple[str, Any]],
    *,
    input_snapshot: dict[str, Any],
    referee: Any = None,
    budget_state: BudgetState | None = None,
    verdict_whitelist: Sequence[str] = VERIFICATION_VERDICTS,
) -> PanelReview:
    claims_json = json.dumps(input_snapshot.get("claims") or [], ensure_ascii=False)
    snapshot_json = json.dumps(input_snapshot.get("ledger_snapshot") or {}, ensure_ascii=False)
    prompt = PANEL_MEMBER_PROMPT.format(claims_json=claims_json, snapshot_json=snapshot_json)

    def call(index: int, label: str, model: Any) -> dict[str, Any] | None:
        persona = PANEL_PERSONAS[index % len(PANEL_PERSONAS)]
        system = PANEL_MEMBER_SYSTEM.format(persona=persona)
        return _invoke_member(model, system, prompt, budget_state, role=f"panel_{index + 1}")

    review, executed = _collect_member_outputs(members, call, input_snapshot, budget_state)
    if len(executed) < 2:
        return review
    aggregated = _aggregate_checks(executed, verdict_whitelist)
    _attach_referee(referee, aggregated, review, budget_state)
    review.result = aggregated
    return review


def _run_arbitration_panel(
    members: Sequence[tuple[str, Any]],
    *,
    input_snapshot: dict[str, Any],
    referee: Any = None,
    budget_state: BudgetState | None = None,
    verdict_whitelist: Sequence[str] = ARBITRATION_VERDICTS,
) -> PanelReview:
    subquestions_json = json.dumps(input_snapshot.get("subquestions") or [], ensure_ascii=False)
    snapshot_json = json.dumps(input_snapshot.get("ledger_snapshot") or {}, ensure_ascii=False)
    prompt = PANEL_ARBITRATION_MEMBER_PROMPT.format(
        subquestions_json=subquestions_json, snapshot_json=snapshot_json
    )

    def call(index: int, label: str, model: Any) -> dict[str, Any] | None:
        persona = PANEL_PERSONAS[index % len(PANEL_PERSONAS)]
        system = PANEL_ARBITRATION_MEMBER_SYSTEM.format(persona=persona)
        return _invoke_member(model, system, prompt, budget_state, role=f"panel_arb_{index + 1}")

    review, executed = _collect_member_outputs(members, call, input_snapshot, budget_state)
    if len(executed) < 2:
        return review
    aggregated = _aggregate_checks(executed, verdict_whitelist, items_key="judgments")
    aggregated["action_proposals"] = _aggregate_action_proposals(executed)
    _attach_referee(referee, aggregated, review, budget_state)
    review.result = aggregated
    return review


def _collect_member_outputs(
    members: Sequence[tuple[str, Any]],
    call,
    input_snapshot: dict[str, Any],
    budget_state: BudgetState | None,
) -> tuple[PanelReview, list[tuple[str, str, dict[str, Any]]]]:
    member_models = [(str(label), model) for label, model in members]
    outputs: list[dict[str, Any] | None]
    if len(member_models) > 1:
        with ThreadPoolExecutor(max_workers=len(member_models)) as pool:
            futures = [
                pool.submit(call, index, label, model)
                for index, (label, model) in enumerate(member_models)
            ]
            outputs = [future.result() for future in futures]
    else:
        outputs = [call(0, *member_models[0])] if member_models else []

    review = PanelReview(input_snapshot=input_snapshot)
    executed: list[tuple[str, str, dict[str, Any]]] = []
    for index, ((label, _model), payload) in enumerate(zip(member_models, outputs)):
        if payload is None or not isinstance(payload, dict):
            # P2.4：失败/弃权进入 trace（空响应/异常/预算耗尽/坏 JSON）。
            review.failures.append({
                "label": label,
                "persona": PANEL_PERSONAS[index % len(PANEL_PERSONAS)],
                "reason": "member_failed_or_abstained",
            })
            continue
        executed.append((label, PANEL_PERSONAS[index % len(PANEL_PERSONAS)], payload))
    review.members = [
        {"label": label, "persona": persona, **payload}
        for label, persona, payload in executed
    ]
    return review, executed


def _attach_referee(
    referee: Any,
    aggregated: dict[str, Any],
    review: PanelReview,
    budget_state: BudgetState | None,
) -> None:
    referee_record: dict[str, Any] | None = None
    if referee is not None and len(review.members) >= 3:
        referee_record = _invoke_referee(referee, aggregated, budget_state)
        aggregated["referee"] = referee_record
    review.referee = referee_record


def _aggregate_action_proposals(
    member_outputs: Sequence[tuple[str, str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """action_proposals 按 (subquestion_id, source, trigger) 多数采纳。

    每成员对同一 (subquestion_id, source, trigger) 至多记一票；
    仅当提出成员数 > 未提出成员数（严格多数）才采纳，避免单个弱模型
    的噪声提案消耗检索预算。query 取多数派第一个非空文本。
    """

    total = max(1, len(member_outputs))
    votes: dict[tuple[str, str, str], dict[str, Any]] = {}
    for label, _persona, payload in member_outputs:
        for item in payload.get("action_proposals") or []:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("subquestion_id") or ""),
                str(item.get("source") or ""),
                str(item.get("trigger") or ""),
            )
            if not all(key):
                continue
            entry = votes.setdefault(key, {"_votes": set(), "query": str(item.get("query") or "").strip()})
            entry["_votes"].add(label)
            if not entry["query"]:
                entry["query"] = str(item.get("query") or "").strip()
    adopted = []
    for (subquestion_id, source, trigger), entry in sorted(votes.items()):
        if len(entry["_votes"]) * 2 > total:
            adopted.append({
                "subquestion_id": subquestion_id,
                "source": source,
                "trigger": trigger,
                "query": entry["query"],
                "members": sorted(entry["_votes"]),
            })
    return adopted


def _invoke_referee(
    referee: Any,
    aggregated: dict[str, Any],
    budget_state: BudgetState | None,
) -> dict[str, Any] | None:
    """裁判一次调用：只产出分歧结构叙事，不改变票数结论。"""

    prompt = json.dumps(
        {
            "tallied_checks": aggregated.get("checks") or [],
            "dissent": aggregated.get("dissent") or [],
        },
        ensure_ascii=False,
    )
    payload = _invoke_member(referee, REFEREE_SYSTEM, prompt, budget_state, role="panel_referee")
    if not isinstance(payload, dict):
        return None
    return {"narrative": str(payload.get("narrative") or ""), "raw": payload}
