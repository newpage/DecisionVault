from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.business_concepts.service import (
    BusinessConceptNotFoundError,
    BusinessConceptService,
)


class FakeRepository:
    concept = SimpleNamespace(
        id="concept-1",
        name="Software Validation",
        slug="software-validation",
        description="Validated systems and evidence.",
        category="Quality",
        icon="ShieldCheck",
        color="#5b8def",
        status="active",
        updated_at=datetime.now(timezone.utc),
    )

    def get_concept(self, **kwargs):
        return self.concept if kwargs["concept_id"] == "concept-1" else None

    def list_knowledge(self, **kwargs):
        return [
            SimpleNamespace(
                id="card-1",
                title="Validation Plan",
                summary="Defines the validation approach.",
                lifecycle_status="published",
                approval_status="approved",
                trust_score=0.94,
                created_at=datetime.now(timezone.utc),
            )
        ]

    def list_activity(self, **kwargs):
        return []

    def list_related(self, **kwargs):
        return []


def test_workspace_calculates_readiness_and_health():
    workspace = BusinessConceptService(FakeRepository()).get_workspace(
        tenant_id="tenant-1",
        concept_id="concept-1",
    )

    metrics = {metric.key: metric.value for metric in workspace.metrics}
    assert metrics["knowledge"] == 1
    assert metrics["readiness"] == 100
    assert metrics["health"] == 100


def test_workspace_rejects_missing_concept():
    with pytest.raises(BusinessConceptNotFoundError):
        BusinessConceptService(FakeRepository()).get_workspace(
            tenant_id="tenant-1",
            concept_id="missing",
        )
