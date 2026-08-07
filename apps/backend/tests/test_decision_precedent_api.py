from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.router import get_precedent_service, router


NOW = datetime.now(timezone.utc).isoformat()


def precedent():
    return {
        "id": "ref-1",
        "historical_decision_id": "historical-1",
        "relationship_type": "cautionary",
        "rationale": "Avoid the prior rollout gap",
        "similarity_algorithm_version": "decision_similarity_v1",
        "similarity_score": 82.5,
        "similarity_components": {},
        "snapshot_business_concept_id": "concept-1",
        "snapshot_business_concept_name": "Change Control",
        "snapshot_historical_title": "Prior rollout",
        "snapshot_historical_status": "approved",
        "snapshot_outcome_classification": "did_not_meet",
        "snapshot_effectiveness_summary": "Controls arrived late",
        "compared_at": NOW,
        "referenced_by_membership_id": "member-1",
        "referenced_at": NOW,
        "removed_by_membership_id": None,
        "removed_at": None,
        "removal_rationale": None,
    }


def adoption():
    return {
        "id": "adoption-1",
        "historical_decision_id": "historical-1",
        "historical_lesson_id": "lesson-1",
        "status": "rejected",
        "rationale": "Not applicable to this operating model",
        "application_note": "",
        "snapshot_lesson_type": "risk",
        "snapshot_lesson_description": "Stage the rollout",
        "snapshot_lesson_business_impact": "Lower disruption",
        "acted_by_membership_id": "member-1",
        "acted_at": NOW,
        "superseded_by_membership_id": None,
        "superseded_at": None,
        "supersession_rationale": None,
    }


class FakeService:
    def list_precedents(self, **kwargs):
        return [precedent()]

    def attach(self, **kwargs):
        return {"input_revision": 3, "precedent": precedent()}

    def remove(self, **kwargs):
        return {
            "input_revision": 4,
            "precedent": {
                **precedent(),
                "removed_at": NOW,
                "removed_by_membership_id": "member-1",
                "removal_rationale": kwargs["rationale"],
            },
        }

    def list_adoptions(self, **kwargs):
        return [adoption()]

    def adopt_or_reject(self, **kwargs):
        return {"input_revision": 5, "adoption": adoption()}

    def supersede(self, **kwargs):
        return {
            "input_revision": 6,
            "adoption": {
                **adoption(),
                "superseded_at": NOW,
                "superseded_by_membership_id": "member-1",
                "supersession_rationale": kwargs["rationale"],
            },
        }


def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_precedent_service] = FakeService
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        membership=SimpleNamespace(id="member-1", clearance_rank=50),
        user=SimpleNamespace(id="user-1"),
        role_ids={"role-1"},
        permissions={
            "decision.view",
            "decision.edit",
            "decision.memory.view",
            "decision.precedent.view",
            "decision.precedent.manage",
            "decision.outcome.view",
            "decision.lesson.adopt",
            "decision.lesson.reject",
        },
    )
    return TestClient(app)


def test_governed_precedent_endpoints_use_explicit_dtos():
    api = client()
    assert (
        api.get("/decisions/current/precedent-references").json()[0]["similarity_score"]
        == 82.5
    )
    attached = api.post(
        "/decisions/current/precedent-references",
        json={
            "historical_decision_id": "historical-1",
            "relationship_type": "cautionary",
            "rationale": "Avoid the prior rollout gap",
        },
    )
    assert attached.status_code == 201
    assert attached.json()["input_revision"] == 3
    assert (
        api.request(
            "DELETE",
            "/decisions/current/precedent-references/ref-1",
            json={"rationale": "No longer relevant"},
        ).json()["input_revision"]
        == 4
    )


def test_lesson_choice_and_supersession_endpoints():
    api = client()
    assert (
        api.get("/decisions/current/lesson-adoptions").json()[0]["status"] == "rejected"
    )
    created = api.post(
        "/decisions/current/lesson-adoptions",
        json={
            "historical_decision_id": "historical-1",
            "historical_lesson_id": "lesson-1",
            "status": "rejected",
            "rationale": "Not applicable",
        },
    )
    assert created.status_code == 201
    superseded = api.post(
        "/decisions/current/lesson-adoptions/adoption-1/supersede",
        json={"rationale": "Reconsidered"},
    ).json()["adoption"]
    assert superseded["status"] == "rejected"
    assert superseded["superseded_at"] is not None


def test_controlled_values_and_rationales_are_validated_at_api_boundary():
    api = client()
    assert (
        api.post(
            "/decisions/current/precedent-references",
            json={
                "historical_decision_id": "historical-1",
                "relationship_type": "related",
                "rationale": "valid",
            },
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/decisions/current/lesson-adoptions",
            json={
                "historical_decision_id": "historical-1",
                "historical_lesson_id": "lesson-1",
                "status": "adopted",
                "rationale": "",
            },
        ).status_code
        == 422
    )
