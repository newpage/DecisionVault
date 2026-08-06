from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.modules.decisions.lifecycle import InvalidTransitionError
from app.modules.decisions.evidence import EvidenceValidationError
from app.modules.decisions.policies import DecisionPermissionError
from app.modules.decisions.review import ReviewStateError
from app.modules.decisions.repository import DecisionRepository
from app.modules.decisions.outcome_repository import DecisionOutcomeRepository
from app.modules.decisions.outcome_service import (
    DecisionOutcomeService,
    OutcomeStateError,
)
from app.modules.decisions.schemas import (
    ApprovalConditionResponse,
    ApprovalMutationResponse,
    ConditionSatisfaction,
    ConditionalApprovalRequest,
    DecisionActionRequest,
    DecisionCreate,
    AvailableEvidenceResponse,
    EvidenceMutationResponse,
    EvidenceRemoval,
    EvidenceResponse,
    EvidenceSelection,
    DecisionResponse,
    DecisionWorkspaceResponse,
    ReviewAssignment,
    ReviewReassignment,
    ReviewCancellation,
    ReviewCompletion,
    ReviewFindingCreate,
    ReviewFindingResolution,
    ReviewFindingResponse,
    ReviewResponse,
    ReviewWorkspaceResponse,
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
    ObservationVerify,
)
from app.modules.decisions.service import (
    DecisionNotFoundError,
    DecisionConflictError,
    DecisionService,
)
from app.modules.decisions.review_service import DecisionReviewService
from app.modules.members.repository import MemberDirectoryRepository
from app.modules.members.service import (
    CandidateEligibilityError,
    MemberDirectoryService,
)

router = APIRouter(tags=["Decision Intelligence"])


def get_service(db: Session = Depends(get_db)) -> DecisionService:
    return DecisionService(DecisionRepository(db))


def get_review_service(db: Session = Depends(get_db)) -> DecisionReviewService:
    return DecisionReviewService(
        DecisionRepository(db),
        MemberDirectoryService(MemberDirectoryRepository(db)),
    )


def get_outcome_service(db: Session = Depends(get_db)) -> DecisionOutcomeService:
    return DecisionOutcomeService(DecisionOutcomeRepository(db), DecisionRepository(db))


def map_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, DecisionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DecisionPermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, DecisionConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, EvidenceValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ReviewStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, CandidateEligibilityError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, OutcomeStateError):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.get(
    "/decisions/{decision_id}/effectiveness",
    response_model=EffectivenessWorkspaceResponse,
)
def get_effectiveness(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/outcomes",
    response_model=ExpectedOutcomeResponse,
    status_code=201,
)
def create_expected_outcome(
    decision_id: str,
    body: ExpectedOutcomeCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.create_outcome(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.patch(
    "/decisions/{decision_id}/outcomes/{outcome_id}",
    response_model=ExpectedOutcomeResponse,
)
def update_expected_outcome(
    decision_id: str,
    outcome_id: str,
    body: ExpectedOutcomeUpdate,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.update_outcome(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/outcomes/{outcome_id}/observations",
    response_model=ObservationResponse,
    status_code=201,
)
def record_outcome_observation(
    decision_id: str,
    outcome_id: str,
    body: ObservationCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.record_observation(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/outcomes/{outcome_id}/observations/{observation_id}/verify",
    response_model=ObservationResponse,
)
def verify_outcome_observation(
    decision_id: str,
    outcome_id: str,
    observation_id: str,
    body: ObservationVerify,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.verify_observation(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            observation_id=observation_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/outcomes/{outcome_id}/observations/{observation_id}/supersede",
    response_model=ObservationResponse,
    status_code=201,
)
def supersede_outcome_observation(
    decision_id: str,
    outcome_id: str,
    observation_id: str,
    body: ObservationSupersede,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.supersede_observation(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            outcome_id=outcome_id,
            observation_id=observation_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/effectiveness-assessments",
    response_model=AssessmentResponse,
    status_code=201,
)
def create_effectiveness_assessment(
    decision_id: str,
    body: AssessmentCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.create_assessment(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/effectiveness-assessments/{assessment_id}/complete",
    response_model=AssessmentResponse,
)
def complete_effectiveness_assessment(
    decision_id: str,
    assessment_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.complete_assessment(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            assessment_id=assessment_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lessons", response_model=LessonResponse, status_code=201
)
def record_decision_lesson(
    decision_id: str,
    body: LessonCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionOutcomeService = Depends(get_outcome_service),
):
    try:
        return service.record_lesson(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, OutcomeStateError) as exc:
        raise map_failure(exc) from exc


@router.get("/decisions", response_model=list[DecisionResponse])
def list_decisions(
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_decisions(
            tenant_id=principal.tenant_id,
            permissions=principal.permissions,
        )
    except (DecisionPermissionError,) as exc:
        raise map_failure(exc) from exc


@router.get("/decisions/{decision_id}", response_model=DecisionWorkspaceResponse)
def get_decision_workspace(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.get_workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post("/decisions", response_model=DecisionResponse, status_code=201)
def create_decision(
    body: DecisionCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.create_decision(
            tenant_id=principal.tenant_id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/available-evidence",
    response_model=list[AvailableEvidenceResponse],
)
def list_available_evidence(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_available_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/evidence",
    response_model=list[EvidenceResponse],
)
def list_active_evidence(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_active_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/evidence/history",
    response_model=list[EvidenceResponse],
)
def list_evidence_history(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.list_evidence_history(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/evidence",
    response_model=EvidenceMutationResponse,
    status_code=201,
)
def select_evidence(
    decision_id: str,
    body: EvidenceSelection,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.select_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            card_id=body.knowledge_card_id,
            chunk_id=body.knowledge_chunk_id,
            relationship_type=body.relationship_type,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        EvidenceValidationError,
    ) as exc:
        raise map_failure(exc) from exc


@router.delete(
    "/decisions/{decision_id}/evidence/{evidence_id}",
    response_model=EvidenceMutationResponse,
)
def remove_evidence(
    decision_id: str,
    evidence_id: str,
    body: EvidenceRemoval,
    principal: Principal = Depends(get_principal),
    service: DecisionService = Depends(get_service),
):
    try:
        return service.remove_evidence(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            evidence_id=evidence_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        EvidenceValidationError,
    ) as exc:
        raise map_failure(exc) from exc


def review_failure(exc: Exception) -> HTTPException:
    return map_failure(exc)


@router.get(
    "/decisions/{decision_id}/review-workspace",
    response_model=ReviewWorkspaceResponse,
)
def get_review_workspace(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/reviews",
    response_model=ReviewResponse,
    status_code=201,
)
def assign_review(
    decision_id: str,
    body: ReviewAssignment,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.assign(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            membership_id=body.membership_id,
            review_type=body.review_type,
            rationale=body.rationale,
        )
    except (
        CandidateEligibilityError,
        DecisionNotFoundError,
        DecisionPermissionError,
        ReviewStateError,
    ) as exc:
        raise review_failure(exc) from exc


@router.patch(
    "/decisions/{decision_id}/reviews/{review_id}/assignment",
    response_model=ReviewResponse,
)
def reassign_review(
    decision_id: str,
    review_id: str,
    body: ReviewReassignment,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.reassign(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            membership_id=body.membership_id,
            rationale=body.rationale,
        )
    except (
        CandidateEligibilityError,
        DecisionNotFoundError,
        DecisionPermissionError,
        ReviewStateError,
    ) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/submit-review",
    response_model=DecisionResponse,
)
def submit_review(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.submit(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        ReviewStateError,
        InvalidTransitionError,
    ) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/reviews/{review_id}/start",
    response_model=ReviewResponse,
)
def start_review(
    decision_id: str,
    review_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.start(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/reviews/{review_id}/findings",
    response_model=ReviewFindingResponse,
    status_code=201,
)
def add_review_finding(
    decision_id: str,
    review_id: str,
    body: ReviewFindingCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.add_finding(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            command=body,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc


@router.patch(
    "/decisions/{decision_id}/reviews/{review_id}/findings/{finding_id}",
    response_model=ReviewFindingResponse,
)
def resolve_review_finding(
    decision_id: str,
    review_id: str,
    finding_id: str,
    body: ReviewFindingResolution,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.resolve_finding(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            finding_id=finding_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            status=body.status,
            response=body.response,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/reviews/{review_id}/complete",
    response_model=ReviewResponse,
)
def complete_review(
    decision_id: str,
    review_id: str,
    body: ReviewCompletion,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.complete(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            conclusion=body.conclusion,
            summary=body.summary,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/reviews/{review_id}/cancel",
    response_model=ReviewResponse,
)
def cancel_review(
    decision_id: str,
    review_id: str,
    body: ReviewCancellation,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.cancel(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            review_id=review_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc


def _approval(
    decision_id: str,
    body: DecisionActionRequest,
    action: str,
    principal: Principal,
    service: DecisionReviewService,
):
    try:
        return service.approval(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            action=action,
            rationale=body.rationale,
            conditions=getattr(body, "conditions", None),
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        ReviewStateError,
        InvalidTransitionError,
    ) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/approve", response_model=ApprovalMutationResponse
)
def approve_decision(
    decision_id: str,
    body: DecisionActionRequest,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    return _approval(decision_id, body, "approved", principal, service)


@router.post(
    "/decisions/{decision_id}/conditionally-approve",
    response_model=ApprovalMutationResponse,
)
def conditionally_approve_decision(
    decision_id: str,
    body: ConditionalApprovalRequest,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    return _approval(decision_id, body, "conditionally_approved", principal, service)


@router.post("/decisions/{decision_id}/reject", response_model=ApprovalMutationResponse)
def reject_decision(
    decision_id: str,
    body: DecisionActionRequest,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    return _approval(decision_id, body, "rejected", principal, service)


@router.post(
    "/decisions/{decision_id}/return-for-changes",
    response_model=ApprovalMutationResponse,
)
def return_for_changes(
    decision_id: str,
    body: DecisionActionRequest,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.return_for_changes(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        ReviewStateError,
        InvalidTransitionError,
    ) as exc:
        raise review_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/conditions/{condition_id}/satisfy",
    response_model=ApprovalConditionResponse,
)
def satisfy_approval_condition(
    decision_id: str,
    condition_id: str,
    body: ConditionSatisfaction,
    principal: Principal = Depends(get_principal),
    service: DecisionReviewService = Depends(get_review_service),
):
    try:
        return service.satisfy_condition(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            condition_id=condition_id,
            actor_id=principal.user.id,
            permissions=principal.permissions,
            response=body.response,
        )
    except (DecisionNotFoundError, DecisionPermissionError, ReviewStateError) as exc:
        raise review_failure(exc) from exc
