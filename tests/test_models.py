"""Tests for the shared domain models."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import DiagnosisCategory, Invoice, InvoiceStatus


def make_invoice(**overrides: object) -> Invoice:
    values: dict[str, object] = {
        "invoice_id": "INV-001",
        "customer_name": "Example Customer",
        "customer_email": "ar@example.com",
        "amount": Decimal("12500.00"),
        "due_date": date(2026, 1, 15),
    }
    values.update(overrides)
    return Invoice(**values)


def test_valid_invoice_defaults_to_overdue() -> None:
    invoice = make_invoice()

    assert invoice.status is InvoiceStatus.OVERDUE
    assert invoice.touches == 0
    assert invoice.failed_attempts == 0
    assert invoice.broken_promises == 0
    assert invoice.recovered_amount == Decimal("0")


def test_only_approved_diagnosis_categories_exist() -> None:
    assert {category.value for category in DiagnosisCategory} == {
        "forgetful",
        "cash_flow_strapped",
        "disputed",
        "wrong_bounced_contact",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", Decimal("0")),
        ("amount", Decimal("-1")),
        ("touches", -1),
        ("failed_attempts", -1),
        ("broken_promises", -1),
    ],
)
def test_invalid_positive_or_counter_fields_are_rejected(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        make_invoice(**{field: value})


def test_recovered_amount_cannot_exceed_invoice_amount() -> None:
    with pytest.raises(ValidationError, match="recovered_amount"):
        make_invoice(recovered_amount=Decimal("12500.01"))


def test_promise_fields_must_be_supplied_together() -> None:
    with pytest.raises(ValidationError, match="supplied together"):
        make_invoice(promise_to_pay_date=date(2026, 2, 1))


def test_promise_fields_can_be_supplied_together() -> None:
    invoice = make_invoice(
        promise_to_pay_date=date(2026, 2, 1),
        promise_to_pay_amount=Decimal("5000"),
    )

    assert invoice.promise_to_pay_amount == Decimal("5000")


def test_invoice_serializes_to_json_compatible_data() -> None:
    data = make_invoice(diagnosis=DiagnosisCategory.FORGETFUL).model_dump(mode="json")

    assert data["status"] == "overdue"
    assert data["diagnosis"] == "forgetful"
    assert data["amount"] == "12500.00"
