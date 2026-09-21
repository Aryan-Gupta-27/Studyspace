"""Structured, consistent API errors.

Every failure leaves the API through one of these shapes so clients can rely
on a single envelope (RULEBOOK rules 39, 40, 122):

    {"error": {"code": "RESOURCE_NOT_FOUND", "message": "Project not found"}}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("studyspace.errors")


class AppError(Exception):
    """Base class for every expected, user-facing failure."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    # Safe by default: subclasses opt in to echoing their own message.
    public_message = "The request could not be completed."

    def __init__(self, message: str | None = None, **details: Any) -> None:
        self.message = message or self.public_message
        self.details = details
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    public_message = "The submitted data is not valid."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    public_message = "You need to sign in to continue."


class InvalidCredentialsError(AppError):
    """Deliberately vague so the API cannot be used to enumerate accounts."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"
    public_message = "The email or password you entered is incorrect."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    public_message = "You do not have permission to do that."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "RESOURCE_NOT_FOUND"
    public_message = "We couldn't find what you were looking for."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "RESOURCE_CONFLICT"
    public_message = "That conflicts with something that already exists."


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
    public_message = "That file is larger than the allowed limit."


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"
    public_message = "You're doing that too quickly. Please slow down and try again."

    def __init__(self, retry_after_seconds: int = 60, message: str | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        payload = exc.to_payload()
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error("app_error code=%s message=%s", exc.code, exc.message)
        else:
            logger.info("app_error code=%s message=%s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field-level detail is useful and contains no internals, so it is safe
        # to return; the raw exception text is not.
        fields = [
            {"field": ".".join(str(part) for part in error["loc"][1:]) or "body", "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Please check the highlighted fields.", "details": {"fields": fields}}},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        # Log the real cause for operators; never leak it to the client.
        logger.exception("unhandled_error type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong on our side. Please try again."}},
        )
