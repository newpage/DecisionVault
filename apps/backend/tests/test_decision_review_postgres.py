import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
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
    DecisionReviewEvidence,
    Organization,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.review import ReviewStateError
from app.modules.decisions.review_service import DecisionReviewService


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
        assigned_reviewer_id=user.id,
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
    return tenant, user, decision, evidence, review


def test_review_records_freeze_evidence_and_enforce_controlled_states(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, decision, evidence, review = seed(db, "valid")
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
            assigned_reviewer_id=user.id,
            assigned_by=user.id,
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()


def test_review_evidence_association_cannot_cross_tenant_boundaries(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, _, _, _, review_a = seed(db, "tenant-a")
        tenant_b, _, _, evidence_b, _ = seed(db, "tenant-b")
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
        tenant, user, decision, _, review = seed(db, "condition")
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
        tenant, user, decision, _, review = seed(db, "authority")
        db.commit()
        service = DecisionReviewService(DecisionRepository(db))

        review.freshness_status = "stale"
        db.commit()
        with pytest.raises(ReviewStateError, match="current completed"):
            service.approval(
                tenant_id=tenant.id,
                decision_id=decision.id,
                actor_id=user.id,
                permissions={"decision.approve"},
                action="approved",
                rationale="All approval requirements are satisfied",
            )

        review.freshness_status = "current"
        db.commit()
        result = service.approval(
            tenant_id=tenant.id,
            decision_id=decision.id,
            actor_id=user.id,
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
