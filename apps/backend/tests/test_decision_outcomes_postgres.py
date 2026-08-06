import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    BusinessConcept,
    DecisionCase,
    DecisionExpectedOutcome,
    DecisionOutcomeObservation,
    Membership,
    Organization,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.outcome_repository import DecisionOutcomeRepository
from app.modules.decisions.outcome_service import (
    DecisionOutcomeService,
    OutcomeStateError,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.schemas import (
    AssessmentCreate,
    ExpectedOutcomeCreate,
    ObservationCreate,
)
from app.modules.decisions.service import DecisionNotFoundError


pytestmark = pytest.mark.postgres
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
PERMISSIONS = {
    "decision.view",
    "decision.outcome.view",
    "decision.outcome.define",
    "decision.outcome.record",
    "decision.outcome.verify",
    "decision.outcome.assess",
    "decision.lesson.record",
}


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
    tenant = Tenant(slug=f"outcome-{suffix}", name=f"Outcome {suffix}")
    creator = User(
        email=f"creator-{suffix}@example.com",
        full_name="Creator",
        password_hash="unused",
    )
    verifier = User(
        email=f"verifier-{suffix}@example.com",
        full_name="Verifier",
        password_hash="unused",
    )
    db.add_all([tenant, creator, verifier])
    db.flush()
    organization = Organization(tenant_id=tenant.id, name="Org", code=suffix)
    db.add(organization)
    db.flush()
    creator_membership = Membership(
        tenant_id=tenant.id, organization_id=organization.id, user_id=creator.id
    )
    verifier_membership = Membership(
        tenant_id=tenant.id, organization_id=organization.id, user_id=verifier.id
    )
    workspace = Workspace(
        tenant_id=tenant.id, organization_id=organization.id, name="Workspace"
    )
    concept = BusinessConcept(
        tenant_id=tenant.id, name="Concept", slug=f"outcome-concept-{suffix}"
    )
    db.add_all([creator_membership, verifier_membership, workspace, concept])
    db.flush()
    decision = DecisionCase(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        title="Approved decision",
        question="Did this approved decision work?",
        status="approved",
        created_by=creator.id,
    )
    db.add(decision)
    db.commit()
    return tenant, creator_membership, verifier_membership, decision


def command(**changes):
    values = dict(
        title="Reduce cycle time",
        description="Reduce processing time",
        measurement_type="duration",
        baseline_value=20,
        target_value=10,
        unit="days",
        target_direction="decrease",
        target_date=date.today(),
        weight=2,
        is_critical=True,
        success_criteria="Verified cycle time is ten days or less",
    )
    values.update(changes)
    return ExpectedOutcomeCreate(**values)


def test_governed_observation_verification_and_assessment_are_atomic(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, recorder, verifier, decision = seed(db, "flow")
        service = DecisionOutcomeService(
            DecisionOutcomeRepository(db), DecisionRepository(db)
        )
        outcome = service.create_outcome(
            tenant_id=tenant.id,
            decision_id=decision.id,
            membership_id=recorder.id,
            permissions=PERMISSIONS,
            command=command(),
        )
        assert outcome.frozen_at is not None
        observation = service.record_observation(
            tenant_id=tenant.id,
            decision_id=decision.id,
            outcome_id=outcome.id,
            membership_id=recorder.id,
            permissions=PERMISSIONS,
            command=ObservationCreate(
                observation_date=date.today(),
                numeric_value=8,
                observed_status="achieved",
                provenance="verified_business_record",
                source_reference="ERP report 42",
            ),
        )
        with pytest.raises(OutcomeStateError, match="cannot independently verify"):
            service.verify_observation(
                tenant_id=tenant.id,
                decision_id=decision.id,
                outcome_id=outcome.id,
                observation_id=observation.id,
                membership_id=recorder.id,
                permissions=PERMISSIONS,
                rationale="Self check",
            )
        verified = service.verify_observation(
            tenant_id=tenant.id,
            decision_id=decision.id,
            outcome_id=outcome.id,
            observation_id=observation.id,
            membership_id=verifier.id,
            permissions=PERMISSIONS,
            rationale="Matched the governed record",
        )
        assert verified.verification_status == "verified"
        assessment = service.create_assessment(
            tenant_id=tenant.id,
            decision_id=decision.id,
            membership_id=verifier.id,
            permissions=PERMISSIONS,
            command=AssessmentCreate(
                assessment_date=date.today(),
                classification="met",
                rationale="Verified critical target was met",
            ),
        )
        completed = service.complete_assessment(
            tenant_id=tenant.id,
            decision_id=decision.id,
            assessment_id=assessment.id,
            membership_id=verifier.id,
            permissions=PERMISSIONS,
        )
        assert completed.status == "completed"
        assert completed.calculation_details["aggregate"]["classification"] == "met"


def test_composite_tenant_constraints_reject_foreign_membership(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, member_a, _, decision_a = seed(db, "constraint-a")
        _, member_b, _, _ = seed(db, "constraint-b")
        db.add(
            DecisionExpectedOutcome(
                tenant_id=tenant_a.id,
                decision_case_id=decision_a.id,
                title="Foreign owner",
                description="Invalid cross tenant owner",
                measurement_type="numeric",
                target_value=1,
                target_direction="increase",
                success_criteria="Must fail",
                responsible_membership_id=member_b.id,
                created_by_membership_id=member_a.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_verification_metadata_and_separation_constraints(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, member, _, decision = seed(db, "constraints")
        outcome = DecisionExpectedOutcome(
            tenant_id=tenant.id,
            decision_case_id=decision.id,
            title="Outcome",
            description="Outcome description",
            measurement_type="numeric",
            target_value=1,
            target_direction="increase",
            success_criteria="Target reached",
            created_by_membership_id=member.id,
        )
        db.add(outcome)
        db.flush()
        db.add(
            DecisionOutcomeObservation(
                tenant_id=tenant.id,
                decision_case_id=decision.id,
                expected_outcome_id=outcome.id,
                observation_date=date.today(),
                numeric_value=1,
                provenance="manually_reported",
                recorded_by_membership_id=member.id,
                verification_status="verified",
                verified_by_membership_id=member.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_foreign_tenant_identifiers_are_non_disclosing(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, member_a, _, _ = seed(db, "scope-a")
        _, _, _, decision_b = seed(db, "scope-b")
        service = DecisionOutcomeService(
            DecisionOutcomeRepository(db), DecisionRepository(db)
        )
        with pytest.raises(DecisionNotFoundError, match="Decision not found"):
            service.create_outcome(
                tenant_id=tenant_a.id,
                decision_id=decision_b.id,
                membership_id=member_a.id,
                permissions=PERMISSIONS,
                command=command(),
            )
