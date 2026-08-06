from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import AuditEvent, DecisionLessonAdoption, DecisionPrecedentReference
from app.modules.decisions.memory import compare_profiles
from app.modules.decisions.memory_repository import DecisionMemoryRepository
from app.modules.decisions.policies import (
    OUTCOME_VIEW_PERMISSION,
    authorize_view,
    require_permission,
)
from app.modules.decisions.precedent_repository import DecisionPrecedentRepository
from app.modules.decisions.precedent_schemas import (
    LessonAdoptionMutationResponse,
    LessonAdoptionResponse,
    PrecedentMutationResponse,
    PrecedentReferenceResponse,
)
from app.modules.decisions.service import DecisionConflictError, DecisionNotFoundError


EDITABLE_STATUSES = frozenset({"draft", "evidence_collection"})


class PrecedentStateError(ValueError):
    pass


class DecisionPrecedentService:
    def __init__(
        self, repository: DecisionPrecedentRepository, memory: DecisionMemoryRepository
    ) -> None:
        self._repository = repository
        self._memory = memory

    def list_precedents(
        self,
        *,
        tenant_id,
        decision_id,
        clearance_rank,
        role_ids,
        permissions,
        history=False,
    ):
        authorize_view(permissions)
        require_permission(permissions, "decision.precedent.view")
        self._visible_decision(tenant_id, decision_id, clearance_rank, role_ids)
        return [
            PrecedentReferenceResponse.model_validate(item)
            for item in self._repository.list_precedents(
                tenant_id=tenant_id, decision_id=decision_id, history=history
            )
        ]

    def attach(
        self,
        *,
        tenant_id,
        decision_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        command,
    ):
        authorize_view(permissions)
        require_permission(permissions, "decision.memory.view")
        require_permission(permissions, "decision.precedent.manage")
        rationale = self._text(command.rationale, "Attachment rationale")
        decision = self._editable_decision(
            tenant_id, decision_id, membership_id, clearance_rank, role_ids
        )
        historical = self._memory.get_historical_decision(
            tenant_id=tenant_id,
            current_decision_id=decision.id,
            historical_decision_id=command.historical_decision_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if historical is None:
            raise DecisionNotFoundError("Historical Decision not found")
        comparison = compare_profiles(
            self._memory.profile(
                decision,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
                include_evidence="decision.evidence.view" in permissions,
                include_governance="decision.review.view" in permissions,
                include_outcomes=OUTCOME_VIEW_PERMISSION in permissions,
            ),
            self._memory.profile(
                historical,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
                include_evidence="decision.evidence.view" in permissions,
                include_governance="decision.review.view" in permissions,
                include_outcomes=OUTCOME_VIEW_PERMISSION in permissions,
            ),
        )
        assessment = (
            self._memory.latest_assessment(
                tenant_id=tenant_id, decision_id=historical.id
            )
            if OUTCOME_VIEW_PERMISSION in permissions
            else None
        )
        before = decision.input_revision
        decision.input_revision += 1
        record = DecisionPrecedentReference(
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            historical_decision_id=historical.id,
            relationship_type=command.relationship_type,
            rationale=rationale,
            similarity_algorithm_version=comparison["algorithm_version"],
            similarity_score=comparison["overall_similarity"],
            similarity_components=comparison["components"],
            snapshot_business_concept_id=historical.business_concept_id,
            snapshot_business_concept_name=self._memory.concept_name(
                tenant_id=tenant_id, concept_id=historical.business_concept_id
            ),
            snapshot_historical_title=historical.title,
            snapshot_historical_status=historical.status,
            snapshot_outcome_classification=assessment.classification
            if assessment
            else None,
            snapshot_effectiveness_summary=assessment.outcome_summary
            if assessment
            else None,
            referenced_by_membership_id=membership_id,
        )
        stale = self._repository.mark_reviews_stale(
            tenant_id=tenant_id, decision_id=decision.id
        )
        events = self._events(
            decision,
            actor_id,
            membership_id,
            "decision.precedent.attached",
            {
                "historical_decision_id": historical.id,
                "relationship_type": command.relationship_type,
                "similarity_algorithm_version": comparison["algorithm_version"],
                "similarity_score": comparison["overall_similarity"],
                "rationale": rationale,
                "before_input_revision": before,
                "after_input_revision": decision.input_revision,
            },
            stale,
        )
        try:
            self._repository.save(
                objects=[decision, record, *stale], events=events, refresh=record
            )
        except IntegrityError as exc:
            raise DecisionConflictError(
                "Active precedent relationship already exists"
            ) from exc
        return PrecedentMutationResponse(
            input_revision=decision.input_revision,
            precedent=PrecedentReferenceResponse.model_validate(record),
        )

    def remove(
        self,
        *,
        tenant_id,
        decision_id,
        precedent_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        rationale,
    ):
        authorize_view(permissions)
        require_permission(permissions, "decision.precedent.manage")
        decision = self._editable_decision(
            tenant_id, decision_id, membership_id, clearance_rank, role_ids
        )
        record = self._repository.precedent(
            tenant_id=tenant_id, decision_id=decision.id, precedent_id=precedent_id
        )
        if record is None or record.removed_at is not None:
            raise DecisionNotFoundError("Precedent reference not found")
        rationale = self._text(rationale, "Removal rationale")
        before = decision.input_revision
        decision.input_revision += 1
        record.removed_at = datetime.now(timezone.utc)
        record.removed_by_membership_id = membership_id
        record.removal_rationale = rationale
        stale = self._repository.mark_reviews_stale(
            tenant_id=tenant_id, decision_id=decision.id
        )
        events = self._events(
            decision,
            actor_id,
            membership_id,
            "decision.precedent.removed",
            {
                "historical_decision_id": record.historical_decision_id,
                "relationship_type": record.relationship_type,
                "rationale": rationale,
                "before_input_revision": before,
                "after_input_revision": decision.input_revision,
            },
            stale,
        )
        self._repository.save(
            objects=[decision, record, *stale], events=events, refresh=record
        )
        return PrecedentMutationResponse(
            input_revision=decision.input_revision,
            precedent=PrecedentReferenceResponse.model_validate(record),
        )

    def list_adoptions(
        self, *, tenant_id, decision_id, clearance_rank, role_ids, permissions
    ):
        authorize_view(permissions)
        require_permission(permissions, "decision.precedent.view")
        self._visible_decision(tenant_id, decision_id, clearance_rank, role_ids)
        return [
            LessonAdoptionResponse.model_validate(item)
            for item in self._repository.list_adoptions(
                tenant_id=tenant_id, decision_id=decision_id
            )
        ]

    def adopt_or_reject(
        self,
        *,
        tenant_id,
        decision_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        command,
    ):
        authorize_view(permissions)
        require_permission(permissions, OUTCOME_VIEW_PERMISSION)
        require_permission(
            permissions,
            "decision.lesson.adopt"
            if command.status == "adopted"
            else "decision.lesson.reject",
        )
        decision = self._editable_decision(
            tenant_id, decision_id, membership_id, clearance_rank, role_ids
        )
        lesson = self._repository.lesson(
            tenant_id=tenant_id,
            historical_decision_id=command.historical_decision_id,
            lesson_id=command.historical_lesson_id,
        )
        # Resolve the lesson first by tenant, then revalidate its owning historical Decision.
        if lesson is None:
            raise DecisionNotFoundError("Historical lesson not found")
        historical = self._memory.get_historical_decision(
            tenant_id=tenant_id,
            current_decision_id=decision.id,
            historical_decision_id=lesson.decision_case_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if historical is None:
            raise DecisionNotFoundError("Historical lesson not found")
        rationale = self._text(command.rationale, f"{command.status.title()} rationale")
        before = decision.input_revision
        decision.input_revision += 1
        record = DecisionLessonAdoption(
            tenant_id=tenant_id,
            decision_case_id=decision.id,
            historical_decision_id=historical.id,
            historical_lesson_id=lesson.id,
            status=command.status,
            rationale=rationale,
            application_note=command.application_note.strip(),
            snapshot_lesson_type=lesson.lesson_type,
            snapshot_lesson_description=lesson.description,
            snapshot_lesson_business_impact=lesson.business_impact,
            acted_by_membership_id=membership_id,
        )
        stale = self._repository.mark_reviews_stale(
            tenant_id=tenant_id, decision_id=decision.id
        )
        events = self._events(
            decision,
            actor_id,
            membership_id,
            f"decision.lesson.{command.status}",
            {
                "historical_decision_id": historical.id,
                "lesson_id": lesson.id,
                "rationale": rationale,
                "before_input_revision": before,
                "after_input_revision": decision.input_revision,
            },
            stale,
        )
        try:
            self._repository.save(
                objects=[decision, record, *stale], events=events, refresh=record
            )
        except IntegrityError as exc:
            raise DecisionConflictError(
                "An active choice already exists for this lesson"
            ) from exc
        return LessonAdoptionMutationResponse(
            input_revision=decision.input_revision,
            adoption=LessonAdoptionResponse.model_validate(record),
        )

    def supersede(
        self,
        *,
        tenant_id,
        decision_id,
        adoption_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        rationale,
    ):
        authorize_view(permissions)
        require_permission(permissions, "decision.lesson.adopt")
        require_permission(permissions, "decision.lesson.reject")
        decision = self._editable_decision(
            tenant_id, decision_id, membership_id, clearance_rank, role_ids
        )
        record = self._repository.adoption(
            tenant_id=tenant_id, decision_id=decision.id, adoption_id=adoption_id
        )
        if record is None or record.status == "superseded":
            raise DecisionNotFoundError("Lesson adoption not found")
        rationale = self._text(rationale, "Supersession rationale")
        before = decision.input_revision
        decision.input_revision += 1
        record.status = "superseded"
        record.superseded_at = datetime.now(timezone.utc)
        record.superseded_by_membership_id = membership_id
        record.supersession_rationale = rationale
        stale = self._repository.mark_reviews_stale(
            tenant_id=tenant_id, decision_id=decision.id
        )
        events = self._events(
            decision,
            actor_id,
            membership_id,
            "decision.lesson.adoption_superseded",
            {
                "historical_decision_id": record.historical_decision_id,
                "lesson_id": record.historical_lesson_id,
                "rationale": rationale,
                "before_input_revision": before,
                "after_input_revision": decision.input_revision,
            },
            stale,
        )
        self._repository.save(
            objects=[decision, record, *stale], events=events, refresh=record
        )
        return LessonAdoptionMutationResponse(
            input_revision=decision.input_revision,
            adoption=LessonAdoptionResponse.model_validate(record),
        )

    def _visible_decision(self, tenant_id, decision_id, clearance_rank, role_ids):
        decision = self._memory.get_decision(
            tenant_id=tenant_id,
            decision_id=decision_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision

    def _editable_decision(
        self, tenant_id, decision_id, membership_id, clearance_rank, role_ids
    ):
        visible = self._visible_decision(
            tenant_id, decision_id, clearance_rank, role_ids
        )
        decision = self._repository.decision_for_update(
            tenant_id=tenant_id, decision_id=visible.id
        )
        if (
            self._repository.active_membership(
                tenant_id=tenant_id, membership_id=membership_id
            )
            is None
        ):
            raise DecisionNotFoundError("Decision not found")
        if decision.status not in EDITABLE_STATUSES:
            raise PrecedentStateError(
                "Governed precedent inputs are frozen in this Decision state"
            )
        return decision

    @staticmethod
    def _text(value, label):
        value = value.strip()
        if len(value) < 3:
            raise PrecedentStateError(f"{label} is required")
        return value

    @staticmethod
    def _events(decision, actor_id, membership_id, event_type, details, stale):
        events = [
            AuditEvent(
                tenant_id=decision.tenant_id,
                actor_id=actor_id,
                event_type=event_type,
                entity_type="decision_case",
                entity_id=decision.id,
                description=event_type.replace(".", " ").title(),
                details={**details, "actor_membership_id": membership_id},
            )
        ]
        events.append(
            AuditEvent(
                tenant_id=decision.tenant_id,
                actor_id=actor_id,
                event_type="decision.input_revision.incremented",
                entity_type="decision_case",
                entity_id=decision.id,
                description="Decision input revision incremented for governed precedent change",
                details={
                    "actor_membership_id": membership_id,
                    "before_input_revision": details["before_input_revision"],
                    "after_input_revision": details["after_input_revision"],
                },
            )
        )
        for review in stale:
            events.append(
                AuditEvent(
                    tenant_id=decision.tenant_id,
                    actor_id=actor_id,
                    event_type="decision.review.marked_stale",
                    entity_type="decision_case",
                    entity_id=decision.id,
                    description="Completed review marked stale after governed precedent change",
                    details={
                        "actor_membership_id": membership_id,
                        "review_id": review.id,
                        "input_revision": decision.input_revision,
                    },
                )
            )
        return events
