from datetime import date
from decimal import Decimal

import pytest

from app.modules.decisions.outcomes import (
    OutcomeCalculationInput,
    aggregate_outcomes,
    calculate_outcome,
)


@pytest.mark.parametrize(
    ("direction", "actual", "target", "met"),
    [
        ("increase", "12", "10", True),
        ("increase", "8", "10", False),
        ("decrease", "8", "10", True),
        ("decrease", "12", "10", False),
        ("exact", "10", "10", True),
    ],
)
def test_numeric_target_directions(direction, actual, target, met):
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="numeric",
            target_direction=direction,
            target=Decimal(target),
            actual=Decimal(actual),
            verified=True,
        )
    )
    assert result["assessable"] is True
    assert result["target_met"] is met


def test_numeric_variance_and_percentage_are_explicit():
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="percentage",
            target_direction="increase",
            baseline=Decimal("40"),
            target=Decimal("50"),
            actual=Decimal("55"),
            verified=True,
        )
    )
    assert result["variance"] == 5.0
    assert result["variance_percentage"] == 10.0


def test_range_target():
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="duration",
            target_direction="range",
            target_min=Decimal("5"),
            target_max=Decimal("8"),
            actual=Decimal("6"),
            verified=True,
        )
    )
    assert result["target_met"] is True
    assert result["target_value"] == {"minimum": 5.0, "maximum": 8.0}


@pytest.mark.parametrize(
    ("measurement_type", "actual_boolean", "status", "met"),
    [
        ("boolean", True, None, True),
        ("boolean", False, None, False),
        ("milestone", None, "achieved", True),
    ],
)
def test_boolean_and_milestone_targets(measurement_type, actual_boolean, status, met):
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type=measurement_type,
            target_direction="complete"
            if measurement_type == "milestone"
            else "maintain",
            target_boolean=True,
            actual_boolean=actual_boolean,
            observed_status=status,
            verified=True,
        )
    )
    assert result["target_met"] is met


def test_qualitative_requires_governed_assessment():
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="qualitative",
            target_direction="maintain",
            verified=True,
        )
    )
    assert result["assessable"] is False
    assert "assessor" in result["explanation"]


@pytest.mark.parametrize("verified", [False, True])
def test_missing_actual_is_not_success(verified):
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="numeric",
            target_direction="increase",
            target=Decimal("10"),
            verified=verified,
        )
    )
    assert result["assessable"] is False
    assert result["target_met"] is None


def test_unverified_actual_is_not_authoritative():
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="numeric",
            target_direction="increase",
            target=Decimal("10"),
            actual=Decimal("20"),
            verified=False,
        )
    )
    assert result["assessable"] is False
    assert result["verification_status"] == "unverified"


def test_target_date_marks_too_early():
    result = calculate_outcome(
        OutcomeCalculationInput(
            measurement_type="numeric",
            target_direction="increase",
            target=Decimal("10"),
            actual=Decimal("20"),
            verified=True,
            target_date=date(2027, 1, 1),
            evaluation_date=date(2026, 1, 1),
        )
    )
    assert result["timing"] == "too_early"
    assert result["assessable"] is False


def test_weighted_aggregation_and_missing_data():
    result = aggregate_outcomes(
        [
            {
                "weight": 3,
                "critical": False,
                "calculation": {"assessable": True, "target_met": True},
            },
            {
                "weight": 1,
                "critical": False,
                "calculation": {"assessable": True, "target_met": False},
            },
        ]
    )
    assert result["classification"] == "partially_met"
    assert result["weighted_target_met_ratio"] == 75.0

    incomplete = aggregate_outcomes(
        [
            {
                "weight": 1,
                "critical": False,
                "calculation": {"assessable": False, "target_met": None},
            }
        ]
    )
    assert incomplete["classification"] == "inconclusive"


def test_critical_failure_overrides_weighted_success():
    result = aggregate_outcomes(
        [
            {
                "weight": 99,
                "critical": False,
                "calculation": {"assessable": True, "target_met": True},
            },
            {
                "weight": 1,
                "critical": True,
                "calculation": {"assessable": True, "target_met": False},
            },
        ]
    )
    assert result["classification"] == "did_not_meet"
    assert result["critical_failure"] is True
