from __future__ import annotations

from datetime import datetime, timezone

from app.modules.business_concepts.repository import BusinessConceptRepository
from app.modules.business_concepts.schemas import (
    BusinessConceptSummary,
    BusinessConceptWorkspace,
    ConceptActivityItem,
    ConceptInsight,
    ConceptKnowledgeItem,
    ConceptMetric,
    RelatedConcept,
)


class BusinessConceptNotFoundError(LookupError):
    """Raised when a tenant cannot access the requested concept."""


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

    def get_workspace(
        self,
        *,
        tenant_id: str,
        concept_id: str,
    ) -> BusinessConceptWorkspace:
        concept = self._repository.get_concept(
            tenant_id=tenant_id,
            concept_id=concept_id,
        )
        if concept is None:
            raise BusinessConceptNotFoundError("Business Concept not found")

        knowledge = self._repository.list_knowledge(
            tenant_id=tenant_id,
            concept_id=concept.id,
        )
        activity = self._repository.list_activity(
            tenant_id=tenant_id,
            knowledge_ids=[card.id for card in knowledge],
        )
        related = self._repository.list_related(
            tenant_id=tenant_id,
            concept=concept,
        )

        approved_count = sum(
            1 for card in knowledge if card.approval_status == "approved"
        )
        trusted_count = sum(1 for card in knowledge if card.trust_score >= 0.8)
        readiness = (
            round((approved_count / len(knowledge)) * 100)
            if knowledge
            else 0
        )
        knowledge_health = (
            round((trusted_count / len(knowledge)) * 100)
            if knowledge
            else 0
        )

        return BusinessConceptWorkspace(
            id=concept.id,
            name=concept.name,
            slug=concept.slug,
            description=concept.description,
            category=concept.category,
            icon=concept.icon,
            color=concept.color,
            status=concept.status,
            updated_at=concept.updated_at,
            insight=ConceptInsight(
                summary=(
                    f"{concept.name} brings together trusted knowledge, "
                    f"evidence, governance activity, and related business "
                    f"context so teams can make consistent decisions. "
                    f"{concept.description}"
                ),
                confidence=max(72, knowledge_health),
                generated_at=datetime.now(timezone.utc),
            ),
            metrics=[
                ConceptMetric(
                    key="knowledge",
                    label="Knowledge Cards",
                    value=len(knowledge),
                    source="calculated",
                    status="good" if knowledge else "attention",
                ),
                ConceptMetric(
                    key="readiness",
                    label="Decision Readiness",
                    value=readiness,
                    source="calculated",
                    status=(
                        "good"
                        if readiness >= 80
                        else "watch"
                        if readiness >= 50
                        else "attention"
                    ),
                ),
                ConceptMetric(
                    key="health",
                    label="Knowledge Health",
                    value=knowledge_health,
                    source="calculated",
                    status=(
                        "good"
                        if knowledge_health >= 80
                        else "watch"
                        if knowledge_health >= 50
                        else "attention"
                    ),
                ),
                ConceptMetric(
                    key="relationships",
                    label="Related Concepts",
                    value=len(related),
                    source="calculated",
                    status="good",
                ),
            ],
            knowledge=[
                ConceptKnowledgeItem(
                    id=card.id,
                    title=card.title,
                    summary=card.summary,
                    lifecycle_status=card.lifecycle_status,
                    approval_status=card.approval_status,
                    trust_score=card.trust_score,
                    updated_at=card.created_at,
                )
                for card in knowledge
            ],
            activity=[
                ConceptActivityItem(
                    id=event.id,
                    event_type=event.event_type,
                    description=event.description,
                    created_at=event.created_at,
                )
                for event in activity
            ],
            related_concepts=[
                RelatedConcept(
                    id=item.id,
                    name=item.name,
                    slug=item.slug,
                    category=item.category,
                    icon=item.icon,
                    color=item.color,
                )
                for item in related
            ],
        )
