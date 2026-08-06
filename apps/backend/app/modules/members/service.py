from __future__ import annotations

from dataclasses import dataclass

from app.modules.decisions.service import DecisionNotFoundError
from app.modules.members.policies import authorize_reviewer_discovery
from app.modules.members.repository import MemberCandidateRow, MemberDirectoryRepository
from app.modules.members.schemas import (
    AssignmentCandidatePage,
    AssignmentCandidateResponse,
)


@dataclass(frozen=True)
class CandidateEligibilityError(ValueError):
    message: str = "Reviewer candidate not found"

    def __str__(self) -> str:
        return self.message


class MemberDirectoryService:
    def __init__(self, repository: MemberDirectoryRepository) -> None:
        self._repository = repository

    def reviewer_candidates(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_permissions: set[str],
        responsibility: str,
        query: str,
        offset: int,
        limit: int,
    ) -> AssignmentCandidatePage:
        authorize_reviewer_discovery(actor_permissions)
        if responsibility != "decision_reviewer":
            raise CandidateEligibilityError("Unsupported assignment responsibility")
        decision = self._repository.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        evidence = self._repository.list_active_evidence(
            tenant_id=tenant_id, decision_id=decision.id
        )
        rows, _ = self._repository.list_reviewer_candidates(
            tenant_id=tenant_id,
            query=query,
            offset=0,
            limit=50,
        )
        eligible = [
            row
            for row in rows
            if self.is_eligible(
                tenant_id=tenant_id,
                decision=decision,
                evidence=evidence,
                candidate=row,
            )
        ]
        page = eligible[offset : offset + limit]
        return AssignmentCandidatePage(
            items=[self._response(tenant_id, item) for item in page],
            offset=offset,
            limit=limit,
            total=len(eligible),
        )

    def require_eligible_reviewer(
        self, *, tenant_id: str, decision_id: str, membership_id: str
    ) -> MemberCandidateRow:
        decision = self._repository.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        candidate = self._repository.get_candidate(
            tenant_id=tenant_id, membership_id=membership_id
        )
        if candidate is None or not self.is_eligible(
            tenant_id=tenant_id,
            decision=decision,
            evidence=self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision.id
            ),
            candidate=candidate,
        ):
            raise CandidateEligibilityError()
        return candidate

    def get_tenant_member(
        self, *, tenant_id: str, membership_id: str
    ) -> MemberCandidateRow:
        candidate = self._repository.get_candidate(
            tenant_id=tenant_id, membership_id=membership_id
        )
        if candidate is None:
            raise CandidateEligibilityError()
        return candidate

    def is_eligible(self, *, tenant_id: str, decision, evidence, candidate) -> bool:
        membership = candidate.membership
        if (
            membership.tenant_id != tenant_id
            or not membership.is_active
            or not candidate.user.is_active
        ):
            return False
        permissions = self._repository.membership_permissions(
            tenant_id=tenant_id, membership_id=membership.id
        )
        required = {
            "decision.view",
            "decision.evidence.view",
            "decision.review.perform",
        }
        if not required.issubset(permissions):
            return False
        role_ids = {
            role.id
            for role in self._repository.membership_roles(
                tenant_id=tenant_id, membership_id=membership.id
            )
        }
        for snapshot in evidence:
            if membership.clearance_rank < snapshot.snapshot_classification_rank:
                return False
            if snapshot.snapshot_access_policy_id:
                allowed = self._repository.access_policy_role_ids(
                    tenant_id=tenant_id,
                    policy_id=snapshot.snapshot_access_policy_id,
                )
                if not role_ids.intersection(allowed):
                    return False
        return True

    def _response(
        self, tenant_id: str, candidate: MemberCandidateRow
    ) -> AssignmentCandidateResponse:
        roles = self._repository.membership_roles(
            tenant_id=tenant_id, membership_id=candidate.membership.id
        )
        return AssignmentCandidateResponse(
            membership_id=candidate.membership.id,
            display_name=candidate.user.full_name,
            email=candidate.user.email,
            organization_name=candidate.organization_name,
            role_labels=[role.name for role in roles],
            responsibility="decision_reviewer",
        )
