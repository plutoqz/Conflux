"""意图路由准确率评测（确定性，纯规则路径）。

基于 conflux.workbench.api_v2.intent.classify_intent：
- 规则优先（关键词有序匹配）→ 白名单动作
- 未命中且无 LLM → 转 clarify（安全设计，无幻觉执行）

构造金标准消息集，覆盖 9 个白名单动作 + 澄清（无意图/超出范围）。
测量（llm=None 纯规则路径）：
- routing_accuracy   : 规则命中的动作分类正确率
- clarify_recall     : 无意图/超范围消息被正确转澄清的比例
- overall_accuracy   : 全样本动作分类正确率

说明：LLM 兜底路径仅接受白名单动作，否则 clarify，属安全设计，本评测不依赖 LLM。
用法:
    python scripts/eval_intent_routing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.workbench.api_v2.intent import classify_intent  # noqa: E402


GOLDEN = [
    # action, message
    ("run_radar", "帮我对项目 A 跑一下论文雷达，找最近的新论文"),
    ("run_radar", "启动 paper radar 扫描我们登记的课题"),
    ("run_radar", "我想找论文，看看这个方向最近有什么进展"),
    ("cycle_summary", "帮我做个周期总结，汇总本周期进展"),
    ("cycle_summary", "生成本周期的进展汇总"),
    ("experiment", "登记一个实验：假设模型 size 越大越好，lr=0.01"),
    ("experiment", "记录实验 commit 提交 #a1b2c3d 的对比结果"),
    ("experiment", "新增实验：batch=32 对延迟的影响"),
    ("mentor_report", "生成一份导师周报草稿"),
    ("mentor_report", "帮我写 mentor 评审报告"),
    ("mentor_report", "出个周报，整理这周的进展"),
    ("paper_notes", "读一下文献笔记，生成 related work 草稿"),
    ("paper_notes", "相关工作那块帮我整理一下笔记库"),
    ("code_query", "代码里处理检索的函数在哪"),
    ("code_query", "这个模块的调用链是什么，帮我看代码问答"),
    ("code_query", "code qa：X 类的定义在哪个文件哪一行"),
    ("project_audit", "对项目做一次审计，看下项目状态"),
    ("project_audit", "给这个工程做个体检 audit"),
    ("memory_query", "查询我保存的偏好记忆"),
    ("memory_query", "你还记得我之前记住什么吗，memory 一下"),
    ("research_query", "调研一下 RAG 的局限，检索相关论文"),
    ("research_query", "帮我研究下这个算法的原理并查证"),
    ("research_query", "retrieval-augmented generation 的相关调查"),
    ("research_query", "检索一下 Conflux 的架构设计"),
    # 澄清（无意图关键词 / 超出范围）
    ("clarify", "今天天气怎么样"),
    ("clarify", "你好"),
    ("clarify", "讲个笑话"),
    ("clarify", "你觉得人工智能未来会取代程序员吗"),
    ("clarify", "帮我订一张去北京的机票"),
    ("clarify", "我现在心情不太好"),
    ("clarify", "推荐几部科幻电影"),
    ("clarify", "翻译这段话到英文"),
]

# research_query 关键词极宽，澄清样本必须避免命中任何关键词
# 复核：以上 clarify 样本均不含 调研/研究/检索/查证/research/调查/雷达/论文扫描/周期/总结/实验/周报/导师/文献/代码/审计/体检/记忆/偏好 等


def main() -> int:
    rows = []
    correct = 0
    clarify_total = clarify_correct = 0
    rule_hit_total = 0
    for expected, msg in GOLDEN:
        res = classify_intent(msg, llm=None)
        pred = res.action
        src = res.source
        if src == "rules":
            rule_hit_total += 1
        ok = (pred == expected)
        if ok:
            correct += 1
        if expected == "clarify":
            clarify_total += 1
            if pred == "clarify":
                clarify_correct += 1
        rows.append({"expected": expected, "predicted": pred, "source": src,
                     "message": msg[:40], "ok": ok})

    total = len(GOLDEN)
    result = {
        "schema_version": "conflux-intent-routing-v1",
        "total": total,
        "rule_hit": rule_hit_total,
        "rule_coverage": round(rule_hit_total / total, 4),
        "routing_accuracy": round(correct / total, 4),
        "clarify_total": clarify_total,
        "clarify_recall": round(clarify_correct / clarify_total, 4) if clarify_total else None,
        "overall_accuracy": round(correct / total, 4),
        "note": "纯规则路径（llm=None）；LLM 兜底仅接受白名单动作，否则 clarify（安全设计，未计入本评测）",
        "rows": rows,
    }
    out = PROJECT_ROOT / "reports" / "eval" / "intent_routing" / "intent_routing.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    keep = {k: v for k, v in result.items() if k != "rows"}
    out.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out.parent / "intent_routing_detail.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(keep, ensure_ascii=False, indent=2))
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
