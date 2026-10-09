# Browser Extension Internals & Upstream Bridge

This document details the inner workings of the `fme_extension` Chrome extension, how it interacts with Google Flow's DOM in the MAIN execution world, and how it translates batch RPCs across the WebSocket bridge.

---

## 🧩 Why a Browser Extension is Mandatory

Following Google's decommission of the legacy REST endpoint (`aisandbox-pa.googleapis.com`), all generation calls on `flow.google.com` operate exclusively via Google's internal `batchexecute` RPC framework.

Every call requires three ambient runtime assets that cannot be synthesized by headless scripts:
1. **Live Session State**: Valid Google authentication cookies (`SID`, `SSID`, `HSID`, `OSID`).
2. **Dynamic Context Signing**: Ambient anti-CSRF tokens (`f.req`, `at=`) minted dynamically by Google's client JavaScript.
3. **In-Context reCAPTCHA Minting**: A single-use verification token generated inside the active page's event loop.

By executing generations from an extension running directly inside the open canvas tab, the calls originate natively within Google's human evaluation perimeter.

---

## 📂 Extension Files & Manifest V3 Structure

```
fme_extension/
├── manifest.json       # Manifest V3 definitions & permission scopes
├── background.js       # Background service worker & WebSocket relay
└── content.js          # In-page script running in MAIN world
```

### 1. `manifest.json`
```json
{
  "manifest_version": 3,
  "name": "Free Media Engine Bridge",
  "version": "1.0.0",
  "description": "Local bridge extension connecting Free Media Engine to Google Flow workspace.",
  "permissions": [
    "storage",
    "activeTab"
  ],
  "host_permissions": [
    "https://flow.google.com/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://flow.google.com/*"],
      "js": ["content.js"],
      "run_at": "document_start",
      "world": "MAIN"
    }
  ]
}
```

> [!IMPORTANT]
> **MAIN World Execution (`"world": "MAIN"`)**:
> Modern Manifest V3 extensions default to `ISOLATED` world execution, which prevents them from accessing page JavaScript variables and prototype functions. Free Media Engine specifies `"world": "MAIN"`, allowing `content.js` to execute in the exact same JavaScript context as Google Flow.

---

## ⚡ WebSocket Bridge Communication Protocol

The extension and backend daemon exchange JSON envelopes across `ws://127.0.0.1:9222`:

### 1. Inbound Command (Daemon $\rightarrow$ Extension)
Dispatched when the queue worker begins processing a job:

```json
{
  "action": "GENERATE",
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "project_id": "00000000-0000-0000-0000-000000000000",
  "prompt": "Aerial drone shot descending into a deep lush canyon with a roaring waterfall",
  "mode": "t2v",
  "model_family": "omni_flash",
  "aspect_ratio": "16:9",
  "duration": 8,
  "seed_image_url": null,
  "reference_image_urls": [],
  "allow_degraded": true
}
```

### 2. Status Update (Extension $\rightarrow$ Daemon)
Emitted periodically during upstream rendering:

```json
{
  "type": "STATUS_UPDATE",
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "payload": {
    "state": "RENDERING",
    "progress": 55,
    "current_step": "synthesizing_frames"
  }
}
```

### 3. Completion Event (Extension $\rightarrow$ Daemon)
Dispatched when the generation completes and Google returns the media artifact URL:

```json
{
  "type": "GENERATION_COMPLETE",
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "payload": {
    "url": "https://lh3.googleusercontent.com/fife/ABSRl...",
    "mime_type": "video/mp4",
    "width": 1920,
    "height": 1080,
    "duration_seconds": 8
  }
}
```

### 4. Error Event (Extension $\rightarrow$ Daemon)
Emitted if Google Flow rejects the transaction:

```json
{
  "type": "ERROR",
  "job_id": "83a7acd5-46c8-4d97-9cb7-f759d6161524",
  "payload": {
    "error_code": "SAFETY_POLICY_VIOLATION",
    "message": "Prompt blocked by safety classifier."
  }
}
```

---

## 🛠️ Handling Upstream Google Flow Changes

If Google updates the DOM or alters RPC payload structures:
1. Open KasmVNC at `https://localhost:6901` and open Chromium DevTools (`F12`) on the Google Flow tab.
2. In the Network tab, filter for `batchexecute` requests during a manual generation.
3. Inspect the `f.req` payload array structure.
4. Update the corresponding serializing logic in `fme_extension/content.js`.
5. Reload the extension at `chrome://extensions/` and trigger a test generation.
