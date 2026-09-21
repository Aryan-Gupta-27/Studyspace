"""FastAPI application factory.

Route handlers, exception handling, CORS and health live here; all business
rules live in services (RULEBOOK rule 30).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import get_engine, init_database
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import add_request_logging

logger = logging.getLogger("studyspace")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings: Settings = app.state.settings
    configure_logging(settings)
    get_settings.cache_clear()
    if settings.environment != "production":
        # Development and tests bootstrap from the models. Deployed schema
        # changes go through Alembic instead (RULEBOOK rule 24).
        init_database(get_engine())
    logger.info("startup environment=%s", settings.environment)
    yield
    logger.info("shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(
        title=resolved.app_name,
        version="1.0.0",
        description="StudySpace collaborative study platform API.",
        lifespan=lifespan,
        docs_url=None if resolved.is_production else "/docs",
        openapi_url=None if resolved.is_production else "/openapi.json",
    )
    app.state.settings = resolved

    register_exception_handlers(app)
    add_request_logging(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(api_router, prefix=resolved.api_v1_prefix)

    @app.get("/health", tags=["meta"], summary="Service health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": resolved.environment}

    return app


app = create_app()
