from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    AccessPolicy,
    AccessPolicyRole,
    BusinessConcept,
    DecisionCase,
    KnowledgeCard,
    Organization,
    Role,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.repository import DecisionRepository


def integration_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_tenant(db, suffix):
    tenant = Tenant(slug=f"tenant-{suffix}", name=f"Tenant {suffix}")
    user = User(
        email=f"user-{suffix}@example.com",
        full_name=f"User {suffix}",
        password_hash="not-used",
    )
    db.add_all([tenant, user])
    db.flush()
    organization = Organization(
        tenant_id=tenant.id, name=f"Organization {suffix}", code=suffix
    )
    db.add(organization)
    db.flush()
    workspace = Workspace(
        tenant_id=tenant.id,
        organization_id=organization.id,
        name=f"Workspace {suffix}",
    )
    concept = BusinessConcept(
        tenant_id=tenant.id,
        name=f"Concept {suffix}",
        slug=f"concept-{suffix}",
    )
    db.add_all([workspace, concept])
    db.flush()
    return tenant, user, workspace, concept


def test_tenant_scoped_lookups_reject_foreign_objects():
    with integration_session() as db:
        tenant_a, user_a, workspace_a, concept_a = seed_tenant(db, "a")
        tenant_b, _, workspace_b, concept_b = seed_tenant(db, "b")
        decision = DecisionCase(
            tenant_id=tenant_a.id,
            workspace_id=workspace_a.id,
            business_concept_id=concept_a.id,
            title="Decision",
            question="Should this decision proceed?",
            created_by=user_a.id,
        )
        db.add(decision)
        db.commit()
        repository = DecisionRepository(db)

        assert repository.get_workspace(
            tenant_id=tenant_a.id, workspace_id=workspace_b.id
        ) is None
        assert repository.get_concept(
            tenant_id=tenant_a.id, concept_id=concept_b.id
        ) is None
        assert repository.get_decision(
            tenant_id=tenant_b.id, decision_id=decision.id
        ) is None


def test_evidence_enforces_tenant_workspace_clearance_and_access_policy():
    with integration_session() as db:
        tenant_a, user_a, workspace_a, concept_a = seed_tenant(db, "a")
        tenant_b, user_b, workspace_b, concept_b = seed_tenant(db, "b")
        allowed_role = Role(
            tenant_id=tenant_a.id, code="allowed", name="Allowed"
        )
        denied_role = Role(
            tenant_id=tenant_a.id, code="denied", name="Denied"
        )
        policy = AccessPolicy(tenant_id=tenant_a.id, name="Restricted")
        db.add_all([allowed_role, denied_role, policy])
        db.flush()
        db.add(
            AccessPolicyRole(policy_id=policy.id, role_id=allowed_role.id)
        )

        def add_card(title, *, tenant, workspace, concept, rank=20, policy_id=None):
            db.add(
                KnowledgeCard(
                    tenant_id=tenant.id,
                    workspace_id=workspace.id,
                    business_concept_id=concept.id,
                    title=title,
                    summary=title,
                    body=title,
                    classification_rank=rank,
                    access_policy_id=policy_id,
                    owner_id=user_a.id if tenant is tenant_a else user_b.id,
                )
            )

        add_card(
            "Allowed restricted",
            tenant=tenant_a,
            workspace=workspace_a,
            concept=concept_a,
            policy_id=policy.id,
        )
        add_card(
            "Above clearance",
            tenant=tenant_a,
            workspace=workspace_a,
            concept=concept_a,
            rank=50,
        )
        add_card(
            "Foreign tenant",
            tenant=tenant_b,
            workspace=workspace_b,
            concept=concept_b,
        )
        db.commit()
        repository = DecisionRepository(db)

        denied = repository.list_authorized_evidence(
            tenant_id=tenant_a.id,
            concept_id=concept_a.id,
            workspace_id=workspace_a.id,
            clearance_rank=20,
            role_ids={denied_role.id},
        )
        allowed = repository.list_authorized_evidence(
            tenant_id=tenant_a.id,
            concept_id=concept_a.id,
            workspace_id=workspace_a.id,
            clearance_rank=20,
            role_ids={allowed_role.id},
        )

        assert denied == []
        assert [card.title for card in allowed] == ["Allowed restricted"]


class FailingSession:
    def __init__(self):
        self.rolled_back = False

    def add(self, item):
        pass

    def flush(self):
        raise RuntimeError("audit transaction failed")

    def rollback(self):
        self.rolled_back = True


def test_state_and_audit_transaction_rolls_back_on_failure():
    session = FailingSession()
    repository = DecisionRepository(session)

    try:
        repository.save_with_audit(
            decision=object(), event=object()
        )
    except RuntimeError:
        pass

    assert session.rolled_back is True
