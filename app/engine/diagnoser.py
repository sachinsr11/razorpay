"""LLM-assisted diagnosis with strict category validation."""

import json
from dataclasses import dataclass
from typing import Protocol

from app.llm.client import LLMClient
from app.models.enums import DiagnosisCategory
from app.models.invoice import Invoice


class TextCompleter(Protocol):
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        ...


class DiagnosisError(ValueError):
    """Raised when an LLM diagnosis cannot be safely interpreted."""


@dataclass(frozen=True)
class DiagnosisResult:
    """A validated diagnosis and the reasoning that produced it."""

    category: DiagnosisCategory
    reasoning: str
    raw_response: str


SYSTEM_PROMPT = """Classify the invoice into exactly one approved category:
forgetful, cash_flow_strapped, disputed, or wrong_bounced_contact.
Return JSON with exactly these keys: category and reasoning.
Do not select an intervention rung."""


def _json_object(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").removeprefix("json").strip()
        cleaned = cleaned.removesuffix("```").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise DiagnosisError("diagnosis response did not contain a JSON object")

    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise DiagnosisError("diagnosis response contained invalid JSON") from exc

    if not isinstance(payload, dict):
        raise DiagnosisError("diagnosis response must be a JSON object")
    return payload


class Diagnoser:
    """Ask the LLM for a category while keeping validation deterministic."""

    def __init__(self, client: TextCompleter | None = None) -> None:
        self.client = client or LLMClient()

    def diagnose(self, invoice: Invoice) -> DiagnosisResult:
        prompt = (
            "Classify this invoice.\n"
            f"invoice_id: {invoice.invoice_id}\n"
            f"customer_name: {invoice.customer_name}\n"
            f"amount: {invoice.amount}\n"
            f"due_date: {invoice.due_date.isoformat()}\n"
            f"failed_attempts: {invoice.failed_attempts}\n"
            f"broken_promises: {invoice.broken_promises}"
        )
        raw_response = self.client.complete(prompt, SYSTEM_PROMPT)
        payload = _json_object(raw_response)

        try:
            category = DiagnosisCategory(str(payload["category"]))
        except (KeyError, ValueError) as exc:
            raise DiagnosisError("diagnosis category is not approved") from exc

        reasoning = payload.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise DiagnosisError("diagnosis reasoning is required")

        return DiagnosisResult(
            category=category,
            reasoning=reasoning.strip(),
            raw_response=raw_response,
        )
