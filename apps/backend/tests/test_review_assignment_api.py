from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.router import get_review_service, router
from app.modules.members.service import CandidateEligibilityError


def review_response(membership_id="membership-1"):
    now = datetime.now(timezone.utc)
    return {
        "id": "review-1",
        "decision_case_id": "decision-1",
        "sequence": 1,
        "review_type": "risk",
        "assigned_reviewer_membership_id": membership_id,
        "assigned_reviewer_name": "Avery Reviewer",
        "assigned_reviewer_email": "avery@example.com",
        "assigned_reviewer_organization": "Risk and Quality",
        "assigned_by": "manager-1",
        "assigned_at": now,
        "status": "assigned",
        "conclusion": None,
        "summary": "",
        "decision_revision": None,
        "freshness_status": "pending",
        "submitted_at": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_by": None,
        "cancelled_at": None,
        "cancellation_reason": None,
        "created_at": now,
        "updated_at": now,
        "evidence_ids": [],
    }


class FakeReviewService:
    failure = None

    def assign(self, **kwargs):
        if self.failure:
            raise self.failure
        return review_response(kwargs["membership_id"])

    def reassign(self, **kwargs):
        if self.failure:
            raise self.failure
        return review_response(kwargs["membership_id"])


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_review_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        user=SimpleNamespace(id="manager-1"),
        permissions={"decision.review.assign"},
    )
    return TestClient(app)


def test_assignment_and_reassignment_accept_membership_identity_and_rationale():
    test_client = client(FakeReviewService())
    assigned = test_client.post(
        "/decisions/decision-1/reviews",
        json={
            "membership_id": "membership-1",
            "review_type": "risk",
            "rationale": "Risk expertise is required",
        },
    )
    reassigned = test_client.patch(
        "/decisions/decision-1/reviews/review-1/assignment",
        json={
            "membership_id": "membership-2",
            "rationale": "Coverage changed before work started",
        },
    )

    assert assigned.status_code == 201
    assert assigned.json()["assigned_reviewer_membership_id"] == "membership-1"
    assert reassigned.status_code == 200
    assert reassigned.json()["assigned_reviewer_membership_id"] == "membership-2"


def test_assignment_rationale_is_required_at_api_boundary():
    result = client(FakeReviewService()).post(
        "/decisions/decision-1/reviews",
        json={"membership_id": "membership-1", "review_type": "risk"},
    )
    assert result.status_code == 422


def test_foreign_or_ineligible_membership_is_non_disclosing():
    service = FakeReviewService()
    service.failure = CandidateEligibilityError()

    result = client(service).post(
        "/decisions/decision-1/reviews",
        json={
            "membership_id": "foreign-membership",
            "review_type": "risk",
            "rationale": "Attempted forced assignment",
        },
    )
    assert result.status_code == 404
    assert result.json() == {"detail": "Reviewer candidate not found"}
