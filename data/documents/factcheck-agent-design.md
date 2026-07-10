# FactCheck Agent Design for Multi-Agent Research Systems

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
