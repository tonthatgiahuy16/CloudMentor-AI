import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logger import (
    JsonFormatter,
    REDACTED,
    redact_text,
    redact_value,
)
from app.core.request_context import RequestContextMiddleware


def _record(**extra):
    record = logging.LogRecord(
        name="CloudMentorAI",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Pipeline stage completed",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_includes_request_id_and_structured_fields():
    record = _record(
        request_id="req-123",
        structured={
            "event": "pipeline_stage",
            "document_id": "doc-1",
            "stage": "EMBEDDING",
            "duration_ms": 42,
        },
    )

    payload = json.loads(
        JsonFormatter().format(record)
    )

    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["event"] == "pipeline_stage"
    assert payload["duration_ms"] == 42


def test_sensitive_keys_are_redacted():
    record = _record(
        structured={
            "password": "hunter2",
            "access_token": "abc.def.ghi",
            "employee_id": "alice",
        },
    )

    payload = json.loads(
        JsonFormatter().format(record)
    )

    assert payload["password"] == REDACTED
    assert payload["access_token"] == REDACTED
    assert payload["employee_id"] == "alice"


def test_common_credentials_in_text_are_redacted():
    text = (
        "contact alice@example.com "
        "Authorization: Bearer abc.def.ghi"
    )

    redacted = redact_text(text)

    assert "alice@example.com" not in redacted
    assert "abc.def.ghi" not in redacted


def test_redact_value_walks_nested_structures():
    redacted = redact_value(
        "payload",
        {
            "password": "hunter2",
            "nested": [
                {"token": "abc"},
                {"employee_id": "alice"},
            ],
        },
    )

    assert redacted["password"] == REDACTED
    assert redacted["nested"][0]["token"] == REDACTED
    assert redacted["nested"][1]["employee_id"] == "alice"


def test_request_context_middleware_returns_request_id_header():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)

    response = client.get(
        "/ping",
        headers={"X-Request-ID": "client-request-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == (
        "client-request-1"
    )


def test_request_context_middleware_generates_missing_header():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    response = TestClient(app).get("/ping")

    assert response.headers["X-Request-ID"]
