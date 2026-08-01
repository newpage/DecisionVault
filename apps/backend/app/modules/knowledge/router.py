from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import KnowledgeModuleStatus, UploadQueuedResponse
from app.modules.knowledge.service import (
    KnowledgeNotFoundError,
    KnowledgePermissionError,
    KnowledgeService,
    KnowledgeValidationError,
)

router = APIRouter(tags=["Knowledge"])


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(db))


@router.get("/knowledge")
def list_cards(
    q: str = "",
    principal: Principal = Depends(get_principal),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return service.list_cards(
        tenant_id=principal.tenant_id,
        clearance_rank=principal.membership.clearance_rank,
        query=q,
    )


@router.post("/sources/upload", response_model=UploadQueuedResponse)
async def upload(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> UploadQueuedResponse:
    try:
        source, job = service.queue_source_upload(
            tenant_id=principal.tenant_id,
            workspace_id=workspace_id,
            user_id=principal.user.id,
            filename=file.filename or "upload",
            mime_type=file.content_type or "application/octet-stream",
            raw=await file.read(),
        )
    except KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KnowledgeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadQueuedResponse(source_id=source.id, job_id=job.id)


@router.get("/ingestion/jobs")
def jobs(
    principal: Principal = Depends(get_principal),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return service.list_ingestion_jobs(tenant_id=principal.tenant_id)


@router.post("/knowledge/{card_id}/submit")
def submit(
    card_id: str,
    principal: Principal = Depends(get_principal),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.submit_card(
            card_id=card_id,
            tenant_id=principal.tenant_id,
        )
    except KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/knowledge/{card_id}/approve")
def approve(
    card_id: str,
    principal: Principal = Depends(get_principal),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.approve_card(
            card_id=card_id,
            tenant_id=principal.tenant_id,
            approver_id=principal.user.id,
            can_approve=principal.can("knowledge.approve"),
        )
    except KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KnowledgePermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/knowledge/module/health", response_model=KnowledgeModuleStatus)
def module_health() -> KnowledgeModuleStatus:
    return KnowledgeModuleStatus()
