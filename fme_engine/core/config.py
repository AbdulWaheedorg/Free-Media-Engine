"""Free Media Engine (FME) — Centralized Configuration.

Loads environment variables from .env and provides a strictly typed,
validated singleton for all daemon, worker, and CLI operations.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Locate and load .env file from workspace root or parent directories
_current_dir = Path(__file__).resolve().parent
_env_path = _current_dir.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
else:
    load_dotenv()


class Settings(BaseModel):
    # Remote VPS & Infrastructure
    VPS_HOST: str = Field(default_factory=lambda: os.getenv("VPS_HOST", "127.0.0.1"))
    VPS_USER: str = Field(default_factory=lambda: os.getenv("VPS_USER", "ubuntu"))
    VPS_SSH_KEY_PATH: str = Field(
        default_factory=lambda: os.getenv("VPS_SSH_KEY_PATH", "")
    )
    VPS_SSH_COMMAND: str = Field(default_factory=lambda: os.getenv("VPS_SSH_COMMAND", ""))
    DOMAIN_NAME: str = Field(default_factory=lambda: os.getenv("DOMAIN_NAME", "flow.yourdomain.com"))

    # Google Flow Project Pinned UUID
    FLOW_PROJECT_ID: str = Field(
        default_factory=lambda: os.getenv("FLOW_PROJECT_ID", "")
    )
    FLOW_ALLOW_DEGRADED: bool = Field(
        default_factory=lambda: os.getenv("FLOW_ALLOW_DEGRADED", "true").lower() in ("true", "1", "yes")
    )

    # Ports & Service Network Bindings
    DAEMON_HOST: str = Field(default_factory=lambda: os.getenv("DAEMON_HOST", "0.0.0.0"))
    DAEMON_PORT: int = Field(default_factory=lambda: int(os.getenv("DAEMON_PORT", "8120")))
    WEB_UI_PORT: int = Field(default_factory=lambda: int(os.getenv("WEB_UI_PORT", "6901")))
    VNC_PASSWORD: str = Field(
        default_factory=lambda: os.getenv("VNC_PASSWORD", "ChangeMe_SecurePassword_2026!")
    )

    # WebSocket Bridge for FME Extension
    FME_WS_HOST: str = Field(default_factory=lambda: os.getenv("FME_WS_HOST", "0.0.0.0"))
    FME_WS_PORT: int = Field(default_factory=lambda: int(os.getenv("FME_WS_PORT", "9222")))
    FLOW_WS_URL: str = Field(default_factory=lambda: os.getenv("FLOW_WS_URL", "ws://127.0.0.1:9222"))
    GATEWAY_PORT: int = Field(default_factory=lambda: int(os.getenv("GATEWAY_PORT", "443")))

    # Storage Paths
    DATA_DIR: str = Field(default_factory=lambda: os.getenv("DATA_DIR", "./data"))
    OUTPUTS_DIR: str = Field(default_factory=lambda: os.getenv("OUTPUTS_DIR", "./data/outputs"))
    SQLITE_DB_PATH: str = Field(default_factory=lambda: os.getenv("SQLITE_DB_PATH", "./data/fme.db"))
    CHROME_PROFILE_DIR: str = Field(
        default_factory=lambda: os.getenv("CHROME_PROFILE_DIR", "./data/chrome-profile")
    )

    # Queue Pacing & Rate Limits
    QUEUE_CONCURRENCY: int = Field(default_factory=lambda: int(os.getenv("QUEUE_CONCURRENCY", "1")))
    PACING_MIN_DELAY: float = Field(default_factory=lambda: float(os.getenv("PACING_MIN_DELAY", "5.0")))
    PACING_MAX_DELAY: float = Field(default_factory=lambda: float(os.getenv("PACING_MAX_DELAY", "12.0")))
    JOB_TIMEOUT_VIDEO: int = Field(default_factory=lambda: int(os.getenv("JOB_TIMEOUT_VIDEO", "180")))
    JOB_TIMEOUT_IMAGE: int = Field(default_factory=lambda: int(os.getenv("JOB_TIMEOUT_IMAGE", "45")))

    # Engine Defaults
    DEFAULT_PAYGATE_TIER: str = "PAYGATE_TIER_ONE"
    FLOW_GENERATION_MIN_INTERVAL_S: float = 4.0
    FLOW_GENERATION_MAX_CONCURRENT: int = 1
    FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S: float = 300.0
    VIDEO_MODELS: dict = Field(
        default_factory=lambda: {
            "omni_flash": "gemini-omni-1.1-flash",
            "veo": "veo-2.0-generate-001",
        }
    )

    # Security & API Keys
    API_KEY_PREFIX: str = Field(default_factory=lambda: os.getenv("API_KEY_PREFIX", "fme_live_"))
    FME_MASTER_KEY: str = Field(default_factory=lambda: os.getenv("FME_MASTER_KEY", ""))

    # Health & Alerting
    ALERT_WEBHOOK_URL: str = Field(default_factory=lambda: os.getenv("ALERT_WEBHOOK_URL", ""))
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "900"))
    )

    def ensure_directories(self) -> None:
        """Ensure necessary storage directories exist on host."""
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.CHROME_PROFILE_DIR).mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
