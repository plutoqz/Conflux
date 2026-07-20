"""P1 output-focused rubric and anonymous pairwise evaluation helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


RUBRIC_DIMENSIONS = (
    "correctness",
    "breadth",
    "depth",
    "case_specificity",
    "recommendation_value",
    "coherence",
)

PAIRWISE_SYSTEM = (
    "你是独立研究质量评审者。候选 A/B 已匿名且顺序随机。"
    "不得因篇幅、引用数量、术语密度或排版精美直接加分。"
    "可审计证据摘要中的来源身份、日期和引文是运行时已取得的确定性输入；"
    "不得凭模型记忆、编号观感或来源知名度推测这些来源不存在或系伪造。"
    "不要输出思考过程、分析草稿或 Markdown，只输出有效 JSON。"
)

PAIRWISE_RUBRIC = """逐项使用 1-5 分：
- correctness：1=存在核心事实错误或证据错配；3=大体正确但有过强推断；5=关键事实、边界和引用均准确。
- breadth：1=只覆盖一个局部；3=覆盖约半数重要维度；5=所有重要维度均有实质内容而非只有标题。
- depth：1=罗列结论；3=部分解释原因或影响；5=持续给出机制、因果链、权衡、边界和反例。
- case_specificity：1=没有具体案例/数据；3=有少量案例但关联弱；5=核心维度有直接、可核查的案例或证据。
- recommendation_value：1=无建议或口号化；3=建议相关但缺少条件；5=建议可执行并说明优先级、条件和权衡。
- coherence：1=碎片化或按来源拼接；3=结构可读但重复；5=围绕问题形成连贯综合。

硬约束：引用全部正确但只展开少数维度的窄短报告，breadth/depth 不得高于 2；
只有标题命中、免责声明或置信度说明不算实质覆盖。"""


@dataclass(frozen=True, slots=True)
class AnonymousPair:
    query: str
    required_dimensions: tuple[str, ...]
    answer_a: str
    answer_b: str
    candidate_label: str
    reference_label: str
    input_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_anonymous_pair(
    query: str,
    candidate: str,
    reference: str,
    required_dimensions: list[str] | tuple[str, ...],
    *,
    seed: str = "p1",
) -> AnonymousPair:
    """Return a reproducibly shuffled A/B pair without provenance labels."""

    clean_candidate = _anonymize_report(candidate)
    clean_reference = _anonymize_report(reference)
    digest = hashlib.sha256(
        (seed + "\0" + query + "\0" + clean_candidate + "\0" + clean_reference).encode("utf-8")
    ).hexdigest()
    candidate_first = int(digest[:2], 16) % 2 == 0
    return AnonymousPair(
        query=str(query).strip(),
        required_dimensions=tuple(str(item).strip() for item in required_dimensions if str(item).strip()),
        answer_a=clean_candidate if candidate_first else clean_reference,
        answer_b=clean_reference if candidate_first else clean_candidate,
        candidate_label="A" if candidate_first else "B",
        reference_label="B" if candidate_first else "A",
        input_sha256=digest,
    )


def build_pairwise_prompt(pair: AnonymousPair, evidence: str = "", *, evaluation_date: str | None = None) -> str:
    dimensions = "、".join(pair.required_dimensions) or "由问题本身确定的重要维度"
    return f"""{PAIRWISE_RUBRIC}

评测日期：{evaluation_date or date.today().isoformat()}。不得把该日期之前已发布的材料误判为未来来源。
问题：{pair.query}
必须实质覆盖：{dimensions}

候选 A：
{pair.answer_a}

候选 B：
{pair.answer_b}

可审计证据摘要（仅用于检查事实和引用，不代表任一候选身份）：
{evidence or '未提供；此时不要凭记忆虚构确定性反证。'}

证据审计规则：
- 摘要中列出的来源身份、发布日期和逐字引文均为本次运行已取得的事实，不是候选自行声称的元数据。
- 不得依据模型记忆、arXiv/DOI 编号观感、标题熟悉度或来源知名度断言已列来源可疑、虚构或不存在。
- 只有逐字引文本身不支持候选对应表述时，才可据此扣减 correctness；摘要未列出的来源只能标为待核验，不能推定为错误。
- 明确标注为“模型分析”“非外部事实”的内容应按逻辑、限定条件和推断强度评分，不能仅因缺少外部引用判为事实错误。

仅输出以下 JSON；每项 A/B 均为 1-5：
{{"scores":{{"correctness":{{"A":1,"B":1}},"breadth":{{"A":1,"B":1}},
"depth":{{"A":1,"B":1}},"case_specificity":{{"A":1,"B":1}},
"recommendation_value":{{"A":1,"B":1}},"coherence":{{"A":1,"B":1}}}},
"preference":"A|B|tie","reason":"具体差异","critical_issues":{{"A":[],"B":[]}}}}"""


def normalize_pairwise_judgement(payload: dict[str, Any], pair: AnonymousPair) -> dict[str, Any]:
    """Validate score bounds and translate anonymous labels back after judging."""

    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    candidate_scores: dict[str, int] = {}
    reference_scores: dict[str, int] = {}
    for dimension in RUBRIC_DIMENSIONS:
        row = raw_scores.get(dimension) if isinstance(raw_scores.get(dimension), dict) else {}
        candidate_scores[dimension] = _bounded_score(row.get(pair.candidate_label))
        reference_scores[dimension] = _bounded_score(row.get(pair.reference_label))

    preference = str(payload.get("preference") or "tie").upper()
    if preference not in {"A", "B", "TIE"}:
        preference = "TIE"
    translated = "tie"
    if preference in {"A", "B"}:
        translated = "candidate" if preference == pair.candidate_label else "reference"
    core = ("correctness", "breadth", "depth", "case_specificity", "recommendation_value")
    candidate_overall = round(sum(candidate_scores[item] for item in core) / len(core), 2)
    reference_overall = round(sum(reference_scores[item] for item in core) / len(core), 2)
    return {
        "candidate_scores": candidate_scores,
        "reference_scores": reference_scores,
        "candidate_overall": candidate_overall,
        "reference_overall": reference_overall,
        "candidate_preference": translated,
        "passed": translated in {"candidate", "tie"}
        and all(candidate_scores[item] >= 4 for item in core)
        and all(candidate_scores[item] >= reference_scores[item] for item in core),
        "reason": str(payload.get("reason") or "").strip(),
        "critical_issues": payload.get("critical_issues") or {},
        "anonymous_order": {"candidate": pair.candidate_label, "reference": pair.reference_label},
        "input_sha256": pair.input_sha256,
    }


def deterministic_output_rubric(report: str, required_dimensions: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Detect narrow/shallow counterexamples without pretending to judge truth."""

    body = _answer_body(report)
    dimensions = [str(item).strip() for item in required_dimensions if str(item).strip()]
    dimension_hits = {item: _dimension_is_substantive(body, item) for item in dimensions}
    coverage_ratio = sum(dimension_hits.values()) / len(dimensions) if dimensions else 1.0
    breadth = _ratio_score(coverage_ratio)

    units = [
        line.strip()
        for line in body.splitlines()
        if len(line.strip()) >= 35 and not line.lstrip().startswith("#")
    ]
    mechanism = _feature_ratio(units, ("因为", "由于", "导致", "机制", "原因", "约束", "权衡", "依赖", "从而"))
    impact = _feature_ratio(units, ("影响", "风险", "结果", "边界", "后果", "意味着"))
    cases = _feature_ratio(units, ("例如", "案例", "实测", "研究发现", "报告", "数据集", "系统"))
    recommendations = _feature_ratio(units, ("建议", "应当", "需要", "优先", "可以", "缓解", "改进"))
    depth = _ratio_score(min(1.0, (mechanism * 0.65) + (impact * 0.35)))
    case_score = _ratio_score(cases)
    recommendation_score = _ratio_score(recommendations)
    if dimensions and coverage_ratio < 0.5:
        depth = min(depth, 2)
        case_score = min(case_score, 2)
        recommendation_score = min(recommendation_score, 2)
    return {
        "breadth": breadth,
        "depth": depth,
        "case_specificity": case_score,
        "recommendation_value": recommendation_score,
        "coverage_ratio": round(coverage_ratio, 3),
        "dimension_hits": dimension_hits,
        "substantive_units": len(units),
        "passed": min(breadth, depth, case_score, recommendation_score) >= 4,
    }


def _answer_body(report: str) -> str:
    value = str(report or "")
    if "## 回答" in value:
        value = value.split("## 回答", 1)[1]
    value = re.split(r"^##\s+(?:参考文献与证据|置信度附录|研究依据|可靠性与缺口)\s*$", value, 1, re.MULTILINE)[0]
    return value.strip()


def _dimension_is_substantive(body: str, dimension: str) -> bool:
    terms = [term for term in re.split(r"[/、与和\s]+", dimension) if len(term) >= 2]
    if not terms:
        return False
    for match in re.finditer("|".join(re.escape(term) for term in terms), body, re.IGNORECASE):
        context = body[max(0, match.start() - 80) : match.end() + 180]
        context = re.sub(r"[#*|`\[\]\s]", "", context)
        if len(context) >= 70:
            return True
    return False


def _feature_ratio(units: list[str], markers: tuple[str, ...]) -> float:
    if not units:
        return 0.0
    hits = sum(any(marker.casefold() in unit.casefold() for marker in markers) for unit in units)
    return min(1.0, hits / max(2, min(6, len(units))))


def _ratio_score(ratio: float) -> int:
    if ratio >= 0.8:
        return 5
    if ratio >= 0.6:
        return 4
    if ratio >= 0.4:
        return 3
    if ratio > 0:
        return 2
    return 1


def _bounded_score(value: Any) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 1


def _anonymize_report(report: str) -> str:
    value = str(report or "").strip()
    value = re.sub(r"(?im)^\s*(?:run(?: id)?|model|provider|生成模型|报告来源)\s*[:：].*$", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def judgement_json(payload: dict[str, Any]) -> str:
    """Stable serialization used by recorded-response fixtures."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
