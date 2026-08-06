from __future__ import annotations

from datetime import datetime, timezone

from app.models import AuditEvent, DecisionCase
from app.modules.decisions.lifecycle import (
    allowed_transitions,
    validate_transition,
)
from app.modules.decisions.policies import (
    authorize_create,
    authorize_transition,
    authorize_view,
)
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.schemas import (
    DecisionCreate,
    DecisionResponse,
    DecisionWorkspaceResponse,
)
from app.modules.decisions.scoring import (
    calculate_readiness,
    generate_recommendation,
)


class DecisionNotFoundError(LookupError):
    """Raised for absent and foreign-tenant Decision resources."""


class DecisionService:
    """Application operations for Decision Intelligence."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def list_decisions(
        self, *, tenant_id: str, permissions: set[str]
    ) -> list[DecisionResponse]:
        authorize_view(permissions)
        return [
            DecisionResponse.model_validate(item)
            for item in self._repository.list_decisions(tenant_id=tenant_id)
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
        decision = self._require_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        concept = (
            self._repository.get_concept(
                tenant_id=tenant_id,
                concept_id=decision.business_concept_id,
            )
            if decision.business_concept_id
            else None
        )
        evidence = (
            self._repository.list_authorized_evidence(
                tenant_id=tenant_id,
                concept_id=decision.business_concept_id,
                workspace_id=decision.workspace_id,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
            )
            if decision.business_concept_id
            else []
        )
        activity = self._repository.list_activity(
            tenant_id=tenant_id, decision_id=decision.id
        )
        readiness = calculate_readiness(evidence)
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
                    "missing_information": summary.get(
                        "missing_information", []
                    ),
                    "control_areas": summary.get("control_areas", []),
                    "calculation": summary.get("calculation", {}),
                    "allowed_transitions": allowed_transitions(
                        decision.status
                    ),
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
        if self._repository.get_workspace(
            tenant_id=tenant_id, workspace_id=command.workspace_id
        ) is None:
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
        evidence = self._repository.list_authorized_evidence(
            tenant_id=tenant_id,
            concept_id=concept.id,
            workspace_id=command.workspace_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        readiness = calculate_readiness(evidence)
        decision = DecisionCase(
            tenant_id=tenant_id,
            workspace_id=command.workspace_id,
            business_concept_id=concept.id,
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
            created_by=actor_id,
        )
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="DecisionCreated",
            entity_type="decision_case",
            description=(
                "Supplier qualification decision created for "
                f"{command.supplier_name}."
            ),
            details={
                "supplier_category": command.supplier_category,
                "readiness_score": readiness.score,
                "risk_level": command.risk_level,
                "evidence_count": readiness.total,
            },
        )
        saved = self._repository.save_with_audit(
            decision=decision, event=event
        )
        return DecisionResponse.model_validate(saved)

    def transition(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        actor_id: str,
        permissions: set[str],
        status: str,
        rationale: str = "",
    ) -> DecisionResponse:
        authorize_transition(permissions)
        decision = self._require_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        validate_transition(current=decision.status, requested=status)
        previous = decision.status
        decision.status = status
        decision.updated_at = datetime.now(timezone.utc)
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="DecisionStatusChanged",
            entity_type="decision_case",
            entity_id=decision.id,
            description=f"Decision status changed from {previous} to {status}.",
            details={
                "previous": previous,
                "current": status,
                "rationale": rationale,
            },
        )
        saved = self._repository.save_with_audit(
            decision=decision, event=event
        )
        return DecisionResponse.model_validate(saved)

    def _require_decision(
        self, *, tenant_id: str, decision_id: str
    ) -> DecisionCase:
        decision = self._repository.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision
