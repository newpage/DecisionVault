from __future__ import annotations

from dataclasses import dataclass


VIEW_PERMISSION = "decision.view"
CREATE_PERMISSION = "decision.create"
EDIT_PERMISSION = "decision.edit"
TRANSITION_PERMISSION = "decision.transition"
EVIDENCE_VIEW_PERMISSION = "decision.evidence.view"
EVIDENCE_SELECT_PERMISSION = "decision.evidence.select"
EVIDENCE_REMOVE_PERMISSION = "decision.evidence.remove"
EVIDENCE_HISTORY_PERMISSION = "decision.evidence.history"


@dataclass(frozen=True)
class DecisionPermissionError(PermissionError):
    permission: str

    def __str__(self) -> str:
        return f"{self.permission} permission required"


def require_permission(permissions: set[str], permission: str) -> None:
    if permission not in permissions:
        raise DecisionPermissionError(permission)


def authorize_view(permissions: set[str]) -> None:
    require_permission(permissions, VIEW_PERMISSION)


def authorize_create(permissions: set[str]) -> None:
    require_permission(permissions, CREATE_PERMISSION)


def authorize_edit(permissions: set[str]) -> None:
    require_permission(permissions, EDIT_PERMISSION)


def authorize_transition(permissions: set[str]) -> None:
    require_permission(permissions, TRANSITION_PERMISSION)


def authorize_evidence_view(permissions: set[str]) -> None:
    require_permission(permissions, EVIDENCE_VIEW_PERMISSION)


def authorize_evidence_select(permissions: set[str]) -> None:
    require_permission(permissions, EVIDENCE_SELECT_PERMISSION)


def authorize_evidence_remove(permissions: set[str]) -> None:
    require_permission(permissions, EVIDENCE_REMOVE_PERMISSION)


def authorize_evidence_history(permissions: set[str]) -> None:
    require_permission(permissions, EVIDENCE_HISTORY_PERMISSION)
