<!-- source: synthetic -->
# Multi-Agent System Architectures for Research

> Source: Synthetic document for RAG evaluation
> Topics: AI agents, orchestration, LangGraph, AutoGen

## Overview

Multi-agent systems (MAS) consist of multiple interacting intelligent agents.
In the context of large language models (LLMs), each agent typically has access
to a language model plus a set of tools (search, code execution, APIs).

## Common Patterns

### Fan-out / Fan-in

A coordinator dispatches a query to multiple specialist agents in parallel
(fan-out), collects their responses, and merges the results (fan-in).

**Advantages:**
- Parallel execution reduces latency
- Isolated contexts prevent cross-contamination
- Specialist agents can use different tools/instructions

**Disadvantages:**
- Higher token cost (multiple agents)
- Requires robust result merging

### Sequential Pipeline

Agents execute in sequence: the output of Agent A becomes the input of Agent B.

**Use cases:**
- Retrieve → Verify → Generate
- Research → Draft → Review → Publish

### Debate / Arbitration

Multiple agents independently answer the same question, then compare results.
Disagreements can trigger additional research or human review.

### Hierarchical

A supervisor agent delegates sub-tasks to worker agents and assembles the final
output. Common in frameworks like AutoGen and LangGraph's Supervisor pattern.

## Key Design Decisions

### State Management

How does the system persist and share state between agents?

- **Centralized state** (LangGraph StateGraph): Single source of truth
- **Message passing** (AutoGen): Agents communicate via messages
- **Blackboard**: Shared workspace all agents can read/write

### Tool Access

Which agents get which tools?

- **Equal access**: All agents have the same toolbox
- **Role-based**: Each agent gets tools matching its specialty
- **On-demand**: Tools are dynamically provisioned

### Source Status Protocol

When agents retrieve from different sources (RAG, Web, Model knowledge), each
source result should carry:
- `status`: success | failed | fallback
- `latency_ms`: response time
- `error`: explanation if failed/fallback

Failed sources are excluded from evidence graphs and consensus voting.

## Evaluation Considerations

### Retrieval Quality

- **Recall@k**: Proportion of relevant documents in top-k results
- **Precision@k**: Proportion of top-k results that are relevant
- **MRR (Mean Reciprocal Rank)**: Average of reciprocal ranks of the first relevant result

### Report Quality

- **Factual accuracy**: Claims supported by sources
- **Source coverage**: All expected sources consulted
- **Conflict resolution**: Disagreements properly handled
- **Uncertainty communication**: Limitations stated clearly

### Robustness

- **Failed source handling**: Graceful degradation when a source is unavailable
- **Prompt injection resistance**: Retrieved text treated as data, not instruction
- **Hallucination detection**: Claims traceable to sources
