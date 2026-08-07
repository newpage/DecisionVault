from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dashboard.cache import dashboard_cache
from app.dashboard.service import build_dashboard
from app.deps import Principal, get_db, get_principal
from app.models import KnowledgeCard
from app.modules.knowledge.policies import authorized_knowledge_filters

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
def dashboard(
    refresh: bool = Query(default=False),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    if not refresh:
        cached = dashboard_cache.get(p.tenant_id)
        if cached is not None:
            return cached

    response = build_dashboard(db, p.tenant_id)
    dashboard_cache.set(p.tenant_id, response)
    return response


@router.get("/governance")
def governance(
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    if "knowledge.approve" not in p.permissions:
        raise HTTPException(403, "Knowledge approval permission required")
    cards = db.scalars(
        select(KnowledgeCard)
        .where(
            KnowledgeCard.tenant_id == p.tenant_id,
            KnowledgeCard.approval_status == "pending_review",
            *authorized_knowledge_filters(
                clearance_rank=p.membership.clearance_rank, role_ids=p.role_ids
            ),
        )
        .order_by(KnowledgeCard.created_at)
    ).all()
    return {"review_queue": cards}
