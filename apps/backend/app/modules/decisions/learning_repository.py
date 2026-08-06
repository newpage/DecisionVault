from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DecisionEffectivenessAssessment,
    DecisionLessonAdoption,
    DecisionLessonEvaluation,
    DecisionPrecedentEvaluation,
    DecisionPrecedentReference,
    Membership,
    utcnow,
)


class DecisionLearningRepository:
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

    def assessment(self, tenant_id, decision_id, assessment_id):
        return self._db.scalar(
            select(DecisionEffectivenessAssessment).where(
                DecisionEffectivenessAssessment.tenant_id == tenant_id,
                DecisionEffectivenessAssessment.decision_case_id == decision_id,
                DecisionEffectivenessAssessment.id == assessment_id,
                DecisionEffectivenessAssessment.status == "completed",
            )
        )

    def precedent(self, tenant_id, decision_id, reference_id):
        return self._db.scalar(
            select(DecisionPrecedentReference).where(
                DecisionPrecedentReference.tenant_id == tenant_id,
                DecisionPrecedentReference.decision_case_id == decision_id,
                DecisionPrecedentReference.id == reference_id,
            )
        )

    def adoption(self, tenant_id, decision_id, adoption_id):
        return self._db.scalar(
            select(DecisionLessonAdoption).where(
                DecisionLessonAdoption.tenant_id == tenant_id,
                DecisionLessonAdoption.decision_case_id == decision_id,
                DecisionLessonAdoption.id == adoption_id,
            )
        )

    def precedent_evaluation(self, tenant_id, decision_id, reference_id, active=True):
        statement = select(DecisionPrecedentEvaluation).where(
            DecisionPrecedentEvaluation.tenant_id == tenant_id,
            DecisionPrecedentEvaluation.decision_case_id == decision_id,
            DecisionPrecedentEvaluation.precedent_reference_id == reference_id,
        )
        if active:
            statement = statement.where(
                DecisionPrecedentEvaluation.superseded_at.is_(None)
            )
        return self._db.scalar(
            statement.order_by(DecisionPrecedentEvaluation.evaluated_at.desc())
        )

    def lesson_evaluation(self, tenant_id, decision_id, adoption_id, active=True):
        statement = select(DecisionLessonEvaluation).where(
            DecisionLessonEvaluation.tenant_id == tenant_id,
            DecisionLessonEvaluation.decision_case_id == decision_id,
            DecisionLessonEvaluation.lesson_adoption_id == adoption_id,
        )
        if active:
            statement = statement.where(
                DecisionLessonEvaluation.superseded_at.is_(None)
            )
        return self._db.scalar(
            statement.order_by(DecisionLessonEvaluation.evaluated_at.desc())
        )

    def list_precedent_evaluations(self, tenant_id, decision_id):
        return list(
            self._db.scalars(
                select(DecisionPrecedentEvaluation)
                .where(
                    DecisionPrecedentEvaluation.tenant_id == tenant_id,
                    DecisionPrecedentEvaluation.decision_case_id == decision_id,
                )
                .order_by(DecisionPrecedentEvaluation.evaluated_at.desc())
            ).all()
        )

    def list_lesson_evaluations(self, tenant_id, decision_id):
        return list(
            self._db.scalars(
                select(DecisionLessonEvaluation)
                .where(
                    DecisionLessonEvaluation.tenant_id == tenant_id,
                    DecisionLessonEvaluation.decision_case_id == decision_id,
                )
                .order_by(DecisionLessonEvaluation.evaluated_at.desc())
            ).all()
        )

    def references_to(self, tenant_id, historical_id):
        return list(
            self._db.scalars(
                select(DecisionPrecedentReference).where(
                    DecisionPrecedentReference.tenant_id == tenant_id,
                    DecisionPrecedentReference.historical_decision_id == historical_id,
                    DecisionPrecedentReference.removed_at.is_(None),
                )
            ).all()
        )

    def save(self, record, event):
        try:
            self._db.add(record)
            self._db.flush()
            self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(record)
        return record

    def supersede(self, old, replacement, event, membership_id, rationale):
        try:
            old.superseded_by_evaluation_id = replacement.id
            old.superseded_by_membership_id = membership_id
            old.superseded_at = utcnow()
            old.supersession_rationale = rationale
            self._db.add_all([old, replacement])
            self._db.flush()
            self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(replacement)
        return replacement
