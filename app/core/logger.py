"""Structured JSON logging with request correlation and redaction.

Every log line is a JSON object. Values whose key looks sensitive are
replaced before serialization, and common credential patterns are
redacted from free text. Application code must still avoid logging
document content, questions, or prompts.
"""

from contextvars import ContextVar
import json
import logging
from pathlib import Path
import re


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_request_id_var: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

REDACTED = "***REDACTED***"

_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
    "credential",
)

_EMAIL_PATTERN = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.-]+"
)
_BEARER_PATTERN = re.compile(
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"
)
_API_KEY_PATTERN = re.compile(
    r"\b(?:sk|AIza)[-_A-Za-z0-9]{12,}\b"
)

_STANDARD_RECORD_KEYS = {
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "taskName",
    "message", "asctime", "structured",
}


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_request_id(request_id: str):
    return _request_id_var.set(request_id)


def reset_request_id(token) -> None:
    _request_id_var.reset(token)


def redact_text(value: str) -> str:
    value = _EMAIL_PATTERN.sub(REDACTED, value)
    value = _BEARER_PATTERN.sub(
        f"Bearer {REDACTED}",
        value,
    )
    value = _API_KEY_PATTERN.sub(REDACTED, value)

    if len(value) > 2_000:
        return f"{value[:2_000]}...[truncated]"

    return value


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        part in lowered
        for part in _SENSITIVE_KEY_PARTS
    )


def redact_value(key: str, value):
    if is_sensitive_key(key):
        return REDACTED

    if isinstance(value, str):
        return redact_text(value)

    if isinstance(value, dict):
        return {
            str(item_key): redact_value(
                str(item_key),
                item_value,
            )
            for item_key, item_value in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [redact_value(key, item) for item in value]

    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(
                record,
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(
                record.getMessage()
            ),
        }

        request_id = getattr(
            record,
            "request_id",
            None,
        ) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        structured = getattr(
            record,
            "structured",
            None,
        )
        if isinstance(structured, dict):
            for key, value in structured.items():
                payload[str(key)] = redact_value(
                    str(key),
                    value,
                )

        for key, value in record.__dict__.items():
            if (
                key in _STANDARD_RECORD_KEYS
                or key.startswith("_")
                or key in payload
            ):
                continue
            payload[key] = redact_value(key, value)

        if record.exc_info:
            payload["exception"] = redact_text(
                self.formatException(record.exc_info)
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )


class HumanFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(
            record,
            "request_id",
            None,
        ) or get_request_id()
        prefix = f"[{request_id}] " if request_id else ""
        return (
            f"{self.formatTime(record)} | "
            f"{record.levelname} | "
            f"{prefix}{record.getMessage()}"
        )


def _configure_logger() -> logging.Logger:
    from app.core.config import LOG_FORMAT

    application_logger = logging.getLogger(
        "CloudMentorAI"
    )
    application_logger.setLevel(logging.INFO)
    application_logger.propagate = False

    if application_logger.handlers:
        return application_logger

    formatter = (
        JsonFormatter()
        if LOG_FORMAT == "json"
        else HumanFormatter()
    )

    file_handler = logging.FileHandler(
        LOG_DIR / "cloudmentor.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    application_logger.addHandler(file_handler)
    application_logger.addHandler(stream_handler)

    return application_logger


logger = _configure_logger()
