"""证据网络（Evidence Graph）— 声明→来源→支持/反驳的有向图

每次查询构建一个临时 EvidenceGraph，追踪：
- 每个声明的来源（RAG/Web/Model）
- 声明之间的支持/反驳关系
- 每条证据链的不确定性传播

对应架构文档 §2.2
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from .source_status import SourceResult


SOURCE_AUTHORITY = {
    "RAG": 0.7,
    "Web": 0.5,
    "Model": 0.4,
    "FactCheck": 0.8,
    "Synthesize": 0.6,
}


@dataclass
class EvidenceNode:
    """证据图中的节点 — 一个原子声明"""
    id: str
    claim: str                          # 声明内容
    source: Literal["RAG", "Web", "Model", "FactCheck", "Synthesize"]
    source_detail: str = ""             # 来源详情（文档ID/URL/模型名）
    authority_score: float = 0.5        # 来源权威分 [0, 1]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 图结构
    supporting: list[str] = field(default_factory=list)     # 支持此声明的节点 ID
    contradicting: list[str] = field(default_factory=list)  # 与此声明矛盾的节点 ID
    derived_from: list[str] = field(default_factory=list)   # 推理来源节点 ID

    # 不确定性分解（§2.3）
    uncertainty: float = 0.3            # 综合不确定性 [0, 1]
    uncertainty_breakdown: dict = field(default_factory=lambda: {
        "aleatoric": 0.1,       # 数据固有噪音
        "epistemic": 0.15,      # 知识不足
        "source_quality": 0.05, # 源质量
        "temporal": 0.2,        # 时效性
        "consensus_gap": 0.3,   # 源间分歧
    })

    verified: bool = False              # 是否经过 FactCheck 验证

    def to_dict(self) -> dict:
        """序列化为可写入报告的结构。"""
        return asdict(self)


@dataclass
class EvidenceGraph:
    """每次查询的证据网络 — 声明节点的有向图"""
    nodes: dict[str, EvidenceNode] = field(default_factory=dict)
    source_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_node(self, node: EvidenceNode) -> None:
        if node.authority_score == 0.5:
            node.authority_score = SOURCE_AUTHORITY.get(node.source, node.authority_score)
        self.nodes[node.id] = node

    def add_support(self, supporter_id: str, supported_id: str) -> None:
        """添加支持关系"""
        if supporter_id in self.nodes and supported_id in self.nodes:
            self.nodes[supporter_id].supporting.append(supported_id)
            self.nodes[supported_id].derived_from.append(supporter_id)

    def add_contradiction(self, node_a: str, node_b: str) -> None:
        """添加矛盾关系"""
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].contradicting.append(node_b)
            self.nodes[node_b].contradicting.append(node_a)

    def find_contradictions(self) -> list[tuple[EvidenceNode, EvidenceNode]]:
        """找出所有矛盾对"""
        pairs = []
        seen = set()
        for nid, node in self.nodes.items():
            for cid in node.contradicting:
                pair = tuple(sorted([nid, cid]))
                if pair not in seen:
                    seen.add(pair)
                    pairs.append((node, self.nodes[cid]))
        return pairs

    def find_single_source(self) -> list[EvidenceNode]:
        """找出仅单一来源支持的声明（derived_from 为空且无 supporting）"""
        return [
            n for n in self.nodes.values()
            if not n.derived_from and not n.supporting and not n.contradicting
        ]

    def consensus_summary(self) -> dict:
        """生成共识摘要：共识声明 / 分歧声明 / 单源声明"""
        uncontested = []
        contested = []
        source_counts: dict[str, int] = {}
        for n in self.nodes.values():
            source_counts[n.source] = source_counts.get(n.source, 0) + 1
            if n.contradicting:
                contested.append(n)
            else:
                uncontested.append(n)

        return {
            "total_nodes": len(self.nodes),
            "consensus_count": len(uncontested),
            "contested_count": len(contested),
            "single_source_count": len(self.find_single_source()),
            "source_counts": source_counts,
            "contested_pairs": [
                {"a": a.claim[:80], "b": b.claim[:80]}
                for a, b in self.find_contradictions()
            ],
            "avg_authority": round(
                sum(n.authority_score for n in self.nodes.values()) / len(self.nodes),
                3,
            ) if self.nodes else 0,
        }

    def propagate_uncertainty(self) -> None:
        """不确定性传播：被降权源的 derived_from 节点自动降置信度"""
        for node in self.nodes.values():
            if node.authority_score < 0.3:
                for child_id in node.supporting:
                    if child_id in self.nodes:
                        child = self.nodes[child_id]
                        child.uncertainty = min(1.0, child.uncertainty + 0.2)
                        child.uncertainty_breakdown["source_quality"] += 0.15

    def link_surface_relations(self) -> None:
        """基于文本相似度建立轻量支持/反驳关系。

        这是 Phase 2 的确定性保底逻辑：不依赖 LLM，也不会替代后续更精确的
        claim extraction。它只处理明显相似且极性相反/相同的声明。
        """
        nodes = list(self.nodes.values())
        for idx, left in enumerate(nodes):
            for right in nodes[idx + 1:]:
                overlap = _claim_overlap(left.claim, right.claim)
                if overlap < 0.55:
                    continue
                left_polarity = _claim_polarity(left.claim)
                right_polarity = _claim_polarity(right.claim)
                if left_polarity != right_polarity:
                    self.add_contradiction(left.id, right.id)
                elif left.source != right.source:
                    self.add_support(left.id, right.id)
                    self.add_support(right.id, left.id)

    def to_dict(self) -> dict:
        """完整证据图 payload。"""
        return {
            "summary": self.consensus_summary(),
            "source_statuses": self.source_statuses,
            "nodes": [node.to_dict() for node in self.nodes.values()],
        }

    def to_json(self) -> str:
        """完整证据图 JSON。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def build_evidence_graph(sources: dict[str, str]) -> EvidenceGraph:
    """从三源文本输出构建 EvidenceGraph。"""
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
    """从结构化来源结果构建证据图；failed/fallback 来源不参与投票。"""

    graph = EvidenceGraph()
    graph.source_statuses = {source: result.to_dict() for source, result in results.items()}
    for source, result in results.items():
        if not result.is_valid_evidence:
            continue
        for node in extract_claims_from_text(
            result.content,
            source,
            result.detail or result.source,
            prefix=source.lower(),
        ):
            graph.add_node(node)
    graph.link_surface_relations()
    graph.propagate_uncertainty()
    return graph


def extract_claims_from_text(
    text: str,
    source: str,
    source_detail: str = "",
    prefix: str = "claim",
) -> list[EvidenceNode]:
    """从文本中简单提取声明节点（按段落分割，每段一个节点）

    更精确的提取应由 LLM 完成，此函数用于 Phase 1 快速原型。
    """
    nodes = []
    paragraphs = []
    for raw in re.split(r"\n\s*\n|\n(?=[\-*]\s+|\d+[.、]\s*)", text):
        cleaned = _clean_claim_text(raw)
        if cleaned and _is_meaningful_claim(cleaned):
            paragraphs.append(cleaned)

    for i, para in enumerate(paragraphs):
        # 跳过明显的标题行
        if para.startswith("#") or para.startswith("##") or para.startswith("---"):
            continue
        # 截断过长段落
        claim = para[:200]
        node = EvidenceNode(
            id=f"{source}_{prefix}_{i}",
            claim=claim,
            source=source,
            source_detail=source_detail,
            authority_score=SOURCE_AUTHORITY.get(source, 0.5),
        )
        nodes.append(node)

    return nodes


def _clean_claim_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"^[-*]\s*", "", text)
    text = re.sub(r"^\d+[.、]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_meaningful_claim(text: str) -> bool:
    """过滤标题和噪声，同时保留短事实句。"""
    if len(text) < 8:
        return False
    if text in {"无", "none", "n/a"}:
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
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())
    if not text:
        return set()
    if len(text) <= 12:
        return {text}
    return {text[i:i + 2] for i in range(len(text) - 1)}


def _claim_polarity(text: str) -> str:
    negative_markers = ["不", "未", "没有", "无法", "不能", "不会", "无 ", "not", "no "]
    lowered = text.lower()
    return "negative" if any(marker in lowered for marker in negative_markers) else "positive"
