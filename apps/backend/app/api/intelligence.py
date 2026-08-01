from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import Principal, get_db, get_principal
from app.models import (
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    KnowledgeCard,
)
from app.schemas import (
    DecisionCreate,
    DecisionStatusUpdate,
    QuestionRequest,
)
from app.services import answer, retrieve

router = APIRouter(tags=["Decision Intelligence"])


@router.post("/ask")
async def ask(
    body: QuestionRequest,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    evidence = await retrieve(
        db,
        tenant_id=p.tenant_id,
        clearance_rank=p.membership.clearance_rank,
        role_ids=p.role_ids,
        query=body.question,
    )
    response = await answer(body.question, evidence)
    db.add(
        AuditEvent(
            tenant_id=p.tenant_id,
            actor_id=p.user.id,
            event_type="QuestionAnswered",
            entity_type="ai_interaction",
            description=body.question,
            details={"evidence_count": len(evidence)},
        )
    )
    db.commit()
    return {
        "answer": response,
        "confidence": round(
            sum(item[2] for item in evidence)
            / max(1, len(evidence))
            * 100
        ),
        "citations": [
            {
                "id": card.id,
                "title": card.title,
                "excerpt": chunk.content,
                "score": round(score * 100),
            }
            for chunk, card, score in evidence
        ],
    }


@router.get("/decisions")
def decisions(
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(DecisionCase)
        .where(DecisionCase.tenant_id == p.tenant_id)
        .order_by(DecisionCase.created_at.desc())
    ).all()


@router.get("/decisions/{decision_id}")
def decision_workspace(
    decision_id: str,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    decision = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == decision_id,
            DecisionCase.tenant_id == p.tenant_id,
        )
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    concept = None
    if decision.business_concept_id:
        concept = db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.id == decision.business_concept_id,
                BusinessConcept.tenant_id == p.tenant_id,
            )
        )

    knowledge = list(
        db.scalars(
            select(KnowledgeCard)
            .where(
                KnowledgeCard.tenant_id == p.tenant_id,
                KnowledgeCard.business_concept_id
                == decision.business_concept_id,
                KnowledgeCard.classification_rank
                <= p.membership.clearance_rank,
            )
            .order_by(
                KnowledgeCard.approval_status.desc(),
                KnowledgeCard.trust_score.desc(),
                KnowledgeCard.created_at.desc(),
            )
        ).all()
    )

    activity = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == p.tenant_id,
                AuditEvent.entity_type == "decision_case",
                AuditEvent.entity_id == decision.id,
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(25)
        ).all()
    )

    approved = sum(
        card.approval_status == "approved" for card in knowledge
    )
    trusted = sum(card.trust_score >= 0.8 for card in knowledge)
    governed = sum(
        card.approval_status == "approved"
        and card.trust_score >= 0.8
        and card.ai_usage_allowed
        for card in knowledge
    )

    return {
        "decision": decision,
        "business_concept": concept,
        "evidence": knowledge,
        "activity": activity,
        "workspace_summary": {
            "evidence_count": len(knowledge),
            "approved_count": approved,
            "trusted_count": trusted,
            "governed_count": governed,
            "confidence_percent": round(decision.confidence * 100),
            "missing_information": (
                decision.evidence_summary or {}
            ).get("missing_information", []),
            "control_areas": (
                decision.evidence_summary or {}
            ).get("control_areas", []),
            "calculation": (
                decision.evidence_summary or {}
            ).get("calculation", {}),
        },
    }


@router.post("/decisions")
def create_decision(
    body: DecisionCreate,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    concept_id = body.business_concept_id or db.scalar(
        select(BusinessConcept.id).where(
            BusinessConcept.tenant_id == p.tenant_id,
            BusinessConcept.slug == "supplier-qualification",
        )
    )
    cards = list(
        db.scalars(
            select(KnowledgeCard).where(
                KnowledgeCard.tenant_id == p.tenant_id,
                KnowledgeCard.business_concept_id == concept_id,
            )
        ).all()
    )
    total = len(cards)
    approved = sum(
        card.approval_status == "approved" for card in cards
    )
    trusted = sum(card.trust_score >= 0.8 for card in cards)
    eligible = sum(card.ai_usage_allowed for card in cards)

    approval = (
        round(approved / max(1, total) * 40) if total else 0
    )
    trust = round(trusted / max(1, total) * 30) if total else 0
    coverage = min(20, total * 5)
    governance = (
        round(eligible / max(1, total) * 10) if total else 0
    )
    readiness = approval + trust + coverage + governance

    missing = []
    if total == 0:
        missing.append(
            "No supplier qualification evidence is connected."
        )
    if approved < total:
        missing.append(
            "One or more evidence items are not approved."
        )
    if trusted < total:
        missing.append(
            "One or more evidence items have trust below 80%."
        )
    if total < 4:
        missing.append(
            "Evidence coverage is below the recommended four control areas."
        )

    readiness_status = (
        "ready"
        if readiness >= 80 and not missing
        else "review_required"
        if readiness >= 50
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
        "control_areas": [
            "Quality management and certifications",
            "Manufacturing capability and process controls",
            "Component traceability and counterfeit prevention",
            "Supply continuity and cybersecurity",
        ],
    }
    recommendation = (
        f"{body.supplier_name} currently has a readiness score of "
        f"{readiness}%. DecisionVault found {total} connected evidence "
        f"item(s), including {approved} approved and {trusted} trusted "
        "item(s). Final approval remains with accountable business "
        "reviewers."
    )
    decision = DecisionCase(
        tenant_id=p.tenant_id,
        workspace_id=body.workspace_id,
        business_concept_id=concept_id,
        title=body.title,
        question=body.question,
        status="evidence_collection",
        recommendation=recommendation,
        confidence=readiness / 100,
        supplier_name=body.supplier_name,
        supplier_category=body.supplier_category,
        supplier_location=body.supplier_location,
        owner_name=body.owner_name,
        due_date=body.due_date,
        priority=body.priority,
        risk_level=body.risk_level,
        decision_type=body.decision_type,
        business_unit=body.business_unit,
        readiness_score=readiness,
        readiness_status=readiness_status,
        evidence_summary=summary,
        created_by=p.user.id,
    )
    db.add(decision)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=p.tenant_id,
            actor_id=p.user.id,
            event_type="DecisionCreated",
            entity_type="decision_case",
            entity_id=decision.id,
            description=(
                "Supplier qualification decision created for "
                f"{body.supplier_name}."
            ),
            details={
                "supplier_category": body.supplier_category,
                "readiness_score": readiness,
                "risk_level": body.risk_level,
            },
        )
    )
    db.commit()
    db.refresh(decision)
    return decision


@router.patch("/decisions/{decision_id}/status")
def update_status(
    decision_id: str,
    body: DecisionStatusUpdate,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    decision = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == decision_id,
            DecisionCase.tenant_id == p.tenant_id,
        )
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    previous = decision.status
    decision.status = body.status
    decision.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            tenant_id=p.tenant_id,
            actor_id=p.user.id,
            event_type="DecisionStatusChanged",
            entity_type="decision_case",
            entity_id=decision.id,
            description=(
                f"Decision status changed from {previous} "
                f"to {body.status}."
            ),
            details={
                "previous": previous,
                "current": body.status,
            },
        )
    )
    db.commit()
    db.refresh(decision)
    return decision
