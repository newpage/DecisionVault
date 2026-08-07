import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    AccessPolicy,
    AccessPolicyRole,
    AuditEvent,
    KnowledgeCard,
    Organization,
    Role,
    Tenant,
    User,
    Workspace,
)
from app.modules.knowledge.repository import KnowledgeRepository


pytestmark = pytest.mark.postgres
URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def engine():
    if not URL.startswith("postgresql"):
        pytest.skip("PostgreSQL required")
    if "test" not in URL.lower():
        pytest.fail("Refusing to reset a PostgreSQL URL without 'test' in it")
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    yield engine
    engine.dispose()


def seed(db: Session):
    first = Tenant(slug="gov-first", name="First")
    second = Tenant(slug="gov-second", name="Second")
    reviewer = User(email="reviewer@gov.test", full_name="Reviewer", password_hash="x")
    db.add_all([first, second, reviewer])
    db.flush()
    first_org = Organization(tenant_id=first.id, name="First org", code="FIRST")
    second_org = Organization(tenant_id=second.id, name="Second org", code="SECOND")
    db.add_all([first_org, second_org])
    db.flush()
    first_workspace = Workspace(
        tenant_id=first.id, organization_id=first_org.id, name="First workspace"
    )
    second_workspace = Workspace(
        tenant_id=second.id, organization_id=second_org.id, name="Second workspace"
    )
    role = Role(tenant_id=first.id, code="restricted-reviewer", name="Restricted reviewer")
    policy = AccessPolicy(tenant_id=first.id, name="Restricted policy")
    db.add_all([first_workspace, second_workspace, role, policy])
    db.flush()
    db.add(AccessPolicyRole(policy_id=policy.id, role_id=role.id))
    visible = KnowledgeCard(
        tenant_id=first.id,
        workspace_id=first_workspace.id,
        title="Visible critical alert",
        summary="Visible",
        body="{}",
        lifecycle_status="in_review",
        approval_status="pending_review",
        classification_rank=40,
        owner_id=reviewer.id,
    )
    restricted = KnowledgeCard(
        tenant_id=first.id,
        workspace_id=first_workspace.id,
        title="Restricted critical alert",
        summary="Restricted",
        body="{}",
        lifecycle_status="in_review",
        approval_status="pending_review",
        classification_rank=80,
        access_policy_id=policy.id,
        owner_id=reviewer.id,
    )
    foreign = KnowledgeCard(
        tenant_id=second.id,
        workspace_id=second_workspace.id,
        title="Foreign alert",
        summary="Foreign",
        body="{}",
        lifecycle_status="in_review",
        approval_status="pending_review",
        classification_rank=20,
        owner_id=reviewer.id,
    )
    db.add_all([visible, restricted, foreign])
    db.commit()
    return first, second, reviewer, role, visible, restricted, foreign


def test_review_queue_enforces_tenant_clearance_and_access_policy(engine):
    with Session(engine) as db:
        first, second, _, role, visible, restricted, foreign = seed(db)
        repository = KnowledgeRepository(db)
        basic = repository.list_review_cards(
            tenant_id=first.id, clearance_rank=60, role_ids=set()
        )
        assert [card.id for card in basic] == [visible.id]
        authorized = repository.list_review_cards(
            tenant_id=first.id, clearance_rank=100, role_ids={role.id}
        )
        assert {card.id for card in authorized} == {visible.id, restricted.id}
        assert repository.get_card(
            card_id=foreign.id,
            tenant_id=first.id,
            clearance_rank=100,
            role_ids={role.id},
        ) is None
        assert repository.get_card(
            card_id=visible.id,
            tenant_id=second.id,
            clearance_rank=100,
            role_ids={role.id},
        ) is None


def test_review_state_and_audit_write_roll_back_atomically(engine):
    with Session(engine) as db:
        visible = db.query(KnowledgeCard).filter_by(title="Visible critical alert").one()
        visible.lifecycle_status = "published"
        visible.approval_status = "approved"
        event = AuditEvent(
            tenant_id=visible.tenant_id,
            actor_id="missing-user",
            event_type="KnowledgePublished",
            entity_type="knowledge_card",
            entity_id=visible.id,
            description="Must roll back",
            details={"rationale": "Atomic review"},
        )
        with pytest.raises(IntegrityError):
            KnowledgeRepository(db).commit_card(visible, event)
        db.expire_all()
        persisted = db.get(KnowledgeCard, visible.id)
        assert persisted.lifecycle_status == "in_review"
        assert persisted.approval_status == "pending_review"
