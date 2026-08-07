from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UploadQueuedResponse(BaseModel):
    source_id: str
    job_id: str
    status: str = "queued"


class KnowledgeModuleStatus(BaseModel):
    module: str = "knowledge"
    status: str = "UP"


class KnowledgeCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    title: str
    summary: str
    body: str
    knowledge_type: str
    lifecycle_status: str
    approval_status: str
    authority_level: str
    classification_rank: int
    ai_usage_allowed: bool
    trust_score: float


class GovernanceChecklist(BaseModel):
    provenance_verified: bool
    classification_confirmed: bool
    policy_authority_confirmed: bool
    conflicts_reviewed: bool
    ai_eligibility_appropriate: bool


class KnowledgeReviewRequest(BaseModel):
    action: Literal["approve_publish", "return_correction", "reject"]
    rationale: str = Field(min_length=10, max_length=2000)
    checklist: GovernanceChecklist
