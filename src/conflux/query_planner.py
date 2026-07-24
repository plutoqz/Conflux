"""Lightweight deterministic query planning and relevance helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any


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
    "当前",
    "目前",
    "采用",
    "各有",
    "代表性",
    "场景",
}


DOMAIN_PRIORITY = {
    "nist.gov": 1.0,
    "csrc.nist.gov": 1.0,
    "nccoe.nist.gov": 1.0,
    "cisa.gov": 0.95,
    "nsa.gov": 0.95,
    "media.defense.gov": 0.95,
    "europa.eu": 0.95,
    "digital-strategy.ec.europa.eu": 0.95,
    "eur-lex.europa.eu": 1.0,
    "federalregister.gov": 1.0,
    "bis.gov": 1.0,
    "whitehouse.gov": 0.95,
    "gov.uk": 0.95,
    "gov.cn": 0.95,
    "cac.gov.cn": 1.0,
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
    "地理处理": ["geoprocessing", "geospatial analysis", "spatial data processing"],
    "地理数据": ["geospatial data", "spatial data"],
    "自动化": ["automation", "automated workflow", "workflow automation"],
    "质量控制": ["data quality control", "quality assurance"],
    "数据融合": ["geospatial data fusion", "multisource data fusion"],
    "配准": ["spatial registration", "image registration"],
    "规则引擎": ["rule-based geoprocessing", "expert system"],
    "机器学习": ["machine learning", "GeoAI"],
    "深度学习": ["deep learning", "remote sensing"],
    "云原生": ["cloud-native geospatial", "cloud geoprocessing"],
    "工作流编排": ["workflow orchestration", "geoprocessing pipeline"],
    "评估基准": ["geospatial benchmark", "evaluation benchmark"],
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
    "基础模型": [
        "foundation model",
        "general-purpose AI model",
        "GPAI",
        "generative AI",
        "生成式人工智能",
        "frontier AI",
        "advanced AI model",
    ],
    "透明度义务": [
        "transparency obligations",
        "disclosure requirements",
        "documentation requirements",
    ],
    "司法辖区": [
        "major jurisdictions",
        "European Union",
        "United States",
        "China",
        "United Kingdom",
    ],
    "洪水": ["flood", "flood depth estimation", "water level", "hydrology"],
    "水深": ["water depth", "flood depth estimation", "water level", "inundation depth"],
    "内涝": ["urban flooding", "pluvial flood", "inundation depth", "urban drainage"],
    "水文": ["hydrology", "hydrological modelling", "water level", "flood forecasting"],
    "flood": ["flood depth estimation", "inundation mapping", "water level", "hydrology"],
    "局限性": ["limitations", "challenges", "failure modes", "research gaps", "future work"],
    "局限": ["limitations", "challenges", "failure modes", "research gaps", "future work"],
    "挑战": ["limitations", "challenges", "failure modes"],
    "失败模式": ["failure modes", "failure cases", "limitations"],
    "未来工作": ["future work", "research gaps", "open problems"],
    "研究空白": ["research gaps", "open problems", "future work"],
    "limitations": ["limitations", "challenges", "research gaps", "future work"],
    "failure modes": ["failure modes", "failure cases", "limitations"],
    "research gaps": ["research gaps", "open problems", "future work"],
}


TEMPORAL_MARKERS = {
    "截至",
    "当前",
    "目前",
    "最新",
    "近期",
    "近两年",
    "近三年",
    "recent",
    "latest",
    "current",
    "as of",
    "update",
    "updated",
}


WEB_INTENT_EXPANSIONS = {
    "第四轮": "fourth round",
    "筛选": "selection",
    "入选": "selection",
    "选定": "selection",
    "标准化": "standardization",
    "额外签名": "additional digital signature",
    "签名算法": "digital signature algorithms",
    "迁移": "migration",
    "路线图": "roadmap",
    "指南": "guidance",
    "指导": "guidance",
    "最终": "final",
    "草案": "draft",
    "发布": "publication",
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
    "geospatial",
    "geoprocessing",
    "llm",
    "rag",
    "bm25",
    "hydrology",
    "flood depth estimation",
    "water level",
    "nist.gov",
}


BILINGUAL_TERM_MAP = {
    "主要司法辖区": "major jurisdictions",
    "透明度义务": "transparency obligations",
    "可核验差异": "verifiable differences",
    "通用人工智能模型": "general-purpose AI model",
    "基础模型": "foundation model",
    "司法辖区": "jurisdictions",
    "地理数据": "geospatial data",
    "地理AI": "GeoAI",
    "地理处理": "geoprocessing",
    "地理信息系统": "geographic information system",
    "自动化": "automation",
    "数据采集": "data acquisition",
    "质量控制": "quality control",
    "规则引擎": "rule engine",
    "传统机器学习": "traditional machine learning",
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "大语言模型": "large language model",
    "云原生地理计算": "cloud-native geospatial computing",
    "云原生": "cloud-native",
    "工作流编排": "workflow orchestration",
    "空间分析": "spatial analysis",
    "遥感影像": "remote sensing imagery",
    "配准": "registration",
    "融合": "fusion",
    "清洗": "cleaning",
    "采集": "acquisition",
    "互操作性": "interoperability",
    "可移植性": "portability",
    "可重复性": "reproducibility",
    "可解释性": "explainability",
    "可靠性": "reliability",
    "错误恢复": "error recovery",
    "不确定性": "uncertainty",
    "系统工程": "systems engineering",
    "评估基准": "evaluation benchmark",
    "基准": "benchmark",
    "数据": "data",
    "工具": "tools",
    "部署": "deployment",
    "治理": "governance",
    "伦理": "ethics",
    "应用边界": "application boundaries",
    "跨学科": "interdisciplinary",
    "可扩展性": "scalability",
    "泛化能力": "generalization",
    "泛化": "generalization",
    "算法": "algorithm",
    "效率": "efficiency",
    "隐私": "privacy",
    "公平性": "fairness",
    "公平": "fairness",
    "审计": "audit",
    "当前": "current",
    "目前": "current",
    "局限性": "limitations",
    "局限": "limitations",
    "挑战": "challenges",
    "失败模式": "failure modes",
    "未来工作": "future work",
    "研究空白": "research gaps",
    "评估": "evaluation",
    "方法": "methods",
    "模型": "model",
    "数据集": "dataset",
    "论文": "paper",
    "研究": "research",
    "深度估计": "depth estimation",
    "水深": "water depth",
    "内涝": "urban flooding",
    "洪水": "flood",
    "水文": "hydrology",
    "风险": "risk assessment",
    "遥感": "remote sensing",
    "知识图谱": "knowledge graph",
    "智能体": "agent",
    "大模型": "large language model",
}


def concept_alias_groups(query: str) -> list[list[str]]:
    """Return deterministic cross-language aliases for concepts named in a query."""

    text = str(query or "")
    lowered = text.casefold()
    groups: list[list[str]] = []
    for trigger, expansions in sorted(
        CONCEPT_EXPANSIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if trigger.casefold() not in lowered:
            continue
        groups.append(_dedupe_words([
            trigger,
            BILINGUAL_TERM_MAP.get(trigger, ""),
            *expansions,
        ]))
    return groups


@dataclass(frozen=True)
class QueryPlan:
    """A small deterministic query plan for retrieval tools."""

    original_query: str
    subqueries: list[str]
    entities: list[str]
    terms: list[str]
    bilingual_queries: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query,
            "subqueries": self.subqueries,
            "entities": self.entities,
            "terms": self.terms,
            "bilingual_queries": self.bilingual_queries or [],
        }


class QueryRewriteProvider:
    """Independent query-rewrite boundary for bilingual retrieval.

    The deterministic path is always available. A caller may inject a cheap
    chat model for higher-quality translation without coupling the retriever
    to an LLM client.
    """

    def __init__(self, model: Any | None = None) -> None:
        self.model = model

    def rewrite(self, query: str, *, target: str = "rag") -> list[str]:
        variants = _deterministic_bilingual_queries(query, target=target)
        if self.model is None:
            return variants
        try:
            generated = self._model_rewrite(query, target=target)
        except Exception:
            generated = []
        return _dedupe_texts([*variants, *generated])

    def _model_rewrite(self, query: str, *, target: str) -> list[str]:
        from langchain_core.messages import HumanMessage

        prompt = f"""Rewrite this research query for {target} retrieval.
Return a JSON array with at most 3 concise queries: the original language,
an English translation preserving technical terms, and a terminology-expanded
variant. Do not answer the question or add prose.

Query: {query}"""
        response = self.model.invoke([HumanMessage(content=prompt)])
        content = str(response.content if hasattr(response, "content") else response)
        start, end = content.find("["), content.rfind("]")
        if start >= 0 and end > start:
            import json

            value = json.loads(content[start : end + 1])
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
        return [line.strip(" -*\t") for line in content.splitlines() if len(line.strip()) >= 8]


def plan_queries(query: str, *, target: str, max_subqueries: int = 4) -> QueryPlan:
    """Create a compact query plan for RAG or Web retrieval."""

    terms = sorted(important_terms(query))
    entities = sorted(extract_entities(query))
    expansions = _expansions_for_query(query)

    bilingual_queries = QueryRewriteProvider().rewrite(query, target=target)
    combined = _dedupe_words([*entities, *expansions])

    if target == "web":
        official_queries = _official_web_queries(query, combined)
        if is_temporal_query(query):
            # Official, dimension-specific searches must not sit behind several
            # broad rewrites where a provider result cap can prevent execution.
            subqueries = [query.strip(), *official_queries]
            subqueries.extend(bilingual_queries[:1])
            if combined:
                years = " ".join(str(year) for year in temporal_years(query))
                subqueries.append(f"{' '.join(combined[:10])} latest official status {years}".strip())
        else:
            subqueries = [query.strip(), *bilingual_queries]
            if combined:
                subqueries.append(" ".join(combined[:12]))
            subqueries.extend(official_queries)
    elif terms:
        subqueries = [query.strip(), *bilingual_queries]
        if combined:
            subqueries.append(" ".join(combined[:12]))
        subqueries.append(" ".join(terms[:10]))
    else:
        subqueries = [query.strip(), *bilingual_queries]
        if combined:
            subqueries.append(" ".join(combined[:12]))

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
        bilingual_queries=bilingual_queries,
    )


def rewrite_queries(query: str, *, target: str, attempt: int = 1) -> list[str]:
    """Generate deterministic gap-focused retries after weak retrieval."""

    plan = plan_queries(query, target=target, max_subqueries=6)
    expansions = _expansions_for_query(query)
    core = _dedupe_words([*plan.entities, *expansions, *plan.terms])[:12]
    suffixes = ["method results limitations", "review benchmark dataset"]
    if target == "rag":
        candidates = [" ".join(core), f"{' '.join(core)} {suffixes[(attempt - 1) % len(suffixes)]}"]
    elif is_temporal_query(query):
        years = " ".join(str(year) for year in temporal_years(query))
        candidates = [
            f"{' '.join(core)} latest official status update {years}",
            *_official_web_queries(query, core),
        ]
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

    acronym_pattern = (
        r"(?<![A-Za-z0-9])(?:[A-Z][A-Z0-9+.\-]{1,}|"
        r"[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)(?![A-Za-z0-9])"
    )
    for raw in re.findall(acronym_pattern, text):
        if len(raw) >= 2:
            entities.add(raw.lower())

    entities.update(item.lower() for item in standard_identifiers(text))

    for phrase in _known_phrases(text):
        entities.add(phrase.lower())
    return entities


def is_academic_query(text: str) -> bool:
    lower = text.casefold()
    markers = {
        "论文", "文献", "研究", "方法", "实验", "基准", "数据集", "综述",
        "paper", "study", "research", "method", "experiment", "benchmark", "dataset", "review",
        "doi", "arxiv", "limitation", "limitations", "challenge", "failure mode", "future work",
        "research gap", "evaluation", "algorithm", "model", "洪水", "水深", "水文", "遥感",
        "局限", "挑战", "失败模式", "未来工作", "研究空白", "评估", "算法", "模型", "风险",
    }
    # "model" describes many policy, product, statistical, and biological
    # questions; by itself it is not evidence that scholarly APIs are useful.
    markers.discard("model")
    markers.discard("模型")
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


def _deterministic_bilingual_queries(query: str, *, target: str) -> list[str]:
    if target not in {"rag", "web"}:
        return []
    original = str(query or "").strip()
    if not original:
        return []
    translated = original
    for source, target_term in sorted(BILINGUAL_TERM_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(source, f" {target_term} ")
    translated = _clean_partial_translation(translated)
    expansions = _expansions_for_query(original)
    terms = sorted(important_terms(original))
    expanded = " ".join(_dedupe_words([*expansions, *terms])[:14])
    candidates = []
    if (
        translated.casefold() != original.casefold()
        and translated
        and _useful_bilingual_variant(translated)
    ):
        candidates.append(translated)
    if expanded:
        candidates.append(expanded)
    return _dedupe_texts(candidates)


def _clean_partial_translation(value: str) -> str:
    glue = {"对", "有哪些", "有什么", "是什么", "在", "的", "方面", "之间"}
    tokens = []
    for raw in re.sub(r"\s+", " ", str(value or "")).split():
        token = raw.strip("，,；;。.?？:：")
        if token and token not in glue:
            tokens.append(token)
    return " ".join(tokens)


def _useful_bilingual_variant(value: str) -> bool:
    """Reject partial translations that collapse a subject to generic words."""

    tokens = {
        token.casefold()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9.+-]*", str(value or ""))
    }
    generic = {
        "current", "latest", "recent", "model", "models", "research",
        "paper", "papers", "method", "methods", "study", "studies",
    }
    return len(tokens - generic) >= 2


def _dedupe_texts(items: list[str]) -> list[str]:
    clean: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = re.sub(r"\s+", " ", str(item or "")).strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            clean.append(normalized)
    return clean


def _priority_domains_for_query(query: str) -> list[str]:
    lower = query.lower()
    domains: list[str] = []
    if any(term in lower for term in ("nist", "pqc", "后量子", "fips")):
        domains.extend(["nist.gov", "csrc.nist.gov"])
    if any(term in lower for term in ("nccoe", "迁移", "migration", "roadmap")):
        domains.append("nccoe.nist.gov")
    if "cisa" in lower:
        domains.append("cisa.gov")
    if re.search(r"\bnsa\b", lower):
        # NSA's public cybersecurity PDFs are reliably hosted on the official
        # Defense media domain even when nsa.gov HTML pages reject fetches.
        domains.append("media.defense.gov")
    if any(term in lower for term in ("ai act", "欧盟", "european union", "eu ")):
        domains.extend(["europa.eu", "digital-strategy.ec.europa.eu"])
    if _is_ai_policy_query(query):
        domains.extend([
            "eur-lex.europa.eu",
            "federalregister.gov",
            "whitehouse.gov",
            "gov.uk",
            "cac.gov.cn",
            "gov.cn",
        ])
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


def _is_ai_policy_query(query: str) -> bool:
    lower = str(query or "").casefold()
    return any(term in lower for term in (
        "基础模型", "通用人工智能模型", "foundation model", "general-purpose ai", "gpai",
    )) and any(term in lower for term in (
        "司法辖区", "透明度义务", "监管", "法规", "政策", "治理",
        "jurisdiction", "transparency obligation", "regulation", "policy", "governance",
    ))


def is_temporal_query(text: str) -> bool:
    """Return whether the query explicitly asks for current or recent state."""

    lowered = str(text or "").casefold()
    return bool(re.search(r"\b20\d{2}\b", lowered)) or any(marker in lowered for marker in TEMPORAL_MARKERS)


def temporal_years(text: str) -> list[int]:
    """Return a compact newest-first year window for time-sensitive search."""

    current_year = date.today().year
    explicit = [int(value) for value in re.findall(r"\b(20\d{2})\b", str(text or ""))]
    target = max(explicit) if explicit else current_year
    target = min(target, current_year + 1)
    return [target, target - 1]


def _official_web_queries(query: str, combined: list[str]) -> list[str]:
    domains = _priority_domains_for_query(query)
    if not domains:
        return []
    explicit = _explicit_web_identifiers(query)
    standards = standard_identifiers(query)
    intents = [english for marker, english in WEB_INTENT_EXPANSIONS.items() if marker in query]
    suffix = ""
    if is_temporal_query(query):
        years = " ".join(str(year) for year in temporal_years(query))
        suffix = f" latest official status update {years}"
    queries = []
    agency_names = {"nist", "nccoe", "cisa", "nsa"}
    agency_for_domain = {
        "nist.gov": "NIST",
        "csrc.nist.gov": "NIST",
        "nccoe.nist.gov": "NCCoE",
        "cisa.gov": "CISA",
        "nsa.gov": "NSA",
        "media.defense.gov": "NSA",
        "eur-lex.europa.eu": "European Union AI Act",
        "federalregister.gov": "United States AI policy",
        "whitehouse.gov": "United States AI policy",
        "gov.uk": "United Kingdom AI regulation",
        "cac.gov.cn": "China generative AI regulation",
        "gov.cn": "China generative AI regulation",
    }
    pqc_migration = any(term in query.casefold() for term in ("pqc", "post-quantum", "后量子")) and any(
        term in query.casefold() for term in ("迁移", "migration", "roadmap", "路线图")
    )
    ai_policy = _is_ai_policy_query(query)
    for domain in domains:
        agency = agency_for_domain.get(domain, "")
        topic_identifiers = [item for item in explicit if item.casefold() not in agency_names]
        if domain == "csrc.nist.gov" and len(standards) >= 2:
            final_standards = [item for item in standards if not item.casefold().endswith(" 206")]
            draft_standards = [item for item in standards if item.casefold().endswith(" 206")]
            if final_standards:
                queries.append(
                    f"site:{domain} {' '.join(final_standards)} final published NIST PQC standard{suffix}".strip()
                )
            if draft_standards:
                queries.append(
                    f"site:{domain} {' '.join(draft_standards)} FN-DSA Initial Public Draft soon".strip()
                )
            continue
        domain_hints: list[str] = []
        if ai_policy:
            domain_hints = {
                "eur-lex.europa.eu": ["GPAI", "transparency obligations"],
                "federalregister.gov": ["foundation model", "reporting requirements"],
                "whitehouse.gov": ["foundation model", "transparency reporting"],
                "gov.uk": ["foundation model", "transparency regulation"],
                "cac.gov.cn": ["generative AI service", "transparency measures"],
                "gov.cn": ["generative AI service", "transparency measures"],
            }.get(domain, [])
        elif pqc_migration:
            domain_hints = {
                "nist.gov": ["crypto agility", "SP 800-227"],
                "csrc.nist.gov": ["crypto agility", "SP 800-227"],
                "nccoe.nist.gov": ["SP 1800-38B", "SP 1800-38C", "CISA NSA quantum readiness fact sheet"],
                "cisa.gov": ["quantum readiness", "automated PQC discovery inventory tools"],
                "nsa.gov": ["CNSA 2.0", "CSfC Post Quantum Cryptography Guidance Addendum"],
                "media.defense.gov": ["CNSS Policy 15", "CNSA 2.0", "NSA post-quantum guidance"],
            }.get(domain, [])
        if domain == "nccoe.nist.gov" and any(item.casefold().startswith("sp 1800-38") for item in standards):
            queries.append(
                f"site:{domain} SP 1800-38 post-quantum cryptography migration practice guide{suffix}".strip()
            )
            continue
        focused = [agency, *topic_identifiers, *intents, *domain_hints]
        background = [item for item in combined if item.casefold() not in agency_names] if len(focused) < 3 else []
        core = _dedupe_words([*focused, *background])
        if not core:
            core = sorted(important_terms(query))
        format_hint = " filetype:pdf" if domain in {
            "nccoe.nist.gov", "cisa.gov", "nsa.gov", "media.defense.gov",
        } else ""
        queries.append(f"site:{domain}{format_hint} {' '.join(core[:12])}{suffix}".strip())
    return queries


def _explicit_web_identifiers(text: str) -> list[str]:
    pattern = (
        r"(?<![A-Za-z0-9])(?:[A-Z][A-Z0-9+.\-]{1,}|"
        r"[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)(?![A-Za-z0-9])"
    )
    identifiers = re.findall(pattern, str(text or ""))
    identifiers.extend(standard_identifiers(text))
    return _dedupe_words(identifiers)


def standard_identifiers(text: str) -> list[str]:
    """Expand compact standard lists such as ``FIPS 203/204/205/206``."""

    identifiers: list[str] = []
    pattern = re.compile(
        r"(?<![A-Za-z0-9])(FIPS|SP|IR)\s*"
        r"(\d+(?:-\d+)*(?:\s*(?:/|,|，|、)\s*\d+(?:-\d+)*)*)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(str(text or "")):
        family = match.group(1).upper()
        for number in re.split(r"\s*(?:/|,|，|、)\s*", match.group(2)):
            identifiers.append(f"{family} {number}")
    return _dedupe_words(identifiers)


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
