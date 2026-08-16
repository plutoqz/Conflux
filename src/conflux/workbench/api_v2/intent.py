"""C2 意图路由：确定性规则优先，LLM 分类兜底（非白名单即拒绝）。

规则表（命令词/关键词，有序匹配）→ 动作白名单；未命中 → LLM 结构化分类
（flash，JSON 输出），分类结果不在白名单内一律转澄清（无幻觉执行）；
LLM 不可用/解析失败 → 澄清问题。
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .schemas import IntentResult

ACTION_WHITELIST = (
    "research_query",
    "run_radar",
    "project_audit",
    "cycle_summary",
    "memory_query",
    "experiment",
    "mentor_report",
    "code_query",
    "paper_notes",
)

_CLARIFY_HINTS: dict[str, str] = {
    "research_query": "我可以启动一次多源调研：检索文档库与网络，生成带证据的报告。",
    "run_radar": "我可以为已登记项目运行论文雷达：扫描新论文并生成候选清单（入库需先确认）。",
    "project_audit": "我可以读取项目的审计与状态快照（只读）。",
    "cycle_summary": "我可以汇总本周期已确认的研究进展与风险。",
    "memory_query": "我可以查询你保存的偏好与术语记忆。",
    "experiment": "我可以登记实验（假设/参数/指标/提交），写入后进入周期审计与周报。",
    "mentor_report": "我可以生成导师周报草稿：只整理已登记的进展与实验数据。",
    "code_query": "我可以查询已登记项目的 Python 代码并返回文件与行号。",
    "paper_notes": "我可以读取结构化文献笔记并生成可回溯的 related work 草稿。",
}

# (action, 关键词组)：组内全命中才算；空组仅按词命中。有序，先到先得。
_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("run_radar", ("雷达", "论文扫描", "paper radar", "找论文", "新论文")),
    ("cycle_summary", ("周期", "总结", "进展汇总")),
    ("experiment", ("实验", "登记实验", "记录实验", "experiment")),
    ("mentor_report", ("周报", "导师", "mentor", "评审报告", "周报草稿")),
    ("paper_notes", ("文献笔记", "related work", "相关工作", "笔记库")),
    ("code_query", ("代码问答", "代码里", "函数在哪", "调用链", "code qa")),
    ("project_audit", ("审计", "项目状态", "体检", "audit")),
    ("memory_query", ("记忆", "偏好", "memory", "记住什么")),
    ("research_query", ("调研", "研究", "检索", "查证", "research", "调查")),
]

_INTENT_SYSTEM = (
    "You are Conflux's chat intent classifier. Classify the user message into "
    "exactly one action from the whitelist. Return valid JSON only."
)

_INTENT_PROMPT = """Classify the user message.

Actions:
- research_query: start a multi-source research investigation and produce an evidence-backed report
- run_radar: run the paper radar for a registered project (enqueues a durable job)
- project_audit: read a project's audit or status snapshot (read-only)
- cycle_summary: summarize the confirmed cycle progress and risks
- memory_query: query saved user preferences and terminology memories
- experiment: register an experiment (hypothesis/params/metrics/commit) into the experiment ledger
- mentor_report: draft a mentor weekly report from registered progress and experiments
- code_query: query a registered project's source code with file and line references
- paper_notes: read literature notes or create a traceable related-work draft
- clarify: anything else, or when the message is ambiguous

User message:
{message}

Return JSON:
{{"action": "...", "confidence": 0.0}}
"""


def _rule_hits(message: str) -> tuple[str, float]:
    lowered = str(message or "").casefold()
    for action, keywords in _RULES:
        if any(keyword.casefold() in lowered for keyword in keywords):
            return action, 1.0
    return "", 0.0


def _extract_params(action: str, message: str) -> dict[str, Any]:
    if action != "experiment":
        return {}
    text = str(message or "").strip()
    metrics: dict[str, float] = {}
    for name, value in re.findall(r"([A-Za-z][A-Za-z0-9_.-]*)\s*=\s*(-?\d+(?:\.\d+)?)", text):
        metrics[name] = float(value)
    commit_match = re.search(r"(?:commit|提交)\s*[:：#]?\s*([0-9a-f]{7,40})\b", text, re.IGNORECASE)
    hypothesis_match = re.search(r"(?:假设|hypothesis)\s*[:：]\s*([^，,；;]+)", text, re.IGNORECASE)
    name = re.sub(r"^(?:帮我)?(?:登记|记录|新增)?\s*(?:一个)?实验\s*", "", text).strip()
    name = re.split(r"[，,；;]", name, maxsplit=1)[0].strip() or text[:40]
    return {
        "name": name[:120],
        "hypothesis": hypothesis_match.group(1).strip() if hypothesis_match else "",
        "commit": commit_match.group(1) if commit_match else "",
        "metrics": metrics,
    }


def classify_intent(
    message: str,
    *,
    llm: Any | None = None,
    llm_invoke: Callable[[list[Any]], Any] | None = None,
) -> IntentResult:
    """确定性规则优先；LLM 兜底仅接受白名单动作，否则澄清。"""

    action, confidence = _rule_hits(message)
    if action:
        return IntentResult(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            source="rules",
            clarify_question="",
            params=_extract_params(action, message),
        )
    if llm is not None or llm_invoke is not None:
        try:
            invoker = llm_invoke or llm.invoke
            response = invoker([
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": _INTENT_PROMPT.format(message=str(message))},
            ])
            content = str(getattr(response, "content", response) or "")
            json_start, json_end = content.find("{"), content.rfind("}")
            payload = json.loads(content[json_start:json_end + 1]) if json_start >= 0 and json_end > json_start else {}
            llm_action = str(payload.get("action") or "")
            if llm_action in ACTION_WHITELIST:
                return IntentResult(
                    action=llm_action,  # type: ignore[arg-type]
                    confidence=max(0.0, min(1.0, float(payload.get("confidence") or 0.5))),
                    source="llm",
                )
        except Exception:
            pass
    return IntentResult(
        action="clarify",
        confidence=0.0,
        source="fallback",
        clarify_question=(
            "我不确定你想做什么。可以试试：" + "；".join(_CLARIFY_HINTS.values())
        ),
    )
