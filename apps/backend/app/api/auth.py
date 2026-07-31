from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_password
from app.deps import Principal, get_db, get_principal
from app.models import Membership, Session as LoginSession, Tenant, User
from app.schemas import LoginRequest

router=APIRouter(prefix="/auth",tags=["Authentication"])
@router.post("/login")
def login(body:LoginRequest,db:Session=Depends(get_db)):
    tenant=db.scalar(select(Tenant).where(Tenant.slug==body.tenant.lower())); user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not tenant or not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Invalid credentials")
    membership=db.scalar(select(Membership).where(Membership.tenant_id==tenant.id,Membership.user_id==user.id))
    if not membership: raise HTTPException(401,"Invalid credentials")
    session=LoginSession(tenant_id=tenant.id,user_id=user.id); db.add(session); db.commit(); db.refresh(session)
    return {"access_token":create_access_token(user_id=user.id,tenant_id=tenant.id,session_id=session.id),"token_type":"bearer","user":{"name":user.full_name,"email":user.email,"roles":["tenant_admin"],"tenant":tenant.name}}
@router.get("/me")
def me(p:Principal=Depends(get_principal)): return {"id":p.user.id,"name":p.user.full_name,"email":p.user.email,"roles":sorted(p.role_codes),"permissions":sorted(p.permissions),"tenant_id":p.tenant_id}
@router.post("/logout")
def logout(p:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    p.session.revoked_at=datetime.now(timezone.utc); db.commit(); return {"ok":True}
