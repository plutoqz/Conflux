# Model Knowledge Reliability in Research Systems

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
