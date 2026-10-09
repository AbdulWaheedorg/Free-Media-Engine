# Character Consistency Engine (`/api/v1/characters`)

Generative video models frequently struggle to maintain consistent facial features, clothing, and anatomical characteristics across distinct camera angles and scene cuts. Free Media Engine solves this by storing and managing **Character Anchors** that are automatically injected as reference conditioners into downstream generation runs.

---

## 🎭 Character Workflow Overview

```
1. Create Character Profile (POST /characters)
   └── Supplies 1–3 reference portraits and a canonical description
2. Submit Generation referencing Character ID
   └── Engine pulls reference frames & applies Gemini Omni Flash conditioning
3. Result: Multiple scenes featuring the exact same actor/character persona
```

---

## 📋 Endpoints Reference

### 1. Create Character (`POST /api/v1/characters`)
Creates and registers a new persistent character persona in the database.

- **Method**: `POST`
- **Path**: `/api/v1/characters`
- **Authentication**: `Bearer <API_KEY>`
- **Content-Type**: `application/json`

#### Request Body
```json
{
  "name": "Captain Amelia Vance",
  "description": "Mid-30s female astronaut with short auburn hair, hazel eyes, wearing a weathered white spacesuit with blue accents",
  "reference_image_urls": [
    "https://example.com/portraits/amelia_front.png",
    "https://example.com/portraits/amelia_side.png"
  ]
}
```

#### Response (`201 Created`)
```json
{
  "id": "char_8df1c3a09b",
  "name": "Captain Amelia Vance",
  "description": "Mid-30s female astronaut with short auburn hair...",
  "reference_image_urls": [
    "https://example.com/portraits/amelia_front.png",
    "https://example.com/portraits/amelia_side.png"
  ],
  "created_at": "2026-10-09T18:50:00Z"
}
```

---

### 2. List Characters (`GET /api/v1/characters`)
Returns all active character profiles created under the caller's organization.

- **Method**: `GET`
- **Path**: `/api/v1/characters`
- **Authentication**: `Bearer <API_KEY>`

#### Response (`200 OK`)
```json
[
  {
    "id": "char_8df1c3a09b",
    "name": "Captain Amelia Vance",
    "reference_count": 2,
    "created_at": "2026-10-09T18:50:00Z"
  }
]
```

---

### 3. Generate Video with Character Persona
To generate a video utilizing an anchor character, reference the character's reference image URLs in `reference_image_urls`:

```bash
curl -X POST "https://flow.yourdomain.com/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_FME_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Captain Amelia Vance inspecting the broken nav-computer on a damaged spaceship, red emergency beacons pulsing, intense concentration",
    "mode": "references",
    "model": "omni_flash",
    "duration": 8,
    "reference_image_urls": [
      "https://example.com/portraits/amelia_front.png",
      "https://example.com/portraits/amelia_side.png"
    ]
  }'
```

---

### 4. Delete Character (`DELETE /api/v1/characters/{id}`)
Removes a character profile from the database.

- **Method**: `DELETE`
- **Path**: `/api/v1/characters/{id}`
- **Authentication**: `Bearer <API_KEY>`

#### Response (`200 OK`)
```json
{
  "id": "char_8df1c3a09b",
  "status": "DELETED"
}
```
