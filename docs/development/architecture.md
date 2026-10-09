# Architecture & Hybrid Relay Pattern

Free Media Engine employs a **Hybrid Relay Pattern** to bridge external, authenticated REST traffic with Google Flow's proprietary, session-gated browser canvas.

---

## 🏛️ System Topology

```mermaid
flowchart TD
    subgraph PublicInternet [Public Internet (Port 443)]
        Client["External Clients / CLI / Web Apps"]
    end

    subgraph ReverseProxyGateway [Reverse Proxy Gateway (Port 443 -> 8120)]
        Caddy["Caddy Server (TLS 1.3 / Let's Encrypt)"]
    end

    subgraph InternalHost [Private Docker Network (fme-net)]
        subgraph FmeDaemon [Backend Daemon (fme-daemon:8120)]
            FastAPI["FastAPI REST API Gateway"]
            Auth["Constant-Time SHA-256 Auth Middleware"]
            Queue["Sequential FIFO Queue (concurrency=1)"]
            SQLite[("SQLite Catalog (fme.db)")]
            WSBridge["WebSocket Server (:9222)"]
            Downloader["Streaming Media Downloader"]
        end

        subgraph FmeChromium [Virtual Frame Container (fme-chromium)]
            Xvfb["X11 Framebuffer / KasmVNC (:6901)"]
            Chrome["Headed Chromium (User Profile Mounted)"]
            Extension["Unpacked FME Bridge Extension"]
            FlowTab["Google Flow Active Tab (/project/{UUID})"]
        end
    end

    Client -->|HTTPS Bearer Token| Caddy
    Caddy -->|Proxy HTTP| FastAPI
    FastAPI --> Auth
    Auth --> Queue
    Queue -->|State & Metadata| SQLite
    Queue -->|JSON-RPC Command| WSBridge
    WSBridge <-->|Bi-directional WS :9222| Extension
    Extension -->|batchexecute in DOM| FlowTab
    FlowTab -->|CDN Asset URL| Extension
    Extension -->|Completion Event| WSBridge
    WSBridge -->|CDN URL| Downloader
    Downloader -->|Stream MP4 / PNG| HostStorage[("/data/outputs/")]
```

---

## 🛡️ Four Isolation Tiers

### 1. Reverse Proxy Gateway (Public Perimeter)
- **Role**: Fronted by Caddy, this is the **only component exposed to the public internet** (Port 80/443).
- **Function**: Automatically provisions and renews TLS certificates via Let's Encrypt, enforces TLS 1.3 encryption, and terminates HTTPS traffic before proxying to the internal daemon.
- **Cloudflare Integration**: Configured with `auto_https disable_redirects` and dual HTTP/HTTPS listeners to support Cloudflare Proxy in both Flexible and Full/Strict SSL modes without redirect loops.

### 2. Orchestration Daemon & Sequential Queue (`fme-daemon`)
- **Role**: An asynchronous Python service built on FastAPI and Uvicorn.
- **Function**: Validates incoming bearer tokens against the SQLite hash table, queues generation requests in strict FIFO order, manages artificial jitter pacing ($5\text{s}$–$12\text{s}$), and runs the local WebSocket bridge.
- **Storage**: Maintains `fme.db` (storing jobs, keys, characters, and scenes) and `/data/outputs` (persisting raw generated media).

### 3. Headed Chromium Virtual Frame (`fme-chromium`)
- **Role**: An unmodified, headed Chromium instance running inside an X11 virtual framebuffer (via `kasmweb/chromium`).
- **Function**: Houses the logged-in Google account state, persistent browser profile volume, and the unpacked `fme_extension`. It maintains an active tab pointed directly at the pinned Google Flow workspace URL.
- **Anti-Bot Defense**: Because generations originate natively from an unmodified browser event loop inside an active Google user session, Google evaluates all transactions as legitimate human interactions. CDP/Puppeteer automation signatures are completely avoided.

### 4. Browser Extension Bridge (`fme_extension`)
- **Role**: A Manifest V3 Chrome extension running in the page's MAIN world context.
- **Function**: Connects to the local WebSocket bridge on `ws://127.0.0.1:9222`, listens for generation RPC commands, injects `batchexecute` transactions directly into the Google Flow canvas, captures single-use reCAPTCHA mints, and streams back completion payloads.

---

## 🔒 Security Boundaries

| Component | Network Binding | Public Exposure |
| :--- | :--- | :--- |
| **Caddy TLS Proxy** | `0.0.0.0:80`, `0.0.0.0:443` | **Yes** (Public HTTPS) |
| **REST API Daemon** | `0.0.0.0:8120` (Docker internal) | **No** (Proxied via Caddy only) |
| **Extension WS Bridge** | `127.0.0.1:9222` | **No** (Strictly localhost) |
| **KasmVNC Management** | `127.0.0.1:6901` | **No** (SSH tunnel only) |
| **SQLite Database** | Host filesystem mount | **No** (File permission locked) |
