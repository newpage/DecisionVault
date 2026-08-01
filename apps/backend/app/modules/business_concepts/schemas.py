from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BusinessConceptSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    category: str
    icon: str
    color: str
    status: str
    knowledge_count: int
    updated_at: datetime


class ConceptMetric(BaseModel):
    key: str
    label: str
    value: int
    source: Literal["calculated", "demo"]
    status: Literal["good", "watch", "attention"]


class ConceptInsight(BaseModel):
    summary: str
    confidence: int
    source: Literal["curated", "ai"] = "curated"
    generated_at: datetime


class ConceptKnowledgeItem(BaseModel):
    id: str
    title: str
    summary: str
    lifecycle_status: str
    approval_status: str
    trust_score: float
    updated_at: datetime


class ConceptActivityItem(BaseModel):
    id: str
    event_type: str
    description: str
    created_at: datetime


class RelatedConcept(BaseModel):
    id: str
    name: str
    slug: str
    category: str
    icon: str
    color: str


class BusinessConceptWorkspace(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    category: str
    icon: str
    color: str
    status: str
    updated_at: datetime
    insight: ConceptInsight
    metrics: list[ConceptMetric]
    knowledge: list[ConceptKnowledgeItem]
    activity: list[ConceptActivityItem]
    related_concepts: list[RelatedConcept]
