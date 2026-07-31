from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.deps import Principal,get_db,get_principal
from app.models import AuditEvent,DecisionCase,DecisionEvidence,KnowledgeCard,KnowledgeChunk
from app.schemas import DecisionCreate,QuestionRequest
from app.services import answer,retrieve
router=APIRouter(tags=["Decision Intelligence"])
@router.post("/ask")
async def ask(body:QuestionRequest,p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    evidence=await retrieve(db,tenant_id=p.tenant_id,clearance_rank=p.membership.clearance_rank,role_ids=p.role_ids,query=body.question)
    response=await answer(body.question,evidence)
    db.add(AuditEvent(tenant_id=p.tenant_id,actor_id=p.user.id,event_type="QuestionAnswered",entity_type="ai_interaction",description=body.question,details={"evidence_count":len(evidence)}));db.commit()
    return {"answer":response,"confidence":round(sum(x[2] for x in evidence)/max(1,len(evidence))*100),"citations":[{"id":card.id,"title":card.title,"excerpt":chunk.content,"score":round(score*100)} for chunk,card,score in evidence]}
@router.get("/decisions")
def decisions(p:Principal=Depends(get_principal),db:Session=Depends(get_db)): return db.scalars(select(DecisionCase).where(DecisionCase.tenant_id==p.tenant_id).order_by(DecisionCase.created_at.desc())).all()
@router.post("/decisions")
async def create_decision(body:DecisionCreate,p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    evidence=await retrieve(db,tenant_id=p.tenant_id,clearance_rank=p.membership.clearance_rank,role_ids=p.role_ids,query=body.question)
    recommendation=await answer(body.question,evidence); score=sum(x[2] for x in evidence)/max(1,len(evidence))
    decision=DecisionCase(tenant_id=p.tenant_id,workspace_id=body.workspace_id,title=body.title,question=body.question,recommendation=recommendation,confidence=score,created_by=p.user.id);db.add(decision);db.flush()
    for chunk,card,s in evidence: db.add(DecisionEvidence(tenant_id=p.tenant_id,decision_case_id=decision.id,knowledge_card_id=card.id,chunk_id=chunk.id,score=s))
    db.commit();db.refresh(decision);return decision
