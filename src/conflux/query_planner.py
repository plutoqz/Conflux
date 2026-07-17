"""Lightweight deterministic query planning and relevance helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "that",
    "this",
    "what",
    "how",
    "why",
    "research",
    "explain",
    "system",
    "systems",
    "design",
    "risk",
    "risks",
    "retrieval",
    "augmented",
    "研究",
    "说明",
    "结合",
    "核心",
    "概念",
    "流程",
    "设计",
    "风险",
    "控制",
    "工程",
    "落地",
    "建议",
    "系统",
    "关系",
    "发展",
    "脉络",
    "如何",
    "什么",
    "哪些",
}


DOMAIN_PRIORITY = {
    "nist.gov": 1.0,
    "csrc.nist.gov": 1.0,
    "esri.com": 0.95,
    "developers.arcgis.com": 0.95,
    "doc.arcgis.com": 0.95,
    "pro.arcgis.com": 0.95,
    "enterprise.arcgis.com": 0.95,
    "opengeospatial.org": 0.9,
    "ogc.org": 0.9,
    "arxiv.org": 0.85,
    "doi.org": 0.8,
    "springer.com": 0.75,
    "link.springer.com": 0.8,
    "sciencedirect.com": 0.75,
    "ieee.org": 0.75,
    "acm.org": 0.75,
    "usgs.gov": 0.8,
    "semanticscholar.org": 0.9,
    "openalex.org": 0.9,
    "crossref.org": 0.9,
    "openstreetmap.org": 0.8,
    "osm.org": 0.8,
}


LOW_QUALITY_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "pinterest.com",
    "slideshare.net",
    "scribd.com",
    "quora.com",
    "medium.com",
}


CONCEPT_EXPANSIONS = {
    "ArcGIS": ["ArcGIS", "Esri", "ArcGIS Enterprise", "ArcGIS Pro"],
    "后量子": ["post-quantum cryptography", "PQC", "NIST", "FIPS 203"],
    "抗量子": ["post-quantum cryptography", "PQC", "NIST"],
    "量子": ["quantum computing", "post-quantum cryptography"],
    "NIST": ["NIST", "FIPS 203", "ML-KEM"],
    "PQC": ["post-quantum cryptography", "PQC", "NIST"],
    "OSM": ["OpenStreetMap", "OSM"],
    "OpenStreetMap": ["OpenStreetMap", "OSM"],
    "知识图谱": ["knowledge graph", "semantic mapping", "GeoSPARQL", "ontology"],
    "语义": ["semantic mapping", "ontology", "GeoSPARQL"],
    "地理信息系统": ["geographic information system", "GIS"],
    "GIS": ["GIS", "geographic information system", "geospatial"],
    "遥感": ["remote sensing", "geospatial analysis"],
    "智能体": ["agent", "LLM agent", "GeoAI", "GIS agent"],
    "大模型": ["large language model", "LLM"],
    "GeoAI": ["GeoAI", "geospatial artificial intelligence"],
    "洪水": ["flood", "flood depth estimation", "water level", "hydrology"],
    "水深": ["water depth", "flood depth estimation", "water level", "inundation depth"],
    "内涝": ["urban flooding", "pluvial flood", "inundation depth", "urban drainage"],
    "水文": ["hydrology", "hydrological modelling", "water level", "flood forecasting"],
    "flood": ["flood depth estimation", "inundation mapping", "water level", "hydrology"],
}


TECHNICAL_ENTITIES = {
    "arcgis",
    "esri",
    "pqc",
    "nist",
    "fips",
    "fips 203",
    "ml-kem",
    "ml-dsa",
    "slh-dsa",
    "osm",
    "openstreetmap",
    "geosparql",
    "gis",
    "geoai",
    "llm",
    "rag",
    "bm25",
    "hydrology",
    "flood depth estimation",
    "water level",
    "nist.gov",
}


@dataclass(frozen=True)
class QueryPlan:
    """A small deterministic query plan for retrieval tools."""

    original_query: str
    subqueries: list[str]
    entities: list[str]
    terms: list[str]

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query,
            "subqueries": self.subqueries,
            "entities": self.entities,
            "terms": self.terms,
        }


def plan_queries(query: str, *, target: str, max_subqueries: int = 4) -> QueryPlan:
    """Create a compact query plan for RAG or Web retrieval."""

    terms = sorted(important_terms(query))
    entities = sorted(extract_entities(query))
    expansions = _expansions_for_query(query)

    subqueries = [query.strip()]
    combined = _dedupe_words([*entities, *expansions])
    if combined:
        subqueries.append(" ".join(combined[:12]))

    if target == "web":
        for domain in _priority_domains_for_query(query):
            if combined:
                subqueries.append(f"site:{domain} {' '.join(combined[:8])}")
    elif terms:
        subqueries.append(" ".join(terms[:10]))

    clean = []
    seen = set()
    for item in subqueries:
        normalized = re.sub(r"\s+", " ", item).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            clean.append(normalized)
        if len(clean) >= max_subqueries:
            break

    return QueryPlan(
        original_query=query,
        subqueries=clean or [query],
        entities=entities,
        terms=terms,
    )


def rewrite_queries(query: str, *, target: str, attempt: int = 1) -> list[str]:
    """Generate deterministic gap-focused retries after weak retrieval."""

    plan = plan_queries(query, target=target, max_subqueries=6)
    expansions = _expansions_for_query(query)
    core = _dedupe_words([*plan.entities, *expansions, *plan.terms])[:12]
    suffixes = ["method results limitations", "review benchmark dataset"]
    if target == "rag":
        candidates = [" ".join(core), f"{' '.join(core)} {suffixes[(attempt - 1) % len(suffixes)]}"]
    else:
        academic = " ".join(core)
        candidates = [
            f"{academic} paper results DOI",
            f"site:semanticscholar.org {academic}",
            f"site:openalex.org {academic}",
            f"site:arxiv.org {academic}",
        ]
    original = {item.casefold() for item in plan.subqueries}
    return [
        item for item in _dedupe_words(candidates)
        if item and item.casefold() not in original
    ]


def important_terms(text: str) -> set[str]:
    """Extract mixed Chinese/English content terms from a query or snippet."""

    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9+.\-]{1,}|[\u4e00-\u9fff]{2,}", text):
        lowered = raw.lower()
        if lowered not in STOPWORDS and raw not in STOPWORDS and len(raw) >= 2:
            terms.add(lowered)

    for phrase in _known_phrases(text):
        lowered = phrase.lower()
        if lowered not in STOPWORDS:
            terms.add(lowered)

    terms.update(_optional_jieba_terms(text))
    return {term for term in terms if term not in STOPWORDS and len(term) >= 2}


def extract_entities(text: str) -> set[str]:
    """Extract high-signal technical entities and standards."""

    entities = set()
    lower = text.lower()
    for entity in TECHNICAL_ENTITIES:
        if entity in lower:
            entities.add(entity)

    for raw in re.findall(r"\b[A-Z][A-Z0-9+.\-]{1,}\b|\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b", text):
        if len(raw) >= 2:
            entities.add(raw.lower())

    for phrase in _known_phrases(text):
        entities.add(phrase.lower())
    return entities


def is_academic_query(text: str) -> bool:
    lower = text.casefold()
    markers = {
        "论文", "文献", "研究", "方法", "实验", "基准", "数据集", "综述",
        "paper", "study", "research", "method", "experiment", "benchmark", "dataset", "review",
        "doi", "arxiv", "洪水", "水深", "水文", "遥感",
    }
    return any(marker in lower for marker in markers)


def overlap_score(query_terms: set[str], text: str) -> float:
    """Return the fraction of query terms found in text."""

    if not query_terms:
        return 0.0
    lowered = text.lower()
    matched = {term for term in query_terms if term in lowered}
    return len(matched) / len(query_terms)


def entity_score(query_entities: set[str], text: str) -> float:
    """Return the fraction of query entities found in text."""

    if not query_entities:
        return 0.0
    lowered = text.lower()
    matched = {entity for entity in query_entities if entity in lowered}
    return len(matched) / len(query_entities)


def _expansions_for_query(query: str) -> list[str]:
    expansions: list[str] = []
    lower = query.lower()
    for trigger, values in CONCEPT_EXPANSIONS.items():
        if trigger.lower() in lower or trigger in query:
            expansions.extend(values)
    return _dedupe_words(expansions)


def _priority_domains_for_query(query: str) -> list[str]:
    lower = query.lower()
    domains: list[str] = []
    if any(term in lower for term in ("nist", "pqc", "后量子", "fips")):
        domains.extend(["nist.gov", "csrc.nist.gov"])
    if any(term in lower for term in ("arcgis", "esri")):
        domains.extend(["esri.com", "developers.arcgis.com"])
    if any(term in lower for term in ("osm", "openstreetmap", "geosparql", "ogc", "知识图谱")):
        domains.extend(["opengeospatial.org", "openstreetmap.org"])
    if any(term in lower for term in ("gis", "geoai", "智能体", "llm")):
        domains.extend(["arxiv.org", "doi.org"])
    if any(term in lower for term in (
        "论文", "研究", "paper", "study", "flood", "洪水", "水深", "水文", "遥感",
    )):
        domains.extend(["semanticscholar.org", "openalex.org", "crossref.org", "arxiv.org", "doi.org"])
    return _dedupe_words(domains)


def _known_phrases(text: str) -> set[str]:
    phrases = set()
    lower = text.lower()
    for trigger, values in CONCEPT_EXPANSIONS.items():
        if trigger.lower() in lower or trigger in text:
            phrases.add(trigger)
            phrases.update(values)
    return phrases


def _optional_jieba_terms(text: str) -> set[str]:
    try:
        import jieba
    except Exception:
        return set()

    terms = set()
    for raw in jieba.cut(text):
        term = raw.strip().lower()
        if len(term) >= 2 and term not in STOPWORDS:
            terms.add(term)
    return terms


def _dedupe_words(items: list[str]) -> list[str]:
    clean = []
    seen = set()
    for item in items:
        normalized = re.sub(r"\s+", " ", str(item)).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            clean.append(normalized)
    return clean
