# Example Report: Web Failed, RAG + Model Succeeded

- Scenario: Web search times out, while RAG and Model return usable results.
- Query: How should Loop Engineering be represented in a research-agent workflow?
- Run mode: offline illustrative sample.

## Final Report

### Final Conclusions

- Loop Engineering needs explicit retrieval and verification loops. [RAG][Model]
- Failed Web output is visible in source status, but it is excluded from evidence nodes and consensus votes.
- The report should state uncertainty for freshness-sensitive claims because Web failed.

### Source Status

| Source | Status | Detail | Note |
|---|---|---|---|
| RAG | success | local Chroma hybrid retrieval | local docs support loop design |
| Web | failed | duckduckgo | timeout |
| Model | success | LLM world knowledge | model inference labeled |

### Evidence Summary

- Consensus: RAG and Model agree on explicit stop conditions and verification loops.
- Excluded source: Web failed and cannot support factual claims.
- Uncertainty: current web examples and latest tooling may be incomplete.

## FactCheck

- Deterministic traceability check: passed.
- Failed/fallback leakage: none.

## Run Summary

- checkpoint_backend: none
- trace: examples/web_failed_rag_model_success.trace.jsonl
- acceptance: passed
