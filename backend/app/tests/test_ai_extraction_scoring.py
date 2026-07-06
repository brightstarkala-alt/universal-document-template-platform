from app.services.ai_extraction.scoring import compute_composite_confidence, confidence_tier


def test_agreement_raises_confidence_above_disagreement() -> None:
    agree = compute_composite_confidence(
        heuristic_confidence=0.8, llm_confidence=0.8, heuristic_and_llm_agree=True
    )
    disagree = compute_composite_confidence(
        heuristic_confidence=0.8, llm_confidence=0.8, heuristic_and_llm_agree=False
    )
    assert agree > disagree


def test_unit_confidence_dampens_the_composite_score() -> None:
    full_confidence_unit = compute_composite_confidence(
        heuristic_confidence=0.9,
        llm_confidence=0.9,
        heuristic_and_llm_agree=True,
        unit_confidence=1.0,
    )
    low_confidence_unit = compute_composite_confidence(
        heuristic_confidence=0.9,
        llm_confidence=0.9,
        heuristic_and_llm_agree=True,
        unit_confidence=0.4,
    )
    assert low_confidence_unit < full_confidence_unit
    assert low_confidence_unit == full_confidence_unit * 0.4


def test_composite_confidence_is_clamped_to_zero_one() -> None:
    score = compute_composite_confidence(
        heuristic_confidence=1.0, llm_confidence=1.0, heuristic_and_llm_agree=True
    )
    assert 0.0 <= score <= 1.0


def test_confidence_tier_boundaries() -> None:
    assert confidence_tier(0.85) == "high"
    assert confidence_tier(0.84999) == "medium"
    assert confidence_tier(0.5) == "medium"
    assert confidence_tier(0.49999) == "low"
    assert confidence_tier(0.0) == "low"
