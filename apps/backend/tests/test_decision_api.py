from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.router import get_service, router
from app.modules.decisions.schemas import DecisionResponse
from app.modules.decisions.service import DecisionNotFoundError


def response(status="in_review"):
    now = datetime.now(timezone.utc)
    return DecisionResponse.model_validate(
        {
            "id": "decision-1",
            "workspace_id": "workspace-1",
            "business_concept_id": "concept-1",
            "title": "Qualify Acme",
            "question": "Should Acme be approved?",
            "status": status,
            "recommendation": "Review evidence.",
            "confidence": 0.8,
            "supplier_name": "Acme",
            "supplier_category": "Manufacturer",
            "supplier_location": "",
            "owner_name": "Owner",
            "due_date": None,
            "priority": "high",
            "risk_level": "medium",
            "decision_type": "initial_qualification",
            "business_unit": "Supply Chain",
            "readiness_score": 80,
            "readiness_status": "ready",
            "evidence_summary": {},
            "created_by": "user-1",
            "created_at": now,
            "updated_at": now,
        }
    )


class FakeService:
    failure = None

    def transition(self, **kwargs):
        if self.failure:
            raise self.failure
        return response(kwargs["status"])

    def create_decision(self, **kwargs):
        if self.failure:
            raise self.failure
        return response("evidence_collection")

    def list_available_evidence(self, **kwargs):
        if self.failure:
            raise self.failure
        return [
            {
                "id": "card-1",
                "title": "Approved policy",
                "summary": "Summary",
                "knowledge_type": "policy",
                "authority_level": "sop",
                "trust_score": 0.9,
                "ai_usage_allowed": True,
                "chunks": [],
                "selected": False,
            }
        ]

    def list_active_evidence(self, **kwargs):
        if self.failure:
            raise self.failure
        return [evidence_response()]

    def list_evidence_history(self, **kwargs):
        return self.list_active_evidence(**kwargs)

    def select_evidence(self, **kwargs):
        if self.failure:
            raise self.failure
        return {"decision": response(), "evidence": evidence_response()}

    def remove_evidence(self, **kwargs):
        if self.failure:
            raise self.failure
        evidence = evidence_response()
        evidence["removed_at"] = datetime.now(timezone.utc)
        evidence["removal_rationale"] = kwargs["rationale"]
        evidence["removed_by"] = "user-1"
        return {"decision": response(), "evidence": evidence}


def evidence_response():
    now = datetime.now(timezone.utc)
    return {
        "id": "evidence-1",
        "knowledge_card_id": "card-1",
        "knowledge_chunk_id": None,
        "source_document_id": None,
        "relationship_type": "supporting",
        "selection_rationale": "Directly supports qualification",
        "snapshot_title": "Approved policy",
        "snapshot_content": "Immutable content",
        "snapshot_source_filename": "",
        "snapshot_source_mime_type": "",
        "snapshot_source_locator": "",
        "snapshot_knowledge_type": "policy",
        "snapshot_authority_level": "sop",
        "snapshot_lifecycle_status": "published",
        "snapshot_approval_status": "approved",
        "snapshot_classification_rank": 20,
        "snapshot_access_policy_id": None,
        "snapshot_trust_score": 0.9,
        "snapshot_ai_usage_allowed": True,
        "snapshot_card_created_at": now,
        "snapshot_content_revision": None,
        "snapshot_source_metadata": {},
        "selected_by": "user-1",
        "selected_at": now,
        "removed_by": None,
        "removed_at": None,
        "removal_rationale": None,
        "superseded_by_id": None,
    }


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        user=SimpleNamespace(id="user-1"),
        membership=SimpleNamespace(clearance_rank=20),
        role_ids={"role-1"},
        permissions={
            "decision.create",
            "decision.view",
            "decision.edit",
            "decision.transition",
            "decision.evidence.view",
            "decision.evidence.select",
            "decision.evidence.remove",
            "decision.evidence.history",
        },
    )
    return TestClient(app)


def creation_body():
    return {
        "workspace_id": "workspace-1",
        "business_concept_id": "concept-1",
        "title": "Qualify Acme",
        "question": "Should Acme be approved?",
        "supplier_name": "Acme",
        "owner_name": "Owner",
    }


def test_authenticated_creation_has_explicit_response_schema():
    result = client(FakeService()).post("/decisions", json=creation_body())

    assert result.status_code == 201
    assert result.json()["status"] == "evidence_collection"
    assert result.json()["workspace_id"] == "workspace-1"


def test_unauthorized_mutation_is_forbidden():
    service = FakeService()
    service.failure = DecisionPermissionError("decision.transition")

    result = client(service).patch(
        "/decisions/decision-1/status", json={"status": "in_review"}
    )

    assert result.status_code == 403


def test_valid_transition_returns_updated_decision():
    result = client(FakeService()).patch(
        "/decisions/decision-1/status", json={"status": "in_review"}
    )

    assert result.status_code == 200
    assert result.json()["status"] == "in_review"


def test_foreign_object_reference_is_non_disclosing_not_found():
    service = FakeService()
    service.failure = DecisionNotFoundError("Workspace not found")

    result = client(service).post("/decisions", json=creation_body())

    assert result.status_code == 404
    assert result.json() == {"detail": "Workspace not found"}


def test_invalid_status_is_rejected_at_api_boundary():
    result = client(FakeService()).patch(
        "/decisions/decision-1/status", json={"status": "invented"}
    )

    assert result.status_code == 422


def test_available_active_history_selection_and_removal_contracts():
    test_client = client(FakeService())

    available = test_client.get(
        "/decisions/decision-1/available-evidence"
    )
    selected = test_client.post(
        "/decisions/decision-1/evidence",
        json={
            "knowledge_card_id": "card-1",
            "relationship_type": "supporting",
            "rationale": "Directly supports qualification",
        },
    )
    active = test_client.get("/decisions/decision-1/evidence")
    history = test_client.get("/decisions/decision-1/evidence/history")
    removed = test_client.request(
        "DELETE",
        "/decisions/decision-1/evidence/evidence-1",
        json={"rationale": "Superseded evidence"},
    )

    assert available.status_code == 200
    assert selected.status_code == 201
    assert selected.json()["evidence"]["snapshot_content"] == "Immutable content"
    assert active.status_code == 200
    assert history.status_code == 200
    assert removed.status_code == 200
    assert removed.json()["evidence"]["removed_at"] is not None


def test_invalid_evidence_relationship_and_rationales_are_rejected():
    test_client = client(FakeService())

    invalid_relationship = test_client.post(
        "/decisions/decision-1/evidence",
        json={
            "knowledge_card_id": "card-1",
            "relationship_type": "uncontrolled",
            "rationale": "Relevant evidence",
        },
    )
    missing_selection_rationale = test_client.post(
        "/decisions/decision-1/evidence",
        json={
            "knowledge_card_id": "card-1",
            "relationship_type": "supporting",
            "rationale": "",
        },
    )
    missing_removal_rationale = test_client.request(
        "DELETE",
        "/decisions/decision-1/evidence/evidence-1",
        json={"rationale": ""},
    )

    assert invalid_relationship.status_code == 422
    assert missing_selection_rationale.status_code == 422
    assert missing_removal_rationale.status_code == 422
