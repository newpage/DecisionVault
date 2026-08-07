from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.router import get_learning_service, router
from app.modules.decisions.service import DecisionNotFoundError


NOW = datetime.now(timezone.utc).isoformat()


class FakeLearningService:
    failure = None

    def workspace(self, **kwargs):
        if self.failure:
            raise self.failure
        return {"precedent_evaluations": [], "lesson_evaluations": []}

    def evaluate_precedent(self, **kwargs):
        return {
            "id": "pe-1",
            "precedent_reference_id": kwargs["reference_id"],
            "historical_decision_id": "old",
            "effectiveness_assessment_id": kwargs[
                "command"
            ].effectiveness_assessment_id,
            "classification": kwargs["command"].classification,
            "rationale": kwargs["command"].rationale,
            "evaluator_membership_id": "member",
            "evaluated_at": NOW,
            "similarity_score_snapshot": 84,
            "historical_effectiveness_snapshot": "did_not_meet",
            "current_effectiveness_snapshot": "met",
            "outcome_alignment_details": {"same_classification": False},
            "superseded_at": None,
            "supersession_rationale": None,
        }

    def evaluate_lesson(self, **kwargs):
        return {
            "id": "le-1",
            "lesson_adoption_id": kwargs["adoption_id"],
            "historical_decision_id": "old",
            "effectiveness_assessment_id": kwargs[
                "command"
            ].effectiveness_assessment_id,
            "classification": kwargs["command"].classification,
            "rationale": kwargs["command"].rationale,
            "was_applied": kwargs["command"].was_applied,
            "relevant_outcome_ids": [],
            "evaluator_membership_id": "member",
            "evaluated_at": NOW,
            "current_effectiveness_snapshot": "met",
            "outcome_relevance_details": {},
            "superseded_at": None,
            "supersession_rationale": None,
        }

    def usage(self, **kwargs):
        if self.failure:
            raise self.failure
        return {
            "historical_decision_id": kwargs["historical_decision_id"],
            "referenced_count": 3,
            "evaluated_count": 2,
            "classification_counts": {"useful": 1, "misleading": 1},
            "current_outcome_distribution": {"met": 2},
        }


def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_learning_service] = FakeLearningService
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant",
        membership=SimpleNamespace(id="member", clearance_rank=50),
        user=SimpleNamespace(id="user"),
        role_ids=set(),
        permissions={
            "decision.view",
            "decision.outcome.view",
            "decision.learning.view",
            "decision.learning.evaluate",
        },
    )
    return TestClient(app)


def client_with(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_learning_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant",
        membership=SimpleNamespace(id="member", clearance_rank=50),
        user=SimpleNamespace(id="user"),
        role_ids=set(),
        permissions={
            "decision.view",
            "decision.outcome.view",
            "decision.learning.view",
        },
    )
    return TestClient(app)


def test_precedent_and_lesson_evaluation_dtos():
    api = client()
    precedent = api.post(
        "/decisions/current/precedent-references/ref/evaluation",
        json={
            "effectiveness_assessment_id": "assessment",
            "classification": "useful",
            "rationale": "Prevented a repeat failure",
        },
    )
    assert (
        precedent.status_code == 201 and precedent.json()["classification"] == "useful"
    )
    lesson = api.post(
        "/decisions/current/lesson-adoptions/adoption/evaluation",
        json={
            "effectiveness_assessment_id": "assessment",
            "classification": "beneficial",
            "rationale": "Reduced disruption",
            "was_applied": True,
        },
    )
    assert lesson.status_code == 201 and lesson.json()["was_applied"] is True


def test_learning_workspace_and_authorized_usage_shape():
    api = client()
    assert api.get("/decisions/current/learning").json() == {
        "precedent_evaluations": [],
        "lesson_evaluations": [],
    }
    usage = api.get("/decision-memory/old/usage").json()
    assert (
        usage["referenced_count"] == 3
        and usage["classification_counts"]["misleading"] == 1
    )


def test_learning_classifications_are_controlled():
    response = client().post(
        "/decisions/current/precedent-references/ref/evaluation",
        json={
            "effectiveness_assessment_id": "assessment",
            "classification": "perfect",
            "rationale": "Invalid",
        },
    )
    assert response.status_code == 422


def test_restricted_learning_resources_return_non_disclosing_404():
    service = FakeLearningService()
    service.failure = DecisionNotFoundError("Decision not found")
    response = client_with(service).get("/decision-memory/restricted/usage")
    assert response.status_code == 404
    assert response.json() == {"detail": "Decision not found"}
