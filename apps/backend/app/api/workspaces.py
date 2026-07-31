from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.deps import Principal,get_db,get_principal
from app.models import Workspace
from app.schemas import WorkspaceCreate
router=APIRouter(prefix="/workspaces",tags=["Workspaces"])
@router.get("")
def list_workspaces(p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    return db.scalars(select(Workspace).where(Workspace.tenant_id==p.tenant_id).order_by(Workspace.name)).all()
@router.post("")
def create(body:WorkspaceCreate,p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    item=Workspace(tenant_id=p.tenant_id,organization_id=p.membership.organization_id,name=body.name,description=body.description);db.add(item);db.commit();db.refresh(item);return item
