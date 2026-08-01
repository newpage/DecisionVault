from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.business_concepts.service import BusinessConceptService


class FakeRepository:
    def list_with_knowledge_counts(self, *, tenant_id: str, query: str = ""):
        assert tenant_id == "tenant-1"
        assert query == "validation"
        return [
            (
                SimpleNamespace(
                    id="concept-1",
                    name="Software Validation",
                    slug="software-validation",
                    description="Validated systems and evidence.",
                    category="Quality",
                    icon="ShieldCheck",
                    color="#5b8def",
                    status="active",
                    updated_at=datetime.now(timezone.utc),
                ),
                12,
            )
        ]


def test_list_concepts_maps_knowledge_counts():
    service = BusinessConceptService(FakeRepository())

    concepts = service.list_concepts(
        tenant_id="tenant-1",
        query="validation",
    )

    assert len(concepts) == 1
    assert concepts[0].name == "Software Validation"
    assert concepts[0].knowledge_count == 12
