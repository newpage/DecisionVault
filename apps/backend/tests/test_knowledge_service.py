from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.knowledge.service import (
    KnowledgeNotFoundError,
    KnowledgePermissionError,
    KnowledgeService,
    KnowledgeValidationError,
)


@dataclass
class FakeCard:
    id: str = "card-1"
    tenant_id: str = "tenant-1"
    approval_status: str = "not_submitted"
    lifecycle_status: str = "draft"
    approved_by: str | None = None
    approved_at: object | None = None
    trust_score: float = 0.5
    title: str = "Critical network alert"
    summary: str = "Coordinated card testing"
    body: str = '{"risk_level":"critical","facts":["11.6x baseline"]}'
    knowledge_type: str = "network_risk_alert"
    classification_rank: int = 50
    ai_usage_allowed: bool = True
    authority_level: str = "network_alert"
    access_policy_id: str | None = None
    created_at: datetime = datetime(2026, 8, 1, tzinfo=timezone.utc)


class FakeRepository:
    def __init__(self) -> None:
        self.card = FakeCard()
        self.workspace = SimpleNamespace(id="workspace-1")
        self.saved_card = None
        self.saved_event = None

    def list_cards(self, **kwargs):
        return [self.card]

    def get_workspace(self, **kwargs):
        return self.workspace

    def get_card(self, **kwargs):
        return self.card if kwargs["card_id"] == self.card.id else None

    def create_source(self, **kwargs):
        source = kwargs["source"]
        source.id = "source-1"
        job = kwargs["job"]
        job.id = "job-1"
        return source, job

    def list_jobs(self, **kwargs):
        return []

    def commit_card(self, card, event):
        self.saved_card = card
        self.saved_event = event
        return card

    def list_review_cards(self, **kwargs):
        return [self.card]

    def review_context(self, **kwargs):
        return {"evidence": [], "access_policy": None}


def test_submit_card_changes_governance_state():
    repository = FakeRepository()
    service = KnowledgeService(repository)

    card = service.submit_card(
        card_id="card-1",
        tenant_id="tenant-1",
        actor_id="user-1",
        clearance_rank=50,
        role_ids=set(),
        can_submit=True,
    )

    assert card.approval_status == "pending_review"
    assert card.lifecycle_status == "in_review"
    assert repository.saved_card is card


def test_approve_requires_permission():
    service = KnowledgeService(FakeRepository())

    with pytest.raises(KnowledgePermissionError):
        service.approve_card(
            card_id="card-1",
            tenant_id="tenant-1",
            approver_id="user-1",
            can_approve=False,
            clearance_rank=50,
            role_ids=set(),
        )


def test_missing_card_raises_not_found():
    service = KnowledgeService(FakeRepository())

    with pytest.raises(KnowledgeNotFoundError):
        service.submit_card(
            card_id="missing",
            tenant_id="tenant-1",
            actor_id="user-1",
            clearance_rank=50,
            role_ids=set(),
            can_submit=True,
        )


def test_empty_upload_is_rejected():
    service = KnowledgeService(FakeRepository())

    with pytest.raises(KnowledgeValidationError):
        service.queue_source_upload(
            tenant_id="tenant-1",
            workspace_id="workspace-1",
            user_id="user-1",
            filename="empty.txt",
            mime_type="text/plain",
            raw=b"",
        )


CHECKLIST = {
    "provenance_verified": True,
    "classification_confirmed": True,
    "policy_authority_confirmed": True,
    "conflicts_reviewed": True,
    "ai_eligibility_appropriate": True,
}


@pytest.mark.parametrize(
    ("action", "lifecycle", "approval", "event_type"),
    [
        ("approve_publish", "published", "approved", "KnowledgePublished"),
        ("return_correction", "draft", "not_submitted", "KnowledgeReturnedForCorrection"),
        ("reject", "retired", "rejected", "KnowledgeRejected"),
    ],
)
def test_human_review_actions_are_governed_and_audited(
    action, lifecycle, approval, event_type
):
    repository = FakeRepository()
    repository.card.lifecycle_status = "in_review"
    repository.card.approval_status = "pending_review"
    service = KnowledgeService(repository)

    card = service.review_card(
        card_id="card-1",
        tenant_id="tenant-1",
        reviewer_id="reviewer-1",
        can_approve=True,
        clearance_rank=80,
        role_ids=set(),
        action=action,
        rationale="Reviewed against policy and provenance.",
        checklist=CHECKLIST,
    )

    assert (card.lifecycle_status, card.approval_status) == (lifecycle, approval)
    assert repository.saved_event.event_type == event_type
    assert repository.saved_event.details["rationale"].startswith("Reviewed")
    assert repository.saved_event.details["checklist"] == CHECKLIST


def test_review_requires_rationale_complete_checklist_and_valid_transition():
    repository = FakeRepository()
    repository.card.lifecycle_status = "in_review"
    repository.card.approval_status = "pending_review"
    service = KnowledgeService(repository)
    base = dict(
        card_id="card-1",
        tenant_id="tenant-1",
        reviewer_id="reviewer-1",
        can_approve=True,
        clearance_rank=80,
        role_ids=set(),
        action="approve_publish",
        rationale="Reviewed against policy.",
        checklist=CHECKLIST,
    )
    with pytest.raises(KnowledgeValidationError):
        service.review_card(**(base | {"rationale": "short"}))
    with pytest.raises(KnowledgeValidationError):
        service.review_card(
            **(base | {"checklist": CHECKLIST | {"conflicts_reviewed": False}})
        )
    repository.card.lifecycle_status = "published"
    repository.card.approval_status = "approved"
    with pytest.raises(KnowledgeValidationError):
        service.review_card(**base)


def test_queue_prioritizes_critical_and_reports_executive_summary():
    repository = FakeRepository()
    repository.card.lifecycle_status = "in_review"
    repository.card.approval_status = "pending_review"
    result = KnowledgeService(repository).governance_queue(
        tenant_id="tenant-1",
        clearance_rank=80,
        role_ids=set(),
        can_review=True,
    )
    assert result["review_queue"][0]["risk_level"] == "critical"
    assert result["summary"]["pending_reviews"] == 1
    assert result["summary"]["critical_items"] == 1
    assert result["summary"]["ai_eligible_items"] == 1
