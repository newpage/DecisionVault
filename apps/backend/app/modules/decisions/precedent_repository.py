from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    DecisionCase,
    DecisionLesson,
    DecisionLessonAdoption,
    DecisionPrecedentReference,
    DecisionReview,
    Membership,
)


class DecisionPrecedentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def decision_for_update(self, *, tenant_id: str, decision_id: str):
        return self._db.scalar(
            select(DecisionCase)
            .where(DecisionCase.tenant_id == tenant_id, DecisionCase.id == decision_id)
            .with_for_update()
        )

    def active_membership(self, *, tenant_id: str, membership_id: str):
        return self._db.scalar(
            select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.id == membership_id,
                Membership.is_active.is_(True),
            )
        )

    def lesson(self, *, tenant_id: str, historical_decision_id: str, lesson_id: str):
        return self._db.scalar(
            select(DecisionLesson).where(
                DecisionLesson.tenant_id == tenant_id,
                DecisionLesson.decision_case_id == historical_decision_id,
                DecisionLesson.id == lesson_id,
            )
        )

    def list_precedents(
        self, *, tenant_id: str, decision_id: str, history: bool = False
    ):
        statement = select(DecisionPrecedentReference).where(
            DecisionPrecedentReference.tenant_id == tenant_id,
            DecisionPrecedentReference.decision_case_id == decision_id,
        )
        if not history:
            statement = statement.where(DecisionPrecedentReference.removed_at.is_(None))
        return list(
            self._db.scalars(
                statement.order_by(DecisionPrecedentReference.referenced_at.desc())
            ).all()
        )

    def precedent(self, *, tenant_id: str, decision_id: str, precedent_id: str):
        return self._db.scalar(
            select(DecisionPrecedentReference).where(
                DecisionPrecedentReference.tenant_id == tenant_id,
                DecisionPrecedentReference.decision_case_id == decision_id,
                DecisionPrecedentReference.id == precedent_id,
            )
        )

    def list_adoptions(self, *, tenant_id: str, decision_id: str):
        return list(
            self._db.scalars(
                select(DecisionLessonAdoption)
                .where(
                    DecisionLessonAdoption.tenant_id == tenant_id,
                    DecisionLessonAdoption.decision_case_id == decision_id,
                )
                .order_by(DecisionLessonAdoption.acted_at.desc())
            ).all()
        )

    def adoption(self, *, tenant_id: str, decision_id: str, adoption_id: str):
        return self._db.scalar(
            select(DecisionLessonAdoption).where(
                DecisionLessonAdoption.tenant_id == tenant_id,
                DecisionLessonAdoption.decision_case_id == decision_id,
                DecisionLessonAdoption.id == adoption_id,
                DecisionLessonAdoption.superseded_at.is_(None),
            )
        )

    def mark_reviews_stale(self, *, tenant_id: str, decision_id: str):
        reviews = list(
            self._db.scalars(
                select(DecisionReview).where(
                    DecisionReview.tenant_id == tenant_id,
                    DecisionReview.decision_case_id == decision_id,
                    DecisionReview.status == "completed",
                    DecisionReview.freshness_status == "current",
                )
            ).all()
        )
        for review in reviews:
            review.freshness_status = "stale"
        return reviews

    def save(self, *, objects: list, events: list[AuditEvent], refresh):
        try:
            self._db.add_all(objects)
            self._db.flush()
            self._db.add_all(events)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(refresh)
        return refresh
