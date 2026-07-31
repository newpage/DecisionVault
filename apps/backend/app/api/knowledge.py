from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.deps import Principal,get_db,get_principal
from app.models import AuditEvent,IngestionJob,KnowledgeCard,SourceDocument,Workspace
router=APIRouter(tags=["Knowledge"])
@router.get("/knowledge")
def list_cards(q:str="",p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    stmt=select(KnowledgeCard).where(KnowledgeCard.tenant_id==p.tenant_id,KnowledgeCard.classification_rank<=p.membership.clearance_rank)
    if q: stmt=stmt.where((KnowledgeCard.title.ilike(f"%{q}%"))|(KnowledgeCard.summary.ilike(f"%{q}%")))
    return db.scalars(stmt.order_by(KnowledgeCard.created_at.desc())).all()
@router.post("/sources/upload")
async def upload(workspace_id:str=Form(...),file:UploadFile=File(...),p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    ws=db.scalar(select(Workspace).where(Workspace.id==workspace_id,Workspace.tenant_id==p.tenant_id))
    if not ws: raise HTTPException(404,"Workspace not found")
    raw=await file.read();
    if not raw: raise HTTPException(400,"Empty file")
    key=f"{p.tenant_id}/{uuid4()}-{Path(file.filename or 'upload').name}"; target=Path(settings.storage_path)/key; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    doc=SourceDocument(tenant_id=p.tenant_id,workspace_id=workspace_id,filename=file.filename or "upload",mime_type=file.content_type or "application/octet-stream",storage_key=key,created_by=p.user.id)
    db.add(doc);db.flush();job=IngestionJob(tenant_id=p.tenant_id,source_document_id=doc.id);db.add(job);db.add(AuditEvent(tenant_id=p.tenant_id,actor_id=p.user.id,event_type="SourceUploaded",entity_type="source_document",entity_id=doc.id,description=f"Uploaded {doc.filename}"));db.commit();return {"source_id":doc.id,"job_id":job.id,"status":"queued"}
@router.get("/ingestion/jobs")
def jobs(p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    return db.scalars(select(IngestionJob).where(IngestionJob.tenant_id==p.tenant_id).order_by(IngestionJob.created_at.desc()).limit(20)).all()
@router.post("/knowledge/{card_id}/submit")
def submit(card_id:str,p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    card=db.scalar(select(KnowledgeCard).where(KnowledgeCard.id==card_id,KnowledgeCard.tenant_id==p.tenant_id));
    if not card: raise HTTPException(404,"Knowledge Card not found")
    card.approval_status="pending_review"; card.lifecycle_status="in_review"; db.commit(); return card
@router.post("/knowledge/{card_id}/approve")
def approve(card_id:str,p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    if not p.can("knowledge.approve"): raise HTTPException(403,"Knowledge approval permission required")
    card=db.scalar(select(KnowledgeCard).where(KnowledgeCard.id==card_id,KnowledgeCard.tenant_id==p.tenant_id));
    if not card: raise HTTPException(404,"Knowledge Card not found")
    from datetime import datetime,timezone
    card.approval_status="approved";card.lifecycle_status="published";card.approved_by=p.user.id;card.approved_at=datetime.now(timezone.utc);card.trust_score=max(card.trust_score,.8);db.commit();return card
