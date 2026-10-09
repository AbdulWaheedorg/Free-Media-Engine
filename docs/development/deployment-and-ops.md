# Deployment, Containers & Ops Guide

This operations guide covers deploying, maintaining, and troubleshooting Free Media Engine in a production Linux VPS environment.

---

## 🏗️ Production Architecture Breakdown

On the host VPS, services run in isolated Docker containers communicating across the internal bridge network `fme-net`:

```
[Host Storage: ./data]
  ├── outputs/           (Persisted MP4/PNG renders)
  ├── chrome-profile/    (Persistent Google user account session)
  └── fme.db             (SQLite jobs and keys catalog)
           │
     (Volume Mounts)
           ▼
[Docker Network: fme-net]
  ├── fme-daemon:8120    (FastAPI + WS bridge :9222)
  ├── fme-chromium:6901  (KasmVNC + Headed Chromium)
  └── n8n-setup-caddy-1  (Public TLS reverse proxy on :80/:443)
```

---

## 🚀 Docker Compose Service Configuration

```yaml
version: "3.8"

networks:
  fme-net:
    driver: bridge

services:
  fme-daemon:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fme-daemon
    restart: unless-stopped
    ports:
      - "8120:8120"
      - "127.0.0.1:9222:9222"
    environment:
      - FLOW_PROJECT_ID=00000000-0000-0000-0000-000000000000
      - FLOW_WS_URL=ws://127.0.0.1:9222
      - DATA_DIR=/data
      - DAEMON_PORT=8120
      - DATABASE_URL=sqlite+aiosqlite:////data/fme.db
    volumes:
      - ./data:/data
    networks:
      - fme-net

  fme-chromium:
    image: kasmweb/chromium:1.16.0
    container_name: fme-chromium
    restart: unless-stopped
    ports:
      - "127.0.0.1:6901:6901"
    environment:
      - VNC_PW=vncpassword
      - APP_ARGS=--user-data-dir=/home/kasm-user/chrome-data https://flow.google.com/project/${FLOW_PROJECT_ID}
    volumes:
      - ./data/chrome-profile:/home/kasm-user/chrome-data
      - ./fme_extension:/usr/share/chromium/extensions/fme_extension:ro
    networks:
      - fme-net
```

---

## 🔒 Accessing KasmVNC for Google Login / 2FA

Port `6901` is strictly bound to `127.0.0.1` and is never exposed to the public internet. To access the browser session for 1-time Google login or 2FA recovery:

### 1. Establish an SSH Port Forward Tunnel
```bash
ssh -N -L 6901:127.0.0.1:6901 ubuntu@YOUR_VPS_IP
```
*(If using an SSH key file, include `-i /path/to/key.pem`)*.

### 2. Connect in Browser
Navigate to `https://localhost:6901` in your browser:
- **Username**: `kasm_user`
- **Password**: `vncpassword`

Once logged in, open `https://flow.google.com/project/${FLOW_PROJECT_ID}`. The profile will persist indefinitely in `./data/chrome-profile`.

---

## 🌐 Caddy Reverse Proxy & Cloudflare Compatibility

The public reverse proxy routes HTTPS traffic from your domain to the daemon on `127.0.0.1:8120`:

```caddy
{
    email your-email@example.com
    auto_https disable_redirects
}

http://flow.yourdomain.com, https://flow.yourdomain.com {
    reverse_proxy 127.0.0.1:8120
}
```

### Cloudflare Proxy Compatibility Notes
1. **`auto_https disable_redirects`**: Prevents Caddy from forcing an HTTP $\rightarrow$ HTTPS 308 redirect loop if Cloudflare SSL mode is set to "Flexible".
2. **Dual Listeners (`http://...`, `https://...`)**: Allows Caddy to handle traffic seamlessly regardless of whether Cloudflare connects via port 80 or 443.
3. **Recommended Setting in Cloudflare**: Set SSL/TLS Encryption mode to **Full (Strict)** or **Full** for end-to-end encrypted traffic.

---

## 🔧 Operational Maintenance & Troubleshooting

### Check Service Status
```bash
docker compose ps
```

### View Live Daemon Logs
```bash
docker logs -f fme-daemon
```

### Restart Stack Safely
```bash
docker compose down
docker compose up -d
```

### Clear Stale Chromium Singleton Locks
If Chromium crashes or the host reboots unexpectedly, stale lock files may prevent Chromium from booting:
```bash
rm -f ./data/chrome-profile/Singleton*
docker restart fme-chromium
```
