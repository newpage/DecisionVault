from __future__ import annotations

from app.modules.business_concepts.repository import BusinessConceptRepository
from app.modules.business_concepts.schemas import BusinessConceptSummary


class BusinessConceptService:
    """Application operations for the business knowledge model."""

    def __init__(self, repository: BusinessConceptRepository) -> None:
        self._repository = repository

    def list_concepts(
        self,
        *,
        tenant_id: str,
        query: str = "",
    ) -> list[BusinessConceptSummary]:
        rows = self._repository.list_with_knowledge_counts(
            tenant_id=tenant_id,
            query=query,
        )
        return [
            BusinessConceptSummary.model_validate(
                {
                    "id": concept.id,
                    "name": concept.name,
                    "slug": concept.slug,
                    "description": concept.description,
                    "category": concept.category,
                    "icon": concept.icon,
                    "color": concept.color,
                    "status": concept.status,
                    "knowledge_count": knowledge_count,
                    "updated_at": concept.updated_at,
                }
            )
            for concept, knowledge_count in rows
        ]
