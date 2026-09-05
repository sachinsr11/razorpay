"""Tests for the mocked LLM integration boundary."""

from types import SimpleNamespace

import pytest

from app.llm.client import (
    API_KEY_ENV,
    BASE_URL,
    MODEL,
    LLMClient,
    LLMConfigurationError,
    LLMResponseError,
)


class FakeResponses:
    def __init__(self, output_text: str | None) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAI:
    def __init__(self, output_text: str | None = '{"ok": true}') -> None:
        self.responses = FakeResponses(output_text)


def test_missing_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(API_KEY_ENV, raising=False)

    with pytest.raises(LLMConfigurationError, match=API_KEY_ENV):
        LLMClient()


def test_injected_client_does_not_require_api_key() -> None:
    fake = FakeOpenAI()

    client = LLMClient(client=fake)

    assert client.model == MODEL
    assert client.base_url == BASE_URL


def test_complete_uses_model_and_returns_text() -> None:
    fake = FakeOpenAI('{"category": "forgetful"}')
    client = LLMClient(client=fake)

    result = client.complete("Classify this invoice")

    assert result == '{"category": "forgetful"}'
    assert fake.responses.calls == [
        {"model": MODEL, "input": "Classify this invoice"}
    ]


def test_complete_can_include_system_prompt() -> None:
    fake = FakeOpenAI("response")
    client = LLMClient(client=fake)

    client.complete("invoice context", "You classify invoices.")

    assert fake.responses.calls[0]["input"] == [
        {"role": "system", "content": "You classify invoices."},
        {"role": "user", "content": "invoice context"},
    ]


def test_empty_provider_response_is_rejected() -> None:
    client = LLMClient(client=FakeOpenAI("  "))

    with pytest.raises(LLMResponseError, match="usable text"):
        client.complete("prompt")
