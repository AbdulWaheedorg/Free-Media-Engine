"""Free Media Engine (FME) — Async SQLite Database Manager."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator
import aiosqlite

from fme_engine.core.config import settings
from fme_engine.db.schema import SCHEMA

logger = logging.getLogger(__name__)

_db_connection: aiosqlite.Connection | None = None
_db_lock = asyncio.Lock()


async def get_db_path() -> str:
    """Return database file path and ensure parent directory exists."""
    db_path = Path(settings.SQLITE_DB_PATH).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


async def init_db() -> None:
    """Initialize SQLite database and run schema migrations."""
    db_path = await get_db_path()
    logger.info("Initializing SQLite database at %s", db_path)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.executescript(SCHEMA)
        await db.commit()
    logger.info("SQLite database schema initialized successfully")


async def get_connection() -> aiosqlite.Connection:
    """Get active singleton aiosqlite connection."""
    global _db_connection
    async with _db_lock:
        if _db_connection is None:
            db_path = await get_db_path()
            _db_connection = await aiosqlite.connect(db_path)
            _db_connection.row_factory = aiosqlite.Row
            await _db_connection.execute("PRAGMA journal_mode=WAL;")
            await _db_connection.execute("PRAGMA foreign_keys=ON;")
        return _db_connection


async def close_db() -> None:
    """Close active aiosqlite connection on shutdown."""
    global _db_connection
    async with _db_lock:
        if _db_connection is not None:
            await _db_connection.close()
            _db_connection = None
            logger.info("Database connection closed")
