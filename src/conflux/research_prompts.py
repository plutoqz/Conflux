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
