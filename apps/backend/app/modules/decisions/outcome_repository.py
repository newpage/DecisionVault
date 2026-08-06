from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    DecisionEffectivenessAssessment,
    DecisionExpectedOutcome,
    DecisionLesson,
    DecisionOutcomeObservation,
    Membership,
)


class DecisionOutcomeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active_membership(
        self, *, tenant_id: str, membership_id: str
    ) -> Membership | None:
        return self._db.scalar(
            select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.id == membership_id,
                Membership.is_active.is_(True),
            )
        )

    def list_outcomes(
        self, *, tenant_id: str, decision_id: str, include_history: bool = False
    ) -> list[DecisionExpectedOutcome]:
        statement = select(DecisionExpectedOutcome).where(
            DecisionExpectedOutcome.tenant_id == tenant_id,
            DecisionExpectedOutcome.decision_case_id == decision_id,
        )
        if not include_history:
            statement = statement.where(DecisionExpectedOutcome.status == "active")
        return list(
            self._db.scalars(
                statement.order_by(DecisionExpectedOutcome.created_at)
            ).all()
        )

    def get_outcome(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        for_update: bool = False,
    ) -> DecisionExpectedOutcome | None:
        statement = select(DecisionExpectedOutcome).where(
            DecisionExpectedOutcome.tenant_id == tenant_id,
            DecisionExpectedOutcome.decision_case_id == decision_id,
            DecisionExpectedOutcome.id == outcome_id,
        )
        return self._db.scalar(statement.with_for_update() if for_update else statement)

    def list_observations(
        self, *, tenant_id: str, decision_id: str, outcome_id: str | None = None
    ) -> list[DecisionOutcomeObservation]:
        statement = select(DecisionOutcomeObservation).where(
            DecisionOutcomeObservation.tenant_id == tenant_id,
            DecisionOutcomeObservation.decision_case_id == decision_id,
        )
        if outcome_id:
            statement = statement.where(
                DecisionOutcomeObservation.expected_outcome_id == outcome_id
            )
        return list(
            self._db.scalars(
                statement.order_by(
                    DecisionOutcomeObservation.observation_date.desc(),
                    DecisionOutcomeObservation.recorded_at.desc(),
                )
            ).all()
        )

    def get_observation(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        observation_id: str,
        for_update: bool = False,
    ) -> DecisionOutcomeObservation | None:
        statement = select(DecisionOutcomeObservation).where(
            DecisionOutcomeObservation.tenant_id == tenant_id,
            DecisionOutcomeObservation.decision_case_id == decision_id,
            DecisionOutcomeObservation.expected_outcome_id == outcome_id,
            DecisionOutcomeObservation.id == observation_id,
        )
        return self._db.scalar(statement.with_for_update() if for_update else statement)

    def list_assessments(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionEffectivenessAssessment]:
        return list(
            self._db.scalars(
                select(DecisionEffectivenessAssessment)
                .where(
                    DecisionEffectivenessAssessment.tenant_id == tenant_id,
                    DecisionEffectivenessAssessment.decision_case_id == decision_id,
                )
                .order_by(DecisionEffectivenessAssessment.revision.desc())
            ).all()
        )

    def get_assessment(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        assessment_id: str,
        for_update: bool = False,
    ) -> DecisionEffectivenessAssessment | None:
        statement = select(DecisionEffectivenessAssessment).where(
            DecisionEffectivenessAssessment.tenant_id == tenant_id,
            DecisionEffectivenessAssessment.decision_case_id == decision_id,
            DecisionEffectivenessAssessment.id == assessment_id,
        )
        return self._db.scalar(statement.with_for_update() if for_update else statement)

    def next_assessment_revision(self, *, tenant_id: str, decision_id: str) -> int:
        return (
            int(
                self._db.scalar(
                    select(func.max(DecisionEffectivenessAssessment.revision)).where(
                        DecisionEffectivenessAssessment.tenant_id == tenant_id,
                        DecisionEffectivenessAssessment.decision_case_id == decision_id,
                    )
                )
                or 0
            )
            + 1
        )

    def list_lessons(self, *, tenant_id: str, decision_id: str) -> list[DecisionLesson]:
        return list(
            self._db.scalars(
                select(DecisionLesson)
                .where(
                    DecisionLesson.tenant_id == tenant_id,
                    DecisionLesson.decision_case_id == decision_id,
                )
                .order_by(DecisionLesson.created_at.desc())
            ).all()
        )

    def save(
        self, *, objects: list, events: list[AuditEvent], refresh: list | None = None
    ) -> None:
        try:
            self._db.add_all(objects)
            self._db.flush()
            self._db.add_all(events)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        for item in refresh or []:
            self._db.refresh(item)
