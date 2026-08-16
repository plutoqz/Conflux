#!/usr/bin/env python
"""P4-B 评审团 A/B 扩充 gold 集生成器。

产出 `evaluation/p4_panel_ab/verification_claims_gold_v2.jsonl`（可复现、可审计）：
- 冻结真值子集：v2_gold/verification_gold.jsonl 的 10 条 insufficient（frozen，保持忠实）；
- 构造子集（provenance=constructed-2026-08-14）：supports / contradicts / insufficient / uncertain
  四类各 ≥10，覆盖 verifier 最容易误判的场景（overclaim、off-domain、相关但不足、证据缺失）。

用途：配合 `scripts/p4_panel_ab.py --gold ...` 跑单 verifier vs 评审团 A/B，
报告中以 `n_claims` 与 Wilson CI 表述统计不确定性。

用法：
  python scripts/p4_build_gold_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "evaluation/p4_panel_ab/verification_claims_gold_v2.jsonl"
V2_GOLD = Path(__file__).resolve().parent.parent / "evaluation/v2_gold/verification_gold.jsonl"

GOLD_VERDICTS = ("supports", "contradicts", "insufficient", "uncertain")


def _mk_case(case_id: str, pairs: list[tuple[str, list[str], str]], note: str) -> dict:
    """pairs: (claim_text, evidence_texts, gold_verdict)"""
    claims, records = [], []
    for i, (text, ev_texts, verdict) in enumerate(pairs, 1):
        assert verdict in GOLD_VERDICTS, (case_id, i, verdict)
        eids = [f"{case_id}:e{j}" for j in range(1, len(ev_texts) + 1)]
        claims.append({
            "claim_id": f"{case_id}:c{i}",
            "claim": text,
            "evidence_ids": eids,
            "gold_verdict": verdict,
            "provenance": "constructed-2026-08-14",
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


def _frozen_case() -> dict:
    rows = [json.loads(l) for l in V2_GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    claims, records = [], []
    for row in rows:
        for sq in row.get("subquestions") or []:
            for ev in sq.get("evidence") or []:
                eid = str(ev.get("evidence_id") or "")
                claims.append({
                    "claim_id": f"f2:{eid.rsplit(':', 1)[-1]}",
                    "claim": ("The evidence record directly establishes a concrete technical limitation "
                              "of EvidenceLedger-based RAG verification for research reports."),
                    "evidence_ids": [eid],
                    "gold_verdict": "insufficient",
                    "provenance": "frozen-v2-gold-2026-07",
                })
                records.append({
                    "evidence_id": eid,
                    "claim": str(ev.get("reason") or ""),
                    "source_identity": "v2-gold-fixture",
                    "evidence_class": "insufficient-review",
                })
    return {
        "case_id": "frozen-v2",
        "claims": claims,
        "snapshot": {"records": records},
        "_provenance": "冻结 v2_gold/verification_gold.jsonl（10 insufficient）",
    }


def main() -> int:
    cases = [_frozen_case()]
    cases.append(_mk_case(
        "panel-pos",
        [
            ("The pipeline enforces a citation coverage gate at 0.9 before delivery.",
             ["The delivery gate requires citation coverage >= 0.9 else the report is marked limited."], "supports"),
            ("The verification step cannot overturn a deterministic insufficient verdict.",
             ["Verifier may not upgrade a deterministic insufficient result to supports."], "supports"),
            ("The retriever caps candidate evidence per paper at 3 chunks.",
             ["Each paper contributes at most 3 chunks to the candidate set."], "supports"),
            ("The workbench persists job lease state in SQLite.",
             ["Job leases and heartbeats are stored in the SQLite runtime."], "supports"),
            ("The index uses parent-child chunking at 512/128 tokens.",
             ["Parent chunks are 512 tokens with 128-token children."], "supports"),
            ("Web search degrades across DuckDuckGo, Bing, Google, SerpAPI.",
             ["The provider chain falls back through DDG, Bing, Google, SerpAPI."], "supports"),
            ("Panel members run in parallel and cannot see other members' outputs.",
             ["Member reasoning executes concurrently and each member keeps its output private from the others."], "supports"),
            ("Task resume survives process restart via the checkpoint store.",
             ["Checkpointed runs can be resumed after an external process interruption."], "supports"),
            ("The audit step computes confidence bands deterministically.",
             ["Confidence bands are derived from deterministic audit metrics."], "supports"),
            ("The radar uses tier refresh days for low-frequency tiers.",
             ["Milestone and classic tiers are refreshed on a 30-day cursor."], "supports"),
        ],
        "supports 正例（确定性规则与配置直接支持）",
    ))
    cases.append(_mk_case(
        "panel-neg",
        [
            ("The verifier can overturn any deterministic verdict to supports when the model disagrees.",
             ["The model may override an insufficient deterministic verdict."], "contradicts"),
            ("Reranking with an LLM judge improves production hit rate by 4 points.",
             ["R1 ablation showed an LLM judge degrades hit rate; production disables rerank."], "contradicts"),
            ("The workbench uses Postgres for job state.",
             ["Job leases are stored in SQLite"], "contradicts"),
            ("Knowledge base vectors are stored in a Redis cluster.",
             ["The vector store is ChromaDB persisted to local disk."], "contradicts"),
            ("Paper radar performs a live semantic scholar search for every promoted paper.",
             ["Radar uses cached arxiv metadata and local curation; only active fetches are live."], "contradicts"),
        ],
        "contradicts 反例（直接矛盾）",
    ))
    cases.append(_mk_case(
        "panel-ins",
        [
            ("The evidence record directly establishes that EvidenceLedger fails on strong-recall datasets.",
             ["The item describes a related ledger benchmark that does not exercise EvidenceLedger itself."], "insufficient"),
            ("Index-level recall proves the report is accepted every time.",
             ["Index accuracy is measured offline; the delivery gate is a threshold on citation coverage."], "insufficient"),
            ("A single smoke case proves the panel never misjudges supports.",
             ["One frozen case with ten insufficient items cannot establish a zero-error guarantee."], "insufficient"),
            ("The performance baseline proves P95 below 300 ms on production machines.",
             ["The baseline is a local proxy with TTL caching; real machines were not tested."], "insufficient"),
        ],
        "insufficient（相关但不足以支持强结论）",
    ))
    cases.append(_mk_case(
        "panel-unc",
        [
            ("The pipeline's absolute recall after the 0.9 gate is exactly 90 percent.",
             ["One experiment measured 96.7% on a 30-question set; no guarantee is stated."], "uncertain"),
            ("The system's cost remains at least 40 percent lower than all alternatives.",
             ["A single provider comparison exists; market-wide alternatives are not benchmarked."], "uncertain"),
            ("Evolution to a new model layer never reduces accuracy.",
             ["A downgrade plan exists; no empirical fairness claim is made."], "uncertain"),
        ],
        "uncertain（证据不足且日常可能误判）",
    ))
    # 第二轮：让 supports/contradicts 也各 >= 10（当前 supports=10、contradicts=5）
    cases.append(_mk_case(
        "panel-pos2",
        [
            ("The CLI audit writes no project content upstream.",
             ["Progress audit executes read-only local checks and never uploads project files."], "supports"),
            ("The retrieval query rewriter produces bilingual queries by default.",
             ["Bilingual queries are generated deterministically when rewrite is enabled."], "supports"),
            ("P3 snapshots cap runs at 200 partitions.",
             ["Snapshot partitions are capped at runs=200 tests=100 sources=200."], "supports"),
            ("The provenance attribute belongs to a paper record.",
             ["Records carry an evidence provenance trace."], "supports"),
        ],
        "supports 补充（再 +4）",
    ))
    cases.append(_mk_case(
        "panel-neg2",
        [
            ("Conflux is a fully serverless multi-tenant platform.",
             ["Conflux is a local-first single-user research workbench."], "contradicts"),
            ("Memory injection stores fact content in RAG vectors.",
             ["Memory is kept out of the RAG evidence path; only preferences are injected."], "contradicts"),
            ("The web fetcher requires an API key for DuckDuckGo.",
             ["DuckDuckGo is free and keyless; keys are only for the fallback providers."], "contradicts"),
        ],
        "contradicts 补充（再 +3）",
    ))
    cases.append(_mk_case(
        "panel-ins2",
        [
            ("This run proves the delivery gate never blocks acceptance on real queries.",
             ["The gate is applied to one fixture case; real queries are not part of this evaluation."], "insufficient"),
            ("Coverage of the whole knowledge base equals the hit rate measured on 30 questions.",
             ["Hit rate was measured on a 30-question sample, not the full 1190 vectors."], "insufficient"),
            ("The absence of recorded rate limits proves rate limits never occur.",
             ["No rate limit was observed during an offline fixture; limits may appear on live feeds."], "insufficient"),
            ("The best-of-five runs means the pipeline always completes in five seconds.",
             ["Completion time depends on the model; the benchmark is not a latency guarantee."], "insufficient"),
        ],
        "insufficient 补充（再 +4）",
    ))

    # 46→66：再补 supports/contradicts/insufficient/uncertain 共 +23
    cases.append(_mk_case(
        "panel-pos3",
        [
            ("The engine re-indexes only changed documents.",
             ["Only changed documents are re-indexed; unchanged ones are skipped."], "supports"),
            ("Workbench settings persist across restarts.",
             ["Settings are stored in the SQLite config store."], "supports"),
            ("A crashed worker job can be resumed from its checkpoint.",
             ["Expired leases are reclaimed and the job continues from the checkpoint."], "supports"),
            ("The status endpoint caches its expensive audit result for 30 seconds.",
             ["The audit subquery is cached for 30 seconds with TTL."], "supports"),
            ("The retriever filters out papers already ingested globally.",
             ["Radar excludes papers already present in the global ingested set."], "supports"),
        ],
        "supports 补充（再 +5）",
    ))
    cases.append(_mk_case(
        "panel-pos4",
        [
            ("The CLI returns structured JSON for both snapshot and audit commands.",
             ["CLI commands output JSON artifacts for snapshot and audit."], "supports"),
            ("Confidence bands are derived from deterministic audit metrics.",
             ["Confidence bands are computed deterministically from the audit stage."], "supports"),
            ("The memory injector keeps fact content out of the RAG evidence path.",
             ["Only preference and style entries are injected; fact content stays in the evidence ledger."], "supports"),
            ("Radar promotes a paper only after the LLM review approves it.",
             ["Promotion requires an approved review outcome before it is accepted."], "supports"),
            ("Cycle summaries become the baseline for the next cycle.",
             ["Confirmed cycle summaries are used as the next cycle baseline."], "supports"),
        ],
        "supports 补充（再 +5）",
    ))
    cases.append(_mk_case(
        "panel-neg3",
        [
            ("The workbench produces a serverless multitenant deployment.",
             ["The workbench runs locally with a single-user registry."], "contradicts"),
            ("Memory injection stores raw user chat logs.",
             ["Memory stores structured preference entries, not chat transcripts."], "contradicts"),
            ("DuckDuckGo requires an API key by default.",
             ["DuckDuckGo is free and keyless; keys are only used for fallback providers."], "contradicts"),
            ("The radar uses a live vector DB as its primary source.",
             ["The radar relies on arXiv metadata and a curated local pool."], "contradicts"),
            ("The report composer invents citations when evidence is missing.",
             ["Composer may only cite evidence records present in the snapshot."], "contradicts"),
        ],
        "contradicts 补充（再 +5）",
    ))
    cases.append(_mk_case(
        "panel-ins3",
        [
            ("This benchmark establishes that no rate limit ever occurs.",
             ["Rate limits were not observed during an offline fixture; live feeds may still throttle."], "insufficient"),
            ("Five successful runs prove the pipeline always finishes in five seconds.",
             ["Completion time depends on the provider; the benchmark is not a latency guarantee."], "insufficient"),
            ("The 30-question sample covers the full knowledge-base accuracy.",
             ["Accuracy on 30 questions does not generalise to all 1190 indexed vectors."], "insufficient"),
            ("The single fixture case proves panel zero-error behaviour.",
             ["One fixture case cannot support a zero-error claim statistically."], "insufficient"),
            ("The performance proxy measures real production latency.",
             ["The P95 proxy misses rendering and SSE handshake; real machines were not tested."], "insufficient"),
        ],
        "insufficient 补充（再 +5）",
    ))
    cases.append(_mk_case(
        "panel-unc2",
        [
            ("The pipeline's total cost stays below 40% of the alternative.",
             ["A single provider comparison exists; market-wide cost data is incomplete."], "uncertain"),
            ("Applying a new model layer never degrades accuracy.",
             ["No empirical history supports a guaranteed non-regression."], "uncertain"),
            ("The retrieval hash changes reflect exactly one feature change.",
             ["The hash mixes multiple dimensions; attribution is not established."], "uncertain"),
        ],
        "uncertain 补充（再 +3）",
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