"""Free Media Engine (FME) — Generation API Route."""
from __future__ import annotations

import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, status

from fme_engine.core.auth import get_current_api_key
from fme_engine.db import crud
from fme_engine.models.schemas import GenerateRequest, GenerateResponse, JobStatus

router = APIRouter(tags=["Generation"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a generation job",
    description="Accepts generation requests for t2v, i2v, t2i, references, or upscaling and queues them for execution.",
)
async def submit_generate_job(
    request: GenerateRequest,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> GenerateResponse:
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "api_key_id": current_key.get("id"),
        "prompt": request.prompt,
        "mode": request.mode.value,
        "model": request.model.value,
        "aspect_ratio": request.aspect_ratio.value,
        "seed_image_url": request.seed_image_url,
        "last_frame_image_url": request.last_frame_image_url,
        "reference_image_urls": request.reference_image_urls,
        "seed": request.seed,
        "duration_seconds": request.duration_seconds,
        "webhook_url": request.webhook_url,
    }

    await crud.create_job(job_data)
    pos = await crud.get_queue_position(job_id)

    # Estimate wait: approx 60-90s per video in queue ahead
    est_seconds = max(0, (pos - 1) * 75)

    return GenerateResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        queue_position=pos,
        estimated_wait_seconds=est_seconds,
        message=f"Job accepted and placed at position {pos} in the queue",
    )
