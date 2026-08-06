from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    DecisionEvidence,
    KnowledgeCard,
    KnowledgeChunk,
    KnowledgeEvidence,
    SourceDocument,
    Workspace,
)
from app.modules.knowledge.policies import authorized_knowledge_filters


class DecisionRepository:
    """Tenant-aware persistence for Decision Intelligence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_decisions(self, *, tenant_id: str) -> list[DecisionCase]:
        return list(
            self._db.scalars(
                select(DecisionCase)
                .where(DecisionCase.tenant_id == tenant_id)
                .order_by(DecisionCase.created_at.desc())
            ).all()
        )

    def get_decision(
        self, *, tenant_id: str, decision_id: str
    ) -> DecisionCase | None:
        return self._db.scalar(
            select(DecisionCase).where(
                DecisionCase.id == decision_id,
                DecisionCase.tenant_id == tenant_id,
            )
        )

    def get_decision_for_update(
        self, *, tenant_id: str, decision_id: str
    ) -> DecisionCase | None:
        return self._db.scalar(
            select(DecisionCase)
            .where(
                DecisionCase.id == decision_id,
                DecisionCase.tenant_id == tenant_id,
            )
            .with_for_update()
        )

    def get_workspace(
        self, *, tenant_id: str, workspace_id: str
    ) -> Workspace | None:
        return self._db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == tenant_id,
            )
        )

    def get_concept(
        self, *, tenant_id: str, concept_id: str
    ) -> BusinessConcept | None:
        return self._db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.id == concept_id,
                BusinessConcept.tenant_id == tenant_id,
            )
        )

    def get_default_concept(self, *, tenant_id: str) -> BusinessConcept | None:
        return self._db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.tenant_id == tenant_id,
                BusinessConcept.slug == "supplier-qualification",
            )
        )

    def list_authorized_evidence(
        self,
        *,
        tenant_id: str,
        concept_id: str,
        workspace_id: str,
        clearance_rank: int,
        role_ids: set[str],
        require_published: bool = False,
    ) -> list[KnowledgeCard]:
        statement = (
            select(KnowledgeCard)
            .where(
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.workspace_id == workspace_id,
                KnowledgeCard.business_concept_id == concept_id,
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank,
                    role_ids=role_ids,
                    require_published=require_published,
                ),
            )
            .order_by(
                KnowledgeCard.approval_status.desc(),
                KnowledgeCard.trust_score.desc(),
                KnowledgeCard.created_at.desc(),
            )
        )
        return list(self._db.scalars(statement).all())

    def list_available_evidence(
        self,
        *,
        tenant_id: str,
        concept_id: str,
        workspace_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> list[tuple[KnowledgeCard, list[KnowledgeChunk]]]:
        cards = self.list_authorized_evidence(
            tenant_id=tenant_id,
            concept_id=concept_id,
            workspace_id=workspace_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
            require_published=True,
        )
        card_ids = [card.id for card in cards]
        chunks = (
            list(
                self._db.scalars(
                    select(KnowledgeChunk)
                    .where(
                        KnowledgeChunk.tenant_id == tenant_id,
                        KnowledgeChunk.knowledge_card_id.in_(card_ids),
                    )
                    .order_by(
                        KnowledgeChunk.knowledge_card_id,
                        KnowledgeChunk.chunk_index,
                    )
                ).all()
            )
            if card_ids
            else []
        )
        by_card: dict[str, list[KnowledgeChunk]] = {
            card_id: [] for card_id in card_ids
        }
        for chunk in chunks:
            by_card[chunk.knowledge_card_id].append(chunk)
        return [(card, by_card[card.id]) for card in cards]

    def get_authorized_card(
        self,
        *,
        tenant_id: str,
        card_id: str,
        concept_id: str,
        workspace_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> KnowledgeCard | None:
        return self._db.scalar(
            select(KnowledgeCard).where(
                KnowledgeCard.id == card_id,
                KnowledgeCard.tenant_id == tenant_id,
                KnowledgeCard.workspace_id == workspace_id,
                KnowledgeCard.business_concept_id == concept_id,
                *authorized_knowledge_filters(
                    clearance_rank=clearance_rank,
                    role_ids=role_ids,
                    require_published=True,
                ),
            )
        )

    def get_chunk(
        self, *, tenant_id: str, card_id: str, chunk_id: str
    ) -> KnowledgeChunk | None:
        return self._db.scalar(
            select(KnowledgeChunk).where(
                KnowledgeChunk.id == chunk_id,
                KnowledgeChunk.tenant_id == tenant_id,
                KnowledgeChunk.knowledge_card_id == card_id,
            )
        )

    def get_source_snapshot(
        self, *, tenant_id: str, card_id: str
    ) -> tuple[KnowledgeEvidence, SourceDocument] | None:
        row = self._db.execute(
            select(KnowledgeEvidence, SourceDocument)
            .join(
                SourceDocument,
                (SourceDocument.id == KnowledgeEvidence.source_document_id)
                & (SourceDocument.tenant_id == tenant_id),
            )
            .where(
                KnowledgeEvidence.tenant_id == tenant_id,
                KnowledgeEvidence.knowledge_card_id == card_id,
            )
            .order_by(KnowledgeEvidence.id)
            .limit(1)
        ).first()
        return (row[0], row[1]) if row else None

    def list_active_evidence(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionEvidence]:
        return list(
            self._db.scalars(
                select(DecisionEvidence)
                .where(
                    DecisionEvidence.tenant_id == tenant_id,
                    DecisionEvidence.decision_case_id == decision_id,
                    DecisionEvidence.removed_at.is_(None),
                )
                .order_by(DecisionEvidence.selected_at.desc())
            ).all()
        )

    def list_evidence_history(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionEvidence]:
        return list(
            self._db.scalars(
                select(DecisionEvidence)
                .where(
                    DecisionEvidence.tenant_id == tenant_id,
                    DecisionEvidence.decision_case_id == decision_id,
                )
                .order_by(DecisionEvidence.selected_at.desc())
            ).all()
        )

    def get_evidence(
        self, *, tenant_id: str, decision_id: str, evidence_id: str
    ) -> DecisionEvidence | None:
        return self._db.scalar(
            select(DecisionEvidence).where(
                DecisionEvidence.id == evidence_id,
                DecisionEvidence.tenant_id == tenant_id,
                DecisionEvidence.decision_case_id == decision_id,
            )
        )

    def has_active_selection(
        self, *, tenant_id: str, decision_id: str, card_id: str
    ) -> bool:
        return (
            self._db.scalar(
                select(DecisionEvidence.id).where(
                    DecisionEvidence.tenant_id == tenant_id,
                    DecisionEvidence.decision_case_id == decision_id,
                    DecisionEvidence.knowledge_card_id == card_id,
                    DecisionEvidence.removed_at.is_(None),
                )
            )
            is not None
        )

    def list_activity(
        self, *, tenant_id: str, decision_id: str, limit: int = 25
    ) -> list[AuditEvent]:
        return list(
            self._db.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.entity_type == "decision_case",
                    AuditEvent.entity_id == decision_id,
                )
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            ).all()
        )

    def save_with_audit(
        self, *, decision: DecisionCase, event: AuditEvent
    ) -> DecisionCase:
        try:
            self._db.add(decision)
            self._db.flush()
            event.entity_id = decision.id
            self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(decision)
        return decision

    def save_evidence_change(
        self,
        *,
        decision: DecisionCase,
        evidence: DecisionEvidence,
        events: list[AuditEvent],
    ) -> tuple[DecisionCase, DecisionEvidence]:
        try:
            self._db.add(decision)
            self._db.add(evidence)
            self._db.flush()
            for event in events:
                event.entity_id = decision.id
                self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(decision)
        self._db.refresh(evidence)
        return decision, evidence
