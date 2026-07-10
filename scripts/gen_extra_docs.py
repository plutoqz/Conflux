"""Generate a few more synthetic docs for knowledge base diversity."""
from pathlib import Path

OUTPUT = Path("data/documents")

docs = {
    "factcheck-agent-design.md": """# FactCheck Agent Design for Multi-Agent Research Systems

## Purpose

The FactCheck agent is an independent verification component within a multi-agent
research pipeline. Its primary responsibility is to audit the final report for
factual accuracy before human review or publication.

## Architecture

### Position in Pipeline

The FactCheck agent operates AFTER synthesis but BEFORE human review. It can
trigger a revision loop if significant issues are found.

Pipeline: RAG/Web/Model Agents -> Evidence Merge -> Claim Arbitration ->
Synthesize Report -> FactCheck -> Human Review -> Final Output

## Verification Protocol

### Step 1: Claim Extraction

Parse the synthesized report to extract discrete factual claims:
- Each sentence or clause that asserts a fact
- Statistics, dates, names, technical specifications
- Causal or comparative statements

### Step 2: Source Tracing

For each claim, trace back to the original evidence:
- Which agent produced this information?
- What source(s) did that agent cite?
- Is the source still accessible and unmodified?

### Step 3: Cross-Validation

Check claims against all available sources:
- Does RAG content support this claim?
- Do web search results confirm it?
- Does model knowledge align?

### Step 4: Leakage Detection

Identify claims that appear in the report but cannot be traced to any source:
- Hallucination: Claim fabricated by the model
- Failed-source leakage: Claim from a source that was marked as failed
- Prompt-injection contamination: Claim influenced by injected content

### Step 5: Confidence Scoring

Assign confidence to each claim:
- Verified: Supported by 2+ independent sources
- Likely: Supported by 1 source, not contradicted
- Uncertain: Insufficient evidence
- Contested: Sources disagree
- Unverifiable: No source available

## Revision Triggers

FactCheck can trigger automatic revision when:
1. Any claim is marked as Contested or Hallucination
2. Overall report confidence falls below threshold
3. Failed-source content is detected in claims
4. Key expected facts from golden dataset are missing

## Implementation Considerations

### Deterministic vs. LLM-based Checking

Deterministic checks cover source tracing, failed-source leakage detection,
and prompt-injection pattern matching. LLM-based checks handle semantic
entailment verification, fact consistency across sources, and claim
decomposition. Deterministic checks run in milliseconds; LLM checks are
parallelized where possible.

### False Positives

Not all unverifiable claims are hallucinations. Some represent legitimate
model knowledge. Confidence thresholds should be configurable and human
review remains the final arbiter.
""",

    "evidence-graph-format.md": """# Evidence Graph Format Specification

## Overview

An Evidence Graph is a structured representation of the relationships between
claims, sources, and evidence in a multi-agent research system. It enables
transparent traceability from conclusions back to their evidential basis.

## Graph Schema

### Node Types

| Type | Description | Properties |
|------|-------------|------------|
| Claim | A factual assertion | text, confidence, status |
| Source | An origin of information | type (rag/web/model), status, url/path |
| Evidence | A specific piece of supporting material | chunk_id, excerpt, relevance_score |
| Agent | The agent that produced a claim | agent_type, run_id |

### Edge Types

| Type | Description | Properties |
|------|-------------|------------|
| SUPPORTS | Evidence supports a claim | strength (strong/moderate/weak) |
| CONTRADICTS | Evidence contradicts a claim | conflict_type |
| PRODUCED | Agent produced a claim | timestamp |
| DERIVED_FROM | Claim derived from source | transformation |
| CITES | Claim cites specific evidence | citation_format |

## Example

A claim like "NIST released PQC standards in August 2024" would be represented
as a Claim node, connected via DERIVED_FROM edge to a Source node (web search
from csrc.nist.gov), with a SUPPORTS edge from an Evidence node containing the
relevant chunk from nist--nist-pqc-overview.md.

## Failure Handling

### Failed Sources
- Failed sources do not become nodes in the evidence graph
- Claims exclusively from failed sources are flagged
- Failed source content appearing in accepted claims indicates leakage

### Contradictory Evidence
- Marked with CONTRADICTS edges
- Triggers conflict resolution protocol
- May result in contested claim status

### Missing Evidence
- Claims without SUPPORTS edges after verification are suspect
- May indicate hallucination or model-only knowledge
- Should be explicitly labeled as model knowledge

## Visualization

The evidence graph can be rendered as:
- Interactive D3.js force-directed graph in HTML reports
- Mermaid diagrams in Markdown reports
- NetworkX graphs for programmatic analysis
""",

    "model-knowledge-reliability.md": """# Model Knowledge Reliability in Research Systems

## Definition

Model knowledge refers to information that a language model produces from its
training data, without retrieving from external sources. In a multi-agent
research system, this is one of three knowledge sources (alongside RAG and Web).

## Characteristics

### Strengths
- Speed: No retrieval latency
- Coverage: Massive breadth from training on diverse corpora
- Synthesis: Can combine concepts across domains
- Reasoning: Can perform multi-step logical inference

### Weaknesses
- Knowledge cutoff: Training data has a fixed end date
- Hallucination: May generate plausible but incorrect information
- No source attribution: Cannot cite specific documents
- Confidence miscalibration: May express high confidence for incorrect facts
- Bias: Reflects biases present in training data
- Recency blind spot: Completely unaware of events after training cutoff

## When to Trust Model Knowledge

### High Confidence Scenarios
- Well-established scientific facts
- Widely known historical events
- Common technical definitions in mature fields
- Mathematical and logical relationships
- Widely agreed-upon best practices

### Low Confidence Scenarios
- Recent events (within 6 months of training cutoff)
- Rapidly changing fields (AI regulation, crypto standards)
- Specific numerical data (population, prices, statistics)
- Organization-specific details (APIs, policies, internal procedures)
- Geopolitical assessments
- Niche technical specifications

## Hybrid Approaches

### Confidence-Weighted Voting

When sources disagree, weight by source reliability. Model weight should be
lower for recent topics, specific data points, and contested topics.

### Uncertainty Communication

Model-generated content must be clearly labeled with the training cutoff date
and a note that the information has not been verified against external sources.
Use confidence qualifiers like likely, possibly, and may be.

### Fallback Role

Model knowledge serves as fallback when RAG returns no relevant documents or
Web search fails. It also handles reasoning over retrieved facts.

## Evaluation

### Hallucination Detection

Check model claims against retrieved documents, web search results, and known
facts from the golden dataset.

### Leakage Prevention

Model output must never be presented as verified fact without qualification,
masquerade as retrieved evidence, or override higher-confidence sources without
explicit justification.
""",
}

for name, content in docs.items():
    (OUTPUT / name).write_text(content, encoding="utf-8")
    print(f"  [OK] {name} ({len(content)/1024:.1f} KB)")

print(f"Done. Total files: {len(list(OUTPUT.glob('*')))}")
