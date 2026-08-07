from dataclasses import dataclass
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


class FakeRepository:
    def __init__(self) -> None:
        self.card = FakeCard()
        self.workspace = SimpleNamespace(id="workspace-1")
        self.saved_card = None

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
        return card


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
