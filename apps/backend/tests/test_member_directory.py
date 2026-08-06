from types import SimpleNamespace

import pytest

from app.modules.decisions.policies import DecisionPermissionError
from app.modules.members.repository import MemberCandidateRow
from app.modules.members.service import (
    CandidateEligibilityError,
    MemberDirectoryService,
)


class DirectoryRepository:
    def __init__(self):
        self.decision = SimpleNamespace(id="decision-1")
        self.evidence = [
            SimpleNamespace(
                snapshot_classification_rank=20,
                snapshot_access_policy_id=None,
            )
        ]
        self.rows = [
            self.row("member-1", "tenant-1", "Avery Reviewer", "avery@example.com"),
            self.row(
                "member-2",
                "tenant-1",
                "Inactive Member",
                "inactive@example.com",
                membership_active=False,
            ),
            self.row(
                "member-3",
                "tenant-1",
                "Inactive User",
                "disabled@example.com",
                user_active=False,
            ),
            self.row("member-4", "tenant-2", "Foreign Reviewer", "foreign@example.com"),
        ]
        self.permissions = {
            "member-1": {
                "decision.view",
                "decision.evidence.view",
                "decision.review.perform",
            },
            "member-2": {"decision.review.perform"},
            "member-3": {"decision.review.perform"},
            "member-4": {
                "decision.view",
                "decision.evidence.view",
                "decision.review.perform",
            },
        }

    @staticmethod
    def row(
        member_id, tenant_id, name, email, membership_active=True, user_active=True
    ):
        return MemberCandidateRow(
            SimpleNamespace(
                id=member_id,
                tenant_id=tenant_id,
                is_active=membership_active,
                clearance_rank=50,
            ),
            SimpleNamespace(
                id=f"user-{member_id}",
                full_name=name,
                email=email,
                is_active=user_active,
            ),
            "Risk and Quality",
        )

    def get_decision(self, **kwargs):
        return self.decision

    def list_active_evidence(self, **kwargs):
        return self.evidence

    def list_reviewer_candidates(self, *, query, **kwargs):
        rows = [
            row
            for row in self.rows
            if not query or query.lower() in row.user.full_name.lower()
        ]
        return rows, len(rows)

    def get_candidate(self, *, tenant_id, membership_id):
        return next(
            (
                row
                for row in self.rows
                if row.membership.tenant_id == tenant_id
                and row.membership.id == membership_id
            ),
            None,
        )

    def membership_permissions(self, *, membership_id, **kwargs):
        return self.permissions.get(membership_id, set())

    def membership_roles(self, *, membership_id, **kwargs):
        return [SimpleNamespace(id="role-reviewer", name="Decision Reviewer")]

    def access_policy_role_ids(self, **kwargs):
        return {"role-reviewer"}


PERMISSIONS = {
    "decision.view",
    "decision.evidence.view",
    "decision.review.assign",
}


def candidates(service, **overrides):
    values = {
        "tenant_id": "tenant-1",
        "decision_id": "decision-1",
        "actor_permissions": PERMISSIONS,
        "responsibility": "decision_reviewer",
        "query": "",
        "offset": 0,
        "limit": 20,
    }
    values.update(overrides)
    return service.reviewer_candidates(**values)


def test_directory_returns_only_active_eligible_same_tenant_members():
    result = candidates(MemberDirectoryService(DirectoryRepository()))

    assert result.total == 1
    assert result.items[0].membership_id == "member-1"
    assert result.items[0].display_name == "Avery Reviewer"
    assert result.items[0].role_labels == ["Decision Reviewer"]
    assert set(result.items[0].model_dump()) == {
        "membership_id",
        "display_name",
        "email",
        "organization_name",
        "role_labels",
        "responsibility",
    }


def test_directory_search_pagination_and_responsibility_are_bounded():
    service = MemberDirectoryService(DirectoryRepository())

    assert candidates(service, query="avery").total == 1
    assert candidates(service, query="missing").total == 0
    assert candidates(service, offset=1, limit=1).items == []
    with pytest.raises(CandidateEligibilityError, match="Unsupported"):
        candidates(service, responsibility="approver")


def test_directory_requires_assignment_visibility_and_evidence_permissions():
    service = MemberDirectoryService(DirectoryRepository())

    with pytest.raises(DecisionPermissionError):
        candidates(service, actor_permissions={"decision.review.assign"})


def test_direct_assignment_revalidation_rejects_inactive_foreign_and_permission_loss():
    repository = DirectoryRepository()
    service = MemberDirectoryService(repository)

    assert (
        service.require_eligible_reviewer(
            tenant_id="tenant-1",
            decision_id="decision-1",
            membership_id="member-1",
        ).user.full_name
        == "Avery Reviewer"
    )
    repository.permissions["member-1"] = set()
    with pytest.raises(CandidateEligibilityError):
        service.require_eligible_reviewer(
            tenant_id="tenant-1",
            decision_id="decision-1",
            membership_id="member-1",
        )
    for member_id in ["member-2", "member-3", "member-4"]:
        with pytest.raises(CandidateEligibilityError):
            service.require_eligible_reviewer(
                tenant_id="tenant-1",
                decision_id="decision-1",
                membership_id=member_id,
            )


def test_evidence_clearance_and_policy_roles_are_required():
    repository = DirectoryRepository()
    service = MemberDirectoryService(repository)
    repository.evidence[0].snapshot_classification_rank = 60
    assert candidates(service).items == []

    repository.evidence[0].snapshot_classification_rank = 20
    repository.evidence[0].snapshot_access_policy_id = "policy-1"
    repository.access_policy_role_ids = lambda **kwargs: {"different-role"}
    assert candidates(service).items == []
