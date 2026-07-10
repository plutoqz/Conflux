# Web Search Agent Design Patterns

## Overview

A web search agent is an LLM-powered system that can formulate search queries,
evaluate results, extract relevant information, and synthesize findings.
Designing such an agent requires careful consideration of search strategy,
result evaluation, and integration with other knowledge sources.

## Core Components

### 1. Query Formulation

The agent must translate a research question into effective search queries:

- **Query decomposition**: Break complex questions into sub-queries
- **Keyword extraction**: Identify the most salient search terms
- **Query expansion**: Add related terms to improve recall
- **Language adaptation**: Match the language of expected sources

### 2. Search Execution

- **Search API selection**: Google, Bing, DuckDuckGo, SerpAPI
- **Result count**: Typically 3-10 results per query
- **Search filters**: Date range, domain, language
- **Rate limiting**: Respect API quotas and politeness

### 3. Result Evaluation

Not all search results are equal:

- **Authority assessment**: Government (.gov), academic (.edu), reputable news
- **Recency evaluation**: Publication date, last updated
- **Source diversity**: Avoid echo chamber from single domain
- **Relevance scoring**: LLM-based or heuristic scoring

### 4. Content Extraction

- **HTML parsing**: Extract main content (not nav/sidebar/ads)
- **Paywall handling**: Some sources require authentication
- **Dynamic content**: JavaScript-rendered pages may need headless browser
- **Content summarization**: LLM-based extraction of key points

### 5. Information Synthesis

- **Cross-referencing**: Verify claims across multiple sources
- **Conflict detection**: Identify contradictory information
- **Confidence estimation**: Signal when information is uncertain
- **Source attribution**: Maintain traceable references

## Search Strategies

### Breadth-First

Execute multiple search queries in parallel, then synthesize.

**Best for:** Broad research questions, diverse perspectives
**Risk:** Information overload, conflicting results

### Depth-First

Follow one promising result deeply before exploring others.

**Best for:** Specific technical questions, verification
**Risk:** Missing alternative perspectives

### Iterative Refinement

Use initial results to generate better follow-up queries.

**Best for:** Exploration, complex multi-faceted questions
**Risk:** Higher latency, higher API cost

## Integration with RAG and Model Knowledge

### Source Status Protocol

Each source provides:
```python
@dataclass
class SourceResult:
    source_type: str  # "web" | "rag" | "model"
    status: str       # "success" | "failed" | "fallback"
    content: str
    evidence_refs: list[str]
    confidence: float
    limitations: list[str]
    latency_ms: int
```

### When to Prefer Web over RAG

- Policy changes in the last 6 months
- Current events and news
- Product prices and availability
- Recent research publications (not yet in RAG index)
- Regulatory updates (new laws, standards)
- Any topic where the RAG index may be stale

### When to Prefer RAG over Web

- Internal/proprietary documentation
- Audited and verified knowledge
- Domain-specific controlled vocabulary
- Topics requiring precise technical definitions
- Information that changes rarely (e.g., GIS fundamentals)

### When to Prefer Model over Both

- General knowledge with broad consensus
- Definitions and explanations of well-established concepts
- Tasks requiring reasoning rather than fact lookup
- When both Web and RAG fail

## Risk Management

### Common Failure Modes

1. **SEO spam**: Low-quality content optimized for search engines
2. **Outdated information**: Old pages ranking high
3. **Misinformation**: Deliberately false or misleading content
4. **Source bias**: Results skewed by search engine algorithms
5. **Content farms**: AI-generated low-quality content

### Mitigation Strategies

- **Authority whitelist**: Prefer trusted domains
- **Cross-validation**: Require multiple independent sources
- **Date filtering**: Limit to recent results when timeliness matters
- **Confidence thresholds**: Flag low-confidence results for human review
- **Source diversity**: Require multiple distinct domains

## Performance Considerations

- **Latency budget**: Web search often dominates end-to-end latency
- **Parallel vs. sequential**: Parallel search reduces latency, increases cost
- **Caching**: Cache search results for repeated/rephrased queries
- **Timeout handling**: Graceful degradation when search fails
