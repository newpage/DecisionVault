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


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        user=SimpleNamespace(id="user-1"),
        membership=SimpleNamespace(clearance_rank=20),
        role_ids={"role-1"},
        permissions={"decision.create", "decision.transition"},
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
