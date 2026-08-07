from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.modules.decisions.memory_repository import DecisionMemoryRepository
from app.modules.decisions.memory_service import DecisionMemoryService
from app.modules.decisions.memory_schemas import (
    DecisionComparisonResponse,
    PrecedentListResponse,
)
from app.modules.decisions.precedent_repository import DecisionPrecedentRepository
from app.modules.decisions.precedent_service import (
    DecisionPrecedentService,
    PrecedentStateError,
)
from app.modules.decisions.precedent_schemas import (
    LessonAdoptionCreate,
    LessonAdoptionMutationResponse,
    LessonAdoptionResponse,
    LessonAdoptionSupersede,
    PrecedentAttach,
    PrecedentMutationResponse,
    PrecedentReferenceResponse,
    PrecedentRemove,
)
from app.modules.decisions.learning_repository import DecisionLearningRepository
from app.modules.decisions.learning_service import (
    DecisionLearningService,
    LearningStateError,
)
from app.modules.decisions.learning_schemas import (
    DecisionLearningResponse,
    EvaluationSupersede,
    HistoricalUsageResponse,
    LessonEvaluationCreate,
    LessonEvaluationResponse,
    PrecedentEvaluationCreate,
    PrecedentEvaluationResponse,
)
from app.modules.decisions.promotion_repository import DecisionLessonPromotionRepository
from app.modules.decisions.promotion_service import (
    DecisionLessonPromotionService,
    LessonPromotionStateError,
)
from app.modules.decisions.promotion_schemas import (
    KnowledgeLessonProvenanceResponse,
    LessonPromotionAction,
    LessonPromotionCreate,
    LessonPromotionResponse,
    LessonPromotionWorkspaceResponse,
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


def get_memory_service(db: Session = Depends(get_db)) -> DecisionMemoryService:
    memory = DecisionMemoryRepository(db)
    learning = DecisionLearningService(DecisionLearningRepository(db), memory)
    return DecisionMemoryService(memory, learning)


def get_precedent_service(db: Session = Depends(get_db)) -> DecisionPrecedentService:
    return DecisionPrecedentService(
        DecisionPrecedentRepository(db), DecisionMemoryRepository(db)
    )


def get_learning_service(db: Session = Depends(get_db)) -> DecisionLearningService:
    return DecisionLearningService(
        DecisionLearningRepository(db), DecisionMemoryRepository(db)
    )


def get_promotion_service(
    db: Session = Depends(get_db),
) -> DecisionLessonPromotionService:
    return DecisionLessonPromotionService(
        DecisionLessonPromotionRepository(db), DecisionMemoryRepository(db)
    )


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
    if isinstance(exc, PrecedentStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, LearningStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, LessonPromotionStateError):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.get(
    "/decisions/{decision_id}/lessons/{lesson_id}/promotions",
    response_model=LessonPromotionWorkspaceResponse,
)
def lesson_promotion_workspace(
    decision_id: str,
    lesson_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionLessonPromotionService = Depends(get_promotion_service),
):
    try:
        return service.workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            lesson_id=lesson_id,
            membership_id=principal.membership.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        LessonPromotionStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lessons/{lesson_id}/promotions",
    response_model=LessonPromotionResponse,
    status_code=201,
)
def propose_lesson_promotion(
    decision_id: str,
    lesson_id: str,
    body: LessonPromotionCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionLessonPromotionService = Depends(get_promotion_service),
):
    try:
        return service.propose(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            lesson_id=lesson_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        LessonPromotionStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lessons/{lesson_id}/promotions/{proposal_id}/review/{action}",
    response_model=LessonPromotionResponse,
)
def act_on_lesson_promotion(
    decision_id: str,
    lesson_id: str,
    proposal_id: str,
    action: Literal["approve", "reject", "withdraw"],
    body: LessonPromotionAction,
    principal: Principal = Depends(get_principal),
    service: DecisionLessonPromotionService = Depends(get_promotion_service),
):
    try:
        if action == "withdraw":
            return service.withdraw(
                tenant_id=principal.tenant_id,
                decision_id=decision_id,
                lesson_id=lesson_id,
                proposal_id=proposal_id,
                membership_id=principal.membership.id,
                actor_id=principal.user.id,
                clearance_rank=principal.membership.clearance_rank,
                role_ids=principal.role_ids,
                permissions=principal.permissions,
                rationale=body.rationale,
            )
        return service.review(
            action={"approve": "approved", "reject": "rejected"}[action],
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            lesson_id=lesson_id,
            proposal_id=proposal_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        LessonPromotionStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lessons/{lesson_id}/promotions/{proposal_id}/promote",
    response_model=LessonPromotionResponse,
)
def promote_lesson(
    decision_id: str,
    lesson_id: str,
    proposal_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionLessonPromotionService = Depends(get_promotion_service),
):
    try:
        return service.promote(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            lesson_id=lesson_id,
            proposal_id=proposal_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        LessonPromotionStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/knowledge/{card_id}/decision-lesson-provenance",
    response_model=KnowledgeLessonProvenanceResponse,
)
def knowledge_lesson_provenance(
    card_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionLessonPromotionService = Depends(get_promotion_service),
):
    try:
        return service.provenance(
            tenant_id=principal.tenant_id,
            card_id=card_id,
            membership_id=principal.membership.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get("/decisions/{decision_id}/precedents", response_model=PrecedentListResponse)
def list_decision_precedents(
    decision_id: str,
    minimum_relevance: Literal[
        "strongly_relevant", "relevant", "somewhat_relevant", "weakly_relevant"
    ] = "weakly_relevant",
    limit: int = Query(default=10, ge=1, le=50),
    date_from: date | None = None,
    date_to: date | None = None,
    outcome_classification: Literal[
        "exceeded",
        "met",
        "partially_met",
        "did_not_meet",
        "inconclusive",
        "too_early",
        "cancelled",
    ]
    | None = None,
    business_concept_id: str | None = None,
    principal: Principal = Depends(get_principal),
    service: DecisionMemoryService = Depends(get_memory_service),
):
    try:
        return service.list_precedents(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            membership_id=principal.membership.id,
            minimum_relevance=minimum_relevance,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
            outcome_classification=outcome_classification,
            business_concept_id=business_concept_id,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/precedents/{historical_decision_id}",
    response_model=DecisionComparisonResponse,
)
def compare_decision_precedent(
    decision_id: str,
    historical_decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionMemoryService = Depends(get_memory_service),
):
    try:
        return service.compare(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            historical_decision_id=historical_decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            membership_id=principal.membership.id,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/precedent-references",
    response_model=list[PrecedentReferenceResponse],
)
def list_precedent_references(
    decision_id: str,
    history: bool = False,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.list_precedents(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            history=history,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/precedent-references",
    response_model=PrecedentMutationResponse,
    status_code=201,
)
def attach_precedent_reference(
    decision_id: str,
    body: PrecedentAttach,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.attach(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        PrecedentStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.delete(
    "/decisions/{decision_id}/precedent-references/{precedent_id}",
    response_model=PrecedentMutationResponse,
)
def remove_precedent_reference(
    decision_id: str,
    precedent_id: str,
    body: PrecedentRemove,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.remove(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            precedent_id=precedent_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (DecisionNotFoundError, DecisionPermissionError, PrecedentStateError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/lesson-adoptions",
    response_model=list[LessonAdoptionResponse],
)
def list_lesson_adoptions(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.list_adoptions(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lesson-adoptions",
    response_model=LessonAdoptionMutationResponse,
    status_code=201,
)
def create_lesson_adoption(
    decision_id: str,
    body: LessonAdoptionCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.adopt_or_reject(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        PrecedentStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lesson-adoptions/{adoption_id}/supersede",
    response_model=LessonAdoptionMutationResponse,
)
def supersede_lesson_adoption(
    decision_id: str,
    adoption_id: str,
    body: LessonAdoptionSupersede,
    principal: Principal = Depends(get_principal),
    service: DecisionPrecedentService = Depends(get_precedent_service),
):
    try:
        return service.supersede(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            adoption_id=adoption_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            rationale=body.rationale,
        )
    except (DecisionNotFoundError, DecisionPermissionError, PrecedentStateError) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decisions/{decision_id}/learning", response_model=DecisionLearningResponse
)
def get_decision_learning(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.workspace(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            membership_id=principal.membership.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/precedent-references/{reference_id}/evaluation",
    response_model=PrecedentEvaluationResponse,
    status_code=201,
)
def evaluate_precedent(
    decision_id: str,
    reference_id: str,
    body: PrecedentEvaluationCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.evaluate_precedent(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            reference_id=reference_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        LearningStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lesson-adoptions/{adoption_id}/evaluation",
    response_model=LessonEvaluationResponse,
    status_code=201,
)
def evaluate_lesson(
    decision_id: str,
    adoption_id: str,
    body: LessonEvaluationCreate,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.evaluate_lesson(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            adoption_id=adoption_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        LearningStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.get(
    "/decision-memory/{historical_decision_id}/usage",
    response_model=HistoricalUsageResponse,
)
def historical_usage(
    historical_decision_id: str,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.usage(
            tenant_id=principal.tenant_id,
            historical_decision_id=historical_decision_id,
            membership_id=principal.membership.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
        )
    except (DecisionNotFoundError, DecisionPermissionError) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/precedent-references/{reference_id}/evaluation/supersede",
    response_model=PrecedentEvaluationResponse,
)
def supersede_precedent_evaluation(
    decision_id: str,
    reference_id: str,
    body: EvaluationSupersede,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.supersede_precedent(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            reference_id=reference_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        LearningStateError,
    ) as exc:
        raise map_failure(exc) from exc


@router.post(
    "/decisions/{decision_id}/lesson-adoptions/{adoption_id}/evaluation/supersede",
    response_model=LessonEvaluationResponse,
)
def supersede_lesson_evaluation(
    decision_id: str,
    adoption_id: str,
    body: EvaluationSupersede,
    principal: Principal = Depends(get_principal),
    service: DecisionLearningService = Depends(get_learning_service),
):
    try:
        return service.supersede_lesson(
            tenant_id=principal.tenant_id,
            decision_id=decision_id,
            adoption_id=adoption_id,
            membership_id=principal.membership.id,
            actor_id=principal.user.id,
            clearance_rank=principal.membership.clearance_rank,
            role_ids=principal.role_ids,
            permissions=principal.permissions,
            command=body,
        )
    except (
        DecisionNotFoundError,
        DecisionPermissionError,
        DecisionConflictError,
        LearningStateError,
    ) as exc:
        raise map_failure(exc) from exc


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
