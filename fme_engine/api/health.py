"""Free Media Engine (FME) — System Health & Telemetry Routes."""
from __future__ import annotations

import time
from fastapi import APIRouter
from fme_engine.core.config import settings
from fme_engine.db import crud
from fme_engine.models.schemas import SystemHealthResponse
from fme_engine.services.ws_bridge import ws_bridge
from fme_engine.worker.queue import get_queue_worker

router = APIRouter(tags=["Health"])

_START_TIME = time.time()


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Engine health & telemetry",
    description="Inspects browser extension connection state, active Flow project, queue depth, and worker latency.",
)
async def get_health() -> SystemHealthResponse:
    worker = get_queue_worker()
    queue_count = await crud.count_queued_jobs()
    current_job_id = worker.current_job["id"] if worker.current_job else None

    return SystemHealthResponse(
        status="healthy",
        version="1.0.0",
        extension_connected=ws_bridge.is_connected,
        flow_session_active=ws_bridge.is_connected,
        active_project_id=settings.FLOW_PROJECT_ID,
        queue_depth=queue_count,
        current_job_id=current_job_id,
        uptime_seconds=round(time.time() - _START_TIME, 2),
    )
