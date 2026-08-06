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
