from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RelationshipType = Literal[
    "supporting", "cautionary", "analogous", "exception", "contrary"
]
AdoptionStatus = Literal["adopted", "rejected"]


class PrecedentAttach(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    historical_decision_id: str
    relationship_type: RelationshipType
    rationale: str = Field(min_length=3)


class PrecedentRemove(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    rationale: str = Field(min_length=3)


class PrecedentReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    historical_decision_id: str
    relationship_type: str
    rationale: str
    similarity_algorithm_version: str
    similarity_score: float
    similarity_components: dict
    snapshot_business_concept_id: str | None
    snapshot_business_concept_name: str | None
    snapshot_historical_title: str
    snapshot_historical_status: str
    snapshot_outcome_classification: str | None
    snapshot_effectiveness_summary: str | None
    compared_at: datetime
    referenced_by_membership_id: str
    referenced_at: datetime
    removed_by_membership_id: str | None
    removed_at: datetime | None
    removal_rationale: str | None


class PrecedentMutationResponse(BaseModel):
    input_revision: int
    precedent: PrecedentReferenceResponse


class LessonAdoptionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    historical_decision_id: str
    historical_lesson_id: str
    status: Literal["adopted", "rejected"]
    rationale: str = Field(min_length=3)
    application_note: str = ""


class LessonAdoptionSupersede(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    rationale: str = Field(min_length=3)


class LessonAdoptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    historical_decision_id: str
    historical_lesson_id: str
    status: str
    rationale: str
    application_note: str
    snapshot_lesson_type: str
    snapshot_lesson_description: str
    snapshot_lesson_business_impact: str
    acted_by_membership_id: str
    acted_at: datetime
    superseded_by_membership_id: str | None
    superseded_at: datetime | None
    supersession_rationale: str | None


class LessonAdoptionMutationResponse(BaseModel):
    input_revision: int
    adoption: LessonAdoptionResponse
