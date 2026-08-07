from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SimilarityComponentResponse(BaseModel):
    score: float
    weight: float
    weighted_points: float
    available: bool
    explanation: str


class HistoricalDecisionSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    business_concept_id: str | None
    business_concept_name: str | None
    final_status: str
    approval_result: str | None
    effectiveness_classification: str | None
    evidence_count: int | None
    evidence_types: list[str] | None
    material_conditions: list[str] | None
    material_findings: list[str] | None
    lessons: list[str] | None


class PrecedentResultResponse(BaseModel):
    historical_decision: HistoricalDecisionSummary
    overall_similarity: float
    relevance: str
    algorithm_version: str
    similarity_components: dict[str, SimilarityComponentResponse]
    shared_characteristics: list[str]
    different_characteristics: list[str]
    observed_usage: dict | None = None


class PrecedentListResponse(BaseModel):
    current_decision_id: str
    algorithm_version: str
    items: list[PrecedentResultResponse]
    considered_count: int
    returned_count: int


class DecisionComparisonResponse(BaseModel):
    current_decision: dict
    historical_decision: HistoricalDecisionSummary
    overall_similarity: float
    relevance: str
    algorithm_version: str
    similarity_components: dict[str, SimilarityComponentResponse]
    shared_characteristics: list[str]
    different_characteristics: list[str]
    historical_governance: dict | None
    historical_outcome: dict | None
    historical_lessons: list[dict] | None
    observed_usage: dict | None = None
