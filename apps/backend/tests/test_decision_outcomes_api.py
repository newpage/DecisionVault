from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.outcome_service import OutcomeStateError
from app.modules.decisions.router import get_outcome_service, router
from app.modules.decisions.service import DecisionNotFoundError


def outcome_response():
    now = datetime.now(timezone.utc)
    return {
        "id": "outcome-1",
        "decision_case_id": "decision-1",
        "title": "Reduce cycle time",
        "description": "Reduce processing time",
        "category": "business",
        "measurement_type": "duration",
        "baseline_value": 20,
        "target_value": 10,
        "target_min_value": None,
        "target_max_value": None,
        "target_boolean": None,
        "unit": "days",
        "target_direction": "decrease",
        "target_date": date.today(),
        "evaluation_window_days": None,
        "responsible_membership_id": None,
        "weight": 1,
        "is_critical": False,
        "success_criteria": "Ten days or less",
        "revision": 1,
        "status": "active",
        "amended_from_id": None,
        "amendment_rationale": "",
        "frozen_at": None,
        "created_by_membership_id": "member-1",
        "created_at": now,
        "updated_at": now,
    }


class FakeOutcomeService:
    failure = None
    calls = []

    def create_outcome(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return outcome_response()

    def verify_observation(self, **kwargs):
        if self.failure:
            raise self.failure
        now = datetime.now(timezone.utc)
        return {
            "id": "observation-1",
            "expected_outcome_id": "outcome-1",
            "observation_date": date.today(),
            "numeric_value": 8,
            "boolean_value": None,
            "observed_status": "achieved",
            "narrative": "",
            "provenance": "verified_business_record",
            "source_reference": "record",
            "decision_evidence_id": None,
            "recorded_by_membership_id": "member-2",
            "recorded_at": now,
            "verification_status": "verified",
            "verified_by_membership_id": "member-1",
            "verified_at": now,
            "verification_rationale": kwargs["rationale"],
            "superseded_by_id": None,
            "supersession_rationale": "",
        }


def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_outcome_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        membership=SimpleNamespace(id="member-1"),
        user=SimpleNamespace(id="user-1"),
        permissions={"decision.outcome.define"},
    )
    return TestClient(app)


def test_outcome_api_uses_authenticated_membership_and_explicit_dto():
    service = FakeOutcomeService()
    result = client(service).post(
        "/decisions/decision-1/outcomes",
        json={
            "title": "Reduce cycle time",
            "description": "Reduce processing time",
            "measurement_type": "duration",
            "target_value": 10,
            "unit": "days",
            "target_direction": "decrease",
            "success_criteria": "Ten days or less",
        },
    )
    assert result.status_code == 201
    assert result.json()["measurement_type"] == "duration"
    assert service.calls[-1]["tenant_id"] == "tenant-1"
    assert service.calls[-1]["membership_id"] == "member-1"


def test_invalid_lifecycle_action_returns_conflict():
    service = FakeOutcomeService()
    service.failure = OutcomeStateError(
        "Observations require an authoritatively approved Decision"
    )
    result = client(service).post(
        "/decisions/decision-1/outcomes",
        json={
            "title": "Reduce cycle time",
            "description": "Reduce processing time",
            "measurement_type": "duration",
            "target_value": 10,
            "target_direction": "decrease",
            "success_criteria": "Ten days or less",
        },
    )
    assert result.status_code == 409


def test_foreign_identifier_is_non_disclosing():
    service = FakeOutcomeService()
    service.failure = DecisionNotFoundError("Decision not found")
    result = client(service).post(
        "/decisions/foreign/outcomes",
        json={
            "title": "Reduce cycle time",
            "description": "Reduce processing time",
            "measurement_type": "duration",
            "target_value": 10,
            "target_direction": "decrease",
            "success_criteria": "Ten days or less",
        },
    )
    assert result.status_code == 404


def test_verification_requires_rationale_at_api_boundary():
    result = client(FakeOutcomeService()).post(
        "/decisions/decision-1/outcomes/outcome-1/observations/observation-1/verify",
        json={},
    )
    assert result.status_code == 422
