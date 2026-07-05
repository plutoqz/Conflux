"""Evidence Graph for source-aware claim tracing.

The graph stores claim nodes emitted by RAG, Web, and Model agents. Successful
and low-relevance source results are allowed to become evidence nodes;
no-evidence, failed, and fallback sources remain visible in source_statuses but
are excluded from consensus and FactCheck support.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from .source_status import SourceResult


EvidenceSource = Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]

SOURCE_AUTHORITY = {
    "RAG": 0.7,
    "Web": 0.5,
    "Model": 0.4,
    "FactCheck": 0.8,
    "Synthesize": 0.6,
}

LOW_RELEVANCE_AUTHORITY_MULTIPLIER = 0.6
LOW_RELEVANCE_CONFIDENCE_MULTIPLIER = 0.65


@dataclass
class EvidenceNode:
    """One atomic claim in the evidence graph."""

    id: str
    claim: str
    source: EvidenceSource
    source_detail: str = ""
    authority_score: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    limitations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    supporting: list[str] = field(default_factory=list)
    contradicting: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    uncertainty: float = 0.3
    uncertainty_breakdown: dict = field(default_factory=lambda: {
        "aleatoric": 0.1,
        "epistemic": 0.15,
        "source_quality": 0.05,
        "temporal": 0.2,
        "consensus_gap": 0.3,
    })
    verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceGraph:
    """A temporary claim graph for one research run."""

    nodes: dict[str, EvidenceNode] = field(default_factory=dict)
    source_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_node(self, node: EvidenceNode) -> None:
        if node.authority_score == 0.5:
            node.authority_score = SOURCE_AUTHORITY.get(node.source, node.authority_score)
        self.nodes[node.id] = node

    def add_support(self, supporter_id: str, supported_id: str) -> None:
        if supporter_id in self.nodes and supported_id in self.nodes:
            self.nodes[supporter_id].supporting.append(supported_id)
            self.nodes[supported_id].derived_from.append(supporter_id)

    def add_contradiction(self, node_a: str, node_b: str) -> None:
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].contradicting.append(node_b)
            self.nodes[node_b].contradicting.append(node_a)

    def find_contradictions(self) -> list[tuple[EvidenceNode, EvidenceNode]]:
        pairs = []
        seen = set()
        for node_id, node in self.nodes.items():
            for other_id in node.contradicting:
                pair = tuple(sorted([node_id, other_id]))
                if pair not in seen and other_id in self.nodes:
                    seen.add(pair)
                    pairs.append((node, self.nodes[other_id]))
        return pairs

    def find_single_source(self) -> list[EvidenceNode]:
        return [
            node
            for node in self.nodes.values()
            if not node.derived_from and not node.supporting and not node.contradicting
        ]

    def consensus_summary(self) -> dict:
        uncontested = []
        contested = []
        source_counts: dict[str, int] = {}
        for node in self.nodes.values():
            source_counts[node.source] = source_counts.get(node.source, 0) + 1
            if node.contradicting:
                contested.append(node)
            else:
                uncontested.append(node)

        return {
            "total_nodes": len(self.nodes),
            "consensus_count": len(uncontested),
            "contested_count": len(contested),
            "single_source_count": len(self.find_single_source()),
            "source_counts": source_counts,
            "contested_pairs": [
                {"a": left.claim[:80], "b": right.claim[:80]}
                for left, right in self.find_contradictions()
            ],
            "avg_authority": round(
                sum(node.authority_score for node in self.nodes.values()) / len(self.nodes),
                3,
            ) if self.nodes else 0,
        }

    def propagate_uncertainty(self) -> None:
        for node in self.nodes.values():
            if node.authority_score < 0.3:
                for child_id in node.supporting:
                    if child_id in self.nodes:
                        child = self.nodes[child_id]
                        child.uncertainty = min(1.0, child.uncertainty + 0.2)
                        child.uncertainty_breakdown["source_quality"] += 0.15

    def link_surface_relations(self) -> None:
        nodes = list(self.nodes.values())
        for index, left in enumerate(nodes):
            for right in nodes[index + 1:]:
                overlap = _claim_overlap(left.claim, right.claim)
                if overlap < 0.55:
                    continue
                if _claim_polarity(left.claim) != _claim_polarity(right.claim):
                    self.add_contradiction(left.id, right.id)
                elif left.source != right.source:
                    self.add_support(left.id, right.id)
                    self.add_support(right.id, left.id)

    def to_dict(self) -> dict:
        return {
            "summary": self.consensus_summary(),
            "source_statuses": self.source_statuses,
            "nodes": [node.to_dict() for node in self.nodes.values()],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def build_evidence_graph(sources: dict[str, str]) -> EvidenceGraph:
    """Build a graph from plain text source outputs."""

    graph = EvidenceGraph()
    detail_map = {
        "RAG": "Local KB",
        "Web": "Web Search",
        "Model": "LLM Knowledge",
    }
    for source, text in sources.items():
        if not text:
            continue
        for node in extract_claims_from_text(text, source, detail_map.get(source, source), prefix=source.lower()):
            graph.add_node(node)
    graph.link_surface_relations()
    graph.propagate_uncertainty()
    return graph


def build_evidence_graph_from_results(results: dict[str, SourceResult]) -> EvidenceGraph:
    """Build a graph from structured source results.

    No-evidence, failed, and fallback sources are deliberately excluded from
    nodes while their status payloads remain available for report transparency.
    Low-relevance sources can contribute contextual nodes, but their authority
    and confidence are reduced.
    """

    graph = EvidenceGraph()
    graph.source_statuses = {source: result.to_dict() for source, result in results.items()}
    for source, result in results.items():
        if not result.is_valid_evidence:
            continue
        if result.claims:
            for index, claim in enumerate(result.claims):
                if not claim.claim.strip():
                    continue
                graph.add_node(EvidenceNode(
                    id=f"{source}_claim_{index}",
                    claim=claim.claim[:240],
                    source=source,
                    source_detail=result.detail or result.source,
                    authority_score=_authority_for_result(source, result),
                    evidence_refs=claim.evidence_refs,
                    confidence=_confidence_for_result(claim.confidence, result),
                    limitations=_limitations_for_result(claim.limitations, result),
                ))
        else:
            for node in extract_claims_from_text(
                result.content,
                source,
                result.detail or result.source,
                prefix=source.lower(),
            ):
                node.authority_score = _authority_for_result(source, result)
                node.confidence = _confidence_for_result(node.confidence, result)
                node.limitations = _limitations_for_result(node.limitations, result)
                graph.add_node(node)
    graph.link_surface_relations()
    graph.propagate_uncertainty()
    return graph


def _authority_for_result(source: str, result: SourceResult) -> float:
    authority = SOURCE_AUTHORITY.get(source, 0.5)
    if result.is_low_relevance:
        authority *= LOW_RELEVANCE_AUTHORITY_MULTIPLIER
    return round(authority, 3)


def _confidence_for_result(confidence: float, result: SourceResult) -> float:
    if result.is_low_relevance:
        confidence *= LOW_RELEVANCE_CONFIDENCE_MULTIPLIER
    return round(max(0.0, min(1.0, confidence)), 3)


def _limitations_for_result(limitations: list[str], result: SourceResult) -> list[str]:
    merged = list(limitations)
    if result.is_low_relevance:
        merged.append("low relevance; use as contextual evidence only")
    return merged


def extract_claims_from_text(
    text: str,
    source: str,
    source_detail: str = "",
    prefix: str = "claim",
) -> list[EvidenceNode]:
    """Extract coarse claim nodes from paragraphs and bullet lines."""

    nodes: list[EvidenceNode] = []
    paragraphs = []
    for raw in re.split(r"\n\s*\n|\n(?=[\-*]\s+|\d+[.)]\s*)", text):
        cleaned = _clean_claim_text(raw)
        if cleaned and _is_meaningful_claim(cleaned):
            paragraphs.append(cleaned)

    for index, paragraph in enumerate(paragraphs):
        if paragraph.startswith("#") or paragraph.startswith("---"):
            continue
        nodes.append(EvidenceNode(
            id=f"{source}_{prefix}_{index}",
            claim=paragraph[:200],
            source=source,
            source_detail=source_detail,
            authority_score=SOURCE_AUTHORITY.get(source, 0.5),
        ))
    return nodes


def _clean_claim_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"^[-*]\s*", "", text)
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_meaningful_claim(text: str) -> bool:
    if len(text) < 8:
        return False
    if text.lower() in {"none", "n/a", "na"}:
        return False
    if re.fullmatch(r"[-=_#\s]+", text):
        return False
    return True


def _claim_overlap(left: str, right: str) -> float:
    left_tokens = _claim_tokens(left)
    right_tokens = _claim_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _claim_tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())
    if not cleaned:
        return set()
    if len(cleaned) <= 12:
        return {cleaned}
    return {cleaned[index:index + 2] for index in range(len(cleaned) - 1)}


def _claim_polarity(text: str) -> str:
    negative_markers = [
        "不",
        "没有",
        "无法",
        "不能",
        "不会",
        "not",
        "no ",
    ]
    lowered = text.lower()
    return "negative" if any(marker in lowered for marker in negative_markers) else "positive"
