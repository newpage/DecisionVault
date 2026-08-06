from __future__ import annotations

from sqlalchemy import exists, or_, select

from app.models import AccessPolicyRole, KnowledgeCard


def authorized_knowledge_filters(
    *,
    clearance_rank: int,
    role_ids: set[str],
    require_published: bool = False,
    require_ai_eligible: bool = False,
):
    """Return the shared clearance and role-policy authorization predicate."""
    filters = [
        KnowledgeCard.classification_rank <= clearance_rank,
        or_(
            KnowledgeCard.access_policy_id.is_(None),
            exists(
                select(1).where(
                    AccessPolicyRole.policy_id
                    == KnowledgeCard.access_policy_id,
                    AccessPolicyRole.role_id.in_(role_ids),
                )
            ),
        ),
    ]
    if require_published:
        filters.extend(
            [
                KnowledgeCard.lifecycle_status == "published",
                KnowledgeCard.approval_status == "approved",
            ]
        )
    if require_ai_eligible:
        filters.append(KnowledgeCard.ai_usage_allowed.is_(True))
    return filters
