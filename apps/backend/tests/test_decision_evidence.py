from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.decisions.evidence import EvidenceValidationError
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.service import (
    DecisionConflictError,
    DecisionNotFoundError,
    DecisionService,
)


def decision():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id="decision-1",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        business_concept_id="concept-1",
        title="Qualify Acme",
        question="Should Acme be approved?",
        status="evidence_collection",
        recommendation="",
        confidence=0,
        supplier_name="Acme",
        supplier_category="Manufacturer",
        supplier_location="",
        owner_name="Owner",
        due_date=None,
        priority="high",
        risk_level="medium",
        decision_type="initial_qualification",
        business_unit="Supply Chain",
        readiness_score=0,
        readiness_status="insufficient_evidence",
        evidence_summary={},
        created_by="user-1",
        created_at=now,
        updated_at=now,
    )


class EvidenceRepository:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.decision = decision()
        self.card = SimpleNamespace(
            id="card-1",
            title="Approved policy",
            body="Immutable policy content",
            summary="Policy summary",
            knowledge_type="policy",
            authority_level="sop",
            lifecycle_status="published",
            approval_status="approved",
            classification_rank=20,
            access_policy_id=None,
            trust_score=0.9,
            ai_usage_allowed=True,
            created_at=now,
        )
        self.chunk = SimpleNamespace(
            id="chunk-1",
            knowledge_card_id="card-1",
            content="Immutable selected excerpt",
            chunk_index=0,
        )
        self.active = []
        self.events = []
        self.allow_card = True
        self.saved = False

    def get_decision_for_update(self, *, tenant_id, decision_id):
        if tenant_id == "tenant-1" and decision_id == self.decision.id:
            return self.decision
        return None

    def get_decision(self, *, tenant_id, decision_id):
        return self.get_decision_for_update(
            tenant_id=tenant_id, decision_id=decision_id
        )

    def get_authorized_card(self, **kwargs):
        return self.card if self.allow_card else None

    def get_chunk(self, *, tenant_id, card_id, chunk_id):
        if (
            tenant_id == "tenant-1"
            and card_id == self.card.id
            and chunk_id == self.chunk.id
        ):
            return self.chunk
        return None

    def has_active_selection(self, **kwargs):
        return any(
            item.knowledge_card_id == kwargs["card_id"]
            and item.removed_at is None
            for item in self.active
        )

    def get_source_snapshot(self, **kwargs):
        return None

    def list_active_evidence(self, **kwargs):
        return [item for item in self.active if item.removed_at is None]

    def get_evidence(self, *, tenant_id, decision_id, evidence_id):
        return next(
            (item for item in self.active if item.id == evidence_id), None
        )

    def save_evidence_change(self, *, decision, evidence, events):
        if evidence.selected_at is None:
            evidence.selected_at = datetime.now(timezone.utc)
        if evidence.removed_at is None and evidence not in self.active:
            self.active.append(evidence)
        self.events.extend(events)
        self.saved = True
        return decision, evidence


def select(service, **overrides):
    values = {
        "tenant_id": "tenant-1",
        "decision_id": "decision-1",
        "actor_id": "user-1",
        "clearance_rank": 20,
        "role_ids": {"role-1"},
        "permissions": {"decision.edit", "decision.evidence.select"},
        "card_id": "card-1",
        "chunk_id": "chunk-1",
        "relationship_type": "supporting",
        "rationale": "Controls directly support qualification",
    }
    values.update(overrides)
    return service.select_evidence(**values)


def test_selection_creates_snapshot_recalculates_and_audits():
    repository = EvidenceRepository()
    result = select(DecisionService(repository))

    assert result.evidence.snapshot_content == "Immutable selected excerpt"
    assert result.evidence.snapshot_approval_status == "approved"
    assert result.decision.readiness_score == 85
    assert [event.event_type for event in repository.events] == [
        "DecisionEvidenceSelected",
        "DecisionRecalculated",
    ]


def test_snapshot_does_not_change_when_live_card_changes():
    repository = EvidenceRepository()
    result = select(DecisionService(repository))

    repository.card.title = "Changed title"
    repository.chunk.content = "Changed content"

    assert result.evidence.snapshot_title == "Approved policy"
    assert result.evidence.snapshot_content == "Immutable selected excerpt"


def test_duplicate_active_selection_is_rejected():
    repository = EvidenceRepository()
    service = DecisionService(repository)
    select(service)

    with pytest.raises(DecisionConflictError):
        select(service)


@pytest.mark.parametrize("relationship", ["supporting", "opposing", "contextual"])
def test_controlled_relationship_types_are_accepted(relationship):
    select(DecisionService(EvidenceRepository()), relationship_type=relationship)


def test_invalid_relationship_and_missing_rationale_are_rejected():
    service = DecisionService(EvidenceRepository())

    with pytest.raises(EvidenceValidationError):
        select(service, relationship_type="uncontrolled")
    with pytest.raises(EvidenceValidationError):
        select(service, rationale=" ")


def test_removal_retains_snapshot_recalculates_and_audits():
    repository = EvidenceRepository()
    service = DecisionService(repository)
    selected = select(service)

    result = service.remove_evidence(
        tenant_id="tenant-1",
        decision_id="decision-1",
        evidence_id=selected.evidence.id,
        actor_id="user-1",
        permissions={"decision.edit", "decision.evidence.remove"},
        rationale="Superseded by a current assessment",
    )

    assert result.evidence.removed_at is not None
    assert result.evidence.snapshot_content == "Immutable selected excerpt"
    assert result.decision.readiness_score == 0
    assert repository.events[-2].event_type == "DecisionEvidenceRemoved"


def test_evidence_operations_require_explicit_permissions():
    service = DecisionService(EvidenceRepository())

    with pytest.raises(DecisionPermissionError):
        select(service, permissions={"decision.edit"})


def test_foreign_decision_card_and_chunk_are_non_disclosing_not_found():
    repository = EvidenceRepository()
    service = DecisionService(repository)

    with pytest.raises(DecisionNotFoundError, match="Decision not found"):
        select(service, tenant_id="tenant-2")
    repository.allow_card = False
    with pytest.raises(DecisionNotFoundError, match="Knowledge Card not found"):
        select(service)
    repository.allow_card = True
    with pytest.raises(DecisionNotFoundError, match="Knowledge Chunk not found"):
        select(service, chunk_id="foreign-chunk")
