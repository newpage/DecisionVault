from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    AccessPolicy,
    AccessPolicyRole,
    BusinessConcept,
    DecisionCase,
    DecisionEvidence,
    DecisionExpectedOutcome,
    DecisionApprovalAction,
    DecisionApprovalCondition,
    DecisionReview,
    DecisionReviewAssignment,
    DecisionReviewEvidence,
    DecisionReviewFinding,
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

    def list_decisions(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
    ) -> list[DecisionCase]:
        policy_allowed = (
            exists(
                select(AccessPolicyRole.policy_id).where(
                    AccessPolicyRole.policy_id == DecisionCase.access_policy_id,
                    AccessPolicyRole.role_id.in_(role_ids),
                )
            )
            if role_ids
            else False
        )
        return list(
            self._db.scalars(
                select(DecisionCase)
                .where(
                    DecisionCase.tenant_id == tenant_id,
                    DecisionCase.classification_rank <= clearance_rank,
                    DecisionCase.access_policy_id.is_(None) | policy_allowed,
                )
                .order_by(DecisionCase.created_at.desc())
            ).all()
        )

    def get_decision(self, *, tenant_id: str, decision_id: str) -> DecisionCase | None:
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

    def get_workspace(self, *, tenant_id: str, workspace_id: str) -> Workspace | None:
        return self._db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == tenant_id,
            )
        )

    def get_concept(self, *, tenant_id: str, concept_id: str) -> BusinessConcept | None:
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

    def get_authorized_access_policy(
        self, *, tenant_id: str, policy_id: str, role_ids: set[str]
    ) -> AccessPolicy | None:
        return self._db.scalar(
            select(AccessPolicy).where(
                AccessPolicy.tenant_id == tenant_id,
                AccessPolicy.id == policy_id,
                exists(
                    select(AccessPolicyRole.policy_id).where(
                        AccessPolicyRole.policy_id == AccessPolicy.id,
                        AccessPolicyRole.role_id.in_(role_ids),
                    )
                ),
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
        by_card: dict[str, list[KnowledgeChunk]] = {card_id: [] for card_id in card_ids}
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

    def next_review_sequence(self, *, tenant_id: str, decision_id: str) -> int:
        current = self._db.scalar(
            select(func.max(DecisionReview.sequence)).where(
                DecisionReview.tenant_id == tenant_id,
                DecisionReview.decision_case_id == decision_id,
            )
        )
        return int(current or 0) + 1

    def has_active_reviewer_type(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        membership_id: str,
        review_type: str,
        exclude_review_id: str | None = None,
    ) -> bool:
        statement = select(DecisionReview.id).where(
            DecisionReview.tenant_id == tenant_id,
            DecisionReview.decision_case_id == decision_id,
            DecisionReview.assigned_reviewer_membership_id == membership_id,
            DecisionReview.review_type == review_type,
            DecisionReview.status.in_({"assigned", "in_progress"}),
        )
        if exclude_review_id:
            statement = statement.where(DecisionReview.id != exclude_review_id)
        return self._db.scalar(statement) is not None

    def list_assignment_history(
        self, *, tenant_id: str, review_id: str
    ) -> list[DecisionReviewAssignment]:
        return list(
            self._db.scalars(
                select(DecisionReviewAssignment)
                .where(
                    DecisionReviewAssignment.tenant_id == tenant_id,
                    DecisionReviewAssignment.review_id == review_id,
                )
                .order_by(DecisionReviewAssignment.assigned_at)
            ).all()
        )

    def list_reviews(self, *, tenant_id: str, decision_id: str) -> list[DecisionReview]:
        return list(
            self._db.scalars(
                select(DecisionReview)
                .where(
                    DecisionReview.tenant_id == tenant_id,
                    DecisionReview.decision_case_id == decision_id,
                )
                .order_by(DecisionReview.sequence.desc())
            ).all()
        )

    def get_review(
        self, *, tenant_id: str, decision_id: str, review_id: str
    ) -> DecisionReview | None:
        return self._db.scalar(
            select(DecisionReview).where(
                DecisionReview.id == review_id,
                DecisionReview.tenant_id == tenant_id,
                DecisionReview.decision_case_id == decision_id,
            )
        )

    def get_review_for_update(
        self, *, tenant_id: str, decision_id: str, review_id: str
    ) -> DecisionReview | None:
        return self._db.scalar(
            select(DecisionReview)
            .where(
                DecisionReview.id == review_id,
                DecisionReview.tenant_id == tenant_id,
                DecisionReview.decision_case_id == decision_id,
            )
            .with_for_update()
        )

    def list_review_evidence_ids(self, *, tenant_id: str, review_id: str) -> list[str]:
        return list(
            self._db.scalars(
                select(DecisionReviewEvidence.decision_evidence_id).where(
                    DecisionReviewEvidence.tenant_id == tenant_id,
                    DecisionReviewEvidence.review_id == review_id,
                )
            ).all()
        )

    def list_findings(
        self, *, tenant_id: str, decision_id: str, review_id: str | None = None
    ) -> list[DecisionReviewFinding]:
        statement = (
            select(DecisionReviewFinding)
            .join(
                DecisionReview,
                (DecisionReview.id == DecisionReviewFinding.review_id)
                & (DecisionReview.tenant_id == tenant_id),
            )
            .where(
                DecisionReviewFinding.tenant_id == tenant_id,
                DecisionReview.decision_case_id == decision_id,
            )
        )
        if review_id:
            statement = statement.where(DecisionReviewFinding.review_id == review_id)
        return list(
            self._db.scalars(
                statement.order_by(DecisionReviewFinding.raised_at.desc())
            ).all()
        )

    def get_finding(
        self, *, tenant_id: str, review_id: str, finding_id: str
    ) -> DecisionReviewFinding | None:
        return self._db.scalar(
            select(DecisionReviewFinding).where(
                DecisionReviewFinding.id == finding_id,
                DecisionReviewFinding.tenant_id == tenant_id,
                DecisionReviewFinding.review_id == review_id,
            )
        )

    def list_approval_actions(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionApprovalAction]:
        return list(
            self._db.scalars(
                select(DecisionApprovalAction)
                .where(
                    DecisionApprovalAction.tenant_id == tenant_id,
                    DecisionApprovalAction.decision_case_id == decision_id,
                )
                .order_by(DecisionApprovalAction.created_at.desc())
            ).all()
        )

    def list_conditions(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionApprovalCondition]:
        return list(
            self._db.scalars(
                select(DecisionApprovalCondition)
                .where(
                    DecisionApprovalCondition.tenant_id == tenant_id,
                    DecisionApprovalCondition.decision_case_id == decision_id,
                )
                .order_by(DecisionApprovalCondition.created_at)
            ).all()
        )

    def get_condition(
        self, *, tenant_id: str, decision_id: str, condition_id: str
    ) -> DecisionApprovalCondition | None:
        return self._db.scalar(
            select(DecisionApprovalCondition).where(
                DecisionApprovalCondition.id == condition_id,
                DecisionApprovalCondition.tenant_id == tenant_id,
                DecisionApprovalCondition.decision_case_id == decision_id,
            )
        )

    def mark_completed_reviews_stale(
        self, *, tenant_id: str, decision_id: str
    ) -> list[DecisionReview]:
        reviews = self.list_reviews(tenant_id=tenant_id, decision_id=decision_id)
        stale = []
        for review in reviews:
            if review.status == "completed" and review.freshness_status == "current":
                review.freshness_status = "stale"
                self._db.add(review)
                stale.append(review)
        return stale

    def freeze_expected_outcomes(
        self, *, tenant_id: str, decision_id: str, frozen_at
    ) -> list[DecisionExpectedOutcome]:
        outcomes = list(
            self._db.scalars(
                select(DecisionExpectedOutcome).where(
                    DecisionExpectedOutcome.tenant_id == tenant_id,
                    DecisionExpectedOutcome.decision_case_id == decision_id,
                    DecisionExpectedOutcome.status == "active",
                    DecisionExpectedOutcome.frozen_at.is_(None),
                )
            ).all()
        )
        for outcome in outcomes:
            outcome.frozen_at = frozen_at
            self._db.add(outcome)
        return outcomes

    def save_review_action(
        self,
        *,
        objects: list,
        events: list[AuditEvent],
        refresh: list | None = None,
    ) -> None:
        try:
            for item in objects:
                self._db.add(item)
            self._db.flush()
            for event in events:
                self._db.add(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        for item in refresh or []:
            self._db.refresh(item)

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
