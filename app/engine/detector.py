"""Aging-bucket detection for overdue invoices."""

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Iterable

from app.engine.compliance import ComplianceResult, check_eligibility
from app.models.enums import AgingBucket, InvoiceStatus
from app.models.invoice import Invoice


@dataclass(frozen=True)
class DetectedCase:
    """An overdue invoice together with deterministic detection metadata."""

    invoice: Invoice
    overdue_days: int
    aging_bucket: AgingBucket
    compliance: ComplianceResult


def _bucket_for(overdue_days: int) -> AgingBucket:
    if overdue_days <= 7:
        return AgingBucket.DAYS_1_7
    if overdue_days <= 30:
        return AgingBucket.DAYS_8_30
    return AgingBucket.DAYS_30_PLUS


def detect_invoices(
    invoices: Iterable[Invoice],
    now: datetime | None = None,
) -> list[DetectedCase]:
    """Detect overdue invoices and attach their compliance result."""

    current_time = now or datetime.now(timezone.utc)
    detected: list[DetectedCase] = []

    for invoice in invoices:
        if invoice.status is not InvoiceStatus.OVERDUE:
            continue

        overdue_days = (current_time.date() - invoice.due_date).days
        if overdue_days <= 0:
            continue

        detected.append(
            DetectedCase(
                invoice=invoice,
                overdue_days=overdue_days,
                aging_bucket=_bucket_for(overdue_days),
                compliance=check_eligibility(invoice, current_time),
            )
        )

    return detected
