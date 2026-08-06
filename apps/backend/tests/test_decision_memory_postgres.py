import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    AccessPolicy,
    AccessPolicyRole,
    BusinessConcept,
    DecisionCase,
    DecisionEvidence,
    Organization,
    Role,
    Tenant,
    User,
    Workspace,
)
from app.modules.decisions.memory_repository import DecisionMemoryRepository


pytestmark = pytest.mark.postgres
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def postgres_engine():
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL does not select PostgreSQL")
    if "test" not in TEST_DATABASE_URL.lower():
        pytest.fail("Refusing to reset a PostgreSQL URL without 'test' in it")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed_tenant(db, suffix):
    tenant = Tenant(slug=f"memory-{suffix}", name=f"Memory {suffix}")
    user = User(email=f"memory-{suffix}@example.com", full_name="Memory User", password_hash="unused")
    db.add_all([tenant, user])
    db.flush()
    organization = Organization(tenant_id=tenant.id, name="Organization", code=suffix)
    db.add(organization)
    db.flush()
    workspace = Workspace(tenant_id=tenant.id, organization_id=organization.id, name="Workspace")
    concept = BusinessConcept(tenant_id=tenant.id, name="Concept", slug=f"memory-concept-{suffix}")
    db.add_all([workspace, concept])
    db.flush()
    return tenant, user, workspace, concept


def decision(db, tenant, user, workspace, concept, title, status):
    item = DecisionCase(tenant_id=tenant.id, workspace_id=workspace.id, business_concept_id=concept.id, title=title, question=f"Should {title} proceed?", status=status, created_by=user.id)
    db.add(item)
    db.flush()
    return item


def evidence(db, tenant, decision_item, user, *, title, rank=20, policy_id=None):
    item = DecisionEvidence(tenant_id=tenant.id, decision_case_id=decision_item.id, knowledge_card_id=f"card-{title}", relationship_type="supporting", selection_rationale="Historical basis", snapshot_title=title, snapshot_content="Governed immutable snapshot", snapshot_knowledge_type="policy", snapshot_authority_level="sop", snapshot_lifecycle_status="published", snapshot_approval_status="approved", snapshot_classification_rank=rank, snapshot_access_policy_id=policy_id, snapshot_trust_score=0.9, snapshot_ai_usage_allowed=True, snapshot_card_created_at=decision_item.created_at, selected_by=user.id)
    db.add(item)
    db.flush()
    return item


def test_candidate_retrieval_filters_tenant_state_and_current_decision_before_ranking(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, user_a, workspace_a, concept_a = seed_tenant(db, "candidates-a")
        tenant_b, user_b, workspace_b, concept_b = seed_tenant(db, "candidates-b")
        current = decision(db, tenant_a, user_a, workspace_a, concept_a, "Current", "in_review")
        approved = decision(db, tenant_a, user_a, workspace_a, concept_a, "Approved history", "approved")
        rejected = decision(db, tenant_a, user_a, workspace_a, concept_a, "Rejected history", "rejected")
        decision(db, tenant_a, user_a, workspace_a, concept_a, "Draft history", "draft")
        decision(db, tenant_b, user_b, workspace_b, concept_b, "Foreign history", "approved")
        db.commit()
        candidates = DecisionMemoryRepository(db).list_candidates(tenant_id=tenant_a.id, current_decision_id=current.id, clearance_rank=20, role_ids=set())
        assert {item.id for item in candidates} == {approved.id, rejected.id}


def test_evidence_authorization_is_applied_inside_profile_query(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, workspace, concept = seed_tenant(db, "evidence")
        historical = decision(db, tenant, user, workspace, concept, "Historical", "approved")
        allowed_role = Role(tenant_id=tenant.id, code="allowed", name="Allowed")
        other_role = Role(tenant_id=tenant.id, code="other", name="Other")
        policy = AccessPolicy(tenant_id=tenant.id, name="Restricted evidence")
        db.add_all([allowed_role, other_role, policy])
        db.flush()
        db.add(AccessPolicyRole(policy_id=policy.id, role_id=allowed_role.id))
        evidence(db, tenant, historical, user, title="visible")
        evidence(db, tenant, historical, user, title="above-clearance", rank=60)
        evidence(db, tenant, historical, user, title="policy-restricted", policy_id=policy.id)
        db.commit()
        repository = DecisionMemoryRepository(db)
        denied = repository.authorized_evidence(tenant_id=tenant.id, decision_id=historical.id, clearance_rank=20, role_ids={other_role.id})
        allowed = repository.authorized_evidence(tenant_id=tenant.id, decision_id=historical.id, clearance_rank=20, role_ids={allowed_role.id})
        assert {item.snapshot_title for item in denied} == {"visible"}
        assert {item.snapshot_title for item in allowed} == {"visible", "policy-restricted"}


def test_pairwise_historical_lookup_is_tenant_scoped_and_non_disclosing(postgres_engine):
    with Session(postgres_engine) as db:
        tenant_a, user_a, workspace_a, concept_a = seed_tenant(db, "pair-a")
        tenant_b, user_b, workspace_b, concept_b = seed_tenant(db, "pair-b")
        current = decision(db, tenant_a, user_a, workspace_a, concept_a, "Current pair", "in_review")
        foreign = decision(db, tenant_b, user_b, workspace_b, concept_b, "Foreign pair", "approved")
        db.commit()
        assert DecisionMemoryRepository(db).get_historical_decision(tenant_id=tenant_a.id, current_decision_id=current.id, historical_decision_id=foreign.id, clearance_rank=20, role_ids=set()) is None


def test_restricted_decision_never_enters_candidate_retrieval(postgres_engine):
    with Session(postgres_engine) as db:
        tenant, user, workspace, concept = seed_tenant(db, "restricted")
        current = decision(db, tenant, user, workspace, concept, "Current restricted test", "in_review")
        visible = decision(db, tenant, user, workspace, concept, "Visible precedent", "approved")
        restricted = decision(db, tenant, user, workspace, concept, "Restricted precedent", "approved")
        role = Role(tenant_id=tenant.id, code="restricted-role", name="Restricted")
        policy = AccessPolicy(tenant_id=tenant.id, name="Restricted Decisions")
        db.add_all([role, policy])
        db.flush()
        db.add(AccessPolicyRole(policy_id=policy.id, role_id=role.id))
        restricted.access_policy_id = policy.id
        restricted.classification_rank = 40
        db.commit()
        repository = DecisionMemoryRepository(db)
        denied = repository.list_candidates(tenant_id=tenant.id, current_decision_id=current.id, clearance_rank=20, role_ids=set())
        allowed = repository.list_candidates(tenant_id=tenant.id, current_decision_id=current.id, clearance_rank=50, role_ids={role.id})
        assert {item.id for item in denied} == {visible.id}
        assert {item.id for item in allowed} == {visible.id, restricted.id}
