from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.modules.business_concepts.repository import BusinessConceptRepository
from app.modules.business_concepts.schemas import (
    BusinessConceptSummary,
    BusinessConceptWorkspace,
)
from app.modules.business_concepts.service import (
    BusinessConceptNotFoundError,
    BusinessConceptService,
)

router = APIRouter(prefix="/business-concepts", tags=["Business Concepts"])


def get_business_concept_service(
    db: Session = Depends(get_db),
) -> BusinessConceptService:
    return BusinessConceptService(BusinessConceptRepository(db))


@router.get("", response_model=list[BusinessConceptSummary])
def list_business_concepts(
    q: str = Query(default="", max_length=120),
    principal: Principal = Depends(get_principal),
    service: BusinessConceptService = Depends(get_business_concept_service),
) -> list[BusinessConceptSummary]:
    return service.list_concepts(
        tenant_id=principal.tenant_id,
        query=q,
    )


@router.get("/{concept_id}", response_model=BusinessConceptWorkspace)
def get_business_concept_workspace(
    concept_id: str,
    principal: Principal = Depends(get_principal),
    service: BusinessConceptService = Depends(get_business_concept_service),
) -> BusinessConceptWorkspace:
    try:
        return service.get_workspace(
            tenant_id=principal.tenant_id,
            concept_id=concept_id,
        )
    except BusinessConceptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
