from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BusinessConcept, KnowledgeCard


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
