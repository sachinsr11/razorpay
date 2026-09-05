"""Deterministic compliance and automation eligibility rules."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import InterventionRung, InvoiceStatus
from app.models.invoice import Invoice

MAX_AUTOMATED_TOUCHES = 3
COOLDOWN_DAYS = 4
HIGH_VALUE_THRESHOLD = Decimal("10000")
MAX_FAILED_ATTEMPTS_BEFORE_HANDOFF = 2
BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 18
MAX_CASE_AGE_DAYS = 90


@dataclass(frozen=True)
class ComplianceResult:
    """The outcome and reasons for a compliance evaluation."""

    eligible: bool
    reasons: tuple[str, ...]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_within_business_hours(now: datetime) -> bool:
    """Return whether an action may run during configured business hours."""

    current_hour = _as_utc(now).hour
    return BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END


def check_eligibility(
    invoice: Invoice,
    now: datetime,
) -> ComplianceResult:
    """Evaluate whether an invoice may receive automated treatment.

    ``now`` must be supplied explicitly: batch runs anchor themselves at a
    fixed reference time so results never depend on wall-clock time.
    """

    current_time = _as_utc(now)
    blocking_reasons: list[str] = []

    if invoice.status is not InvoiceStatus.OVERDUE:
        blocking_reasons.append("invoice is not overdue")

    if invoice.touches >= MAX_AUTOMATED_TOUCHES:
        blocking_reasons.append("automated touch cap reached")

    if invoice.intervention_rung is InterventionRung.RUNG_3:
        blocking_reasons.append("invoice is already at terminal rung 3")

    overdue_days = (current_time.date() - invoice.due_date).days
    if overdue_days > MAX_CASE_AGE_DAYS:
        blocking_reasons.append("case exceeds maximum age")

    if invoice.last_touch_at is not None:
        last_touch = _as_utc(invoice.last_touch_at)
        elapsed_days = (current_time - last_touch).total_seconds() / 86400
        if elapsed_days < COOLDOWN_DAYS:
            blocking_reasons.append("cooldown has not elapsed")

    if not is_within_business_hours(current_time):
        blocking_reasons.append("outside business hours")

    if blocking_reasons:
        return ComplianceResult(eligible=False, reasons=tuple(blocking_reasons))

    return ComplianceResult(eligible=True, reasons=("eligible for automation",))
