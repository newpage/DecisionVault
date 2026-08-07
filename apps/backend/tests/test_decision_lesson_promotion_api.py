from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_principal
from app.modules.decisions.router import get_promotion_service, router
from app.modules.decisions.service import DecisionNotFoundError


NOW = datetime.now(timezone.utc).isoformat()


def proposal(status="proposed"):
    return {
        "id": "proposal",
        "source_decision_id": "source",
        "source_lesson_id": "lesson",
        "evaluation_decision_id": "evaluation",
        "lesson_adoption_id": "adoption",
        "lesson_evaluation_id": "evaluation-row",
        "effectiveness_assessment_id": "assessment",
        "status": status,
        "rationale": "Reusable",
        "applicability": "Regulated rollouts",
        "limitations": "Not universal",
        "proposed_title": "Phased rollout",
        "proposed_summary": "Stage rollout",
        "proposed_body": "Use verified phases",
        "snapshot_source_decision": {},
        "snapshot_lesson": {},
        "snapshot_adoption": {},
        "snapshot_evaluation": {},
        "snapshot_effectiveness": {},
        "snapshot_relevant_outcomes": [],
        "snapshot_provenance": {},
        "inherited_classification_rank": 40,
        "inherited_access_policy_id": None,
        "proposed_by_membership_id": "member",
        "proposed_at": NOW,
        "reviewed_by_membership_id": None,
        "reviewed_at": None,
        "review_rationale": None,
        "withdrawn_at": None,
        "withdrawal_rationale": None,
        "promoted_at": None,
        "resulting_knowledge_card_id": None,
    }


class Service:
    failure = None

    def _result(self, status="proposed"):
        if self.failure:
            raise self.failure
        return proposal(status)

    def workspace(self, **kwargs):
        if self.failure:
            raise self.failure
        return {
            "eligibility": {
                "lesson_id": "lesson",
                "eligible": True,
                "reasons": [],
                "evaluations": [{"evaluation_id": "evaluation-row"}],
            },
            "proposals": [proposal()],
        }

    def propose(self, **kwargs):
        return self._result()

    def review(self, **kwargs):
        return self._result(kwargs["action"])

    def withdraw(self, **kwargs):
        return self._result("withdrawn")

    def promote(self, **kwargs):
        item = self._result("promoted")
        item["resulting_knowledge_card_id"] = "card"
        item["promoted_at"] = NOW
        return item

    def provenance(self, **kwargs):
        if self.failure:
            raise self.failure
        return {
            "knowledge_card_id": "card",
            "promotion_proposal_id": "proposal",
            "source_decision_id": "source",
            "source_lesson_id": "lesson",
            "lesson_evaluation_id": "evaluation-row",
            "immutable_snapshot": {"applicability": "Regulated rollouts"},
            "created_at": NOW,
        }


def client(service=None, permissions=None):
    app = FastAPI()
    app.include_router(router)
    service = service or Service()
    app.dependency_overrides[get_promotion_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant",
        membership=SimpleNamespace(id="member", clearance_rank=50),
        user=SimpleNamespace(id="user"),
        role_ids=set(),
        permissions=permissions
        or {
            "decision.view",
            "decision.lesson.promotion.view",
            "decision.lesson.promote",
            "decision.lesson.promotion.review",
        },
    )
    return TestClient(app)


def test_promotion_lifecycle_and_provenance_endpoints():
    api = client()
    assert (
        api.get("/decisions/source/lessons/lesson/promotions").json()["eligibility"][
            "eligible"
        ]
        is True
    )
    created = api.post(
        "/decisions/source/lessons/lesson/promotions",
        json={
            "lesson_evaluation_id": "evaluation-row",
            "rationale": "Reusable",
            "applicability": "Regulated rollouts",
            "limitations": "Not universal",
            "title": "Phased rollout",
            "summary": "Stage rollout",
            "body": "Use verified phases",
        },
    )
    assert created.status_code == 201
    assert (
        api.post(
            "/decisions/source/lessons/lesson/promotions/proposal/review/approve",
            json={"rationale": "Reviewed"},
        ).json()["status"]
        == "approved"
    )
    assert (
        api.post("/decisions/source/lessons/lesson/promotions/proposal/promote").json()[
            "resulting_knowledge_card_id"
        ]
        == "card"
    )
    assert (
        api.get("/knowledge/card/decision-lesson-provenance").json()[
            "immutable_snapshot"
        ]["applicability"]
        == "Regulated rollouts"
    )


def test_invalid_dto_permission_and_restricted_sources_are_non_disclosing():
    assert (
        client()
        .post("/decisions/source/lessons/lesson/promotions", json={})
        .status_code
        == 422
    )
    restricted = Service()
    restricted.failure = DecisionNotFoundError("Decision lesson not found")
    response = client(restricted).get("/decisions/source/lessons/lesson/promotions")
    assert response.status_code == 404 and response.json() == {
        "detail": "Decision lesson not found"
    }
