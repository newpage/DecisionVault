from __future__ import annotations
import re

import httpx
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import AccessPolicyRole, KnowledgeCard, KnowledgeChunk

TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{2,}")


def terms(q: str) -> list[str]:
    return list(dict.fromkeys(x.lower() for x in TOKEN_RE.findall(q)))[:12]


async def embedding(text: str) -> list[float] | None:
    if not settings.ollama_enabled:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{settings.ollama_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": text},
            )
            r.raise_for_status()
            data = r.json()
            return (data.get("embeddings") or [None])[0]
    except Exception:
        return None


async def retrieve(
    db: Session,
    *,
    tenant_id: str,
    clearance_rank: int,
    role_ids: set[str],
    query: str,
    limit: int = 8,
):
    qterms = terms(query)
    filters = [
        KnowledgeChunk.tenant_id == tenant_id,
        KnowledgeCard.lifecycle_status == "published",
        KnowledgeCard.approval_status == "approved",
        KnowledgeCard.ai_usage_allowed.is_(True),
        KnowledgeCard.classification_rank <= clearance_rank,
        or_(
            KnowledgeCard.access_policy_id.is_(None),
            exists(
                select(1).where(
                    AccessPolicyRole.policy_id == KnowledgeCard.access_policy_id,
                    AccessPolicyRole.role_id.in_(role_ids),
                )
            ),
        ),
    ]
    stmt = (
        select(KnowledgeChunk, KnowledgeCard)
        .join(KnowledgeCard, KnowledgeCard.id == KnowledgeChunk.knowledge_card_id)
        .where(*filters)
    )
    if qterms:
        stmt = stmt.where(
            or_(*[KnowledgeChunk.search_text.ilike(f"%{t}%") for t in qterms])
        )
    rows = db.execute(stmt.limit(50)).all()
    vec = await embedding(query)
    if vec:
        semantic = db.execute(
            select(
                KnowledgeChunk,
                KnowledgeCard,
                (1 - KnowledgeChunk.embedding.cosine_distance(vec)).label("semantic"),
            )
            .join(KnowledgeCard, KnowledgeCard.id == KnowledgeChunk.knowledge_card_id)
            .where(*filters, KnowledgeChunk.embedding.is_not(None))
            .order_by(KnowledgeChunk.embedding.cosine_distance(vec))
            .limit(30)
        ).all()
    else:
        semantic = []
    merged = {}
    for chunk, card in rows:
        lexical = sum(1 for t in qterms if t in chunk.search_text.lower()) / max(
            1, len(qterms)
        )
        merged[chunk.id] = (chunk, card, lexical * 0.7 + card.trust_score * 0.3)
    for chunk, card, score in semantic:
        old = merged.get(chunk.id)
        combined = float(score) * 0.75 + card.trust_score * 0.25
        if not old or combined > old[2]:
            merged[chunk.id] = (chunk, card, combined)
    return sorted(merged.values(), key=lambda x: x[2], reverse=True)[:limit]


async def answer(question: str, evidence: list[tuple]) -> str:
    if not evidence:
        return "DecisionVault could not find approved knowledge that applies to this question."
    context = "\n\n".join(
        f"[{i + 1}] {card.title}: {chunk.content}"
        for i, (chunk, card, _) in enumerate(evidence)
    )
    if settings.ollama_enabled:
        prompt = f"""You are DecisionVault. Answer only from the evidence. Cite sources as [1], [2]. State uncertainty and missing information.
Question: {question}
Evidence:
{context}"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_chat_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                r.raise_for_status()
                return r.json().get("response", "").strip()
        except Exception:
            pass
    top = evidence[0][1]
    return f"Based on approved knowledge, the strongest applicable source is **{top.title}**. Review citation [1] and the listed evidence before making the final decision."
