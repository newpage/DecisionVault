from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PrecedentEvaluationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    effectiveness_assessment_id: str
    classification: Literal[
        "highly_useful",
        "useful",
        "neutral",
        "misleading",
        "harmful",
        "inconclusive",
        "too_early",
    ]
    rationale: str = Field(min_length=3)
    outcome_alignment_details: dict = Field(default_factory=dict)


class LessonEvaluationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    effectiveness_assessment_id: str
    classification: Literal[
        "beneficial",
        "neutral",
        "ineffective",
        "harmful",
        "not_applied",
        "inconclusive",
        "appropriate_rejection",
        "potentially_costly_rejection",
    ]
    rationale: str = Field(min_length=3)
    was_applied: bool | None = None
    relevant_outcome_ids: list[str] = Field(default_factory=list)
    outcome_relevance_details: dict = Field(default_factory=dict)


class EvaluationSupersede(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    supersession_rationale: str = Field(min_length=3)
    classification: str
    rationale: str = Field(min_length=3)


class PrecedentEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    precedent_reference_id: str
    historical_decision_id: str
    effectiveness_assessment_id: str
    classification: str
    rationale: str
    evaluator_membership_id: str
    evaluated_at: datetime
    similarity_score_snapshot: float
    historical_effectiveness_snapshot: str | None
    current_effectiveness_snapshot: str
    outcome_alignment_details: dict
    superseded_at: datetime | None
    supersession_rationale: str | None


class LessonEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lesson_adoption_id: str
    historical_decision_id: str
    effectiveness_assessment_id: str
    classification: str
    rationale: str
    was_applied: bool | None
    relevant_outcome_ids: list
    evaluator_membership_id: str
    evaluated_at: datetime
    current_effectiveness_snapshot: str
    outcome_relevance_details: dict
    superseded_at: datetime | None
    supersession_rationale: str | None


class DecisionLearningResponse(BaseModel):
    precedent_evaluations: list[PrecedentEvaluationResponse]
    lesson_evaluations: list[LessonEvaluationResponse]


class HistoricalUsageResponse(BaseModel):
    historical_decision_id: str
    referenced_count: int
    evaluated_count: int
    classification_counts: dict[str, int]
    current_outcome_distribution: dict[str, int]


class LessonUsageResponse(BaseModel):
    historical_lesson_id: str
    adopted_count: int
    rejected_count: int
    evaluated_count: int
    classification_counts: dict[str, int]
