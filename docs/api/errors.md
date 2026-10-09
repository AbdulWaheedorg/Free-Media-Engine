# Errors, Edge Cases & Rate Limits

This reference documents the error codes, upstream edge cases, and automated mitigations implemented in Free Media Engine.

---

## 🚦 HTTP Status Code Reference

| Status Code | Reason | Cause | Client Resolution |
| :--- | :--- | :--- | :--- |
| `200 OK` | Success | The operation completed successfully. | Process response payload. |
| `202 Accepted` | Job Queued | Generation job accepted and placed in the queue. | Poll status or open SSE stream. |
| `400 Bad Request` | Invalid Arguments | Invalid prompt length, unrecognized mode, or unsupported aspect ratio. | Correct request parameters. |
| `401 Unauthorized` | Invalid / Revoked Key | Missing `Authorization: Bearer` header, invalid token, or revoked key. | Check API key validity or issue a new key. |
| `404 Not Found` | Not Found | `job_id`, `character_id`, or `asset_id` does not exist in the database. | Verify the requested UUID. |
| `409 Conflict` | Operation Conflict | Attempting to delete a job currently in `PROCESSING` state. | Wait for job completion or failure. |
| `422 Unprocessable` | Schema Mismatch | Missing required JSON fields or incorrect types. | Inspect FastAPI validation errors in response. |
| `502 Bad Gateway` | Upstream RPC Error | Google Flow returned an unhandled RPC error. | Review job `error_message`; retry with modified prompt. |
| `503 Service Unavailable` | Extension Offline | The Chrome extension WebSocket bridge is disconnected or Chromium crashed. | Check `/api/v1/health` or restart browser container. |
| `504 Gateway Timeout` | Timeout Exceeded | Job exceeded execution threshold (180s video / 45s image). | Job automatically marked `STALLED`. |

---

## 🔍 Upstream Error Code Matrix

When a generation fails upstream inside Google Flow, the `error_message` field in the job payload is populated with a descriptive error identifier:

### 1. `SAFETY_POLICY_VIOLATION`
- **Cause**: Google's upstream safety classifier detected disallowed terms (violence, adult content, copyrighted characters, political likenesses) in the prompt or seed image.
- **Handling**: Modify the prompt to use neutral, descriptive language. The queue worker immediately releases the slot and moves to the next job.

### 2. `UNSUPPORTED_ON_BATCH_API`
- **Cause**: A combination of settings (e.g., specific Veo resolution modes or unsupported frame chaining) is restricted by Google's batch execute engine.
- **Handling**: Use Omni Flash (`omni_flash`) and standard duration values (`4`, `6`, `8`, or `10` seconds).

### 3. `FLOW_WORKSPACE_REDIRECT`
- **Cause**: Google Flow dropped the user session and redirected the active tab to `accounts.google.com` or a 2FA challenge.
- **Handling**: The queue worker pauses execution to prevent repeated authentication failures and fires an alert. The operator opens KasmVNC at `https://localhost:6901` to resolve the prompt once.

### 4. `EXTENSION_DISCONNECTED`
- **Cause**: The browser extension's WebSocket connection on port 9222 was severed (e.g., browser tab crashed or container restarted).
- **Handling**: The daemon's WebSocket supervisor automatically attempts continuous exponential backoff reconnection.

---

## 🔁 Recommended Client Retry Policy

When building external microservices that consume FME, implement the following retry guidelines:

```
                  ┌───────────────────────┐
                  │ API Request Dispatched│
                  └───────────┬───────────┘
                              │
                     HTTP Status Code?
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
        401 / 400         429 / 503           202 / 200
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ DO NOT RETRY  │ │ RETRY WITH    │ │ SUCCESS       │
    │ Check key or  │ │ EXPONENTIAL   │ │ Continue      │
    │ request data  │ │ BACKOFF       │ │ workflow      │
    └───────────────┘ └───────────────┘ └───────────────┘
```

### Python Retry Helper
```python
import time
import requests

def call_with_backoff(url, headers, json_data, max_attempts=4):
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=15)
            if response.status_code in (200, 202):
                return response.json()
            elif response.status_code in (400, 401, 404, 422):
                # Permanent client errors - fail immediately
                raise RuntimeError(f"Client Error ({response.status_code}): {response.text}")
            elif response.status_code in (429, 502, 503, 504):
                # Transient errors - retry with backoff
                backoff = 2 ** attempt
                print(f"[!] Transient status {response.status_code}. Retrying in {backoff}s...")
                time.sleep(backoff)
        except requests.RequestException as exc:
            backoff = 2 ** attempt
            print(f"[!] Network error: {exc}. Retrying in {backoff}s...")
            time.sleep(backoff)
            
    raise TimeoutError("Exceeded maximum retry attempts.")
```
