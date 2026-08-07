from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LessonPromotionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    lesson_evaluation_id: str
    rationale: str = Field(min_length=3)
    applicability: str = Field(min_length=3)
    limitations: str = Field(min_length=3)
    title: str = Field(min_length=3, max_length=240)
    summary: str = Field(min_length=3)
    body: str = Field(min_length=3)


class LessonPromotionAction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    rationale: str = Field(min_length=3)


class LessonPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_decision_id: str
    source_lesson_id: str
    evaluation_decision_id: str
    lesson_adoption_id: str
    lesson_evaluation_id: str
    effectiveness_assessment_id: str
    status: Literal["proposed", "approved", "rejected", "withdrawn", "promoted"]
    rationale: str
    applicability: str
    limitations: str
    proposed_title: str
    proposed_summary: str
    proposed_body: str
    snapshot_source_decision: dict
    snapshot_lesson: dict
    snapshot_adoption: dict
    snapshot_evaluation: dict
    snapshot_effectiveness: dict
    snapshot_relevant_outcomes: list
    snapshot_provenance: dict
    inherited_classification_rank: int
    inherited_access_policy_id: str | None
    proposed_by_membership_id: str
    proposed_at: datetime
    reviewed_by_membership_id: str | None
    reviewed_at: datetime | None
    review_rationale: str | None
    withdrawn_at: datetime | None
    withdrawal_rationale: str | None
    promoted_at: datetime | None
    resulting_knowledge_card_id: str | None


class LessonPromotionEligibilityResponse(BaseModel):
    lesson_id: str
    eligible: bool
    reasons: list[str]
    evaluations: list[dict]


class LessonPromotionWorkspaceResponse(BaseModel):
    eligibility: LessonPromotionEligibilityResponse
    proposals: list[LessonPromotionResponse]


class KnowledgeLessonProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    knowledge_card_id: str
    promotion_proposal_id: str
    source_decision_id: str
    source_lesson_id: str
    lesson_evaluation_id: str
    immutable_snapshot: dict
    created_at: datetime
