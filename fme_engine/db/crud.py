"""Free Media Engine (FME) — Asynchronous Database CRUD Operations."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import aiosqlite

from fme_engine.db.database import get_connection


def utc_now() -> str:
    """Return formatted UTC ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── API Keys CRUD ───────────────────────────────────────────────────────────

async def create_api_key(name: str, key_hash: str, key_prefix: str) -> Dict[str, Any]:
    db = await get_connection()
    now = utc_now()
    cursor = await db.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, status, created_at) VALUES (?, ?, ?, 'active', ?)",
        (name, key_hash, key_prefix, now),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "name": name,
        "key_prefix": key_prefix,
        "status": "active",
        "created_at": now,
        "last_used_at": None,
    }


async def get_api_key_by_hash(key_hash: str) -> Optional[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute(
        "SELECT id, name, key_hash, key_prefix, status, created_at, last_used_at FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_api_key_by_id_or_prefix(identifier: str) -> Optional[Dict[str, Any]]:
    db = await get_connection()
    if identifier.isdigit():
        async with db.execute(
            "SELECT id, name, key_hash, key_prefix, status, created_at, last_used_at FROM api_keys WHERE id = ?",
            (int(identifier),),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    async with db.execute(
        "SELECT id, name, key_hash, key_prefix, status, created_at, last_used_at FROM api_keys WHERE key_prefix = ? OR name = ?",
        (identifier, identifier),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_api_keys() -> List[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute(
        "SELECT id, name, key_prefix, status, created_at, last_used_at FROM api_keys ORDER BY id DESC"
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def revoke_api_key(identifier: str) -> bool:
    db = await get_connection()
    if identifier.isdigit():
        cursor = await db.execute(
            "UPDATE api_keys SET status = 'revoked' WHERE id = ?",
            (int(identifier),),
        )
    else:
        cursor = await db.execute(
            "UPDATE api_keys SET status = 'revoked' WHERE key_prefix = ? OR name = ?",
            (identifier, identifier),
        )
    await db.commit()
    return cursor.rowcount > 0


async def touch_api_key(key_id: int) -> None:
    db = await get_connection()
    now = utc_now()
    await db.execute(
        "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
        (now, key_id),
    )
    await db.commit()


# ─── Jobs CRUD ───────────────────────────────────────────────────────────────

async def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_connection()
    now = utc_now()
    refs = (
        json.dumps(job_data.get("reference_image_urls"))
        if job_data.get("reference_image_urls")
        else None
    )

    await db.execute(
        """
        INSERT INTO jobs (
            id, api_key_id, prompt, mode, model, aspect_ratio,
            seed_image_url, last_frame_image_url, reference_image_urls,
            seed, duration_seconds, status, progress, webhook_url, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, ?, ?)
        """,
        (
            job_data["id"],
            job_data.get("api_key_id"),
            job_data["prompt"],
            job_data["mode"],
            job_data.get("model", "omni_flash"),
            job_data.get("aspect_ratio", "16:9"),
            job_data.get("seed_image_url"),
            job_data.get("last_frame_image_url"),
            refs,
            job_data.get("seed"),
            job_data.get("duration_seconds", 5),
            job_data.get("webhook_url"),
            now,
        ),
    )
    await db.commit()
    return await get_job(job_data["id"])  # type: ignore


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("reference_image_urls"):
            try:
                res["reference_image_urls"] = json.loads(res["reference_image_urls"])
            except Exception:
                pass
        return res


async def update_job(job_id: str, **fields: Any) -> bool:
    if not fields:
        return False
    db = await get_connection()
    keys = list(fields.keys())
    values = list(fields.values())
    set_clause = ", ".join(f"{k} = ?" for k in keys)
    values.append(job_id)

    cursor = await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return cursor.rowcount > 0


async def get_next_queued_job() -> Optional[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute(
        "SELECT * FROM jobs WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT 1"
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("reference_image_urls"):
            try:
                res["reference_image_urls"] = json.loads(res["reference_image_urls"])
            except Exception:
                pass
        return res


async def get_queue_position(job_id: str) -> int:
    db = await get_connection()
    job = await get_job(job_id)
    if not job or job["status"] != "QUEUED":
        return 0
    async with db.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'QUEUED' AND created_at <= ?",
        (job["created_at"],),
    ) as cursor:
        val = await cursor.fetchone()
        return val[0] if val else 1


async def count_queued_jobs() -> int:
    db = await get_connection()
    async with db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('QUEUED', 'PROCESSING')") as cursor:
        val = await cursor.fetchone()
        return val[0] if val else 0


async def list_jobs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ─── Characters CRUD ─────────────────────────────────────────────────────────

async def create_character(char_data: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_connection()
    now = utc_now()
    await db.execute(
        """
        INSERT INTO characters (id, name, description, image_prompt, voice_description, reference_image_url, media_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            char_data["id"],
            char_data["name"],
            char_data.get("description"),
            char_data.get("image_prompt"),
            char_data.get("voice_description"),
            char_data.get("reference_image_url"),
            char_data.get("media_id"),
            now,
            now,
        ),
    )
    await db.commit()
    return await get_character(char_data["id"])  # type: ignore


async def get_character(char_id: str) -> Optional[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute("SELECT * FROM characters WHERE id = ?", (char_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_characters() -> List[Dict[str, Any]]:
    db = await get_connection()
    async with db.execute("SELECT * FROM characters ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_character(char_id: str) -> bool:
    db = await get_connection()
    cursor = await db.execute("DELETE FROM characters WHERE id = ?", (char_id,))
    await db.commit()
    return cursor.rowcount > 0
