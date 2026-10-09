# Adding New Modes & Extending Models

This walkthrough explains how to extend Free Media Engine with new generation modes, models, or post-processing features.

---

## 🗺️ Extension Lifecycle Overview

Adding a new feature (for example: an `upscale_4k` mode or a new model family) requires updates across six layers:

```
[1. Pydantic Schemas] ──► [2. Database CRUD] ──► [3. WebSocket RPC]
          │
          ▼
[4. Extension Bridge] ──► [5. Queue Dispatcher] ──► [6. API & CLI Routes]
```

---

## 🛠️ Step-by-Step Implementation Guide

### Step 1: Update Pydantic Schemas (`fme_engine/models/schemas.py`)
Add the new mode or model to the enumeration types:

```python
# In fme_engine/models/schemas.py
from typing import Literal

# Add new mode literal
GenerationMode = Literal["t2v", "i2v", "t2i", "references", "upscale_4k"]

# Update GenerateRequest schema
class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    mode: GenerationMode = "t2v"
    source_media_url: Optional[str] = Field(None, description="Source media for 4K upscaling")
    # ... other fields
```

---

### Step 2: Database Schema & CRUD (`fme_engine/db/`)
If the new feature introduces new metadata fields (such as `upscale_factor` or `source_media_url`), update the SQLite schema in `fme_engine/db/database.py`:

```python
# In fme_engine/db/database.py
CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    api_key_id INTEGER,
    prompt TEXT,
    mode TEXT,
    model TEXT,
    aspect_ratio TEXT,
    duration INTEGER,
    source_media_url TEXT,  -- New column
    status TEXT DEFAULT 'QUEUED',
    -- ...
);
"""
```

And update the corresponding helper in `fme_engine/db/crud.py`:
```python
# In fme_engine/db/crud.py
async def create_job(db: aiosqlite.Connection, job: GenerateRequest, api_key_id: int) -> JobRecord:
    # Add new column binding to INSERT query
```

---

### Step 3: WebSocket RPC Bridge (`fme_engine/services/ws_bridge.py`)
Ensure the outbound JSON envelope passes the new parameters to the extension:

```python
# In fme_engine/services/ws_bridge.py
command_payload = {
    "action": "GENERATE",
    "job_id": job.id,
    "mode": job.mode,
    "source_media_url": job.source_media_url,
    # ...
}
```

---

### Step 4: Extension DOM Execution (`fme_extension/content.js`)
Implement the client-side RPC mapping in `fme_extension/content.js` to dispatch the corresponding Google Flow `batchexecute` action:

```javascript
// In fme_extension/content.js
if (msg.action === "GENERATE" && msg.mode === "upscale_4k") {
  executeBatchUpscale(msg.job_id, msg.source_media_url);
}
```

---

### Step 5: Queue Worker Dispatch (`fme_engine/worker/queue.py`)
Route the new mode to the appropriate execution or polling handler:

```python
# In fme_engine/worker/queue.py
if job.mode == "upscale_4k":
    result = await self.ws_bridge.send_upscale_command(job)
    output_url = result["url"]
```

---

### Step 6: CLI & API Exposure (`fme_engine/cli/main.py`)
Add support in the Typer CLI:

```python
# In fme_engine/cli/main.py
@app.command()
def upscale(
    source_url: str = typer.Argument(..., help="Source video URL to upscale"),
    wait: bool = typer.Option(True, help="Wait for upscale completion")
):
    """Upscale video to 4K resolution."""
    # Send request to POST /api/v1/generate with mode='upscale_4k'
```

---

## 🧪 Verifying the New Feature

1. **Unit Test**: Test request validation with valid and invalid parameters using `pytest`.
2. **Local Daemon Test**: Launch `uvicorn fme_engine.api.app:app --reload` and verify OpenAPI docs at `http://127.0.0.1:8120/docs`.
3. **End-to-End Test**: Submit a job and verify the media file is saved to `/data/outputs/`.
