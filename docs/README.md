# Free Media Engine (FME) Documentation

Welcome to the official documentation for **Free Media Engine (FME)** — an enterprise-grade, unattended automation engine, authenticated REST API, and accompanying CLI for generating high-fidelity generative video and images via Google Flow (`flow.google.com`).

---

## 📚 Documentation Table of Contents

### 🌐 Part I: API Reference (`docs/api/`)
Learn how to authenticate, submit generation jobs, stream real-time events, download high-definition media, manage consistent characters, and handle API keys from any external application, web service, or client.

1. [API Overview & Authentication](file:///docs/api/overview.md)
   - Architecture overview, Base URLs, Bearer key authentication (`fme_live_...`), constant-time verification, queue concurrency, and status lifecycle.
2. [Generation Endpoints (`POST /api/v1/generate`)](file:///docs/api/generate.md)
   - Text-to-Video (`t2v`), Image-to-Video (`i2v`), Text-to-Image 2K (`t2i`), Reference-to-Video, model selectors (`omni_flash` vs `veo`), duration, aspect ratios, and complete code samples in cURL, Python, and TypeScript.
3. [Job Polling & SSE Real-Time Streaming](file:///docs/api/jobs.md)
   - Inspecting job status (`GET /jobs/{id}`), canceling pending jobs (`DELETE /jobs/{id}`), and consuming Server-Sent Events (`GET /jobs/{id}/stream`) for real-time progress updates without polling.
4. [Binary Asset Streaming & Storage](file:///docs/api/assets.md)
   - Authenticated direct asset retrieval (`GET /assets/{id}`), HTTP `206 Partial Content` video range streaming, storage locations, and local offloading guarantees.
5. [Character Consistency Engine](file:///docs/api/characters.md)
   - Creating reusable character anchors (`POST /characters`), face reference embeddings, and generating multi-scene videos with consistent actor identity.
6. [Scene Composition & Sequencing](file:///docs/api/scenes.md)
   - Multi-shot scene management (`POST /scenes`), timeline ordering, and compiling finished multi-scene video packages (`POST /videos`).
7. [API Key Management & Revocation](file:///docs/api/admin-keys.md)
   - Creating scoped keys, instant zero-downtime revocation (`<50ms`), listing keys, and emergency master key override.
8. [Errors, Edge Cases & Rate Limits](file:///docs/api/errors.md)
   - Standardized HTTP status codes, upstream error recovery (`UNSUPPORTED_ON_BATCH_API`, quota flags), retry strategies, and rate limits.

---

### 🛠️ Part II: Engineering & Development Guide (`docs/development/`)
Everything an engineer or contributor needs to understand the architecture, run the system locally, extend models, modify the browser extension, and deploy updates safely.

1. [Architecture & Hybrid Relay Pattern](file:///docs/development/architecture.md)
   - Deep dive into the 4 isolation tiers: Reverse Proxy Gateway, Queue Daemon, WebSocket Bridge, and Headed Virtual Frame Chromium.
2. [Local Setup & Development Workflow](file:///docs/development/local-setup.md)
   - Setting up a local virtual environment, installing dependencies, configuring `.env`, running unit tests, and spinning up the mock bridge.
3. [Browser Extension Internals & Upstream Bridge](file:///docs/development/extension-internals.md)
   - How `fme_extension` communicates with Google Flow's DOM in MAIN world, intercepting `batchexecute`, minting one-time reCAPTCHA tokens, and WebSocket protocol envelopes.
4. [Queue Daemon & Anti-Abuse Rate Pacing](file:///docs/development/queue-and-worker.md)
   - Single-worker sequential processing (`concurrency = 1`), artificial jitter delay ($5\text{s}$–$12\text{s}$), stall detection, and automatic tab refreshes.
5. [Adding New Modes & Extending Models](file:///docs/development/adding-new-features.md)
   - Step-by-step guide to adding new generation modes, extending Pydantic schemas, database migrations, WebSocket RPC schemas, and CLI subcommands.
6. [Deployment, Containers & Ops Guide](file:///docs/development/deployment-and-ops.md)
   - Docker Compose configuration, persistent Chromium profile volumes, KasmVNC remote login, Caddy reverse proxy, and Cloudflare Proxy configuration.

---

## ⚡ Quick Verification

To verify that your deployment is healthy and ready to accept requests:

```bash
curl -s "https://flow.yourdomain.com/api/v1/health"
```

Expected JSON response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "extension_connected": true,
  "flow_session_active": true,
  "active_project_id": "00000000-0000-0000-0000-000000000000",
  "queue_depth": 0,
  "current_job_id": null
}
```
