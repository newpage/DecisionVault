from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.service import DecisionNotFoundError
from app.modules.members.repository import MemberDirectoryRepository
from app.modules.members.schemas import AssignmentCandidatePage
from app.modules.members.service import (
    CandidateEligibilityError,
    MemberDirectoryService,
)


router = APIRouter(tags=["Tenant Members"])


def get_member_service(db: Session = Depends(get_db)) -> MemberDirectoryService:
    return MemberDirectoryService(MemberDirectoryRepository(db))


@router.get(
    "/decisions/{decision_id}/reviewer-candidates",
    response_model=AssignmentCandidatePage,
)
def reviewer_candidates(
    decision_id: str,
    responsibility: str = Query(default="decision_reviewer"),
    query: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    service: MemberDirectoryService = Depends(get_member_service),
):
    try:
        return service.reviewer_candidates(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_permissions=principal.permissions,
            responsibility=responsibility,
            query=query,
            offset=offset,
            limit=limit,
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DecisionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CandidateEligibilityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
