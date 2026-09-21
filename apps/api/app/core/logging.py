"""Structured logging setup.

Logs are for diagnosis only: passwords, tokens and message bodies are never
written to them (RULEBOOK rules 65, 66).
"""

from __future__ import annotations

import logging

from app.core.config import Settings

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s request_id=%(request_id)s %(message)s"
_DEFAULT_REQUEST_ID = "-"


class _ContextFilter(logging.Filter):
    """Adds a ``request_id`` attribute so the format stays uniform."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id", _DEFAULT_REQUEST_ID)
        return True


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(_ContextFilter())

    root = logging.getLogger("studyspace")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if settings.environment == "development" else logging.INFO)
    root.propagate = False
