import importlib
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def load_gemini_service(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.llm import config, service

    importlib.reload(config)
    return importlib.reload(service).GeminiService


def test_retries_transient_provider_error_then_returns_answer(
    monkeypatch,
):
    GeminiService = load_gemini_service(monkeypatch)
    models = FakeModels(
        [
            errors.ServerError(503, {}),
            SimpleNamespace(text="grounded answer"),
        ]
    )
    sleep_delays = []

    service = GeminiService(
        client=SimpleNamespace(models=models),
        max_attempts=3,
        retry_backoff_seconds=0.25,
        sleep=sleep_delays.append,
    )

    assert service.generate("prompt") == "grounded answer"
    assert len(models.calls) == 2
    assert sleep_delays == [0.25]


def test_raises_controlled_unavailable_error_after_retry_exhausted(
    monkeypatch,
):
    GeminiService = load_gemini_service(monkeypatch)
    models = FakeModels([TimeoutError("timed out")] * 3)
    sleep_delays = []

    service = GeminiService(
        client=SimpleNamespace(models=models),
        max_attempts=3,
        retry_backoff_seconds=0.5,
        sleep=sleep_delays.append,
    )

    with pytest.raises(LLMProviderUnavailableError):
        service.generate("prompt")

    assert len(models.calls) == 3
    assert sleep_delays == [0.5, 1.0]


def test_does_not_retry_non_transient_provider_error(monkeypatch):
    GeminiService = load_gemini_service(monkeypatch)
    models = FakeModels([errors.ClientError(400, {})])
    sleep_delays = []

    service = GeminiService(
        client=SimpleNamespace(models=models),
        max_attempts=3,
        sleep=sleep_delays.append,
    )

    with pytest.raises(LLMProviderError):
        service.generate("prompt")

    assert len(models.calls) == 1
    assert sleep_delays == []


def test_does_not_translate_unexpected_internal_error(monkeypatch):
    GeminiService = load_gemini_service(monkeypatch)
    models = FakeModels([RuntimeError("unexpected bug")])

    service = GeminiService(
        client=SimpleNamespace(models=models),
    )

    with pytest.raises(RuntimeError, match="unexpected bug"):
        service.generate("prompt")

    assert len(models.calls) == 1
