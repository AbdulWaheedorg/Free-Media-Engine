# Job Polling & SSE Real-Time Streaming

Once a job has been submitted to the Free Media Engine, clients can monitor its status either by polling the `/jobs/{job_id}` endpoint or by subscribing to real-time events via the Server-Sent Events (SSE) streaming endpoint `/jobs/{job_id}/stream`.

---

## 1. Get Job Status (`GET /api/v1/jobs/{job_id}`)

Retrieves the current state, progress percentage, and output download link for a specific job.

- **Method**: `GET`
- **Path**: `/api/v1/jobs/{job_id}`
- **Authentication**: `Bearer <API_KEY>`

### Response Schema

#### When Queued or In-Progress (200 OK)
```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "PROCESSING",
  "progress": 45,
  "prompt": "Aerial drone shot descending into a deep lush canyon with a roaring waterfall",
  "mode": "t2v",
  "model": "omni_flash",
  "download_url": null,
  "error_message": null,
  "created_at": "2026-10-09T18:44:48.371892Z",
  "completed_at": null
}
```

#### When Completed (200 OK)
```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "COMPLETED",
  "progress": 100,
  "prompt": "Aerial drone shot descending into a deep lush canyon with a roaring waterfall",
  "mode": "t2v",
  "model": "omni_flash",
  "download_url": "/api/v1/assets/83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "error_message": null,
  "created_at": "2026-10-09T18:44:48.371892Z",
  "completed_at": "2026-10-09T18:45:35.819402Z"
}
```

#### When Failed (200 OK)
```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "FAILED",
  "progress": 0,
  "prompt": "...",
  "download_url": null,
  "error_message": "Prompt triggered Google safety filter: VIOLENCE_POLICY",
  "created_at": "2026-10-09T18:44:48.371892Z",
  "completed_at": "2026-10-09T18:44:52.128471Z"
}
```

---

## 2. Server-Sent Events (SSE) Stream (`GET /api/v1/jobs/{job_id}/stream`)

Server-Sent Events provide an efficient, unidirectional stream of updates over a single persistent HTTP connection. SSE eliminates redundant polling loops and informs your application immediately when generation and asset downloads finish.

- **Method**: `GET`
- **Path**: `/api/v1/jobs/{job_id}/stream`
- **Authentication**: `Bearer <API_KEY>` (or query parameter `?token=<API_KEY>` for native browser EventSource)
- **Response Content-Type**: `text/event-stream`

### Stream Event Types

| Event Name | Description | Payload |
| :--- | :--- | :--- |
| `status` | Emitted whenever the job transitions state (`QUEUED`, `PROCESSING`, `DOWNLOADING`). | `{"status": "PROCESSING", "job_id": "..."}` |
| `progress` | Periodic integer progress updates (0% to 100%). | `{"progress": 65}` |
| `complete` | Dispatched immediately upon final media verification on VPS disk. | `{"status": "COMPLETED", "download_url": "/api/v1/assets/..."}` |
| `error` | Emitted if generation fails or times out. Connection closes immediately. | `{"status": "FAILED", "error": "Error reason"}` |

### Consuming SSE in JavaScript / Browser

```javascript
const jobId = "83a7acd5-46c8-4d97-9cb7-f759d6161524";
const apiKey = "<YOUR_FME_API_KEY>";

const eventSource = new EventSource(
  `https://flow.yourdomain.com/api/v1/jobs/${jobId}/stream?token=${apiKey}`
);

eventSource.addEventListener("status", (event) => {
  const data = JSON.parse(event.data);
  console.log(`Current Status: ${data.status}`);
});

eventSource.addEventListener("progress", (event) => {
  const data = JSON.parse(event.data);
  console.log(`Generation Progress: ${data.progress}%`);
});

eventSource.addEventListener("complete", (event) => {
  const data = JSON.parse(event.data);
  console.log(`Media is ready! Download at: ${data.download_url}`);
  eventSource.close();
});

eventSource.addEventListener("error", (event) => {
  console.error("Stream terminated or generation failed");
  eventSource.close();
});
```

### Consuming SSE in Python (`httpx_sse`)

```python
import httpx
from httpx_sse import connect_sse

API_KEY = "<YOUR_FME_API_KEY>"
STREAM_URL = "https://flow.yourdomain.com/api/v1/jobs/83a7acd5-46c8-4d97-9cb7-f759d6161524/stream"

with httpx.Client() as client:
    with connect_sse(client, "GET", STREAM_URL, headers={"Authorization": f"Bearer {API_KEY}"}) as event_source:
        for sse in event_source.iter_sse():
            print(f"Event: {sse.event} | Data: {sse.data}")
            if sse.event in ("complete", "error"):
                break
```

---

## 3. Cancel Job (`DELETE /api/v1/jobs/{job_id}`)

Cancels a job if it has not yet started execution (must be in `QUEUED` state).

- **Method**: `DELETE`
- **Path**: `/api/v1/jobs/{job_id}`
- **Authentication**: `Bearer <API_KEY>`

### Response (200 OK)
```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "CANCELED",
  "message": "Job removed from queue."
}
```

> [!NOTE]
> If a job is already in `PROCESSING` state, attempting to delete it will return `409 Conflict`, as canceling an in-flight Google Flow transaction mid-cycle would risk DOM synchronization corruption.
