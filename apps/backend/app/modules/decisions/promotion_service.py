from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditEvent,
    DecisionLessonPromotionProposal,
    KnowledgeCard,
    KnowledgeCardLessonProvenance,
    uid,
)
from app.modules.decisions.policies import authorize_view, require_permission
from app.modules.decisions.promotion_schemas import (
    KnowledgeLessonProvenanceResponse,
    LessonPromotionEligibilityResponse,
    LessonPromotionResponse,
    LessonPromotionWorkspaceResponse,
)
from app.modules.decisions.service import DecisionConflictError, DecisionNotFoundError


ELIGIBLE_EVALUATIONS = frozenset(
    {
        "beneficial",
        "neutral",
        "ineffective",
        "harmful",
        "appropriate_rejection",
        "potentially_costly_rejection",
    }
)


class LessonPromotionStateError(ValueError):
    pass


class DecisionLessonPromotionService:
    def __init__(self, repository, memory):
        self._repository = repository
        self._memory = memory

    def workspace(
        self,
        *,
        tenant_id,
        decision_id,
        lesson_id,
        membership_id,
        clearance_rank,
        role_ids,
        permissions,
    ):
        self._authorize(permissions, "decision.lesson.promotion.view")
        source, lesson = self._source(
            tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
        )
        source_assessment = self._repository.completed_assessment(tenant_id, source.id)
        contexts = []
        for evaluation, adoption, assessment in (
            self._repository.eligible_contexts(tenant_id, lesson.id)
            if source_assessment is not None
            else []
        ):
            evaluation_decision = self._visible(
                tenant_id, evaluation.decision_case_id, clearance_rank, role_ids
            )
            if (
                evaluation_decision
                and evaluation.classification in ELIGIBLE_EVALUATIONS
            ):
                contexts.append(
                    {
                        "evaluation_id": evaluation.id,
                        "evaluation_decision_id": evaluation.decision_case_id,
                        "classification": evaluation.classification,
                        "rationale": evaluation.rationale,
                        "effectiveness_classification": assessment.classification,
                        "evaluated_at": evaluation.evaluated_at,
                    }
                )
        reasons = []
        if source_assessment is None:
            reasons.append("The source Decision requires completed effectiveness")
        if not contexts:
            reasons.append(
                "A completed, conclusive governed lesson evaluation is required"
            )
        proposals = []
        for item in self._repository.proposals(tenant_id, lesson.id):
            try:
                self._revalidate_proposal(item, tenant_id, clearance_rank, role_ids)
            except DecisionNotFoundError:
                continue
            proposals.append(LessonPromotionResponse.model_validate(item))
        return LessonPromotionWorkspaceResponse(
            eligibility=LessonPromotionEligibilityResponse(
                lesson_id=lesson.id,
                eligible=bool(contexts),
                reasons=reasons,
                evaluations=contexts,
            ),
            proposals=proposals,
        )

    def propose(
        self,
        *,
        tenant_id,
        decision_id,
        lesson_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        command,
    ):
        self._authorize(permissions, "decision.lesson.promote")
        source, lesson = self._source(
            tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
        )
        source_assessment = self._repository.completed_assessment(tenant_id, source.id)
        if source_assessment is None:
            raise LessonPromotionStateError(
                "The source Decision requires completed effectiveness"
            )
        context = self._repository.evaluation_context(
            tenant_id, lesson.id, command.lesson_evaluation_id
        )
        if context is None:
            raise DecisionNotFoundError("Eligible lesson evaluation not found")
        evaluation, adoption, assessment = context
        if evaluation.classification not in ELIGIBLE_EVALUATIONS:
            raise LessonPromotionStateError(
                "The lesson evaluation is not eligible for promotion"
            )
        evaluation_decision = self._visible(
            tenant_id, evaluation.decision_case_id, clearance_rank, role_ids
        )
        if evaluation_decision is None:
            raise DecisionNotFoundError("Eligible lesson evaluation not found")
        inherited_policy = self._inherited_policy(
            source.access_policy_id, evaluation_decision.access_policy_id
        )
        outcomes = self._repository.outcomes(
            tenant_id, evaluation.decision_case_id, evaluation.relevant_outcome_ids
        )
        if len(outcomes) != len(set(evaluation.relevant_outcome_ids)):
            raise DecisionNotFoundError("Relevant outcome not found")
        proposal = DecisionLessonPromotionProposal(
            id=uid(),
            tenant_id=tenant_id,
            source_decision_id=source.id,
            source_lesson_id=lesson.id,
            evaluation_decision_id=evaluation.decision_case_id,
            lesson_adoption_id=adoption.id,
            lesson_evaluation_id=evaluation.id,
            effectiveness_assessment_id=assessment.id,
            status="proposed",
            rationale=command.rationale,
            applicability=command.applicability,
            limitations=command.limitations,
            proposed_title=command.title,
            proposed_summary=command.summary,
            proposed_body=command.body,
            snapshot_source_decision={
                "id": source.id,
                "title": source.title,
                "status": source.status,
                "workspace_id": source.workspace_id,
                "business_concept_id": source.business_concept_id,
            },
            snapshot_lesson={
                "id": lesson.id,
                "type": lesson.lesson_type,
                "description": lesson.description,
                "business_impact": lesson.business_impact,
            },
            snapshot_adoption={
                "id": adoption.id,
                "status": adoption.status,
                "rationale": adoption.rationale,
                "application_note": adoption.application_note,
            },
            snapshot_evaluation={
                "id": evaluation.id,
                "classification": evaluation.classification,
                "rationale": evaluation.rationale,
                "was_applied": evaluation.was_applied,
                "relevant_outcome_ids": list(evaluation.relevant_outcome_ids),
                "outcome_relevance_details": evaluation.outcome_relevance_details,
                "evaluated_at": evaluation.evaluated_at.isoformat(),
            },
            snapshot_effectiveness={
                "source": self._assessment_snapshot(source_assessment),
                "evaluation": self._assessment_snapshot(assessment),
            },
            snapshot_relevant_outcomes=[
                self._outcome_snapshot(item) for item in outcomes
            ],
            snapshot_provenance={
                "kind": "decision_lesson_evaluation",
                "observed_usefulness_caveat": "Observed usefulness supports reuse consideration but does not prove universal applicability.",
            },
            source_classification_rank=source.classification_rank,
            evaluation_classification_rank=evaluation_decision.classification_rank,
            inherited_classification_rank=max(
                source.classification_rank, evaluation_decision.classification_rank
            ),
            source_access_policy_id=source.access_policy_id,
            evaluation_access_policy_id=evaluation_decision.access_policy_id,
            inherited_access_policy_id=inherited_policy,
            proposed_by_membership_id=membership_id,
        )
        event = self._event(
            proposal,
            actor_id,
            membership_id,
            "decision.lesson.promotion.proposed",
            command.rationale,
        )
        try:
            return LessonPromotionResponse.model_validate(
                self._repository.save([proposal], [event], proposal)
            )
        except IntegrityError as exc:
            raise DecisionConflictError(
                "An active promotion proposal already exists"
            ) from exc

    def review(
        self,
        *,
        action,
        tenant_id,
        decision_id,
        lesson_id,
        proposal_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        rationale,
    ):
        self._authorize(permissions, "decision.lesson.promotion.review")
        self._source(
            tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
        )
        proposal = self._proposal(tenant_id, decision_id, lesson_id, proposal_id)
        self._revalidate_proposal(proposal, tenant_id, clearance_rank, role_ids)
        if proposal.status != "proposed" or action not in {"approved", "rejected"}:
            raise LessonPromotionStateError(
                "Only a proposed lesson promotion can be reviewed"
            )
        proposal.status = action
        proposal.reviewed_by_membership_id = membership_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.review_rationale = rationale.strip()
        event = self._event(
            proposal,
            actor_id,
            membership_id,
            f"decision.lesson.promotion.{action}",
            rationale,
        )
        return LessonPromotionResponse.model_validate(
            self._repository.save([proposal], [event], proposal)
        )

    def withdraw(
        self,
        *,
        tenant_id,
        decision_id,
        lesson_id,
        proposal_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
        rationale,
    ):
        self._authorize(permissions, "decision.lesson.promote")
        self._source(
            tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
        )
        proposal = self._proposal(tenant_id, decision_id, lesson_id, proposal_id)
        if proposal.status not in {"proposed", "approved"}:
            raise LessonPromotionStateError(
                "Only an active promotion proposal can be withdrawn"
            )
        proposal.status = "withdrawn"
        proposal.withdrawn_by_membership_id = membership_id
        proposal.withdrawn_at = datetime.now(timezone.utc)
        proposal.withdrawal_rationale = rationale.strip()
        event = self._event(
            proposal,
            actor_id,
            membership_id,
            "decision.lesson.promotion.withdrawn",
            rationale,
        )
        return LessonPromotionResponse.model_validate(
            self._repository.save([proposal], [event], proposal)
        )

    def promote(
        self,
        *,
        tenant_id,
        decision_id,
        lesson_id,
        proposal_id,
        membership_id,
        actor_id,
        clearance_rank,
        role_ids,
        permissions,
    ):
        self._authorize(permissions, "decision.lesson.promote")
        source, _ = self._source(
            tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
        )
        proposal = self._proposal(tenant_id, decision_id, lesson_id, proposal_id)
        source_current, evaluation_current = self._revalidate_proposal(
            proposal, tenant_id, clearance_rank, role_ids
        )
        if proposal.status != "approved":
            raise LessonPromotionStateError(
                "Only an approved lesson promotion can be promoted"
            )
        inherited_policy = self._inherited_policy(
            source_current.access_policy_id, evaluation_current.access_policy_id
        )
        if inherited_policy != proposal.inherited_access_policy_id:
            raise LessonPromotionStateError(
                "Promotion access controls no longer match the approved proposal"
            )
        inherited_rank = max(
            proposal.inherited_classification_rank,
            source_current.classification_rank,
            evaluation_current.classification_rank,
        )
        card = KnowledgeCard(
            id=uid(),
            tenant_id=tenant_id,
            workspace_id=source.workspace_id,
            business_concept_id=source.business_concept_id,
            title=proposal.proposed_title,
            summary=proposal.proposed_summary,
            body=f"{proposal.proposed_body}\n\nApplicability\n{proposal.applicability}\n\nLimitations\n{proposal.limitations}\n\nObserved usefulness supports reuse consideration but does not prove universal applicability.",
            knowledge_type="decision_lesson",
            lifecycle_status="draft",
            approval_status="not_submitted",
            authority_level="organizational_knowledge",
            classification_rank=inherited_rank,
            access_policy_id=proposal.inherited_access_policy_id,
            ai_usage_allowed=False,
            trust_score=0.5,
            owner_id=actor_id,
        )
        provenance = KnowledgeCardLessonProvenance(
            tenant_id=tenant_id,
            knowledge_card_id=card.id,
            promotion_proposal_id=proposal.id,
            source_decision_id=proposal.source_decision_id,
            source_lesson_id=proposal.source_lesson_id,
            lesson_evaluation_id=proposal.lesson_evaluation_id,
            immutable_snapshot={
                "source_decision": proposal.snapshot_source_decision,
                "lesson": proposal.snapshot_lesson,
                "adoption": proposal.snapshot_adoption,
                "evaluation": proposal.snapshot_evaluation,
                "effectiveness": proposal.snapshot_effectiveness,
                "relevant_outcomes": proposal.snapshot_relevant_outcomes,
                "applicability": proposal.applicability,
                "limitations": proposal.limitations,
                "provenance": proposal.snapshot_provenance,
                "classification_rank": inherited_rank,
                "access_policy_id": proposal.inherited_access_policy_id,
            },
        )
        proposal.status = "promoted"
        proposal.promoted_by_membership_id = membership_id
        proposal.promoted_at = datetime.now(timezone.utc)
        proposal.resulting_knowledge_card_id = card.id
        events = [
            self._event(
                proposal,
                actor_id,
                membership_id,
                "decision.lesson.promotion.promoted",
                "Approved lesson promoted to governed draft Knowledge Card",
            ),
            AuditEvent(
                tenant_id=tenant_id,
                actor_id=actor_id,
                event_type="KnowledgeDraftCreatedFromDecisionLesson",
                entity_type="knowledge_card",
                entity_id=card.id,
                description="Governed draft Knowledge Card created from approved Decision learning",
                details={
                    "promotion_proposal_id": proposal.id,
                    "source_decision_id": proposal.source_decision_id,
                    "source_lesson_id": proposal.source_lesson_id,
                    "lesson_evaluation_id": proposal.lesson_evaluation_id,
                    "classification_rank": inherited_rank,
                    "access_policy_id": proposal.inherited_access_policy_id,
                    "actor_membership_id": membership_id,
                },
            ),
        ]
        return LessonPromotionResponse.model_validate(
            self._repository.save([proposal, card, provenance], events, proposal)
        )

    def provenance(
        self,
        *,
        tenant_id,
        card_id,
        membership_id,
        clearance_rank,
        role_ids,
        permissions,
    ):
        self._authorize(permissions, "decision.lesson.promotion.view")
        if self._repository.active_membership(tenant_id, membership_id) is None:
            raise DecisionNotFoundError("Knowledge Card not found")
        item = self._repository.provenance(tenant_id, card_id, clearance_rank, role_ids)
        if item is None:
            raise DecisionNotFoundError("Knowledge Card provenance not found")
        if (
            self._visible(tenant_id, item.source_decision_id, clearance_rank, role_ids)
            is None
        ):
            raise DecisionNotFoundError("Knowledge Card provenance not found")
        return KnowledgeLessonProvenanceResponse.model_validate(item)

    def _source(
        self, tenant_id, decision_id, lesson_id, membership_id, clearance_rank, role_ids
    ):
        if self._repository.active_membership(tenant_id, membership_id) is None:
            raise DecisionNotFoundError("Decision lesson not found")
        source = self._visible(tenant_id, decision_id, clearance_rank, role_ids)
        lesson = self._repository.lesson(tenant_id, decision_id, lesson_id)
        if source is None or lesson is None:
            raise DecisionNotFoundError("Decision lesson not found")
        return source, lesson

    def _visible(self, tenant_id, decision_id, clearance_rank, role_ids):
        return self._memory.get_decision(
            tenant_id=tenant_id,
            decision_id=decision_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
        )

    def _proposal(self, tenant_id, decision_id, lesson_id, proposal_id):
        item = self._repository.proposal(
            tenant_id, decision_id, lesson_id, proposal_id, True
        )
        if item is None:
            raise DecisionNotFoundError("Lesson promotion proposal not found")
        return item

    def _revalidate_proposal(self, proposal, tenant_id, clearance_rank, role_ids):
        source = self._visible(
            tenant_id, proposal.source_decision_id, clearance_rank, role_ids
        )
        evaluation = self._visible(
            tenant_id, proposal.evaluation_decision_id, clearance_rank, role_ids
        )
        if source is None or evaluation is None:
            raise DecisionNotFoundError("Lesson promotion proposal not found")
        return source, evaluation

    @staticmethod
    def _inherited_policy(source_policy, evaluation_policy):
        policies = {value for value in (source_policy, evaluation_policy) if value}
        if len(policies) > 1:
            raise LessonPromotionStateError(
                "Source materials use incompatible restrictive access policies"
            )
        return next(iter(policies), None)

    @staticmethod
    def _outcome_snapshot(item):
        values = {}
        for column in item.__table__.columns:
            if column.name == "tenant_id":
                continue
            value = getattr(item, column.name)
            values[column.name] = (
                value.isoformat() if hasattr(value, "isoformat") else value
            )
        return values

    @staticmethod
    def _assessment_snapshot(item):
        return {
            "id": item.id,
            "classification": item.classification,
            "rationale": item.rationale,
            "completed_at": item.completed_at.isoformat()
            if item.completed_at
            else None,
        }

    @staticmethod
    def _authorize(permissions, required):
        authorize_view(permissions)
        require_permission(permissions, required)

    @staticmethod
    def _event(proposal, actor_id, membership_id, event_type, rationale):
        return AuditEvent(
            tenant_id=proposal.tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            entity_type="decision_lesson_promotion",
            entity_id=proposal.id,
            description=event_type.replace(".", " ").title(),
            details={
                "source_decision_id": proposal.source_decision_id,
                "source_lesson_id": proposal.source_lesson_id,
                "lesson_evaluation_id": proposal.lesson_evaluation_id,
                "status": proposal.status,
                "rationale": rationale,
                "actor_membership_id": membership_id,
            },
        )
