from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.modules.decisions.lifecycle import InvalidTransitionError
from app.modules.decisions.evidence import EvidenceValidationError
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.schemas import (
    DecisionCreate,
    AvailableEvidenceResponse,
    EvidenceMutationResponse,
    EvidenceRemoval,
    EvidenceResponse,
    EvidenceSelection,
    DecisionResponse,
    DecisionTransition,
    DecisionWorkspaceResponse,
)
from app.modules.decisions.service import (
    DecisionNotFoundError,
    DecisionConflictError,
    DecisionService,
)

router = APIRouter(tags=["Decision Intelligence"])


def get_service(db: Session = Depends(get_db)) -> DecisionService:
    return DecisionService(DecisionRepository(db))


def map_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, DecisionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DecisionPermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, DecisionConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, EvidenceValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    raise exc


@router.get("/decisions", response_model=list[DecisionResponse])
def list_decisions(
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_decisions(
            tenant_id=principal.tenant_id,
            permissions=principal.permissions,
        )
    except (DecisionPermissionError,) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}", response_model=DecisionWorkspaceResponse
)
def get_decision_workspace(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.get_workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions", response_model=DecisionResponse, status_code=201
)
def create_decision(
    body: DecisionCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.create_decision(
            tenant_id=principal.tenant_id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.patch(
    "/decisions/{decision_id}/status", response_model=DecisionResponse
)
def transition_decision(
    decision_id: str,
    body: DecisionTransition,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.transition(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            status=body.status,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        InvalidTransitionError,
    ) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/available-evidence",
    response_model=list[AvailableEvidenceResponse],
)
def list_available_evidence(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_available_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/evidence",
    response_model=list[EvidenceResponse],
)
def list_active_evidence(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_active_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/evidence/history",
    response_model=list[EvidenceResponse],
)
def list_evidence_history(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_evidence_history(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/evidence",
    response_model=EvidenceMutationResponse,
    status_code=201,
)
def select_evidence(
    decision_id: str,
    body: EvidenceSelection,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.select_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            card_id=body.knowledge_card_id,
            chunk_id=body.knowledge_chunk_id,
            relationship_type=body.relationship_type,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        EvidenceValidationError,
    ) as exc:
        raise map_failure(exc) from exc


@router.delete(
    "/decisions/{decision_id}/evidence/{evidence_id}",
    response_model=EvidenceMutationResponse,
)
def remove_evidence(
    decision_id: str,
    evidence_id: str,
    body: EvidenceRemoval,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.remove_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            evidence_id=evidence_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        EvidenceValidationError,
    ) as exc:
        raise map_failure(exc) from exc
