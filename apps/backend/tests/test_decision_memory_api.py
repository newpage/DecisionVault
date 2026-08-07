from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.router import get_memory_service, router
from app.modules.decisions.service import DecisionNotFoundError


def result_item():
    return {
        "historical_decision": {
            "id": "historical-1", "title": "Prior supplier decision", "created_at": datetime.now(timezone.utc),
            "business_concept_id": "concept-1", "business_concept_name": "Supplier Qualification",
            "final_status": "approved", "approval_result": "approved", "effectiveness_classification": "did_not_meet",
            "evidence_count": 2, "evidence_types": ["policy"], "material_conditions": [], "material_findings": ["Dependency risk"],
            "lessons": ["Dependency was underestimated"],
        },
        "overall_similarity": 84.5, "relevance": "strongly_relevant", "algorithm_version": "decision_similarity_v1",
        "similarity_components": {"business_concept": {"score": 1, "weight": 0.2, "weighted_points": 20, "available": True, "explanation": "Same Business Concept"}},
        "shared_characteristics": ["Business Concept"], "different_characteristics": ["Effectiveness classification differs"],
        "observed_usage": {"decision": {"historical_decision_id": "historical-1", "referenced_count": 3, "evaluated_count": 2, "classification_counts": {"useful": 1, "misleading": 1}, "current_outcome_distribution": {"met": 2}}, "lessons": {}},
    }


class FakeMemoryService:
    failure = None
    call = None

    def list_precedents(self, **kwargs):
        self.call = kwargs
        if self.failure:
            raise self.failure
        return {"current_decision_id": kwargs["decision_id"], "algorithm_version": "decision_similarity_v1", "items": [result_item()], "considered_count": 3, "returned_count": 1}

    def compare(self, **kwargs):
        if self.failure:
            raise self.failure
        return {"current_decision": {"id": kwargs["decision_id"], "title": "Current", "status": "in_review", "business_concept_id": "concept-1"}, **result_item(), "historical_governance": {"approval_actions": ["approved"]}, "historical_outcome": {"effectiveness_classification": "did_not_meet"}, "historical_lessons": [{"id": "lesson-1", "type": "risk", "description": "Dependency was underestimated", "business_impact": "Delay"}]}


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_memory_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(tenant_id="tenant-1", membership=SimpleNamespace(id="member-1", clearance_rank=30), role_ids={"role-1"}, permissions={"decision.view", "decision.memory.view"})
    return TestClient(app)


def test_precedent_listing_filters_and_explicit_dto():
    service = FakeMemoryService()
    response = client(service).get("/decisions/current/precedents?minimum_relevance=relevant&limit=5&outcome_classification=did_not_meet")
    assert response.status_code == 200
    assert response.json()["items"][0]["historical_decision"]["effectiveness_classification"] == "did_not_meet"
    assert response.json()["items"][0]["algorithm_version"] == "decision_similarity_v1"
    assert response.json()["items"][0]["observed_usage"]["decision"]["referenced_count"] == 3
    assert response.json()["items"][0]["overall_similarity"] == 84.5
    assert service.call["minimum_relevance"] == "relevant"
    assert service.call["limit"] == 5


def test_pairwise_comparison_exposes_facts_not_recommendation():
    response = client(FakeMemoryService()).get("/decisions/current/precedents/historical-1")
    assert response.status_code == 200
    assert response.json()["historical_outcome"]["effectiveness_classification"] == "did_not_meet"
    assert "recommendation" not in response.json()


def test_invalid_filters_are_rejected_at_api_boundary():
    response = client(FakeMemoryService()).get("/decisions/current/precedents?minimum_relevance=recommended&limit=500")
    assert response.status_code == 422


def test_foreign_historical_identifier_is_non_disclosing():
    service = FakeMemoryService()
    service.failure = DecisionNotFoundError("Historical Decision not found")
    response = client(service).get("/decisions/current/precedents/foreign")
    assert response.status_code == 404
    assert response.json() == {"detail": "Historical Decision not found"}
