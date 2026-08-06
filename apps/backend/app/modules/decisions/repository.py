from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    KnowledgeCard,
    Workspace,
)
from app.modules.knowledge.policies import authorized_knowledge_filters


class DecisionRepository:
    """Tenant-aware persistence for Decision Intelligence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_decisions(self, *, tenant_id: str) -> list[DecisionCase]:
        return list(
            self._db.scalars(
                select(DecisionCase)
                .where(DecisionCase.tenant_id == tenant_id)
                .order_by(DecisionCase.created_at.desc())
            ).all()
        )

    def get_decision(
        self, *, tenant_id: str, decision_id: str
    ) -> DecisionCase | None:
        return self._db.scalar(
            select(DecisionCase).where(
                DecisionCase.id == decision_id,
                DecisionCase.tenant_id == tenant_id,
            )
        )

    def get_workspace(
        self, *, tenant_id: str, workspace_id: str
    ) -> Workspace | None:
        return self._db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == tenant_id,
            )
        )

    def get_concept(
        self, *, tenant_id: str, concept_id: str
    ) -> BusinessConcept | None:
        return self._db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.id == concept_id,
                BusinessConcept.tenant_id == tenant_id,
            )
        )

    def get_default_concept(self, *, tenant_id: str) -> BusinessConcept | None:
        return self._db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.tenant_id == tenant_id,
                BusinessConcept.slug == "supplier-qualification",
            )
        )

    def list_authorized_evidence(
        self,
        *,
        tenant_id: str,
        concept_id: str,
        workspace_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> list[KnowledgeCard]:
        statement = (
            select(KnowledgeCard)
            .where(
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.workspace_id == workspace_id,
                KnowledgeCard.business_concept_id == concept_id,
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank,
                    role_ids=role_ids,
                ),
            )
            .order_by(
                KnowledgeCard.approval_status.desc(),
                KnowledgeCard.trust_score.desc(),
                KnowledgeCard.created_at.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def list_activity(
        self, *, tenant_id: str, decision_id: str, limit: int = 25
    ) -> list[AuditEvent]:
        return list(
            self._db.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.entity_type == "decision_case",
                    AuditEvent.entity_id == decision_id,
                )
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            ).all()
        )

    def save_with_audit(
        self, *, decision: DecisionCase, event: AuditEvent
    ) -> DecisionCase:
        try:
            self._db.add(decision)
            self._db.flush()
            event.entity_id = decision.id
            self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(decision)
        return decision
