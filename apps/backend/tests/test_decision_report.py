from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.deps import get_principal
from app.modules.decisions.router import get_service, router
from app.modules.decisions.schemas import DecisionWorkspaceResponse
from app.modules.decisions.service import DecisionNotFoundError


def workspace() -> DecisionWorkspaceResponse:
    now = datetime.now(timezone.utc)
    return DecisionWorkspaceResponse.model_validate(
        {
            "decision": {
                "id": "decision-1",
                "workspace_id": "workspace-1",
                "business_concept_id": "concept-1",
                "classification_rank": 30,
                "title": "Northstar merchant acquiring decision",
                "question": "Should Northstar be approved for merchant acquiring?",
                "status": "evidence_collection",
                "recommendation": "Do not activate processing while the critical alert remains open.",
                "confidence": 0.89,
                "supplier_name": "Northstar Digital Commerce LLC",
                "supplier_category": "Digital-goods marketplace merchant",
                "supplier_location": "Austin, Texas",
                "owner_name": "Merchant Risk Committee",
                "due_date": None,
                "priority": "critical",
                "risk_level": "critical",
                "decision_type": "initial_qualification",
                "business_unit": "Merchant Acquiring Risk",
                "readiness_score": 89,
                "readiness_status": "review_required",
                "evidence_summary": {
                    "demo_analysis": {
                        "critical_findings": [
                            "Active coordinated card-testing attack detected",
                            "$186,000 attempted exposure in 24 hours",
                        ],
                        "facts": ["Authorization attempts reached 11.6x baseline."],
                        "conflicts": ["Merchant narrative reports no anomaly."],
                        "risks": ["Immediate containment is required."],
                        "missing_information": ["Independent containment verification."],
                        "assumptions": ["Telemetry is synthetic demo evidence."],
                        "controls": ["Block activation pending containment."],
                        "citations": ["Critical fraud-network escalation alert"],
                        "accountability": "Final approval remains human-controlled.",
                    }
                },
                "input_revision": 3,
                "created_by": "user-1",
                "created_at": now,
                "updated_at": now,
            },
            "business_concept": {
                "id": "concept-1",
                "name": "Merchant Risk",
                "description": "Payments risk decisions",
            },
            "evidence": [
                {
                    "id": "evidence-1",
                    "knowledge_card_id": "card-1",
                    "knowledge_chunk_id": None,
                    "source_document_id": "source-1",
                    "relationship_type": "risk",
                    "selection_rationale": "Critical governed risk evidence.",
                    "snapshot_title": "Critical fraud-network escalation - 24-hour alert",
                    "snapshot_content": "Attempted exposure reached $186,000.",
                    "snapshot_source_filename": "critical-alert.json",
                    "snapshot_source_mime_type": "application/json",
                    "snapshot_source_locator": "Synthetic source",
                    "snapshot_knowledge_type": "payments_critical_fraud_alert",
                    "snapshot_authority_level": "network_risk_alert",
                    "snapshot_lifecycle_status": "published",
                    "snapshot_approval_status": "approved",
                    "snapshot_classification_rank": 30,
                    "snapshot_access_policy_id": None,
                    "snapshot_trust_score": 0.99,
                    "snapshot_ai_usage_allowed": True,
                    "snapshot_card_created_at": now,
                    "snapshot_content_revision": "payments-demo-v1",
                    "snapshot_source_metadata": {"synthetic": True},
                    "selected_by": "user-1",
                    "selected_at": now,
                    "removed_by": None,
                    "removed_at": None,
                    "removal_rationale": None,
                    "superseded_by_id": None,
                }
            ],
            "activity": [],
            "workspace_summary": {
                "evidence_count": 1,
                "approved_count": 1,
                "trusted_count": 1,
                "governed_count": 1,
                "confidence_percent": 89,
                "missing_information": ["Independent containment verification."],
                "control_areas": ["Fraud monitoring"],
                "calculation": {},
                "allowed_transitions": [],
            },
        }
    )


class FakeReportService:
    failure = None

    def get_workspace(self, **kwargs):
        if self.failure:
            raise self.failure
        assert kwargs["tenant_id"] == "tenant-1"
        assert kwargs["clearance_rank"] == 30
        assert kwargs["role_ids"] == {"risk-role"}
        return workspace()


def client(service: FakeReportService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(
        tenant_id="tenant-1",
        user=SimpleNamespace(
            id="user-1",
            full_name="Payments Risk Presenter",
            email="presenter@example.test",
        ),
        membership=SimpleNamespace(clearance_rank=30),
        role_ids={"risk-role"},
        permissions={"decision.view", "decision.evidence.view"},
    )
    return TestClient(app)


def test_decision_brief_download_is_confidential_and_governed():
    result = client(FakeReportService()).get(
        "/decisions/decision-1/reports/decision-brief.pdf"
    )

    assert result.status_code == 200
    assert result.headers["content-type"] == "application/pdf"
    assert result.headers["cache-control"] == "private, no-store"
    assert "attachment" in result.headers["content-disposition"]
    reader = PdfReader(BytesIO(result.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "CONFIDENTIAL" in text
    assert "DecisionVault™, a DiscoverA.ai Technology" in text
    assert "CRITICAL SIGNAL DETECTED" in text
    assert "$186,000 attempted exposure" in text
    assert "Final approval remains human-controlled" in text


def test_unauthorized_decision_report_is_non_disclosing_not_found():
    service = FakeReportService()
    service.failure = DecisionNotFoundError("Decision not found")

    result = client(service).get(
        "/decisions/restricted/reports/decision-brief.pdf"
    )

    assert result.status_code == 404
    assert result.json() == {"detail": "Decision not found"}
