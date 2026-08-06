from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import (
    AccessPolicyRole,
    BusinessConcept,
    DecisionApprovalAction,
    DecisionApprovalCondition,
    DecisionCase,
    DecisionEffectivenessAssessment,
    DecisionEvidence,
    DecisionExpectedOutcome,
    DecisionLesson,
    DecisionReview,
    DecisionReviewFinding,
)
from app.modules.decisions.memory import DecisionMemoryProfile


HISTORICAL_STATUSES = frozenset({"conditionally_approved", "approved", "rejected", "closed"})


class DecisionMemoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_decision(self, *, tenant_id: str, decision_id: str, clearance_rank: int, role_ids: set[str]) -> DecisionCase | None:
        return self._db.scalar(select(DecisionCase).where(DecisionCase.tenant_id == tenant_id, DecisionCase.id == decision_id, *self._decision_access(clearance_rank, role_ids)))

    def list_candidates(self, *, tenant_id: str, current_decision_id: str, clearance_rank: int, role_ids: set[str], date_from: date | None = None, date_to: date | None = None, business_concept_id: str | None = None) -> list[DecisionCase]:
        statement = select(DecisionCase).where(
            DecisionCase.tenant_id == tenant_id,
            DecisionCase.id != current_decision_id,
            DecisionCase.status.in_(HISTORICAL_STATUSES),
            *self._decision_access(clearance_rank, role_ids),
        )
        if date_from:
            statement = statement.where(DecisionCase.created_at >= date_from)
        if date_to:
            statement = statement.where(
                DecisionCase.created_at
                <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
            )
        if business_concept_id:
            statement = statement.where(DecisionCase.business_concept_id == business_concept_id)
        return list(self._db.scalars(statement.order_by(DecisionCase.created_at.desc())).all())

    def get_historical_decision(self, *, tenant_id: str, current_decision_id: str, historical_decision_id: str, clearance_rank: int, role_ids: set[str]) -> DecisionCase | None:
        return self._db.scalar(select(DecisionCase).where(DecisionCase.tenant_id == tenant_id, DecisionCase.id == historical_decision_id, DecisionCase.id != current_decision_id, DecisionCase.status.in_(HISTORICAL_STATUSES), *self._decision_access(clearance_rank, role_ids)))

    def concept_name(self, *, tenant_id: str, concept_id: str | None) -> str | None:
        if concept_id is None:
            return None
        return self._db.scalar(select(BusinessConcept.name).where(BusinessConcept.tenant_id == tenant_id, BusinessConcept.id == concept_id))

    def profile(self, decision: DecisionCase, *, clearance_rank: int, role_ids: set[str], include_evidence: bool, include_governance: bool, include_outcomes: bool) -> DecisionMemoryProfile:
        evidence = self._authorized_evidence(decision.tenant_id, decision.id, clearance_rank, role_ids) if include_evidence else None
        reviews = self._reviews(decision.tenant_id, decision.id) if include_governance else None
        outcomes = self._outcomes(decision.tenant_id, decision.id) if include_outcomes else None
        assessment = self._latest_assessment(decision.tenant_id, decision.id) if include_outcomes else None
        lessons = self._lessons(decision.tenant_id, decision.id) if include_outcomes else None
        approvals = self._approvals(decision.tenant_id, decision.id) if include_governance else None
        conditions = self._conditions(decision.tenant_id, decision.id) if include_governance else None
        findings = self._findings(decision.tenant_id, decision.id) if include_governance else None
        return DecisionMemoryProfile(
            decision_id=decision.id,
            business_concept_id=decision.business_concept_id,
            workspace_id=decision.workspace_id,
            title=decision.title,
            question=decision.question,
            decision_type=decision.decision_type,
            business_unit=decision.business_unit,
            supplier_category=decision.supplier_category,
            risk_level=decision.risk_level,
            created_at=decision.created_at,
            evidence_types=frozenset(item.snapshot_knowledge_type for item in evidence) if evidence is not None else None,
            evidence_authorities=frozenset(item.snapshot_authority_level for item in evidence) if evidence is not None else None,
            evidence_relationships=frozenset(item.relationship_type for item in evidence) if evidence is not None else None,
            review_types=frozenset(item.review_type for item in reviews) if reviews is not None else None,
            finding_types=frozenset(item.finding_type for item in findings) if findings is not None else None,
            approval_actions=frozenset(item.action for item in approvals) if approvals is not None else None,
            condition_statuses=frozenset(item.status for item in conditions) if conditions is not None else None,
            outcome_categories=frozenset(item.category for item in outcomes) if outcomes is not None else None,
            outcome_measurements=frozenset(item.measurement_type for item in outcomes) if outcomes is not None else None,
            effectiveness_classification=assessment.classification if assessment else None,
            lesson_types=frozenset(item.lesson_type for item in lessons) if lessons is not None else None,
        )

    def authorized_evidence(self, *, tenant_id: str, decision_id: str, clearance_rank: int, role_ids: set[str]) -> list[DecisionEvidence]:
        return self._authorized_evidence(tenant_id, decision_id, clearance_rank, role_ids)

    def reviews(self, *, tenant_id: str, decision_id: str):
        return self._reviews(tenant_id, decision_id)

    def findings(self, *, tenant_id: str, decision_id: str):
        return self._findings(tenant_id, decision_id)

    def approvals(self, *, tenant_id: str, decision_id: str):
        return self._approvals(tenant_id, decision_id)

    def conditions(self, *, tenant_id: str, decision_id: str):
        return self._conditions(tenant_id, decision_id)

    def outcomes(self, *, tenant_id: str, decision_id: str):
        return self._outcomes(tenant_id, decision_id)

    def latest_assessment(self, *, tenant_id: str, decision_id: str):
        return self._latest_assessment(tenant_id, decision_id)

    def lessons(self, *, tenant_id: str, decision_id: str):
        return self._lessons(tenant_id, decision_id)

    def _authorized_evidence(self, tenant_id: str, decision_id: str, clearance_rank: int, role_ids: set[str]):
        policy_allowed = exists(select(AccessPolicyRole.policy_id).where(AccessPolicyRole.policy_id == DecisionEvidence.snapshot_access_policy_id, AccessPolicyRole.role_id.in_(role_ids))) if role_ids else False
        return list(self._db.scalars(select(DecisionEvidence).where(
            DecisionEvidence.tenant_id == tenant_id,
            DecisionEvidence.decision_case_id == decision_id,
            DecisionEvidence.removed_at.is_(None),
            DecisionEvidence.snapshot_classification_rank <= clearance_rank,
            (DecisionEvidence.snapshot_access_policy_id.is_(None) | policy_allowed),
        )).all())

    def _reviews(self, tenant_id, decision_id):
        return list(self._db.scalars(select(DecisionReview).where(DecisionReview.tenant_id == tenant_id, DecisionReview.decision_case_id == decision_id)).all())

    def _findings(self, tenant_id, decision_id):
        return list(self._db.scalars(select(DecisionReviewFinding).join(DecisionReview, (DecisionReview.tenant_id == tenant_id) & (DecisionReview.id == DecisionReviewFinding.review_id)).where(DecisionReviewFinding.tenant_id == tenant_id, DecisionReview.decision_case_id == decision_id)).all())

    def _approvals(self, tenant_id, decision_id):
        return list(
            self._db.scalars(
                select(DecisionApprovalAction)
                .where(
                    DecisionApprovalAction.tenant_id == tenant_id,
                    DecisionApprovalAction.decision_case_id == decision_id,
                )
                .order_by(DecisionApprovalAction.created_at)
            ).all()
        )

    def _conditions(self, tenant_id, decision_id):
        return list(self._db.scalars(select(DecisionApprovalCondition).where(DecisionApprovalCondition.tenant_id == tenant_id, DecisionApprovalCondition.decision_case_id == decision_id)).all())

    def _outcomes(self, tenant_id, decision_id):
        return list(self._db.scalars(select(DecisionExpectedOutcome).where(DecisionExpectedOutcome.tenant_id == tenant_id, DecisionExpectedOutcome.decision_case_id == decision_id, DecisionExpectedOutcome.status == "active")).all())

    def _latest_assessment(self, tenant_id, decision_id):
        return self._db.scalar(select(DecisionEffectivenessAssessment).where(DecisionEffectivenessAssessment.tenant_id == tenant_id, DecisionEffectivenessAssessment.decision_case_id == decision_id, DecisionEffectivenessAssessment.status == "completed").order_by(DecisionEffectivenessAssessment.revision.desc()).limit(1))

    def _lessons(self, tenant_id, decision_id):
        return list(self._db.scalars(select(DecisionLesson).where(DecisionLesson.tenant_id == tenant_id, DecisionLesson.decision_case_id == decision_id).order_by(DecisionLesson.created_at.desc())).all())

    @staticmethod
    def _decision_access(clearance_rank: int, role_ids: set[str]):
        policy_allowed = exists(
            select(AccessPolicyRole.policy_id).where(
                AccessPolicyRole.policy_id == DecisionCase.access_policy_id,
                AccessPolicyRole.role_id.in_(role_ids),
            )
        ) if role_ids else False
        return (
            DecisionCase.classification_rank <= clearance_rank,
            DecisionCase.access_policy_id.is_(None) | policy_allowed,
        )
