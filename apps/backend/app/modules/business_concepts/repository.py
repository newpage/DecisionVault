from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, BusinessConcept, KnowledgeCard


class BusinessConceptRepository:
    """Tenant-aware persistence for Business Concepts."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_with_knowledge_counts(
        self,
        *,
        tenant_id: str,
        query: str = "",
    ) -> list[tuple[BusinessConcept, int]]:
        statement = (
            select(BusinessConcept, func.count(KnowledgeCard.id))
            .outerjoin(
                KnowledgeCard,
                (KnowledgeCard.business_concept_id == BusinessConcept.id)
                & (KnowledgeCard.tenant_id == tenant_id),
            )
            .where(BusinessConcept.tenant_id == tenant_id)
            .group_by(BusinessConcept.id)
            .order_by(BusinessConcept.category, BusinessConcept.name)
        )
        normalized_query = query.strip()
        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                BusinessConcept.name.ilike(pattern)
                | BusinessConcept.description.ilike(pattern)
                | BusinessConcept.category.ilike(pattern)
            )
        rows = self._db.execute(statement).all()
        return [(row[0], int(row[1])) for row in rows]

    def get_concept(
        self,
        *,
        tenant_id: str,
        concept_id: str,
    ) -> BusinessConcept | None:
        return self._db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.id == concept_id,
                BusinessConcept.tenant_id == tenant_id,
            )
        )

    def list_knowledge(
        self,
        *,
        tenant_id: str,
        concept_id: str,
        limit: int = 12,
    ) -> list[KnowledgeCard]:
        statement = (
            select(KnowledgeCard)
            .where(
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.business_concept_id == concept_id,
            )
            .order_by(KnowledgeCard.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(statement).all())

    def list_activity(
        self,
        *,
        tenant_id: str,
        knowledge_ids: list[str],
        limit: int = 10,
    ) -> list[AuditEvent]:
        if not knowledge_ids:
            return []
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.entity_type == "knowledge_card",
                AuditEvent.entity_id.in_(knowledge_ids),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(statement).all())

    def list_related(
        self,
        *,
        tenant_id: str,
        concept: BusinessConcept,
        limit: int = 4,
    ) -> list[BusinessConcept]:
        statement = (
            select(BusinessConcept)
            .where(
                BusinessConcept.tenant_id == tenant_id,
                BusinessConcept.id != concept.id,
            )
            .order_by(
                (BusinessConcept.category == concept.category).desc(),
                BusinessConcept.name,
            )
            .limit(limit)
        )
        return list(self._db.scalars(statement).all())
