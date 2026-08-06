import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionApprovalAction,
    DecisionApprovalCondition,
    DecisionCase,
    DecisionEvidence,
    DecisionReview,
    DecisionReviewAssignment,
    DecisionReviewEvidence,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    Workspace,
    uid,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.review import ReviewStateError
from app.modules.decisions.review_service import DecisionReviewService
from app.modules.members.repository import MemberDirectoryRepository
from app.modules.members.service import MemberDirectoryService


pytestmark = pytest.mark.postgres
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def postgres_engine():
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL does not select PostgreSQL")
    if "test" not in TEST_DATABASE_URL.lower():
        pytest.fail("Refusing to reset a PostgreSQL URL without 'test' in it")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed(db: Session, suffix: str):
    tenant = Tenant(slug=f"review-{suffix}", name=f"Review {suffix}")
    user = User(
        email=f"review-{suffix}@example.com",
        full_name=f"Reviewer {suffix}",
        password_hash="unused",
    )
    db.add_all([tenant, user])
    db.flush()
    organization = Organization(tenant_id=tenant.id, name="Org", code=suffix)
    db.add(organization)
    db.flush()
    membership = Membership(
        tenant_id=tenant.id,
        organization_id=organization.id,
        user_id=user.id,
        clearance_rank=50,
    )
    role = Role(
        tenant_id=tenant.id,
        code=f"reviewer-{suffix}",
        name="Decision Reviewer",
    )
    db.add_all([membership, role])
    db.flush()
    db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    for code in [
        "decision.view",
        "decision.evidence.view",
        "decision.review.perform",
    ]:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=code)
            db.add(permission)
            db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    workspace = Workspace(
        tenant_id=tenant.id, organization_id=organization.id, name="Workspace"
    )
    concept = BusinessConcept(
        tenant_id=tenant.id, name="Concept", slug=f"review-concept-{suffix}"
    )
    db.add_all([workspace, concept])
    db.flush()
    decision = DecisionCase(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        title="Governed decision",
        question="Should this governed decision proceed?",
        status="in_review",
        input_revision=2,
        created_by=user.id,
    )
    db.add(decision)
    db.flush()
    evidence = DecisionEvidence(
        tenant_id=tenant.id,
        decision_case_id=decision.id,
        knowledge_card_id=f"card-{suffix}",
        relationship_type="supporting",
        selection_rationale="Supports the decision",
        snapshot_title="Immutable evidence",
        snapshot_content="Governed snapshot content",
        snapshot_knowledge_type="policy",
        snapshot_authority_level="sop",
        snapshot_lifecycle_status="published",
        snapshot_approval_status="approved",
        snapshot_classification_rank=20,
        snapshot_trust_score=0.9,
        snapshot_ai_usage_allowed=True,
        snapshot_card_created_at=datetime.now(timezone.utc),
        selected_by=user.id,
    )
    review = DecisionReview(
        tenant_id=tenant.id,
        decision_case_id=decision.id,
        sequence=1,
        review_type="final_approval",
        assigned_reviewer_membership_id=membership.id,
        assigned_by=user.id,
        status="completed",
        conclusion="recommend_approve",
        summary="All governed checks passed",
        decision_revision=2,
        freshness_status="current",
        submitted_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add_all([evidence, review])
    db.flush()
    db.add(
        DecisionReviewEvidence(
            tenant_id=tenant.id,
            review_id=review.id,
            decision_evidence_id=evidence.id,
        )
    )
    return tenant, user, membership, decision, evidence, review


def add_reviewer(db: Session, tenant, organization_id: str, suffix: str):
    user = User(
        email=f"candidate-{suffix}@example.com",
        full_name=f"Candidate {suffix}",
        password_hash="unused",
    )
    db.add(user)
    db.flush()
    membership = Membership(
        tenant_id=tenant.id,
        organization_id=organization_id,
        user_id=user.id,
        clearance_rank=50,
    )
    role = Role(
        tenant_id=tenant.id,
        code=f"candidate-role-{suffix}",
        name="Decision Reviewer",
    )
    db.add_all([membership, role])
    db.flush()
    db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    for code in [
        "decision.view",
        "decision.evidence.view",
        "decision.review.perform",
    ]:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.flush()
    return user, membership


def test_review_records_freeze_evidence_and_enforce_controlled_states(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, membership, decision, evidence, review = seed(db, "valid")
        db.commit()
        association = db.get(
            DecisionReviewEvidence, (tenant.id, review.id, evidence.id)
        )
        assert association is not None
        assert review.decision_revision == decision.input_revision

        invalid = DecisionReview(
            tenant_id=tenant.id,
            decision_case_id=decision.id,
            sequence=2,
            review_type="informal",
            assigned_reviewer_membership_id=membership.id,
            assigned_by=user.id,
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()


def test_review_evidence_association_cannot_cross_tenant_boundaries(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, _, _, _, _, review_a = seed(db, "tenant-a")
        tenant_b, _, _, _, evidence_b, _ = seed(db, "tenant-b")
        db.flush()
        db.add(
            DecisionReviewEvidence(
                tenant_id=tenant_a.id,
                review_id=review_a.id,
                decision_evidence_id=evidence_b.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        assert tenant_a.id != tenant_b.id


def test_conditional_approval_requires_auditable_condition_metadata(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, _, decision, _, review = seed(db, "condition")
        action = DecisionApprovalAction(
            tenant_id=tenant.id,
            decision_case_id=decision.id,
            review_id=review.id,
            action="conditionally_approved",
            rationale="Proceed only after the control is verified",
            actor_id=user.id,
        )
        db.add(action)
        db.flush()
        condition = DecisionApprovalCondition(
            tenant_id=tenant.id,
            decision_case_id=decision.id,
            approval_action_id=action.id,
            condition_text="Verify the compensating control",
            responsible_party="Risk owner",
            created_by=user.id,
        )
        db.add(condition)
        db.commit()
        assert condition.status == "open"

        user_id = user.id
        condition.status = "satisfied"
        condition.satisfied_by = user_id
        condition.satisfied_at = datetime.now(timezone.utc)
        condition.satisfaction_response = ""
        db.add(condition)
        with pytest.raises(IntegrityError):
            db.commit()


def test_authority_cannot_approve_stale_review_and_success_is_audited(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, _, decision, _, review = seed(db, "authority")
        db.commit()
        authority = User(
            email="authority@example.com",
            full_name="Decision Authority",
            password_hash="unused",
        )
        db.add(authority)
        db.commit()
        service = DecisionReviewService(
            DecisionRepository(db),
            MemberDirectoryService(MemberDirectoryRepository(db)),
        )

        review.freshness_status = "stale"
        db.commit()
        with pytest.raises(ReviewStateError, match="current completed"):
            service.approval(
                tenant_id=tenant.id,
                decision_id=decision.id,
                actor_id=authority.id,
                permissions={"decision.approve"},
                action="approved",
                rationale="All approval requirements are satisfied",
            )

        review.freshness_status = "current"
        db.commit()
        with pytest.raises(ReviewStateError, match="cannot exercise approval"):
            service.approval(
                tenant_id=tenant.id,
                decision_id=decision.id,
                actor_id=user.id,
                permissions={"decision.approve"},
                action="approved",
                rationale="A reviewer cannot approve their own final review",
            )
        result = service.approval(
            tenant_id=tenant.id,
            decision_id=decision.id,
            actor_id=authority.id,
            permissions={"decision.approve"},
            action="approved",
            rationale="All approval requirements are satisfied",
        )

        assert result.decision.status == "approved"
        event = (
            db.query(AuditEvent)
            .filter_by(tenant_id=tenant.id, event_type="DecisionApprovalRecorded")
            .one()
        )
        assert event.details["review_id"] == review.id
        assert event.details["rationale"] == "All approval requirements are satisfied"


def test_review_assignment_uses_tenant_membership_and_preserves_reassignment_history(
    postgres_engine,
):
    with Session(postgres_engine) as db:
        tenant, _, existing_membership, decision, _, _ = seed(db, "assignment")
        first_user, first = add_reviewer(
            db, tenant, existing_membership.organization_id, "first"
        )
        _, second = add_reviewer(
            db, tenant, existing_membership.organization_id, "second"
        )
        db.commit()
        service = DecisionReviewService(
            DecisionRepository(db),
            MemberDirectoryService(MemberDirectoryRepository(db)),
        )

        assigned = service.assign(
            tenant_id=tenant.id,
            decision_id=decision.id,
            actor_id=first_user.id,
            permissions={
                "decision.review.assign",
                "decision.view",
                "decision.evidence.view",
            },
            membership_id=first.id,
            review_type="risk",
            rationale="Risk expertise is required",
        )
        reassigned = service.reassign(
            tenant_id=tenant.id,
            decision_id=decision.id,
            review_id=assigned.id,
            actor_id=first_user.id,
            permissions={
                "decision.review.assign",
                "decision.view",
                "decision.evidence.view",
            },
            membership_id=second.id,
            rationale="Coverage changed before review work started",
        )

        assert reassigned.assigned_reviewer_membership_id == second.id
        history = DecisionRepository(db).list_assignment_history(
            tenant_id=tenant.id, review_id=assigned.id
        )
        assert [item.new_membership_id for item in history] == [first.id, second.id]
        assert history[1].previous_membership_id == first.id
        assert (
            db.query(AuditEvent)
            .filter_by(
                tenant_id=tenant.id,
                event_type="DecisionReviewerReassigned",
            )
            .count()
            == 1
        )

        stored = db.get(DecisionReview, assigned.id)
        stored.status = "in_progress"
        stored.started_at = datetime.now(timezone.utc)
        db.commit()
        with pytest.raises(ReviewStateError, match="after work starts"):
            service.reassign(
                tenant_id=tenant.id,
                decision_id=decision.id,
                review_id=assigned.id,
                actor_id=first_user.id,
                permissions={
                    "decision.review.assign",
                    "decision.view",
                    "decision.evidence.view",
                },
                membership_id=first.id,
                rationale="This reassignment must be rejected",
            )


def test_review_assignment_membership_cannot_cross_tenant(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, user_a, _, decision_a, _, _ = seed(db, "assignment-a")
        tenant_b, _, membership_b, _, _, _ = seed(db, "assignment-b")
        invalid = DecisionReview(
            tenant_id=tenant_a.id,
            decision_case_id=decision_a.id,
            sequence=2,
            review_type="business",
            assigned_reviewer_membership_id=membership_b.id,
            assigned_by=user_a.id,
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()
        assert tenant_a.id != tenant_b.id


def test_assignment_and_audit_roll_back_atomically(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, membership, decision, _, _ = seed(db, "assignment-rollback")
        assignment = DecisionReviewAssignment(
            id=uid(),
            tenant_id=tenant.id,
            review_id="missing-review",
            new_membership_id=membership.id,
            assigned_by=user.id,
            rationale="Must roll back with invalid review",
        )
        event = AuditEvent(
            tenant_id=tenant.id,
            actor_id=user.id,
            event_type="DecisionReviewAssigned",
            entity_type="decision_case",
            entity_id=decision.id,
            description="Must roll back",
        )
        with pytest.raises(IntegrityError):
            DecisionRepository(db).save_review_action(
                objects=[assignment], events=[event]
            )
        assert db.get(DecisionReviewAssignment, assignment.id) is None
        assert (
            db.query(AuditEvent)
            .filter_by(
                tenant_id=tenant.id,
                event_type="DecisionReviewAssigned",
            )
            .count()
            == 0
        )


def test_concurrent_duplicate_assignment_allows_one_winner(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, _, existing, decision, _, _ = seed(db, "assignment-race")
        actor, candidate = add_reviewer(
            db, tenant, existing.organization_id, "race-candidate"
        )
        db.commit()
        tenant_id = tenant.id
        decision_id = decision.id
        actor_id = actor.id
        membership_id = candidate.id

    def assign_once(label: str):
        with Session(postgres_engine) as db:
            service = DecisionReviewService(
                DecisionRepository(db),
                MemberDirectoryService(MemberDirectoryRepository(db)),
            )
            try:
                service.assign(
                    tenant_id=tenant_id,
                    decision_id=decision_id,
                    actor_id=actor_id,
                    permissions={
                        "decision.review.assign",
                        "decision.view",
                        "decision.evidence.view",
                    },
                    membership_id=membership_id,
                    review_type="compliance",
                    rationale=f"Concurrent governed assignment {label}",
                )
                return "assigned"
            except ReviewStateError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(assign_once, ["one", "two"]))

    assert sorted(results) == ["assigned", "conflict"]
    with Session(postgres_engine) as db:
        active = db.scalars(
            select(DecisionReview).where(
                DecisionReview.tenant_id == tenant_id,
                DecisionReview.decision_case_id == decision_id,
                DecisionReview.assigned_reviewer_membership_id == membership_id,
                DecisionReview.review_type == "compliance",
                DecisionReview.status == "assigned",
            )
        ).all()
        assert len(active) == 1


def test_postgres_directory_search_excludes_inactive_and_foreign_members(
    postgres_engine,
):
    with Session(postgres_engine) as db:
        tenant, _, existing, decision, _, _ = seed(db, "directory")
        _, eligible = add_reviewer(
            db, tenant, existing.organization_id, "directory-eligible"
        )
        inactive_user, inactive = add_reviewer(
            db, tenant, existing.organization_id, "directory-inactive"
        )
        inactive.is_active = False
        inactive_user.is_active = False
        foreign_tenant, _, foreign_existing, _, _, _ = seed(db, "directory-foreign")
        add_reviewer(
            db,
            foreign_tenant,
            foreign_existing.organization_id,
            "directory-foreign-candidate",
        )
        db.commit()
        service = MemberDirectoryService(MemberDirectoryRepository(db))

        result = service.reviewer_candidates(
            tenant_id=tenant.id,
            decision_id=decision.id,
            actor_permissions={
                "decision.view",
                "decision.evidence.view",
                "decision.review.assign",
            },
            responsibility="decision_reviewer",
            query="directory-eligible",
            offset=0,
            limit=20,
        )

        assert [item.membership_id for item in result.items] == [eligible.id]
        assert all(item.organization_name == "Org" for item in result.items)
