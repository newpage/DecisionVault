from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.deps import Principal, get_db, get_principal
from app.models import AuditEvent
from app.schemas import QuestionRequest
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
        "mode": (
            "Local AI enabled · deterministic fallback available"
            if settings.ollama_enabled
            else "Deterministic grounded fallback"
        ),
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
