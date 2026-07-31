from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models import *

DEMO_TEXT="""Vendor onboarding requires Quality approval, a current supplier assessment, executed quality agreement, and verification that required testing capabilities are qualified. Conditional approval may be considered only when documented controls and an accountable owner are assigned."""

def seed(db:Session):
    if db.scalar(select(Tenant.id).limit(1)): return
    tenant=Tenant(slug=settings.demo_tenant_slug,name="Acme Life Sciences")
    user=User(email=settings.demo_email,full_name="DecisionVault Demo Administrator",password_hash=hash_password(settings.demo_password))
    db.add_all([tenant,user]); db.flush()
    org=Organization(tenant_id=tenant.id,name="Acme Life Sciences",code="ACME")
    db.add(org); db.flush()
    membership=Membership(tenant_id=tenant.id,organization_id=org.id,user_id=user.id,clearance_rank=50)
    db.add(membership); db.flush()
    role=Role(tenant_id=tenant.id,code="tenant_admin",name="Tenant Administrator")
    permissions=[Permission(code=code,description=code) for code in ["workspace.manage","knowledge.create","knowledge.submit","knowledge.approve","decision.create","admin.manage"]]
    db.add(role); db.add_all(permissions); db.flush()
    db.add(MembershipRole(membership_id=membership.id,role_id=role.id))
    for permission in permissions: db.add(RolePermission(role_id=role.id,permission_id=permission.id))
    ws=Workspace(tenant_id=tenant.id,organization_id=org.id,name="Supplier Governance",description="Trusted knowledge and decisions for supplier qualification.")
    db.add(ws); db.flush()
    card=KnowledgeCard(tenant_id=tenant.id,workspace_id=ws.id,title="Supplier Qualification Requirements",summary="Controls required before a supplier may be approved.",body=DEMO_TEXT,knowledge_type="procedure",lifecycle_status="published",approval_status="approved",authority_level="sop",classification_rank=20,ai_usage_allowed=True,trust_score=.94,owner_id=user.id,approved_by=user.id,approved_at=utcnow())
    db.add(card); db.flush()
    db.add(KnowledgeChunk(tenant_id=tenant.id,knowledge_card_id=card.id,content=DEMO_TEXT,chunk_index=0,search_text=DEMO_TEXT.lower()))
    db.add(AuditEvent(tenant_id=tenant.id,actor_id=user.id,event_type="KnowledgePublished",entity_type="knowledge_card",entity_id=card.id,description="Supplier Qualification Requirements was approved and published."))
    db.commit()
