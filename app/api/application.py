from importlib import metadata
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, UJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.lifespan import lifespan_setup
from app.api.v1.router import api_router
from app.core.exceptions.exceptions import AppError
from app.core.logging.log import configure_logging
from app.core.middleware.logging_middleware import logging_middleware

APP_ROOT = Path(__file__).parent.parent


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    configure_logging()
    app = FastAPI(
        title="app",
        version=metadata.version("app"),
        lifespan=lifespan_setup,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return exc.to_response()

    app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)

    # Main router for the API.
    app.include_router(router=api_router, prefix="/user/v1")
    # Adds static directory.
    # This directory is used to access swagger files.
    app.mount("/static", StaticFiles(directory=APP_ROOT / "static"), name="static")

    return app
