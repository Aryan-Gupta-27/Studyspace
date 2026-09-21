"""Request logging middleware.

Every request gets a correlation id that is echoed in log lines and returned
to the client, so a reported problem can be traced back to a specific call
(RULEBOOK rules 65, 66, 140).
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("studyspace.requests")
REQUEST_ID_HEADER = "x-request-id"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        started = time.perf_counter()

        # Query strings can contain tokens; only method and path are logged.
        logger.info("request start %s %s", request.method, request.url.path, extra={"request_id": request_id})
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed %s %s", request.method, request.url.path, extra={"request_id": request_id}
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "request end status=%s duration_ms=%.1f",
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def add_request_logging(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
