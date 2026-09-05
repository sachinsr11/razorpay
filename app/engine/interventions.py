"""Deterministic intervention selection."""

from dataclasses import dataclass
from enum import Enum

from app.engine.compliance import HIGH_VALUE_THRESHOLD
from app.engine.detector import DetectedCase
from app.models.enums import (
    DiagnosisCategory,
    InterventionRung,
    InvoiceStatus,
)


class InterventionAction(str, Enum):
    """Allowed simulated outcomes of intervention selection."""

    NO_ACTION = "no_action"
    GENTLE_REMINDER = "gentle_reminder"
    FIRM_REMINDER_PAYMENT_PLAN = "firm_reminder_payment_plan"
    AR_REP_HANDOFF = "ar_rep_handoff"
    FREEZE_HUMAN_REVIEW = "freeze_human_review"


@dataclass(frozen=True)
class InterventionDecision:
    """A deterministic, auditable intervention decision."""

    action: InterventionAction
    rung: InterventionRung | None
    freeze_automation: bool
    reason: str
    new_status: InvoiceStatus | None = None


def select_intervention(
    case: DetectedCase,
    diagnosis: DiagnosisCategory | None,
) -> InterventionDecision:
    """Select the next bounded action without making an external side effect."""

    if not case.compliance.eligible:
        terminal = case.invoice.intervention_rung is InterventionRung.RUNG_3
        return InterventionDecision(
            action=InterventionAction.NO_ACTION,
            rung=case.invoice.intervention_rung,
            freeze_automation=terminal,
            reason="; ".join(case.compliance.reasons),
        )

    if diagnosis in {
        DiagnosisCategory.DISPUTED,
        DiagnosisCategory.WRONG_BOUNCED_CONTACT,
    }:
        return InterventionDecision(
            action=InterventionAction.FREEZE_HUMAN_REVIEW,
            rung=None,
            freeze_automation=True,
            reason=f"diagnosis requires human review: {diagnosis.value}",
            new_status=InvoiceStatus.FROZEN_HUMAN_REVIEW,
        )

    if case.overdue_days > 30 and case.invoice.amount > HIGH_VALUE_THRESHOLD:
        return _handoff("high-value invoice is over 30 days overdue")

    if case.invoice.failed_attempts >= 2:
        return _handoff("maximum failed automated attempts reached")

    if diagnosis is DiagnosisCategory.CASH_FLOW_STRAPPED:
        return InterventionDecision(
            action=InterventionAction.FIRM_REMINDER_PAYMENT_PLAN,
            rung=InterventionRung.RUNG_2,
            freeze_automation=False,
            reason="cash-flow diagnosis forces rung 2",
        )

    if case.overdue_days <= 7:
        return InterventionDecision(
            action=InterventionAction.GENTLE_REMINDER,
            rung=InterventionRung.RUNG_1,
            freeze_automation=False,
            reason="invoice is 1-7 days overdue",
        )

    return InterventionDecision(
        action=InterventionAction.FIRM_REMINDER_PAYMENT_PLAN,
        rung=InterventionRung.RUNG_2,
        freeze_automation=False,
        reason="invoice is more than 7 days overdue",
    )


def _handoff(reason: str) -> InterventionDecision:
    return InterventionDecision(
        action=InterventionAction.AR_REP_HANDOFF,
        rung=InterventionRung.RUNG_3,
        freeze_automation=True,
        reason=reason,
        new_status=InvoiceStatus.FROZEN_HUMAN_REVIEW,
    )
