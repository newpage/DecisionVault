from __future__ import annotations

from datetime import datetime, timezone
import json
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
        role_ids: set[str],
        query: str = "",
    ):
        cards = self._repository.list_cards(
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
            query=query,
        )
        provenances = self._repository.provenances(
            tenant_id=tenant_id, card_ids=[card.id for card in cards]
        )
        return [
            {
                column.name: getattr(card, column.name)
                for column in card.__table__.columns
            }
            | {
                "decision_lesson_provenance": provenances.get(
                    card.id
                ).immutable_snapshot
                if provenances.get(card.id)
                else None
            }
            for card in cards
        ]

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

    def governance_queue(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
        can_review: bool,
    ) -> dict:
        if not can_review:
            raise KnowledgePermissionError("Knowledge approval permission required")
        now = datetime.now(timezone.utc)
        items = [
            self._review_view(card, self._repository.review_context(
                tenant_id=tenant_id, card_id=card.id
            ), now=now)
            for card in self._repository.list_review_cards(
                tenant_id=tenant_id,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
            )
        ]
        items.sort(
            key=lambda item: (
                -item["risk_priority"],
                -item["review_age_hours"],
                item["title"].lower(),
            )
        )
        return {
            "summary": {
                "pending_reviews": len(items),
                "critical_items": sum(item["risk_level"] == "critical" for item in items),
                "oldest_pending_hours": max(
                    (item["review_age_hours"] for item in items), default=0
                ),
                "ai_eligible_items": sum(item["ai_eligible_if_approved"] for item in items),
            },
            "review_queue": items,
        }

    def governance_detail(
        self,
        *,
        card_id: str,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
        can_review: bool,
    ) -> dict:
        if not can_review:
            raise KnowledgePermissionError("Knowledge approval permission required")
        card = self._require_card(
            card_id=card_id,
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if card.lifecycle_status != "in_review" or card.approval_status != "pending_review":
            raise KnowledgeNotFoundError("Knowledge Card not found")
        return self._review_view(
            card,
            self._repository.review_context(tenant_id=tenant_id, card_id=card.id),
            now=datetime.now(timezone.utc),
            include_detail=True,
        )

    def submit_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        actor_id: str,
        clearance_rank: int,
        role_ids: set[str],
        can_submit: bool,
    ) -> KnowledgeCard:
        if not can_submit:
            raise KnowledgePermissionError("Knowledge submission permission required")
        card = self._require_card(
            card_id=card_id,
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if card.lifecycle_status != "draft" or card.approval_status != "not_submitted":
            raise KnowledgeValidationError("Only a governed draft can be submitted")
        card.approval_status = "pending_review"
        card.lifecycle_status = "in_review"
        return self._repository.commit_card(
            card,
            self._event(
                card,
                actor_id,
                "KnowledgeSubmitted",
                "Knowledge Card submitted for governance review",
            ),
        )

    def review_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        reviewer_id: str,
        can_approve: bool,
        clearance_rank: int,
        role_ids: set[str],
        action: str,
        rationale: str,
        checklist: dict[str, bool],
    ) -> KnowledgeCard:
        if not can_approve:
            raise KnowledgePermissionError("Knowledge approval permission required")
        card = self._require_card(
            card_id=card_id,
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if (
            card.lifecycle_status != "in_review"
            or card.approval_status != "pending_review"
        ):
            raise KnowledgeValidationError(
                "Only a submitted Knowledge Card can be approved"
            )
        rationale = rationale.strip()
        if len(rationale) < 10:
            raise KnowledgeValidationError("A human rationale of at least 10 characters is required")
        if not all(checklist.values()) or len(checklist) != 5:
            raise KnowledgeValidationError("Every governance checklist item must be reviewed")
        transitions = {
            "approve_publish": ("published", "approved", "KnowledgePublished"),
            "return_correction": ("draft", "not_submitted", "KnowledgeReturnedForCorrection"),
            "reject": ("retired", "rejected", "KnowledgeRejected"),
        }
        if action not in transitions:
            raise KnowledgeValidationError("Unsupported governance action")
        lifecycle_status, approval_status, event_type = transitions[action]
        card.approval_status = approval_status
        card.lifecycle_status = lifecycle_status
        if action == "approve_publish":
            card.approved_by = reviewer_id
            card.approved_at = datetime.now(timezone.utc)
            card.trust_score = max(card.trust_score, 0.8)
        else:
            card.approved_by = None
            card.approved_at = None
        return self._repository.commit_card(
            card,
            self._event(
                card,
                reviewer_id,
                event_type,
                {
                    "approve_publish": "Knowledge Card approved and published",
                    "return_correction": "Knowledge Card returned for correction",
                    "reject": "Knowledge Card rejected",
                }[action],
                details={
                    "action": action,
                    "rationale": rationale,
                    "checklist": checklist,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "ai_eligible_after_action": action == "approve_publish" and card.ai_usage_allowed,
                },
            ),
        )

    def approve_card(self, **kwargs) -> KnowledgeCard:
        """Compatibility wrapper for callers using the original method name."""
        kwargs["reviewer_id"] = kwargs.pop("approver_id")
        kwargs.setdefault("action", "approve_publish")
        kwargs.setdefault("rationale", "Human reviewer approved and published this knowledge.")
        kwargs.setdefault("checklist", {
            "provenance_verified": True,
            "classification_confirmed": True,
            "policy_authority_confirmed": True,
            "conflicts_reviewed": True,
            "ai_eligibility_appropriate": True,
        })
        return self.review_card(**kwargs)

    def _require_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> KnowledgeCard:
        card = self._repository.get_card(
            card_id=card_id,
            tenant_id=tenant_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if card is None:
            raise KnowledgeNotFoundError("Knowledge Card not found")
        return card

    @staticmethod
    def _event(card, actor_id, event_type, description, details=None):
        return AuditEvent(
            tenant_id=card.tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            entity_type="knowledge_card",
            entity_id=card.id,
            description=description,
            details={
                "lifecycle_status": card.lifecycle_status,
                "approval_status": card.approval_status,
            } | (details or {}),
        )

    @staticmethod
    def _structured_body(card: KnowledgeCard) -> dict:
        try:
            parsed = json.loads(card.body)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def _review_view(self, card, context, *, now, include_detail=False) -> dict:
        structured = self._structured_body(card)
        title = card.title.lower()
        explicit_risk = str(structured.get("risk_level", "")).lower()
        if explicit_risk in {"critical", "high", "medium", "low"}:
            risk_level = explicit_risk
        elif "critical" in title or "network" in title and "alert" in title:
            risk_level = "critical"
        elif any(term in title for term in ("fraud", "aml", "chargeback")):
            risk_level = "high"
        else:
            risk_level = "medium"
        priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}[risk_level]
        created = card.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_hours = max(0, int((now - created).total_seconds() // 3600))
        evidence_rows = context["evidence"]
        sources = [
            {
                "filename": source.filename,
                "mime_type": source.mime_type,
                "locator": evidence.locator,
                "excerpt": evidence.excerpt,
            }
            for evidence, source in evidence_rows
        ]
        policy = context["access_policy"]
        view = {
            "id": card.id,
            "title": card.title,
            "summary": card.summary,
            "knowledge_type": card.knowledge_type,
            "risk_level": risk_level,
            "risk_priority": priority,
            "classification_rank": card.classification_rank,
            "classification": self._classification(card.classification_rank),
            "trust_score": round(card.trust_score * 100),
            "review_age_hours": age_hours,
            "authority_level": card.authority_level,
            "policy_relevance": structured.get("policy_relevance")
            or ("Authoritative policy input" if card.authority_level == "approved_policy" else "Material evidence for merchant-risk policy review"),
            "ai_eligible_if_approved": bool(card.ai_usage_allowed),
            "source": sources[0]["filename"] if sources else "No source recorded",
            "provenance": sources[0]["locator"] if sources else "No provenance recorded",
            "created_at": card.created_at.isoformat(),
        }
        if include_detail:
            view |= {
                "extracted_facts": structured.get("facts", []),
                "conflicts": structured.get("conflicts", []),
                "missing_information": structured.get("missing_information", []),
                "sources": sources,
                "access_control": policy.name if policy else "Tenant members with sufficient classification clearance",
                "intended_usage": structured.get("intended_usage")
                or "Governed Decision evidence, grounded retrieval, comparison, and gap analysis after human approval.",
                "what_changes_if_approved": (
                    "The card becomes published governed knowledge and eligible for Decision Intelligence retrieval."
                    if card.ai_usage_allowed
                    else "The card becomes published governed knowledge but remains excluded from AI-assisted retrieval."
                ),
            }
        return view

    @staticmethod
    def _classification(rank: int) -> str:
        if rank >= 80:
            return "Restricted"
        if rank >= 50:
            return "Confidential"
        if rank >= 20:
            return "Internal"
        return "Public"
