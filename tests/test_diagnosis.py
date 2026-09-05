"""Tests for diagnosis validation and parsing."""

from datetime import date
from decimal import Decimal

import pytest

from app.engine.diagnoser import DiagnosisError, Diagnoser
from app.models import DiagnosisCategory, Invoice


class FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        self.calls.append((prompt, system_prompt))
        return self.response


def make_invoice() -> Invoice:
    return Invoice(
        invoice_id="INV-001",
        customer_name="Example Customer",
        customer_email="ar@example.com",
        amount=Decimal("12500"),
        due_date=date(2026, 9, 1),
    )


@pytest.mark.parametrize("category", list(DiagnosisCategory))
def test_all_approved_categories_are_accepted(category: DiagnosisCategory) -> None:
    fake = FakeClient(
        f'{{"category": "{category.value}", "reasoning": "customer context"}}'
    )

    result = Diagnoser(fake).diagnose(make_invoice())

    assert result.category is category
    assert result.reasoning == "customer context"


def test_markdown_json_is_accepted_and_prompt_contains_invoice_context() -> None:
    fake = FakeClient(
        '```json\n{"category":"forgetful","reasoning":"missed reminder"}\n```'
    )

    result = Diagnoser(fake).diagnose(make_invoice())

    assert result.category is DiagnosisCategory.FORGETFUL
    assert "INV-001" in fake.calls[0][0]
    assert fake.calls[0][1] is not None


@pytest.mark.parametrize(
    "response,expected_message",
    [
        ('{"category":"dissatisfied","reasoning":"reason"}', "approved"),
        ('{"category":"forgetful"}', "reasoning"),
        ("not json", "JSON"),
    ],
)
def test_invalid_diagnosis_responses_fail_closed(
    response: str, expected_message: str
) -> None:
    with pytest.raises(DiagnosisError, match=expected_message):
        Diagnoser(FakeClient(response)).diagnose(make_invoice())
