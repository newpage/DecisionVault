from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_STATUSES = frozenset(
    {
        "draft",
        "evidence_collection",
        "in_review",
        "conditionally_approved",
        "approved",
        "rejected",
        "closed",
    }
)
TERMINAL_STATUSES = frozenset({"closed"})
ALLOWED_TRANSITIONS = {
    "draft": frozenset({"evidence_collection"}),
    "evidence_collection": frozenset({"in_review"}),
    "in_review": frozenset(
        {"conditionally_approved", "approved", "rejected"}
    ),
    "conditionally_approved": frozenset({"approved", "rejected", "closed"}),
    "approved": frozenset({"closed"}),
    "rejected": frozenset({"closed"}),
    "closed": frozenset(),
}


@dataclass(frozen=True)
class InvalidTransitionError(ValueError):
    current: str
    requested: str

    def __str__(self) -> str:
        if self.requested not in SUPPORTED_STATUSES:
            return f"Unsupported decision status: {self.requested}"
        if self.current == self.requested:
            return "A decision cannot transition to its current status"
        return f"Decision cannot transition from {self.current} to {self.requested}"


def validate_transition(*, current: str, requested: str) -> None:
    if (
        requested not in SUPPORTED_STATUSES
        or requested == current
        or requested not in ALLOWED_TRANSITIONS.get(current, frozenset())
    ):
        raise InvalidTransitionError(current=current, requested=requested)


def allowed_transitions(status: str) -> list[str]:
    return sorted(ALLOWED_TRANSITIONS.get(status, frozenset()))
