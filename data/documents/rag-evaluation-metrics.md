# RAG Evaluation Metrics and Methodology

## Introduction

Evaluating Retrieval-Augmented Generation (RAG) systems requires measuring
both the retrieval component and the generation component, as well as the
interaction between them.

## Retrieval Metrics

### Recall@k

The proportion of relevant documents retrieved in the top-k results:

```
Recall@k = |{relevant docs} ∩ {top-k results}| / |{relevant docs}|
```

High recall is critical: if relevant documents aren't retrieved, the generator
cannot use them.

### Precision@k

The proportion of top-k results that are relevant:

```
Precision@k = |{relevant docs} ∩ {top-k results}| / k
```

High precision means fewer irrelevant chunks consuming context window space.

### Mean Reciprocal Rank (MRR)

The average of the reciprocal ranks of the first relevant result:

```
MRR = (1/|Q|) × Σ (1 / rank_i)
```

Where rank_i is the position of the first relevant document for query i.
MRR penalizes systems that bury the first relevant result deep in the results.

### Hit Rate

The fraction of queries where at least one relevant document appears in the
top-k results:

```
HitRate@k = |{q: |relevant(q) ∩ top-k(q)| > 0}| / |Q|
```

### Normalized Discounted Cumulative Gain (NDCG@k)

Considers both relevance and position, with position discounts:

```
DCG@k = Σ (rel_i / log2(i+1)) for i=1 to k
NDCG@k = DCG@k / IDCG@k
```

Where IDCG is the ideal DCG (perfect ranking).

## Generation Metrics

### Faithfulness

Measures whether the generated answer is supported by the retrieved context.

Approaches:
- **Natural Language Inference (NLI)**: Classify each claim as entailed/
  contradicted/neutral given the context
- **Fact-checking models**: Verify claims against retrieved evidence
- **LLM-as-judge**: Use a separate LLM to evaluate faithfulness

### Answer Relevance

How well the generated answer addresses the query.

Often measured via:
- Semantic similarity between query and answer
- LLM-based scoring
- Human evaluation

### Context Relevance

How much of the retrieved context is actually used in the answer.

Metrics:
- **Context utilization rate**: Tokens from context appearing in answer
- **Attribution score**: Proportion of claims with proper citations

## End-to-End Metrics

### Exact Match (EM)

The generated answer exactly matches one of the ground-truth answers.

### F1 Score

Token-level overlap between generated and ground-truth answers.

### BERTScore

Semantic similarity using BERT embeddings — more robust than n-gram overlap.

### RAGAS Framework

RAGAS (RAG Assessment) provides a structured evaluation:

1. **Faithfulness**: Is the answer grounded in the context?
2. **Answer Relevancy**: Does the answer address the query?
3. **Context Recall**: How much relevant context was retrieved?
4. **Context Precision**: How much retrieved context is relevant?
5. **Answer Correctness**: Factual accuracy compared to ground truth

## Evaluation Dataset Design

### Golden Dataset Structure

Each entry should include:
```yaml
- id: unique identifier
  query: user question
  expected_sources: [RAG, Web, Model]  # expected source types
  min_confidence: high | medium | low
  key_facts:
    - fact that must appear in answer
    - another required fact
  ground_truth: optional reference answer
  relevant_doc_ids: ids of documents that should be retrieved
```

### Test Categories

Good evaluation datasets cover:

1. **Source isolation**: Queries answerable from a single source
2. **Source combination**: Queries requiring multiple sources
3. **Source conflict**: Queries where sources disagree
4. **Knowledge cutoff**: Queries requiring recent information
5. **Ambiguity**: Queries with multiple valid interpretations
6. **Unanswerable**: Queries that no source can answer

### Difficulty Levels

| Level | Description | Example |
|-------|-------------|---------|
| Easy | Single-source, direct match | "What is ML-KEM?" |
| Medium | Multi-source, requires synthesis | "Compare EU and China AI regulation" |
| Hard | Ambiguous, requires reasoning | "When should Web override RAG?" |

## Offline vs Online Evaluation

### Offline Evaluation

- Uses pre-built golden dataset
- Fast, reproducible, deterministic
- Good for regression testing
- Cannot measure real-time web search quality

### Online Evaluation

- Uses real API calls
- Measures end-to-end performance
- Includes real web results
- Higher cost and latency

## Common Pitfalls

1. **Memorization overlap**: Test queries too similar to training data
2. **Dataset contamination**: Evaluation data leaked into training
3. **Metric gaming**: Optimizing for metric without improving real quality
4. **Insufficient diversity**: Test set doesn't cover failure modes
5. **No negative examples**: All queries answerable, no robustness test
