"""Free Media Engine (FME) — SQLite Database Schema Definitions."""

SCHEMA = """
-- API Keys Table: cryptographic SHA-256 tokens for zero-downtime authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'revoked')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

-- Jobs Table: Unified Generation Job Tracking & Local Storage Offloading
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    prompt TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('t2v', 'i2v', 't2i', 'references', 'upscale')),
    model TEXT NOT NULL DEFAULT 'omni_flash',
    aspect_ratio TEXT NOT NULL DEFAULT '16:9',
    seed_image_url TEXT,
    last_frame_image_url TEXT,
    reference_image_urls TEXT,
    seed INTEGER,
    duration_seconds INTEGER DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK(status IN ('QUEUED', 'PROCESSING', 'DOWNLOADING', 'COMPLETED', 'FAILED', 'STALLED', 'CANCELLED')),
    progress INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    local_path TEXT,
    webhook_url TEXT,
    webhook_status TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- Characters Table: Visual consistency & reference registry
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    image_prompt TEXT,
    voice_description TEXT,
    reference_image_url TEXT,
    media_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);

-- Videos Table: Multi-scene parent container
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'PROCESSING', 'COMPLETED', 'FAILED')),
    aspect_ratio TEXT DEFAULT '16:9',
    output_url TEXT,
    local_path TEXT,
    duration REAL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Scenes Table: Individual timeline cuts, continuations, and transitions
CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    display_order INTEGER NOT NULL DEFAULT 0,
    prompt TEXT NOT NULL,
    image_prompt TEXT,
    video_prompt TEXT,
    character_names TEXT,
    parent_scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    chain_type TEXT NOT NULL DEFAULT 'ROOT' CHECK(chain_type IN ('ROOT', 'CONTINUATION', 'INSERT')),
    image_url TEXT,
    video_url TEXT,
    local_path TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_scenes_video ON scenes(video_id);
"""
