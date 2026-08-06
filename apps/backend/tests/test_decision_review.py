import pytest

from app.modules.decisions.policies import (
    DecisionPermissionError,
    authorize_assigned_reviewer,
    authorize_approval,
)
from app.modules.decisions.review import (
    ReviewStateError,
    evidence_set_is_current,
    require_text,
    validate_conclusion,
    validate_review_type,
)


def test_review_evidence_freshness_requires_an_exact_snapshot_set():
    assert evidence_set_is_current({"evidence-1"}, {"evidence-1"})
    assert not evidence_set_is_current({"evidence-1"}, {"evidence-1", "evidence-2"})


def test_review_vocabularies_and_rationale_are_controlled():
    validate_review_type("final_approval")
    validate_conclusion("recommend_conditional")
    assert require_text("  governed rationale  ", "Rationale") == "governed rationale"
    with pytest.raises(ReviewStateError):
        validate_review_type("informal")
    with pytest.raises(ReviewStateError):
        validate_conclusion("looks_good")
    with pytest.raises(ReviewStateError):
        require_text(" ", "Rationale")


def test_assigned_reviewer_and_decision_authority_are_separate_permissions():
    authorize_assigned_reviewer(
        permissions={"decision.review.perform"},
        actor_id="reviewer-1",
        reviewer_id="reviewer-1",
    )
    with pytest.raises(DecisionPermissionError):
        authorize_assigned_reviewer(
            permissions={"decision.review.perform"},
            actor_id="reviewer-2",
            reviewer_id="reviewer-1",
        )
    with pytest.raises(DecisionPermissionError):
        authorize_approval({"decision.review.perform"}, "approved")
