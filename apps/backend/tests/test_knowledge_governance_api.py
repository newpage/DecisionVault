from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.knowledge.router import get_knowledge_service, router
from app.modules.knowledge.service import KnowledgeNotFoundError, KnowledgePermissionError


CHECKLIST = {
    "provenance_verified": True,
    "classification_confirmed": True,
    "policy_authority_confirmed": True,
    "conflicts_reviewed": True,
    "ai_eligibility_appropriate": True,
}


class Service:
    failure = None
    review_kwargs = None

    def governance_queue(self, **kwargs):
        if self.failure:
            raise self.failure
        if not kwargs["can_review"]:
            raise KnowledgePermissionError("Knowledge approval permission required")
        return {"summary": {}, "review_queue": []}

    def governance_detail(self, **kwargs):
        if self.failure:
            raise self.failure
        return {"id": kwargs["card_id"], "title": "Critical alert"}

    def review_card(self, **kwargs):
        self.review_kwargs = kwargs
        if self.failure:
            raise self.failure
        return {"id": kwargs["card_id"], "approval_status": "approved"}


def client(service=None, *, can_review=True):
    app = FastAPI()
    app.include_router(router)
    service = service or Service()
    app.dependency_overrides[get_knowledge_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        membership=SimpleNamespace(clearance_rank=60),
        user=SimpleNamespace(id="user-1", full_name="Risk Reviewer", email="reviewer@example.com"),
        role_ids={"role-1"},
        can=lambda permission: can_review and permission == "knowledge.approve",
    )
    return TestClient(app), service


def test_queue_detail_and_review_use_authenticated_authorization_context():
    api, service = client()
    queue = api.get("/governance")
    assert queue.status_code == 200
    assert queue.json()["reviewer"]["name"] == "Risk Reviewer"
    assert api.get("/governance/card-1").status_code == 200
    response = api.post(
        "/knowledge/card-1/review",
        json={
            "action": "approve_publish",
            "rationale": "Verified against authoritative network evidence.",
            "checklist": CHECKLIST,
        },
    )
    assert response.status_code == 200
    assert service.review_kwargs["tenant_id"] == "tenant-1"
    assert service.review_kwargs["clearance_rank"] == 60
    assert service.review_kwargs["role_ids"] == {"role-1"}


def test_review_api_validates_human_rationale_and_non_disclosing_not_found():
    api, _ = client()
    invalid = api.post(
        "/knowledge/card-1/review",
        json={"action": "reject", "rationale": "short", "checklist": CHECKLIST},
    )
    assert invalid.status_code == 422

    service = Service()
    service.failure = KnowledgeNotFoundError("Knowledge Card not found")
    hidden, _ = client(service)
    assert hidden.get("/governance/foreign-card").status_code == 404
    assert hidden.get("/governance/foreign-card").json()["detail"] == "Knowledge Card not found"


def test_queue_requires_review_permission():
    api, _ = client(can_review=False)
    assert api.get("/governance").status_code == 403
