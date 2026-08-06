from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionCreate(BaseModel):
    workspace_id: str
    business_concept_id: str | None = None
    title: str = Field(min_length=3, max_length=240)
    question: str = Field(min_length=10)
    supplier_name: str = Field(min_length=2, max_length=180)
    supplier_category: str = Field(
        default="Electronic Manufacturer", max_length=120
    )
    supplier_location: str = Field(default="", max_length=180)
    owner_name: str = Field(min_length=2, max_length=180)
    due_date: date | None = None
    priority: Literal["low", "medium", "high", "critical"] = "high"
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    decision_type: Literal[
        "initial_qualification",
        "conditional_approval",
        "renewal",
        "disqualification",
    ] = "initial_qualification"
    business_unit: str = Field(
        default="Electronics Supply Chain", max_length=180
    )


class DecisionTransition(BaseModel):
    status: Literal[
        "draft",
        "evidence_collection",
        "in_review",
        "approved",
        "conditionally_approved",
        "rejected",
        "closed",
    ]
    rationale: str = Field(default="", max_length=1000)


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    business_concept_id: str | None
    title: str
    question: str
    status: str
    recommendation: str
    confidence: float
    supplier_name: str
    supplier_category: str
    supplier_location: str
    owner_name: str
    due_date: date | None
    priority: str
    risk_level: str
    decision_type: str
    business_unit: str
    readiness_score: int
    readiness_status: str
    evidence_summary: dict
    created_by: str
    created_at: datetime
    updated_at: datetime


class BusinessConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_card_id: str
    knowledge_chunk_id: str | None
    source_document_id: str | None
    relationship_type: str
    selection_rationale: str
    snapshot_title: str
    snapshot_content: str
    snapshot_source_filename: str
    snapshot_source_mime_type: str
    snapshot_source_locator: str
    snapshot_knowledge_type: str
    snapshot_authority_level: str
    snapshot_lifecycle_status: str
    snapshot_approval_status: str
    snapshot_classification_rank: int
    snapshot_access_policy_id: str | None
    snapshot_trust_score: float
    snapshot_ai_usage_allowed: bool
    snapshot_card_created_at: datetime
    snapshot_content_revision: str | None
    snapshot_source_metadata: dict
    selected_by: str
    selected_at: datetime
    removed_by: str | None
    removed_at: datetime | None
    removal_rationale: str | None
    superseded_by_id: str | None


class AvailableChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chunk_index: int
    content: str


class AvailableEvidenceResponse(BaseModel):
    id: str
    title: str
    summary: str
    knowledge_type: str
    authority_level: str
    trust_score: float
    ai_usage_allowed: bool
    chunks: list[AvailableChunkResponse]
    selected: bool


class EvidenceSelection(BaseModel):
    knowledge_card_id: str
    knowledge_chunk_id: str | None = None
    relationship_type: Literal[
        "supporting", "opposing", "contextual", "risk", "constraint"
    ]
    rationale: str = Field(min_length=3, max_length=2000)


class EvidenceRemoval(BaseModel):
    rationale: str = Field(min_length=3, max_length=2000)


class EvidenceMutationResponse(BaseModel):
    decision: DecisionResponse
    evidence: EvidenceResponse


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_type: str
    description: str
    created_at: datetime


class WorkspaceSummary(BaseModel):
    evidence_count: int
    approved_count: int
    trusted_count: int
    governed_count: int
    confidence_percent: int
    missing_information: list[str]
    control_areas: list[str]
    calculation: dict
    allowed_transitions: list[str]


class DecisionWorkspaceResponse(BaseModel):
    decision: DecisionResponse
    business_concept: BusinessConceptResponse | None
    evidence: list[EvidenceResponse]
    activity: list[ActivityResponse]
    workspace_summary: WorkspaceSummary
