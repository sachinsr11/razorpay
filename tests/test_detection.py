"""Tests for overdue invoice detection."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine.detector import detect_invoices
from app.models import AgingBucket, Invoice, InvoiceStatus


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def make_invoice(invoice_id: str, due_date: date, **overrides: object) -> Invoice:
    values: dict[str, object] = {
        "invoice_id": invoice_id,
        "customer_name": "Example Customer",
        "customer_email": "ar@example.com",
        "amount": Decimal("1000"),
        "due_date": due_date,
    }
    values.update(overrides)
    return Invoice(**values)


@pytest.mark.parametrize(
    "overdue_days,expected_bucket",
    [
        (1, AgingBucket.DAYS_1_7),
        (7, AgingBucket.DAYS_1_7),
        (8, AgingBucket.DAYS_8_30),
        (30, AgingBucket.DAYS_8_30),
        (31, AgingBucket.DAYS_30_PLUS),
    ],
)
def test_detection_assigns_boundary_buckets(
    overdue_days: int, expected_bucket: AgingBucket
) -> None:
    invoice = make_invoice(
        "INV-001",
        NOW.date() - timedelta(days=overdue_days),
    )

    cases = detect_invoices([invoice], NOW)

    assert len(cases) == 1
    assert cases[0].overdue_days == overdue_days
    assert cases[0].aging_bucket is expected_bucket


def test_future_and_due_today_invoices_are_not_detected() -> None:
    invoices = [
        make_invoice("FUTURE", date(2026, 9, 6)),
        make_invoice("TODAY", date(2026, 9, 5)),
    ]

    assert detect_invoices(invoices, NOW) == []


def test_non_overdue_statuses_are_not_detected() -> None:
    invoice = make_invoice(
        "PAID",
        date(2026, 9, 1),
        status=InvoiceStatus.PAID,
    )

    assert detect_invoices([invoice], NOW) == []


def test_detection_keeps_ineligible_overdue_cases_with_reasons() -> None:
    invoice = make_invoice("TOUCHED", date(2026, 9, 1), touches=3)

    cases = detect_invoices([invoice], NOW)

    assert len(cases) == 1
    assert cases[0].compliance.eligible is False
    assert "touch cap" in cases[0].compliance.reasons[0]
