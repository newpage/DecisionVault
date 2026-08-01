from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    tenant: str
    email: str
    password: str

class WorkspaceCreate(BaseModel):
    name: str=Field(min_length=2,max_length=180)
    description: str=""

class QuestionRequest(BaseModel):
    question: str=Field(min_length=3)

class DecisionCreate(BaseModel):
    workspace_id: str
    business_concept_id: str|None=None
    title: str=Field(min_length=3,max_length=240)
    question: str=Field(min_length=10)
    supplier_name: str=Field(min_length=2,max_length=180)
    supplier_category: str=Field(default="Electronic Manufacturer",max_length=120)
    supplier_location: str=Field(default="",max_length=180)
    owner_name: str=Field(min_length=2,max_length=180)
    due_date: date|None=None
    priority: Literal["low","medium","high","critical"]="high"
    risk_level: Literal["low","medium","high","critical"]="medium"
    decision_type: Literal["initial_qualification","conditional_approval","renewal","disqualification"]="initial_qualification"
    business_unit: str=Field(default="Electronics Supply Chain",max_length=180)

class DecisionStatusUpdate(BaseModel):
    status: Literal["draft","evidence_collection","in_review","approved","conditionally_approved","rejected","closed"]
