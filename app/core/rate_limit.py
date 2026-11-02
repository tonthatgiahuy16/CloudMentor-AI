from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.core import config


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True

        now = monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                return False

            timestamps.append(now)
            return True


chat_rate_limiter = SlidingWindowRateLimiter(
    limit=config.CHAT_RATE_LIMIT_PER_MINUTE,
)


def get_client_ip(request: Request) -> str:
    """Use Render's forwarding header, falling back to the direct peer."""
    forwarded_for = request.headers.get("x-forwarded-for", "")

    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


def enforce_chat_rate_limit(request: Request) -> None:
    if chat_rate_limiter.allow(get_client_ip(request)):
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Chat rate limit exceeded. Please try again in a minute.",
        headers={"Retry-After": "60"},
    )
