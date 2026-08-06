from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    KnowledgeCard,
    SourceDocument,
    Workspace,
)


OPEN_STATUSES = {
    "draft",
    "analysis",
    "evidence_collection",
    "in_review",
    "conditionally_approved",
}
APPROVAL_STATUSES = {"in_review", "conditionally_approved"}
CLOSED_STATUSES = {"approved", "rejected", "closed"}
RISK_ORDER = ["low", "medium", "high", "critical"]


def _count(db: Session, model: Any, tenant_id: str, *extra: Any) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.tenant_id == tenant_id, *extra)
        )
        or 0
    )


def _average(db: Session, column: Any, tenant_id: str, model: Any) -> float:
    return float(
        db.scalar(
            select(func.avg(column)).where(model.tenant_id == tenant_id)
        )
        or 0
    )


def _month_start(offset: int = 0) -> datetime:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month + offset
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def _build_decision_trend(decisions: list[DecisionCase]) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    for offset in range(-5, 1):
        start = _month_start(offset)
        end = _month_start(offset + 1)
        created = sum(start <= item.created_at < end for item in decisions)
        completed = sum(
            item.status in CLOSED_STATUSES
            and start <= item.updated_at < end
            for item in decisions
        )
        buckets.append(
            {
                "label": start.strftime("%b"),
                "created": created,
                "completed": completed,
            }
        )
    return buckets


def _build_readiness_distribution(
    decisions: list[DecisionCase],
) -> list[dict[str, Any]]:
    ranges = [
        ("0–24", 0, 25),
        ("25–49", 25, 50),
        ("50–74", 50, 75),
        ("75–100", 75, 101),
    ]
    return [
        {
            "label": label,
            "value": sum(low <= item.readiness_score < high for item in decisions),
        }
        for label, low, high in ranges
    ]


def _build_alerts(
    decisions: list[DecisionCase],
    pending_review: int,
) -> list[dict[str, Any]]:
    today = date.today()
    alerts: list[dict[str, Any]] = []

    critical = [
        item
        for item in decisions
        if item.status in OPEN_STATUSES and item.risk_level == "critical"
    ]
    high = [
        item
        for item in decisions
        if item.status in OPEN_STATUSES and item.risk_level == "high"
    ]
    overdue = [
        item
        for item in decisions
        if item.status in OPEN_STATUSES
        and item.due_date is not None
        and item.due_date < today
    ]
    low_readiness = [
        item
        for item in decisions
        if item.status in OPEN_STATUSES and item.readiness_score < 50
    ]

    if critical:
        alerts.append(
            {
                "severity": "critical",
                "title": f"{len(critical)} critical-risk decision"
                f"{'' if len(critical) == 1 else 's'}",
                "description": "Immediate accountable review is required.",
                "href": "/decisions",
            }
        )
    if high:
        alerts.append(
            {
                "severity": "high",
                "title": f"{len(high)} high-risk decision"
                f"{'' if len(high) == 1 else 's'}",
                "description": "Risk owners should confirm evidence and mitigation.",
                "href": "/decisions",
            }
        )
    if overdue:
        alerts.append(
            {
                "severity": "high",
                "title": f"{len(overdue)} overdue review"
                f"{'' if len(overdue) == 1 else 's'}",
                "description": "The planned decision date has passed.",
                "href": "/decisions",
            }
        )
    if low_readiness:
        alerts.append(
            {
                "severity": "medium",
                "title": f"{len(low_readiness)} decision"
                f"{'' if len(low_readiness) == 1 else 's'} below 50% readiness",
                "description": "Additional governed evidence is required.",
                "href": "/decisions",
            }
        )
    if pending_review:
        alerts.append(
            {
                "severity": "medium",
                "title": f"{pending_review} knowledge item"
                f"{'' if pending_review == 1 else 's'} pending review",
                "description": "Approval will improve governed evidence coverage.",
                "href": "/governance",
            }
        )

    return alerts[:5]


def _build_insights(
    summary: dict[str, Any],
    risk_distribution: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []

    if summary["average_readiness"] >= 80:
        insights.append(
            {
                "tone": "positive",
                "title": "Decision readiness is strong",
                "description": (
                    f"Average readiness is {summary['average_readiness']}%, "
                    "supporting efficient accountable review."
                ),
            }
        )
    elif summary["open_decisions"] > 0:
        insights.append(
            {
                "tone": "attention",
                "title": "Decision readiness requires attention",
                "description": (
                    f"Average readiness is {summary['average_readiness']}%. "
                    "Focus on missing or unapproved evidence."
                ),
            }
        )

    high_risk = sum(
        item["value"]
        for item in risk_distribution
        if item["label"] in {"high", "critical"}
    )
    if high_risk:
        insights.append(
            {
                "tone": "attention",
                "title": "Risk review should be prioritized",
                "description": (
                    f"{high_risk} open decision"
                    f"{'' if high_risk == 1 else 's'} "
                    "carry high or critical risk."
                ),
            }
        )
    elif summary["open_decisions"] > 0:
        insights.append(
            {
                "tone": "positive",
                "title": "No high-risk decisions are open",
                "description": "The active portfolio is currently below the high-risk threshold.",
            }
        )

    if summary["governance_score"] >= 80:
        insights.append(
            {
                "tone": "positive",
                "title": "Governed knowledge coverage is healthy",
                "description": (
                    f"{summary['governance_score']}% of knowledge is approved, "
                    "trusted, and eligible for governed AI use."
                ),
            }
        )
    else:
        insights.append(
            {
                "tone": "neutral",
                "title": "Knowledge governance can improve",
                "description": (
                    f"Governance coverage is {summary['governance_score']}%. "
                    "Resolve approval and trust gaps to improve decision support."
                ),
            }
        )

    if not alerts:
        insights.append(
            {
                "tone": "positive",
                "title": "No executive alerts require action",
                "description": "The current portfolio has no overdue, high-risk, or review exceptions.",
            }
        )

    return insights[:4]


def build_dashboard(db: Session, tenant_id: str) -> dict[str, Any]:
    decisions = list(
        db.scalars(
            select(DecisionCase)
            .where(DecisionCase.tenant_id == tenant_id)
            .order_by(DecisionCase.created_at.desc())
        ).all()
    )

    knowledge_cards = list(
        db.scalars(
            select(KnowledgeCard).where(KnowledgeCard.tenant_id == tenant_id)
        ).all()
    )

    open_decisions = [
        item for item in decisions if item.status in OPEN_STATUSES
    ]
    pending_approval = [
        item for item in decisions if item.status in APPROVAL_STATUSES
    ]
    high_risk = [
        item
        for item in open_decisions
        if item.risk_level in {"high", "critical"}
    ]
    today = date.today()
    overdue = [
        item
        for item in open_decisions
        if item.due_date is not None and item.due_date < today
    ]

    average_readiness = (
        round(
            sum(item.readiness_score for item in open_decisions)
            / len(open_decisions)
        )
        if open_decisions
        else 0
    )
    average_confidence = (
        round(
            sum(item.confidence for item in decisions)
            / len(decisions)
            * 100
        )
        if decisions
        else 0
    )

    approved_cards = [
        card for card in knowledge_cards if card.approval_status == "approved"
    ]
    governed_cards = [
        card
        for card in knowledge_cards
        if card.approval_status == "approved"
        and card.trust_score >= 0.8
        and card.ai_usage_allowed
    ]
    governance_score = (
        round(len(governed_cards) / len(knowledge_cards) * 100)
        if knowledge_cards
        else 0
    )

    summary = {
        "open_decisions": len(open_decisions),
        "pending_approval": len(pending_approval),
        "high_risk": len(high_risk),
        "overdue": len(overdue),
        "average_readiness": average_readiness,
        "knowledge_cards": len(knowledge_cards),
        "business_concepts": _count(
            db,
            BusinessConcept,
            tenant_id,
            BusinessConcept.status == "active",
        ),
        "evidence_sources": _count(db, SourceDocument, tenant_id),
        "workspaces": _count(db, Workspace, tenant_id),
        "governance_score": governance_score,
        "ai_confidence": average_confidence,
        "published_knowledge": len(approved_cards),
    }

    status_counts = Counter(item.status for item in decisions)
    risk_counts = Counter(item.risk_level for item in open_decisions)
    business_unit_counts = Counter(
        item.business_unit or "Unassigned" for item in decisions
    )

    charts = {
        "decision_status": [
            {"label": key, "value": value}
            for key, value in sorted(status_counts.items())
        ],
        "risk_distribution": [
            {"label": risk, "value": risk_counts.get(risk, 0)}
            for risk in RISK_ORDER
        ],
        "readiness_distribution": _build_readiness_distribution(decisions),
        "decision_trend": _build_decision_trend(decisions),
        "business_units": [
            {"label": key, "value": value}
            for key, value in business_unit_counts.most_common(6)
        ],
    }

    pending_review = sum(
        card.approval_status == "pending_review"
        for card in knowledge_cards
    )
    alerts = _build_alerts(decisions, pending_review)
    insights = _build_insights(
        summary,
        charts["risk_distribution"],
        alerts,
    )

    activity = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
        ).all()
    )

    briefing_parts = []
    if summary["open_decisions"]:
        briefing_parts.append(
            f"{summary['open_decisions']} open decision"
            f"{'' if summary['open_decisions'] == 1 else 's'} "
            f"with {summary['average_readiness']}% average readiness"
        )
    else:
        briefing_parts.append("no open decisions")
    if summary["high_risk"]:
        briefing_parts.append(
            f"{summary['high_risk']} high-risk item"
            f"{'' if summary['high_risk'] == 1 else 's'}"
        )
    if pending_review:
        briefing_parts.append(
            f"{pending_review} knowledge review"
            f"{'' if pending_review == 1 else 's'} awaiting action"
        )

    briefing = {
        "title": "Executive decision briefing",
        "summary": (
            "DecisionVault is currently tracking "
            + ", ".join(briefing_parts)
            + f". Governance coverage is {governance_score}%."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "deterministic",
    }

    return {
        "summary": summary,
        "briefing": briefing,
        "charts": charts,
        "alerts": alerts,
        "insights": insights,
        "activity": activity,
        "cache_ttl_seconds": 30,
    }
