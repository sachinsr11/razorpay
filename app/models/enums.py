"""Enumerations shared by the receivables recovery workflow."""

from enum import Enum, IntEnum


class InvoiceStatus(str, Enum):
    """Current lifecycle state of an invoice."""

    OVERDUE = "overdue"
    PAID = "paid"
    PROMISE_TO_PAY = "promise_to_pay"
    FROZEN_HUMAN_REVIEW = "frozen_human_review"


class DiagnosisCategory(str, Enum):
    """Approved root-cause categories for an overdue invoice."""

    FORGETFUL = "forgetful"
    CASH_FLOW_STRAPPED = "cash_flow_strapped"
    DISPUTED = "disputed"
    WRONG_BOUNCED_CONTACT = "wrong_bounced_contact"


class AgingBucket(str, Enum):
    """Allowed aging buckets used by detection."""

    DAYS_1_7 = "1-7"
    DAYS_8_30 = "8-30"
    DAYS_30_PLUS = "30+"


class InterventionRung(IntEnum):
    """The three-rung, email-only escalation ladder."""

    RUNG_1 = 1
    RUNG_2 = 2
    RUNG_3 = 3
