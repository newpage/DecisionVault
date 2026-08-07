from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DecisionEffectivenessAssessment,
    DecisionExpectedOutcome,
    DecisionLesson,
    DecisionLessonAdoption,
    DecisionLessonEvaluation,
    DecisionLessonPromotionProposal,
    KnowledgeCard,
    KnowledgeCardLessonProvenance,
    Membership,
)
from app.modules.knowledge.policies import authorized_knowledge_filters


class DecisionLessonPromotionRepository:
    def __init__(self, db: Session):
        self._db = db

    def active_membership(self, tenant_id, membership_id):
        return self._db.scalar(
            select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.id == membership_id,
                Membership.is_active.is_(True),
            )
        )

    def lesson(self, tenant_id, decision_id, lesson_id):
        return self._db.scalar(
            select(DecisionLesson).where(
                DecisionLesson.tenant_id == tenant_id,
                DecisionLesson.decision_case_id == decision_id,
                DecisionLesson.id == lesson_id,
            )
        )

    def completed_assessment(self, tenant_id, decision_id):
        return self._db.scalar(
            select(DecisionEffectivenessAssessment)
            .where(
                DecisionEffectivenessAssessment.tenant_id == tenant_id,
                DecisionEffectivenessAssessment.decision_case_id == decision_id,
                DecisionEffectivenessAssessment.status == "completed",
            )
            .order_by(DecisionEffectivenessAssessment.revision.desc())
            .limit(1)
        )

    def evaluation_context(self, tenant_id, source_lesson_id, evaluation_id):
        return self._db.execute(
            select(
                DecisionLessonEvaluation,
                DecisionLessonAdoption,
                DecisionEffectivenessAssessment,
            )
            .join(
                DecisionLessonAdoption,
                (DecisionLessonAdoption.tenant_id == DecisionLessonEvaluation.tenant_id)
                & (
                    DecisionLessonAdoption.id
                    == DecisionLessonEvaluation.lesson_adoption_id
                ),
            )
            .join(
                DecisionEffectivenessAssessment,
                (
                    DecisionEffectivenessAssessment.tenant_id
                    == DecisionLessonEvaluation.tenant_id
                )
                & (
                    DecisionEffectivenessAssessment.id
                    == DecisionLessonEvaluation.effectiveness_assessment_id
                ),
            )
            .where(
                DecisionLessonEvaluation.tenant_id == tenant_id,
                DecisionLessonEvaluation.id == evaluation_id,
                DecisionLessonEvaluation.superseded_at.is_(None),
                DecisionLessonAdoption.historical_lesson_id == source_lesson_id,
                DecisionLessonAdoption.superseded_at.is_(None),
                DecisionEffectivenessAssessment.status == "completed",
            )
        ).one_or_none()

    def eligible_contexts(self, tenant_id, source_lesson_id):
        return self._db.execute(
            select(
                DecisionLessonEvaluation,
                DecisionLessonAdoption,
                DecisionEffectivenessAssessment,
            )
            .join(
                DecisionLessonAdoption,
                (DecisionLessonAdoption.tenant_id == DecisionLessonEvaluation.tenant_id)
                & (
                    DecisionLessonAdoption.id
                    == DecisionLessonEvaluation.lesson_adoption_id
                ),
            )
            .join(
                DecisionEffectivenessAssessment,
                (
                    DecisionEffectivenessAssessment.tenant_id
                    == DecisionLessonEvaluation.tenant_id
                )
                & (
                    DecisionEffectivenessAssessment.id
                    == DecisionLessonEvaluation.effectiveness_assessment_id
                ),
            )
            .where(
                DecisionLessonEvaluation.tenant_id == tenant_id,
                DecisionLessonEvaluation.superseded_at.is_(None),
                DecisionLessonAdoption.historical_lesson_id == source_lesson_id,
                DecisionLessonAdoption.superseded_at.is_(None),
                DecisionEffectivenessAssessment.status == "completed",
            )
            .order_by(DecisionLessonEvaluation.evaluated_at.desc())
        ).all()

    def outcomes(self, tenant_id, decision_id, ids):
        if not ids:
            return []
        return list(
            self._db.scalars(
                select(DecisionExpectedOutcome).where(
                    DecisionExpectedOutcome.tenant_id == tenant_id,
                    DecisionExpectedOutcome.decision_case_id == decision_id,
                    DecisionExpectedOutcome.id.in_(ids),
                )
            ).all()
        )

    def proposals(self, tenant_id, lesson_id):
        return list(
            self._db.scalars(
                select(DecisionLessonPromotionProposal)
                .where(
                    DecisionLessonPromotionProposal.tenant_id == tenant_id,
                    DecisionLessonPromotionProposal.source_lesson_id == lesson_id,
                )
                .order_by(DecisionLessonPromotionProposal.proposed_at.desc())
            ).all()
        )

    def proposal(
        self, tenant_id, decision_id, lesson_id, proposal_id, for_update=False
    ):
        statement = select(DecisionLessonPromotionProposal).where(
            DecisionLessonPromotionProposal.tenant_id == tenant_id,
            DecisionLessonPromotionProposal.source_decision_id == decision_id,
            DecisionLessonPromotionProposal.source_lesson_id == lesson_id,
            DecisionLessonPromotionProposal.id == proposal_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def save(self, objects, events, refresh):
        try:
            self._db.add_all([*objects, *events])
            cards = [item for item in objects if isinstance(item, KnowledgeCard)]
            if cards:
                # Materialize the new card before updating the proposal's
                # tenant-composite resulting-card foreign key.
                self._db.flush(cards)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(refresh)
        return refresh

    def provenance(self, tenant_id, card_id, clearance_rank, role_ids):
        return self._db.scalar(
            select(KnowledgeCardLessonProvenance)
            .join(
                KnowledgeCard,
                (KnowledgeCard.tenant_id == KnowledgeCardLessonProvenance.tenant_id)
                & (KnowledgeCard.id == KnowledgeCardLessonProvenance.knowledge_card_id),
            )
            .where(
                KnowledgeCardLessonProvenance.tenant_id == tenant_id,
                KnowledgeCardLessonProvenance.knowledge_card_id == card_id,
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank, role_ids=role_ids
                ),
            )
        )
