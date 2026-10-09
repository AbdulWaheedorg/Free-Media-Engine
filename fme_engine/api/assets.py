"""Free Media Engine (FME) — Direct Binary Asset Streaming Route."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import FileResponse

from fme_engine.core.auth import authenticate_bearer_token
from fme_engine.core.config import settings
from fme_engine.db import crud

router = APIRouter(tags=["Assets"])


@router.get(
    "/assets/{job_id}",
    summary="Download or stream completed media asset",
    description="Streams the binary MP4 or PNG directly from VPS disk. Supports byte-ranges for video seek and token authentication in header or query parameter.",
)
async def get_media_asset(
    job_id: str,
    token: Optional[str] = Query(None, description="API Key token passed in query parameter for browser <video> tags"),
    authorization: Optional[str] = Header(None, description="Standard Authorization: Bearer <API_KEY> header"),
):
    # 1. Resolve and verify authentication token
    auth_token = None
    if authorization and authorization.lower().startswith("bearer "):
        auth_token = authorization[7:].strip()
    elif token:
        auth_token = token.strip()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token or ?token= query parameter",
        )

    key_record = await authenticate_bearer_token(auth_token)
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    # 2. Look up job and file path
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    local_path = job.get("local_path")
    if not local_path or not os.path.exists(local_path):
        # Check standard default path
        ext = ".png" if job.get("mode") in ("t2i", "edit_image") else ".mp4"
        candidate = Path(settings.OUTPUTS_DIR) / f"{job_id}{ext}"
        if candidate.exists():
            local_path = str(candidate)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset file not found on disk. Job may still be processing or failed.",
            )

    media_type = "video/mp4" if local_path.endswith(".mp4") else "image/png"
    return FileResponse(
        path=local_path,
        media_type=media_type,
        filename=os.path.basename(local_path),
        headers={"Accept-Ranges": "bytes"},
    )
