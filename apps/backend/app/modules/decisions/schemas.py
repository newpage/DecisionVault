from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionCreate(BaseModel):
    workspace_id: str
    business_concept_id: str | None = None
    title: str = Field(min_length=3, max_length=240)
    question: str = Field(min_length=10)
    supplier_name: str = Field(min_length=2, max_length=180)
    supplier_category: str = Field(default="Electronic Manufacturer", max_length=120)
    supplier_location: str = Field(default="", max_length=180)
    owner_name: str = Field(min_length=2, max_length=180)
    due_date: date | None = None
    priority: Literal["low", "medium", "high", "critical"] = "high"
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    decision_type: Literal[
        "initial_qualification",
        "conditional_approval",
        "renewal",
        "disqualification",
    ] = "initial_qualification"
    business_unit: str = Field(default="Electronics Supply Chain", max_length=180)
    classification_rank: int = Field(default=20, ge=0)
    access_policy_id: str | None = None


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    business_concept_id: str | None
    classification_rank: int = 20
    access_policy_id: str | None = None
    title: str
    question: str
    status: str
    recommendation: str
    confidence: float
    supplier_name: str
    supplier_category: str
    supplier_location: str
    owner_name: str
    due_date: date | None
    priority: str
    risk_level: str
    decision_type: str
    business_unit: str
    readiness_score: int
    readiness_status: str
    evidence_summary: dict
    input_revision: int = 1
    created_by: str
    created_at: datetime
    updated_at: datetime


class BusinessConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_card_id: str
    knowledge_chunk_id: str | None
    source_document_id: str | None
    relationship_type: str
    selection_rationale: str
    snapshot_title: str
    snapshot_content: str
    snapshot_source_filename: str
    snapshot_source_mime_type: str
    snapshot_source_locator: str
    snapshot_knowledge_type: str
    snapshot_authority_level: str
    snapshot_lifecycle_status: str
    snapshot_approval_status: str
    snapshot_classification_rank: int
    snapshot_access_policy_id: str | None
    snapshot_trust_score: float
    snapshot_ai_usage_allowed: bool
    snapshot_card_created_at: datetime
    snapshot_content_revision: str | None
    snapshot_source_metadata: dict
    selected_by: str
    selected_at: datetime
    removed_by: str | None
    removed_at: datetime | None
    removal_rationale: str | None
    superseded_by_id: str | None


class AvailableChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chunk_index: int
    content: str


class AvailableEvidenceResponse(BaseModel):
    id: str
    title: str
    summary: str
    knowledge_type: str
    authority_level: str
    trust_score: float
    ai_usage_allowed: bool
    chunks: list[AvailableChunkResponse]
    selected: bool


class EvidenceSelection(BaseModel):
    knowledge_card_id: str
    knowledge_chunk_id: str | None = None
    relationship_type: Literal[
        "supporting", "opposing", "contextual", "risk", "constraint"
    ]
    rationale: str = Field(min_length=3, max_length=2000)


class EvidenceRemoval(BaseModel):
    rationale: str = Field(min_length=3, max_length=2000)


class EvidenceMutationResponse(BaseModel):
    decision: DecisionResponse
    evidence: EvidenceResponse


class ReviewAssignment(BaseModel):
    membership_id: str
    review_type: Literal["business", "risk", "compliance", "final_approval"]
    rationale: str = Field(min_length=3, max_length=2000)


class ReviewReassignment(BaseModel):
    membership_id: str
    rationale: str = Field(min_length=3, max_length=2000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    sequence: int
    review_type: str
    assigned_reviewer_membership_id: str
    assigned_reviewer_name: str
    assigned_reviewer_email: str
    assigned_reviewer_organization: str
    assigned_by: str
    assigned_at: datetime
    status: str
    conclusion: str | None
    summary: str
    decision_revision: int | None
    freshness_status: str
    submitted_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_by: str | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewFindingCreate(BaseModel):
    finding_type: Literal[
        "information_request",
        "evidence_gap",
        "risk_concern",
        "policy_concern",
        "control_concern",
        "recommendation",
        "approval_condition",
        "comment",
    ]
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=4000)
    related_evidence_id: str | None = None
    related_section: str = Field(default="", max_length=120)
    required_response: bool = False


class ReviewFindingResolution(BaseModel):
    status: Literal["addressed", "accepted", "closed", "withdrawn"]
    response: str = Field(min_length=3, max_length=4000)


class ReviewFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    review_id: str
    finding_type: str
    severity: str
    title: str
    description: str
    related_evidence_id: str | None
    related_section: str
    required_response: bool
    status: str
    resolution_response: str
    raised_by: str
    raised_at: datetime
    resolved_by: str | None
    resolved_at: datetime | None


class ReviewCompletion(BaseModel):
    conclusion: Literal[
        "recommend_approve",
        "recommend_conditional",
        "recommend_reject",
        "changes_required",
    ]
    summary: str = Field(min_length=3, max_length=4000)


class ReviewCancellation(BaseModel):
    rationale: str = Field(min_length=3, max_length=2000)


class DecisionActionRequest(BaseModel):
    rationale: str = Field(min_length=3, max_length=4000)


class ApprovalConditionCreate(BaseModel):
    condition_text: str = Field(min_length=3, max_length=4000)
    responsible_party: str = Field(default="", max_length=180)
    due_date: date | None = None


class ConditionalApprovalRequest(DecisionActionRequest):
    conditions: list[ApprovalConditionCreate] = Field(min_length=1)


class ConditionSatisfaction(BaseModel):
    response: str = Field(min_length=3, max_length=4000)


class ApprovalActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    review_id: str | None
    action: str
    rationale: str
    actor_id: str
    created_at: datetime


class ApprovalConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    approval_action_id: str
    condition_text: str
    responsible_party: str
    due_date: date | None
    status: str
    created_by: str
    created_at: datetime
    satisfied_by: str | None
    satisfied_at: datetime | None
    satisfaction_response: str


class ApprovalMutationResponse(BaseModel):
    decision: DecisionResponse
    action: ApprovalActionResponse
    conditions: list[ApprovalConditionResponse] = Field(default_factory=list)


class ReviewWorkspaceResponse(BaseModel):
    reviews: list[ReviewResponse]
    findings: list[ReviewFindingResponse]
    approval_actions: list[ApprovalActionResponse]
    conditions: list[ApprovalConditionResponse]
    capabilities: dict[str, bool]


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_type: str
    description: str
    created_at: datetime


class WorkspaceSummary(BaseModel):
    evidence_count: int
    approved_count: int
    trusted_count: int
    governed_count: int
    confidence_percent: int
    missing_information: list[str]
    control_areas: list[str]
    calculation: dict
    allowed_transitions: list[str]


class DecisionWorkspaceResponse(BaseModel):
    decision: DecisionResponse
    business_concept: BusinessConceptResponse | None
    evidence: list[EvidenceResponse]
    activity: list[ActivityResponse]
    workspace_summary: WorkspaceSummary


class ExpectedOutcomeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=4000)
    category: str = Field(default="business", min_length=2, max_length=60)
    measurement_type: Literal[
        "numeric",
        "percentage",
        "currency",
        "duration",
        "boolean",
        "milestone",
        "qualitative",
    ]
    baseline_value: float | None = None
    target_value: float | None = None
    target_min_value: float | None = None
    target_max_value: float | None = None
    target_boolean: bool | None = None
    unit: str = Field(default="", max_length=60)
    target_direction: Literal[
        "increase", "decrease", "range", "exact", "complete", "maintain"
    ]
    target_date: date | None = None
    evaluation_window_days: int | None = Field(default=None, gt=0)
    responsible_membership_id: str | None = None
    weight: float = Field(default=1, gt=0, le=100)
    is_critical: bool = False
    success_criteria: str = Field(min_length=3, max_length=4000)


class ExpectedOutcomeUpdate(ExpectedOutcomeCreate):
    amendment_rationale: str | None = Field(default=None, min_length=3, max_length=2000)


class ExpectedOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    title: str
    description: str
    category: str
    measurement_type: str
    baseline_value: float | None
    target_value: float | None
    target_min_value: float | None
    target_max_value: float | None
    target_boolean: bool | None
    unit: str
    target_direction: str
    target_date: date | None
    evaluation_window_days: int | None
    responsible_membership_id: str | None
    weight: float
    is_critical: bool
    success_criteria: str
    revision: int
    status: str
    amended_from_id: str | None
    amendment_rationale: str
    frozen_at: datetime | None
    created_by_membership_id: str
    created_at: datetime
    updated_at: datetime


class ObservationCreate(BaseModel):
    observation_date: date
    numeric_value: float | None = None
    boolean_value: bool | None = None
    observed_status: Literal[
        "reported", "achieved", "not_achieved", "in_progress", "inconclusive"
    ] = "reported"
    narrative: str = Field(default="", max_length=4000)
    provenance: Literal[
        "manually_reported", "verified_business_record", "documented_evidence"
    ]
    source_reference: str = Field(default="", max_length=500)
    decision_evidence_id: str | None = None


class ObservationVerify(BaseModel):
    rationale: str = Field(min_length=3, max_length=2000)


class ObservationSupersede(ObservationCreate):
    rationale: str = Field(min_length=3, max_length=2000)


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    expected_outcome_id: str
    observation_date: date
    numeric_value: float | None
    boolean_value: bool | None
    observed_status: str
    narrative: str
    provenance: str
    source_reference: str
    decision_evidence_id: str | None
    recorded_by_membership_id: str
    recorded_at: datetime
    verification_status: str
    verified_by_membership_id: str | None
    verified_at: datetime | None
    verification_rationale: str
    superseded_by_id: str | None
    supersession_rationale: str


class AssessmentCreate(BaseModel):
    assessment_date: date
    evaluation_start: date | None = None
    evaluation_end: date | None = None
    classification: Literal[
        "exceeded",
        "met",
        "partially_met",
        "did_not_meet",
        "inconclusive",
        "too_early",
        "cancelled",
    ]
    rationale: str = Field(min_length=3, max_length=4000)
    outcome_summary: str = Field(default="", max_length=4000)
    risk_summary: str = Field(default="", max_length=4000)
    condition_summary: str = Field(default="", max_length=4000)
    evidence_references: list[str] = Field(default_factory=list, max_length=100)
    observation_references: list[str] = Field(default_factory=list, max_length=100)


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    revision: int
    status: str
    assessment_date: date
    evaluation_start: date | None
    evaluation_end: date | None
    assessor_membership_id: str
    classification: str
    rationale: str
    outcome_summary: str
    risk_summary: str
    condition_summary: str
    calculation_details: dict
    evidence_references: list[str]
    observation_references: list[str]
    completed_at: datetime | None
    supersedes_assessment_id: str | None
    created_at: datetime


class LessonCreate(BaseModel):
    lesson_type: Literal[
        "evidence", "process", "risk", "assumption", "execution", "governance"
    ]
    description: str = Field(min_length=3, max_length=4000)
    business_impact: str = Field(default="", max_length=4000)
    related_outcome_id: str | None = None
    related_evidence_id: str | None = None
    related_finding_id: str | None = None
    related_condition_id: str | None = None


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision_case_id: str
    lesson_type: str
    description: str
    business_impact: str
    related_outcome_id: str | None
    related_evidence_id: str | None
    related_finding_id: str | None
    related_condition_id: str | None
    created_by_membership_id: str
    created_at: datetime


class EffectivenessWorkspaceResponse(BaseModel):
    outcomes: list[ExpectedOutcomeResponse]
    observations: list[ObservationResponse]
    calculations: dict[str, dict]
    aggregate: dict
    assessments: list[AssessmentResponse]
    lessons: list[LessonResponse]
    conditions: list[ApprovalConditionResponse]
    capabilities: dict[str, bool]
