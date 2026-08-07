from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    AccessPolicy,
    IngestionJob,
    KnowledgeCard,
    KnowledgeEvidence,
    KnowledgeCardLessonProvenance,
    SourceDocument,
    Workspace,
)
from app.modules.knowledge.policies import authorized_knowledge_filters


class KnowledgeRepository:
    """Persistence operations for the Knowledge bounded context."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_cards(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
        query: str = "",
    ) -> Sequence[KnowledgeCard]:
        stmt = select(KnowledgeCard).where(
            KnowledgeCard.tenant_id == tenant_id,
            *authorized_knowledge_filters(
                clearance_rank=clearance_rank, role_ids=role_ids
            ),
        )
        normalized_query = query.strip()
        if normalized_query:
            pattern = f"%{normalized_query}%"
            stmt = stmt.where(
                KnowledgeCard.title.ilike(pattern)
                | KnowledgeCard.summary.ilike(pattern)
            )
        return self._db.scalars(stmt.order_by(KnowledgeCard.created_at.desc())).all()

    def provenances(self, *, tenant_id: str, card_ids: list[str]):
        if not card_ids:
            return {}
        return {
            item.knowledge_card_id: item
            for item in self._db.scalars(
                select(KnowledgeCardLessonProvenance).where(
                    KnowledgeCardLessonProvenance.tenant_id == tenant_id,
                    KnowledgeCardLessonProvenance.knowledge_card_id.in_(card_ids),
                )
            ).all()
        }

    def get_workspace(
        self,
        *,
        workspace_id: str,
        tenant_id: str,
    ) -> Workspace | None:
        return self._db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == tenant_id,
            )
        )

    def get_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> KnowledgeCard | None:
        return self._db.scalar(
            select(KnowledgeCard).where(
                KnowledgeCard.id == card_id,
                KnowledgeCard.tenant_id == tenant_id,
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank, role_ids=role_ids
                ),
            )
        )

    def list_review_cards(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> Sequence[KnowledgeCard]:
        return self._db.scalars(
            select(KnowledgeCard).where(
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.lifecycle_status == "in_review",
                KnowledgeCard.approval_status == "pending_review",
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank, role_ids=role_ids
                ),
            )
        ).all()

    def review_context(self, *, tenant_id: str, card_id: str) -> dict:
        evidence = self._db.execute(
            select(KnowledgeEvidence, SourceDocument)
            .join(
                SourceDocument,
                (SourceDocument.id == KnowledgeEvidence.source_document_id)
                & (SourceDocument.tenant_id == KnowledgeEvidence.tenant_id),
            )
            .where(
                KnowledgeEvidence.tenant_id == tenant_id,
                KnowledgeEvidence.knowledge_card_id == card_id,
                SourceDocument.tenant_id == tenant_id,
            )
            .order_by(SourceDocument.created_at)
        ).all()
        card = self._db.scalar(
            select(KnowledgeCard).where(
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.id == card_id,
            )
        )
        policy = None
        if card and card.access_policy_id:
            policy = self._db.scalar(
                select(AccessPolicy).where(
                    AccessPolicy.tenant_id == tenant_id,
                    AccessPolicy.id == card.access_policy_id,
                )
            )
        return {"evidence": evidence, "access_policy": policy}

    def create_source(
        self,
        *,
        source: SourceDocument,
        job: IngestionJob,
        audit_event: AuditEvent,
    ) -> tuple[SourceDocument, IngestionJob]:
        self._db.add(source)
        self._db.flush()
        job.source_document_id = source.id
        self._db.add(job)
        self._db.add(audit_event)
        self._db.commit()
        self._db.refresh(source)
        self._db.refresh(job)
        return source, job

    def list_jobs(
        self,
        *,
        tenant_id: str,
        limit: int = 20,
    ) -> Sequence[IngestionJob]:
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.tenant_id == tenant_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(limit)
        )
        return self._db.scalars(stmt).all()

    def commit_card(self, card: KnowledgeCard, event: AuditEvent) -> KnowledgeCard:
        try:
            self._db.add_all([card, event])
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(card)
        return card
