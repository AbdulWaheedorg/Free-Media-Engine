"""Free Media Engine (FME) — Single-Worker Sequential Queue & Pacing Engine.

Enforces concurrency = 1, pseudo-random jitter delays (5s–12s), per-job timeouts,
direct media offloading, and outbound webhook callbacks.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, Optional

from fme_engine.core.config import settings
from fme_engine.db import crud
from fme_engine.db.crud import utc_now
from fme_engine.services.downloader import download_asset
from fme_engine.services.event_bus import event_bus
from fme_engine.services.flow_client import get_flow_client
from fme_engine.services.webhook import dispatch_webhook

logger = logging.getLogger(__name__)


def map_aspect_ratio(aspect: str, is_video: bool) -> str:
    """Map common aspect descriptors to Flow RPC enum strings."""
    if is_video:
        if aspect in ("9:16", "vertical"):
            return "VIDEO_ASPECT_RATIO_PORTRAIT"
        return "VIDEO_ASPECT_RATIO_LANDSCAPE"
    else:
        if aspect in ("9:16", "vertical"):
            return "IMAGE_ASPECT_RATIO_PORTRAIT"
        if aspect in ("1:1", "square"):
            return "IMAGE_ASPECT_RATIO_SQUARE"
        return "IMAGE_ASPECT_RATIO_LANDSCAPE"


class QueueWorker:
    def __init__(self):
        self.running: bool = False
        self.current_job: Optional[Dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background worker queue loop."""
        self.running = True
        logger.info("[Queue Worker] Started single-worker sequential queue (concurrency=1)")
        while self.running:
            try:
                job = await crud.get_next_queued_job()
                if not job:
                    await asyncio.sleep(1.0)
                    continue

                self.current_job = job
                await self.process_job(job)
                self.current_job = None

                # Mandatory pacing jitter between jobs to avoid bot telemetry flags
                jitter = random.uniform(settings.PACING_MIN_DELAY, settings.PACING_MAX_DELAY)
                logger.info("[Queue Worker] Applying pacing jitter: sleeping %.2fs before next job", jitter)
                await asyncio.sleep(jitter)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("[Queue Worker] Unexpected error in worker loop: %s", e)
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self.running = False
        logger.info("[Queue Worker] Stopped worker queue")

    async def process_job(self, job: Dict[str, Any]) -> None:
        job_id = job["id"]
        mode = job["mode"]
        prompt = job["prompt"]
        aspect = job.get("aspect_ratio", "16:9")
        model = job.get("model", "omni_flash")
        timeout = settings.JOB_TIMEOUT_IMAGE if mode == "t2i" else settings.JOB_TIMEOUT_VIDEO

        logger.info("[Queue Worker] >>> Processing job %s [%s] (model: %s): %s", job_id, mode, model, prompt[:60])
        await crud.update_job(job_id, status="PROCESSING", progress=15)
        await event_bus.emit(f"job:{job_id}", {"status": "PROCESSING", "progress": 15})

        client = get_flow_client()
        source_url: Optional[str] = None
        error_msg: Optional[str] = None

        try:
            # ── 1. Text-to-Image (T2I) ───────────────────────────────────────
            if mode == "t2i":
                aspect_rpc = map_aspect_ratio(aspect, is_video=False)
                res = await asyncio.wait_for(
                    client.generate_images(
                        prompt=prompt,
                        project_id=settings.FLOW_PROJECT_ID,
                        aspect_ratio=aspect_rpc,
                        seed=job.get("seed"),
                        count=1,
                    ),
                    timeout=timeout,
                )
                if res.get("status") == 200 and res.get("data", {}).get("media"):
                    media = res["data"]["media"][0]
                    source_url = (
                        media.get("url")
                        or media.get("image", {}).get("generatedImage", {}).get("fifeUrl")
                    )
                else:
                    error_msg = res.get("error") or "Image generation returned no media URL"

            # ── 2. Video Modes (T2V, I2V, References) ────────────────────────
            elif mode in ("t2v", "i2v", "references"):
                aspect_rpc = map_aspect_ratio(aspect, is_video=True)
                raw_duration = job.get("duration_seconds", 8) or 8
                duration = raw_duration if raw_duration in (4, 6, 8, 10) else 8

                # For Omni Flash Video modes
                if model == "omni_flash" or not job.get("seed_image_url"):
                    from fme_engine.services import omni_flash

                    if mode == "t2v":
                        gen_res = await omni_flash.generate_omni_flash_text_video(
                            prompt=prompt,
                            project_id=settings.FLOW_PROJECT_ID,
                            aspect_ratio=aspect_rpc,
                            duration_s=duration,
                            seed=job.get("seed"),
                        )
                    elif mode == "i2v" and job.get("last_frame_image_url"):
                        gen_res = await omni_flash.generate_omni_flash_first_last_video(
                            start_image_media_id=job["seed_image_url"],
                            end_image_media_id=job["last_frame_image_url"],
                            prompt=prompt,
                            project_id=settings.FLOW_PROJECT_ID,
                            aspect_ratio=aspect_rpc,
                            duration_s=duration,
                            seed=job.get("seed"),
                        )
                    elif mode == "references" and job.get("reference_image_urls"):
                        gen_res = await omni_flash.generate_omni_flash_video(
                            reference_media_ids=job["reference_image_urls"],
                            prompt=prompt,
                            project_id=settings.FLOW_PROJECT_ID,
                            aspect_ratio=aspect_rpc,
                            duration_s=duration,
                            seed=job.get("seed"),
                        )
                    else:
                        gen_res = await omni_flash.generate_omni_flash_first_frame_video(
                            start_image_media_id=job.get("seed_image_url") or "",
                            prompt=prompt,
                            project_id=settings.FLOW_PROJECT_ID,
                            aspect_ratio=aspect_rpc,
                            duration_s=duration,
                            seed=job.get("seed"),
                        )

                    # Poll operation or workflows until video URL is resolved
                    if gen_res.get("status") == 200:
                        data = gen_res.get("data", {})
                        if data.get("workflows"):
                            source_url, error_msg = await self._poll_omni_workflows(
                                data["workflows"], job_id, timeout
                            )
                        elif data.get("operations"):
                            ops = data["operations"]
                            source_url, error_msg = await self._poll_video_operations(
                                client, ops, job_id, timeout
                            )
                        else:
                            error_msg = "Video generation returned no operations or workflows"
                    else:
                        error_msg = gen_res.get("error") or "Video submission failed"

                else:
                    # Veo I2V fallback
                    gen_res = await client.generate_video(
                        start_image_media_id=job.get("seed_image_url"),
                        prompt=prompt,
                        project_id=settings.FLOW_PROJECT_ID,
                        scene_id=job_id,
                        aspect_ratio=aspect_rpc,
                    )
                    if gen_res.get("status") == 200 and gen_res.get("data", {}).get("operations"):
                        ops = gen_res["data"]["operations"]
                        source_url, error_msg = await self._poll_video_operations(client, ops, job_id, timeout)
                    else:
                        error_msg = gen_res.get("error") or "Veo video submission failed"

            # ── 3. Upscale Mode ──────────────────────────────────────────────
            elif mode == "upscale":
                res = await client.upscale_image(
                    media_id=job.get("seed_image_url") or "",
                    project_id=settings.FLOW_PROJECT_ID,
                )
                if res.get("status") == 200:
                    source_url = res.get("data", {}).get("encodedImage")
                else:
                    error_msg = res.get("error") or "Upscale failed"

            else:
                error_msg = f"Unsupported mode: {mode}"

        except asyncio.TimeoutError:
            error_msg = f"Job timed out after {timeout} seconds"
            logger.error("[Queue Worker] Job %s timed out", job_id)
        except Exception as exc:
            error_msg = str(exc)
            logger.exception("[Queue Worker] Generation exception on job %s: %s", job_id, exc)

        # ── 4. Ingestion & Completion ────────────────────────────────────────
        if source_url and not error_msg:
            logger.info("[Queue Worker] Generation succeeded for job %s. Offloading asset...", job_id)
            await crud.update_job(job_id, status="DOWNLOADING", progress=85, source_url=source_url)
            await event_bus.emit(f"job:{job_id}", {"status": "DOWNLOADING", "progress": 85})

            local_path = await download_asset(url=source_url, job_id=job_id, mode=mode)
            now = utc_now()
            download_url = f"/api/v1/assets/{job_id}"

            await crud.update_job(
                job_id,
                status="COMPLETED",
                progress=100,
                local_path=local_path,
                completed_at=now,
            )
            await event_bus.emit(
                f"job:{job_id}",
                {
                    "status": "COMPLETED",
                    "progress": 100,
                    "download_url": download_url,
                    "local_path": local_path,
                },
            )
            logger.info("[Queue Worker] <<< Job %s COMPLETED successfully!", job_id)

            # Webhook Dispatch
            if job.get("webhook_url"):
                asyncio.create_task(
                    dispatch_webhook(
                        job["webhook_url"],
                        {
                            "job_id": job_id,
                            "status": "COMPLETED",
                            "prompt": prompt,
                            "mode": mode,
                            "download_url": f"https://{settings.DOMAIN_NAME}{download_url}",
                            "completed_at": now,
                        },
                    )
                )

        else:
            logger.error("[Queue Worker] <<< Job %s FAILED: %s", job_id, error_msg)
            await crud.update_job(
                job_id,
                status="FAILED",
                progress=0,
                error_message=error_msg or "Unknown generation failure",
            )
            await event_bus.emit(
                f"job:{job_id}",
                {"status": "FAILED", "progress": 0, "error": error_msg},
            )

            if job.get("webhook_url"):
                asyncio.create_task(
                    dispatch_webhook(
                        job["webhook_url"],
                        {
                            "job_id": job_id,
                            "status": "FAILED",
                            "error": error_msg,
                        },
                    )
                )

    async def _poll_omni_workflows(
        self, workflows: list, job_id: str, timeout: float
    ) -> tuple[Optional[str], Optional[str]]:
        """Poll Omni workflow descriptors until finished media URL is available."""
        from fme_engine.services import omni_flash
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            await asyncio.sleep(5.0)
            status_res = await omni_flash.check_omni_flash_status(workflows)
            if status_res.get("done") and status_res.get("workflows"):
                for w in status_res["workflows"]:
                    if w.get("done") and w.get("media", {}).get("url"):
                        return w["media"]["url"], None
            elif status_res.get("workflows"):
                for w in status_res["workflows"]:
                    if w.get("done") and w.get("media", {}).get("url"):
                        return w["media"]["url"], None

            # Progress increment
            elapsed = time.monotonic() - start_time
            prog = min(80, int(20 + (elapsed / timeout) * 60))
            await crud.update_job(job_id, progress=prog)
            await event_bus.emit(f"job:{job_id}", {"status": "PROCESSING", "progress": prog})

        return None, f"Video polling timed out after {timeout} seconds"

    async def _poll_video_operations(
        self, client: Any, operations: list, job_id: str, timeout: float
    ) -> tuple[Optional[str], Optional[str]]:
        """Poll operations until completed or timeout."""
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            await asyncio.sleep(5.0)
            status_res = await client.check_video_status(operations)
            if status_res.get("status") == 200:
                ops_data = status_res.get("data", {}).get("operations", [])
                for op in ops_data:
                    op_status = op.get("status")
                    if op_status == "MEDIA_GENERATION_STATUS_SUCCESSFUL" or op.get("videoUrl"):
                        return op.get("videoUrl"), None
                    if op_status in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        return None, op.get("error") or "Upstream generation failed"

            # Progress increment
            elapsed = time.monotonic() - start_time
            prog = min(80, int(20 + (elapsed / timeout) * 60))
            await crud.update_job(job_id, progress=prog)
            await event_bus.emit(f"job:{job_id}", {"status": "PROCESSING", "progress": prog})

        return None, f"Video polling timed out after {timeout} seconds"


_worker = QueueWorker()

def get_queue_worker() -> QueueWorker:
    return _worker
