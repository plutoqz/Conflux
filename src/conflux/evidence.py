"""Evidence Graph for source-aware claim tracing.

The graph stores claim nodes emitted by RAG, Web, and Model agents. Successful
and low-relevance source results are allowed to become evidence nodes;
no-evidence, failed, and fallback sources remain visible in source_statuses but
are excluded from consensus and FactCheck support.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from .source_status import EXTERNAL_EVIDENCE_CLASSES, EvidenceItem, SourceResult


EvidenceSource = Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]

EVIDENCE_AUTHORITY = {
    "peer_reviewed": 0.9,
    "authoritative_document": 0.85,
    "preprint": 0.72,
    "community_content": 0.42,
    # Parametric knowledge is not externally citable, but it is still useful
    # research context. Reliability is controlled by claim type and required
    # verification, not by assigning the Model channel a near-zero weight.
    "model_inference": 0.55,
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
    paper_id: str = ""
    evidence_class: str = ""
    verbatim_quote: str = ""
    paper_section: str = ""
    relevance: float = 0.0
    research_type: str = ""
    metric: str = ""
    document_title: str = ""
    authors: list[str] = field(default_factory=list)
    organization: str = ""
    url: str = ""
    published_at: str = ""
    retrieved_at: str = ""
    content_hash: str = ""
    content_kind: str = ""
    directness: float = 0.0
    subquestion_id: str = ""
    relationship: str = "supports"
    page_start: int | None = None
    page_end: int | None = None
    domain_relevance: float = 0.0
    claim_entailment: float = 0.0
    evidence_role: str = ""
    source_identity: str = ""
    body_valid: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceGraph:
    """A temporary claim graph for one research run."""

    nodes: dict[str, EvidenceNode] = field(default_factory=dict)
    source_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_node(self, node: EvidenceNode) -> None:
        if node.authority_score == 0.5:
            node.authority_score = EVIDENCE_AUTHORITY.get(node.evidence_class, 0.2)
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
        """Summarise uncontested vs contested nodes and true multi-source consensus.

        A claim reaches *consensus* only when it is supported by at least two
        independent external-fact sources (RAG or Web) with distinct paper/URL
        identity — a RAG paper and a Web page reprinting it do not count as two.
        """
        uncontested = []
        contested = []
        source_counts: dict[str, int] = {}
        for node in self.nodes.values():
            source_counts[node.source] = source_counts.get(node.source, 0) + 1
            if node.contradicting:
                contested.append(node)
            else:
                uncontested.append(node)

        external_nodes = {
            node.id: node
            for node in self.nodes.values()
            if node.evidence_class in EXTERNAL_EVIDENCE_CLASSES
        }
        consensus_components = []
        for component in _support_components(external_nodes):
            identity_groups = _independent_identity_groups(
                [external_nodes[node_id] for node_id in component]
            )
            if len(identity_groups) >= 2:
                consensus_components.append({
                    "node_ids": sorted(component),
                    "source_identities": sorted(group[0] for group in identity_groups),
                })
        independent_source_count = len(_independent_identity_groups(list(external_nodes.values())))
        true_consensus_count = len(consensus_components)

        return {
            "total_nodes": len(self.nodes),
            "consensus_count": true_consensus_count,
            "true_consensus_count": true_consensus_count,
            "uncontested_count": len(uncontested),
            "contested_count": len(contested),
            "single_source_count": len(self.find_single_source()),
            "independent_external_sources": independent_source_count,
            "consensus_components": consensus_components,
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
                    claim=claim.claim[:500],
                    source=source,
                    source_detail=result.detail or result.source,
                    authority_score=_authority_for_item(result, claim),
                    evidence_refs=claim.evidence_refs,
                    confidence=_confidence_for_result(claim.confidence, result),
                    limitations=_limitations_for_result(claim.limitations, result),
                    paper_id=_paper_id_for_item(claim),
                    evidence_class=claim.evidence_class or result.evidence_class,
                    verbatim_quote=claim.verbatim_quote,
                    paper_section=claim.paper_section,
                    relevance=claim.relevance,
                    research_type=claim.research_type,
                    metric=claim.metric,
                    document_title=claim.document_title,
                    authors=list(claim.authors),
                    organization=claim.organization,
                    url=claim.url,
                    published_at=claim.published_at,
                    retrieved_at=claim.retrieved_at,
                    content_hash=claim.content_hash,
                    content_kind=claim.content_kind,
                    directness=claim.directness,
                    subquestion_id=claim.subquestion_id,
                    relationship=claim.relationship,
                    page_start=claim.page_start,
                    page_end=claim.page_end,
                    domain_relevance=claim.domain_relevance,
                    claim_entailment=claim.claim_entailment,
                    evidence_role=claim.evidence_role,
                    source_identity=claim.source_identity or _paper_id_for_item(claim),
                    body_valid=claim.body_valid,
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
                node.evidence_class = result.evidence_class
                graph.add_node(node)
        _deduplicate_source_nodes(graph, source)
    graph.link_surface_relations()
    graph.propagate_uncertainty()
    return graph


def _authority_for_result(source: str, result: SourceResult) -> float:
    authority = EVIDENCE_AUTHORITY.get(result.evidence_class, 0.2)
    if result.is_low_relevance:
        authority *= LOW_RELEVANCE_AUTHORITY_MULTIPLIER
    return round(authority, 3)


def _authority_for_item(result: SourceResult, item: EvidenceItem) -> float:
    evidence_class = item.evidence_class or result.evidence_class
    authority = item.authority or EVIDENCE_AUTHORITY.get(evidence_class, 0.55)
    if result.is_low_relevance:
        authority *= LOW_RELEVANCE_AUTHORITY_MULTIPLIER
    if item.relevance:
        authority *= 0.7 + (0.3 * max(0.0, min(1.0, item.relevance)))
    if item.directness:
        authority *= 0.75 + (0.25 * max(0.0, min(1.0, item.directness)))
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
            authority_score=0.2,
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


def _support_components(nodes: dict[str, EvidenceNode]) -> list[set[str]]:
    """Return connected support components; unrelated claims stay isolated."""

    remaining = set(nodes)
    components: list[set[str]] = []
    while remaining:
        root = remaining.pop()
        component = {root}
        stack = [root]
        while stack:
            current = stack.pop()
            node = nodes[current]
            neighbours = (set(node.supporting) | set(node.derived_from)) & set(nodes)
            for neighbour in neighbours:
                if neighbour not in component:
                    component.add(neighbour)
                    remaining.discard(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def _paper_id_for_item(item: EvidenceItem) -> str:
    if item.paper_id.strip():
        return _normalize_identity(item.paper_id)
    for ref in item.evidence_refs:
        identity = _identity_from_ref(ref)
        if identity:
            return identity
    return ""


def _identity_from_ref(ref: str) -> str:
    text = str(ref).strip().strip("[]")
    if text.startswith("RAG:"):
        return _normalize_identity(text[4:].split("#chunk", 1)[0])
    if text.startswith("Web:"):
        return _normalize_identity(text[4:])
    return ""


def _normalize_identity(value: str) -> str:
    text = value.strip()
    text = re.sub(r"[#?].*$", "", text)
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "doi:", text, flags=re.IGNORECASE)
    text = re.sub(r"^https?://(www\.)?arxiv\.org/(abs|pdf)/", "arxiv:", text, flags=re.IGNORECASE)
    text = re.sub(r"\.pdf$", "", text, flags=re.IGNORECASE)
    text = text.rstrip("/").lower()
    arxiv_match = re.fullmatch(r"(?:arxiv:|paper:)?(\d{4}\.\d{4,5})(?:v\d+)?", text)
    if arxiv_match:
        return f"arxiv:{arxiv_match.group(1)}"
    return text


def _evidence_identity(node: EvidenceNode) -> str:
    return _explicit_evidence_identity(node) or f"{node.source.lower()}:{node.id}"


def _explicit_evidence_identity(node: EvidenceNode) -> str:
    if node.paper_id:
        return _normalize_identity(node.paper_id)
    for ref in node.evidence_refs:
        identity = _identity_from_ref(ref)
        if identity:
            return identity
    return ""


def _deduplicate_source_nodes(graph: EvidenceGraph, source: str) -> None:
    """Drop exact normalized duplicates within one source, never prefix matches."""

    seen: set[str] = set()
    for node_id, node in list(graph.nodes.items()):
        if node.source != source:
            continue
        normalized = re.sub(r"\s+", " ", node.claim).strip().casefold()
        digest = sha256(normalized.encode("utf-8")).hexdigest()
        key = f"{_explicit_evidence_identity(node) or source.casefold()}:{digest}"
        if key in seen:
            del graph.nodes[node_id]
        else:
            seen.add(key)


def _independent_identity_groups(nodes: list[EvidenceNode]) -> list[list[str]]:
    """Group mirrors/reprints of the same claim before counting independence."""

    groups: list[tuple[EvidenceNode, list[str]]] = []
    for node in nodes:
        identity = _evidence_identity(node)
        for representative, identities in groups:
            same_document = identity in identities
            mirrored_claim = (
                _claim_overlap(node.claim, representative.claim) >= 0.9
                and (
                    _is_scholarly_mirror(identity)
                    or any(_is_scholarly_mirror(item) for item in identities)
                )
            )
            if same_document or mirrored_claim:
                if identity not in identities:
                    identities.append(identity)
                break
        else:
            groups.append((node, [identity]))
    return [identities for _, identities in groups]


def _is_scholarly_mirror(identity: str) -> bool:
    return any(
        marker in identity
        for marker in ("semanticscholar.org/", "openalex.org/", "api.crossref.org/")
    )
