from datetime import datetime
from typing import Literal

from pydantic import BaseModel


MetricStatus = Literal["good", "watch", "attention"]
FindingSeverity = Literal["high", "medium", "low"]
FindingType = Literal[
    "missing_knowledge",
    "pending_approval",
    "low_trust",
    "stale_knowledge",
    "ai_restricted",
]


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


class ScoreFactor(BaseModel):
    key: str
    label: str
    achieved: int
    possible: int
    explanation: str


class ScoreExplanation(BaseModel):
    label: str
    score: int
    rating: Literal["strong", "developing", "needs_attention"]
    formula: str
    factors: list[ScoreFactor]


class ConceptMetric(BaseModel):
    key: str
    label: str
    value: int
    source: Literal["calculated", "demo"]
    status: MetricStatus
    explanation: str


class ConceptFinding(BaseModel):
    id: str
    finding_type: FindingType
    severity: FindingSeverity
    title: str
    description: str
    recommended_action: str
    affected_count: int


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
    ai_usage_allowed: bool
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
    score_explanation: ScoreExplanation
    findings: list[ConceptFinding]
    knowledge: list[ConceptKnowledgeItem]
    activity: list[ConceptActivityItem]
    related_concepts: list[RelatedConcept]
