# Local Setup & Development Workflow

This guide details how to configure a local development environment, run the Free Media Engine daemon locally, and execute the test suite.

---

## 💻 Prerequisites

- **Python**: 3.11 or 3.12+
- **Docker & Docker Compose**: (v2.20+)
- **ffmpeg**: Installed and available in your system `$PATH` (for video inspection/concatenation)
- **Git**

---

## 🚀 Step-by-Step Local Setup

### 1. Clone the Repository & Create Virtual Environment
```bash
# Clone the repository
git clone https://github.com/AbdulWaheedorg/Free-Media-Engine.git
cd Free-Media-Engine

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Local Environment (`.env`)
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```

Edit `.env` to configure your local parameters:
```ini
# Domain & Networking
DOMAIN_NAME=flow.yourdomain.com
DAEMON_PORT=8120
FLOW_WS_PORT=9222
FLOW_WS_URL=ws://127.0.0.1:9222

# Workspace Pinned Project
FLOW_PROJECT_ID=00000000-0000-0000-0000-000000000000

# Storage Paths
DATA_DIR=./data
DATABASE_URL=sqlite+aiosqlite:///./data/fme.db

# Anti-Abuse Rate Pacing (in seconds)
PACING_MIN_DELAY=5
PACING_MAX_DELAY=12
JOB_TIMEOUT_VIDEO=180
JOB_TIMEOUT_IMAGE=45

# Security
FLOW_MASTER_KEY=your_emergency_master_secret_here
```

### 4. Initialize Local SQLite Database
Run the database initialization script or boot the daemon to generate tables automatically:
```bash
python -c "import asyncio; from fme_engine.db.database import init_db; asyncio.run(init_db())"
```

### 5. Generate a Local Developer Key
```bash
python -m fme_engine.cli.main keys create --name "local-dev-key"
```
Note the generated key (e.g., `fme_live_...`).

---

## 🏃 Running the Daemon Locally

To start the FastAPI REST API server with live code reloading:

```bash
uvicorn fme_engine.api.app:app --host 127.0.0.1 --port 8120 --reload
```

The server will initialize:
- **REST Endpoints**: `http://127.0.0.1:8120/api/v1`
- **Swagger Documentation**: `http://127.0.0.1:8120/docs`
- **WebSocket Bridge**: `ws://127.0.0.1:9222`

---

## 🧪 Testing Endpoints Locally

### Check System Health
```bash
curl -s "http://127.0.0.1:8120/api/v1/health"
```

### Submit a Test Job
```bash
curl -X POST "http://127.0.0.1:8120/api/v1/generate" \
  -H "Authorization: Bearer <YOUR_LOCAL_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Cyberpunk hovercar flying in heavy rain",
    "mode": "t2i",
    "aspect_ratio": "16:9"
  }'
```

---

## 📁 Project Directory Layout

```
.
├── .env.example              # Sample environment template
├── Dockerfile                # Production container definition
├── docker-compose.yml        # Multi-container orchestration stack
├── requirements.txt          # Python dependency manifest
├── fme_engine/               # Core backend service package
│   ├── api/                  # FastAPI router, endpoints & dependencies
│   ├── cli/                  # Typer CLI utility commands
│   ├── core/                 # Config, security & constant-time auth
│   ├── db/                   # Async SQLite database models & CRUD
│   ├── models/               # Pydantic validation schemas
│   ├── services/             # WebSocket bridge, Omni Flash & downloader
│   └── worker/               # Single-worker sequential queue daemon
├── fme_extension/            # Unpacked Chrome MV3 extension
│   ├── manifest.json         # Extension manifest
│   ├── background.js         # Service worker & WS client
│   └── content.js            # DOM bridge in MAIN world
└── docs/                     # Full project documentation
```
