from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.modules.business_concepts.scoring import (
    KnowledgeAssessment,
    assess_knowledge,
    calculate_readiness,
    detect_findings,
)


def card(
    *,
    approval_status: str = "approved",
    trust_score: float = 0.9,
    ai_usage_allowed: bool = True,
    age_days: int = 10,
):
    return SimpleNamespace(
        approval_status=approval_status,
        trust_score=trust_score,
        ai_usage_allowed=ai_usage_allowed,
        created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
    )


def test_readiness_uses_documented_weighting():
    assessment = KnowledgeAssessment(
        total=2,
        approved=1,
        trusted=2,
        current=2,
        ai_eligible=1,
    )

    result = calculate_readiness(assessment)

    assert result.score == 75
    assert [factor.possible for factor in result.factors] == [40, 30, 20, 10]


def test_findings_detect_governance_conditions():
    findings = detect_findings(
        [
            card(
                approval_status="pending_review",
                trust_score=0.5,
                ai_usage_allowed=False,
                age_days=220,
            )
        ]
    )

    finding_types = {finding.finding_type for finding in findings}
    assert finding_types == {
        "pending_approval",
        "low_trust",
        "stale_knowledge",
        "ai_restricted",
    }


def test_empty_concept_has_missing_knowledge_finding():
    assessment = assess_knowledge([])
    readiness = calculate_readiness(assessment)
    findings = detect_findings([])

    assert readiness.score == 0
    assert findings[0].finding_type == "missing_knowledge"
