"""Compile internal evidence references into a stable public report format."""

from __future__ import annotations

import re
from typing import Any

from .research_protocol import CitationEntry, ConfidenceAssessment


INTERNAL_CITATION_RE = re.compile(r"\[(?:RAG:[^\]]+|Web:https?://[^\]]+)\]")
NUMERIC_CITATION_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class CitationCompiler:
    """Stable per-report numbering derived only from actually used evidence."""

    def __init__(self, evidence: list[dict[str, Any]]) -> None:
        self.evidence = [item for item in evidence if isinstance(item, dict)]
        self.by_ref: dict[str, dict[str, Any]] = {}
        for item in self.evidence:
            for ref in item.get("evidence_refs") or []:
                if str(ref):
                    key = str(ref)
                    if key not in self.by_ref:
                        self.by_ref[key] = dict(item)
                        continue
                    existing = self.by_ref[key]
                    quotes = []
                    for candidate in (existing, item):
                        quote = re.sub(
                            r"\s+",
                            " ",
                            str(candidate.get("verbatim_quote") or candidate.get("claim") or ""),
                        ).strip()
                        if quote and quote not in quotes:
                            quotes.append(quote)
                    existing["verbatim_quote"] = " ".join(quotes)[:1800]

    def compile(
        self,
        raw_report: str,
        *,
        claim_assessments: list[dict[str, Any]] | None = None,
        source_coverage: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[CitationEntry], list[ConfidenceAssessment]]:
        body = _extract_answer(raw_report)
        ordered_refs: list[str] = []
        for ref in INTERNAL_CITATION_RE.findall(body):
            if ref in self.by_ref and ref not in ordered_refs:
                ordered_refs.append(ref)
        number_by_ref = {ref: index + 1 for index, ref in enumerate(ordered_refs)}
        evidence_number_by_id = {
            str(item.get("id")): number_by_ref[ref]
            for item in self.evidence
            for ref in item.get("evidence_refs") or []
            if str(item.get("id") or "") and ref in number_by_ref
        }
        body = INTERNAL_CITATION_RE.sub(lambda match: f"[{number_by_ref[match.group(0)]}]" if match.group(0) in number_by_ref else "", body)
        body = _merge_adjacent_numeric_citations(body)
        entries = [self._entry(number_by_ref[ref], self.by_ref[ref]) for ref in ordered_refs]
        confidence = _confidence_assessments(
            body,
            entries,
            claim_assessments or [],
            source_coverage or [],
            evidence_number_by_id,
        )
        return _render_report(body, entries, confidence), entries, confidence

    @staticmethod
    def is_compiled(report: str) -> bool:
        headings = re.findall(r"^##\s+(.+?)\s*$", str(report or ""), re.MULTILINE)
        return headings == ["回答", "参考文献与证据", "置信度附录"]

    def _entry(self, number: int, item: dict[str, Any]) -> CitationEntry:
        location = str(item.get("paper_section") or "").strip()
        page_start = item.get("page_start")
        page_end = item.get("page_end")
        if page_start is not None:
            location = f"{location + '；' if location else ''}p.{page_start}"
            if page_end not in (None, page_start):
                location += f"-{page_end}"
        quote = re.sub(r"\s+", " ", str(item.get("verbatim_quote") or item.get("claim") or "")).strip()
        return CitationEntry(
            number=number,
            title=str(item.get("document_title") or "题名元数据未提供"),
            source_type=str(item.get("evidence_class") or item.get("source") or "source"),
            authors=[
                str(value).strip()
                for value in item.get("authors") or item.get("creators") or []
                if str(value).strip()
            ],
            organization=str(
                item.get("organization") or item.get("institution")
                or item.get("publisher") or ""
            ).strip(),
            publication_year=_publication_year(
                item.get("publication_year") or item.get("published_at") or item.get("year")
            ),
            identifier=str(item.get("paper_id") or ""),
            url=str(item.get("url") or ""),
            location=location,
            quote=quote[:900],
            evidence_id=str(item.get("id") or ""),
        )


def compile_report(
    raw_report: str,
    evidence: list[dict[str, Any]],
    *,
    claim_assessments: list[dict[str, Any]] | None = None,
    source_coverage: list[dict[str, Any]] | None = None,
) -> str:
    return CitationCompiler(evidence).compile(
        raw_report,
        claim_assessments=claim_assessments,
        source_coverage=source_coverage,
    )[0]


def _extract_answer(report: str) -> str:
    value = str(report or "").strip()
    if "## 回答" in value:
        value = value.split("## 回答", 1)[1]
    value = re.split(
        r"^##\s+(?:研究依据|可靠性与缺口|参考文献(?:与证据)?|置信度附录)\s*$",
        value,
        1,
        re.MULTILINE,
    )[0]
    return value.strip()


def _merge_adjacent_numeric_citations(text: str) -> str:
    pattern = re.compile(r"\[(\d+)\](?:\s*[,，、]?\s*)\[(\d+)\]")
    value = str(text)
    while pattern.search(value):
        value = pattern.sub(lambda match: f"[{match.group(1)},{match.group(2)}]", value)
    return value


def _confidence_assessments(
    body: str,
    entries: list[CitationEntry],
    claim_assessments: list[dict[str, Any]],
    source_coverage: list[dict[str, Any]],
    evidence_number_by_id: dict[str, int] | None = None,
) -> list[ConfidenceAssessment]:
    entry_numbers = {
        **(evidence_number_by_id or {}),
        **{entry.evidence_id: entry.number for entry in entries if entry.evidence_id},
    }
    rows: list[ConfidenceAssessment] = []
    for index, assessment in enumerate(claim_assessments):
        wording = str(assessment.get("wording") or assessment.get("claim") or "").strip()
        if not wording:
            continue
        evidence_ids = [str(item) for item in assessment.get("evidence_ids") or []]
        numbers = [entry_numbers[item] for item in evidence_ids if item in entry_numbers]
        reliability = str(assessment.get("reliability") or "provisional").casefold()
        limitations = [str(item) for item in assessment.get("limitations") or [] if str(item).strip()]
        if numbers and reliability in {"high", "verified", "strong"} and not limitations:
            level = "高"
        elif numbers:
            level = "中"
        elif reliability in {"low", "weak"}:
            level = "低"
        else:
            level = "待核验"
        rows.append(ConfidenceAssessment(
            claim_id=str(assessment.get("claim_id") or f"conclusion-{index + 1}"),
            conclusion=wording[:220],
            level=level,
            citation_numbers=numbers,
            rationale="直接正文证据" if numbers else "模型综合或分析判断，尚无直接外部证据",
            limitations=limitations,
        ))
        if len(rows) >= 12:
            break

    if not rows:
        for index, sentence in enumerate(_key_conclusions(body)):
            numbers = [int(item) for group in NUMERIC_CITATION_RE.findall(sentence) for item in re.split(r"\s*,\s*", group)]
            rows.append(ConfidenceAssessment(
                claim_id=f"conclusion-{index + 1}",
                conclusion=NUMERIC_CITATION_RE.sub("", sentence).strip()[:220],
                level="中" if numbers else "待核验",
                citation_numbers=numbers,
                rationale="正文引用可反向定位" if numbers else "分析判断，缺少直接外部证据",
                limitations=[],
            ))
    uncovered = sorted({
        str(item.get("subquestion_id") or "")
        for item in source_coverage
        if str(item.get("status") or "") in {"gap", "failed"}
    } - {""})
    if uncovered and rows:
        rows[-1].limitations.append(
            f"仍有 {len(uncovered)} 个研究维度未闭合，详见正文的证据边界说明"
        )
    return rows[:12]


def _key_conclusions(body: str) -> list[str]:
    candidates = []
    for raw in body.splitlines():
        line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", raw).strip()
        if line.startswith("#") or len(line) < 30:
            continue
        sentence = re.split(r"(?<=[。！？.!?])\s*", line, 1)[0]
        if sentence and sentence not in candidates:
            candidates.append(sentence)
        if len(candidates) >= 8:
            break
    return candidates or ["本报告的主要分析结论"]


def _render_report(
    body: str,
    entries: list[CitationEntry],
    confidence: list[ConfidenceAssessment],
) -> str:
    references = []
    for entry in entries:
        identity = "；".join(item for item in (entry.identifier, entry.url, entry.location) if item)
        creator = "、".join(entry.authors) or entry.organization or "作者/机构元数据未提供"
        year = entry.publication_year or "年份元数据未提供"
        references.append(
            f"{entry.number}. **{_escape(entry.title)}**（{_escape(entry.source_type)}"
            f"；{_escape(creator)}；{_escape(year)}"
            f"{'；' + _escape(identity) if identity else ''}）\n"
            f"   - 引用内容：{_escape(entry.quote) or '未提供可复核正文片段'}"
        )
    if not references:
        references.append("本轮没有可作为外部事实依据的正文证据；正文中的未引用内容均按分析判断处理。")

    confidence_lines = [
        "| 关键结论 | 置信度 | 依据 | 限制与待核验项 |",
        "|---|---|---|---|",
    ]
    for item in confidence:
        refs = "".join(f"[{number}]" for number in item.citation_numbers)
        rationale = (refs + ("；" if refs else "") + item.rationale).strip("；")
        confidence_lines.append(
            f"| {_cell(item.conclusion)} | {item.level} | {_cell(rationale)} | "
            f"{_cell('；'.join(item.limitations) or '无已知关键限制')} |"
        )
    return (
        "## 回答\n\n" + body.strip()
        + "\n\n## 参考文献与证据\n\n" + "\n".join(references)
        + "\n\n## 置信度附录\n\n" + "\n".join(confidence_lines)
    ).strip()


def _escape(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().replace("|", "\\|")


def _cell(value: str) -> str:
    return _escape(value).replace("\n", " ")


def _publication_year(value: Any) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return match.group(0) if match else ""
