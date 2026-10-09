"""Free Media Engine (FME) — Outbound Webhook Dispatcher.

Dispatches completion payloads to caller-defined webhook URLs with retry support.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
import httpx

from fme_engine.db import crud

logger = logging.getLogger(__name__)


async def dispatch_webhook(webhook_url: str, payload: Dict[str, Any], max_retries: int = 3) -> bool:
    """
    POST completion payload to external webhook URL with exponential backoff.
    """
    if not webhook_url:
        return False

    job_id = payload.get("job_id", "unknown")
    logger.info("[Webhook] Dispatching callback for job %s to %s", job_id, webhook_url)

    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code in (200, 201, 202, 204):
                    logger.info("[Webhook] Job %s callback accepted with status %d", job_id, resp.status_code)
                    await crud.update_job(job_id, webhook_status=f"DELIVERED_{resp.status_code}")
                    return True
                logger.warning(
                    "[Webhook] Attempt %d: Webhook endpoint returned %d: %s",
                    attempt,
                    resp.status_code,
                    resp.text[:100],
                )
        except Exception as e:
            logger.warning("[Webhook] Attempt %d failed for job %s: %s", attempt, job_id, e)

        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2.0

    await crud.update_job(job_id, webhook_status="FAILED_AFTER_RETRIES")
    return False
