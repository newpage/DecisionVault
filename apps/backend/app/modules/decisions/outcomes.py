from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class OutcomeCalculationInput:
    measurement_type: str
    target_direction: str
    baseline: Decimal | None = None
    target: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_boolean: bool | None = None
    actual: Decimal | None = None
    actual_boolean: bool | None = None
    observed_status: str | None = None
    verified: bool = False
    target_date: date | None = None
    evaluation_date: date | None = None


def calculate_outcome(value: OutcomeCalculationInput) -> dict[str, Any]:
    result: dict[str, Any] = {
        "assessable": False,
        "target_met": None,
        "verification_status": "verified" if value.verified else "unverified",
        "target_value": _number(value.target),
        "actual_value": _number(value.actual),
        "variance": None,
        "variance_percentage": None,
        "explanation": "",
    }
    if (
        value.evaluation_date
        and value.target_date
        and value.evaluation_date < value.target_date
    ):
        result["explanation"] = "The target date has not been reached."
        result["timing"] = "too_early"
        return result
    if not value.verified:
        result["explanation"] = "A verified observation is required."
        return result

    if value.measurement_type in {"boolean", "milestone"}:
        actual = (
            value.actual_boolean
            if value.measurement_type == "boolean"
            else value.observed_status == "achieved"
        )
        target = value.target_boolean if value.measurement_type == "boolean" else True
        if actual is None:
            result["explanation"] = "The observation has no assessable value."
            return result
        result.update(
            assessable=True,
            target_met=actual == target,
            actual_value=actual,
            target_value=target,
            explanation=f"Observed condition {'matches' if actual == target else 'does not match'} the governed target.",
        )
        return result

    if value.measurement_type == "qualitative":
        result["explanation"] = (
            "Qualitative outcomes require governed assessor classification."
        )
        return result

    if value.actual is None:
        result["explanation"] = "The verified observation has no numeric value."
        return result

    met: bool | None = None
    if value.target_direction == "range":
        if value.target_min is not None and value.target_max is not None:
            met = value.target_min <= value.actual <= value.target_max
            result["target_value"] = {
                "minimum": _number(value.target_min),
                "maximum": _number(value.target_max),
            }
    elif value.target is not None:
        met = {
            "increase": value.actual >= value.target,
            "decrease": value.actual <= value.target,
            "exact": value.actual == value.target,
            "maintain": value.actual == value.target,
        }.get(value.target_direction)
        variance = value.actual - value.target
        result["variance"] = _number(variance)
        if value.target != 0:
            result["variance_percentage"] = _number(variance / abs(value.target) * 100)
    if met is None:
        result["explanation"] = "The governed target is incomplete."
        return result
    result.update(
        assessable=True,
        target_met=met,
        explanation=f"Verified actual {_number(value.actual)} {'meets' if met else 'does not meet'} the {value.target_direction} target.",
    )
    return result


def aggregate_outcomes(items: list[dict[str, Any]]) -> dict[str, Any]:
    assessable = [item for item in items if item["calculation"]["assessable"]]
    missing = len(items) - len(assessable)
    total_weight = sum(Decimal(str(item["weight"])) for item in assessable)
    met_weight = sum(
        Decimal(str(item["weight"]))
        for item in assessable
        if item["calculation"]["target_met"]
    )
    critical_failure = any(
        item["critical"] and item["calculation"]["target_met"] is False
        for item in assessable
    )
    ratio = met_weight / total_weight if total_weight else None
    if critical_failure:
        classification = "did_not_meet"
    elif not assessable:
        classification = "inconclusive"
    elif missing:
        classification = "inconclusive"
    elif ratio == 1:
        classification = "met"
    elif ratio and ratio >= Decimal("0.5"):
        classification = "partially_met"
    else:
        classification = "did_not_meet"
    return {
        "classification": classification,
        "weighted_target_met_ratio": _number(ratio * 100)
        if ratio is not None
        else None,
        "assessable_count": len(assessable),
        "missing_count": missing,
        "critical_failure": critical_failure,
        "formula": "sum(weights of verified targets met) / sum(weights of verified assessable outcomes)",
    }


def _number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
