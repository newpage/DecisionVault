import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import (
    AuditEvent,
    DecisionLessonEvaluation,
    DecisionLessonPromotionProposal,
    KnowledgeCard,
    KnowledgeCardLessonProvenance,
    uid,
)
from app.modules.decisions.promotion_repository import DecisionLessonPromotionRepository
from test_decision_precedent_learning_postgres import seed


pytestmark = pytest.mark.postgres
URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def engine():
    if not URL.startswith("postgresql"):
        pytest.skip("PostgreSQL required")
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    yield engine
    engine.dispose()


def context(session, suffix):
    rows = seed(session, suffix)
    tenant, user, member, current, historical, assessment, _, adoption = rows
    evaluation = DecisionLessonEvaluation(
        tenant_id=tenant.id,
        decision_case_id=current.id,
        lesson_adoption_id=adoption.id,
        historical_decision_id=historical.id,
        effectiveness_assessment_id=assessment.id,
        classification="beneficial",
        rationale="Reduced disruption",
        was_applied=True,
        relevant_outcome_ids=[],
        evaluator_membership_id=member.id,
        current_effectiveness_snapshot="met",
        outcome_relevance_details={},
    )
    session.add(evaluation)
    session.commit()
    return rows, evaluation


def proposal(rows, evaluation, status="proposed"):
    tenant, _, member, current, historical, assessment, _, adoption = rows
    return DecisionLessonPromotionProposal(
        tenant_id=tenant.id,
        source_decision_id=historical.id,
        source_lesson_id=adoption.historical_lesson_id,
        evaluation_decision_id=current.id,
        lesson_adoption_id=adoption.id,
        lesson_evaluation_id=evaluation.id,
        effectiveness_assessment_id=assessment.id,
        status=status,
        rationale="Reusable",
        applicability="Regulated rollouts",
        limitations="Not universal",
        proposed_title="Phased rollout",
        proposed_summary="Stage rollout",
        proposed_body="Use verified phases",
        snapshot_source_decision={},
        snapshot_lesson={},
        snapshot_adoption={},
        snapshot_evaluation={},
        snapshot_effectiveness={},
        snapshot_relevant_outcomes=[],
        snapshot_provenance={},
        source_classification_rank=20,
        evaluation_classification_rank=20,
        inherited_classification_rank=20,
        proposed_by_membership_id=member.id,
    )


def test_composite_tenant_controlled_status_and_active_uniqueness(engine):
    with Session(engine) as db:
        first, evaluation = context(db, "promotion-a")
        second, _ = context(db, "promotion-b")
        invalid = proposal(first, evaluation)
        invalid.tenant_id = second[0].id
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        bad = proposal(first, evaluation, "publishing")
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(proposal(first, evaluation))
        db.commit()
        db.add(proposal(first, evaluation))
        with pytest.raises(IntegrityError):
            db.commit()


def test_terminal_history_allows_new_proposal_and_promoted_integrity(engine):
    with Session(engine) as db:
        rows, evaluation = context(db, "promotion-history")
        old = proposal(rows, evaluation, "rejected")
        old.reviewed_by_membership_id = rows[2].id
        old.reviewed_at = datetime.now(timezone.utc)
        old.review_rationale = "Too narrow"
        db.add(old)
        db.commit()
        db.add(proposal(rows, evaluation))
        db.commit()
        broken = proposal(rows, evaluation, "promoted")
        broken.reviewed_by_membership_id = rows[2].id
        broken.reviewed_at = datetime.now(timezone.utc)
        broken.review_rationale = "Approved"
        db.add(broken)
        with pytest.raises(IntegrityError):
            db.commit()


def test_concurrent_active_proposal_has_one_winner(engine):
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as db:
        rows, evaluation = context(db, "promotion-concurrent")
        ids = (
            rows[0].id,
            rows[1].id,
            rows[2].id,
            rows[3].id,
            rows[4].id,
            rows[5].id,
            rows[7].id,
            rows[7].historical_lesson_id,
            evaluation.id,
        )

    def create_one(value):
        (
            tenant_id,
            _,
            member_id,
            current_id,
            historical_id,
            assessment_id,
            adoption_id,
            lesson_id,
            evaluation_id,
        ) = ids
        with maker() as db:
            item = DecisionLessonPromotionProposal(
                tenant_id=tenant_id,
                source_decision_id=historical_id,
                source_lesson_id=lesson_id,
                evaluation_decision_id=current_id,
                lesson_adoption_id=adoption_id,
                lesson_evaluation_id=evaluation_id,
                effectiveness_assessment_id=assessment_id,
                status="proposed",
                rationale=value,
                applicability="Regulated",
                limitations="Bounded",
                proposed_title="Title",
                proposed_summary="Summary",
                proposed_body="Body",
                snapshot_source_decision={},
                snapshot_lesson={},
                snapshot_adoption={},
                snapshot_evaluation={},
                snapshot_effectiveness={},
                snapshot_relevant_outcomes=[],
                snapshot_provenance={},
                source_classification_rank=20,
                evaluation_classification_rank=20,
                inherited_classification_rank=20,
                proposed_by_membership_id=member_id,
            )
            db.add(item)
            try:
                db.commit()
                return True
            except IntegrityError:
                db.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create_one, ["First", "Second"]))
    assert sorted(results) == [False, True]


def test_card_provenance_and_audits_roll_back_atomically(engine):
    with Session(engine) as db:
        rows, evaluation = context(db, "promotion-rollback")
        item = proposal(rows, evaluation, "approved")
        item.reviewed_by_membership_id = rows[2].id
        item.reviewed_at = datetime.now(timezone.utc)
        item.review_rationale = "Approved"
        db.add(item)
        db.commit()
        card = KnowledgeCard(
            id=uid(),
            tenant_id=rows[0].id,
            workspace_id=rows[3].workspace_id,
            business_concept_id=rows[3].business_concept_id,
            title="Draft",
            summary="Summary",
            body="Body",
            knowledge_type="decision_lesson",
            lifecycle_status="draft",
            approval_status="not_submitted",
            classification_rank=20,
            ai_usage_allowed=False,
            owner_id=rows[1].id,
        )
        provenance = KnowledgeCardLessonProvenance(
            tenant_id=rows[0].id,
            knowledge_card_id=card.id,
            promotion_proposal_id=item.id,
            source_decision_id=rows[4].id,
            source_lesson_id=rows[7].historical_lesson_id,
            lesson_evaluation_id=evaluation.id,
            immutable_snapshot={},
        )
        invalid_audit = AuditEvent(
            tenant_id=rows[0].id,
            actor_id="missing",
            event_type="KnowledgeDraftCreatedFromDecisionLesson",
            entity_type="knowledge_card",
            entity_id=card.id,
            description="Invalid",
        )
        with pytest.raises(IntegrityError):
            DecisionLessonPromotionRepository(db).save(
                [card, provenance], [invalid_audit], card
            )
        assert (
            db.get(KnowledgeCard, card.id) is None
            and db.scalar(
                select(KnowledgeCardLessonProvenance).where(
                    KnowledgeCardLessonProvenance.knowledge_card_id == card.id
                )
            )
            is None
        )


def test_card_is_materialized_before_atomic_proposal_link(engine):
    with Session(engine) as db:
        rows, evaluation = context(db, "promotion-ordering")
        item = proposal(rows, evaluation, "approved")
        item.reviewed_by_membership_id = rows[2].id
        item.reviewed_at = datetime.now(timezone.utc)
        item.review_rationale = "Approved"
        db.add(item)
        db.commit()
        member_id = rows[2].id
        card = KnowledgeCard(
            id=uid(),
            tenant_id=rows[0].id,
            workspace_id=rows[3].workspace_id,
            business_concept_id=rows[3].business_concept_id,
            title="Ordered draft",
            summary="Summary",
            body="Body",
            knowledge_type="decision_lesson",
            lifecycle_status="draft",
            approval_status="not_submitted",
            classification_rank=20,
            ai_usage_allowed=False,
            owner_id=rows[1].id,
        )
        provenance = KnowledgeCardLessonProvenance(
            tenant_id=rows[0].id,
            knowledge_card_id=card.id,
            promotion_proposal_id=item.id,
            source_decision_id=rows[4].id,
            source_lesson_id=rows[7].historical_lesson_id,
            lesson_evaluation_id=evaluation.id,
            immutable_snapshot={},
        )
        item.promoted_by_membership_id = member_id
        item.promoted_at = datetime.now(timezone.utc)
        item.resulting_knowledge_card_id = card.id
        event = AuditEvent(
            tenant_id=rows[0].id,
            actor_id=rows[1].id,
            event_type="KnowledgeDraftCreatedFromDecisionLesson",
            entity_type="knowledge_card",
            entity_id=card.id,
            description="Created atomically",
        )
        item.status = "promoted"
        DecisionLessonPromotionRepository(db).save(
            [item, card, provenance], [event], item
        )
        assert db.get(KnowledgeCard, card.id).approval_status == "not_submitted"
        assert db.get(DecisionLessonPromotionProposal, item.id).status == "promoted"
