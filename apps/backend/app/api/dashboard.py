from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dashboard.cache import dashboard_cache
from app.dashboard.service import build_dashboard
from app.deps import Principal, get_db, get_principal

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
def dashboard(
    refresh: bool = Query(default=False),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    cache_key = (
        f"{p.tenant_id}:{p.membership.clearance_rank}:"
        + ",".join(sorted(p.role_ids))
    )
    if not refresh:
        cached = dashboard_cache.get(cache_key)
        if cached is not None:
            return cached

    response = build_dashboard(
        db,
        p.tenant_id,
        clearance_rank=p.membership.clearance_rank,
        role_ids=p.role_ids,
    )
    dashboard_cache.set(cache_key, response)
    return response
