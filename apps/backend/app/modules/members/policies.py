from app.modules.decisions.policies import (
    authorize_evidence_view,
    authorize_review_assign,
    authorize_view,
)


def authorize_reviewer_discovery(permissions: set[str]) -> None:
    authorize_view(permissions)
    authorize_evidence_view(permissions)
    authorize_review_assign(permissions)
