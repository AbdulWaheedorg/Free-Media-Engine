"""Free Media Engine (FME) — Jobs & Real-Time SSE Streaming Routes."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from fme_engine.core.auth import get_current_api_key
from fme_engine.db import crud
from fme_engine.models.schemas import JobResponse, JobStatus
from fme_engine.services.event_bus import event_bus

router = APIRouter(tags=["Jobs"])


@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List recent jobs",
)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> List[JobResponse]:
    rows = await crud.list_jobs(limit=limit, offset=offset)
    results = []
    for r in rows:
        results.append(
            JobResponse(
                job_id=r["id"],
                status=JobStatus(r["status"]),
                progress=r["progress"],
                prompt=r["prompt"],
                mode=r["mode"],
                model=r["model"],
                aspect_ratio=r["aspect_ratio"],
                download_url=f"/api/v1/assets/{r['id']}" if r["status"] == "COMPLETED" else None,
                local_path=r.get("local_path"),
                source_url=r.get("source_url"),
                error_message=r.get("error_message"),
                webhook_url=r.get("webhook_url"),
                created_at=r["created_at"],
                completed_at=r.get("completed_at"),
            )
        )
    return results


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job status and download URL",
)
async def get_job_status(
    job_id: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> JobResponse:
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    pos = await crud.get_queue_position(job_id) if job["status"] == "QUEUED" else 0
    return JobResponse(
        job_id=job["id"],
        status=JobStatus(job["status"]),
        progress=job["progress"],
        prompt=job["prompt"],
        mode=job["mode"],
        model=job["model"],
        aspect_ratio=job["aspect_ratio"],
        download_url=f"/api/v1/assets/{job['id']}" if job["status"] == "COMPLETED" else None,
        local_path=job.get("local_path"),
        source_url=job.get("source_url"),
        error_message=job.get("error_message"),
        queue_position=pos,
        webhook_url=job.get("webhook_url"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.delete(
    "/jobs/{job_id}",
    summary="Cancel a queued job",
)
async def cancel_job(
    job_id: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> Dict[str, str]:
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job["status"] not in ("QUEUED", "PROCESSING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in state: {job['status']}",
        )

    await crud.update_job(job_id, status="CANCELLED", error_message="Cancelled by user")
    return {"message": f"Job {job_id} cancelled"}


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream real-time job progress (Server-Sent Events)",
    description="Maintains an open SSE connection yielding status and progress events until the job finishes or fails.",
)
async def stream_job_events(
    job_id: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
):
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async def event_generator():
        # First send immediate snapshot
        current = await crud.get_job(job_id)
        if current:
            yield f"data: {json.dumps({'status': current['status'], 'progress': current['progress'], 'download_url': f'/api/v1/assets/{job_id}' if current['status'] == 'COMPLETED' else None})}\n\n"
            if current["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                return

        queue = asyncio.Queue()

        def on_event(data):
            queue.put_nowait(data)

        event_bus.subscribe(f"job:{job_id}", on_event)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                        break
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": ping\n\n"
        finally:
            event_bus.unsubscribe(f"job:{job_id}", on_event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
