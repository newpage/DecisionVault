from datetime import datetime, timedelta, timezone

from app.modules.decisions.memory import (
    ALGORITHM_VERSION,
    DecisionMemoryProfile,
    compare_profiles,
)
from app.modules.decisions.policies import DecisionPermissionError, authorize_memory_view
import pytest


NOW = datetime(2026, 8, 6, tzinfo=timezone.utc)


def profile(**changes):
    values = dict(
        decision_id="decision",
        business_concept_id="concept-1",
        workspace_id="workspace-1",
        title="Qualify strategic supplier",
        question="Should we qualify the strategic electronics supplier?",
        decision_type="initial_qualification",
        business_unit="Supply Chain",
        supplier_category="Electronic Manufacturer",
        risk_level="medium",
        created_at=NOW - timedelta(days=30),
        evidence_types=frozenset({"policy", "assessment"}),
        evidence_authorities=frozenset({"sop", "quality_record"}),
        evidence_relationships=frozenset({"supporting", "risk"}),
        review_types=frozenset({"risk", "final_approval"}),
        finding_types=frozenset({"risk_concern"}),
        approval_actions=frozenset({"approved"}),
        condition_statuses=frozenset(),
        outcome_categories=frozenset({"business"}),
        outcome_measurements=frozenset({"duration"}),
        effectiveness_classification="met",
        lesson_types=frozenset({"execution", "risk"}),
    )
    values.update(changes)
    return DecisionMemoryProfile(**values)


def test_exact_characteristics_return_versioned_strong_relevance():
    result = compare_profiles(profile(), profile(decision_id="historical"), now=NOW)
    assert result["algorithm_version"] == ALGORITHM_VERSION
    assert result["relevance"] == "strongly_relevant"
    assert result["overall_similarity"] > 95
    assert result["components"]["business_concept"]["score"] == 1


def test_same_and_different_business_concepts_are_explicit():
    same = compare_profiles(profile(), profile(decision_id="same"), now=NOW)
    different = compare_profiles(
        profile(), profile(decision_id="different", business_concept_id="concept-2"), now=NOW
    )
    assert same["components"]["business_concept"]["score"] == 1
    assert different["components"]["business_concept"]["score"] == 0
    assert "Different Business Concepts" in different["components"]["business_concept"]["explanation"]


def test_similar_and_opposing_evidence_profiles_are_independent():
    similar = compare_profiles(profile(), profile(decision_id="similar", evidence_types=frozenset({"policy", "assessment", "guidance"})), now=NOW)
    opposing = compare_profiles(profile(), profile(decision_id="opposing", evidence_types=frozenset({"contract"}), evidence_authorities=frozenset({"external"}), evidence_relationships=frozenset({"opposing"})), now=NOW)
    assert similar["components"]["evidence_profile"]["score"] > opposing["components"]["evidence_profile"]["score"]
    assert opposing["components"]["evidence_profile"]["score"] == 0


def test_similar_and_different_text():
    similar = compare_profiles(profile(), profile(decision_id="similar", title="Strategic supplier qualification"), now=NOW)
    different = compare_profiles(profile(), profile(decision_id="different", title="Retire payroll software", question="Should payroll software be retired?"), now=NOW)
    assert similar["components"]["decision_text"]["score"] > different["components"]["decision_text"]["score"]


def test_governance_outcomes_and_lessons_are_separate_from_similarity_desirability():
    failed = profile(
        decision_id="failed",
        approval_actions=frozenset({"approved"}),
        effectiveness_classification="did_not_meet",
        lesson_types=frozenset({"execution", "risk"}),
    )
    rejected = profile(
        decision_id="rejected",
        approval_actions=frozenset({"rejected"}),
        effectiveness_classification=None,
    )
    failed_result = compare_profiles(profile(), failed, now=NOW)
    rejected_result = compare_profiles(profile(), rejected, now=NOW)
    assert failed_result["overall_similarity"] >= 80
    assert "did_not_meet" in failed_result["components"]["outcome_profile"]["explanation"]
    assert rejected_result["components"]["governance_pattern"]["score"] < 1
    assert failed_result["components"]["lesson_overlap"]["score"] == 1


def test_recency_declines_without_hiding_old_precedent():
    recent = compare_profiles(profile(), profile(decision_id="recent", created_at=NOW - timedelta(days=10)), now=NOW)
    old = compare_profiles(profile(), profile(decision_id="old", created_at=NOW - timedelta(days=365 * 6)), now=NOW)
    assert recent["components"]["recency"]["score"] > old["components"]["recency"]["score"]
    assert old["components"]["recency"]["score"] == 0
    assert old["overall_similarity"] > 80


def test_missing_outcome_and_restricted_components_are_not_treated_as_mismatch():
    restricted = profile(decision_id="restricted", evidence_types=None, evidence_authorities=None, evidence_relationships=None, review_types=None, finding_types=None, approval_actions=None, condition_statuses=None, outcome_categories=None, outcome_measurements=None, effectiveness_classification=None, lesson_types=None)
    result = compare_profiles(restricted, restricted, now=NOW)
    assert result["components"]["evidence_profile"]["available"] is False
    assert result["components"]["outcome_profile"]["available"] is False
    assert result["overall_similarity"] > 90


def test_completely_unrelated_decision_is_weak():
    unrelated = profile(
        decision_id="unrelated",
        business_concept_id="other",
        workspace_id="other-workspace",
        title="Retire payroll software",
        question="Should a legacy payroll engine be retired?",
        decision_type="disqualification",
        business_unit="Human Resources",
        supplier_category="Software",
        risk_level="critical",
        evidence_types=frozenset({"contract"}),
        evidence_authorities=frozenset({"external"}),
        evidence_relationships=frozenset({"opposing"}),
        review_types=frozenset({"compliance"}),
        finding_types=frozenset({"policy_concern"}),
        approval_actions=frozenset({"rejected"}),
        outcome_categories=frozenset({"people"}),
        outcome_measurements=frozenset({"qualitative"}),
        lesson_types=frozenset({"governance"}),
        created_at=NOW - timedelta(days=365 * 6),
    )
    result = compare_profiles(profile(), unrelated, now=NOW)
    assert result["relevance"] == "weakly_relevant"
    assert result["overall_similarity"] < 40


def test_decision_memory_requires_explicit_permission():
    with pytest.raises(DecisionPermissionError) as caught:
        authorize_memory_view({"decision.view"})
    assert caught.value.permission == "decision.memory.view"
