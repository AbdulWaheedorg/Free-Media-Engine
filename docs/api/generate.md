# Generation Endpoints (`POST /api/v1/generate`)

The `/api/v1/generate` endpoint dispatches text-to-image and generative video creation tasks to the asynchronous queue.

---

## 📋 Endpoint Specification

- **Method**: `POST`
- **Path**: `/api/v1/generate`
- **Authentication**: `Bearer <API_KEY>`
- **Content-Type**: `application/json`

---

## 📥 Request Body Schema

```json
{
  "prompt": "string",
  "mode": "t2v",
  "model": "omni_flash",
  "aspect_ratio": "16:9",
  "duration": 8,
  "seed_image_url": null,
  "last_image_url": null,
  "reference_image_urls": [],
  "negative_prompt": null,
  "webhook_url": null
}
```

### Parameter Reference

| Field | Type | Required | Default | Allowed Values & Description |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | `string` | **Yes** | — | Description of the scene or image to generate (max 4,000 characters). |
| `mode` | `string` | No | `"t2v"` | `"t2v"` (Text-to-Video)<br>`"t2i"` (Text-to-Image)<br>`"i2v"` (Image-to-Video)<br>`"references"` (Reference-Guided Video) |
| `model` | `string` | No | `"omni_flash"` | `"omni_flash"` (Gemini Omni 1.1 Flash — Fast, high dynamic motion)<br>`"veo"` (High-fidelity cinematic render) |
| `aspect_ratio` | `string` | No | `"16:9"` | `"16:9"` (Landscape Widescreen)<br>`"9:16"` (Portrait / Mobile / TikTok)<br>`"1:1"` (Square) |
| `duration` | `integer`| No | `8` | Valid durations for Omni Flash are strictly `4`, `6`, `8`, or `10` seconds. |
| `seed_image_url` | `string` | No | `null` | Public HTTPS URL of the starting frame for `"i2v"` mode. |
| `last_image_url` | `string` | No | `null` | Public HTTPS URL of the ending frame for first-to-last frame interpolation. |
| `reference_image_urls` | `array` | No | `[]` | List of HTTPS URLs (up to 3) used as visual style/actor anchors. |
| `negative_prompt` | `string` | No | `null` | Elements to avoid in the generation (e.g. `"blurry, low quality, artifacts"`). |
| `webhook_url` | `string` | No | `null` | HTTPS endpoint to receive an automated JSON payload when the job completes. |

---

## 📤 Response Schema

### `202 Accepted`
```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "QUEUED",
  "queue_position": 1,
  "created_at": "2026-10-09T18:44:48.371892Z"
}
```

---

## 💡 Practical Examples

### 1. Text-to-Image (2K Photographic Render)
```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Studio portrait of an elderly watchmaker assembling a vintage brass pocket watch, intricate gears, shallow depth of field, dramatic rim lighting, 8k photographic masterwork",
    "mode": "t2i",
    "aspect_ratio": "16:9"
  }'
```

---

### 2. Text-to-Video via Gemini Omni Flash (16:9, 8 Seconds)
```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hyper-realistic slow motion shot of an eagle swooping over a misty alpine lake at sunrise, water droplets flying off the talons, cinematic 4k",
    "mode": "t2v",
    "model": "omni_flash",
    "duration": 8,
    "aspect_ratio": "16:9"
  }'
```

---

### 3. Image-to-Video (First Frame Animation)
Animate an existing static image by providing the starting frame URL:

```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Camera pans slowly around the cybernetic warrior as neon reflections glisten across their chrome armor, smoke drifting across the alley",
    "mode": "i2v",
    "seed_image_url": "https://example.com/character-frame.png",
    "duration": 6,
    "aspect_ratio": "16:9"
  }'
```

---

### 4. First-and-Last Frame Transition
Generate a seamless video bridge transitioning smoothly between two designated visual states:

```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Time-lapse transition of a desert landscape transforming from a scorched sunny afternoon into a starry night with aurora borealis",
    "mode": "i2v",
    "seed_image_url": "https://example.com/day-frame.png",
    "last_image_url": "https://example.com/night-frame.png",
    "duration": 8,
    "aspect_ratio": "16:9"
  }'
```

---

### 5. Automated Webhook Notification
Provide a `webhook_url` to eliminate client-side polling. FME will automatically POST the completion envelope directly to your service:

```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Futuristic flying sports car zipping through glowing skyscrapers in Neo Tokyo",
    "mode": "t2v",
    "duration": 8,
    "webhook_url": "https://your-api.com/webhooks/fme-completion"
  }'
```

---

## 💻 Client Code Examples

### Python Client
```python
import requests

API_KEY = "<YOUR_FME_API_KEY>"
BASE_URL = "https://flow.yourdomain.com/api/v1"

def submit_video_job(prompt: str) -> str:
    response = requests.post(
        f"{BASE_URL}/generate",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "prompt": prompt,
            "mode": "t2v",
            "model": "omni_flash",
            "duration": 8,
            "aspect_ratio": "16:9"
        }
    )
    response.raise_for_status()
    payload = response.json()
    print(f"Queued Job ID: {payload['job_id']} (Position: {payload['queue_position']})")
    return payload["job_id"]

if __name__ == "__main__":
    submit_video_job("Futuristic botanical garden on Mars with bioluminescent plants")
```

### TypeScript / Node.js Client
```typescript
interface GenerateResponse {
  job_id: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  queue_position: number;
  created_at: string;
}

async function createGeneration(prompt: string): Promise<string> {
  const apiKey = "<YOUR_FME_API_KEY>";
  const endpoint = "https://flow.yourdomain.com/api/v1/generate";

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      prompt,
      mode: "t2i",
      aspect_ratio: "16:9"
    })
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`FME API Error (${response.status}): ${errorBody}`);
  }

  const data: GenerateResponse = await response.json();
  console.log(`Job Created: ${data.job_id}`);
  return data.job_id;
}
```
