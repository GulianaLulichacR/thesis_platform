from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    ThesisPlatformError,
    http_exception_handler,
    platform_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    setup_logging()
    settings.ensure_dirs()
    logger.info(
        "Thesis Review AI Platform starting",
        extra={"version": settings.APP_VERSION, "env": settings.ENVIRONMENT},
    )
    yield
    logger.info("Thesis Review AI Platform shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-ready AI platform for academic thesis review. "
            "Supports multi-LLM providers: Gemini, OpenAI, Claude, Ollama."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Exception Handlers ───────────────────────────────────────────────────
    app.add_exception_handler(ThesisPlatformError, platform_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ─── Routers ──────────────────────────────────────────────────────────────
    app.include_router(v1_router)

    # ─── Health Check ─────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Platform health check")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse({"message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}"})

    return app


app = create_app()
