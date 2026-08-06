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
REVIEW_VIEW_PERMISSION = "decision.review.view"
REVIEW_ASSIGN_PERMISSION = "decision.review.assign"
REVIEW_PERFORM_PERMISSION = "decision.review.perform"
REVIEW_MANAGE_PERMISSION = "decision.review.manage"
APPROVE_PERMISSION = "decision.approve"
CONDITIONALLY_APPROVE_PERMISSION = "decision.conditionally_approve"
REJECT_PERMISSION = "decision.reject"
RETURN_PERMISSION = "decision.return_for_changes"
OUTCOME_VIEW_PERMISSION = "decision.outcome.view"
OUTCOME_DEFINE_PERMISSION = "decision.outcome.define"
OUTCOME_RECORD_PERMISSION = "decision.outcome.record"
OUTCOME_VERIFY_PERMISSION = "decision.outcome.verify"
OUTCOME_ASSESS_PERMISSION = "decision.outcome.assess"
LESSON_RECORD_PERMISSION = "decision.lesson.record"


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


def authorize_review_view(permissions: set[str]) -> None:
    require_permission(permissions, REVIEW_VIEW_PERMISSION)


def authorize_review_assign(permissions: set[str]) -> None:
    require_permission(permissions, REVIEW_ASSIGN_PERMISSION)


def authorize_review_perform(permissions: set[str]) -> None:
    require_permission(permissions, REVIEW_PERFORM_PERMISSION)


def authorize_review_manage(permissions: set[str]) -> None:
    require_permission(permissions, REVIEW_MANAGE_PERMISSION)


def authorize_approval(permissions: set[str], action: str) -> None:
    permission = {
        "approved": APPROVE_PERMISSION,
        "conditionally_approved": CONDITIONALLY_APPROVE_PERMISSION,
        "rejected": REJECT_PERMISSION,
        "returned_for_changes": RETURN_PERMISSION,
    }[action]
    require_permission(permissions, permission)


def authorize_assigned_reviewer(
    *, permissions: set[str], actor_id: str, reviewer_id: str
) -> None:
    if actor_id == reviewer_id:
        authorize_review_perform(permissions)
    else:
        authorize_review_manage(permissions)


def authorize_outcome(permissions: set[str], action: str) -> None:
    permission = {
        "view": OUTCOME_VIEW_PERMISSION,
        "define": OUTCOME_DEFINE_PERMISSION,
        "record": OUTCOME_RECORD_PERMISSION,
        "verify": OUTCOME_VERIFY_PERMISSION,
        "assess": OUTCOME_ASSESS_PERMISSION,
        "lesson": LESSON_RECORD_PERMISSION,
    }[action]
    require_permission(permissions, permission)
