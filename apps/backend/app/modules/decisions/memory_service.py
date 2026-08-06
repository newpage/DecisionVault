from __future__ import annotations

from datetime import date

from app.modules.decisions.memory import ALGORITHM_VERSION, RELEVANCE_THRESHOLDS, compare_profiles
from app.modules.decisions.memory_repository import DecisionMemoryRepository
from app.modules.decisions.memory_schemas import DecisionComparisonResponse, HistoricalDecisionSummary, PrecedentListResponse, PrecedentResultResponse
from app.modules.decisions.policies import EVIDENCE_VIEW_PERMISSION, OUTCOME_VIEW_PERMISSION, REVIEW_VIEW_PERMISSION, authorize_memory_view, authorize_view, require_permission
from app.modules.decisions.service import DecisionNotFoundError


class DecisionMemoryService:
    def __init__(self, repository: DecisionMemoryRepository) -> None:
        self._repository = repository

    def list_precedents(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
        minimum_relevance: str = "weakly_relevant",
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
        outcome_classification: str | None = None,
        business_concept_id: str | None = None,
    ) -> PrecedentListResponse:
        authorize_view(permissions)
        authorize_memory_view(permissions)
        if outcome_classification:
            require_permission(permissions, OUTCOME_VIEW_PERMISSION)
        current = self._require_decision(tenant_id, decision_id, clearance_rank, role_ids)
        candidates = self._repository.list_candidates(
            tenant_id=tenant_id,
            current_decision_id=decision_id,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
            date_from=date_from,
            date_to=date_to,
            business_concept_id=business_concept_id,
        )
        current_profile = self._profile(current, clearance_rank, role_ids, permissions)
        results = []
        for historical in candidates:
            historical_profile = self._profile(historical, clearance_rank, role_ids, permissions)
            if outcome_classification and historical_profile.effectiveness_classification != outcome_classification:
                continue
            comparison = compare_profiles(current_profile, historical_profile)
            if comparison["overall_similarity"] < RELEVANCE_THRESHOLDS[minimum_relevance]:
                continue
            results.append(self._result(tenant_id, historical, comparison, clearance_rank, role_ids, permissions))
        results.sort(key=lambda item: (-item.overall_similarity, -item.historical_decision.created_at.timestamp(), item.historical_decision.id))
        returned = results[:limit]
        return PrecedentListResponse(current_decision_id=current.id, algorithm_version=ALGORITHM_VERSION, items=returned, considered_count=len(candidates), returned_count=len(returned))

    def compare(
        self,
        *,
        tenant_id: str,
        decision_id: str,
        historical_decision_id: str,
        clearance_rank: int,
        role_ids: set[str],
        permissions: set[str],
    ) -> DecisionComparisonResponse:
        authorize_view(permissions)
        authorize_memory_view(permissions)
        current = self._require_decision(tenant_id, decision_id, clearance_rank, role_ids)
        historical = self._repository.get_historical_decision(tenant_id=tenant_id, current_decision_id=decision_id, historical_decision_id=historical_decision_id, clearance_rank=clearance_rank, role_ids=role_ids)
        if historical is None:
            raise DecisionNotFoundError("Historical Decision not found")
        comparison = compare_profiles(self._profile(current, clearance_rank, role_ids, permissions), self._profile(historical, clearance_rank, role_ids, permissions))
        summary = self._summary(tenant_id, historical, clearance_rank, role_ids, permissions)
        governance = None
        if REVIEW_VIEW_PERMISSION in permissions:
            governance = {
                "review_types": sorted({item.review_type for item in self._repository.reviews(tenant_id=tenant_id, decision_id=historical.id)}),
                "approval_actions": [item.action for item in self._repository.approvals(tenant_id=tenant_id, decision_id=historical.id)],
                "conditions": [{"status": item.status, "text": item.condition_text} for item in self._repository.conditions(tenant_id=tenant_id, decision_id=historical.id)],
                "material_findings": [{"type": item.finding_type, "severity": item.severity, "title": item.title} for item in self._repository.findings(tenant_id=tenant_id, decision_id=historical.id) if item.severity in {"high", "critical"}],
            }
        outcome = None
        lessons = None
        if OUTCOME_VIEW_PERMISSION in permissions:
            assessment = self._repository.latest_assessment(tenant_id=tenant_id, decision_id=historical.id)
            outcome = {
                "effectiveness_classification": assessment.classification if assessment else None,
                "outcomes": [{"title": item.title, "category": item.category, "measurement_type": item.measurement_type, "target_direction": item.target_direction} for item in self._repository.outcomes(tenant_id=tenant_id, decision_id=historical.id)],
            }
            lessons = [{"type": item.lesson_type, "description": item.description, "business_impact": item.business_impact} for item in self._repository.lessons(tenant_id=tenant_id, decision_id=historical.id)]
        return DecisionComparisonResponse(
            current_decision={"id": current.id, "title": current.title, "status": current.status, "business_concept_id": current.business_concept_id},
            historical_decision=summary,
            overall_similarity=comparison["overall_similarity"],
            relevance=comparison["relevance"],
            algorithm_version=comparison["algorithm_version"],
            similarity_components=comparison["components"],
            shared_characteristics=comparison["shared_characteristics"],
            different_characteristics=comparison["different_characteristics"],
            historical_governance=governance,
            historical_outcome=outcome,
            historical_lessons=lessons,
        )

    def _profile(self, decision, clearance_rank, role_ids, permissions):
        return self._repository.profile(
            decision,
            clearance_rank=clearance_rank,
            role_ids=role_ids,
            include_evidence=EVIDENCE_VIEW_PERMISSION in permissions,
            include_governance=REVIEW_VIEW_PERMISSION in permissions,
            include_outcomes=OUTCOME_VIEW_PERMISSION in permissions,
        )

    def _result(self, tenant_id, historical, comparison, clearance_rank, role_ids, permissions):
        return PrecedentResultResponse(
            historical_decision=self._summary(tenant_id, historical, clearance_rank, role_ids, permissions),
            overall_similarity=comparison["overall_similarity"],
            relevance=comparison["relevance"],
            algorithm_version=comparison["algorithm_version"],
            similarity_components=comparison["components"],
            shared_characteristics=comparison["shared_characteristics"],
            different_characteristics=comparison["different_characteristics"],
        )

    def _summary(self, tenant_id, historical, clearance_rank, role_ids, permissions):
        evidence = self._repository.authorized_evidence(tenant_id=tenant_id, decision_id=historical.id, clearance_rank=clearance_rank, role_ids=role_ids) if EVIDENCE_VIEW_PERMISSION in permissions else None
        approvals = self._repository.approvals(tenant_id=tenant_id, decision_id=historical.id) if REVIEW_VIEW_PERMISSION in permissions else None
        conditions = self._repository.conditions(tenant_id=tenant_id, decision_id=historical.id) if REVIEW_VIEW_PERMISSION in permissions else None
        findings = self._repository.findings(tenant_id=tenant_id, decision_id=historical.id) if REVIEW_VIEW_PERMISSION in permissions else None
        assessment = self._repository.latest_assessment(tenant_id=tenant_id, decision_id=historical.id) if OUTCOME_VIEW_PERMISSION in permissions else None
        lessons = self._repository.lessons(tenant_id=tenant_id, decision_id=historical.id) if OUTCOME_VIEW_PERMISSION in permissions else None
        return HistoricalDecisionSummary(
            id=historical.id,
            title=historical.title,
            created_at=historical.created_at,
            business_concept_id=historical.business_concept_id,
            business_concept_name=self._repository.concept_name(tenant_id=tenant_id, concept_id=historical.business_concept_id),
            final_status=historical.status,
            approval_result=approvals[-1].action if approvals else None,
            effectiveness_classification=assessment.classification if assessment else None,
            evidence_count=len(evidence) if evidence is not None else None,
            evidence_types=sorted({item.snapshot_knowledge_type for item in evidence}) if evidence is not None else None,
            material_conditions=[item.condition_text for item in conditions if item.status == "open"] if conditions is not None else None,
            material_findings=[item.title for item in findings if item.severity in {"high", "critical"}] if findings is not None else None,
            lessons=[item.description for item in lessons] if lessons is not None else None,
        )

    def _require_decision(self, tenant_id, decision_id, clearance_rank, role_ids):
        decision = self._repository.get_decision(tenant_id=tenant_id, decision_id=decision_id, clearance_rank=clearance_rank, role_ids=role_ids)
        if decision is None:
            raise DecisionNotFoundError("Decision not found")
        return decision
