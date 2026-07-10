# Example Report: RAG and Web Conflict

- Scenario: RAG contains an older standard description, while Web points to a newer version.
- Query: How should Conflux arbitrate conflicting local and web evidence?
- Run mode: offline illustrative sample.

## Final Report

### Final Conclusions

- RAG and Web conflicts should be marked as contested rather than collapsed into a single confident claim.
- If the claim is time-sensitive, Web freshness receives priority only when the Web source succeeds and has a verifiable URL.
- Model knowledge cannot overrule external evidence; it can explain tradeoffs and uncertainty.
- If arbitration remains unresolved, the report marks `awaiting_user_review`.

### Source Status

| Source | Status | Detail | Note |
|---|---|---|---|
| RAG | success | local Chroma hybrid retrieval | older local document retrieved |
| Web | success | duckduckgo | newer URL snippet retrieved |
| Model | success | LLM world knowledge | model inference labeled |

### Evidence Summary

- Conflict claim: RAG says the standard is at version N; Web says version N+1.
- Arbitration rule: compare timestamps, prefer successful external freshness for current standards, and retain the older RAG claim as historical context.
- Human review hook: required if source dates or authority cannot be determined.

## FactCheck

- Deterministic traceability check: passed with contested evidence.
- Failed/fallback leakage: none.

## Run Summary

- checkpoint_backend: memory
- trace: examples/rag_web_conflict.trace.jsonl
- acceptance: passed
