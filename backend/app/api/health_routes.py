#Owner::ANIKET::ANHOTRA = MR.Panda
"""Routes that report whether the server is alive and ready."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.dependencies import get_database_session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def report_liveness() -> dict[str, str]:
    """Report that the server process is running.

    Does not touch the database, so it stays fast and cheap.
    """
    return {"status": "ok", "version": __version__}


@router.get("/health/ready", response_model=None)
def report_readiness(
    session: Session = Depends(get_database_session),
) -> JSONResponse | dict[str, str]:
    """Report whether the database answers a simple query.

    Returns status 503 when it does not, so load balancers stop sending traffic.
    """
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "database_unavailable"})
    return {"status": "ready", "version": __version__}
