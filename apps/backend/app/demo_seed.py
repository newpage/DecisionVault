"""Deterministic synthetic portfolio for the isolated payments demonstration."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    AccessPolicy,
    AccessPolicyRole,
    AuditEvent,
    BusinessConcept,
    DecisionCase,
    DecisionEffectivenessAssessment,
    DecisionEvidence,
    DecisionLesson,
    DecisionLessonAdoption,
    DecisionLessonEvaluation,
    DecisionPrecedentEvaluation,
    DecisionPrecedentReference,
    KnowledgeCard,
    KnowledgeChunk,
    KnowledgeEvidence,
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    SourceDocument,
    Tenant,
    User,
    Workspace,
    utcnow,
)


PERMISSIONS = [
    "workspace.manage",
    "knowledge.create",
    "knowledge.submit",
    "knowledge.approve",
    "decision.create",
    "decision.view",
    "decision.edit",
    "decision.transition",
    "decision.evidence.view",
    "decision.evidence.select",
    "decision.evidence.remove",
    "decision.evidence.history",
    "decision.review.view",
    "decision.review.assign",
    "decision.review.perform",
    "decision.review.manage",
    "decision.approve",
    "decision.conditionally_approve",
    "decision.reject",
    "decision.return_for_changes",
    "decision.outcome.view",
    "decision.outcome.define",
    "decision.outcome.record",
    "decision.outcome.verify",
    "decision.outcome.assess",
    "decision.lesson.record",
    "decision.memory.view",
    "decision.precedent.view",
    "decision.precedent.manage",
    "decision.lesson.adopt",
    "decision.lesson.reject",
    "decision.learning.view",
    "decision.learning.evaluate",
    "decision.learning.manage",
    "decision.lesson.promotion.view",
    "decision.lesson.promote",
    "decision.lesson.promotion.review",
    "admin.manage",
]

CURRENT_ID = "10000000-0000-4000-8000-000000000001"
RESTRICTED_ID = "10000000-0000-4000-8000-000000000099"


CARD_DATA = [
    (
        "Merchant profile and processing forecast",
        "payments_merchant_profile",
        "merchant_application",
        0.88,
        "Northstar is an 18-month-old US digital-goods marketplace projecting $8.4M monthly volume, a $86 average ticket, 42,300 monthly transactions, 67% recent growth, and 31% card-not-present cross-border volume.",
        ["$8.4M projected monthly volume", "$86 average ticket", "67% recent growth", "31% CNP cross-border"],
    ),
    (
        "KYB and beneficial-owner verification",
        "payments_kyb",
        "kyb_case_file",
        0.96,
        "Registration and tax identity are verified. Owners representing 75% are verified. Identity and residential-address evidence remain incomplete for one owner holding 25%.",
        ["Entity verified", "75% ownership verified", "25% beneficial owner incomplete"],
    ),
    (
        "Fraud telemetry — 90-day review",
        "payments_fraud",
        "fraud_monitoring",
        0.93,
        "Fraud telemetry shows 3.9x card-testing attempts, a 14.7% device-sharing cluster, and velocity spikes from 02:00–05:00 UTC. The merchant narrative reports no material anomaly.",
        ["3.9x card-testing attempts", "14.7% device-sharing cluster", "overnight velocity spikes"],
    ),
    (
        "Chargeback monitoring report",
        "payments_chargebacks",
        "network_monitoring",
        0.98,
        "Chargebacks increased from 0.62% to 1.48% in 90 days. Fraud-coded disputes represent 58% and are concentrated in cross-border digital-goods cohorts.",
        ["0.62% to 1.48% chargebacks", "58% fraud-coded", "cross-border concentration"],
    ),
    (
        "AML transaction-monitoring review",
        "payments_aml",
        "aml_review",
        0.91,
        "The expected-activity profile is incomplete. Monitoring flags unusual corridor growth, but the available evidence does not establish a suspicious-activity conclusion.",
        ["Expected activity incomplete", "unusual corridor growth", "no confirmed suspicious-activity conclusion"],
    ),
    (
        "Sanctions and watchlist screening",
        "payments_sanctions",
        "screening_record",
        0.97,
        "Northstar and all verified owners have no sanctions or watchlist matches. Final screening cannot be completed for the unresolved 25% beneficial owner.",
        ["Entity clear", "Verified owners clear", "Unresolved owner not finally screened"],
    ),
    (
        "Merchant acquiring risk policy",
        "payments_policy",
        "approved_policy",
        0.99,
        "Chargebacks above 1.0% require enhanced review. An unresolved 25% beneficial owner blocks unconditional approval. Conditional approval may require a 10% rolling reserve, $5M monthly cap, cross-border restrictions, enhanced fraud monitoring, and 30-day KYB remediation.",
        ["1.0% chargeback threshold", "UBO completion required", "Conditional controls permitted"],
    ),
]


HISTORICAL = [
    ("Harbor Home Goods", "approved", "met", "low", "Successful approval; chargebacks stabilized at 0.71%.", 26),
    ("Vela Digital Media", "conditionally_approved", "exceeded", "high", "Successful under a 10% reserve and $5M volume cap.", 24),
    ("Orbit Tickets Online", "closed", "did_not_meet", "critical", "Conditional approval failed; chargebacks later reached 2.3%.", 22),
    ("Meridian Supplements", "rejected", "met", "high", "Rejected because unresolved UBO and AML contradictions remained material.", 20),
    ("Atlas Marketplace", "conditionally_approved", "partially_met", "high", "Restricted processing; account takeover differed from Northstar card testing.", 18),
    ("CipherPay Aggregator", "closed", "did_not_meet", "critical", "Restricted historical case for authorized risk leadership only.", 16),
]


def _assessment(tenant_id, decision_id, member_id, classification, rationale):
    return DecisionEffectivenessAssessment(
        tenant_id=tenant_id,
        decision_case_id=decision_id,
        revision=1,
        status="completed",
        assessment_date=date.today(),
        assessor_membership_id=member_id,
        classification=classification,
        rationale=rationale,
        outcome_summary=rationale,
        completed_at=datetime.now(timezone.utc),
    )


def seed_payments_demo(db: Session) -> None:
    if db.scalar(select(Tenant.id).limit(1)):
        return

    tenant = Tenant(slug=settings.demo_tenant_slug, name="Global Payments Demo")
    presenter = User(
        email=settings.demo_email,
        full_name="Payments Risk Demo Presenter",
        password_hash=hash_password(settings.demo_password),
    )
    analyst = User(
        email="analyst@globalpayments.demo",
        full_name="Merchant Risk Analyst",
        password_hash=hash_password(settings.demo_password),
    )
    db.add_all([tenant, presenter, analyst])
    db.flush()
    organization = Organization(
        tenant_id=tenant.id, name="Global Payments", code="GP-DEMO"
    )
    db.add(organization)
    db.flush()
    presenter_member = Membership(
        tenant_id=tenant.id,
        organization_id=organization.id,
        user_id=presenter.id,
        clearance_rank=80,
    )
    analyst_member = Membership(
        tenant_id=tenant.id,
        organization_id=organization.id,
        user_id=analyst.id,
        clearance_rank=60,
    )
    db.add_all([presenter_member, analyst_member])
    db.flush()
    presenter_role = Role(
        tenant_id=tenant.id, code="payments_demo_presenter", name="Payments Demo Presenter"
    )
    analyst_role = Role(
        tenant_id=tenant.id, code="merchant_risk_analyst", name="Merchant Risk Analyst"
    )
    permissions = [Permission(code=code, description=code) for code in PERMISSIONS]
    db.add_all([presenter_role, analyst_role, *permissions])
    db.flush()
    db.add_all(
        [
            MembershipRole(membership_id=presenter_member.id, role_id=presenter_role.id),
            MembershipRole(membership_id=analyst_member.id, role_id=analyst_role.id),
            *[
                RolePermission(role_id=role.id, permission_id=permission.id)
                for role in (presenter_role, analyst_role)
                for permission in permissions
            ],
        ]
    )
    restricted_policy = AccessPolicy(
        tenant_id=tenant.id, name="Payments Risk Leadership"
    )
    db.add(restricted_policy)
    db.flush()
    db.add(
        AccessPolicyRole(policy_id=restricted_policy.id, role_id=presenter_role.id)
    )
    workspace = Workspace(
        tenant_id=tenant.id,
        organization_id=organization.id,
        name="Merchant Acquiring Risk",
        description="Governed merchant underwriting, fraud, AML, and portfolio decisions.",
    )
    concept = BusinessConcept(
        tenant_id=tenant.id,
        name="Merchant Acquiring",
        slug="supplier-qualification",
        description="Merchant onboarding, transaction risk, fraud, chargebacks, KYB, AML, sanctions, and approval controls.",
        category="Payments Risk",
        icon="CreditCard",
        color="#4f7cff",
    )
    db.add_all([workspace, concept])
    db.flush()

    cards = []
    for index, (title, kind, authority, trust, summary, facts) in enumerate(CARD_DATA):
        source = SourceDocument(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            filename=f"{index + 1:02d}-{kind.replace('payments_', '')}.json",
            mime_type="application/json",
            storage_key=f"{tenant.id}/payments-demo/{index + 1:02d}.json",
            status="processed",
            created_by=presenter.id,
        )
        db.add(source)
        db.flush()
        structured = {
            "extraction_mode": "deterministic synthetic document extraction",
            "facts": facts,
            "provenance": source.filename,
            "review_status": "human reviewed and published",
        }
        card = KnowledgeCard(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            business_concept_id=concept.id,
            title=title,
            summary=summary,
            body=json.dumps(structured),
            knowledge_type=kind,
            lifecycle_status="published",
            approval_status="approved",
            authority_level=authority,
            classification_rank=30,
            ai_usage_allowed=True,
            trust_score=trust,
            owner_id=presenter.id,
            approved_by=presenter.id,
            approved_at=utcnow(),
        )
        db.add(card)
        db.flush()
        chunk = KnowledgeChunk(
            tenant_id=tenant.id,
            knowledge_card_id=card.id,
            content=summary,
            chunk_index=0,
            search_text=f"{title} {summary}".lower(),
        )
        db.add(chunk)
        db.flush()
        db.add(
            KnowledgeEvidence(
                tenant_id=tenant.id,
                knowledge_card_id=card.id,
                source_document_id=source.id,
                locator="Synthetic source document · structured extraction",
                excerpt=summary,
            )
        )
        cards.append((card, chunk, source))

    analysis = {
        "mode": "Deterministic analysis from governed synthetic evidence",
        "facts": [
            "Chargebacks rose from 0.62% to 1.48% in 90 days.",
            "Fraud-coded disputes are 58% of chargebacks.",
            "Card-testing attempts are 3.9x baseline.",
            "A 25% beneficial owner remains unverified.",
            "Verified parties have no sanctions matches.",
        ],
        "conflicts": [
            "Merchant narrative reports no material anomaly; governed telemetry shows card testing, device sharing, and overnight velocity spikes.",
            "Sanctions screening is clear for verified parties, but final disposition is incomplete for the unresolved owner.",
        ],
        "risks": [
            "Chargeback exposure exceeds the 1.0% enhanced-review threshold.",
            "Rapid volume growth may amplify fraud and operational losses.",
            "Cross-border digital-goods concentration increases dispute and monitoring complexity.",
        ],
        "missing_information": [
            "Identity and address evidence for the remaining 25% beneficial owner.",
            "Completed expected-activity profile and corridor rationale.",
            "Merchant response to card-testing and device-sharing telemetry.",
        ],
        "assumptions": [
            "Projected volume and transaction mix remain merchant-supplied until reconciled to processor history.",
            "No confirmed suspicious activity or sanctions match is inferred from incomplete evidence.",
        ],
        "recommendation": "Conditionally approve with restrictions; do not grant unconditional approval.",
        "controls": [
            "10% rolling reserve",
            "$5M monthly processing cap",
            "Restrict high-risk cross-border digital-goods corridors",
            "Enhanced fraud and chargeback monitoring",
            "Complete UBO and expected-activity remediation within 30 days",
            "Human risk-committee approval before activation",
        ],
        "citations": [
            "Chargeback monitoring report",
            "Fraud telemetry — 90-day review",
            "KYB and beneficial-owner verification",
            "AML transaction-monitoring review",
            "Sanctions and watchlist screening",
            "Merchant acquiring risk policy",
        ],
        "accountability": "AI supports retrieval, comparison, gap identification, and explanation. An accountable human must approve, restrict, or reject the merchant.",
    }
    current = DecisionCase(
        id=CURRENT_ID,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        business_concept_id=concept.id,
        classification_rank=30,
        title="Northstar merchant acquiring decision",
        question="Should Northstar Digital Commerce be approved, conditionally approved, restricted, or rejected for merchant acquiring?",
        status="evidence_collection",
        recommendation=analysis["recommendation"],
        confidence=0.89,
        supplier_name="Northstar Digital Commerce LLC",
        supplier_category="Digital-goods marketplace merchant",
        supplier_location="Austin, Texas · US and cross-border CNP",
        owner_name="Merchant Risk Committee",
        due_date=date.today(),
        priority="critical",
        risk_level="critical",
        decision_type="initial_qualification",
        business_unit="Merchant Acquiring Risk",
        readiness_score=89,
        readiness_status="review_required",
        evidence_summary={
            "missing_information": analysis["missing_information"],
            "control_areas": [
                "Merchant profile and processing model",
                "Fraud and transaction behavior",
                "Chargeback exposure",
                "KYC/KYB and beneficial ownership",
                "AML and sanctions",
                "Approval controls and accountability",
            ],
            "calculation": {
                "governed_evidence": {"points": 40, "possible": 40, "count": 7},
                "source_trust": {"points": 27, "possible": 30, "count": 7},
                "risk_coverage": {"points": 16, "possible": 20, "count": 6},
                "citation_readiness": {"points": 6, "possible": 10, "count": 6},
            },
            "demo_analysis": analysis,
        },
        created_by=presenter.id,
    )
    db.add(current)
    db.flush()
    relationships = ["contextual", "constraint", "risk", "risk", "risk", "supporting", "constraint"]
    for (card, chunk, source), relationship in zip(cards, relationships, strict=True):
        db.add(
            DecisionEvidence(
                tenant_id=tenant.id,
                decision_case_id=current.id,
                knowledge_card_id=card.id,
                knowledge_chunk_id=chunk.id,
                source_document_id=source.id,
                relationship_type=relationship,
                selection_rationale=f"Governed {relationship} evidence for the Northstar underwriting decision.",
                snapshot_title=card.title,
                snapshot_content=card.summary,
                snapshot_source_filename=source.filename,
                snapshot_source_mime_type=source.mime_type,
                snapshot_source_locator="Synthetic demo portfolio",
                snapshot_knowledge_type=card.knowledge_type,
                snapshot_authority_level=card.authority_level,
                snapshot_lifecycle_status=card.lifecycle_status,
                snapshot_approval_status=card.approval_status,
                snapshot_classification_rank=card.classification_rank,
                snapshot_access_policy_id=card.access_policy_id,
                snapshot_trust_score=card.trust_score,
                snapshot_ai_usage_allowed=card.ai_usage_allowed,
                snapshot_card_created_at=card.created_at,
                snapshot_content_revision="payments-demo-v1",
                snapshot_source_metadata={"synthetic": True, "demo": "global-payments"},
                selected_by=presenter.id,
            )
        )

    historical_rows = []
    for index, (name, status, effectiveness, risk, summary, age) in enumerate(HISTORICAL):
        restricted = name == "CipherPay Aggregator"
        row = DecisionCase(
            id=RESTRICTED_ID if restricted else None,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            business_concept_id=concept.id,
            classification_rank=50 if restricted else 30,
            access_policy_id=restricted_policy.id if restricted else None,
            title=f"{name} merchant underwriting",
            question=f"Should {name} receive merchant acquiring approval?",
            status=status,
            recommendation=summary,
            confidence=0.82,
            supplier_name=name,
            supplier_category="Card-not-present merchant",
            supplier_location="United States · cross-border activity",
            owner_name="Merchant Risk Committee",
            priority="high",
            risk_level=risk,
            decision_type="initial_qualification",
            business_unit="Merchant Acquiring Risk",
            readiness_score=82,
            readiness_status="ready",
            evidence_summary={"historical_record": "Pre-seeded synthetic outcome"},
            created_by=presenter.id,
            created_at=datetime(2026, 7, max(1, age), tzinfo=timezone.utc),
        )
        db.add(row)
        db.flush()
        db.add(_assessment(tenant.id, row.id, presenter_member.id, effectiveness, summary))
        lesson = DecisionLesson(
            tenant_id=tenant.id,
            decision_case_id=row.id,
            lesson_type="risk" if effectiveness == "did_not_meet" else "governance",
            description=(
                "Rapid growth does not offset unresolved transaction-risk signals."
                if name == "Orbit Tickets Online"
                else f"{name}: {summary}"
            ),
            business_impact=summary,
            created_by_membership_id=presenter_member.id,
        )
        db.add(lesson)
        db.flush()
        historical_rows.append((row, lesson, effectiveness, summary))

    current_assessment = _assessment(
        tenant.id,
        current.id,
        presenter_member.id,
        "partially_met",
        "Synthetic current effectiveness anchor used only for governed learning demonstration records.",
    )
    db.add(current_assessment)
    db.flush()
    precedent_classes = ["useful", "highly_useful", "harmful", "useful", "misleading"]
    lesson_classes = ["beneficial", "beneficial", "ineffective", "appropriate_rejection", "neutral"]
    for index, ((historical, lesson, effectiveness, summary), precedent_class, lesson_class) in enumerate(
        zip(historical_rows[:5], precedent_classes, lesson_classes, strict=True)
    ):
        reference = DecisionPrecedentReference(
            tenant_id=tenant.id,
            decision_case_id=current.id,
            historical_decision_id=historical.id,
            relationship_type="cautionary" if precedent_class in {"harmful", "misleading"} else "analogous",
            rationale=f"Pre-seeded historical comparison: {summary}",
            similarity_algorithm_version="decision_similarity_v1",
            similarity_score=88 - index * 3,
            similarity_components={"demo": "deterministic structural comparison"},
            snapshot_business_concept_id=concept.id,
            snapshot_business_concept_name=concept.name,
            snapshot_historical_title=historical.title,
            snapshot_historical_status=historical.status,
            snapshot_outcome_classification=effectiveness,
            snapshot_effectiveness_summary=summary,
            referenced_by_membership_id=presenter_member.id,
        )
        db.add(reference)
        db.flush()
        db.add(
            DecisionPrecedentEvaluation(
                tenant_id=tenant.id,
                decision_case_id=current.id,
                precedent_reference_id=reference.id,
                historical_decision_id=historical.id,
                effectiveness_assessment_id=current_assessment.id,
                classification=precedent_class,
                rationale=f"Pre-seeded observed usefulness: {precedent_class}; {summary}",
                evaluator_membership_id=presenter_member.id,
                similarity_score_snapshot=reference.similarity_score,
                historical_effectiveness_snapshot=effectiveness,
                current_effectiveness_snapshot=current_assessment.classification,
                outcome_alignment_details={"record_type": "pre-seeded historical evaluation"},
            )
        )
        adoption_status = "rejected" if lesson_class == "appropriate_rejection" else "adopted"
        adoption = DecisionLessonAdoption(
            tenant_id=tenant.id,
            decision_case_id=current.id,
            historical_decision_id=historical.id,
            historical_lesson_id=lesson.id,
            status=adoption_status,
            rationale=f"Pre-seeded {adoption_status} lesson choice for demonstration.",
            application_note="Recorded historical organizational learning; not an AI action.",
            snapshot_lesson_type=lesson.lesson_type,
            snapshot_lesson_description=lesson.description,
            snapshot_lesson_business_impact=lesson.business_impact,
            acted_by_membership_id=presenter_member.id,
        )
        db.add(adoption)
        db.flush()
        db.add(
            DecisionLessonEvaluation(
                tenant_id=tenant.id,
                decision_case_id=current.id,
                lesson_adoption_id=adoption.id,
                historical_decision_id=historical.id,
                effectiveness_assessment_id=current_assessment.id,
                classification=lesson_class,
                rationale=f"Pre-seeded observed lesson result: {lesson_class}.",
                was_applied=adoption_status == "adopted",
                relevant_outcome_ids=[],
                evaluator_membership_id=presenter_member.id,
                current_effectiveness_snapshot=current_assessment.classification,
                outcome_relevance_details={"record_type": "pre-seeded historical evaluation"},
            )
        )

    db.add_all(
        [
            AuditEvent(
                tenant_id=tenant.id,
                actor_id=presenter.id,
                event_type="PaymentsDemoPortfolioSeeded",
                entity_type="decision_case",
                entity_id=current.id,
                description="Deterministic synthetic payments demonstration portfolio created.",
                details={"synthetic": True, "profile": "payments", "cards": len(cards)},
            ),
            AuditEvent(
                tenant_id=tenant.id,
                actor_id=presenter.id,
                event_type="DeterministicAnalysisPrepared",
                entity_type="decision_case",
                entity_id=current.id,
                description="Grounded deterministic evidence picture prepared for human review.",
                details={"live_ai": False, "citations": analysis["citations"]},
            ),
        ]
    )
    db.commit()
