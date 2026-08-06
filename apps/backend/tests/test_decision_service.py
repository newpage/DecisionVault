from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.decisions.lifecycle import InvalidTransitionError
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.schemas import DecisionCreate
from app.modules.decisions.service import DecisionNotFoundError, DecisionService


class FakeRepository:
    def __init__(self):
        self.decision = SimpleNamespace(
            id="decision-1",
            tenant_id="tenant-1",
            workspace_id="workspace-1",
            business_concept_id="concept-1",
            title="Qualify Acme",
            question="Should Acme be approved?",
            status="evidence_collection",
            recommendation="Review evidence.",
            confidence=0.85,
            supplier_name="Acme",
            supplier_category="Manufacturer",
            supplier_location="",
            owner_name="Owner",
            due_date=None,
            priority="high",
            risk_level="medium",
            decision_type="initial_qualification",
            business_unit="Supply Chain",
            readiness_score=85,
            readiness_status="review_required",
            evidence_summary={},
            created_by="user-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.saved = None

    def get_decision(self, *, tenant_id, decision_id):
        if tenant_id == "tenant-1" and decision_id == self.decision.id:
            return self.decision
        return None

    def save_with_audit(self, *, decision, event):
        self.saved = (decision, event)
        return decision


class FakeCreationRepository(FakeRepository):
    def __init__(self):
        super().__init__()
        self.workspace = SimpleNamespace(id="workspace-1")
        self.concept = SimpleNamespace(id="concept-1")
        self.evidence = [
            SimpleNamespace(
                approval_status="approved",
                trust_score=0.9,
                ai_usage_allowed=True,
            )
            for _ in range(4)
        ]

    def get_workspace(self, *, tenant_id, workspace_id):
        if tenant_id == "tenant-1" and workspace_id == self.workspace.id:
            return self.workspace
        return None

    def get_concept(self, *, tenant_id, concept_id):
        if tenant_id == "tenant-1" and concept_id == self.concept.id:
            return self.concept
        return None

    def get_default_concept(self, *, tenant_id):
        return self.concept if tenant_id == "tenant-1" else None

    def list_authorized_evidence(self, **kwargs):
        return self.evidence

    def save_with_audit(self, *, decision, event):
        now = datetime.now(timezone.utc)
        decision.id = "decision-created"
        decision.created_at = now
        decision.updated_at = now
        event.entity_id = decision.id
        self.saved = (decision, event)
        return decision


def create_command(**overrides):
    values = {
        "workspace_id": "workspace-1",
        "business_concept_id": "concept-1",
        "title": "Qualify Acme",
        "question": "Should Acme be approved?",
        "supplier_name": "Acme",
        "owner_name": "Owner",
    }
    values.update(overrides)
    return DecisionCreate.model_validate(values)


def test_creation_starts_without_selected_evidence_and_writes_audit():
    repository = FakeCreationRepository()
    service = DecisionService(repository)

    response = service.create_decision(
        tenant_id="tenant-1",
        actor_id="user-1",
        clearance_rank=20,
        role_ids={"role-1"},
        permissions={"decision.create"},
        command=create_command(),
    )

    decision, event = repository.saved
    assert response.readiness_score == 0
    assert decision.tenant_id == "tenant-1"
    assert event.event_type == "DecisionCreated"
    assert event.details["evidence_count"] == 0


@pytest.mark.parametrize(
    "command",
    [
        create_command(workspace_id="foreign-workspace"),
        create_command(business_concept_id="foreign-concept"),
    ],
)
def test_creation_rejects_foreign_tenant_relationships(command):
    repository = FakeCreationRepository()
    service = DecisionService(repository)

    with pytest.raises(DecisionNotFoundError):
        service.create_decision(
            tenant_id="tenant-1",
            actor_id="user-1",
            clearance_rank=20,
            role_ids={"role-1"},
            permissions={"decision.create"},
            command=command,
        )

    assert repository.saved is None


def test_transition_requires_explicit_permission():
    service = DecisionService(FakeRepository())

    with pytest.raises(DecisionPermissionError):
        service.transition(
            tenant_id="tenant-1",
            decision_id="decision-1",
            actor_id="user-1",
            permissions={"decision.view"},
            status="in_review",
        )


def test_transition_changes_state_and_creates_audit_together():
    repository = FakeRepository()
    service = DecisionService(repository)

    response = service.transition(
        tenant_id="tenant-1",
        decision_id="decision-1",
        actor_id="user-1",
        permissions={"decision.transition"},
        status="in_review",
        rationale="Evidence review complete",
    )

    decision, event = repository.saved
    assert response.status == "in_review"
    assert decision.status == "in_review"
    assert event.event_type == "DecisionStatusChanged"
    assert event.details["rationale"] == "Evidence review complete"


def test_foreign_tenant_decision_is_non_disclosing_not_found():
    service = DecisionService(FakeRepository())

    with pytest.raises(DecisionNotFoundError, match="Decision not found"):
        service.transition(
            tenant_id="tenant-2",
            decision_id="decision-1",
            actor_id="user-2",
            permissions={"decision.transition"},
            status="in_review",
        )


def test_forbidden_transition_does_not_save_or_audit():
    repository = FakeRepository()
    service = DecisionService(repository)

    with pytest.raises(InvalidTransitionError):
        service.transition(
            tenant_id="tenant-1",
            decision_id="decision-1",
            actor_id="user-1",
            permissions={"decision.transition"},
            status="approved",
        )

    assert repository.saved is None
