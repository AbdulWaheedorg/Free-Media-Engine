# Scene Composition & Sequencing (`/api/v1/scenes` & `/api/v1/videos`)

Creating complex narratives and short films requires organizing individual generations into sequential shots and scenes. Free Media Engine provides high-level primitives for tracking multi-shot storyboard projects and linking individual generation outputs.

---

## 🎬 Concepts

- **Scene**: An individual shot or generation unit with a sequence index, duration, prompt, and optional character linkage.
- **Video**: A container grouping multiple scenes into a cohesive film project with an ordered timeline.

---

## 📋 Endpoints Reference

### 1. Create a Scene (`POST /api/v1/scenes`)
Registers an individual scene item in a production storyboard.

- **Method**: `POST`
- **Path**: `/api/v1/scenes`
- **Authentication**: `Bearer <API_KEY>`

#### Request Body
```json
{
  "title": "Establishing Shot - Neon Market",
  "prompt": "Wide angle drone shot moving forward over a bustling futuristic Asian night market, rain falling, steam rising from food stalls",
  "sequence_order": 1,
  "duration": 8,
  "character_id": null
}
```

#### Response (`201 Created`)
```json
{
  "id": "scene_e49b01c4",
  "title": "Establishing Shot - Neon Market",
  "sequence_order": 1,
  "duration": 8,
  "job_id": null,
  "status": "DRAFT",
  "created_at": "2026-10-09T18:55:00Z"
}
```

---

### 2. Link Scene to Generation Output (`PUT /api/v1/scenes/{id}`)
Connects a completed generation `job_id` to the scene slot:

```json
{
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "status": "RENDERED"
}
```

---

### 3. Create Multi-Scene Project (`POST /api/v1/videos`)
Combines multiple scenes into a finished video project.

- **Method**: `POST`
- **Path**: `/api/v1/videos`
- **Authentication**: `Bearer <API_KEY>`

#### Request Body
```json
{
  "title": "Cyberpunk Chronicles - Episode 1",
  "scene_ids": [
    "scene_e49b01c4",
    "scene_a12f99b2",
    "scene_ff40112d"
  ]
}
```

#### Response (`201 Created`)
```json
{
  "id": "vid_99f30128ba",
  "title": "Cyberpunk Chronicles - Episode 1",
  "total_scenes": 3,
  "total_duration_seconds": 24,
  "created_at": "2026-10-09T18:56:00Z"
}
```

---

## 💻 Multi-Shot Storyboard Pipeline (Python)

```python
import time
import requests

API_KEY = "<YOUR_FME_API_KEY>"
BASE_URL = "https://flow.yourdomain.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

SHOTS = [
    {"order": 1, "prompt": "Wide drone shot descending towards an ancient misty mountain monastery at dawn", "duration": 8},
    {"order": 2, "prompt": "Medium shot of an elderly monk striking a massive brass temple bell, resonance vibrations", "duration": 6},
    {"order": 3, "prompt": "Close-up of golden cherry blossoms fluttering in the breeze as birds fly into the sunrise", "duration": 8}
]

def render_storyboard():
    rendered_assets = []
    
    for shot in SHOTS:
        print(f"[*] Submitting Shot #{shot['order']}: {shot['prompt'][:50]}...")
        resp = requests.post(
            f"{BASE_URL}/generate",
            headers=HEADERS,
            json={"prompt": shot["prompt"], "mode": "t2v", "duration": shot["duration"], "aspect_ratio": "16:9"}
        ).json()
        job_id = resp["job_id"]
        
        # Poll completion
        while True:
            job_status = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS).json()
            if job_status["status"] == "COMPLETED":
                print(f"[+] Shot #{shot['order']} completed! Asset: {job_status['download_url']}")
                rendered_assets.append(job_status["download_url"])
                break
            elif job_status["status"] == "FAILED":
                raise RuntimeError(f"Shot #{shot['order']} failed: {job_status['error_message']}")
            time.sleep(5)
            
    print(f"\n[🎉] All {len(rendered_assets)} shots generated successfully!")
    return rendered_assets

if __name__ == "__main__":
    render_storyboard()
```
