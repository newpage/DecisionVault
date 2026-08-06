from __future__ import annotations

from dataclasses import dataclass


REVIEW_TYPES = frozenset({"business", "risk", "compliance", "final_approval"})
REVIEW_CONCLUSIONS = frozenset(
    {
        "recommend_approve",
        "recommend_conditional",
        "recommend_reject",
        "changes_required",
    }
)
FINDING_TYPES = frozenset(
    {
        "information_request",
        "evidence_gap",
        "risk_concern",
        "policy_concern",
        "control_concern",
        "recommendation",
        "approval_condition",
        "comment",
    }
)
FINDING_STATUSES = frozenset({"open", "addressed", "accepted", "closed", "withdrawn"})


@dataclass(frozen=True)
class ReviewStateError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def require_text(value: str, label: str) -> str:
    normalized = value.strip()
    if len(normalized) < 3:
        raise ReviewStateError(f"{label} is required")
    return normalized


def validate_review_type(value: str) -> None:
    if value not in REVIEW_TYPES:
        raise ReviewStateError("Invalid review type")


def validate_conclusion(value: str) -> None:
    if value not in REVIEW_CONCLUSIONS:
        raise ReviewStateError("Invalid reviewer conclusion")


def validate_finding_type(value: str) -> None:
    if value not in FINDING_TYPES:
        raise ReviewStateError("Invalid finding type")


def validate_finding_resolution(value: str) -> None:
    if value not in FINDING_STATUSES - {"open"}:
        raise ReviewStateError("Invalid finding resolution state")


def evidence_set_is_current(reviewed_ids: set[str], active_ids: set[str]) -> bool:
    return reviewed_ids == active_ids
