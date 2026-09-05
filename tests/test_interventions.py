"""Tests for deterministic intervention selection."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine.detector import detect_invoices
from app.engine.interventions import InterventionAction, select_intervention
from app.models import DiagnosisCategory, InterventionRung, Invoice, InvoiceStatus


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def make_case(
    overdue_days: int,
    *,
    amount: str = "5000",
    failed_attempts: int = 0,
    touches: int = 0,
    rung: InterventionRung | None = None,
):
    invoice = Invoice(
        invoice_id="INV-001",
        customer_name="Example Customer",
        customer_email="ar@example.com",
        amount=Decimal(amount),
        due_date=NOW.date() - timedelta(days=overdue_days),
        failed_attempts=failed_attempts,
        touches=touches,
        intervention_rung=rung,
    )
    return detect_invoices([invoice], NOW)[0]


@pytest.mark.parametrize("overdue_days", [1, 7])
def test_early_cases_get_gentle_reminder(overdue_days: int) -> None:
    decision = select_intervention(
        make_case(overdue_days), DiagnosisCategory.FORGETFUL
    )

    assert decision.action is InterventionAction.GENTLE_REMINDER
    assert decision.rung is InterventionRung.RUNG_1
    assert decision.freeze_automation is False


@pytest.mark.parametrize("overdue_days", [8, 30, 31])
def test_later_low_value_cases_get_firm_payment_plan(overdue_days: int) -> None:
    decision = select_intervention(
        make_case(overdue_days), DiagnosisCategory.FORGETFUL
    )

    assert decision.action is InterventionAction.FIRM_REMINDER_PAYMENT_PLAN
    assert decision.rung is InterventionRung.RUNG_2


def test_cash_flow_diagnosis_forces_rung_two() -> None:
    decision = select_intervention(
        make_case(2), DiagnosisCategory.CASH_FLOW_STRAPPED
    )

    assert decision.action is InterventionAction.FIRM_REMINDER_PAYMENT_PLAN
    assert decision.rung is InterventionRung.RUNG_2


@pytest.mark.parametrize(
    "diagnosis",
    [DiagnosisCategory.DISPUTED, DiagnosisCategory.WRONG_BOUNCED_CONTACT],
)
def test_blocking_diagnoses_freeze_for_human_review(
    diagnosis: DiagnosisCategory,
) -> None:
    decision = select_intervention(make_case(2), diagnosis)

    assert decision.action is InterventionAction.FREEZE_HUMAN_REVIEW
    assert decision.freeze_automation is True
    assert decision.new_status is InvoiceStatus.FROZEN_HUMAN_REVIEW


def test_high_value_30_plus_case_handoffs_at_rung_three() -> None:
    decision = select_intervention(
        make_case(31, amount="10000.01"), DiagnosisCategory.FORGETFUL
    )

    assert decision.action is InterventionAction.AR_REP_HANDOFF
    assert decision.rung is InterventionRung.RUNG_3
    assert decision.new_status is InvoiceStatus.FROZEN_HUMAN_REVIEW


def test_two_failed_attempts_handoff_regardless_of_age_or_amount() -> None:
    decision = select_intervention(
        make_case(2, amount="100", failed_attempts=2),
        DiagnosisCategory.FORGETFUL,
    )

    assert decision.action is InterventionAction.AR_REP_HANDOFF
    assert decision.rung is InterventionRung.RUNG_3


def test_ineligible_case_gets_no_action_without_mutating_invoice() -> None:
    case = make_case(2, touches=3)

    decision = select_intervention(case, DiagnosisCategory.FORGETFUL)

    assert decision.action is InterventionAction.NO_ACTION
    assert decision.freeze_automation is False
    assert case.invoice.status is InvoiceStatus.OVERDUE


def test_terminal_case_gets_no_additional_action() -> None:
    case = make_case(31, rung=InterventionRung.RUNG_3)

    decision = select_intervention(case, DiagnosisCategory.FORGETFUL)

    assert decision.action is InterventionAction.NO_ACTION
    assert decision.freeze_automation is True
