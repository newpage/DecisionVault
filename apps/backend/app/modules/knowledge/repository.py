from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    IngestionJob,
    KnowledgeCard,
    SourceDocument,
    Workspace,
)


class KnowledgeRepository:
    """Persistence operations for the Knowledge bounded context."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_cards(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        query: str = "",
    ) -> Sequence[KnowledgeCard]:
        stmt = select(KnowledgeCard).where(
            KnowledgeCard.tenant_id == tenant_id,
            KnowledgeCard.classification_rank <= clearance_rank,
        )
        normalized_query = query.strip()
        if normalized_query:
            pattern = f"%{normalized_query}%"
            stmt = stmt.where(
                KnowledgeCard.title.ilike(pattern)
                | KnowledgeCard.summary.ilike(pattern)
            )
        return self._db.scalars(
            stmt.order_by(KnowledgeCard.created_at.desc())
        ).all()

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
    ) -> KnowledgeCard | None:
        return self._db.scalar(
            select(KnowledgeCard).where(
                KnowledgeCard.id == card_id,
                KnowledgeCard.tenant_id == tenant_id,
            )
        )

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

    def commit_card(self, card: KnowledgeCard) -> KnowledgeCard:
        self._db.add(card)
        self._db.commit()
        self._db.refresh(card)
        return card
