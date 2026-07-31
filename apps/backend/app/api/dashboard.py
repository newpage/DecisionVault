from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.deps import Principal,get_db,get_principal
from app.models import AuditEvent,DecisionCase,IngestionJob,KnowledgeCard,SourceDocument,Workspace
router=APIRouter(tags=["Dashboard"])
@router.get("/dashboard")
def dashboard(p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    def count(model,*extra): return db.scalar(select(func.count()).select_from(model).where(model.tenant_id==p.tenant_id,*extra)) or 0
    return {"metrics":{"workspaces":count(Workspace),"knowledge_cards":count(KnowledgeCard),"published":count(KnowledgeCard,KnowledgeCard.lifecycle_status=="published"),"pending_review":count(KnowledgeCard,KnowledgeCard.approval_status=="pending_review"),"sources":count(SourceDocument),"decisions":count(DecisionCase)},"activity":db.scalars(select(AuditEvent).where(AuditEvent.tenant_id==p.tenant_id).order_by(AuditEvent.created_at.desc()).limit(8)).all()}
@router.get("/governance")
def governance(p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    cards=db.scalars(select(KnowledgeCard).where(KnowledgeCard.tenant_id==p.tenant_id,KnowledgeCard.approval_status=="pending_review").order_by(KnowledgeCard.created_at)).all(); return {"review_queue":cards}
