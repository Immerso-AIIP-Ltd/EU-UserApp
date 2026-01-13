from importlib import metadata
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, UJSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.lifespan import lifespan_setup
from app.api.v1.router import api_router
from app.core.constants import ErrorCodes, ErrorMessages
from app.core.exceptions.exceptions import (
    AppError,
    AppExceptionError,
    RequestTimeoutError,
    ValidationError,
)
from app.core.logging.log import configure_logging
from app.core.middleware.logging_middleware import logging_middleware

APP_ROOT = Path(__file__).parent.parent


# Reload trigger
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
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(AppExceptionError)
    async def app_exception_handler(
        request: Request,
        exc: AppExceptionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": {},
                "meta": {},
                "error": {
                    "code": exc.error_code,
                    "error_type": exc.error_type,
                    "message": exc.detail,
                },
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(RequestTimeoutError)
    async def request_timeout_error_handler(
        request: Request,
        exc: RequestTimeoutError,
    ) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(f"Unhandled exception: {exc}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": {},
                "meta": {},
                "error": {
                    "code": 500,
                    "error_code": ErrorCodes.INTERNAL_SERVER_ERROR_CODE,
                    "message": ErrorMessages.INTERNAL_SERVER_ERROR,
                    "type": exc.__class__.__name__,
                },
            },
        )

    app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)

    # Main router for the API.
    app.include_router(router=api_router, prefix="/user/v1")
    # Adds static directory.
    # This directory is used to access swagger files.
    app.mount("/static", StaticFiles(directory=APP_ROOT / "static"), name="static")

    return app
