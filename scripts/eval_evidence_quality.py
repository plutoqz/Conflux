"""证据质量评测：citation correctness / claim support precision / unsupported rate。

构造金标准 claim 集（引用 Conflux 仓库内真实文件），由 LLM judge 基于
真实引用内容评估：引用是否存在、是否支持声明、语义是否一致。

金标准每条含 ground-truth 类别：
- support        : 引用存在且支持声明
- exists_nosupport: 引用存在但不支持声明（引用了错的内容）
- fabricated     : 引用的文件/行不存在
- inconsistent   : 引用语义与声明不一致

指标：
- citation_correctness : judge 对“引用是否存在”的判断与 ground truth 一致率
- claim_support_precision : 被判为支持的 claim 中，ground truth 确为 support 的比例
- unsupported_claim_rate  : 被判为不支持的 claim 比例
- consistency_rate        : 被判为语义一致的比例

说明：基于构造金标准 + LLM judge 的方法论验证，规模 16，非生产全量；
temperature=0 保证确定性。
用法:
    python scripts/eval_evidence_quality.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from conflux.model_factory import create_chat_model  # noqa: E402

REPO = PROJECT_ROOT


def _read_source(ref: str) -> tuple[bool, str]:
    """ref: 'relpath' 或 'relpath#Lstart-Lend'。返回 (exists, content)。"""
    line_spec = ""
    if "#L" in ref:
        ref, line_spec = ref.split("#L", 1)
    p = REPO / ref
    if not p.exists():
        return False, ""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False, ""
    if line_spec:
        try:
            if "-" in line_spec:
                a, b = line_spec.split("-")
                lo, hi = int(a), int(b)
            else:
                lo = hi = int(line_spec)
            lines = text.splitlines()[lo - 1: hi]
            return True, "\n".join(lines)
        except Exception:
            return True, text[:2000]
    return True, text[:3000]


# (id, claim, cited_ref, ground_truth)
GOLDEN = [
    ("g1", "Conflux 的任务运行时基于 SQLite JobQueue 与租约(lease)机制实现可恢复执行。",
     "src/conflux/workbench/jobs.py", "support"),
    ("g2", "JobQueue 使用唯一幂等键(idempotency_key)防止同一任务被重复入队。",
     "src/conflux/adapters/sqlite_store.py", "support"),
    ("g3", "代码问答索引基于 AST 解析与调用图(call graph)构建。",
     "src/conflux/code_qa.py", "support"),
    ("g4", "工具调用参数通过 JSON Schema 进行校验(validate_capability_input)。",
     "src/conflux/core/policy.py", "support"),
    ("g5", "意图路由采用确定性规则优先、LLM 白名单兜底的策略。",
     "src/conflux/workbench/api_v2/intent.py", "support"),
    ("g6", "EventStore 持久化 trace 事件，支持按 after_id 重放以实现 SSE 断线续传。",
     "src/conflux/adapters/sqlite_store.py", "support"),
    # exists but wrong support
    ("g7", "RAG 检索仅使用 BM25 一种排序算法。",
     "src/conflux/rag.py", "exists_nosupport"),
    ("g8", "Conflux 的研究管道默认关闭所有事实核查(FactCheck)。",
     "src/conflux/workbench/jobs.py", "exists_nosupport"),
    # fabricated
    ("g9", "Conflux 内置了自动 Kubernetes 部署编排模块。",
     "src/conflux/k8s_deploy.py", "fabricated"),
    ("g10", "系统提供内置的实时股价推送服务。",
     "src/conflux/stock_realtime.py", "fabricated"),
    # inconsistent
    ("g11", "CheckpointStore 仅用于缓存，不参与任务恢复。",
     "src/conflux/adapters/sqlite_store.py", "inconsistent"),
    ("g12", "意图分类器会对任意用户输入无差别地执行对应动作。",
     "src/conflux/workbench/api_v2/intent.py", "inconsistent"),
    # 额外 support 几条，强化正例
    ("g13", "JobManager 在任务完成时会写入 terminal checkpoint 以便幂等恢复。",
     "src/conflux/workbench/jobs.py", "support"),
    ("g14", "Evidence Ledger 将声明(claim)绑定到证据(evidence)与源快照(source snapshot)。",
     "src/conflux/adapters/evidence_ledger_store.py", "support"),
    ("g15", "意图路由的澄清(clarify)分支用于无明确意图或超出范围的输入。",
     "src/conflux/workbench/api_v2/intent.py", "support"),
    ("g16", "任务恢复测试中，已完成任务不会被重新认领执行。",
     "src/conflux/adapters/sqlite_store.py", "support"),
]


JUDGE_PROMPT = """你是一个严格的证据审查员。给定一条声明(claim)和它引用的源代码片段(source)。
判断：
1. citation_exists: 该引用是否真实存在（source 非空且看起来是真实代码/文档）。
2. supports: source 内容是否支持该声明（声明可由 source 合理推出）。
3. consistent: source 语义是否与声明一致（无矛盾）。

只返回 JSON：{"citation_exists": true/false, "supports": true/false, "consistent": true/false}

claim: {claim}

source:
{source}
"""


def main() -> int:
    out_dir = PROJECT_ROOT / "reports/eval/evidence_quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    judge = create_chat_model("cheap", temperature=0)

    rows = []
    for cid, claim, ref, gt in GOLDEN:
        exists_fs, content = _read_source(ref)
        src_text = content if exists_fs else "(SOURCE NOT FOUND)"
        prompt = JUDGE_PROMPT.format(claim=claim, source=src_text)
        try:
            resp = judge.invoke([{"role": "user", "content": prompt}])
            content_out = str(getattr(resp, "content", resp) or "")
            s, e = content_out.find("{"), content_out.rfind("}")
            payload = json.loads(content_out[s:e + 1]) if s >= 0 and e > s else {}
        except Exception as exc:
            payload = {"error": str(exc)}
        j_exists = bool(payload.get("citation_exists"))
        j_supports = bool(payload.get("supports"))
        j_consistent = bool(payload.get("consistent"))
        # citation_correctness: judge 的存在判断 vs ground truth 的存在判断
        gt_exists = gt != "fabricated"
        correctness_ok = (j_exists == gt_exists)
        rows.append({
            "id": cid, "claim": claim[:40], "ref": ref, "ground_truth": gt,
            "fs_exists": exists_fs, "judge_exists": j_exists,
            "judge_supports": j_supports, "judge_consistent": j_consistent,
            "citation_correct": correctness_ok,
        })
        time.sleep(0.3)

    total = len(rows)
    cite_corr = sum(1 for r in rows if r["citation_correct"]) / total if total else None
    supports = [r for r in rows if r["judge_supports"]]
    # claim_support_precision: 被判支持的中，ground truth 确为 support 的比例
    if supports:
        csp = sum(1 for r in supports if r["ground_truth"] == "support") / len(supports)
    else:
        csp = None
    unsupported = sum(1 for r in rows if not r["judge_supports"]) / total if total else None
    consistent = sum(1 for r in rows if r["judge_consistent"]) / total if total else None

    result = {
        "schema_version": "conflux-evidence-quality-v1",
        "note": "构造金标准 + LLM judge 的方法论验证；规模 16；temperature=0",
        "total": total,
        "citation_correctness": round(cite_corr, 4) if cite_corr is not None else None,
        "claim_support_precision": round(csp, 4) if csp is not None else None,
        "unsupported_claim_rate": round(unsupported, 4) if unsupported is not None else None,
        "consistency_rate": round(consistent, 4) if consistent is not None else None,
        "rows": rows,
    }
    out = out_dir / "evidence_quality.json"
    out.write_text(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "evidence_quality_detail.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
