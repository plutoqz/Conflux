#!/usr/bin/env python
"""P4-B v1.1 对抗评测集生成器（verification 判断点）。

目的（docs/plans/p4/B_多模型评审团.md §3.3）：让单 verifier 必然出错、
评审团有机会显示"纠偏"，否则 0/0 的 A/B 无区分度。

四类对抗样本：
  1. overclaim 近 miss：证据支持"某限制"，声明过度到"保证/绝对" → gold=insufficient
     （单模型易误判 supports：证据里确有相关内容）；
  2. off-domain 擦边：相关系统而非目标系统，措辞接近 → gold=insufficient
     （单模型易被名词撞车骗过）；
  3. 多源弱支持：多个相关但不直接证据，声明却断言必然 → gold=insufficient/uncertain；
  4. 反直觉真值：证据直接矛盾但声明措辞权威 → gold=contradicts
     （单模型易被权威措辞带偏）。

每条带 provenance=adversarial-2026-08-14；gold 由构造规则决定（fixture 语义，
人工可复核）。输出与 `verification_claims_gold_v2.jsonl` 同 schema，
可直接喂 `scripts/p4_panel_ab.py --gold ... --real --repeats 2`。

用法：
  python scripts/p4_build_gold_adversarial.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "evaluation/p4_panel_ab/verification_claims_gold_adv.jsonl"

VERDICTS = ("supports", "contradicts", "insufficient", "uncertain")


def _mk_case(case_id: str, pairs: list[tuple[str, list[str], str]], note: str) -> dict:
    """pairs: (claim_text, evidence_texts, gold_verdict)"""
    claims, records = [], []
    for i, (text, ev_texts, verdict) in enumerate(pairs, 1):
        assert verdict in VERDICTS, (case_id, i, verdict)
        eids = [f"{case_id}:e{j}" for j in range(1, len(ev_texts) + 1)]
        claims.append({
            "claim_id": f"{case_id}:c{i}",
            "claim": text,
            "evidence_ids": eids,
            "gold_verdict": verdict,
            "provenance": "adversarial-2026-08-14",
        })
        for k, et in enumerate(ev_texts, 1):
            records.append({
                "evidence_id": f"{case_id}:e{k}",
                "claim": et,
                "source_identity": f"fixture:{case_id}",
                "evidence_class": "fixture",
            })
    return {
        "case_id": case_id,
        "claims": claims,
        "snapshot": {"records": records},
        "_note": note,
    }


def main() -> int:
    cases = []
    # ── 1) overclaim 近 miss：证据相关但声明过度（修正 v2：证据文本只谈
    #        主题相关机制，不再包含直接矛盾的限定词，否则模型判 contradicts
    #        是合理的、gold=insufficient 反而错）──
    cases.append(_mk_case(
        "adv-overclaim",
        [
            ("The delivery gate guarantees perfect citation coverage on the first attempt.",
             ["The delivery gate requires citation coverage above a threshold before a report is delivered."], "insufficient"),
            ("The retriever guarantees zero off-topic chunks in the final evidence set.",
             ["The retriever filters candidates using relevance thresholds and per-paper limits."], "insufficient"),
            ("The pipeline guarantees the report never requires a correction round.",
             ["The pipeline supports a bounded correction round when arbitration proposes one."], "insufficient"),
            ("R1 ablation proves reranking always improves hit rate.",
             ["R1 ablation measured hit rate across several retrieval configurations."], "insufficient"),
            ("The web chain guarantees availability of every configured provider.",
             ["The web chain falls back across providers when one fails."], "insufficient"),
            ("Every research run is guaranteed to complete within its stage budget.",
             ["Stage budgets allocate wall-clock targets to each research stage."], "insufficient"),
        ],
        "overclaim：证据只谈主题相关机制、不含矛盾细节，声明绝对化 → gold=insufficient",
    ))

    # ── 2) off-domain 擦边：相关系统而非目标系统 ──
    cases.append(_mk_case(
        "adv-offdomain",
        [
            ("The evidence directly establishes that ChromaDB fails on strong-recall datasets.",
             ["A related vector store benchmark reports saturation on a strong-recall set; ChromaDB itself was not run."], "insufficient"),
            ("The report proves LangGraph checkpoints are the only resume mechanism.",
             ["A generic checkpoint discussion; the project uses its own SQLite checkpoint store."], "insufficient"),
            ("The ablation proves BM25 alone matches the hybrid retriever.",
             ["A keyword-only baseline was measured as a control and scored near zero recall on Chinese text."], "contradicts"),
            ("The benchmark proves the status endpoint never needs caching.",
             ["The status endpoint added a 30-second TTL cache after the first request remained slow."], "contradicts"),
            ("The evidence establishes Redis is used for job leases.",
             ["Job leases are stored in SQLite; a related deployment discussion mentions Redis for another product."], "insufficient"),
            ("The paper demonstrates the radar uses a live vector DB.",
             ["The radar relies on arXiv metadata and a curated local pool; a related system uses a live vector DB."], "insufficient"),
        ],
        "off-domain：措辞接近但证据指向相关系统 → gold=insufficient/contradicts",
    ))

    # ── 3) 多源弱支持：多个相关证据，声明断言必然 ──
    cases.append(_mk_case(
        "adv-weakmulti",
        [
            ("Multiple related reports prove the panel never errs on any claim type.",
             ["One fixture report covers insufficient claims only; another covers supports; neither samples contradicts at scale."], "insufficient"),
            ("The aggregate of several local benchmarks proves production latency is below 100 ms everywhere.",
             ["Local proxy benchmarks on one machine show 20-75 ms P95; no production machine was measured."], "insufficient"),
            ("Several successful smoke runs prove the whole pipeline is always available.",
             ["Smoke runs pass on fixture data; live provider availability was not part of the runs."], "uncertain"),
            ("Two similar datasets prove the embedding choice is irrelevant.",
             ["Two similar datasets were compared; the cross-language set still showed measurable gaps."], "insufficient"),
        ],
        "多源弱支持：多个相关但不直接 → gold=insufficient/uncertain",
    ))

    # ── 4) 反直觉真值：证据直接矛盾但声明措辞权威 ──
    cases.append(_mk_case(
        "adv-contradict",
        [
            ("The workbench is a fully serverless multi-tenant deployment.",
             ["The workbench runs locally and is a single-user local-first tool."], "contradicts"),
            ("Verification may upgrade a deterministic insufficient verdict to supports.",
             ["The verifier is forbidden from upgrading a deterministic insufficient result."], "contradicts"),
            ("DuckDuckGo requires a paid API key.",
             ["DuckDuckGo is free and keyless; only fallback providers require keys."], "contradicts"),
            ("Memory injection stores full chat transcripts.",
             ["Memory stores structured preference entries and never stores chat transcripts."], "contradicts"),
            ("The composer may invent citations when evidence is missing.",
             ["The composer may only cite evidence records present in the snapshot."], "contradicts"),
        ],
        "反直觉：证据直接矛盾但声明权威 → gold=contradicts",
    ))

    out_lines = [json.dumps(case, ensure_ascii=False) for case in cases]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    from collections import Counter
    counts = Counter()
    for case in cases:
        for c in case["claims"]:
            counts[c["gold_verdict"]] += 1
    print(f"written {OUT}  cases={len(cases)}  claims={sum(counts.values())}  verdicts={dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
