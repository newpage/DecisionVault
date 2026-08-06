from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditEvent,
    DecisionApprovalAction,
    DecisionApprovalCondition,
    DecisionCase,
    DecisionReview,
    DecisionReviewEvidence,
    DecisionReviewFinding,
    uid,
)
from app.modules.decisions.lifecycle import (
    validate_approval_action,
    validate_return_for_changes,
    validate_review_submission,
)
from app.modules.decisions.policies import (
    APPROVE_PERMISSION,
    CONDITIONALLY_APPROVE_PERMISSION,
    REJECT_PERMISSION,
    RETURN_PERMISSION,
    REVIEW_ASSIGN_PERMISSION,
    REVIEW_MANAGE_PERMISSION,
    REVIEW_PERFORM_PERMISSION,
    authorize_approval,
    authorize_assigned_reviewer,
    authorize_review_assign,
    authorize_review_manage,
    authorize_review_view,
    authorize_view,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.review import ReviewStateError, require_text
from app.modules.decisions.schemas import (
    ApprovalConditionCreate,
    ApprovalConditionResponse,
    ApprovalMutationResponse,
    ApprovalActionResponse,
    DecisionResponse,
    ReviewFindingResponse,
    ReviewResponse,
    ReviewWorkspaceResponse,
)
from app.modules.decisions.service import DecisionNotFoundError


class DecisionReviewService:
    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def workspace(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        permissions: set[str],
    ) -> ReviewWorkspaceResponse:
        authorize_view(permissions)
        authorize_review_view(permissions)
        self._decision(tenant_id, decision_id)
        reviews = self._repository.list_reviews(
            tenant_id=tenant_id, decision_id=decision_id
        )
        return ReviewWorkspaceResponse(
            reviews=[self._review_response(tenant_id, item) for item in reviews],
            findings=[
                ReviewFindingResponse.model_validate(item)
                for item in self._repository.list_findings(
                    tenant_id=tenant_id, decision_id=decision_id
                )
            ],
            approval_actions=[
                ApprovalActionResponse.model_validate(item)
                for item in self._repository.list_approval_actions(
                    tenant_id=tenant_id, decision_id=decision_id
                )
            ],
            conditions=[
                ApprovalConditionResponse.model_validate(item)
                for item in self._repository.list_conditions(
                    tenant_id=tenant_id, decision_id=decision_id
                )
            ],
            capabilities={
                "assign": REVIEW_ASSIGN_PERMISSION in permissions,
                "manage": REVIEW_MANAGE_PERMISSION in permissions,
                "perform": REVIEW_PERFORM_PERMISSION in permissions,
                "approve": APPROVE_PERMISSION in permissions,
                "conditionally_approve": CONDITIONALLY_APPROVE_PERMISSION
                in permissions,
                "reject": REJECT_PERMISSION in permissions,
                "return_for_changes": RETURN_PERMISSION in permissions,
            },
        )

    def assign(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        permissions: set[str],
        reviewer_id: str,
        review_type: str,
    ) -> ReviewResponse:
        authorize_review_assign(permissions)
        decision = self._locked_decision(tenant_id, decision_id)
        if decision.status not in {"evidence_collection", "in_review"}:
            raise ReviewStateError("Reviews cannot be assigned in this decision state")
        if not self._repository.tenant_has_user(
            tenant_id=tenant_id, user_id=reviewer_id
        ):
            raise DecisionNotFoundError("Reviewer not found")
        now = datetime.now(timezone.utc)
        review = DecisionReview(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            sequence=self._repository.next_review_sequence(
                tenant_id=tenant_id, decision_id=decision.id
            ),
            review_type=review_type,
            assigned_reviewer_id=reviewer_id,
            assigned_by=actor_id,
        )
        objects: list = [review]
        if decision.status == "in_review":
            self._capture_evidence(review, decision, tenant_id, now, objects)
        self._save(
            objects,
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewAssigned",
                    {
                        "review_id": review.id,
                        "review_type": review_type,
                        "reviewer_id": reviewer_id,
                    },
                )
            ],
            [review],
        )
        return self._review_response(tenant_id, review)

    def submit(
        self, *, tenant_id: str, decision_id: str, actor_id: str, permissions: set[str]
    ) -> DecisionResponse:
        authorize_review_manage(permissions)
        decision = self._locked_decision(tenant_id, decision_id)
        validate_review_submission(decision.status)
        evidence = self._repository.list_active_evidence(
            tenant_id=tenant_id, decision_id=decision.id
        )
        if not evidence:
            raise ReviewStateError("At least one active evidence snapshot is required")
        reviews = [
            item
            for item in self._repository.list_reviews(
                tenant_id=tenant_id, decision_id=decision.id
            )
            if item.status == "assigned" and item.submitted_at is None
        ]
        if not reviews or not any(
            item.review_type == "final_approval" for item in reviews
        ):
            raise ReviewStateError("An assigned final approval review is required")
        now = datetime.now(timezone.utc)
        objects: list = [decision]
        for review in reviews:
            self._capture_evidence(review, decision, tenant_id, now, objects, evidence)
        decision.status = "in_review"
        decision.updated_at = now
        self._save(
            objects,
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionSubmittedForReview",
                    {
                        "review_ids": [item.id for item in reviews],
                        "input_revision": decision.input_revision,
                    },
                )
            ],
            [decision],
        )
        return DecisionResponse.model_validate(decision)

    def start(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        review_id: str,
        actor_id: str,
        permissions: set[str],
    ) -> ReviewResponse:
        decision, review = self._review(tenant_id, decision_id, review_id)
        authorize_assigned_reviewer(
            permissions=permissions,
            actor_id=actor_id,
            reviewer_id=review.assigned_reviewer_id,
        )
        if (
            decision.status != "in_review"
            or review.status != "assigned"
            or review.submitted_at is None
        ):
            raise ReviewStateError("Only a submitted assigned review can be started")
        review.status = "in_progress"
        review.started_at = datetime.now(timezone.utc)
        self._save(
            [review],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewStarted",
                    {"review_id": review.id},
                )
            ],
            [review],
        )
        return self._review_response(tenant_id, review)

    def add_finding(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        review_id: str,
        actor_id: str,
        permissions: set[str],
        command,
    ) -> ReviewFindingResponse:
        decision, review = self._review(tenant_id, decision_id, review_id)
        authorize_assigned_reviewer(
            permissions=permissions,
            actor_id=actor_id,
            reviewer_id=review.assigned_reviewer_id,
        )
        if review.status != "in_progress":
            raise ReviewStateError("Findings require an in-progress review")
        if command.related_evidence_id and command.related_evidence_id not in set(
            self._repository.list_review_evidence_ids(
                tenant_id=tenant_id, review_id=review.id
            )
        ):
            raise DecisionNotFoundError("Reviewed evidence not found")
        finding = DecisionReviewFinding(
            id=uid(),
            tenant_id=tenant_id,
            review_id=review.id,
            finding_type=command.finding_type,
            severity=command.severity,
            title=command.title.strip(),
            description=command.description.strip(),
            related_evidence_id=command.related_evidence_id,
            related_section=command.related_section.strip(),
            required_response=command.required_response,
            raised_by=actor_id,
        )
        self._save(
            [finding],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewFindingRaised",
                    {"review_id": review.id, "finding_id": finding.id},
                )
            ],
            [finding],
        )
        return ReviewFindingResponse.model_validate(finding)

    def resolve_finding(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        review_id: str,
        finding_id: str,
        actor_id: str,
        permissions: set[str],
        status: str,
        response: str,
    ) -> ReviewFindingResponse:
        decision, review = self._review(tenant_id, decision_id, review_id)
        authorize_assigned_reviewer(
            permissions=permissions,
            actor_id=actor_id,
            reviewer_id=review.assigned_reviewer_id,
        )
        finding = self._repository.get_finding(
            tenant_id=tenant_id, review_id=review.id, finding_id=finding_id
        )
        if finding is None:
            raise DecisionNotFoundError("Review finding not found")
        if finding.status != "open":
            raise ReviewStateError("Only an open finding can be resolved")
        finding.status = status
        finding.resolution_response = require_text(response, "Resolution response")
        finding.resolved_by = actor_id
        finding.resolved_at = datetime.now(timezone.utc)
        self._save(
            [finding],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewFindingResolved",
                    {
                        "review_id": review.id,
                        "finding_id": finding.id,
                        "status": status,
                    },
                )
            ],
            [finding],
        )
        return ReviewFindingResponse.model_validate(finding)

    def complete(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        review_id: str,
        actor_id: str,
        permissions: set[str],
        conclusion: str,
        summary: str,
    ) -> ReviewResponse:
        decision, review = self._review(tenant_id, decision_id, review_id)
        authorize_assigned_reviewer(
            permissions=permissions,
            actor_id=actor_id,
            reviewer_id=review.assigned_reviewer_id,
        )
        if review.status != "in_progress":
            raise ReviewStateError("Only an in-progress review can be completed")
        active_ids = {
            item.id
            for item in self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision.id
            )
        }
        reviewed_ids = set(
            self._repository.list_review_evidence_ids(
                tenant_id=tenant_id, review_id=review.id
            )
        )
        if (
            review.decision_revision != decision.input_revision
            or reviewed_ids != active_ids
        ):
            review.freshness_status = "stale"
            self._save(
                [review],
                [
                    self._event(
                        decision,
                        actor_id,
                        "DecisionReviewMarkedStale",
                        {"review_id": review.id},
                    )
                ],
            )
            raise ReviewStateError("Review evidence is stale; assign a new review")
        blocking = [
            item
            for item in self._repository.list_findings(
                tenant_id=tenant_id, decision_id=decision.id, review_id=review.id
            )
            if item.required_response
            and item.status not in {"accepted", "closed", "withdrawn"}
        ]
        if blocking:
            raise ReviewStateError(
                "Required findings must be accepted, closed, or withdrawn"
            )
        review.status = "completed"
        review.conclusion = conclusion
        review.summary = require_text(summary, "Review summary")
        review.completed_at = datetime.now(timezone.utc)
        review.freshness_status = "current"
        self._save(
            [review],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewCompleted",
                    {"review_id": review.id, "conclusion": conclusion},
                )
            ],
            [review],
        )
        return self._review_response(tenant_id, review)

    def cancel(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        review_id: str,
        actor_id: str,
        permissions: set[str],
        rationale: str,
    ) -> ReviewResponse:
        authorize_review_manage(permissions)
        decision, review = self._review(tenant_id, decision_id, review_id)
        if review.status not in {"assigned", "in_progress"}:
            raise ReviewStateError("Only an active review can be cancelled")
        review.status = "cancelled"
        review.cancelled_by = actor_id
        review.cancelled_at = datetime.now(timezone.utc)
        review.cancellation_reason = require_text(rationale, "Cancellation rationale")
        self._save(
            [review],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionReviewCancelled",
                    {"review_id": review.id, "rationale": review.cancellation_reason},
                )
            ],
            [review],
        )
        return self._review_response(tenant_id, review)

    def approval(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        permissions: set[str],
        action: str,
        rationale: str,
        conditions: list[ApprovalConditionCreate] | None = None,
    ) -> ApprovalMutationResponse:
        authorize_approval(permissions, action)
        decision = self._locked_decision(tenant_id, decision_id)
        validate_approval_action(decision.status, action)
        final_review = self._approval_preconditions(tenant_id, decision)
        if decision.status == "conditionally_approved":
            open_conditions = [
                item
                for item in self._repository.list_conditions(
                    tenant_id=tenant_id, decision_id=decision.id
                )
                if item.status == "open"
            ]
            if open_conditions:
                raise ReviewStateError(
                    "All approval conditions must be satisfied or waived"
                )
        if action == "conditionally_approved" and not conditions:
            raise ReviewStateError(
                "Conditional approval requires at least one condition"
            )
        rationale = require_text(rationale, "Approval rationale")
        approval = DecisionApprovalAction(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            review_id=final_review.id,
            action=action,
            rationale=rationale,
            actor_id=actor_id,
        )
        objects: list = [decision, approval]
        created_conditions = [
            DecisionApprovalCondition(
                id=uid(),
                tenant_id=tenant_id,
                decision_case_id=decision.id,
                approval_action_id=approval.id,
                condition_text=item.condition_text.strip(),
                responsible_party=item.responsible_party.strip(),
                due_date=item.due_date,
                created_by=actor_id,
            )
            for item in conditions or []
        ]
        objects.extend(created_conditions)
        decision.status = action
        decision.updated_at = datetime.now(timezone.utc)
        try:
            self._save(
                objects,
                [
                    self._event(
                        decision,
                        actor_id,
                        "DecisionApprovalRecorded",
                        {
                            "action_id": approval.id,
                            "review_id": final_review.id,
                            "action": action,
                            "rationale": rationale,
                        },
                    )
                ],
                [decision, approval, *created_conditions],
            )
        except IntegrityError as exc:
            raise ReviewStateError(
                "A conflicting approval action already exists"
            ) from exc
        return ApprovalMutationResponse(
            decision=DecisionResponse.model_validate(decision),
            action=ApprovalActionResponse.model_validate(approval),
            conditions=[
                ApprovalConditionResponse.model_validate(item)
                for item in created_conditions
            ],
        )

    def return_for_changes(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        permissions: set[str],
        rationale: str,
    ) -> ApprovalMutationResponse:
        authorize_approval(permissions, "returned_for_changes")
        decision = self._locked_decision(tenant_id, decision_id)
        validate_return_for_changes(decision.status)
        rationale = require_text(rationale, "Return rationale")
        action = DecisionApprovalAction(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            action="returned_for_changes",
            rationale=rationale,
            actor_id=actor_id,
        )
        decision.status = "evidence_collection"
        decision.input_revision += 1
        decision.updated_at = datetime.now(timezone.utc)
        stale = self._repository.mark_completed_reviews_stale(
            tenant_id=tenant_id, decision_id=decision.id
        )
        events = [
            self._event(
                decision,
                actor_id,
                "DecisionReturnedForChanges",
                {
                    "action_id": action.id,
                    "rationale": rationale,
                    "input_revision": decision.input_revision,
                },
            )
        ]
        events.extend(
            self._event(
                decision, actor_id, "DecisionReviewMarkedStale", {"review_id": item.id}
            )
            for item in stale
        )
        self._save([decision, action, *stale], events, [decision, action])
        return ApprovalMutationResponse(
            decision=DecisionResponse.model_validate(decision),
            action=ApprovalActionResponse.model_validate(action),
        )

    def satisfy_condition(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        condition_id: str,
        actor_id: str,
        permissions: set[str],
        response: str,
    ) -> ApprovalConditionResponse:
        authorize_review_manage(permissions)
        decision = self._decision(tenant_id, decision_id)
        condition = self._repository.get_condition(
            tenant_id=tenant_id, decision_id=decision_id, condition_id=condition_id
        )
        if condition is None:
            raise DecisionNotFoundError("Approval condition not found")
        if condition.status != "open":
            raise ReviewStateError("Approval condition is already resolved")
        condition.status = "satisfied"
        condition.satisfied_by = actor_id
        condition.satisfied_at = datetime.now(timezone.utc)
        condition.satisfaction_response = require_text(
            response, "Satisfaction response"
        )
        self._save(
            [condition],
            [
                self._event(
                    decision,
                    actor_id,
                    "DecisionApprovalConditionSatisfied",
                    {"condition_id": condition.id},
                )
            ],
            [condition],
        )
        return ApprovalConditionResponse.model_validate(condition)

    def _approval_preconditions(
        self, tenant_id: str, decision: DecisionCase
    ) -> DecisionReview:
        active_ids = {
            item.id
            for item in self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision.id
            )
        }
        if not active_ids:
            raise ReviewStateError("Active decision evidence is required")
        reviews = self._repository.list_reviews(
            tenant_id=tenant_id, decision_id=decision.id
        )
        current = [
            item
            for item in reviews
            if item.review_type == "final_approval"
            and item.status == "completed"
            and item.freshness_status == "current"
            and item.decision_revision == decision.input_revision
            and set(
                self._repository.list_review_evidence_ids(
                    tenant_id=tenant_id, review_id=item.id
                )
            )
            == active_ids
        ]
        if not current:
            raise ReviewStateError(
                "A current completed final approval review is required"
            )
        findings = self._repository.list_findings(
            tenant_id=tenant_id, decision_id=decision.id, review_id=current[0].id
        )
        if any(
            item.required_response
            and item.status not in {"accepted", "closed", "withdrawn"}
            for item in findings
        ):
            raise ReviewStateError(
                "Required findings must be accepted, closed, or withdrawn"
            )
        return current[0]

    def _capture_evidence(
        self,
        review: DecisionReview,
        decision: DecisionCase,
        tenant_id: str,
        now: datetime,
        objects: list,
        evidence=None,
    ) -> None:
        evidence = evidence or self._repository.list_active_evidence(
            tenant_id=tenant_id, decision_id=decision.id
        )
        if not evidence:
            raise ReviewStateError("At least one active evidence snapshot is required")
        review.submitted_at = now
        review.decision_revision = decision.input_revision
        review.freshness_status = "pending"
        objects.append(review)
        objects.extend(
            DecisionReviewEvidence(
                tenant_id=tenant_id, review_id=review.id, decision_evidence_id=item.id
            )
            for item in evidence
        )

    def _review(
        self, tenant_id: str, decision_id: str, review_id: str
    ) -> tuple[DecisionCase, DecisionReview]:
        decision = self._decision(tenant_id, decision_id)
        review = self._repository.get_review_for_update(
            tenant_id=tenant_id, decision_id=decision_id, review_id=review_id
        )
        if review is None:
            raise DecisionNotFoundError("Decision review not found")
        return decision, review

    def _decision(self, tenant_id: str, decision_id: str) -> DecisionCase:
        decision = self._repository.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision

    def _locked_decision(self, tenant_id: str, decision_id: str) -> DecisionCase:
        decision = self._repository.get_decision_for_update(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision

    def _review_response(
        self, tenant_id: str, review: DecisionReview
    ) -> ReviewResponse:
        return ReviewResponse.model_validate(
            {
                **review.__dict__,
                "evidence_ids": self._repository.list_review_evidence_ids(
                    tenant_id=tenant_id, review_id=review.id
                ),
            }
        )

    @staticmethod
    def _event(
        decision: DecisionCase, actor_id: str, event_type: str, details: dict
    ) -> AuditEvent:
        return AuditEvent(
            tenant_id=decision.tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            entity_type="decision_case",
            entity_id=decision.id,
            description=event_type,
            details={"decision_id": decision.id, **details},
        )

    def _save(
        self, objects: list, events: list[AuditEvent], refresh: list | None = None
    ) -> None:
        self._repository.save_review_action(
            objects=objects, events=events, refresh=refresh
        )
