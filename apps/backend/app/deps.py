from dataclasses import dataclass
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models import (
    Membership,
    MembershipRole,
    Permission,
    Role,
    RolePermission,
    Session as LoginSession,
    User,
)

bearer = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass
class Principal:
    user: User
    membership: Membership
    session: LoginSession
    role_ids: set[str]
    role_codes: set[str]
    permissions: set[str]

    @property
    def tenant_id(self) -> str:
        return self.membership.tenant_id

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def get_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    try:
        payload = decode_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid or expired token") from exc
    user = db.get(User, payload.get("sub"))
    session = db.get(LoginSession, payload.get("sid"))
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == payload.get("sub"),
            Membership.tenant_id == payload.get("tenant_id"),
        )
    )
    if (
        not user
        or not user.is_active
        or not session
        or session.revoked_at
        or not membership
        or not membership.is_active
    ):
        raise HTTPException(401, "Session is not active")
    role_rows = db.execute(
        select(Role.id, Role.code)
        .join(MembershipRole, MembershipRole.role_id == Role.id)
        .where(MembershipRole.membership_id == membership.id)
    ).all()
    role_ids = {r.id for r in role_rows}
    role_codes = {r.code for r in role_rows}
    permissions = (
        set(
            db.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id.in_(role_ids))
            ).all()
        )
        if role_ids
        else set()
    )
    return Principal(user, membership, session, role_ids, role_codes, permissions)
