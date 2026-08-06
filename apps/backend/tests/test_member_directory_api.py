from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.service import DecisionNotFoundError
from app.modules.members.router import get_member_service, router
from app.modules.members.service import CandidateEligibilityError


class FakeDirectoryService:
    failure = None

    def reviewer_candidates(self, **kwargs):
        if self.failure:
            raise self.failure
        return {
            "items": [
                {
                    "membership_id": "membership-1",
                    "display_name": "Avery Reviewer",
                    "email": "avery@example.com",
                    "organization_name": "Risk and Quality",
                    "role_labels": ["Decision Reviewer"],
                    "responsibility": "decision_reviewer",
                }
            ],
            "offset": kwargs["offset"],
            "limit": kwargs["limit"],
            "total": 1,
        }


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_member_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        permissions={
            "decision.view",
            "decision.evidence.view",
            "decision.review.assign",
        },
    )
    return TestClient(app)


def test_candidate_discovery_search_pagination_and_safe_shape():
    result = client(FakeDirectoryService()).get(
        "/decisions/decision-1/reviewer-candidates",
        params={"query": "avery", "offset": 0, "limit": 10},
    )

    assert result.status_code == 200
    assert result.json()["items"][0] == {
        "membership_id": "membership-1",
        "display_name": "Avery Reviewer",
        "email": "avery@example.com",
        "organization_name": "Risk and Quality",
        "role_labels": ["Decision Reviewer"],
        "responsibility": "decision_reviewer",
    }


def test_directory_errors_are_safe_and_non_disclosing():
    service = FakeDirectoryService()
    service.failure = DecisionNotFoundError("Decision not found")
    assert (
        client(service).get("/decisions/foreign/reviewer-candidates").status_code == 404
    )

    service.failure = DecisionPermissionError("decision.review.assign")
    assert (
        client(service).get("/decisions/decision-1/reviewer-candidates").status_code
        == 403
    )

    service.failure = CandidateEligibilityError("Unsupported assignment responsibility")
    assert (
        client(service).get("/decisions/decision-1/reviewer-candidates").status_code
        == 422
    )


def test_candidate_query_limits_are_validated_at_api_boundary():
    result = client(FakeDirectoryService()).get(
        "/decisions/decision-1/reviewer-candidates", params={"limit": 51}
    )
    assert result.status_code == 422
