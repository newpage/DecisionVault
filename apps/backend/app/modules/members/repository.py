from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AccessPolicyRole,
    AccessPolicy,
    DecisionCase,
    DecisionEvidence,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)


@dataclass(frozen=True)
class MemberCandidateRow:
    membership: Membership
    user: User
    organization_name: str


class MemberDirectoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_decision(self, *, tenant_id: str, decision_id: str) -> DecisionCase | None:
        return self._db.scalar(
            select(DecisionCase).where(
                DecisionCase.tenant_id == tenant_id,
                DecisionCase.id == decision_id,
            )
        )

    def list_active_evidence(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionEvidence]:
        return list(
            self._db.scalars(
                select(DecisionEvidence).where(
                    DecisionEvidence.tenant_id == tenant_id,
                    DecisionEvidence.decision_case_id == decision_id,
                    DecisionEvidence.removed_at.is_(None),
                )
            ).all()
        )

    def list_reviewer_candidates(
        self,
        *,
        tenant_id: str,
        query: str,
        offset: int,
        limit: int,
    ) -> tuple[list[MemberCandidateRow], int]:
        eligible_membership_ids = (
            select(MembershipRole.membership_id)
            .join(Role, Role.id == MembershipRole.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                Role.tenant_id == tenant_id,
                Permission.code == "decision.review.perform",
            )
        )
        filters = [
            Membership.tenant_id == tenant_id,
            Membership.is_active.is_(True),
            User.is_active.is_(True),
            Membership.id.in_(eligible_membership_ids),
        ]
        normalized = query.strip().lower()
        if normalized:
            pattern = f"%{normalized}%"
            filters.append(
                or_(
                    func.lower(User.full_name).like(pattern),
                    func.lower(User.email).like(pattern),
                    func.lower(Organization.name).like(pattern),
                )
            )
        total = int(
            self._db.scalar(
                select(func.count(Membership.id))
                .join(User, User.id == Membership.user_id)
                .join(
                    Organization,
                    (Organization.id == Membership.organization_id)
                    & (Organization.tenant_id == tenant_id),
                )
                .where(*filters)
            )
            or 0
        )
        rows = self._db.execute(
            select(Membership, User, Organization.name)
            .join(User, User.id == Membership.user_id)
            .join(
                Organization,
                (Organization.id == Membership.organization_id)
                & (Organization.tenant_id == tenant_id),
            )
            .where(*filters)
            .order_by(func.lower(User.full_name), Membership.id)
            .offset(offset)
            .limit(limit)
        ).all()
        return (
            [MemberCandidateRow(row[0], row[1], row[2]) for row in rows],
            total,
        )

    def get_candidate(
        self, *, tenant_id: str, membership_id: str
    ) -> MemberCandidateRow | None:
        row = self._db.execute(
            select(Membership, User, Organization.name)
            .join(User, User.id == Membership.user_id)
            .join(
                Organization,
                (Organization.id == Membership.organization_id)
                & (Organization.tenant_id == tenant_id),
            )
            .where(
                Membership.tenant_id == tenant_id,
                Membership.id == membership_id,
            )
        ).first()
        return MemberCandidateRow(row[0], row[1], row[2]) if row else None

    def membership_roles(self, *, tenant_id: str, membership_id: str) -> list[Role]:
        return list(
            self._db.scalars(
                select(Role)
                .join(MembershipRole, MembershipRole.role_id == Role.id)
                .where(
                    Role.tenant_id == tenant_id,
                    MembershipRole.membership_id == membership_id,
                )
                .order_by(Role.name)
            ).all()
        )

    def membership_permissions(self, *, tenant_id: str, membership_id: str) -> set[str]:
        return set(
            self._db.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(MembershipRole, MembershipRole.role_id == Role.id)
                .where(
                    Role.tenant_id == tenant_id,
                    MembershipRole.membership_id == membership_id,
                )
            ).all()
        )

    def access_policy_role_ids(self, *, tenant_id: str, policy_id: str) -> set[str]:
        return set(
            self._db.scalars(
                select(AccessPolicyRole.role_id)
                .join(AccessPolicy, AccessPolicy.id == AccessPolicyRole.policy_id)
                .join(Role, Role.id == AccessPolicyRole.role_id)
                .where(
                    AccessPolicy.tenant_id == tenant_id,
                    Role.tenant_id == tenant_id,
                    AccessPolicyRole.policy_id == policy_id,
                )
            ).all()
        )
