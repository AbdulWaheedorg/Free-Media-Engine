# Queue Daemon & Anti-Abuse Rate Pacing

This document explains the queuing architecture, rate pacing heuristics, and worker lifecycle managed by `fme_engine/worker/queue.py`.

---

## 🏗️ Architectural Invariants

### 1. Strict Sequential Processing (`concurrency = 1`)
Google Flow workspaces operate on a stateful, client-side React/WebGL canvas model. Submitting simultaneous generations in parallel causes:
- Overlapping `batchexecute` mutations that corrupt canvas project tree state.
- Client-side DOM race conditions where multiple active progress bars conflict.
- Heightened risk of Google anti-abuse rate throttling.

To prevent this, the Free Media Engine worker is strictly single-threaded:
```python
# fme_engine/worker/queue.py
class GenerationQueue:
    def __init__(self):
        self._concurrency = 1
        self._lock = asyncio.Lock()
        self._active_job_id: Optional[str] = None
```

---

## ⏱️ Jitter Rate Pacing ($5\text{s}$–$12\text{s}$)

Automated traffic dispatching at exact mathematical intervals (e.g. exactly every 10.00 seconds) creates a distinct signature in datacenter telemetry.

Between consecutive jobs, the queue worker enforces a pseudo-random jitter delay:

```python
import random
import asyncio

async def apply_jitter_pacing(min_delay: float = 5.0, max_delay: float = 12.0):
    delay = random.uniform(min_delay, max_delay)
    logger.info(f"Applying anti-abuse pacing interval: {delay:.2f}s")
    await asyncio.sleep(delay)
```

Configurable via `.env`:
- `PACING_MIN_DELAY=5`
- `PACING_MAX_DELAY=12`

---

## ⏳ Execution Timeouts & Stall Recovery

Generations occasionally stall upstream due to Google GPU queue congestion or transient canvas disconnects. The queue worker enforces strict timeouts per job:

| Mode | Max Timeout | Behavior on Expiry |
| :--- | :--- | :--- |
| **Images (`t2i`)** | **45 seconds** | Marks job as `STALLED`, logs timeout, releases worker lock. |
| **Videos (`t2v`, `i2v`)** | **180 seconds** | Marks job as `STALLED`, alerts supervisor, triggers tab refresh. |

If a job times out:
1. Status flips to `STALLED` with `error_message: "Generation timed out after 180s."`.
2. The worker releases the queue lock so subsequent queued jobs are not blocked indefinitely.
3. The supervisor issues a reload command to the Google Flow tab to reset canvas state.

---

## 💾 Asset Streaming & Verification Pipeline

When Google Flow returns a temporary CDN media link, the daemon invokes `fme_engine/services/downloader.py` to offload the asset immediately:

```
[Google CDN URL] ───(HTTP Stream)───► [Host Disk: /data/outputs/{job_id}.mp4]
                                                       │
                                            (File Size > 0 Verification)
                                                       │
                                        [DB Updated: status = COMPLETED]
                                                       │
                                      [Optional Webhook Dispatched]
```

### Verification Criteria
Before marking any job as `COMPLETED`:
1. The media stream must complete with HTTP `200 OK`.
2. The saved local file must exist on the filesystem (`os.path.exists`).
3. The file size must exceed a non-zero threshold (e.g., $>50\text{ KB}$ for images, $>500\text{ KB}$ for videos).
4. If the download fails or the file is empty, the job transitions to `FAILED`.

---

## 🔔 Asynchronous Webhook Dispatch

If the job request included a `webhook_url`, the daemon asynchronously dispatches the final payload upon completion:

```python
async def dispatch_completion_webhook(webhook_url: str, payload: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(webhook_url, json=payload)
        except Exception as exc:
            logger.warning(f"Failed to deliver completion webhook to {webhook_url}: {exc}")
```
