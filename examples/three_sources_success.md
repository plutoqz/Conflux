# Example Report: Three Sources Succeeded

- Scenario: RAG, Web, and Model all return `success`.
- Query: How should a multi-agent RAG system arbitrate local, web, and model evidence?
- Run mode: offline illustrative sample.

## Final Report

### Final Conclusions

- RAG should provide controlled local knowledge with chunk-level citations such as `[RAG:multi-agent-rag-arbitration.md#chunk-p0-c0]`.
- Web should be used for freshness-sensitive claims and URL-backed evidence.
- Model knowledge should support reasoning and synthesis, but must be labeled as inference rather than external evidence.
- Consensus requires at least two successful sources; single-source claims are shown with lower confidence.

### Source Status

| Source | Status | Detail | Note |
|---|---|---|---|
| RAG | success | local Chroma hybrid retrieval | 3 chunks retrieved |
| Web | success | duckduckgo | 3 URL snippets returned |
| Model | success | LLM world knowledge | model inference labeled |

### Evidence Summary

- Multi-source consensus: source status and evidence graph are required reliability controls.
- Single-source claim: Web freshness may be preferred for new standards.
- Conflict: none in this sample.

## FactCheck

- Deterministic traceability check: passed.
- Failed/fallback leakage: none.

## Run Summary

- checkpoint_backend: memory
- trace: examples/three_sources_success.trace.jsonl
- acceptance: passed
