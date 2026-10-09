"""Free Media Engine (FME) — Unified Pydantic Schemas.

Defines all request, response, and domain entity structures used across the API,
daemon, queue worker, and CLI client.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────

class JobMode(str, Enum):
    t2v = "t2v"
    i2v = "i2v"
    t2i = "t2i"
    references = "references"
    upscale = "upscale"


class ModelFamily(str, Enum):
    omni_flash = "omni_flash"
    veo = "veo"


class AspectRatio(str, Enum):
    widescreen = "16:9"
    vertical = "9:16"
    square = "1:1"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALLED = "STALLED"
    CANCELLED = "CANCELLED"


# ─── Generation Requests & Responses ─────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Generation prompt describing the visual action, style, and content")
    mode: JobMode = Field(default=JobMode.t2v, description="Generation modality (t2v, i2v, t2i, references, upscale)")
    model: ModelFamily = Field(default=ModelFamily.omni_flash, description="Engine model family (omni_flash or veo)")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.widescreen, description="Output dimensions (16:9, 9:16, 1:1)")
    seed_image_url: Optional[str] = Field(None, description="Direct URL or media ID for first-frame image-to-video")
    last_frame_image_url: Optional[str] = Field(None, description="Direct URL or media ID for end-frame video interpolation")
    reference_image_urls: Optional[List[str]] = Field(None, description="List of reference image URLs for visual style/character consistency")
    seed: Optional[int] = Field(None, description="Optional random seed integer for reproducibility")
    duration_seconds: Optional[int] = Field(5, description="Video duration in seconds (typically 5-8s)")
    webhook_url: Optional[str] = Field(None, description="External URL to receive POST callback upon job completion")


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    queue_position: int = 1
    estimated_wait_seconds: Optional[int] = None
    message: str = "Job accepted and queued for processing"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)
    prompt: str
    mode: JobMode
    model: ModelFamily
    aspect_ratio: AspectRatio
    download_url: Optional[str] = None
    local_path: Optional[str] = None
    source_url: Optional[str] = None
    error_message: Optional[str] = None
    queue_position: Optional[int] = None
    webhook_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ─── Characters & Consistency ────────────────────────────────────────────────

class CharacterCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    voice_description: Optional[str] = None
    reference_image_url: Optional[str] = None


class CharacterResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    voice_description: Optional[str] = None
    reference_image_url: Optional[str] = None
    media_id: Optional[str] = None
    created_at: str
    updated_at: str


# ─── Scenes & Composition ────────────────────────────────────────────────────

class SceneCreateRequest(BaseModel):
    video_id: str
    display_order: int = 0
    prompt: str
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    character_names: Optional[List[str]] = None
    parent_scene_id: Optional[str] = None
    chain_type: str = "ROOT"


class SceneResponse(BaseModel):
    id: str
    video_id: str
    display_order: int
    prompt: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    created_at: str


# ─── API Key Management ──────────────────────────────────────────────────────

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., description="Descriptive label for this API key, e.g. 'mobile-app' or 'n8n-agent'")


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    status: str
    created_at: str
    last_used_at: Optional[str] = None
    raw_key: Optional[str] = Field(None, description="Full raw key; ONLY returned once during creation")


# ─── System Health & Telemetry ───────────────────────────────────────────────

class SystemHealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    extension_connected: bool
    flow_session_active: bool
    active_project_id: str
    queue_depth: int
    current_job_id: Optional[str] = None
    uptime_seconds: float
