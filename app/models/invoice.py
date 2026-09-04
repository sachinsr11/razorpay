"""Pydantic models for receivables cases."""

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DiagnosisCategory, InterventionRung, InvoiceStatus


class Invoice(BaseModel):
    """A receivable tracked through the recovery workflow."""

    model_config = ConfigDict(validate_assignment=True)

    invoice_id: str = Field(min_length=1)
    customer_name: str = Field(min_length=1)
    customer_email: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.OVERDUE
    touches: int = Field(default=0, ge=0)
    last_touch_at: datetime | None = None
    failed_attempts: int = Field(default=0, ge=0)
    broken_promises: int = Field(default=0, ge=0)
    intervention_rung: InterventionRung | None = None
    diagnosis: DiagnosisCategory | None = None
    recovered_amount: Decimal = Field(default=Decimal("0"), ge=0)
    promise_to_pay_date: date | None = None
    promise_to_pay_amount: Decimal | None = Field(default=None, gt=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @model_validator(mode="after")
    def validate_recovery_and_promise(self) -> "Invoice":
        """Keep recovery and promise data internally consistent."""

        if self.recovered_amount > self.amount:
            raise ValueError("recovered_amount cannot exceed amount")

        has_promise_date = self.promise_to_pay_date is not None
        has_promise_amount = self.promise_to_pay_amount is not None
        if has_promise_date != has_promise_amount:
            raise ValueError(
                "promise_to_pay_date and promise_to_pay_amount must be supplied together"
            )

        return self
