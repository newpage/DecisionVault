from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.models import AuditEvent, IngestionJob, KnowledgeCard, SourceDocument
from app.modules.knowledge.repository import KnowledgeRepository


class KnowledgeNotFoundError(LookupError):
    """Raised when a tenant-scoped Knowledge resource cannot be found."""


class KnowledgeValidationError(ValueError):
    """Raised when Knowledge input cannot be accepted."""


class KnowledgePermissionError(PermissionError):
    """Raised when a principal lacks a Knowledge permission."""


class KnowledgeService:
    """Business operations for Knowledge Cards and source ingestion."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self._repository = repository

    def list_cards(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        query: str = "",
    ):
        return self._repository.list_cards(
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            query=query,
        )

    def queue_source_upload(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        filename: str,
        mime_type: str,
        raw: bytes,
    ) -> tuple[SourceDocument, IngestionJob]:
        workspace = self._repository.get_workspace(
            workspace_id=workspace_id,
            tenant_id=tenant_id,
        )
        if workspace is None:
            raise KnowledgeNotFoundError("Workspace not found")
        if not raw:
            raise KnowledgeValidationError("Empty file")

        safe_filename = Path(filename or "upload").name
        storage_key = f"{tenant_id}/{uuid4()}-{safe_filename}"
        target = Path(settings.storage_path) / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

        source = SourceDocument(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            filename=safe_filename,
            mime_type=mime_type or "application/octet-stream",
            storage_key=storage_key,
            created_by=user_id,
        )
        job = IngestionJob(
            tenant_id=tenant_id,
            source_document_id="",
        )
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            event_type="SourceUploaded",
            entity_type="source_document",
            entity_id=source.id,
            description=f"Uploaded {source.filename}",
        )
        return self._repository.create_source(
            source=source,
            job=job,
            audit_event=event,
        )

    def list_ingestion_jobs(self, *, tenant_id: str):
        return self._repository.list_jobs(tenant_id=tenant_id)

    def submit_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
    ) -> KnowledgeCard:
        card = self._require_card(card_id=card_id, tenant_id=tenant_id)
        card.approval_status = "pending_review"
        card.lifecycle_status = "in_review"
        return self._repository.commit_card(card)

    def approve_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        approver_id: str,
        can_approve: bool,
    ) -> KnowledgeCard:
        if not can_approve:
            raise KnowledgePermissionError(
                "Knowledge approval permission required"
            )
        card = self._require_card(card_id=card_id, tenant_id=tenant_id)
        card.approval_status = "approved"
        card.lifecycle_status = "published"
        card.approved_by = approver_id
        card.approved_at = datetime.now(timezone.utc)
        card.trust_score = max(card.trust_score, 0.8)
        return self._repository.commit_card(card)

    def _require_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
    ) -> KnowledgeCard:
        card = self._repository.get_card(
            card_id=card_id,
            tenant_id=tenant_id,
        )
        if card is None:
            raise KnowledgeNotFoundError("Knowledge Card not found")
        return card
