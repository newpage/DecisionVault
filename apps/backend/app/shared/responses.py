from typing import Any
from pydantic import BaseModel, Field

class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    metadata: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    request_id: str|None = None
