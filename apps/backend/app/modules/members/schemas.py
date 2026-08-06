from typing import Literal

from pydantic import BaseModel, Field


AssignmentResponsibility = Literal["decision_reviewer"]


class AssignmentCandidateResponse(BaseModel):
    membership_id: str
    display_name: str
    email: str
    organization_name: str
    role_labels: list[str]
    responsibility: AssignmentResponsibility


class AssignmentCandidatePage(BaseModel):
    items: list[AssignmentCandidateResponse]
    offset: int
    limit: int
    total: int


class AssignmentCandidateQuery(BaseModel):
    responsibility: AssignmentResponsibility = "decision_reviewer"
    query: str = Field(default="", max_length=120)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=50)
