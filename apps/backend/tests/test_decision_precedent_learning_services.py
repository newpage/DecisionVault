from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import uid
from app.modules.decisions.learning_schemas import (
    EvaluationSupersede,
    LessonEvaluationCreate,
    PrecedentEvaluationCreate,
)
from app.modules.decisions.learning_service import (
    DecisionLearningService,
    LearningStateError,
)
from app.modules.decisions.memory import DecisionMemoryProfile
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.precedent_schemas import (
    LessonAdoptionCreate,
    PrecedentAttach,
)
from app.modules.decisions.precedent_service import (
    DecisionPrecedentService,
    PrecedentStateError,
)
from app.modules.decisions.service import DecisionConflictError, DecisionNotFoundError


NOW = datetime.now(timezone.utc)
PRECEDENT_PERMISSIONS = {
    "decision.view",
    "decision.edit",
    "decision.memory.view",
    "decision.precedent.manage",
    "decision.outcome.view",
    "decision.lesson.adopt",
    "decision.lesson.reject",
}
LEARNING_PERMISSIONS = {
    "decision.view",
    "decision.outcome.view",
    "decision.learning.view",
    "decision.learning.evaluate",
    "decision.learning.manage",
}


def decision(
    identifier,
    status="evidence_collection",
    classification_rank=20,
    access_policy_id=None,
):
    return SimpleNamespace(
        id=identifier,
        tenant_id="tenant",
        status=status,
        title=identifier,
        question=f"{identifier}?",
        business_concept_id="concept",
        workspace_id="workspace",
        decision_type="type",
        business_unit="unit",
        supplier_category="supplier",
        risk_level="medium",
        created_at=NOW,
        input_revision=1,
        classification_rank=classification_rank,
        access_policy_id=access_policy_id,
    )


def profile(item):
    return DecisionMemoryProfile(
        decision_id=item.id,
        business_concept_id=item.business_concept_id,
        workspace_id=item.workspace_id,
        title=item.title,
        question=item.question,
        decision_type=item.decision_type,
        business_unit=item.business_unit,
        supplier_category=item.supplier_category,
        risk_level=item.risk_level,
        created_at=item.created_at,
    )


class Memory:
    def __init__(self, current=None, historical=None):
        self.current = current or decision("current")
        self.historical = historical or decision("historical", "approved")

    def get_decision(self, **kwargs):
        return (
            self.current
            if kwargs["decision_id"] == self.current.id
            else (
                self.historical if kwargs["decision_id"] == self.historical.id else None
            )
        )

    def get_historical_decision(self, **kwargs):
        return (
            self.historical
            if kwargs["historical_decision_id"] == self.historical.id
            and self.historical.status
            in {"approved", "rejected", "closed", "conditionally_approved"}
            else None
        )

    def profile(self, item, **kwargs):
        return profile(item)

    def concept_name(self, **kwargs):
        return "Concept"

    def latest_assessment(self, **kwargs):
        return SimpleNamespace(classification="did_not_meet", outcome_summary="Failed")


class PrecedentRepository:
    def __init__(self, current=None, fail=False):
        self.current = current or decision("current")
        self.fail = fail
        self.saved = []
        self.events = []
        self.lesson_row = SimpleNamespace(
            id="lesson",
            decision_case_id="historical",
            lesson_type="risk",
            description="Stage rollout",
            business_impact="Lower disruption",
        )

    def decision_for_update(self, **kwargs):
        return self.current

    def active_membership(self, **kwargs):
        return SimpleNamespace(id="member")

    def mark_reviews_stale(self, **kwargs):
        return [SimpleNamespace(id="review")]

    def list_active_evidence(self, **kwargs):
        return []

    def lesson(self, **kwargs):
        return self.lesson_row if kwargs["lesson_id"] == self.lesson_row.id else None

    def list_precedents(self, **kwargs):
        return []

    def list_adoptions(self, **kwargs):
        return []

    def save(self, *, objects, events, refresh):
        if self.fail:
            raise RuntimeError("forced rollback")
        if not refresh.id:
            refresh.id = uid()
        if hasattr(refresh, "referenced_at") and refresh.referenced_at is None:
            refresh.referenced_at = NOW
            refresh.compared_at = NOW
        if hasattr(refresh, "acted_at") and refresh.acted_at is None:
            refresh.acted_at = NOW
        self.saved = objects
        self.events = events

    def precedent(self, **kwargs):
        return None

    def adoption(self, **kwargs):
        return None


def test_precedent_attachment_snapshots_revision_staleness_and_atomic_audits():
    repository = PrecedentRepository()
    service = DecisionPrecedentService(repository, Memory(current=repository.current))
    response = service.attach(
        tenant_id="tenant",
        decision_id="current",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=PRECEDENT_PERMISSIONS,
        command=PrecedentAttach(
            historical_decision_id="historical",
            relationship_type="cautionary",
            rationale="Avoid the failed rollout",
        ),
    )
    assert response.input_revision == 2
    assert response.precedent.similarity_algorithm_version == "decision_similarity_v1"
    assert {event.event_type for event in repository.events} == {
        "decision.precedent.attached",
        "decision.input_revision.incremented",
        "decision.review.marked_stale",
    }


@pytest.mark.parametrize("status", ["adopted", "rejected"])
def test_lesson_adoption_and_rejection_are_explicit_and_audited(status):
    repository = PrecedentRepository()
    service = DecisionPrecedentService(repository, Memory(current=repository.current))
    result = service.adopt_or_reject(
        tenant_id="tenant",
        decision_id="current",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=PRECEDENT_PERMISSIONS,
        command=LessonAdoptionCreate(
            historical_decision_id="historical",
            historical_lesson_id="lesson",
            status=status,
            rationale="Deliberate choice",
        ),
    )
    assert result.adoption.status == status
    assert repository.events[0].event_type == f"decision.lesson.{status}"


def test_precedent_lifecycle_permissions_duplicate_and_rollback():
    frozen = PrecedentRepository(current=decision("current", "approved"))
    with pytest.raises(PrecedentStateError):
        DecisionPrecedentService(frozen, Memory(current=frozen.current)).attach(
            tenant_id="tenant",
            decision_id="current",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=PRECEDENT_PERMISSIONS,
            command=PrecedentAttach(
                historical_decision_id="historical",
                relationship_type="supporting",
                rationale="Frozen",
            ),
        )
    with pytest.raises(DecisionPermissionError):
        DecisionPrecedentService(PrecedentRepository(), Memory()).attach(
            tenant_id="tenant",
            decision_id="current",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions={"decision.view"},
            command=PrecedentAttach(
                historical_decision_id="historical",
                relationship_type="supporting",
                rationale="Missing permission",
            ),
        )
    failing = PrecedentRepository(fail=True)
    with pytest.raises(RuntimeError):
        DecisionPrecedentService(failing, Memory(current=failing.current)).attach(
            tenant_id="tenant",
            decision_id="current",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=PRECEDENT_PERMISSIONS,
            command=PrecedentAttach(
                historical_decision_id="historical",
                relationship_type="supporting",
                rationale="Atomic failure",
            ),
        )
    assert failing.events == []


class LearningRepository:
    def __init__(self, assessment=True, duplicate=False, fail=False):
        self.assessment_ready = assessment
        self.duplicate = duplicate
        self.fail = fail
        self.saved_event = None
        self.saved_record = None
        self.reference = SimpleNamespace(
            id="reference",
            historical_decision_id="historical",
            similarity_score=84,
            snapshot_outcome_classification="did_not_meet",
        )
        self.adoption_row = SimpleNamespace(
            id="adoption", historical_decision_id="historical", status="adopted"
        )

    def active_membership(self, *args):
        return SimpleNamespace(id="member")

    def assessment(self, *args):
        return (
            SimpleNamespace(id="assessment", classification="met")
            if self.assessment_ready
            else None
        )

    def precedent(self, *args):
        return self.reference

    def adoption(self, *args):
        return self.adoption_row

    def valid_outcome_ids(self, *args):
        return set()

    def save(self, record, event):
        if self.fail:
            raise RuntimeError("forced rollback")
        if self.duplicate:
            raise IntegrityError("duplicate", {}, Exception())
        record.id = uid()
        record.evaluated_at = NOW
        self.saved_event = event
        self.saved_record = record
        return record

    def precedent_evaluation(self, *args):
        return self.saved_record

    def lesson_evaluation(self, *args):
        return self.saved_record

    def supersede(self, old, replacement, event, membership_id, rationale):
        old.superseded_at = NOW
        old.supersession_rationale = rationale
        old.superseded_by_evaluation_id = replacement.id
        old.superseded_by_membership_id = membership_id
        replacement.evaluated_at = NOW
        self.saved_event = event
        self.saved_record = replacement
        return replacement


def test_usefulness_evaluation_requires_outcome_readiness_and_is_audited():
    repository = LearningRepository()
    service = DecisionLearningService(repository, Memory())
    result = service.evaluate_precedent(
        tenant_id="tenant",
        decision_id="current",
        reference_id="reference",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=LEARNING_PERMISSIONS,
        command=PrecedentEvaluationCreate(
            effectiveness_assessment_id="assessment",
            classification="useful",
            rationale="Failure pattern avoided",
        ),
    )
    assert result.classification == "useful"
    assert result.historical_effectiveness_snapshot == "did_not_meet"
    assert (
        repository.saved_event.details["evaluation_rationale"]
        == "Failure pattern avoided"
    )
    with pytest.raises(LearningStateError):
        DecisionLearningService(
            LearningRepository(assessment=False), Memory()
        ).evaluate_precedent(
            tenant_id="tenant",
            decision_id="current",
            reference_id="reference",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
            command=PrecedentEvaluationCreate(
                effectiveness_assessment_id="assessment",
                classification="too_early",
                rationale="Not ready",
            ),
        )


def test_lesson_evaluation_semantics_duplicate_and_transaction_failure():
    repository = LearningRepository()
    service = DecisionLearningService(repository, Memory())
    result = service.evaluate_lesson(
        tenant_id="tenant",
        decision_id="current",
        adoption_id="adoption",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=LEARNING_PERMISSIONS,
        command=LessonEvaluationCreate(
            effectiveness_assessment_id="assessment",
            classification="beneficial",
            rationale="Reduced disruption",
            was_applied=True,
        ),
    )
    assert result.classification == "beneficial"
    repository.adoption_row.status = "rejected"
    with pytest.raises(LearningStateError):
        service.evaluate_lesson(
            tenant_id="tenant",
            decision_id="current",
            adoption_id="adoption",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
            command=LessonEvaluationCreate(
                effectiveness_assessment_id="assessment",
                classification="beneficial",
                rationale="Invalid for rejection",
            ),
        )
    with pytest.raises(DecisionConflictError):
        DecisionLearningService(
            LearningRepository(duplicate=True), Memory()
        ).evaluate_precedent(
            tenant_id="tenant",
            decision_id="current",
            reference_id="reference",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
            command=PrecedentEvaluationCreate(
                effectiveness_assessment_id="assessment",
                classification="neutral",
                rationale="Duplicate",
            ),
        )
    failing = LearningRepository(fail=True)
    with pytest.raises(RuntimeError):
        DecisionLearningService(failing, Memory()).evaluate_precedent(
            tenant_id="tenant",
            decision_id="current",
            reference_id="reference",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
            command=PrecedentEvaluationCreate(
                effectiveness_assessment_id="assessment",
                classification="harmful",
                rationale="Rollback",
            ),
        )
    assert failing.saved_event is None


def test_evaluation_supersession_revalidates_history_and_preserves_one_active_record():
    repository = LearningRepository()
    service = DecisionLearningService(repository, Memory())
    service.evaluate_precedent(
        tenant_id="tenant",
        decision_id="current",
        reference_id="reference",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=LEARNING_PERMISSIONS,
        command=PrecedentEvaluationCreate(
            effectiveness_assessment_id="assessment",
            classification="useful",
            rationale="Initially useful",
        ),
    )
    old = repository.saved_record
    replacement = service.supersede_precedent(
        tenant_id="tenant",
        decision_id="current",
        reference_id="reference",
        membership_id="member",
        actor_id="user",
        clearance_rank=50,
        role_ids=set(),
        permissions=LEARNING_PERMISSIONS,
        command=EvaluationSupersede(
            supersession_rationale="Later evidence changed the finding",
            classification="misleading",
            rationale="The apparent benefit did not persist",
        ),
    )
    assert replacement.classification == "misleading"
    assert old.superseded_by_evaluation_id == replacement.id
    assert repository.saved_event.details["supersession_rationale"] == (
        "Later evidence changed the finding"
    )

    hidden_memory = Memory(historical=decision("historical", "draft"))
    repository.saved_record = old
    with pytest.raises(DecisionNotFoundError, match="Historical Decision not found"):
        DecisionLearningService(repository, hidden_memory).supersede_precedent(
            tenant_id="tenant",
            decision_id="current",
            reference_id="reference",
            membership_id="member",
            actor_id="user",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
            command=EvaluationSupersede(
                supersession_rationale="Must not disclose",
                classification="neutral",
                rationale="Hidden source",
            ),
        )


class AggregateRepository:
    def __init__(self, active=True):
        self.active = active
        self.references = [
            SimpleNamespace(id="visible-ref", decision_case_id="visible"),
            SimpleNamespace(id="classified-ref", decision_case_id="classified"),
            SimpleNamespace(id="policy-ref", decision_case_id="policy"),
            SimpleNamespace(id="foreign-ref", decision_case_id="foreign"),
        ]

    def active_membership(self, *args):
        return SimpleNamespace(id="member") if self.active else None

    def references_to(self, *args):
        return self.references

    def precedent_evaluation(self, tenant_id, decision_id, reference_id):
        return SimpleNamespace(
            classification="useful", current_effectiveness_snapshot="met"
        )


class FilteringMemory(Memory):
    def __init__(self):
        super().__init__(historical=decision("historical", "approved"))
        self.rows = {
            "historical": self.historical,
            "visible": decision("visible", "approved"),
            "classified": decision("classified", "approved", classification_rank=60),
            "policy": decision("policy", "approved", access_policy_id="policy-a"),
        }

    def get_decision(self, **kwargs):
        row = self.rows.get(kwargs["decision_id"])
        if row is None or row.classification_rank > kwargs["clearance_rank"]:
            return None
        if row.access_policy_id and "allowed-role" not in kwargs["role_ids"]:
            return None
        return row


def test_aggregate_excludes_foreign_classified_and_policy_restricted_decisions():
    service = DecisionLearningService(AggregateRepository(), FilteringMemory())
    result = service.usage(
        tenant_id="tenant",
        historical_decision_id="historical",
        membership_id="member",
        clearance_rank=50,
        role_ids=set(),
        permissions=LEARNING_PERMISSIONS,
    )
    assert result.referenced_count == 1
    assert result.evaluated_count == 1
    assert result.classification_counts == {"useful": 1}


def test_inactive_membership_and_restricted_decision_are_non_disclosing():
    with pytest.raises(DecisionNotFoundError, match="Decision not found"):
        DecisionLearningService(
            AggregateRepository(active=False), FilteringMemory()
        ).usage(
            tenant_id="tenant",
            historical_decision_id="historical",
            membership_id="inactive",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
        )
    with pytest.raises(DecisionNotFoundError, match="Decision not found"):
        DecisionLearningService(AggregateRepository(), FilteringMemory()).usage(
            tenant_id="tenant",
            historical_decision_id="classified",
            membership_id="member",
            clearance_rank=50,
            role_ids=set(),
            permissions=LEARNING_PERMISSIONS,
        )
