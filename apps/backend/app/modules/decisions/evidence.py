from __future__ import annotations

from dataclasses import dataclass

from app.models import DecisionEvidence


RELATIONSHIP_TYPES = frozenset(
    {"supporting", "opposing", "contextual", "risk", "constraint"}
)


class EvidenceValidationError(ValueError):
    """Raised when an evidence domain value is invalid."""


def validate_relationship_type(value: str) -> None:
    if value not in RELATIONSHIP_TYPES:
        raise EvidenceValidationError("Invalid evidence relationship type")


def require_rationale(value: str, *, action: str) -> str:
    rationale = value.strip()
    if len(rationale) < 3:
        raise EvidenceValidationError(
            f"Evidence {action} rationale is required"
        )
    return rationale


@dataclass(frozen=True)
class SnapshotScoringInput:
    approval_status: str
    trust_score: float
    ai_usage_allowed: bool


def scoring_inputs(
    snapshots: list[DecisionEvidence],
) -> list[SnapshotScoringInput]:
    return [
        SnapshotScoringInput(
            approval_status=item.snapshot_approval_status,
            trust_score=item.snapshot_trust_score,
            ai_usage_allowed=item.snapshot_ai_usage_allowed,
        )
        for item in snapshots
    ]
