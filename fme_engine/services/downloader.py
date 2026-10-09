"""Free Media Engine (FME) — Direct Media Asset Ingestion & Downloader.

Streams high-resolution generation artifacts directly from Google CDN / media URLs
to local host storage (/data/outputs/{job_id}.mp4 or .png) upon completion.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import httpx

from fme_engine.core.config import settings

logger = logging.getLogger(__name__)


async def download_asset(url: str, job_id: str, mode: str) -> Optional[str]:
    """
    Stream remote media file to local VPS storage.
    
    Returns:
        Absolute filesystem path of saved file, or None on failure.
    """
    settings.ensure_directories()
    ext = ".png" if mode in ("t2i", "edit_image") else ".mp4"
    dest_path = Path(settings.OUTPUTS_DIR) / f"{job_id}{ext}"
    temp_path = Path(settings.OUTPUTS_DIR) / f"{job_id}.tmp"

    logger.info("[Downloader] Starting download for job %s from %s", job_id, url)
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

        # Atomic rename once completely downloaded
        temp_path.replace(dest_path)
        logger.info("[Downloader] Job %s asset saved to %s", job_id, dest_path)
        return str(dest_path.resolve())

    except Exception as e:
        logger.exception("[Downloader] Failed to download asset for job %s: %s", job_id, e)
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return None
