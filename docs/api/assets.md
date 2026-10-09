# Binary Asset Streaming & Storage (`GET /api/v1/assets/{job_id}`)

Google Flow's internal CDN links are temporary signed URLs that expire after short intervals. To guarantee persistent access, Free Media Engine streams completed renders directly to local VPS storage (`/data/outputs/{job_id}.mp4` or `.png`) and exposes an authenticated streaming endpoint.

---

## 📋 Endpoint Specification

- **Method**: `GET`
- **Path**: `/api/v1/assets/{job_id}`
- **Authentication**: `Bearer <API_KEY>` OR `?token=<API_KEY>`
- **Response Headers**:
  - `Content-Type`: `video/mp4` or `image/png`
  - `Accept-Ranges`: `bytes`
  - `Content-Disposition`: `inline; filename="{job_id}.mp4"`

---

## 🎬 Native Range Requests & Video Player Scrubbing

Video assets support RFC 7233 HTTP Range Requests. This allows mobile devices, Safari, Chrome, and modern web video players to stream and scrub forward and backward through large MP4 video files without buffering the entire file first.

### Example Range Request (Header)
```http
GET /api/v1/assets/83a7acd5-46c8-4d97-9cb7-f759d6161524 HTTP/1.1
Host: flow.yourdomain.com
Authorization: Bearer <YOUR_FME_API_KEY>
Range: bytes=0-1048575
```

### Expected Response (`206 Partial Content`)
```http
HTTP/1.1 206 Partial Content
Content-Type: video/mp4
Content-Range: bytes 0-1048575/7065902
Content-Length: 1048576
Accept-Ranges: bytes
```

---

## 💻 Embedding in HTML Web Applications

Because standard HTML `<video>` and `<img>` tags cannot pass custom HTTP `Authorization: Bearer` headers, FME supports passing the key via the `?token=` query parameter:

### Embedding Video
```html
<video controls width="100%" poster="/preview.png">
  <source 
    src="https://flow.yourdomain.com/api/v1/assets/83a7acd5-46c8-4d97-9cb7-f759d6161524?token=<YOUR_FME_API_KEY>" 
    type="video/mp4"
  >
  Your browser does not support the video tag.
</video>
```

### Embedding Image
```html
<img 
  src="https://flow.yourdomain.com/api/v1/assets/71e9e6fa-47b9-464b-87ec-78273afeff59?token=<YOUR_FME_API_KEY>" 
  alt="Generated Lion Portrait"
/>
```

---

## 📥 Downloading Finished Assets

### Via cURL
```bash
curl -X GET "https://flow.yourdomain.com/api/v1/assets/83a7acd5-46c8-4d97-9cb7-f759d6161524" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  --output "waterfall_scene.mp4"
```

### Via Python (Chunked Streaming Download)
```python
import requests

API_KEY = "<YOUR_FME_API_KEY>"
JOB_ID = "83a7acd5-46c8-4d97-9cb7-f759d6161524"
OUTPUT_PATH = "lion_photo.png"

url = f"https://flow.yourdomain.com/api/v1/assets/{JOB_ID}"
headers = {"Authorization": f"Bearer {API_KEY}"}

with requests.get(url, headers=headers, stream=True) as response:
    response.raise_for_status()
    with open(OUTPUT_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

print(f"Successfully downloaded to {OUTPUT_PATH}")
```

### Via Node.js (Stream Pipeline)
```javascript
import fs from "fs";
import { pipeline } from "stream/promises";

async function downloadAsset(jobId, destPath) {
  const apiKey = "<YOUR_FME_API_KEY>";
  const url = `https://flow.yourdomain.com/api/v1/assets/${jobId}`;

  const response = await fetch(url, {
    headers: { "Authorization": `Bearer ${apiKey}` }
  });

  if (!response.ok) {
    throw new Error(`Download failed with status: ${response.status}`);
  }

  const fileStream = fs.createWriteStream(destPath);
  await pipeline(response.body, fileStream);
  console.log(`Saved asset to ${destPath}`);
}
```
