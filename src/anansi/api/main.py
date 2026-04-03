"""FastAPI application factory for the Anansi API."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anansi.api.router import router
from anansi.api.store import job_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cleanup_task = asyncio.create_task(job_store.cleanup_loop())
    logger.info("Anansi API started")
    try:
        yield
    finally:
        cleanup_task.cancel()
        logger.info("Anansi API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Anansi API",
        description="AI-Powered Multimodal Education for African Classrooms",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    return app


# ASGI entrypoint: uvicorn anansi.api.main:app
app = create_app()
