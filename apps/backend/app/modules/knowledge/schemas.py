from pydantic import BaseModel, ConfigDict


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
