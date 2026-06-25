from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI

REFACTOR_ROOT: Path = Path(__file__).resolve().parents[3]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from app.routes.interviews import router as interviews_router
from core.config import get_config
from core.middleware import ExceptionHandlerMiddleware, LoggingMiddleware


def create_app() -> FastAPI:
    """Create FastAPI application.

    Returns:
        FastAPI: Configured FastAPI instance.
    """
    config = get_config()
    app = FastAPI(title=config.app_name)

    # Add middleware (order matters: last added = first executed)
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": config.app_name
        }

    @app.get("/readiness", tags=["Health"])
    async def readiness_check():
        """Readiness check endpoint."""
        return {
            "status": "ready",
            "service": config.app_name
        }

    app.include_router(interviews_router)
    return app


app = create_app()
