from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from app.core.config import settings


class EvidenceCard(Protocol):
    approval_status: str
    trust_score: float
    ai_usage_allowed: bool


@dataclass(frozen=True)
class ReadinessResult:
    score: int
    status: str
    approved: int
    trusted: int
    governed: int
    total: int
    summary: dict


GENERIC_CONTROL_AREAS = [
    "Policy and governance requirements",
    "Operational capability and controls",
    "Risk, compliance, and assurance",
    "Continuity, security, and accountability",
]

PAYMENTS_CONTROL_AREAS = [
    "Merchant profile and processing model",
    "Fraud, transaction behavior, and chargebacks",
    "KYC/KYB, beneficial ownership, AML, and sanctions",
    "Approval controls, monitoring, and operational risk",
]

CONTROL_AREAS = (
    PAYMENTS_CONTROL_AREAS
    if settings.demo_profile == "payments"
    else GENERIC_CONTROL_AREAS
)

def calculate_readiness(cards: list[EvidenceCard]) -> ReadinessResult:
    total = len(cards)
    approved = sum(card.approval_status == "approved" for card in cards)
    trusted = sum(card.trust_score >= 0.8 for card in cards)
    eligible = sum(card.ai_usage_allowed for card in cards)
    governed = sum(
        card.approval_status == "approved"
        and card.trust_score >= 0.8
        and card.ai_usage_allowed
        for card in cards
    )
    approval = round(approved / max(1, total) * 40) if total else 0
    trust = round(trusted / max(1, total) * 30) if total else 0
    coverage = min(20, total * 5)
    governance = round(eligible / max(1, total) * 10) if total else 0
    score = approval + trust + coverage + governance
    missing = []
    if total == 0:
        missing.append("No decision evidence is connected.")
    if approved < total:
        missing.append("One or more evidence items are not approved.")
    if trusted < total:
        missing.append("One or more evidence items have trust below 80%.")
    if total < 4:
        missing.append(
            "Evidence coverage is below the recommended four control areas."
        )
    status = (
        "ready"
        if score >= 80 and not missing
        else "review_required"
        if score >= 50
        else "insufficient_evidence"
    )
    summary = {
        "calculation": {
            "approved_evidence": {
                "points": approval,
                "possible": 40,
                "count": approved,
            },
            "trusted_evidence": {
                "points": trust,
                "possible": 30,
                "count": trusted,
            },
            "evidence_coverage": {
                "points": coverage,
                "possible": 20,
                "count": total,
            },
            "governed_ai_eligibility": {
                "points": governance,
                "possible": 10,
                "count": eligible,
            },
        },
        "missing_information": missing,
        "control_areas": CONTROL_AREAS,
    }
    return ReadinessResult(
        score, status, approved, trusted, governed, total, summary
    )


def generate_recommendation(
    *, supplier_name: str, readiness: ReadinessResult
) -> str:
    return (
        f"{supplier_name} currently has a readiness score of "
        f"{readiness.score}%. DecisionVault found {readiness.total} connected "
        f"evidence item(s), including {readiness.approved} approved and "
        f"{readiness.trusted} trusted item(s). Final approval remains with "
        "accountable business reviewers."
    )
