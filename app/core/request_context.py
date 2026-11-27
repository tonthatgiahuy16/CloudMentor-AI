from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import (
    logger,
    reset_request_id,
    set_request_id,
)


REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 100


def _request_id_from_header(value: str | None) -> str:
    if (
        value
        and 0 < len(value) <= _MAX_REQUEST_ID_LENGTH
        and value.isprintable()
    ):
        return value
    return uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to every log line and response."""

    async def dispatch(self, request, call_next):
        request_id = _request_id_from_header(
            request.headers.get(REQUEST_ID_HEADER)
        )
        token = set_request_id(request_id)
        started = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Request failed",
                extra={
                    "structured": {
                        "event": "http_request",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": 500,
                        "duration_ms": round(
                            (perf_counter() - started)
                            * 1000,
                            2,
                        ),
                    },
                },
            )
            raise
        else:
            duration_ms = round(
                (perf_counter() - started) * 1000,
                2,
            )
            response.headers[REQUEST_ID_HEADER] = (
                request_id
            )
            logger.info(
                "Request completed",
                extra={
                    "structured": {
                        "event": "http_request",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                },
            )
            return response
        finally:
            reset_request_id(token)
