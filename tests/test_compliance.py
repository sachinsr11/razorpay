"""Tests for deterministic compliance rules."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine.compliance import (
    COOLDOWN_DAYS,
    MAX_AUTOMATED_TOUCHES,
    MAX_CASE_AGE_DAYS,
    check_eligibility,
    is_within_business_hours,
)
from app.models import InterventionRung, Invoice, InvoiceStatus


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def make_invoice(**overrides: object) -> Invoice:
    values: dict[str, object] = {
        "invoice_id": "INV-001",
        "customer_name": "Example Customer",
        "customer_email": "ar@example.com",
        "amount": Decimal("1000"),
        "due_date": date(2026, 9, 1),
    }
    values.update(overrides)
    return Invoice(**values)


def test_overdue_invoice_is_eligible_during_business_hours() -> None:
    result = check_eligibility(make_invoice(), NOW)

    assert result.eligible is True
    assert result.reasons == ("eligible for automation",)


@pytest.mark.parametrize(
    "overrides,expected_reason",
    [
        ({"status": InvoiceStatus.PAID}, "invoice is not overdue"),
        ({"touches": MAX_AUTOMATED_TOUCHES}, "automated touch cap reached"),
        ({"intervention_rung": InterventionRung.RUNG_3}, "terminal rung 3"),
        (
            {
                "due_date": NOW.date() - timedelta(days=MAX_CASE_AGE_DAYS + 1)
            },
            "maximum age",
        ),
        (
            {"last_touch_at": datetime(2026, 9, 3, 12, tzinfo=timezone.utc)},
            "cooldown",
        ),
    ],
)
def test_blocking_conditions_make_invoice_ineligible(
    overrides: dict[str, object], expected_reason: str
) -> None:
    result = check_eligibility(make_invoice(**overrides), NOW)

    assert result.eligible is False
    assert any(expected_reason in reason for reason in result.reasons)


def test_cooldown_is_eligible_after_configured_days() -> None:
    invoice = make_invoice(
        last_touch_at=datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    )

    result = check_eligibility(invoice, NOW)

    assert result.eligible is True
    assert COOLDOWN_DAYS == 4


@pytest.mark.parametrize("hour", [0, 8, 18, 23])
def test_outside_business_hours_is_blocked(hour: int) -> None:
    now = NOW.replace(hour=hour)

    assert is_within_business_hours(now) is False
    assert check_eligibility(make_invoice(), now).eligible is False


@pytest.mark.parametrize("hour", [9, 12, 17])
def test_business_hours_include_start_and_exclude_end(hour: int) -> None:
    assert is_within_business_hours(NOW.replace(hour=hour)) is True
