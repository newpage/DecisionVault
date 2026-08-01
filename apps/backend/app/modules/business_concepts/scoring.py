from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models import KnowledgeCard
from app.modules.business_concepts.schemas import (
    ConceptFinding,
    ScoreExplanation,
    ScoreFactor,
)


STALE_AFTER_DAYS = 180


@dataclass(frozen=True)
class KnowledgeAssessment:
    total: int
    approved: int
    trusted: int
    current: int
    ai_eligible: int


def assess_knowledge(
    cards: Iterable[KnowledgeCard],
    *,
    now: datetime | None = None,
) -> KnowledgeAssessment:
    card_list = list(cards)
    current_time = now or datetime.now(timezone.utc)
    stale_before = current_time - timedelta(days=STALE_AFTER_DAYS)

    return KnowledgeAssessment(
        total=len(card_list),
        approved=sum(
            1 for card in card_list if card.approval_status == "approved"
        ),
        trusted=sum(1 for card in card_list if card.trust_score >= 0.8),
        current=sum(
            1
            for card in card_list
            if _as_aware(card.created_at) >= stale_before
        ),
        ai_eligible=sum(1 for card in card_list if card.ai_usage_allowed),
    )


def calculate_readiness(
    assessment: KnowledgeAssessment,
) -> ScoreExplanation:
    if assessment.total == 0:
        return ScoreExplanation(
            label="Decision Readiness",
            score=0,
            rating="needs_attention",
            formula=(
                "Approval 40% + Trust 30% + Currency 20% + "
                "AI Eligibility 10%"
            ),
            factors=[
                ScoreFactor(
                    key="coverage",
                    label="Connected knowledge",
                    achieved=0,
                    possible=100,
                    explanation=(
                        "No Knowledge Cards are connected, so readiness "
                        "cannot yet be established."
                    ),
                )
            ],
        )

    approval = round(assessment.approved / assessment.total * 40)
    trust = round(assessment.trusted / assessment.total * 30)
    currency_score = round(assessment.current / assessment.total * 20)
    ai_eligibility = round(assessment.ai_eligible / assessment.total * 10)
    score = approval + trust + currency_score + ai_eligibility

    rating = (
        "strong"
        if score >= 80
        else "developing"
        if score >= 50
        else "needs_attention"
    )

    return ScoreExplanation(
        label="Decision Readiness",
        score=score,
        rating=rating,
        formula=(
            "Approval 40% + Trust 30% + Currency 20% + "
            "AI Eligibility 10%"
        ),
        factors=[
            ScoreFactor(
                key="approval",
                label="Approved knowledge",
                achieved=approval,
                possible=40,
                explanation=(
                    f"{assessment.approved} of {assessment.total} connected "
                    "Knowledge Cards are approved."
                ),
            ),
            ScoreFactor(
                key="trust",
                label="Trusted knowledge",
                achieved=trust,
                possible=30,
                explanation=(
                    f"{assessment.trusted} of {assessment.total} cards have "
                    "a trust score of at least 80%."
                ),
            ),
            ScoreFactor(
                key="currency",
                label="Current knowledge",
                achieved=currency_score,
                possible=20,
                explanation=(
                    f"{assessment.current} of {assessment.total} cards were "
                    f"created within the last {STALE_AFTER_DAYS} days."
                ),
            ),
            ScoreFactor(
                key="ai_eligibility",
                label="AI-eligible knowledge",
                achieved=ai_eligibility,
                possible=10,
                explanation=(
                    f"{assessment.ai_eligible} of {assessment.total} cards "
                    "permit governed AI use."
                ),
            ),
        ],
    )


def detect_findings(
    cards: Iterable[KnowledgeCard],
    *,
    now: datetime | None = None,
) -> list[ConceptFinding]:
    card_list = list(cards)
    current_time = now or datetime.now(timezone.utc)
    stale_before = current_time - timedelta(days=STALE_AFTER_DAYS)
    findings: list[ConceptFinding] = []

    if not card_list:
        findings.append(
            ConceptFinding(
                id="missing-knowledge",
                finding_type="missing_knowledge",
                severity="high",
                title="No connected knowledge",
                description=(
                    "This Business Concept has no connected Knowledge Cards, "
                    "so decisions cannot be grounded in approved evidence."
                ),
                recommended_action=(
                    "Connect at least one authoritative Knowledge Card."
                ),
                affected_count=0,
            )
        )
        return findings

    pending = [
        card for card in card_list
        if card.approval_status != "approved"
    ]
    if pending:
        findings.append(
            ConceptFinding(
                id="pending-approval",
                finding_type="pending_approval",
                severity="high",
                title="Knowledge awaiting approval",
                description=(
                    f"{len(pending)} connected Knowledge Card(s) are not "
                    "approved and should not be treated as final guidance."
                ),
                recommended_action=(
                    "Route the affected cards through review and approval."
                ),
                affected_count=len(pending),
            )
        )

    low_trust = [card for card in card_list if card.trust_score < 0.8]
    if low_trust:
        findings.append(
            ConceptFinding(
                id="low-trust",
                finding_type="low_trust",
                severity="medium",
                title="Low-trust knowledge detected",
                description=(
                    f"{len(low_trust)} connected Knowledge Card(s) have a "
                    "trust score below 80%."
                ),
                recommended_action=(
                    "Review evidence, ownership, and authority level."
                ),
                affected_count=len(low_trust),
            )
        )

    stale = [
        card
        for card in card_list
        if _as_aware(card.created_at) < stale_before
    ]
    if stale:
        findings.append(
            ConceptFinding(
                id="stale-knowledge",
                finding_type="stale_knowledge",
                severity="medium",
                title="Knowledge may require recertification",
                description=(
                    f"{len(stale)} connected Knowledge Card(s) are older "
                    f"than {STALE_AFTER_DAYS} days."
                ),
                recommended_action=(
                    "Confirm the content remains current or assign a review."
                ),
                affected_count=len(stale),
            )
        )

    restricted = [
        card for card in card_list if not card.ai_usage_allowed
    ]
    if restricted:
        findings.append(
            ConceptFinding(
                id="ai-restricted",
                finding_type="ai_restricted",
                severity="low",
                title="AI use is restricted",
                description=(
                    f"{len(restricted)} connected Knowledge Card(s) cannot "
                    "be used by AI services."
                ),
                recommended_action=(
                    "Confirm whether the restriction is intentional."
                ),
                affected_count=len(restricted),
            )
        )

    return findings


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
