from __future__ import annotations

from dataclasses import dataclass


VIEW_PERMISSION = "decision.view"
CREATE_PERMISSION = "decision.create"
EDIT_PERMISSION = "decision.edit"
TRANSITION_PERMISSION = "decision.transition"


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
