from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


ALGORITHM_VERSION = "decision_similarity_v1"
COMPONENT_WEIGHTS = {
    "business_concept": 0.20,
    "context": 0.10,
    "decision_text": 0.20,
    "evidence_profile": 0.20,
    "governance_pattern": 0.10,
    "outcome_profile": 0.10,
    "lesson_overlap": 0.05,
    "recency": 0.05,
}
RELEVANCE_THRESHOLDS = {
    "strongly_relevant": 80,
    "relevant": 60,
    "somewhat_relevant": 40,
    "weakly_relevant": 0,
}
TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
STOP_WORDS = frozenset({"a", "an", "and", "are", "for", "in", "is", "of", "or", "the", "to", "was", "were", "with"})


@dataclass(frozen=True)
class DecisionMemoryProfile:
    decision_id: str
    business_concept_id: str | None
    workspace_id: str
    title: str
    question: str
    decision_type: str
    business_unit: str
    supplier_category: str
    risk_level: str
    created_at: datetime
    evidence_types: frozenset[str] | None = None
    evidence_authorities: frozenset[str] | None = None
    evidence_relationships: frozenset[str] | None = None
    review_types: frozenset[str] | None = None
    finding_types: frozenset[str] | None = None
    approval_actions: frozenset[str] | None = None
    condition_statuses: frozenset[str] | None = None
    outcome_categories: frozenset[str] | None = None
    outcome_measurements: frozenset[str] | None = None
    effectiveness_classification: str | None = None
    lesson_types: frozenset[str] | None = None


def compare_profiles(current: DecisionMemoryProfile, historical: DecisionMemoryProfile, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    components = {
        "business_concept": _component(
            1.0 if current.business_concept_id and current.business_concept_id == historical.business_concept_id else 0.0,
            "Same Business Concept" if current.business_concept_id == historical.business_concept_id and current.business_concept_id else "Different Business Concepts",
        ),
        "context": _set_component(
            {current.workspace_id, current.decision_type, current.business_unit.lower(), current.supplier_category.lower(), current.risk_level},
            {historical.workspace_id, historical.decision_type, historical.business_unit.lower(), historical.supplier_category.lower(), historical.risk_level},
            "structured context",
        ),
        "decision_text": _set_component(_tokens(f"{current.title} {current.question}"), _tokens(f"{historical.title} {historical.question}"), "title and question terms"),
        "evidence_profile": _combined_sets(
            [(current.evidence_types, historical.evidence_types), (current.evidence_authorities, historical.evidence_authorities), (current.evidence_relationships, historical.evidence_relationships)],
            "evidence type, authority, and relationship profile",
        ),
        "governance_pattern": _combined_sets(
            [(current.review_types, historical.review_types), (current.finding_types, historical.finding_types), (current.approval_actions, historical.approval_actions), (current.condition_statuses, historical.condition_statuses)],
            "review, finding, approval, and condition pattern",
        ),
        "outcome_profile": _outcome_component(current, historical),
        "lesson_overlap": _set_component(current.lesson_types, historical.lesson_types, "lesson types"),
        "recency": _recency_component(historical.created_at, now),
    }
    available = {name: value for name, value in components.items() if value["available"]}
    available_weight = sum(COMPONENT_WEIGHTS[name] for name in available)
    overall = round(sum(value["score"] * COMPONENT_WEIGHTS[name] for name, value in available.items()) / available_weight * 100, 1) if available_weight else 0.0
    for name, value in components.items():
        value["weight"] = COMPONENT_WEIGHTS[name]
        value["weighted_points"] = round(value["score"] * COMPONENT_WEIGHTS[name] / available_weight * 100, 1) if value["available"] and available_weight else 0.0
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "overall_similarity": overall,
        "relevance": relevance_for_score(overall),
        "components": components,
        "shared_characteristics": _shared(current, historical),
        "different_characteristics": _different(current, historical),
    }


def relevance_for_score(score: float) -> str:
    for label, threshold in RELEVANCE_THRESHOLDS.items():
        if score >= threshold:
            return label
    return "weakly_relevant"


def _component(score: float, explanation: str, *, available: bool = True) -> dict[str, Any]:
    return {"score": round(score, 4), "available": available, "explanation": explanation}


def _set_component(left: frozenset[str] | set[str] | None, right: frozenset[str] | set[str] | None, label: str) -> dict[str, Any]:
    if left is None or right is None:
        return _component(0, f"{label.capitalize()} not included under current access", available=False)
    union = set(left) | set(right)
    score = len(set(left) & set(right)) / len(union) if union else 0.0
    shared = sorted(set(left) & set(right))
    explanation = (
        f"Shared {label}: {', '.join(shared)}"
        if shared
        else f"No comparable shared {label}"
    )
    return _component(score, explanation)


def _combined_sets(pairs, label: str) -> dict[str, Any]:
    values = [_set_component(left, right, label) for left, right in pairs]
    available = [value for value in values if value["available"]]
    if not available:
        return _component(0, f"{label.capitalize()} not included under current access", available=False)
    return _component(sum(value["score"] for value in available) / len(available), "; ".join(value["explanation"] for value in available))


def _outcome_component(current: DecisionMemoryProfile, historical: DecisionMemoryProfile) -> dict[str, Any]:
    base = _combined_sets([(current.outcome_categories, historical.outcome_categories), (current.outcome_measurements, historical.outcome_measurements)], "outcome category and measurement profile")
    if not base["available"]:
        return base
    if current.effectiveness_classification and historical.effectiveness_classification:
        same = current.effectiveness_classification == historical.effectiveness_classification
        base["score"] = round((base["score"] * 2 + (1.0 if same else 0.0)) / 3, 4)
        base["explanation"] += f"; effectiveness is {'the same' if same else 'different'} ({historical.effectiveness_classification})"
    elif historical.effectiveness_classification:
        base["explanation"] += f"; historical effectiveness: {historical.effectiveness_classification}"
    else:
        base["explanation"] += "; historical effectiveness is not yet assessed"
    return base


def _recency_component(created_at: datetime, now: datetime) -> dict[str, Any]:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0, (now - created_at).days)
    score = max(0.0, 1 - age_days / (365 * 5))
    return _component(score, f"Historical Decision is {age_days} days old; recency reaches zero after five years")


def _tokens(value: str) -> frozenset[str]:
    return frozenset(token for token in TOKEN_RE.findall(value.lower()) if token not in STOP_WORDS)


def _shared(current: DecisionMemoryProfile, historical: DecisionMemoryProfile) -> list[str]:
    shared = []
    if current.business_concept_id and current.business_concept_id == historical.business_concept_id:
        shared.append("Business Concept")
    if current.workspace_id == historical.workspace_id:
        shared.append("Workspace context")
    if current.decision_type == historical.decision_type:
        shared.append(f"Decision type: {current.decision_type}")
    return shared


def _different(current: DecisionMemoryProfile, historical: DecisionMemoryProfile) -> list[str]:
    differences = []
    if current.business_concept_id != historical.business_concept_id:
        differences.append("Business Concept differs")
    if current.risk_level != historical.risk_level:
        differences.append(f"Risk differs: current {current.risk_level}, historical {historical.risk_level}")
    if current.effectiveness_classification != historical.effectiveness_classification:
        differences.append("Effectiveness classification differs or is unavailable")
    return differences
