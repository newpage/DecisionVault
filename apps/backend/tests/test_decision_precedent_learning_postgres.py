import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    DecisionEffectivenessAssessment,
    DecisionLesson,
    DecisionLessonAdoption,
    DecisionLessonEvaluation,
    DecisionPrecedentEvaluation,
    DecisionPrecedentReference,
    Membership,
    Organization,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.learning_repository import DecisionLearningRepository


pytestmark = pytest.mark.postgres
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def engine():
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL does not select PostgreSQL")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    yield engine
    engine.dispose()


def seed(session: Session, suffix: str):
    tenant = Tenant(slug=f"learning-{suffix}", name="Learning")
    user = User(
        email=f"learning-{suffix}@example.com",
        full_name="Evaluator",
        password_hash="unused",
    )
    session.add_all([tenant, user])
    session.flush()
    organization = Organization(tenant_id=tenant.id, name="Org", code=f"ORG-{suffix}")
    session.add(organization)
    session.flush()
    member = Membership(
        tenant_id=tenant.id,
        organization_id=organization.id,
        user_id=user.id,
        clearance_rank=50,
    )
    workspace = Workspace(
        tenant_id=tenant.id,
        organization_id=organization.id,
        name="Workspace",
        description="",
    )
    concept = BusinessConcept(
        tenant_id=tenant.id, name="Concept", slug=f"concept-{suffix}"
    )
    session.add_all([member, workspace, concept])
    session.flush()
    current = DecisionCase(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        title="Current",
        question="Current?",
        status="closed",
        created_by=user.id,
    )
    historical = DecisionCase(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        title="Historical",
        question="Historical?",
        status="approved",
        created_by=user.id,
    )
    session.add_all([current, historical])
    session.flush()
    assessment = DecisionEffectivenessAssessment(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        revision=1,
        status="completed",
        assessment_date=date.today(),
        assessor_membership_id=member.id,
        classification="met",
        rationale="Completed assessment",
        completed_at=datetime.now(timezone.utc),
    )
    lesson = DecisionLesson(
        tenant_id=tenant.id,
        decision_case_id=historical.id,
        lesson_type="risk",
        description="Stage rollout",
        created_by_membership_id=member.id,
    )
    reference = DecisionPrecedentReference(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        historical_decision_id=historical.id,
        relationship_type="cautionary",
        rationale="Avoid failure",
        similarity_algorithm_version="decision_similarity_v1",
        similarity_score=84,
        similarity_components={},
        snapshot_historical_title=historical.title,
        snapshot_historical_status=historical.status,
        referenced_by_membership_id=member.id,
    )
    session.add_all([assessment, lesson, reference])
    session.flush()
    adoption = DecisionLessonAdoption(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        historical_decision_id=historical.id,
        historical_lesson_id=lesson.id,
        status="adopted",
        rationale="Apply staging",
        snapshot_lesson_type=lesson.lesson_type,
        snapshot_lesson_description=lesson.description,
        acted_by_membership_id=member.id,
    )
    session.add(adoption)
    session.commit()
    return tenant, user, member, current, historical, assessment, reference, adoption


def precedent_evaluation(rows, classification="useful"):
    tenant, _, member, current, historical, assessment, reference, _ = rows
    return DecisionPrecedentEvaluation(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        precedent_reference_id=reference.id,
        historical_decision_id=historical.id,
        effectiveness_assessment_id=assessment.id,
        classification=classification,
        rationale="Observed outcome",
        evaluator_membership_id=member.id,
        similarity_score_snapshot=84,
        current_effectiveness_snapshot="met",
        outcome_alignment_details={},
    )


def lesson_evaluation(rows, classification="beneficial"):
    tenant, _, member, current, historical, assessment, _, adoption = rows
    return DecisionLessonEvaluation(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        lesson_adoption_id=adoption.id,
        historical_decision_id=historical.id,
        effectiveness_assessment_id=assessment.id,
        classification=classification,
        rationale="Observed lesson outcome",
        was_applied=True,
        relevant_outcome_ids=[],
        evaluator_membership_id=member.id,
        current_effectiveness_snapshot="met",
        outcome_relevance_details={},
    )


def test_composite_tenant_and_parent_constraints_reject_mismatches(engine):
    with Session(engine) as session:
        first = seed(session, "composite-a")
        second = seed(session, "composite-b")
        invalid = precedent_evaluation(first)
        invalid.effectiveness_assessment_id = second[5].id
        session.add(invalid)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        cross_tenant = precedent_evaluation(first)
        cross_tenant.tenant_id = second[0].id
        session.add(cross_tenant)
        with pytest.raises(IntegrityError):
            session.commit()


def test_controlled_values_and_active_uniqueness(engine):
    with Session(engine) as session:
        rows = seed(session, "constraints")
        session.add(precedent_evaluation(rows, "invented"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(precedent_evaluation(rows))
        session.commit()
        session.add(precedent_evaluation(rows, "neutral"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_lesson_composite_constraints_controlled_values_and_active_uniqueness(engine):
    with Session(engine) as session:
        first = seed(session, "lesson-constraints-a")
        second = seed(session, "lesson-constraints-b")
        invalid_parent = lesson_evaluation(first)
        invalid_parent.effectiveness_assessment_id = second[5].id
        session.add(invalid_parent)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        invalid_value = lesson_evaluation(first, "invented")
        session.add(invalid_value)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(lesson_evaluation(first))
        session.commit()
        session.add(lesson_evaluation(first, "ineffective"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_supersession_integrity_and_atomic_audit(engine):
    with Session(engine) as session:
        rows = seed(session, "supersede")
        old = precedent_evaluation(rows)
        session.add(old)
        session.commit()
        replacement = precedent_evaluation(rows, "misleading")
        event = AuditEvent(
            tenant_id=rows[0].id,
            actor_id=rows[1].id,
            event_type="decision.precedent.evaluation_superseded",
            entity_type="decision_case",
            entity_id=rows[3].id,
            description="Superseded",
            details={},
        )
        saved = DecisionLearningRepository(session).supersede(
            old, replacement, event, rows[2].id, "Corrected after review"
        )
        assert old.superseded_by_evaluation_id == saved.id
        assert session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == event.event_type,
                AuditEvent.entity_id == rows[3].id,
            )
        )


def test_evaluation_and_audit_roll_back_together(engine):
    with Session(engine) as session:
        rows = seed(session, "rollback")
        record = precedent_evaluation(rows)
        invalid_event = AuditEvent(
            tenant_id=rows[0].id,
            actor_id="missing-user",
            event_type="decision.precedent.usefulness_evaluated",
            entity_type="decision_case",
            entity_id=rows[3].id,
            description="Invalid",
            details={},
        )
        with pytest.raises(IntegrityError):
            DecisionLearningRepository(session).save(record, invalid_event)
        assert (
            session.scalar(
                select(DecisionPrecedentEvaluation).where(
                    DecisionPrecedentEvaluation.id == record.id
                )
            )
            is None
        )


def test_concurrent_active_evaluation_allows_one_winner(engine):
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as setup:
        rows = seed(setup, "concurrent")
        ids = tuple(
            item.id for item in (rows[0], rows[2], rows[3], rows[4], rows[5], rows[6])
        )

    def create_one(classification):
        tenant_id, member_id, current_id, historical_id, assessment_id, reference_id = (
            ids
        )
        with maker() as session:
            record = DecisionPrecedentEvaluation(
                tenant_id=tenant_id,
                decision_case_id=current_id,
                precedent_reference_id=reference_id,
                historical_decision_id=historical_id,
                effectiveness_assessment_id=assessment_id,
                classification=classification,
                rationale="Concurrent",
                evaluator_membership_id=member_id,
                similarity_score_snapshot=84,
                current_effectiveness_snapshot="met",
                outcome_alignment_details={},
            )
            session.add(record)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create_one, ["useful", "neutral"]))
    assert sorted(results) == [False, True]
