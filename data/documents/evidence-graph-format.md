# Evidence Graph Format Specification

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
