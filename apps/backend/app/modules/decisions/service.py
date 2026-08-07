from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import AuditEvent, DecisionCase, DecisionEvidence, uid
from app.modules.decisions.evidence import (
    require_rationale,
    scoring_inputs,
    validate_relationship_type,
)
from app.modules.decisions.lifecycle import allowed_transitions
from app.modules.decisions.policies import (
    authorize_create,
    authorize_edit,
    authorize_evidence_history,
    authorize_evidence_remove,
    authorize_evidence_select,
    authorize_evidence_view,
    authorize_view,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.schemas import (
    DecisionCreate,
    AvailableEvidenceResponse,
    EvidenceMutationResponse,
    EvidenceResponse,
    DecisionResponse,
    DecisionWorkspaceResponse,
)
from app.modules.decisions.scoring import (
    calculate_readiness,
    generate_recommendation,
)


class DecisionNotFoundError(LookupError):
    """Raised for absent and foreign-tenant Decision resources."""


class DecisionConflictError(ValueError):
    """Raised when an evidence selection conflicts with active state."""


class DecisionService:
    """Application operations for Decision Intelligence."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def list_decisions(
        self,
        *,
        tenant_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
    ) -> list[DecisionResponse]:
        authorize_view(permissions)
        return [
            DecisionResponse.model_validate(item)
            for item in self._repository.list_decisions(
                tenant_id=tenant_id,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
            )
        ]

    def get_workspace(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
    ) -> DecisionWorkspaceResponse:
        authorize_view(permissions)
        authorize_evidence_view(permissions)
        decision = self._require_decision(tenant_id=tenant_id, decision_id=decision_id)
        if getattr(decision, "classification_rank", 0) > clearance_rank:
            raise DecisionNotFoundError("Decision not found")
        access_policy_id = getattr(decision, "access_policy_id", None)
        if (
            access_policy_id
            and self._repository.get_authorized_access_policy(
                tenant_id=tenant_id,
                policy_id=access_policy_id,
                role_ids=role_ids,
            )
            is None
        ):
            raise DecisionNotFoundError("Decision not found")
        concept = (
            self._repository.get_concept(
                tenant_id=tenant_id,
                concept_id=decision.business_concept_id,
            )
            if decision.business_concept_id
            else None
        )
        evidence = self._repository.list_active_evidence(
            tenant_id=tenant_id, decision_id=decision.id
        )
        activity = self._repository.list_activity(
            tenant_id=tenant_id, decision_id=decision.id
        )
        readiness = calculate_readiness(scoring_inputs(evidence))
        summary = decision.evidence_summary or {}
        return DecisionWorkspaceResponse.model_validate(
            {
                "decision": decision,
                "business_concept": concept,
                "evidence": evidence,
                "activity": activity,
                "workspace_summary": {
                    "evidence_count": len(evidence),
                    "approved_count": readiness.approved,
                    "trusted_count": readiness.trusted,
                    "governed_count": readiness.governed,
                    "confidence_percent": round(decision.confidence * 100),
                    "missing_information": summary.get("missing_information", []),
                    "control_areas": summary.get("control_areas", []),
                    "calculation": summary.get("calculation", {}),
                    "allowed_transitions": allowed_transitions(decision.status),
                },
            }
        )

    def create_decision(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
        command: DecisionCreate,
    ) -> DecisionResponse:
        authorize_create(permissions)
        if (
            self._repository.get_workspace(
                tenant_id=tenant_id, workspace_id=command.workspace_id
            )
            is None
        ):
            raise DecisionNotFoundError("Workspace not found")
        concept = (
            self._repository.get_concept(
                tenant_id=tenant_id,
                concept_id=command.business_concept_id,
            )
            if command.business_concept_id
            else self._repository.get_default_concept(tenant_id=tenant_id)
        )
        if concept is None:
            raise DecisionNotFoundError("Business Concept not found")
        if command.classification_rank > clearance_rank:
            raise DecisionNotFoundError("Decision access policy not found")
        if command.access_policy_id and (
            not role_ids
            or self._repository.get_authorized_access_policy(
                tenant_id=tenant_id,
                policy_id=command.access_policy_id,
                role_ids=role_ids,
            )
            is None
        ):
            raise DecisionNotFoundError("Decision access policy not found")
        readiness = calculate_readiness([])
        decision = DecisionCase(
            tenant_id=tenant_id,
            workspace_id=command.workspace_id,
            business_concept_id=concept.id,
            classification_rank=command.classification_rank,
            access_policy_id=command.access_policy_id,
            title=command.title,
            question=command.question,
            status="evidence_collection",
            recommendation=generate_recommendation(
                supplier_name=command.supplier_name, readiness=readiness
            ),
            confidence=readiness.score / 100,
            supplier_name=command.supplier_name,
            supplier_category=command.supplier_category,
            supplier_location=command.supplier_location,
            owner_name=command.owner_name,
            due_date=command.due_date,
            priority=command.priority,
            risk_level=command.risk_level,
            decision_type=command.decision_type,
            business_unit=command.business_unit,
            readiness_score=readiness.score,
            readiness_status=readiness.status,
            evidence_summary=readiness.summary,
            input_revision=1,
            created_by=actor_id,
        )
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="DecisionCreated",
            entity_type="decision_case",
            description=(
                f"Governed decision created for {command.supplier_name}."
            ),
            details={
                "supplier_category": command.supplier_category,
                "readiness_score": readiness.score,
                "risk_level": command.risk_level,
                "evidence_count": readiness.total,
            },
        )
        saved = self._repository.save_with_audit(decision=decision, event=event)
        return DecisionResponse.model_validate(saved)

    def list_available_evidence(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
    ) -> list[AvailableEvidenceResponse]:
        authorize_evidence_view(permissions)
        authorize_view(permissions)
        decision = self._require_decision(tenant_id=tenant_id, decision_id=decision_id)
        if not decision.business_concept_id:
            return []
        rows = self._repository.list_available_evidence(
            tenant_id=tenant_id,
            concept_id=decision.business_concept_id,
            workspace_id=decision.workspace_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        active_card_ids = {
            item.knowledge_card_id
            for item in self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision.id
            )
        }
        return [
            AvailableEvidenceResponse.model_validate(
                {
                    "id": card.id,
                    "title": card.title,
                    "summary": card.summary,
                    "knowledge_type": card.knowledge_type,
                    "authority_level": card.authority_level,
                    "trust_score": card.trust_score,
                    "ai_usage_allowed": card.ai_usage_allowed,
                    "chunks": chunks,
                    "selected": card.id in active_card_ids,
                }
            )
            for card, chunks in rows
        ]

    def list_active_evidence(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        permissions: set[str],
    ) -> list[EvidenceResponse]:
        authorize_evidence_view(permissions)
        authorize_view(permissions)
        self._require_decision(tenant_id=tenant_id, decision_id=decision_id)
        return [
            EvidenceResponse.model_validate(item)
            for item in self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision_id
            )
        ]

    def list_evidence_history(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        permissions: set[str],
    ) -> list[EvidenceResponse]:
        authorize_evidence_history(permissions)
        authorize_view(permissions)
        self._require_decision(tenant_id=tenant_id, decision_id=decision_id)
        return [
            EvidenceResponse.model_validate(item)
            for item in self._repository.list_evidence_history(
                tenant_id=tenant_id, decision_id=decision_id
            )
        ]

    def select_evidence(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
        card_id: str,
        chunk_id: str | None,
        relationship_type: str,
        rationale: str,
    ) -> EvidenceMutationResponse:
        authorize_evidence_select(permissions)
        authorize_edit(permissions)
        validate_relationship_type(relationship_type)
        rationale = require_rationale(rationale, action="selection")
        decision = self._repository.get_decision_for_update(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        if not decision.business_concept_id:
            raise DecisionNotFoundError("Knowledge Card not found")
        card = self._repository.get_authorized_card(
            tenant_id=tenant_id,
            card_id=card_id,
            concept_id=decision.business_concept_id,
            workspace_id=decision.workspace_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if card is None:
            raise DecisionNotFoundError("Knowledge Card not found")
        chunk = None
        if chunk_id:
            chunk = self._repository.get_chunk(
                tenant_id=tenant_id, card_id=card.id, chunk_id=chunk_id
            )
            if chunk is None:
                raise DecisionNotFoundError("Knowledge Chunk not found")
        if self._repository.has_active_selection(
            tenant_id=tenant_id,
            decision_id=decision.id,
            card_id=card.id,
        ):
            raise DecisionConflictError("Evidence is already selected")
        source = self._repository.get_source_snapshot(
            tenant_id=tenant_id, card_id=card.id
        )
        knowledge_evidence, source_document = source or (None, None)
        snapshot = DecisionEvidence(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            knowledge_card_id=card.id,
            knowledge_chunk_id=chunk.id if chunk else None,
            source_document_id=(source_document.id if source_document else None),
            relationship_type=relationship_type,
            selection_rationale=rationale,
            snapshot_title=card.title,
            snapshot_content=chunk.content if chunk else card.body,
            snapshot_source_filename=(
                source_document.filename if source_document else ""
            ),
            snapshot_source_mime_type=(
                source_document.mime_type if source_document else ""
            ),
            snapshot_source_locator=(
                knowledge_evidence.locator if knowledge_evidence else ""
            ),
            snapshot_knowledge_type=card.knowledge_type,
            snapshot_authority_level=card.authority_level,
            snapshot_lifecycle_status=card.lifecycle_status,
            snapshot_approval_status=card.approval_status,
            snapshot_classification_rank=card.classification_rank,
            snapshot_access_policy_id=card.access_policy_id,
            snapshot_trust_score=card.trust_score,
            snapshot_ai_usage_allowed=card.ai_usage_allowed,
            snapshot_card_created_at=card.created_at,
            snapshot_content_revision=None,
            snapshot_source_metadata={
                "chunk_index": chunk.chunk_index if chunk else None,
                "source_status": (source_document.status if source_document else None),
            },
            selected_by=actor_id,
        )
        active = self._repository.list_active_evidence(
            tenant_id=tenant_id, decision_id=decision.id
        )
        before = self._derived_values(decision)
        self._recalculate(decision, [*active, snapshot])
        decision.input_revision = getattr(decision, "input_revision", 1) + 1
        stale_reviews = (
            self._repository.mark_completed_reviews_stale(
                tenant_id=tenant_id, decision_id=decision.id
            )
            if hasattr(self._repository, "mark_completed_reviews_stale")
            else []
        )
        events = self._evidence_events(
            decision=decision,
            snapshot=snapshot,
            actor_id=actor_id,
            action="selected",
            rationale=rationale,
            before=before,
        )
        events.extend(self._stale_review_events(decision, stale_reviews, actor_id))
        try:
            saved_decision, saved_snapshot = self._repository.save_evidence_change(
                decision=decision, evidence=snapshot, events=events
            )
        except IntegrityError as exc:
            raise DecisionConflictError("Evidence is already selected") from exc
        return EvidenceMutationResponse(
            decision=DecisionResponse.model_validate(saved_decision),
            evidence=EvidenceResponse.model_validate(saved_snapshot),
        )

    def remove_evidence(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        evidence_id: str,
        actor_id: str,
        permissions: set[str],
        rationale: str,
    ) -> EvidenceMutationResponse:
        authorize_evidence_remove(permissions)
        authorize_edit(permissions)
        rationale = require_rationale(rationale, action="removal")
        decision = self._repository.get_decision_for_update(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        evidence = self._repository.get_evidence(
            tenant_id=tenant_id,
            decision_id=decision.id,
            evidence_id=evidence_id,
        )
        if evidence is None or evidence.removed_at is not None:
            raise DecisionNotFoundError("Decision evidence not found")
        evidence.removed_at = datetime.now(timezone.utc)
        evidence.removed_by = actor_id
        evidence.removal_rationale = rationale
        active = [
            item
            for item in self._repository.list_active_evidence(
                tenant_id=tenant_id, decision_id=decision.id
            )
            if item.id != evidence.id
        ]
        before = self._derived_values(decision)
        self._recalculate(decision, active)
        decision.input_revision = getattr(decision, "input_revision", 1) + 1
        stale_reviews = (
            self._repository.mark_completed_reviews_stale(
                tenant_id=tenant_id, decision_id=decision.id
            )
            if hasattr(self._repository, "mark_completed_reviews_stale")
            else []
        )
        events = self._evidence_events(
            decision=decision,
            snapshot=evidence,
            actor_id=actor_id,
            action="removed",
            rationale=rationale,
            before=before,
        )
        events.extend(self._stale_review_events(decision, stale_reviews, actor_id))
        saved_decision, saved_evidence = self._repository.save_evidence_change(
            decision=decision, evidence=evidence, events=events
        )
        return EvidenceMutationResponse(
            decision=DecisionResponse.model_validate(saved_decision),
            evidence=EvidenceResponse.model_validate(saved_evidence),
        )

    @staticmethod
    def _derived_values(decision: DecisionCase) -> dict:
        return {
            "readiness_score": decision.readiness_score,
            "readiness_status": decision.readiness_status,
            "confidence": decision.confidence,
        }

    def _recalculate(
        self, decision: DecisionCase, evidence: list[DecisionEvidence]
    ) -> None:
        readiness = calculate_readiness(scoring_inputs(evidence))
        decision.readiness_score = readiness.score
        decision.readiness_status = readiness.status
        decision.confidence = readiness.score / 100
        decision.evidence_summary = readiness.summary
        decision.recommendation = generate_recommendation(
            supplier_name=decision.supplier_name, readiness=readiness
        )
        decision.updated_at = datetime.now(timezone.utc)

    def _evidence_events(
        self,
        *,
        decision: DecisionCase,
        snapshot: DecisionEvidence,
        actor_id: str,
        action: str,
        rationale: str,
        before: dict,
    ) -> list[AuditEvent]:
        facts = {
            "decision_id": decision.id,
            "evidence_snapshot_id": snapshot.id,
            "knowledge_card_id": snapshot.knowledge_card_id,
            "knowledge_chunk_id": snapshot.knowledge_chunk_id,
            "relationship_type": snapshot.relationship_type,
            "rationale": rationale,
        }
        return [
            AuditEvent(
                tenant_id=decision.tenant_id,
                actor_id=actor_id,
                event_type=(
                    "DecisionEvidenceSelected"
                    if action == "selected"
                    else "DecisionEvidenceRemoved"
                ),
                entity_type="decision_case",
                description=f"Decision evidence {action}.",
                details=facts,
            ),
            AuditEvent(
                tenant_id=decision.tenant_id,
                actor_id=actor_id,
                event_type="DecisionRecalculated",
                entity_type="decision_case",
                description=f"Decision recalculated after evidence was {action}.",
                details={
                    **facts,
                    "before": before,
                    "after": self._derived_values(decision),
                },
            ),
        ]

    @staticmethod
    def _stale_review_events(
        decision: DecisionCase, reviews: list, actor_id: str
    ) -> list[AuditEvent]:
        return [
            AuditEvent(
                tenant_id=decision.tenant_id,
                actor_id=actor_id,
                event_type="DecisionReviewMarkedStale",
                entity_type="decision_case",
                entity_id=decision.id,
                description="Completed review marked stale after Decision inputs changed.",
                details={
                    "review_id": review.id,
                    "input_revision": decision.input_revision,
                },
            )
            for review in reviews
        ]

    def _require_decision(self, *, tenant_id: str, decision_id: str) -> DecisionCase:
        decision = self._repository.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision
