from datetime import datetime

from pydantic import BaseModel


class BusinessConceptSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    category: str
    icon: str
    color: str
    status: str
    knowledge_count: int
    updated_at: datetime
