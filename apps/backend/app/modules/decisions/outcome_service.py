from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.models import (
    AuditEvent,
    DecisionEffectivenessAssessment,
    DecisionExpectedOutcome,
    DecisionLesson,
    DecisionOutcomeObservation,
)
from app.modules.decisions.outcome_repository import DecisionOutcomeRepository
from app.modules.decisions.outcomes import (
    OutcomeCalculationInput,
    aggregate_outcomes,
    calculate_outcome,
)
from app.modules.decisions.policies import authorize_outcome, authorize_view
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.schemas import (
    AssessmentCreate,
    AssessmentResponse,
    EffectivenessWorkspaceResponse,
    ExpectedOutcomeCreate,
    ExpectedOutcomeResponse,
    ExpectedOutcomeUpdate,
    LessonCreate,
    LessonResponse,
    ObservationCreate,
    ObservationResponse,
    ObservationSupersede,
)
from app.modules.decisions.service import DecisionNotFoundError


class OutcomeStateError(ValueError):
    pass


APPROVED_STATES = {"conditionally_approved", "approved", "closed"}


class DecisionOutcomeService:
    def __init__(
        self, repository: DecisionOutcomeRepository, decisions: DecisionRepository
    ) -> None:
        self._repository = repository
        self._decisions = decisions

    def workspace(
        self, *, tenant_id: str, decision_id: str, permissions: set[str]
    ) -> EffectivenessWorkspaceResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "view")
        decision = self._decision(tenant_id, decision_id)
        outcomes = self._repository.list_outcomes(
            tenant_id=tenant_id, decision_id=decision_id
        )
        observations = self._repository.list_observations(
            tenant_id=tenant_id, decision_id=decision_id
        )
        calculations, aggregate = self._calculations(outcomes, observations)
        return EffectivenessWorkspaceResponse(
            outcomes=[
                ExpectedOutcomeResponse.model_validate(item) for item in outcomes
            ],
            observations=[
                ObservationResponse.model_validate(item) for item in observations
            ],
            calculations=calculations,
            aggregate=aggregate,
            assessments=[
                AssessmentResponse.model_validate(item)
                for item in self._repository.list_assessments(
                    tenant_id=tenant_id, decision_id=decision_id
                )
            ],
            lessons=[
                LessonResponse.model_validate(item)
                for item in self._repository.list_lessons(
                    tenant_id=tenant_id, decision_id=decision_id
                )
            ],
            conditions=self._decisions.list_conditions(
                tenant_id=tenant_id, decision_id=decision_id
            ),
            capabilities={
                action: f"decision.outcome.{action}" in permissions
                for action in ("view", "define", "record", "verify", "assess")
            }
            | {
                "lesson": "decision.lesson.record" in permissions,
                "eligible": decision.status in APPROVED_STATES,
            },
        )

    def create_outcome(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        membership_id: str,
        permissions: set[str],
        command: ExpectedOutcomeCreate,
    ) -> ExpectedOutcomeResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "define")
        decision = self._decision(tenant_id, decision_id)
        if decision.status in {"rejected", "closed"}:
            raise OutcomeStateError(
                "Expected outcomes cannot be defined for this Decision state"
            )
        self._validate_outcome(tenant_id, command)
        now = datetime.now(timezone.utc)
        item = DecisionExpectedOutcome(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            created_by_membership_id=membership_id,
            frozen_at=now if decision.status in APPROVED_STATES else None,
            **command.model_dump(),
        )
        self._save(
            decision_id,
            membership_id,
            [item],
            "decision.expected_outcome.created",
            "Expected outcome created",
            {"outcome_id": item.id, "title": item.title},
            [item],
        )
        return ExpectedOutcomeResponse.model_validate(item)

    def update_outcome(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        membership_id: str,
        permissions: set[str],
        command: ExpectedOutcomeUpdate,
    ) -> ExpectedOutcomeResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "define")
        decision = self._decision(tenant_id, decision_id)
        current = self._repository.get_outcome(
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            for_update=True,
        )
        if current is None or current.status != "active":
            raise DecisionNotFoundError("Expected outcome not found")
        self._validate_outcome(tenant_id, command)
        values = command.model_dump(exclude={"amendment_rationale"})
        if decision.status not in APPROVED_STATES:
            before = {key: getattr(current, key) for key in values}
            for key, value in values.items():
                setattr(current, key, value)
            self._save(
                decision_id,
                membership_id,
                [current],
                "decision.expected_outcome.updated",
                "Expected outcome updated before approval",
                {"outcome_id": current.id, "before": _safe(before)},
                [current],
            )
            return ExpectedOutcomeResponse.model_validate(current)
        if not command.amendment_rationale:
            raise OutcomeStateError(
                "Post-approval changes require an amendment rationale"
            )
        current.status = "superseded"
        amended = DecisionExpectedOutcome(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            created_by_membership_id=membership_id,
            revision=current.revision + 1,
            amended_from_id=current.id,
            amendment_rationale=command.amendment_rationale,
            frozen_at=datetime.now(timezone.utc),
            **values,
        )
        self._save(
            decision_id,
            membership_id,
            [current, amended],
            "decision.expected_outcome.amended",
            "Approved expectation amended with retained history",
            {
                "outcome_id": amended.id,
                "amended_from_id": current.id,
                "rationale": command.amendment_rationale,
            },
            [amended],
        )
        return ExpectedOutcomeResponse.model_validate(amended)

    def record_observation(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        membership_id: str,
        permissions: set[str],
        command: ObservationCreate,
    ) -> ObservationResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "record")
        decision = self._decision(tenant_id, decision_id)
        if decision.status not in APPROVED_STATES:
            raise OutcomeStateError(
                "Observations require an authoritatively approved Decision"
            )
        outcome = self._outcome(tenant_id, decision_id, outcome_id)
        self._validate_observation(
            tenant_id, decision_id, outcome.measurement_type, command
        )
        item = DecisionOutcomeObservation(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            expected_outcome_id=outcome_id,
            recorded_by_membership_id=membership_id,
            **command.model_dump(),
        )
        self._save(
            decision_id,
            membership_id,
            [item],
            "decision.outcome_observation.recorded",
            "Outcome observation recorded",
            {
                "outcome_id": outcome_id,
                "observation_id": item.id,
                "provenance": item.provenance,
            },
            [item],
        )
        return ObservationResponse.model_validate(item)

    def verify_observation(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        observation_id: str,
        membership_id: str,
        permissions: set[str],
        rationale: str,
    ) -> ObservationResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "verify")
        self._decision(tenant_id, decision_id)
        item = self._observation(
            tenant_id, decision_id, outcome_id, observation_id, True
        )
        if item.recorded_by_membership_id == membership_id:
            raise OutcomeStateError(
                "An observation recorder cannot independently verify the same observation"
            )
        if item.verification_status != "unverified":
            raise OutcomeStateError("Only an unverified observation can be verified")
        item.verification_status = "verified"
        item.verified_by_membership_id = membership_id
        item.verified_at = datetime.now(timezone.utc)
        item.verification_rationale = rationale.strip()
        self._save(
            decision_id,
            membership_id,
            [item],
            "decision.outcome_observation.verified",
            "Outcome observation independently verified",
            {
                "outcome_id": outcome_id,
                "observation_id": item.id,
                "rationale": rationale,
            },
            [item],
        )
        return ObservationResponse.model_validate(item)

    def supersede_observation(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        observation_id: str,
        membership_id: str,
        permissions: set[str],
        command: ObservationSupersede,
    ) -> ObservationResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "record")
        self._decision(tenant_id, decision_id)
        outcome = self._outcome(tenant_id, decision_id, outcome_id)
        old = self._observation(
            tenant_id, decision_id, outcome_id, observation_id, True
        )
        if old.verification_status == "superseded":
            raise OutcomeStateError("Observation is already superseded")
        self._validate_observation(
            tenant_id, decision_id, outcome.measurement_type, command
        )
        replacement = DecisionOutcomeObservation(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            expected_outcome_id=outcome_id,
            recorded_by_membership_id=membership_id,
            **command.model_dump(exclude={"rationale"}),
        )
        old.verification_status = "superseded"
        old.superseded_by_id = replacement.id
        old.supersession_rationale = command.rationale
        self._save(
            decision_id,
            membership_id,
            [replacement, old],
            "decision.outcome_observation.superseded",
            "Outcome observation superseded with retained history",
            {
                "outcome_id": outcome_id,
                "observation_id": old.id,
                "replacement_id": replacement.id,
                "rationale": command.rationale,
            },
            [replacement],
        )
        return ObservationResponse.model_validate(replacement)

    def create_assessment(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        membership_id: str,
        permissions: set[str],
        command: AssessmentCreate,
    ) -> AssessmentResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "assess")
        decision = self._decision(tenant_id, decision_id)
        if decision.status not in APPROVED_STATES:
            raise OutcomeStateError(
                "Effectiveness assessment requires an authoritatively approved Decision"
            )
        if (
            command.evaluation_start
            and command.evaluation_end
            and command.evaluation_start > command.evaluation_end
        ):
            raise OutcomeStateError("Evaluation start must not follow evaluation end")
        item = DecisionEffectivenessAssessment(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            assessor_membership_id=membership_id,
            revision=self._repository.next_assessment_revision(
                tenant_id=tenant_id, decision_id=decision_id
            ),
            **command.model_dump(),
        )
        self._save(
            decision_id,
            membership_id,
            [item],
            "decision.effectiveness_assessment.created",
            "Effectiveness assessment created",
            {"assessment_id": item.id, "classification": item.classification},
            [item],
        )
        return AssessmentResponse.model_validate(item)

    def complete_assessment(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        assessment_id: str,
        membership_id: str,
        permissions: set[str],
    ) -> AssessmentResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "assess")
        self._decision(tenant_id, decision_id)
        item = self._repository.get_assessment(
            tenant_id=tenant_id,
            decision_id=decision_id,
            assessment_id=assessment_id,
            for_update=True,
        )
        if item is None:
            raise DecisionNotFoundError("Effectiveness assessment not found")
        if item.status != "draft":
            raise OutcomeStateError("Only a draft assessment can be completed")
        outcomes = self._repository.list_outcomes(
            tenant_id=tenant_id, decision_id=decision_id
        )
        observations = self._repository.list_observations(
            tenant_id=tenant_id, decision_id=decision_id
        )
        calculations, aggregate = self._calculations(outcomes, observations)
        open_conditions = [
            c
            for c in self._decisions.list_conditions(
                tenant_id=tenant_id, decision_id=decision_id
            )
            if c.status == "open"
        ]
        if item.classification in {"exceeded", "met"} and (
            aggregate["classification"] not in {"met"} or open_conditions
        ):
            raise OutcomeStateError(
                "A successful assessment requires all assessable targets met, complete data, and no open approval conditions"
            )
        item.status = "completed"
        item.completed_at = datetime.now(timezone.utc)
        item.calculation_details = {
            "outcomes": calculations,
            "aggregate": aggregate,
            "open_condition_ids": [c.id for c in open_conditions],
        }
        self._save(
            decision_id,
            membership_id,
            [item],
            "decision.effectiveness_assessment.completed",
            "Effectiveness assessment completed",
            {
                "assessment_id": item.id,
                "classification": item.classification,
                "aggregate": aggregate,
                "open_condition_ids": [c.id for c in open_conditions],
            },
            [item],
        )
        return AssessmentResponse.model_validate(item)

    def record_lesson(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        membership_id: str,
        permissions: set[str],
        command: LessonCreate,
    ) -> LessonResponse:
        authorize_view(permissions)
        authorize_outcome(permissions, "lesson")
        decision = self._decision(tenant_id, decision_id)
        if decision.status not in APPROVED_STATES:
            raise OutcomeStateError(
                "Lessons require an authoritatively approved Decision"
            )
        refs = command.model_dump()
        if (
            refs["related_outcome_id"]
            and self._repository.get_outcome(
                tenant_id=tenant_id,
                decision_id=decision_id,
                outcome_id=refs["related_outcome_id"],
            )
            is None
        ):
            raise DecisionNotFoundError("Related record not found")
        if (
            refs["related_evidence_id"]
            and self._decisions.get_evidence(
                tenant_id=tenant_id,
                decision_id=decision_id,
                evidence_id=refs["related_evidence_id"],
            )
            is None
        ):
            raise DecisionNotFoundError("Related record not found")
        lesson = DecisionLesson(
            tenant_id=tenant_id,
            decision_case_id=decision_id,
            created_by_membership_id=membership_id,
            **refs,
        )
        self._save(
            decision_id,
            membership_id,
            [lesson],
            "decision.lesson.recorded",
            "Decision lesson recorded",
            {"lesson_id": lesson.id, "lesson_type": lesson.lesson_type},
            [lesson],
        )
        return LessonResponse.model_validate(lesson)

    def _decision(self, tenant_id: str, decision_id: str):
        decision = self._decisions.get_decision(
            tenant_id=tenant_id, decision_id=decision_id
        )
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision

    def _outcome(self, tenant_id: str, decision_id: str, outcome_id: str):
        item = self._repository.get_outcome(
            tenant_id=tenant_id, decision_id=decision_id, outcome_id=outcome_id
        )
        if item is None or item.status != "active":
            raise DecisionNotFoundError("Expected outcome not found")
        return item

    def _observation(
        self,
        tenant_id: str,
        decision_id: str,
        outcome_id: str,
        observation_id: str,
        for_update: bool = False,
    ):
        item = self._repository.get_observation(
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            observation_id=observation_id,
            for_update=for_update,
        )
        if item is None:
            raise DecisionNotFoundError("Outcome observation not found")
        return item

    def _validate_outcome(
        self, tenant_id: str, command: ExpectedOutcomeCreate | ExpectedOutcomeUpdate
    ) -> None:
        if (
            command.responsible_membership_id
            and self._repository.get_active_membership(
                tenant_id=tenant_id, membership_id=command.responsible_membership_id
            )
            is None
        ):
            raise DecisionNotFoundError("Responsible member not found")
        if command.target_direction == "range" and (
            command.target_min_value is None
            or command.target_max_value is None
            or command.target_min_value > command.target_max_value
        ):
            raise OutcomeStateError(
                "Range outcomes require a valid minimum and maximum"
            )
        if command.measurement_type == "boolean" and command.target_boolean is None:
            raise OutcomeStateError("Boolean outcomes require a target condition")
        if (
            command.measurement_type not in {"boolean", "milestone", "qualitative"}
            and command.target_direction != "range"
            and command.target_value is None
        ):
            raise OutcomeStateError("Measurable outcomes require a target value")

    def _validate_observation(
        self,
        tenant_id: str,
        decision_id: str,
        measurement_type: str,
        command: ObservationCreate | ObservationSupersede,
    ) -> None:
        if (
            measurement_type in {"numeric", "percentage", "currency", "duration"}
            and command.numeric_value is None
        ):
            raise OutcomeStateError("This outcome requires a numeric observation")
        if measurement_type == "boolean" and command.boolean_value is None:
            raise OutcomeStateError("This outcome requires a boolean observation")
        if measurement_type == "qualitative" and not command.narrative.strip():
            raise OutcomeStateError("Qualitative observations require a narrative")
        if (
            command.decision_evidence_id
            and self._decisions.get_evidence(
                tenant_id=tenant_id,
                decision_id=decision_id,
                evidence_id=command.decision_evidence_id,
            )
            is None
        ):
            raise DecisionNotFoundError("Supporting Decision evidence not found")

    def _calculations(self, outcomes, observations):
        calculations: dict[str, dict] = {}
        aggregate_items = []
        for outcome in outcomes:
            verified = [
                o
                for o in observations
                if o.expected_outcome_id == outcome.id
                and o.verification_status == "verified"
            ]
            latest = (
                max(verified, key=lambda o: (o.observation_date, o.recorded_at))
                if verified
                else None
            )
            calc = calculate_outcome(
                OutcomeCalculationInput(
                    measurement_type=outcome.measurement_type,
                    target_direction=outcome.target_direction,
                    baseline=_decimal(outcome.baseline_value),
                    target=_decimal(outcome.target_value),
                    target_min=_decimal(outcome.target_min_value),
                    target_max=_decimal(outcome.target_max_value),
                    target_boolean=outcome.target_boolean,
                    actual=_decimal(latest.numeric_value) if latest else None,
                    actual_boolean=latest.boolean_value if latest else None,
                    observed_status=latest.observed_status if latest else None,
                    verified=latest is not None,
                    target_date=outcome.target_date,
                    evaluation_date=datetime.now(timezone.utc).date(),
                )
            )
            calc["observation_id"] = latest.id if latest else None
            calculations[outcome.id] = calc
            aggregate_items.append(
                {
                    "weight": float(outcome.weight),
                    "critical": outcome.is_critical,
                    "calculation": calc,
                }
            )
        return calculations, aggregate_outcomes(aggregate_items)

    def _save(
        self,
        decision_id: str,
        membership_id: str,
        objects: list,
        event_type: str,
        description: str,
        details: dict,
        refresh: list,
    ) -> None:
        # Audit actor_id remains the platform user field in the existing event model;
        # membership identity is retained explicitly in accountable details.
        self._repository.save(
            objects=objects,
            events=[
                AuditEvent(
                    tenant_id=objects[0].tenant_id,
                    actor_id=None,
                    event_type=event_type,
                    entity_type="decision_case",
                    entity_id=decision_id,
                    description=description,
                    details=details | {"actor_membership_id": membership_id},
                )
            ],
            refresh=refresh,
        )


def _decimal(value) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _safe(values: dict) -> dict:
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in values.items()
    }
