#Owner::ANIKET::ANHOTRA = MR.Panda
"""Server entry point. Builds the application, connects the routes and error handling.

Start with: uvicorn app.main:create_app --factory
The factory takes settings and a session factory so tests can supply their own.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app import __version__
from app.api import (
    auth_routes,
    health_routes,
    organization_routes,
    project_routes,
    site_routes,
)
from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory
from app.errors import AuthenticationError, SitePayError
from app.feature_flags import FeatureFlags
from app.logging_setup import configure_logging

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def register_error_handlers(application: FastAPI) -> None:
    """Turn application errors and unexpected failures into consistent JSON replies.

    Unexpected errors are logged in full but only a generic message reaches the client.
    """

    @application.exception_handler(SitePayError)
    async def handle_sitepay_error(request: Request, error: SitePayError) -> JSONResponse:
        """Reply with the error's status and standard body.

        Failed logins also carry the standard Bearer challenge header.
        """
        headers = {"WWW-Authenticate": "Bearer"} if isinstance(error, AuthenticationError) else None
        return JSONResponse(
            status_code=error.status_code, content=error.to_response_body(), headers=headers
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        """Log the real error and reply with a generic 500.

        Internal details never reach the client.
        """
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=error)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Something went wrong."}},
        )


def create_application(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    """Build the FastAPI application with settings, database, flags, routes and handlers.

    Interactive API docs are switched off in production.
    """
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    is_production = active_settings.application_environment == "production"
    application = FastAPI(
        title="SitePay Agent",
        version=__version__,
        docs_url=None if is_production else "/docs",
        redoc_url=None,
        openapi_url=None if is_production else "/openapi.json",
    )
    application.state.settings = active_settings
    application.state.feature_flags = FeatureFlags.from_text(active_settings.feature_flags_raw)
    application.state.session_factory = session_factory or build_session_factory(
        build_engine(active_settings.database_url)
    )

    @application.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add basic security headers to every response.

        Stops content sniffing and framing, and keeps API replies out of caches.
        """
        response = await call_next(request)
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers.setdefault(header_name, header_value)
        return response

    register_error_handlers(application)
    application.include_router(health_routes.router)
    for api_router in (
        auth_routes.router,
        organization_routes.router,
        project_routes.router,
        site_routes.router,
    ):
        application.include_router(api_router, prefix=API_PREFIX)
    return application


def create_app() -> FastAPI:
    """Factory used by the server command line, reading settings from the environment.

    Run with: uvicorn app.main:create_app --factory
    """
    return create_application()
