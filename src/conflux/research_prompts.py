"""Prompt templates for the isolated V3 research model modes."""

INDEPENDENT_ANALYSIS_SYSTEM = (
    "You are Conflux's independent research analyst. "
    "Use only the original research question and task constraints. "
    "Do not invent citations, evidence IDs, or external source claims. "
    "Return valid JSON only."
)

INDEPENDENT_ANALYSIS_PROMPT = """Analyze the original research request without reading retrieval results.

Original research question:
{query}

Return JSON:
{{
  "summary": "...",
  "hypotheses": ["..."],
  "uncertainties": ["..."],
  "critical_aspects": ["..."]
}}
"""

ARBITRATION_SYSTEM = (
    "You are Conflux's evidence arbitration analyst. "
    "Read only the immutable Ledger snapshot and the listed subquestions. "
    "You may propose a bounded RAG or Web correction, but you cannot create, "
    "modify, or cite evidence records. Return valid JSON only."
)

ARBITRATION_PROMPT = """Inspect the evidence snapshot for the research subquestions.

Subquestions:
{subquestions_json}

Immutable Ledger snapshot:
{snapshot_json}

For each material gap or conflict, propose at most one focused correction action.
Only use triggers: no_evidence, low_relevance, conflict, critical_claim_uncovered.
Return JSON:
{{
  "judgments": [
    {{"subquestion_id": "...", "verdict": "covered|gap|conflict|uncertain", "reason": "...", "confidence": 0.0}}
  ],
  "action_proposals": [
    {{"subquestion_id": "...", "source": "RAG|Web", "query": "...", "trigger": "..."}}
  ]
}}
"""

VERIFICATION_SYSTEM = (
    "You are Conflux's independent evidence verifier. "
    "Read only the final immutable Ledger snapshot and the supplied atomic claims. "
    "Do not use parametric knowledge, create evidence IDs, or rewrite the claims. "
    "Return valid JSON only."
)

VERIFICATION_PROMPT = """Verify the supplied atomic claims against the final evidence snapshot.

Atomic claims:
{claims_json}

Final immutable Ledger snapshot:
{snapshot_json}

Use only these verdicts: supports, contradicts, insufficient, uncertain.
Return JSON:
{{
  "checks": [
    {{"claim": "...", "verdict": "supports|contradicts|insufficient|uncertain", "evidence_ids": [], "reason": "...", "confidence": 0.0}}
  ]
}}
"""

CLAIM_GENERATION_SYSTEM = (
    "You are Conflux's structured research claim generator. "
    "Read only the research question and the listed evidence records. "
    "Return valid JSON only. Every claim must be atomic and independently verifiable. "
    "Never create evidence IDs or citation references that are not listed."
)

CLAIM_GENERATION_PROMPT = """Generate atomic claims for one research subquestion.

Research question:
{core_question}

Subquestion:
{sub_question}

Allowed evidence records:
{evidence_json}

Rules:
- Use claim_type direct_fact for one-source factual claims.
- Use claim_type multi_source_fact only when the claim needs at least two independent source identities.
- Use claim_type derived_analysis when the claim is derived from listed evidence or claims.
- Use claim_type model_analysis only for explicitly marked analysis that does not pretend to be externally supported.
- importance must be critical, high, medium, or low. Numbers, dates, causal claims, comparisons, negations, scope limits, and high-risk conclusions are critical.
- evidence_ids may contain only IDs from the allowed evidence records.
- derivation_inputs must contain the evidence IDs or claim IDs used by derived_analysis.
- citation_refs may contain only the citation references attached to the allowed evidence records.
- Do not write a report body. Keep each claim self-contained and concise.

Return JSON:
{{
  "claims": [
    {{
      "text": "...",
      "claim_type": "direct_fact|multi_source_fact|derived_analysis|model_analysis",
      "importance": "critical|high|medium|low",
      "evidence_ids": ["..."],
      "derivation_type": "direct_evidence|multi_source_synthesis|claim_derivation|model_analysis",
      "derivation_inputs": ["..."],
      "citation_refs": ["[1]"]
    }}
  ],
  "summary": "...",
  "analysis_judgments": ["..."],
  "evidence_gaps": ["..."]
}}
"""

CLAIM_GENERATION_NO_EVIDENCE_PROMPT = """Generate atomic analysis claims for one research subquestion.

Research question:
{core_question}

Subquestion:
{sub_question}

No external evidence is available for this subquestion. Return only explicitly marked model_analysis claims.
Do not invent evidence IDs or citation references. Keep each claim self-contained and state important uncertainty as an evidence gap.

Return JSON:
{{
  "claims": [
    {{
      "text": "...",
      "claim_type": "model_analysis",
      "importance": "critical|high|medium|low",
      "evidence_ids": [],
      "derivation_type": "model_analysis",
      "derivation_inputs": [],
      "citation_refs": []
    }}
  ],
  "summary": "...",
  "analysis_judgments": ["..."],
  "evidence_gaps": ["..." ]
}}
"""

CLAIM_SYNTHESIS_SYSTEM = (
    "You are Conflux's claim selector. Select only existing claim IDs for the report overview. "
    "Do not introduce new factual content. Return valid JSON only."
)

CLAIM_SYNTHESIS_PROMPT = """Select existing atomic claims for the report overview.

Research question:
{core_question}

Available claims:
{claims_json}

Return JSON:
{{
  "direct_claim_ids": ["claim-id"],
  "cross_synthesis_claim_ids": ["claim-id"]
}}
"""
