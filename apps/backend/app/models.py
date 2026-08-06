from __future__ import annotations
from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.database import Base


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    code: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    clearance_rank: Mapped[int] = mapped_column(Integer, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "user_id"),
    )


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(240), default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class MembershipRole(Base):
    __tablename__ = "membership_roles"
    membership_id: Mapped[str] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class AccessPolicy(Base):
    __tablename__ = "access_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))


class AccessPolicyRole(Base):
    __tablename__ = "access_policy_roles"
    policy_id: Mapped[str] = mapped_column(
        ForeignKey("access_policies.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (UniqueConstraint("tenant_id", "name"),)


class BusinessConcept(Base):
    __tablename__ = "business_concepts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="Operations", index=True)
    icon: Mapped[str] = mapped_column(String(60), default="Network")
    color: Mapped[str] = mapped_column(String(20), default="#24a99b")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    __table_args__ = (UniqueConstraint("tenant_id", "slug"),)


class SourceDocument(Base):
    __tablename__ = "source_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(String(400), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    source_document_id: Mapped[str] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class KnowledgeCard(Base):
    __tablename__ = "knowledge_cards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    business_concept_id: Mapped[str | None] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    knowledge_type: Mapped[str] = mapped_column(String(60), default="guidance")
    lifecycle_status: Mapped[str] = mapped_column(
        String(40), default="draft", index=True
    )
    approval_status: Mapped[str] = mapped_column(
        String(40), default="not_submitted", index=True
    )
    authority_level: Mapped[str] = mapped_column(
        String(60), default="organizational_knowledge"
    )
    classification_rank: Mapped[int] = mapped_column(Integer, default=20)
    ai_usage_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    access_policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("access_policies.id"), nullable=True, index=True
    )
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class KnowledgeEvidence(Base):
    __tablename__ = "knowledge_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    knowledge_card_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True
    )
    source_document_id: Mapped[str] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    locator: Mapped[str] = mapped_column(String(180), default="")
    excerpt: Mapped[str] = mapped_column(Text)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    knowledge_card_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    search_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)


class DecisionCase(Base):
    __tablename__ = "decision_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    business_concept_id: Mapped[str | None] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    supplier_name: Mapped[str] = mapped_column(String(180), default="")
    supplier_category: Mapped[str] = mapped_column(
        String(120), default="Electronic Manufacturer"
    )
    supplier_location: Mapped[str] = mapped_column(String(180), default="")
    owner_name: Mapped[str] = mapped_column(String(180), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default="high", index=True)
    risk_level: Mapped[str] = mapped_column(String(30), default="medium", index=True)
    decision_type: Mapped[str] = mapped_column(
        String(60), default="initial_qualification"
    )
    business_unit: Mapped[str] = mapped_column(
        String(180), default="Electronics Supply Chain"
    )
    readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    readiness_status: Mapped[str] = mapped_column(
        String(60), default="insufficient_evidence"
    )
    evidence_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    input_revision: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    __table_args__ = (UniqueConstraint("tenant_id", "id"),)


class DecisionEvidence(Base):
    __tablename__ = "decision_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_card_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_chunk_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    source_document_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(30), index=True)
    selection_rationale: Mapped[str] = mapped_column(Text)
    snapshot_title: Mapped[str] = mapped_column(String(240))
    snapshot_content: Mapped[str] = mapped_column(Text)
    snapshot_source_filename: Mapped[str] = mapped_column(String(255), default="")
    snapshot_source_mime_type: Mapped[str] = mapped_column(String(120), default="")
    snapshot_source_locator: Mapped[str] = mapped_column(String(180), default="")
    snapshot_knowledge_type: Mapped[str] = mapped_column(String(60))
    snapshot_authority_level: Mapped[str] = mapped_column(String(60))
    snapshot_lifecycle_status: Mapped[str] = mapped_column(String(40))
    snapshot_approval_status: Mapped[str] = mapped_column(String(40))
    snapshot_classification_rank: Mapped[int] = mapped_column(Integer)
    snapshot_access_policy_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    snapshot_trust_score: Mapped[float] = mapped_column(Float)
    snapshot_ai_usage_allowed: Mapped[bool] = mapped_column(Boolean)
    snapshot_card_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snapshot_content_revision: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    snapshot_source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    selected_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    removed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    removal_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_decision_evidence_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "superseded_by_id"],
            ["decision_evidence.tenant_id", "decision_evidence.id"],
            name="fk_decision_evidence_tenant_supersession",
        ),
        CheckConstraint(
            "relationship_type IN ('supporting','opposing','contextual','risk','constraint')",
            name="ck_decision_evidence_relationship_type",
        ),
        CheckConstraint(
            "length(trim(selection_rationale)) > 0",
            name="ck_decision_evidence_selection_rationale",
        ),
        CheckConstraint(
            "length(trim(snapshot_title)) > 0 AND length(trim(snapshot_content)) > 0",
            name="ck_decision_evidence_snapshot_content",
        ),
        CheckConstraint(
            "(removed_at IS NULL AND removed_by IS NULL AND removal_rationale IS NULL) OR "
            "(removed_at IS NOT NULL AND removed_by IS NOT NULL AND length(trim(removal_rationale)) > 0)",
            name="ck_decision_evidence_removal_metadata",
        ),
        Index(
            "uq_decision_evidence_active_card",
            "tenant_id",
            "decision_case_id",
            "knowledge_card_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
            sqlite_where=text("removed_at IS NULL"),
        ),
    )


class DecisionReview(Base):
    __tablename__ = "decision_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    review_type: Mapped[str] = mapped_column(String(40), index=True)
    assigned_reviewer_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    assigned_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    status: Mapped[str] = mapped_column(String(30), default="assigned", index=True)
    conclusion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    decision_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freshness_status: Mapped[str] = mapped_column(
        String(30), default="pending", index=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint(
            "tenant_id",
            "decision_case_id",
            "sequence",
            name="uq_decision_review_sequence",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_decision_review_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "assigned_reviewer_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_decision_review_tenant_reviewer_membership",
        ),
        CheckConstraint(
            "review_type IN ('business','risk','compliance','final_approval')",
            name="ck_decision_review_type",
        ),
        CheckConstraint(
            "status IN ('assigned','in_progress','completed','cancelled')",
            name="ck_decision_review_status",
        ),
        CheckConstraint(
            "conclusion IS NULL OR conclusion IN ('recommend_approve','recommend_conditional','recommend_reject','changes_required')",
            name="ck_decision_review_conclusion",
        ),
        CheckConstraint(
            "freshness_status IN ('pending','current','stale')",
            name="ck_decision_review_freshness",
        ),
        CheckConstraint(
            "(status != 'completed') OR (conclusion IS NOT NULL AND completed_at IS NOT NULL AND length(trim(summary)) > 0)",
            name="ck_decision_review_completion",
        ),
        CheckConstraint(
            "(status != 'cancelled') OR (cancelled_by IS NOT NULL AND cancelled_at IS NOT NULL AND length(trim(cancellation_reason)) > 0)",
            name="ck_decision_review_cancellation",
        ),
        Index(
            "uq_active_decision_reviewer_type",
            "tenant_id",
            "decision_case_id",
            "assigned_reviewer_membership_id",
            "review_type",
            unique=True,
            postgresql_where=text("status IN ('assigned','in_progress')"),
            sqlite_where=text("status IN ('assigned','in_progress')"),
        ),
    )


class DecisionReviewAssignment(Base):
    __tablename__ = "decision_review_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    review_id: Mapped[str] = mapped_column(String(36), index=True)
    previous_membership_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    new_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    assigned_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    rationale: Mapped[str] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["decision_reviews.tenant_id", "decision_reviews.id"],
            ondelete="CASCADE",
            name="fk_review_assignment_tenant_review",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "previous_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_review_assignment_tenant_previous_membership",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "new_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_review_assignment_tenant_new_membership",
        ),
        CheckConstraint(
            "length(trim(rationale)) > 0",
            name="ck_review_assignment_rationale",
        ),
    )


class DecisionReviewEvidence(Base):
    __tablename__ = "decision_review_evidence"
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    review_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    associated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["decision_reviews.tenant_id", "decision_reviews.id"],
            ondelete="CASCADE",
            name="fk_review_evidence_tenant_review",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_evidence_id"],
            ["decision_evidence.tenant_id", "decision_evidence.id"],
            name="fk_review_evidence_tenant_evidence",
        ),
    )


class DecisionReviewFinding(Base):
    __tablename__ = "decision_review_findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    review_id: Mapped[str] = mapped_column(String(36), index=True)
    finding_type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    related_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_section: Mapped[str] = mapped_column(String(120), default="")
    required_response: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    resolution_response: Mapped[str] = mapped_column(Text, default="")
    raised_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["decision_reviews.tenant_id", "decision_reviews.id"],
            ondelete="CASCADE",
            name="fk_review_finding_tenant_review",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "related_evidence_id"],
            ["decision_evidence.tenant_id", "decision_evidence.id"],
            name="fk_review_finding_tenant_evidence",
        ),
        CheckConstraint(
            "finding_type IN ('information_request','evidence_gap','risk_concern','policy_concern','control_concern','recommendation','approval_condition','comment')",
            name="ck_review_finding_type",
        ),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')",
            name="ck_review_finding_severity",
        ),
        CheckConstraint(
            "status IN ('open','addressed','accepted','closed','withdrawn')",
            name="ck_review_finding_status",
        ),
        CheckConstraint(
            "(status = 'open') OR length(trim(resolution_response)) > 0",
            name="ck_review_finding_resolution",
        ),
    )


class DecisionApprovalAction(Base):
    __tablename__ = "decision_approval_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    review_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_approval_action_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["decision_reviews.tenant_id", "decision_reviews.id"],
            name="fk_approval_action_tenant_review",
        ),
        CheckConstraint(
            "action IN ('approved','conditionally_approved','rejected','returned_for_changes')",
            name="ck_decision_approval_action",
        ),
        CheckConstraint(
            "length(trim(rationale)) > 0", name="ck_decision_approval_rationale"
        ),
    )


class DecisionApprovalCondition(Base):
    __tablename__ = "decision_approval_conditions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    approval_action_id: Mapped[str] = mapped_column(String(36), index=True)
    condition_text: Mapped[str] = mapped_column(Text)
    responsible_party: Mapped[str] = mapped_column(String(180), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    satisfied_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    satisfied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    satisfaction_response: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_approval_condition_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "approval_action_id"],
            ["decision_approval_actions.tenant_id", "decision_approval_actions.id"],
            ondelete="CASCADE",
            name="fk_approval_condition_tenant_action",
        ),
        CheckConstraint(
            "status IN ('open','satisfied','waived')",
            name="ck_approval_condition_status",
        ),
        CheckConstraint(
            "length(trim(condition_text)) > 0", name="ck_approval_condition_text"
        ),
        CheckConstraint(
            "(status = 'open' AND satisfied_by IS NULL AND satisfied_at IS NULL) OR (status IN ('satisfied','waived') AND satisfied_by IS NOT NULL AND satisfied_at IS NOT NULL AND length(trim(satisfaction_response)) > 0)",
            name="ck_approval_condition_satisfaction",
        ),
    )


class DecisionExpectedOutcome(Base):
    __tablename__ = "decision_expected_outcomes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="business")
    measurement_type: Mapped[str] = mapped_column(String(30), index=True)
    baseline_value: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    target_min_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6), nullable=True
    )
    target_max_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6), nullable=True
    )
    target_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str] = mapped_column(String(60), default="")
    target_direction: Mapped[str] = mapped_column(String(30))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evaluation_window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responsible_membership_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    weight: Mapped[float] = mapped_column(Numeric(8, 4), default=1)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    success_criteria: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    amended_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    amendment_rationale: Mapped[str] = mapped_column(Text, default="")
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_expected_outcome_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "responsible_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_expected_outcome_tenant_responsible",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "created_by_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_expected_outcome_tenant_creator",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "amended_from_id"],
            ["decision_expected_outcomes.tenant_id", "decision_expected_outcomes.id"],
            name="fk_expected_outcome_tenant_amendment",
        ),
        CheckConstraint(
            "measurement_type IN ('numeric','percentage','currency','duration','boolean','milestone','qualitative')",
            name="ck_expected_outcome_measurement_type",
        ),
        CheckConstraint(
            "target_direction IN ('increase','decrease','range','exact','complete','maintain')",
            name="ck_expected_outcome_target_direction",
        ),
        CheckConstraint(
            "status IN ('active','superseded')", name="ck_expected_outcome_status"
        ),
        CheckConstraint("weight > 0", name="ck_expected_outcome_weight"),
        CheckConstraint(
            "evaluation_window_days IS NULL OR evaluation_window_days > 0",
            name="ck_expected_outcome_evaluation_window",
        ),
        CheckConstraint(
            "target_direction != 'range' OR (target_min_value IS NOT NULL AND target_max_value IS NOT NULL AND target_min_value <= target_max_value)",
            name="ck_expected_outcome_range",
        ),
        CheckConstraint(
            "length(trim(title)) > 0 AND length(trim(description)) > 0 AND length(trim(success_criteria)) > 0",
            name="ck_expected_outcome_required_text",
        ),
        Index(
            "uq_active_expected_outcome_title",
            "tenant_id",
            "decision_case_id",
            "title",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )


class DecisionOutcomeObservation(Base):
    __tablename__ = "decision_outcome_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    expected_outcome_id: Mapped[str] = mapped_column(String(36), index=True)
    observation_date: Mapped[date] = mapped_column(Date)
    numeric_value: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observed_status: Mapped[str] = mapped_column(String(30), default="reported")
    narrative: Mapped[str] = mapped_column(Text, default="")
    provenance: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(500), default="")
    decision_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recorded_by_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified", index=True
    )
    verified_by_membership_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_rationale: Mapped[str] = mapped_column(Text, default="")
    superseded_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    supersession_rationale: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_observation_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "expected_outcome_id"],
            ["decision_expected_outcomes.tenant_id", "decision_expected_outcomes.id"],
            ondelete="CASCADE",
            name="fk_observation_tenant_outcome",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_evidence_id"],
            ["decision_evidence.tenant_id", "decision_evidence.id"],
            name="fk_observation_tenant_evidence",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "recorded_by_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_observation_tenant_recorder",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "verified_by_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_observation_tenant_verifier",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "superseded_by_id"],
            [
                "decision_outcome_observations.tenant_id",
                "decision_outcome_observations.id",
            ],
            name="fk_observation_tenant_supersession",
        ),
        CheckConstraint(
            "observed_status IN ('reported','achieved','not_achieved','in_progress','inconclusive')",
            name="ck_observation_status",
        ),
        CheckConstraint(
            "provenance IN ('manually_reported','verified_business_record','documented_evidence')",
            name="ck_observation_provenance",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','verified','superseded')",
            name="ck_observation_verification_status",
        ),
        CheckConstraint(
            "(verification_status = 'verified' AND verified_by_membership_id IS NOT NULL AND verified_at IS NOT NULL AND length(trim(verification_rationale)) > 0) OR verification_status != 'verified'",
            name="ck_observation_verification_metadata",
        ),
        CheckConstraint(
            "verified_by_membership_id IS NULL OR verified_by_membership_id != recorded_by_membership_id",
            name="ck_observation_separation_of_duties",
        ),
        CheckConstraint(
            "(verification_status = 'superseded' AND superseded_by_id IS NOT NULL AND length(trim(supersession_rationale)) > 0) OR verification_status != 'superseded'",
            name="ck_observation_supersession_metadata",
        ),
    )


class DecisionEffectivenessAssessment(Base):
    __tablename__ = "decision_effectiveness_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    assessment_date: Mapped[date] = mapped_column(Date)
    evaluation_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    evaluation_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    assessor_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    classification: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[str] = mapped_column(Text)
    outcome_summary: Mapped[str] = mapped_column(Text, default="")
    risk_summary: Mapped[str] = mapped_column(Text, default="")
    condition_summary: Mapped[str] = mapped_column(Text, default="")
    calculation_details: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_references: Mapped[list] = mapped_column(JSON, default=list)
    observation_references: Mapped[list] = mapped_column(JSON, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supersedes_assessment_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint(
            "tenant_id", "decision_case_id", "revision", name="uq_assessment_revision"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_assessment_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "assessor_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_assessment_tenant_assessor",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "supersedes_assessment_id"],
            [
                "decision_effectiveness_assessments.tenant_id",
                "decision_effectiveness_assessments.id",
            ],
            name="fk_assessment_tenant_supersession",
        ),
        CheckConstraint(
            "status IN ('draft','completed','superseded')", name="ck_assessment_status"
        ),
        CheckConstraint(
            "classification IN ('exceeded','met','partially_met','did_not_meet','inconclusive','too_early','cancelled')",
            name="ck_assessment_classification",
        ),
        CheckConstraint(
            "evaluation_end IS NULL OR evaluation_start IS NULL OR evaluation_start <= evaluation_end",
            name="ck_assessment_evaluation_period",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR status != 'completed'",
            name="ck_assessment_completion",
        ),
        CheckConstraint("length(trim(rationale)) > 0", name="ck_assessment_rationale"),
    )


class DecisionLesson(Base):
    __tablename__ = "decision_lessons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    decision_case_id: Mapped[str] = mapped_column(String(36), index=True)
    lesson_type: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str] = mapped_column(Text)
    business_impact: Mapped[str] = mapped_column(Text, default="")
    related_outcome_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_finding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_condition_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by_membership_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "decision_case_id"],
            ["decision_cases.tenant_id", "decision_cases.id"],
            ondelete="CASCADE",
            name="fk_lesson_tenant_decision",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "related_outcome_id"],
            ["decision_expected_outcomes.tenant_id", "decision_expected_outcomes.id"],
            name="fk_lesson_tenant_outcome",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "related_evidence_id"],
            ["decision_evidence.tenant_id", "decision_evidence.id"],
            name="fk_lesson_tenant_evidence",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "related_finding_id"],
            ["decision_review_findings.tenant_id", "decision_review_findings.id"],
            name="fk_lesson_tenant_finding",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "related_condition_id"],
            [
                "decision_approval_conditions.tenant_id",
                "decision_approval_conditions.id",
            ],
            name="fk_lesson_tenant_condition",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "created_by_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_lesson_tenant_creator",
        ),
        CheckConstraint(
            "lesson_type IN ('evidence','process','risk','assumption','execution','governance')",
            name="ck_lesson_type",
        ),
        CheckConstraint("length(trim(description)) > 0", name="ck_lesson_description"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36), default="")
    description: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
