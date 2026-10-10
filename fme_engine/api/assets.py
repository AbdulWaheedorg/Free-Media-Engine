"""Free Media Engine (FME) — Direct Binary Asset Streaming Route."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import FileResponse

from fme_engine.core.auth import authenticate_bearer_token
from fme_engine.core.config import settings
from fme_engine.db import crud

router = APIRouter(tags=["Assets"])

SAFE_JOB_ID_REGEX = re.compile(r"^[0-9a-fA-F\-]{8,64}$")


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
    # 1. Strictly sanitize job_id to prevent path injection
    if not SAFE_JOB_ID_REGEX.fullmatch(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format. Must be a valid UUID.",
        )

    # 2. Resolve and verify authentication token
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

    # 3. Look up job and verify record exists
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    base_dir = os.path.realpath(settings.OUTPUTS_DIR)
    ext = ".png" if job.get("mode") in ("t2i", "edit_image") else ".mp4"
    filename = f"{job_id}{ext}"

    # Canonical path resolution & containment verification (CWE-022 sanitizer)
    target_path = os.path.realpath(os.path.join(base_dir, filename))
    if not target_path.startswith(base_dir + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal detected",
        )

    # Check if target exists; fallback to job's verified local_path if set
    if not os.path.isfile(target_path):
        raw_local = job.get("local_path")
        if raw_local:
            alt_path = os.path.realpath(raw_local)
            if alt_path.startswith(base_dir + os.sep) and os.path.isfile(alt_path):
                target_path = alt_path

    if not os.path.isfile(target_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found on disk. Job may still be processing or failed.",
        )

    media_type = "video/mp4" if target_path.endswith(".mp4") else "image/png"
    return FileResponse(
        path=target_path,
        media_type=media_type,
        filename=os.path.basename(target_path),
        headers={"Accept-Ranges": "bytes"},
    )
