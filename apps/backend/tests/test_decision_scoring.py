from types import SimpleNamespace

from app.modules.decisions.scoring import (
    calculate_readiness,
    generate_recommendation,
)


def card(*, approved=True, trusted=True, ai_allowed=True):
    return SimpleNamespace(
        approval_status="approved" if approved else "pending_review",
        trust_score=0.9 if trusted else 0.6,
        ai_usage_allowed=ai_allowed,
    )


def test_readiness_preserves_existing_calculation():
    result = calculate_readiness([card() for _ in range(4)])

    assert result.score == 100
    assert result.status == "ready"
    assert result.approved == 4
    assert result.governed == 4
    assert result.summary["missing_information"] == []


def test_readiness_reports_missing_and_weak_evidence():
    result = calculate_readiness([card(approved=False, trusted=False)])

    assert result.score == 15
    assert result.status == "insufficient_evidence"
    assert len(result.summary["missing_information"]) == 3


def test_recommendation_is_deterministic_and_structured_from_score():
    readiness = calculate_readiness([card()])

    recommendation = generate_recommendation(
        supplier_name="Acme", readiness=readiness
    )

    assert "Acme currently has a readiness score of 85%" in recommendation
    assert "1 approved and 1 trusted" in recommendation
