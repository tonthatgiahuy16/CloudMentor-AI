import time

import httpx
from google import genai
from google.genai import errors

from app.llm.config import (
    GEMINI_API_KEY,
    LLM_MAX_ATTEMPTS,
    LLM_RETRY_BACKOFF_SECONDS,
    MODEL_NAME
)
from app.llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)


class GeminiService:

    def __init__(
        self,
        *,
        client=None,
        max_attempts: int = LLM_MAX_ATTEMPTS,
        retry_backoff_seconds: float = (
            LLM_RETRY_BACKOFF_SECONDS
        ),
        sleep=time.sleep,
    ):
        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1"
            )
        if retry_backoff_seconds < 0:
            raise ValueError(
                "retry_backoff_seconds must not be negative"
            )

        self.client = client or genai.Client(
            api_key=GEMINI_API_KEY
        )
        self.max_attempts = max_attempts
        self.retry_backoff_seconds = (
            retry_backoff_seconds
        )
        self.sleep = sleep


    def generate(
        self,
        prompt: str
    ) -> str:
        print("Using model:", MODEL_NAME)

        for attempt in range(self.max_attempts):
            try:
                response = (
                    self.client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                    )
                )
                return response.text
            except (
                errors.APIError,
                TimeoutError,
                httpx.TimeoutException,
            ) as exc:
                if not self._is_retryable(exc):
                    raise LLMProviderError(
                        "LLM provider request failed"
                    ) from exc

                if attempt == self.max_attempts - 1:
                    raise LLMProviderUnavailableError(
                        "LLM provider request failed"
                    ) from exc

                self.sleep(
                    self.retry_backoff_seconds * (2 ** attempt)
                )

        raise AssertionError("retry loop did not return or raise")

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(
            exc,
            (TimeoutError, httpx.TimeoutException),
        ):
            return True

        if isinstance(exc, errors.APIError):
            return exc.code in {429, 503}

        return False
