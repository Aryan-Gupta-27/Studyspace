"""In-process sliding-window rate limiter.

Redis is explicitly deferred until after the MVP gate, so abuse protection is
deliberately the simplest thing that works: a bounded, in-memory window keyed
by an actor (user id when known, otherwise client IP). It protects the
authentication and upload endpoints requested by milestone 7 without adding
infrastructure (RULEBOOK rule 55: do not over-engineer).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import Settings
from app.core.errors import RateLimitError

_WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def actor_key(request: Request, scope: str, user_id: str | None = None) -> str:
    identity = user_id or _client_ip(request)
    return f"{scope}:{identity}"


def enforce_rate_limit(key: str, max_per_minute: int) -> None:
    """Raise :class:`RateLimitError` when ``key`` exceeds its budget.

    The bookkeeping is intentionally tiny: expired entries are dropped on every
    call, which keeps memory proportional to real traffic.
    """
    now = time.monotonic()
    with _lock:
        window = _hits[key]
        cutoff = now - _WINDOW_SECONDS
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= max_per_minute:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - window[0])))
            raise RateLimitError(retry_after_seconds=retry_after)
        window.append(now)


def limit_login(request: Request, settings: Settings, user_id: str | None = None) -> None:
    enforce_rate_limit(actor_key(request, "login", user_id), settings.login_max_attempts_per_minute)


def limit_upload(request: Request, settings: Settings, user_id: str | None = None) -> None:
    enforce_rate_limit(actor_key(request, "upload", user_id), settings.upload_max_attempts_per_minute)


def limit_write(request: Request, settings: Settings, user_id: str | None = None) -> None:
    enforce_rate_limit(actor_key(request, "write", user_id), settings.write_max_attempts_per_minute)


def reset() -> None:
    """Clear all windows. Used by tests to start from a clean slate."""
    with _lock:
        _hits.clear()
