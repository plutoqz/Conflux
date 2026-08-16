#!/usr/bin/env python
"""P4-B 评审团 A/B 评测：同证据快照下「单 verifier vs 评审团」对照。

数据：claims-gold JSONL，每行 schema：
  {"case_id", "claims": [{"claim_id","claim","evidence_ids","gold_verdict"}],
   "snapshot": {"records": [{"evidence_id","claim","source_identity","evidence_class"}]}}

指标（对齐 docs/plans/p4/B_多模型评审团.md §6）：
  - 误判率：gold ∈ {insufficient, contradicts, uncertain} 但模型判 supports 的占比
    （另报全量不一致率与反向误判；并给出 95% Wilson 置信区间——小样本 n 下 0%
    的区间往往很宽，勿把点估计读作承诺）；
  - 待核验率：模型判 uncertain 的占比（含缺省对齐）；
  - token 成本：两臂 input/output tokens（BudgetState 记账）；
  - 延迟：每臂墙钟时间（panel 成员并行），多 repeats 取 P95。

默认化决策（写入报告 + JSON artifact）：
  误判率下降或持平 且 成本增量 ≤1.5× → default；否则 deep_optional。

用法：
  python scripts/p4_panel_ab.py \
      --gold evaluation/p4_panel_ab/verification_claims_gold.jsonl \
      [--depth deep] [--real | --offline] [--repeats 3] \
      [--single-preset ds_strong] \
      [--out reports/evaluation/p4/b_panel_ab_20260813.md]

注意：--real 模式下 single 臂默认与 panel 首成员同模型（控制变量，避免
模型差异混入评审团机制对比）；如需复现旧行为可显式 --single-preset <preset>。
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.graph_v2 import _invoke_json  # noqa: E402
from conflux.panel import run_panel  # noqa: E402
from conflux.research_prompts import VERIFICATION_PROMPT, VERIFICATION_SYSTEM  # noqa: E402
from conflux.research_protocol import BudgetState  # noqa: E402

VERDICTS = ("supports", "contradicts", "insufficient", "uncertain")


def load_gold(path: str) -> list[dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        assert isinstance(row.get("claims"), list) and row["claims"], f"bad gold row: {row.get('case_id')}"
    return rows


def _claims_payload(row: dict) -> list[dict]:
    return [
        {
            "claim_id": str(item.get("claim_id") or ""),
            "claim": str(item.get("claim") or ""),
            "evidence_ids": [str(value) for value in item.get("evidence_ids") or []],
        }
        for item in row["claims"]
    ]


def _align(checks: list[dict], claims: list[dict]) -> dict[str, str]:
    by_id = {str(item.get("claim_id") or ""): item for item in checks}
    by_text = {str(item.get("claim") or "").strip(): item for item in checks}
    aligned = {}
    for claim in claims:
        item = by_id.get(claim["claim_id"]) or by_text.get(claim["claim"].strip()) or {}
        verdict = str(item.get("verdict") or "")
        aligned[claim["claim_id"]] = verdict if verdict in VERDICTS else "uncertain"
    return aligned


def wilson_95(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (robust at p=0)."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    z = 1.96
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(max(0.0, p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _token_cost(budget: BudgetState) -> int:
    return budget.input_tokens + budget.output_tokens


def _metric_rows(row: dict, single: dict[str, str], panel: dict[str, str]) -> list[dict]:
    rows = []
    for claim in row["claims"]:
        gold = str(claim.get("gold_verdict") or "uncertain")
        s = single.get(claim["claim_id"], "uncertain")
        p = panel.get(claim["claim_id"], "uncertain")
        rows.append({
            "claim_id": claim["claim_id"],
            "gold": gold,
            "single": s,
            "panel": p,
            "single_misjudged": s == "supports" and gold != "supports",
            "panel_misjudged": p == "supports" and gold != "supports",
        })
    return rows


def _aggregate(rows: list[dict], single_costs: list[int], panel_costs: list[int],
               single_latencies: list[float], panel_latencies: list[float]) -> dict:
    def rate(predicate: str) -> float:
        hits = sum(1 for row in rows if row[predicate])
        return round(hits / len(rows), 4) if rows else 0.0

    def share(arm: str, verdict: str) -> float:
        hits = sum(1 for row in rows if row[arm] == verdict)
        return round(hits / len(rows), 4) if rows else 0.0

    def p95(values: list[float]) -> float:
        if not values:
            return 0.0
        if len(values) < 20:
            return round(max(values), 3)
        return round(statistics.quantiles(values, n=100, method="inclusive")[94], 3)

    single_cost = int(statistics.mean(single_costs)) if single_costs else 0
    panel_cost = int(statistics.mean(panel_costs)) if panel_costs else 0
    cost_ratio = round(panel_cost / single_cost, 3) if single_cost else 0.0
    single_mis = sum(1 for row in rows if row["single_misjudged"])
    panel_mis = sum(1 for row in rows if row["panel_misjudged"])
    single_ci, panel_ci = wilson_95(single_mis, len(rows)), wilson_95(panel_mis, len(rows))
    misjudge_ok = panel_mis <= single_mis
    cost_ok = cost_ratio <= 1.5 or single_cost == 0
    return {
        "n_claims": len(rows),
        "misjudge_rate": {"single": rate("single_misjudged"), "panel": rate("panel_misjudged")},
        "misjudge_ci95": {"single": [round(v, 4) for v in single_ci], "panel": [round(v, 4) for v in panel_ci]},
        "misjudge_n": {"single": single_mis, "panel": panel_mis},
        "mismatch_rate": {
            "single": round(
                sum(1 for row in rows if row["single"] != row["gold"] and row["single"] != "uncertain") / len(rows), 4),
            "panel": round(
                sum(1 for row in rows if row["panel"] != row["gold"] and row["panel"] != "uncertain") / len(rows), 4),
        },
        "uncertain_rate": {"single": share("single", "uncertain"), "panel": share("panel", "uncertain")},
        "token_cost": {"single": single_cost, "panel": panel_cost, "ratio": cost_ratio},
        "latency_p95_seconds": {"single": p95(single_latencies), "panel": p95(panel_latencies)},
        "default_decision": (
            "default" if (misjudge_ok and cost_ok) else "deep_optional"
        ),
        "default_conditions": {
            "misjudge_not_worse": misjudge_ok,
            "cost_within_1_5x": cost_ok,
        },
    }


class _OfflineModel:
    """确定性离线模型（管道验证用，非真实模型质量证据）。

    - lenient：有 evidence_ids 即判 supports（会误判语境/off-domain 证据）；
    - strict：只有证据原文直接陈述局限（"cannot scale"/"append-only"/…）才判
      supports，overclaim（"guarantees"）判 contradicts，其余 insufficient。
    """

    _DIRECT_LIMITATION = ("cannot scale", "saturates", "impossible", "retroactive correction", "append-only")

    def __init__(self, *, lenient: bool):
        self.lenient = lenient
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        prompt = " ".join(str(msg.content) for msg in messages)
        claims_raw = prompt.split("Atomic claims:\n", 1)[1].split("\n\nFinal immutable", 1)[0]
        snapshot_raw = prompt.split("Ledger snapshot:\n", 1)[1].split("\n\nUse only", 1)[0]
        claims = json.loads(claims_raw)
        snapshot = json.loads(snapshot_raw)
        records = {
            str(record.get("evidence_id") or ""): str(record.get("claim") or "")
            for record in snapshot.get("records") or []
        }
        checks = []
        for claim in claims:
            texts = [records.get(str(eid), "") for eid in claim.get("evidence_ids") or []]
            if self.lenient:
                verdict = "supports" if claim.get("evidence_ids") else "insufficient"
            elif any("guarantees" in text for text in texts if text):
                verdict = "contradicts"
            elif any(
                any(marker in text for marker in self._DIRECT_LIMITATION)
                for text in texts if text
            ):
                verdict = "supports"
            else:
                verdict = "insufficient"
            checks.append({
                "claim_id": claim.get("claim_id"),
                "claim": claim.get("claim"),
                "verdict": verdict,
                "evidence_ids": list(claim.get("evidence_ids") or []),
                "reason": "offline-lenient" if self.lenient else "offline-strict",
                "confidence": 0.9,
            })
        return SimpleNamespace(content=json.dumps({"checks": checks}))


def run_arm_offline(row: dict, *, panel: bool, budget_state: BudgetState):
    start = time.perf_counter()
    claims = _claims_payload(row)
    prompt = VERIFICATION_PROMPT.format(
        claims_json=json.dumps(claims, ensure_ascii=False),
        snapshot_json=json.dumps(row.get("snapshot") or {}, ensure_ascii=False),
    )
    if not panel:
        model = _OfflineModel(lenient=True)
        _, payload = _invoke_json(model, VERIFICATION_SYSTEM, prompt,
                                  budget_state=budget_state, role="verification")
        return payload.get("checks") or [], time.perf_counter() - start
    review = run_panel(
        [
            ("lenient", _OfflineModel(lenient=True)),
            ("strict", _OfflineModel(lenient=False)),
        ],
        input_snapshot={"claims": claims, "ledger_snapshot": row.get("snapshot") or {}},
        budget_state=budget_state,
    )
    return (review.result or {}).get("checks") or [], time.perf_counter() - start


def run_arm_real(row: dict, models: dict, panel_models: dict, *, panel: bool, budget_state: BudgetState):
    start = time.perf_counter()
    claims = _claims_payload(row)
    prompt = VERIFICATION_PROMPT.format(
        claims_json=json.dumps(claims, ensure_ascii=False),
        snapshot_json=json.dumps(row.get("snapshot") or {}, ensure_ascii=False),
    )
    if not panel:
        _, payload = _invoke_json(
            models["verifier"], VERIFICATION_SYSTEM, prompt,
            budget_state=budget_state, role="verification",
        )
        return (payload.get("checks") or []) if isinstance(payload, dict) else [], time.perf_counter() - start
    review = run_panel(
        [(str(index), member) for index, member in enumerate(panel_models.get("members") or [])],
        input_snapshot={"claims": claims, "ledger_snapshot": row.get("snapshot") or {}},
        referee=panel_models.get("referee"),
        budget_state=budget_state,
    )
    return (review.result or {}).get("checks") or [], time.perf_counter() - start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--depth", default="deep")
    parser.add_argument("--real", action="store_true", help="真实 API 模型（默认离线确定性）")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", default="reports/evaluation/p4/b_panel_ab_20260813.md")
    parser.add_argument(
        "--single-preset",
        default=None,
        help="single 臂使用的模型 preset（默认 profile.verifier_model；"
        "传 ds_strong 等做控制变量对比，隔离评审团机制与模型本身差异）",
    )
    args = parser.parse_args(argv)

    rows = load_gold(args.gold)
    models = panel_models = None
    if args.real:
        # A/B 隔离模型质量/成本：使用统一宽松超时的裸模型（绕过运行级 42s
        # deadline 封装），成员 max_tokens 减半与 B2 语义一致；生产时限下的
        # 墙钟行为单独记录在报告中。
        from conflux.model_factory import create_chat_model
        from conflux.research_modes import resolve_research_profile

        profile = resolve_research_profile(args.depth)
        ab_timeout = 240
        # 默认 single 臂与 panel 首成员同模型（控制变量）：2026-08-14 控制实验
        # 证明原默认（profile.verifier_model=deepseek-v4-flash-guan）与 panel 成员
        # （ds_strong=deepseek-v4-flash-0731 等）不同模型，导致 42.9% vs 66.7%
        # 的表观差异其实是模型差异而非评审团机制（同模型对照下两臂均为 66.7%）。
        member_presets = profile.panel_members("verification")
        single_preset = args.single_preset or (member_presets[0] if member_presets else profile.verifier_model)
        models = {
            "verifier": create_chat_model(
                single_preset,
                max_tokens=profile.verifier_max_tokens,
                timeout=ab_timeout,
            ),
        }
        member_tokens = max(300, profile.verifier_max_tokens // 2)
        members = [
            create_chat_model(preset, max_tokens=member_tokens, timeout=ab_timeout)
            for preset in profile.panel_members("verification")
        ]
        referee = None
        if len(members) >= 3:
            referee = create_chat_model(
                profile.panel_referee or profile.verifier_model,
                max_tokens=member_tokens, timeout=ab_timeout,
            )
        panel_models = {"members": members, "referee": referee}
        if not panel_models["members"]:
            print("error: depth 档未启用评审团（roster 为空）", file=sys.stderr)
            return 2

    result_rows: list[dict] = []
    single_costs, panel_costs, single_latencies, panel_latencies = [], [], [], []
    for repeat in range(max(1, args.repeats)):
        for row in rows:
            single_budget = BudgetState.for_depth(args.depth)
            panel_budget = BudgetState.for_depth(args.depth)
            if args.real:
                single_checks, single_wall = run_arm_real(row, models, panel_models, panel=False, budget_state=single_budget)
                panel_checks, panel_wall = run_arm_real(row, models, panel_models, panel=True, budget_state=panel_budget)
            else:
                single_checks, single_wall = run_arm_offline(row, panel=False, budget_state=single_budget)
                panel_checks, panel_wall = run_arm_offline(row, panel=True, budget_state=panel_budget)
            claims = _claims_payload(row)
            aligned_single = _align(single_checks, claims)
            aligned_panel = _align(panel_checks, claims)
            if repeat == 0:
                result_rows.extend(_metric_rows(row, aligned_single, aligned_panel))
            single_costs.append(_token_cost(single_budget))
            panel_costs.append(_token_cost(panel_budget))
            single_latencies.append(round(single_wall, 3))
            panel_latencies.append(round(panel_wall, 3))

    metrics = _aggregate(result_rows, single_costs, panel_costs, single_latencies, panel_latencies)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema": "conflux-p4-panel-ab-v1",
        "mode": "real" if args.real else "offline_pipeline_validation",
        "depth": args.depth,
        "single_preset": args.single_preset or "profile.verifier_model",
        "gold": str(Path(args.gold).resolve()),
        "repeats": args.repeats,
        "cases": len(rows),
        "metrics": metrics,
        "detail": result_rows,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out_path.with_suffix(".json")).write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(out_path, artifact)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def write_report(out_path: Path, artifact: dict) -> None:
    m = artifact["metrics"]
    mode_note = (
        "真实 API 模型对照"
        if artifact["mode"] == "real"
        else "**仅离线确定性管道验证（非真实模型质量证据）**"
    )
    rows = [
        f"# P4-B 评审团 A/B 评测报告",
        "",
        f"> 生成时间：{artifact['generated_at']}　模式：{mode_note}",
        f"> 档位：{artifact['depth']}　数据集：{artifact['gold']}　cases={artifact['cases']} repeats={artifact['repeats']}",
        f"> single 臂模型：{artifact.get('single_preset', 'profile.verifier_model')}（默认与 panel 首成员同模型，控制变量）",
        "",
        "## 1. 指标对照（同证据快照：单 verifier vs 评审团）",
        "",
        "| 指标 | 单 verifier | 评审团 | 增量 |",
        "|---|---|---|---|",
        f"| 误判率（本应非 supports 判 supports） | {m['misjudge_rate']['single']:.1%} (n={m['misjudge_n']['single']}) | {m['misjudge_rate']['panel']:.1%} (n={m['misjudge_n']['panel']}) | {m['misjudge_rate']['panel'] - m['misjudge_rate']['single']:+.1%} |",
        f"| 误判率 95% Wilson CI | [{m['misjudge_ci95']['single'][0]:.1%}, {m['misjudge_ci95']['single'][1]:.1%}] | [{m['misjudge_ci95']['panel'][0]:.1%}, {m['misjudge_ci95']['panel'][1]:.1%}] | — |",
        f"| 全量不一致率（不含 uncertain） | {m['mismatch_rate']['single']:.1%} | {m['mismatch_rate']['panel']:.1%} | {m['mismatch_rate']['panel'] - m['mismatch_rate']['single']:+.1%} |",
        f"| 待核验率（uncertain） | {m['uncertain_rate']['single']:.1%} | {m['uncertain_rate']['panel']:.1%} | {m['uncertain_rate']['panel'] - m['uncertain_rate']['single']:+.1%} |",
        f"| token 成本（输入+输出均值） | {m['token_cost']['single']} | {m['token_cost']['panel']} | ×{m['token_cost']['ratio']} |",
        f"| P95 延迟（s，成员并行） | {m['latency_p95_seconds']['single']} | {m['latency_p95_seconds']['panel']} | — |",
        "",
        "## 2. 默认化决策",
        "",
        f"- 误判率下降或持平：{'通过' if m['default_conditions']['misjudge_not_worse'] else '未通过'}",
        f"- 成本增量 ≤1.5×：{'通过' if m['default_conditions']['cost_within_1_5x'] else '未通过'}（实际 ×{m['token_cost']['ratio']}）",
        f"- **结论：`{m['default_decision']}`**",
        "",
        "## 3. 逐条明细",
        "",
        "| claim | gold | 单 verifier | 评审团 |",
        "|---|---|---|---|",
    ]
    for row in artifact["detail"]:
        rows.append(f"| {row['claim_id']} | {row['gold']} | {row['single']} | {row['panel']} |")
    rows += ["", "## 4. 局限", "",
             "- 种子集源自冻结 `evaluation/v2_gold/verification_gold.jsonl`（10 条 insufficient 标注）+ 扩展构造子集，"
             "为小样本；论文级质量结论需扩展到 KG 136 篇终审与 P2 75 篇的 claim 级标注后重跑。",
             "- 离线模式为确定性管道验证，不计入默认化证据。",
             "- 真实 API 模式默认 2+ 成员与裁判；成员 max_tokens 减半；延迟受 provider 波动影响，两臂对称。",
             "- 本脚本以统一宽松超时（240s）隔离模型质量/成本度量；当前 provider 延迟下，deep 档单批 43 claim 的"
             "verification 墙钟超过运行级 role_timeout（deep verifier 42s），生产运行需上调 role_timeout 或减小单批 claim 数。"
             "该问题对两臂对称，不影响评审团质量结论。",
             ""]
    out_path.write_text("\n".join(rows), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
