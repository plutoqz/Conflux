<!-- source: synthetic -->
# Retrieval-Augmented Generation: A Technical Deep Dive

> Source: Synthetic document for RAG evaluation
> Topics: RAG architecture, chunking, retrieval, fusion

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that enhances LLM outputs
by retrieving relevant information from an external knowledge base before
generating a response. First introduced by Lewis et al. (2020), RAG addresses
key LLM limitations: knowledge cutoff, hallucination, and lack of source
attribution.

## Architecture

### 1. Document Ingestion

Raw documents go through a preprocessing pipeline:
1. **Parsing**: Extract text from PDF, HTML, Markdown, etc.
2. **Chunking**: Split into manageable segments
3. **Embedding**: Convert chunks to dense vectors
4. **Indexing**: Store vectors in a vector database

### 2. Retrieval

When a query arrives:
1. **Query embedding**: Convert the query to a vector
2. **Similarity search**: Find nearest chunks in vector space
3. **Reranking** (optional): Reorder results with a cross-encoder

### 3. Generation

The retrieved chunks are inserted into the prompt as context:
```
Answer the question based on the following context:

[Context from retrieved chunks]

Question: {user query}
Answer:
```

## Chunking Strategies

### Fixed-Size Chunking

Split text into fixed-size segments with optional overlap.

**Pros:** Simple, predictable
**Cons:** May split in the middle of sentences or semantic units

### Semantic Chunking

Split at natural boundaries (paragraphs, sections).

**Pros:** Maintains semantic coherence
**Cons:** Inconsistent chunk sizes

### Parent-Child Chunking (Conflux Approach)

Two-level hierarchy:
- **L1 Parent (1024 chars)**: Larger chunks for context
- **L2 Child (256 chars)**: Smaller chunks for precise retrieval

During retrieval, child chunks are matched, then their parent context is
included for richer generation.

### Sentence Window

Retrieve a sentence, expand to include surrounding sentences.

## Retrieval Methods

### Dense Retrieval (Vector Similarity)

Uses embedding models (e.g., text-embedding-3-small) to encode both documents
and queries into the same vector space. Retrieval is by cosine similarity or
Euclidean distance.

**Strengths:** Captures semantic meaning, handles paraphrasing
**Weaknesses:** May miss exact keyword matches, embedding model quality matters

### Sparse Retrieval (BM25)

Statistical method based on term frequency and inverse document frequency.
No embeddings required.

**Strengths:** Good for exact keyword matching, interpretable
**Weaknesses:** Misses semantic equivalences (synonyms)

### Hybrid Retrieval

Combines dense and sparse scores, typically with Reciprocal Rank Fusion (RRF):

```
RRF_score(d) = Σ (1 / (k + rank_i(d)))
```

Where k is a constant (typically 60) and rank_i is the document's rank in
retrieval method i.

Conflux uses a weighted variant:
```
score = dense_weight × dense_score + bm25_weight × bm25_score
```

## Evaluation Metrics

| Metric | Description |
|--------|------------|
| Recall@k | Fraction of relevant docs in top-k results |
| Hit Rate | Fraction of queries with ≥1 relevant result in top-k |
| MRR | Mean reciprocal rank of the first relevant result |
| NDCG@k | Normalized discounted cumulative gain |

## Common Challenges

1. **Irrelevant retrieval**: Retrieved chunks don't answer the question
2. **Context overflow**: Too many/large chunks exceed model context window
3. **Stale index**: Knowledge base not updated with new information
4. **Low-quality chunking**: Chunks break semantic units
5. **Embedding mismatch**: Query and document embeddings not well aligned
