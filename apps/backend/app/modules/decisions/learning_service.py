from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditEvent,
    DecisionLessonEvaluation,
    DecisionPrecedentEvaluation,
    uid,
)
from app.modules.decisions.learning_schemas import (
    DecisionLearningResponse,
    HistoricalUsageResponse,
    LessonUsageResponse,
    LessonEvaluationResponse,
    PrecedentEvaluationResponse,
)
from app.modules.decisions.policies import authorize_view, require_permission
from app.modules.decisions.service import DecisionConflictError, DecisionNotFoundError


class LearningStateError(ValueError):
    pass


class DecisionLearningService:
    def __init__(self, repository, memory):
        self._repository = repository
        self._memory = memory

    def workspace(
        self,
        *,
        tenant_id,
        decision_id,
        membership_id,
        clearance_rank,
        role_ids,
        permissions,
    ):
        self._authorize_view(permissions)
        self._ready(tenant_id, decision_id, membership_id, clearance_rank, role_ids)
        precedents = []
        for item in self._repository.list_precedent_evaluations(tenant_id, decision_id):
            if self._historical_or_none(
                tenant_id,
                decision_id,
                item.historical_decision_id,
                clearance_rank,
                role_ids,
            ):
                precedents.append(PrecedentEvaluationResponse.model_validate(item))
        lessons = []
        for item in self._repository.list_lesson_evaluations(tenant_id, decision_id):
            if self._historical_or_none(
                tenant_id,
                decision_id,
                item.historical_decision_id,
                clearance_rank,
                role_ids,
            ):
                lessons.append(LessonEvaluationResponse.model_validate(item))
        return DecisionLearningResponse(
            precedent_evaluations=precedents,
            lesson_evaluations=lessons,
        )

    def evaluate_precedent(
        self,
        *,
        tenant_id,
        decision_id,
        reference_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        command,
    ):
        self._authorize_evaluate(permissions)
        self._ready(tenant_id, decision_id, membership_id, clearance_rank, role_ids)
        reference = self._repository.precedent(tenant_id, decision_id, reference_id)
        if reference is None:
            raise DecisionNotFoundError("Precedent reference not found")
        self._historical(
            tenant_id,
            decision_id,
            reference.historical_decision_id,
            clearance_rank,
            role_ids,
        )
        assessment = self._assessment(
            tenant_id, decision_id, command.effectiveness_assessment_id
        )
        record = DecisionPrecedentEvaluation(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            precedent_reference_id=reference.id,
            historical_decision_id=reference.historical_decision_id,
            effectiveness_assessment_id=assessment.id,
            classification=command.classification,
            rationale=command.rationale.strip(),
            evaluator_membership_id=membership_id,
            similarity_score_snapshot=reference.similarity_score,
            historical_effectiveness_snapshot=reference.snapshot_outcome_classification,
            current_effectiveness_snapshot=assessment.classification,
            outcome_alignment_details={
                "historical": reference.snapshot_outcome_classification,
                "current": assessment.classification,
                "same_classification": reference.snapshot_outcome_classification
                == assessment.classification,
                **command.outcome_alignment_details,
            },
        )
        return PrecedentEvaluationResponse.model_validate(
            self._save(
                record,
                actor_id,
                "decision.precedent.usefulness_evaluated",
                membership_id,
            )
        )

    def evaluate_lesson(
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
        command,
    ):
        self._authorize_evaluate(permissions)
        self._ready(tenant_id, decision_id, membership_id, clearance_rank, role_ids)
        adoption = self._repository.adoption(tenant_id, decision_id, adoption_id)
        if adoption is None:
            raise DecisionNotFoundError("Lesson adoption not found")
        self._historical(
            tenant_id,
            decision_id,
            adoption.historical_decision_id,
            clearance_rank,
            role_ids,
        )
        assessment = self._assessment(
            tenant_id, decision_id, command.effectiveness_assessment_id
        )
        if set(command.relevant_outcome_ids) != self._repository.valid_outcome_ids(
            tenant_id, decision_id, command.relevant_outcome_ids
        ):
            raise DecisionNotFoundError("Outcome reference not found")
        self._validate_lesson_classification(adoption.status, command.classification)
        record = DecisionLessonEvaluation(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            lesson_adoption_id=adoption.id,
            historical_decision_id=adoption.historical_decision_id,
            effectiveness_assessment_id=assessment.id,
            classification=command.classification,
            rationale=command.rationale.strip(),
            was_applied=command.was_applied,
            relevant_outcome_ids=command.relevant_outcome_ids,
            evaluator_membership_id=membership_id,
            current_effectiveness_snapshot=assessment.classification,
            outcome_relevance_details=command.outcome_relevance_details,
        )
        event = (
            "decision.lesson.rejection_reviewed"
            if adoption.status == "rejected"
            else "decision.lesson.usefulness_evaluated"
        )
        return LessonEvaluationResponse.model_validate(
            self._save(record, actor_id, event, membership_id)
        )

    def usage(
        self,
        *,
        tenant_id,
        historical_decision_id,
        clearance_rank,
        role_ids,
        permissions,
        membership_id,
    ):
        self._authorize_view(permissions)
        self._ready(
            tenant_id,
            historical_decision_id,
            membership_id,
            clearance_rank,
            role_ids,
        )
        visible_refs = []
        for ref in self._repository.references_to(tenant_id, historical_decision_id):
            if self._memory.get_decision(
                tenant_id=tenant_id,
                decision_id=ref.decision_case_id,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
            ):
                visible_refs.append(ref)
        counts = {}
        outcomes = {}
        evaluated = 0
        for ref in visible_refs:
            item = self._repository.precedent_evaluation(
                tenant_id, ref.decision_case_id, ref.id
            )
            if item:
                evaluated += 1
                counts[item.classification] = counts.get(item.classification, 0) + 1
                outcomes[item.current_effectiveness_snapshot] = (
                    outcomes.get(item.current_effectiveness_snapshot, 0) + 1
                )
        return HistoricalUsageResponse(
            historical_decision_id=historical_decision_id,
            referenced_count=len(visible_refs),
            evaluated_count=evaluated,
            classification_counts=counts,
            current_outcome_distribution=outcomes,
        )

    def supersede_precedent(
        self,
        *,
        tenant_id,
        decision_id,
        reference_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        command,
    ):
        self._authorize_evaluate(permissions)
        require_permission(permissions, "decision.learning.manage")
        self._ready(tenant_id, decision_id, membership_id, clearance_rank, role_ids)
        old = self._repository.precedent_evaluation(
            tenant_id, decision_id, reference_id
        )

        if old is None:
            raise DecisionNotFoundError("Precedent evaluation not found")
        self._historical(
            tenant_id,
            decision_id,
            old.historical_decision_id,
            clearance_rank,
            role_ids,
        )
        allowed = {
            "highly_useful",
            "useful",
            "neutral",
            "misleading",
            "harmful",
            "inconclusive",
            "too_early",
        }
        if command.classification not in allowed:
            raise LearningStateError("Invalid precedent evaluation classification")
        replacement = DecisionPrecedentEvaluation(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            precedent_reference_id=old.precedent_reference_id,
            historical_decision_id=old.historical_decision_id,
            effectiveness_assessment_id=old.effectiveness_assessment_id,
            classification=command.classification,
            rationale=command.rationale.strip(),
            evaluator_membership_id=membership_id,
            similarity_score_snapshot=old.similarity_score_snapshot,
            historical_effectiveness_snapshot=old.historical_effectiveness_snapshot,
            current_effectiveness_snapshot=old.current_effectiveness_snapshot,
            outcome_alignment_details=old.outcome_alignment_details,
        )
        event = self._event(
            replacement,
            actor_id,
            "decision.precedent.evaluation_superseded",
            membership_id,
        )
        event.details["supersession_rationale"] = command.supersession_rationale
        return PrecedentEvaluationResponse.model_validate(
            self._repository.supersede(
                old,
                replacement,
                event,
                membership_id,
                command.supersession_rationale.strip(),
            )
        )

    def lesson_usage(
        self,
        *,
        tenant_id,
        historical_decision_id,
        historical_lesson_id,
        membership_id,
        clearance_rank,
        role_ids,
        permissions,
    ):
        self._authorize_view(permissions)
        self._ready(
            tenant_id,
            historical_decision_id,
            membership_id,
            clearance_rank,
            role_ids,
        )
        adopted = rejected = evaluated = 0
        counts = {}
        for adoption in self._repository.adoptions_to_lesson(
            tenant_id, historical_lesson_id
        ):
            if not self._memory.get_decision(
                tenant_id=tenant_id,
                decision_id=adoption.decision_case_id,
                clearance_rank=clearance_rank,
                role_ids=role_ids,
            ):
                continue
            if adoption.status == "adopted":
                adopted += 1
            else:
                rejected += 1
            item = self._repository.lesson_evaluation(
                tenant_id, adoption.decision_case_id, adoption.id
            )
            if item:
                evaluated += 1
                counts[item.classification] = counts.get(item.classification, 0) + 1
        return LessonUsageResponse(
            historical_lesson_id=historical_lesson_id,
            adopted_count=adopted,
            rejected_count=rejected,
            evaluated_count=evaluated,
            classification_counts=counts,
        )

    def supersede_lesson(
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
        command,
    ):
        self._authorize_evaluate(permissions)
        require_permission(permissions, "decision.learning.manage")
        self._ready(tenant_id, decision_id, membership_id, clearance_rank, role_ids)
        old = self._repository.lesson_evaluation(tenant_id, decision_id, adoption_id)
        if old is None:
            raise DecisionNotFoundError("Lesson evaluation not found")
        self._historical(
            tenant_id,
            decision_id,
            old.historical_decision_id,
            clearance_rank,
            role_ids,
        )
        adoption = self._repository.adoption(tenant_id, decision_id, adoption_id)
        if adoption is None:
            raise DecisionNotFoundError("Lesson adoption not found")
        allowed = {
            "beneficial",
            "neutral",
            "ineffective",
            "harmful",
            "not_applied",
            "inconclusive",
            "appropriate_rejection",
            "potentially_costly_rejection",
        }
        if command.classification not in allowed:
            raise LearningStateError("Invalid lesson evaluation classification")
        self._validate_lesson_classification(adoption.status, command.classification)
        replacement = DecisionLessonEvaluation(
            id=uid(),
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            lesson_adoption_id=old.lesson_adoption_id,
            historical_decision_id=old.historical_decision_id,
            effectiveness_assessment_id=old.effectiveness_assessment_id,
            classification=command.classification,
            rationale=command.rationale.strip(),
            was_applied=old.was_applied,
            relevant_outcome_ids=old.relevant_outcome_ids,
            evaluator_membership_id=membership_id,
            current_effectiveness_snapshot=old.current_effectiveness_snapshot,
            outcome_relevance_details=old.outcome_relevance_details,
        )
        event = self._event(
            replacement,
            actor_id,
            "decision.lesson.evaluation_superseded",
            membership_id,
        )
        event.details["supersession_rationale"] = command.supersession_rationale
        return LessonEvaluationResponse.model_validate(
            self._repository.supersede(
                old,
                replacement,
                event,
                membership_id,
                command.supersession_rationale.strip(),
            )
        )

    def _save(self, record, actor_id, event_type, membership_id):
        event = self._event(record, actor_id, event_type, membership_id)
        try:
            return self._repository.save(record, event)
        except IntegrityError as exc:
            raise DecisionConflictError("An active evaluation already exists") from exc

    @staticmethod
    def _event(record, actor_id, event_type, membership_id):
        return AuditEvent(
            tenant_id=record.tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            entity_type="decision_case",
            entity_id=record.decision_case_id,
            description=event_type.replace(".", " ").title(),
            details={
                "historical_decision_id": record.historical_decision_id,
                "precedent_reference_id": getattr(
                    record, "precedent_reference_id", None
                ),
                "lesson_adoption_id": getattr(record, "lesson_adoption_id", None),
                "evaluation_classification": record.classification,
                "evaluation_rationale": record.rationale,
                "effectiveness_assessment_id": record.effectiveness_assessment_id,
                "evaluator_membership_id": membership_id,
                "deterministic_context": getattr(
                    record,
                    "outcome_alignment_details",
                    getattr(record, "outcome_relevance_details", {}),
                ),
            },
        )

    def _assessment(self, tenant_id, decision_id, assessment_id):
        item = self._repository.assessment(tenant_id, decision_id, assessment_id)
        if item is None:
            raise LearningStateError("A completed effectiveness assessment is required")
        return item

    def _ready(self, tenant_id, decision_id, membership_id, clearance_rank, role_ids):
        self._visible(tenant_id, decision_id, clearance_rank, role_ids)
        if self._repository.active_membership(tenant_id, membership_id) is None:
            raise DecisionNotFoundError("Decision not found")

    def _historical(
        self, tenant_id, decision_id, historical_id, clearance_rank, role_ids
    ):
        item = self._memory.get_historical_decision(
            tenant_id=tenant_id,
            current_decision_id=decision_id,
            historical_decision_id=historical_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if item is None:
            raise DecisionNotFoundError("Historical Decision not found")
        return item

    def _historical_or_none(
        self, tenant_id, decision_id, historical_id, clearance_rank, role_ids
    ):
        return self._memory.get_historical_decision(
            tenant_id=tenant_id,
            current_decision_id=decision_id,
            historical_decision_id=historical_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )

    @staticmethod
    def _validate_lesson_classification(status, classification):
        rejection_values = {
            "appropriate_rejection",
            "neutral",
            "potentially_costly_rejection",
            "inconclusive",
        }
        if status == "rejected" and classification not in rejection_values:
            raise LearningStateError("Invalid classification for a rejected lesson")
        if status == "adopted" and classification in {
            "appropriate_rejection",
            "potentially_costly_rejection",
        }:
            raise LearningStateError("Invalid classification for an adopted lesson")

    def _visible(self, tenant_id, decision_id, clearance_rank, role_ids):
        item = self._memory.get_decision(
            tenant_id=tenant_id,
            decision_id=decision_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )
        if item is None:
            raise DecisionNotFoundError("Decision not found")
        return item

    @staticmethod
    def _authorize_view(permissions):
        authorize_view(permissions)
        require_permission(permissions, "decision.learning.view")
        require_permission(permissions, "decision.outcome.view")

    @staticmethod
    def _authorize_evaluate(permissions):
        DecisionLearningService._authorize_view(permissions)
        require_permission(permissions, "decision.learning.evaluate")
