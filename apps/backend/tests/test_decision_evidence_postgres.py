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
    DecisionCase,
    DecisionEvidence,
    Organization,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.repository import DecisionRepository


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


def seed_decision(db: Session, suffix: str):
    tenant = Tenant(slug=f"tenant-{suffix}", name=f"Tenant {suffix}")
    user = User(
        email=f"user-{suffix}@example.com",
        full_name=f"User {suffix}",
        password_hash="unused",
    )
    db.add_all([tenant, user])
    db.flush()
    organization = Organization(
        tenant_id=tenant.id, name=f"Organization {suffix}", code=suffix
    )
    db.add(organization)
    db.flush()
    workspace = Workspace(
        tenant_id=tenant.id,
        organization_id=organization.id,
        name=f"Workspace {suffix}",
    )
    concept = BusinessConcept(
        tenant_id=tenant.id,
        name=f"Concept {suffix}",
        slug=f"concept-{suffix}",
    )
    db.add_all([workspace, concept])
    db.flush()
    decision = DecisionCase(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        title="Decision",
        question="Should this proceed?",
        created_by=user.id,
    )
    db.add(decision)
    db.flush()
    return tenant, user, decision


def snapshot(*, tenant_id, user_id, decision_id, card_id="card-1"):
    now = datetime.now(timezone.utc)
    return DecisionEvidence(
        tenant_id=tenant_id,
        decision_case_id=decision_id,
        knowledge_card_id=card_id,
        relationship_type="supporting",
        selection_rationale="Directly supports this Decision",
        snapshot_title="Immutable title",
        snapshot_content="Immutable content",
        snapshot_knowledge_type="policy",
        snapshot_authority_level="sop",
        snapshot_lifecycle_status="published",
        snapshot_approval_status="approved",
        snapshot_classification_rank=20,
        snapshot_trust_score=0.9,
        snapshot_ai_usage_allowed=True,
        snapshot_card_created_at=now,
        snapshot_source_metadata={"source": "integration-test"},
        selected_by=user_id,
    )


def test_postgres_constraints_json_and_active_duplicate_prevention(
    postgres_engine,
):
    with Session(postgres_engine) as db:
        tenant, user, decision = seed_decision(db, "constraints")
        first = snapshot(
            tenant_id=tenant.id,
            user_id=user.id,
            decision_id=decision.id,
        )
        db.add(first)
        db.commit()
        db.refresh(first)
        user_id = user.id
        assert first.snapshot_source_metadata == {
            "source": "integration-test"
        }

        duplicate = snapshot(
            tenant_id=tenant.id,
            user_id=user.id,
            decision_id=decision.id,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        first.removed_by = user_id
        first.removal_rationale = "Superseded"
        first.removed_at = datetime.now(timezone.utc)
        db.add(first)
        db.commit()
        replacement = snapshot(
            tenant_id=tenant.id,
            user_id=user_id,
            decision_id=decision.id,
        )
        db.add(replacement)
        db.commit()


def test_postgres_rejects_cross_tenant_decision_relationship(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, user_a, decision_a = seed_decision(db, "tenant-a")
        tenant_b, _, _ = seed_decision(db, "tenant-b")
        db.commit()
        invalid = snapshot(
            tenant_id=tenant_b.id,
            user_id=user_a.id,
            decision_id=decision_a.id,
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()


def test_postgres_rejects_invalid_relationship_and_partial_removal_metadata(
    postgres_engine,
):
    with Session(postgres_engine) as db:
        tenant, user, decision = seed_decision(db, "checks")
        db.commit()
        tenant_id = tenant.id
        user_id = user.id
        decision_id = decision.id
        invalid_relationship = snapshot(
            tenant_id=tenant_id,
            user_id=user_id,
            decision_id=decision_id,
            card_id="invalid-relationship-card",
        )
        invalid_relationship.relationship_type = "uncontrolled"
        db.add(invalid_relationship)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        partial_removal = snapshot(
            tenant_id=tenant_id,
            user_id=user_id,
            decision_id=decision_id,
            card_id="partial-removal-card",
        )
        partial_removal.removed_at = datetime.now(timezone.utc)
        db.add(partial_removal)
        with pytest.raises(IntegrityError):
            db.commit()


def test_postgres_rolls_back_snapshot_recalculation_and_audit_atomically(
    postgres_engine,
):
    with Session(postgres_engine) as db:
        tenant, user, decision = seed_decision(db, "rollback")
        db.commit()
        decision_id = decision.id
        evidence = snapshot(
            tenant_id=tenant.id,
            user_id=user.id,
            decision_id=decision.id,
            card_id="rollback-card",
        )
        decision.readiness_score = 85
        invalid_event = AuditEvent(
            tenant_id="missing-tenant",
            actor_id=user.id,
            event_type="DecisionEvidenceSelected",
            entity_type="decision_case",
            description="Must roll back",
        )

        with pytest.raises(IntegrityError):
            DecisionRepository(db).save_evidence_change(
                decision=decision,
                evidence=evidence,
                events=[invalid_event],
            )

    with Session(postgres_engine) as verification:
        stored = verification.get(DecisionCase, decision_id)
        assert stored.readiness_score == 0
        assert verification.get(DecisionEvidence, evidence.id) is None
