import pytest

from app.modules.decisions.lifecycle import (
    InvalidTransitionError,
    allowed_transitions,
    validate_transition,
)


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        ("draft", "evidence_collection"),
        ("evidence_collection", "in_review"),
        ("in_review", "approved"),
        ("in_review", "conditionally_approved"),
        ("in_review", "rejected"),
        ("approved", "closed"),
    ],
)
def test_allowed_transitions(current, requested):
    validate_transition(current=current, requested=requested)


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        ("evidence_collection", "approved"),
        ("closed", "in_review"),
        ("approved", "evidence_collection"),
        ("in_review", "in_review"),
        ("draft", "invented"),
    ],
)
def test_forbidden_same_state_and_invalid_transitions(current, requested):
    with pytest.raises(InvalidTransitionError):
        validate_transition(current=current, requested=requested)


def test_allowed_transitions_exposes_only_next_states():
    assert allowed_transitions("evidence_collection") == []
