"""Small, mockable boundary around the OpenCode Go Responses API."""

import os
from typing import Any

from openai import OpenAI

MODEL = "gpt-5.6-luna"
BASE_URL = "https://opencode.ai/zen/go/v1"
API_KEY_ENV = "OPENCODE_ZEN_API_KEY"


class LLMConfigurationError(RuntimeError):
    """Raised when an LLM call is attempted without configuration."""


class LLMResponseError(RuntimeError):
    """Raised when the provider response has no usable text."""


class LLMClient:
    """Call the configured model, or accept a fake client in tests."""

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv(API_KEY_ENV)
        if client is None and not resolved_key:
            raise LLMConfigurationError(
                f"{API_KEY_ENV} must be set before making an LLM call"
            )

        self.model = MODEL
        self.base_url = BASE_URL
        self._client = client or OpenAI(api_key=resolved_key, base_url=BASE_URL)

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Submit a prompt and return the provider's text output."""

        request_input: str | list[dict[str, str]] = prompt
        if system_prompt is not None:
            request_input = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        response = self._client.responses.create(
            model=self.model,
            input=request_input,
        )
        text = getattr(response, "output_text", None)
        if not text or not text.strip():
            raise LLMResponseError("LLM response did not contain usable text")
        return text.strip()
