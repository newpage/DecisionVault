from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


def uid() -> str: return str(uuid4())
def utcnow() -> datetime: return datetime.now(timezone.utc)

class Tenant(Base):
    __tablename__="tenants"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str]=mapped_column(String(80), unique=True, index=True)
    name: Mapped[str]=mapped_column(String(180))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class Organization(Base):
    __tablename__="organizations"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(180))
    code: Mapped[str]=mapped_column(String(80))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__=(UniqueConstraint("tenant_id","code"),)

class User(Base):
    __tablename__="users"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str]=mapped_column(String(180))
    password_hash: Mapped[str]=mapped_column(String(255))
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class Membership(Base):
    __tablename__="memberships"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    clearance_rank: Mapped[int]=mapped_column(Integer, default=20)
    __table_args__=(UniqueConstraint("tenant_id","user_id"),)


class Role(Base):
    __tablename__="roles"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    code: Mapped[str]=mapped_column(String(80))
    name: Mapped[str]=mapped_column(String(120))
    __table_args__=(UniqueConstraint("tenant_id","code"),)

class Permission(Base):
    __tablename__="permissions"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str]=mapped_column(String(120), unique=True)
    description: Mapped[str]=mapped_column(String(240), default="")

class RolePermission(Base):
    __tablename__="role_permissions"
    role_id: Mapped[str]=mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str]=mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

class MembershipRole(Base):
    __tablename__="membership_roles"
    membership_id: Mapped[str]=mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str]=mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

class AccessPolicy(Base):
    __tablename__="access_policies"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(160))

class AccessPolicyRole(Base):
    __tablename__="access_policy_roles"
    policy_id: Mapped[str]=mapped_column(ForeignKey("access_policies.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str]=mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

class Session(Base):
    __tablename__="sessions"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    revoked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class Workspace(Base):
    __tablename__="workspaces"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(180))
    description: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__=(UniqueConstraint("tenant_id","name"),)


class BusinessConcept(Base):
    __tablename__="business_concepts"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(180))
    slug: Mapped[str]=mapped_column(String(180))
    description: Mapped[str]=mapped_column(Text, default="")
    category: Mapped[str]=mapped_column(String(80), default="Operations", index=True)
    icon: Mapped[str]=mapped_column(String(60), default="Network")
    color: Mapped[str]=mapped_column(String(20), default="#24a99b")
    status: Mapped[str]=mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__=(UniqueConstraint("tenant_id","slug"),)

class SourceDocument(Base):
    __tablename__="source_documents"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str]=mapped_column(String(255))
    mime_type: Mapped[str]=mapped_column(String(120))
    storage_key: Mapped[str]=mapped_column(String(400), unique=True)
    status: Mapped[str]=mapped_column(String(40), default="queued")
    created_by: Mapped[str]=mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class IngestionJob(Base):
    __tablename__="ingestion_jobs"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    source_document_id: Mapped[str]=mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str]=mapped_column(String(40), default="queued", index=True)
    progress: Mapped[int]=mapped_column(Integer, default=0)
    error: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class KnowledgeCard(Base):
    __tablename__="knowledge_cards"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    business_concept_id: Mapped[str|None]=mapped_column(ForeignKey("business_concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str]=mapped_column(String(240))
    summary: Mapped[str]=mapped_column(Text)
    body: Mapped[str]=mapped_column(Text)
    knowledge_type: Mapped[str]=mapped_column(String(60), default="guidance")
    lifecycle_status: Mapped[str]=mapped_column(String(40), default="draft", index=True)
    approval_status: Mapped[str]=mapped_column(String(40), default="not_submitted", index=True)
    authority_level: Mapped[str]=mapped_column(String(60), default="organizational_knowledge")
    classification_rank: Mapped[int]=mapped_column(Integer, default=20)
    ai_usage_allowed: Mapped[bool]=mapped_column(Boolean, default=True)
    access_policy_id: Mapped[str|None]=mapped_column(ForeignKey("access_policies.id"), nullable=True, index=True)
    trust_score: Mapped[float]=mapped_column(Float, default=0.5)
    owner_id: Mapped[str]=mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str|None]=mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class KnowledgeEvidence(Base):
    __tablename__="knowledge_evidence"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    knowledge_card_id: Mapped[str]=mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    source_document_id: Mapped[str]=mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    locator: Mapped[str]=mapped_column(String(180), default="")
    excerpt: Mapped[str]=mapped_column(Text)

class KnowledgeChunk(Base):
    __tablename__="knowledge_chunks"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    knowledge_card_id: Mapped[str]=mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    content: Mapped[str]=mapped_column(Text)
    chunk_index: Mapped[int]=mapped_column(Integer)
    search_text: Mapped[str]=mapped_column(Text)
    embedding: Mapped[list[float]|None]=mapped_column(Vector(768), nullable=True)

class DecisionCase(Base):
    __tablename__="decision_cases"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    business_concept_id: Mapped[str|None]=mapped_column(ForeignKey("business_concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str]=mapped_column(String(240))
    question: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(40), default="draft", index=True)
    recommendation: Mapped[str]=mapped_column(Text, default="")
    confidence: Mapped[float]=mapped_column(Float, default=0)
    supplier_name: Mapped[str]=mapped_column(String(180), default="")
    supplier_category: Mapped[str]=mapped_column(String(120), default="Electronic Manufacturer")
    supplier_location: Mapped[str]=mapped_column(String(180), default="")
    owner_name: Mapped[str]=mapped_column(String(180), default="")
    due_date: Mapped[date|None]=mapped_column(Date, nullable=True)
    priority: Mapped[str]=mapped_column(String(30), default="high", index=True)
    risk_level: Mapped[str]=mapped_column(String(30), default="medium", index=True)
    decision_type: Mapped[str]=mapped_column(String(60), default="initial_qualification")
    business_unit: Mapped[str]=mapped_column(String(180), default="Electronics Supply Chain")
    readiness_score: Mapped[int]=mapped_column(Integer, default=0)
    readiness_status: Mapped[str]=mapped_column(String(60), default="insufficient_evidence")
    evidence_summary: Mapped[dict]=mapped_column(JSON, default=dict)
    created_by: Mapped[str]=mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class DecisionEvidence(Base):
    __tablename__="decision_evidence"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    decision_case_id: Mapped[str]=mapped_column(ForeignKey("decision_cases.id", ondelete="CASCADE"), index=True)
    knowledge_card_id: Mapped[str]=mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    chunk_id: Mapped[str]=mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), index=True)
    score: Mapped[float]=mapped_column(Float)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str|None]=mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str]=mapped_column(String(80), index=True)
    entity_type: Mapped[str]=mapped_column(String(80))
    entity_id: Mapped[str]=mapped_column(String(36), default="")
    description: Mapped[str]=mapped_column(Text)
    details: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
