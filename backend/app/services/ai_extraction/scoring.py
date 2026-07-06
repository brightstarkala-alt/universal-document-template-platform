"""
Confidence scoring — Module 7, Stage E.

A single LLM self-reported confidence is not trusted on its own (poorly
calibrated). The composite blends three signals:

- `heuristic_confidence`: how unambiguous Stage A's regex/layout match was
  (app/services/ai_extraction/candidates.py). 0.5 (neutral) when the LLM
  found a field Stage A had no candidate for at all.
- `llm_confidence`: the model's own reported confidence for this field.
- agreement: whether the heuristic's provisional type and the LLM's final
  type agree — agreement raises confidence, disagreement lowers it, since
  disagreement is itself a signal something is ambiguous.

The result is dampened by the source `Unit.confidence` (Module 6's own
rule-based extraction-quality heuristic, app/schemas/document_model.py) — a
field can't be more trustworthy than the text it was read from.
"""

from app.schemas.ai_extraction import ConfidenceTier

HEURISTIC_WEIGHT = 0.35
LLM_WEIGHT = 0.45
AGREEMENT_WEIGHT = 0.20

_AGREEMENT_BONUS = 1.0
_DISAGREEMENT_PENALTY = 0.0

_HIGH_THRESHOLD = 0.85
_MEDIUM_THRESHOLD = 0.5


def compute_composite_confidence(
    *,
    heuristic_confidence: float,
    llm_confidence: float,
    heuristic_and_llm_agree: bool,
    unit_confidence: float | None = None,
) -> float:
    agreement_score = _AGREEMENT_BONUS if heuristic_and_llm_agree else _DISAGREEMENT_PENALTY
    composite = (
        HEURISTIC_WEIGHT * heuristic_confidence
        + LLM_WEIGHT * llm_confidence
        + AGREEMENT_WEIGHT * agreement_score
    )
    composite = max(0.0, min(1.0, composite))
    if unit_confidence is not None:
        composite *= max(0.0, min(1.0, unit_confidence))
    return composite


def confidence_tier(score: float) -> ConfidenceTier:
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"
