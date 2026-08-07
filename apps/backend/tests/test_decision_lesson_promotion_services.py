from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import uid
from app.modules.decisions.promotion_schemas import LessonPromotionCreate
from app.modules.decisions.promotion_service import (
    DecisionLessonPromotionService,
    LessonPromotionStateError,
)
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.service import DecisionConflictError, DecisionNotFoundError


NOW = datetime.now(timezone.utc)
PERMISSIONS = {
    "decision.view",
    "decision.lesson.promotion.view",
    "decision.lesson.promote",
    "decision.lesson.promotion.review",
}


def decision(identifier, rank=20, policy=None):
    return SimpleNamespace(
        id=identifier,
        tenant_id="tenant",
        title=identifier,
        status="closed",
        workspace_id="workspace",
        business_concept_id="concept",
        classification_rank=rank,
        access_policy_id=policy,
    )


class Memory:
    def __init__(self, hidden=None, evaluation_policy=None):
        self.hidden = hidden
        self.rows = {
            "source": decision("source", 30),
            "evaluation": decision("evaluation", 40, evaluation_policy),
        }

    def get_decision(self, **kwargs):
        return (
            None
            if kwargs["decision_id"] == self.hidden
            else self.rows.get(kwargs["decision_id"])
        )


class Repository:
    def __init__(self, active=True, duplicate=False, fail=False, source_completed=True):
        self.active = active
        self.duplicate = duplicate
        self.fail = fail
        self.source_completed = source_completed
        self.lesson_row = SimpleNamespace(
            id="lesson",
            decision_case_id="source",
            lesson_type="risk",
            description="Stage rollout",
            business_impact="Lower disruption",
        )
        self.adoption = SimpleNamespace(
            id="adoption",
            historical_lesson_id="lesson",
            status="adopted",
            rationale="Apply it",
            application_note="Phase one",
        )
        self.assessment = SimpleNamespace(
            id="assessment",
            classification="met",
            rationale="Targets met",
            completed_at=NOW,
        )
        self.evaluation = SimpleNamespace(
            id="evaluation-row",
            decision_case_id="evaluation",
            lesson_adoption_id="adoption",
            effectiveness_assessment_id="assessment",
            classification="beneficial",
            rationale="Reduced disruption",
            was_applied=True,
            relevant_outcome_ids=[],
            outcome_relevance_details={},
            evaluated_at=NOW,
        )
        self.saved_objects = []
        self.saved_events = []
        self.proposal_row = None

    def active_membership(self, *args):
        return SimpleNamespace(id="member") if self.active else None

    def lesson(self, *args):
        return self.lesson_row

    def completed_assessment(self, *args):
        return self.assessment if self.source_completed else None

    def eligible_contexts(self, *args):
        return [(self.evaluation, self.adoption, self.assessment)]

    def evaluation_context(self, *args):
        return (self.evaluation, self.adoption, self.assessment)

    def outcomes(self, *args):
        return []

    def proposals(self, *args):
        return [self.proposal_row] if self.proposal_row else []

    def proposal(self, *args, **kwargs):
        return self.proposal_row

    def provenance(self, *args):
        return None

    def save(self, objects, events, refresh):
        if self.duplicate:
            raise IntegrityError("duplicate", {}, Exception())
        if self.fail:
            raise RuntimeError("rollback")
        if not refresh.id:
            refresh.id = uid()
        if hasattr(refresh, "proposed_at") and refresh.proposed_at is None:
            refresh.proposed_at = NOW
        for name in [
            "reviewed_by_membership_id",
            "reviewed_at",
            "review_rationale",
            "withdrawn_at",
            "withdrawal_rationale",
            "promoted_at",
            "resulting_knowledge_card_id",
        ]:
            if getattr(refresh, name, None) is None:
                setattr(refresh, name, None)
        self.saved_objects = objects
        self.saved_events = events
        self.proposal_row = refresh
        return refresh


def command():
    return LessonPromotionCreate(
        lesson_evaluation_id="evaluation-row",
        rationale="Reusable control",
        applicability="Regulated supplier rollouts",
        limitations="Not universal outside regulated operations",
        title="Phased supplier rollout",
        summary="Use phased rollout controls",
        body="Stage supplier rollout and verify each phase",
    )


def arguments():
    return dict(
        tenant_id="tenant",
        decision_id="source",
        lesson_id="lesson",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=PERMISSIONS,
    )


def test_proposal_requires_human_input_and_snapshots_governed_context():
    repository = Repository()
    service = DecisionLessonPromotionService(repository, Memory())
    result = service.propose(**arguments(), command=command())
    assert result.status == "proposed"
    assert result.snapshot_evaluation["classification"] == "beneficial"
    assert result.snapshot_effectiveness["source"]["classification"] == "met"
    assert result.snapshot_effectiveness["evaluation"]["classification"] == "met"
    assert result.inherited_classification_rank == 40
    assert (
        "universal applicability"
        in result.snapshot_provenance["observed_usefulness_caveat"]
    )
    assert repository.saved_events[0].event_type == "decision.lesson.promotion.proposed"


def test_duplicate_rollback_restricted_and_incompatible_policy_fail_closed():
    with pytest.raises(DecisionConflictError):
        DecisionLessonPromotionService(Repository(duplicate=True), Memory()).propose(
            **arguments(), command=command()
        )
    failing = Repository(fail=True)
    with pytest.raises(RuntimeError):
        DecisionLessonPromotionService(failing, Memory()).propose(
            **arguments(), command=command()
        )
    assert failing.saved_objects == [] and failing.saved_events == []
    with pytest.raises(DecisionNotFoundError, match="Decision lesson not found"):
        DecisionLessonPromotionService(Repository(active=False), Memory()).propose(
            **arguments(), command=command()
        )
    with pytest.raises(
        DecisionNotFoundError, match="Eligible lesson evaluation not found"
    ):
        DecisionLessonPromotionService(
            Repository(), Memory(hidden="evaluation")
        ).propose(**arguments(), command=command())
    source_memory = Memory(evaluation_policy="policy-b")
    source_memory.rows["source"].access_policy_id = "policy-a"
    with pytest.raises(LessonPromotionStateError, match="incompatible"):
        DecisionLessonPromotionService(Repository(), source_memory).propose(
            **arguments(), command=command()
        )


def test_requires_source_effectiveness_and_explicit_permissions():
    with pytest.raises(LessonPromotionStateError, match="completed effectiveness"):
        DecisionLessonPromotionService(
            Repository(source_completed=False), Memory()
        ).propose(**arguments(), command=command())
    denied = arguments()
    denied["permissions"] = {"decision.view"}
    with pytest.raises(DecisionPermissionError, match="decision.lesson.promote"):
        DecisionLessonPromotionService(Repository(), Memory()).propose(
            **denied, command=command()
        )


def test_approve_promote_creates_draft_card_provenance_and_audits_atomically():
    repository = Repository()
    service = DecisionLessonPromotionService(repository, Memory())
    service.propose(**arguments(), command=command())
    proposal = repository.proposal_row
    service.review(
        **arguments(),
        proposal_id=proposal.id,
        action="approved",
        rationale="Reviewed for reuse",
    )
    result = service.promote(**arguments(), proposal_id=proposal.id)
    assert result.status == "promoted" and result.resulting_knowledge_card_id
    card = next(
        item
        for item in repository.saved_objects
        if item.__class__.__name__ == "KnowledgeCard"
    )
    provenance = next(
        item
        for item in repository.saved_objects
        if item.__class__.__name__ == "KnowledgeCardLessonProvenance"
    )
    assert card.lifecycle_status == "draft" and card.approval_status == "not_submitted"
    assert card.classification_rank == 40 and card.ai_usage_allowed is False
    assert provenance.immutable_snapshot["lesson"]["id"] == "lesson"
    assert {event.event_type for event in repository.saved_events} == {
        "decision.lesson.promotion.promoted",
        "KnowledgeDraftCreatedFromDecisionLesson",
    }


def test_reject_and_withdraw_preserve_terminal_history():
    repository = Repository()
    service = DecisionLessonPromotionService(repository, Memory())
    service.propose(**arguments(), command=command())
    proposal = repository.proposal_row
    rejected = service.review(
        **arguments(),
        proposal_id=proposal.id,
        action="rejected",
        rationale="Too narrow",
    )
    assert rejected.status == "rejected"
    repository.proposal_row = None
    service.propose(**arguments(), command=command())
    proposal = repository.proposal_row
    withdrawn = service.withdraw(
        **arguments(), proposal_id=proposal.id, rationale="Source owner withdrew"
    )
    assert withdrawn.status == "withdrawn"
