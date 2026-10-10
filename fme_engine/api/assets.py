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

    # 3. Look up job and file path
    job = await crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    base_dir = Path(settings.OUTPUTS_DIR).resolve()
    safe_name = Path(job_id).name
    ext = ".png" if job.get("mode") in ("t2i", "edit_image") else ".mp4"

    resolved_file: Optional[Path] = None
    raw_local = job.get("local_path")
    if raw_local:
        candidate = Path(raw_local).resolve()
        try:
            candidate.relative_to(base_dir)
            if candidate.is_file():
                resolved_file = candidate
        except ValueError:
            pass

    if not resolved_file:
        candidate = (base_dir / f"{safe_name}{ext}").resolve()
        try:
            candidate.relative_to(base_dir)
            if candidate.is_file():
                resolved_file = candidate
        except ValueError:
            pass

    if not resolved_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found on disk. Job may still be processing or failed.",
        )

    media_type = "video/mp4" if resolved_file.suffix == ".mp4" else "image/png"
    return FileResponse(
        path=str(resolved_file),
        media_type=media_type,
        filename=resolved_file.name,
        headers={"Accept-Ranges": "bytes"},
    )
