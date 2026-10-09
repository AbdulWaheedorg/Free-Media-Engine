"""Free Media Engine (FME) — Main Application & Server Entry Point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fme_engine.api.router import api_v1_router
from fme_engine.core.config import settings
from fme_engine.db.database import close_db, init_db
from fme_engine.services.ws_bridge import ws_bridge
from fme_engine.worker.queue import get_queue_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fme_engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Free Media Engine v1.0.0...")
    settings.ensure_directories()
    await init_db()

    # Launch background WebSocket bridge for Chrome extension
    await ws_bridge.start()

    # Launch background Queue worker
    worker = get_queue_worker()
    worker_task = asyncio.create_task(worker.start())

    logger.info("Free Media Engine ready on http://%s:%d", settings.DAEMON_HOST, settings.DAEMON_PORT)
    yield

    logger.info("Shutting down Free Media Engine...")
    await worker.stop()
    worker_task.cancel()
    await ws_bridge.stop()
    await close_db()
    logger.info("Free Media Engine shutdown complete")


app = FastAPI(
    title="Free Media Engine (FME)",
    version="1.0.0",
    description="Unattended AI media generation API & engine for photos and videos.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "engine": "Free Media Engine",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "api_v1": "/api/v1",
    }
