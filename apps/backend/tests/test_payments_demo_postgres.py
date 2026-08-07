import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.database import Base
from app.demo_seed import CURRENT_ID, RESTRICTED_ID, seed_payments_demo
from app.dashboard.service import build_dashboard
from app.models import (
    DecisionCase,
    DecisionLessonEvaluation,
    DecisionPrecedentEvaluation,
    KnowledgeCard,
    Membership,
    MembershipRole,
    Role,
    User,
)
from app.modules.decisions.memory_repository import DecisionMemoryRepository
from app.modules.decisions.repository import DecisionRepository


pytestmark = pytest.mark.postgres
URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def seeded_engine():
    if not URL.startswith("postgresql"):
        pytest.skip("PostgreSQL required")
    if "test" not in URL.lower():
        pytest.fail("Refusing to reset a PostgreSQL URL without 'test' in it")
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
    with Session(engine) as db:
        seed_payments_demo(db)
    yield engine
    engine.dispose()


def roles_for(db, email):
    user = db.scalar(select(User).where(User.email == email))
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    roles = set(
        db.scalars(
            select(Role.id)
            .join(MembershipRole, MembershipRole.role_id == Role.id)
            .where(MembershipRole.membership_id == membership.id)
        ).all()
    )
    return membership, roles


def test_payments_portfolio_is_complete_and_truthfully_labeled(seeded_engine):
    with Session(seeded_engine) as db:
        current = db.get(DecisionCase, CURRENT_ID)
        cards = list(
            db.scalars(
                select(KnowledgeCard).where(
                    KnowledgeCard.tenant_id == current.tenant_id,
                    KnowledgeCard.knowledge_type.like("payments_%"),
                )
            ).all()
        )
        assert len(cards) == 7
        assert all(card.approval_status == "approved" for card in cards)
        assert all("deterministic synthetic" in card.body for card in cards)
        analysis = current.evidence_summary["demo_analysis"]
        assert analysis["recommendation"].startswith("Conditionally approve")
        assert len(analysis["citations"]) == 6
        assert "accountable human" in analysis["accountability"]
        assert {
            item.classification
            for item in db.scalars(select(DecisionPrecedentEvaluation)).all()
        } >= {"useful", "highly_useful", "misleading", "harmful"}
        assert {
            item.classification
            for item in db.scalars(select(DecisionLessonEvaluation)).all()
        } >= {"beneficial", "neutral", "ineffective", "appropriate_rejection"}


def test_restricted_history_is_filtered_before_lists_and_memory(seeded_engine):
    with Session(seeded_engine) as db:
        current = db.get(DecisionCase, CURRENT_ID)
        analyst_member, analyst_roles = roles_for(
            db, "analyst@globalpayments.demo"
        )
        presenter_email = db.scalar(
            select(User.email).where(User.full_name == "Payments Risk Demo Presenter")
        )
        presenter_member, presenter_roles = roles_for(db, presenter_email)
        repository = DecisionRepository(db)
        analyst_ids = {
            item.id
            for item in repository.list_decisions(
                tenant_id=current.tenant_id,
                clearance_rank=analyst_member.clearance_rank,
                role_ids=analyst_roles,
            )
        }
        presenter_ids = {
            item.id
            for item in repository.list_decisions(
                tenant_id=current.tenant_id,
                clearance_rank=presenter_member.clearance_rank,
                role_ids=presenter_roles,
            )
        }
        assert RESTRICTED_ID not in analyst_ids
        assert RESTRICTED_ID in presenter_ids
        memory = DecisionMemoryRepository(db)
        analyst_candidates = memory.list_candidates(
            tenant_id=current.tenant_id,
            current_decision_id=current.id,
            clearance_rank=analyst_member.clearance_rank,
            role_ids=analyst_roles,
        )
        presenter_candidates = memory.list_candidates(
            tenant_id=current.tenant_id,
            current_decision_id=current.id,
            clearance_rank=presenter_member.clearance_rank,
            role_ids=presenter_roles,
        )
        assert RESTRICTED_ID not in {item.id for item in analyst_candidates}
        assert RESTRICTED_ID in {item.id for item in presenter_candidates}
        analyst_dashboard = build_dashboard(
            db,
            current.tenant_id,
            clearance_rank=analyst_member.clearance_rank,
            role_ids=analyst_roles,
        )
        presenter_dashboard = build_dashboard(
            db,
            current.tenant_id,
            clearance_rank=presenter_member.clearance_rank,
            role_ids=presenter_roles,
        )
        analyst_total = sum(
            item["value"] for item in analyst_dashboard["charts"]["decision_status"]
        )
        presenter_total = sum(
            item["value"]
            for item in presenter_dashboard["charts"]["decision_status"]
        )
        assert presenter_total == analyst_total + 1
