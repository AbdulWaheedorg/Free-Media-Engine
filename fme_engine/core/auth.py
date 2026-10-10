"""Free Media Engine (FME) — Cryptographic Authentication & Key Management.

Implements high-entropy key minting, SHA-256 hashing, constant-time verification,
and FastAPI security dependencies.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fme_engine.core.config import settings
from fme_engine.db.crud import get_api_key_by_hash, touch_api_key

_security_scheme = HTTPBearer(auto_error=False)


KEY_SALT = b"fme_api_key_salt_v1"


def generate_api_key(prefix: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Generate a new high-entropy API key.
    
    Returns:
        (raw_key, key_hash, key_prefix)
    """
    pfx = prefix or settings.API_KEY_PREFIX
    random_part = secrets.token_urlsafe(32)
    raw_key = f"{pfx}{random_part}"
    key_hash = hash_api_key(raw_key)
    # Store first 12 chars as display prefix (e.g. "fme_live_Ab12")
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """Compute PBKDF2-HMAC-SHA256 hex digest of raw key with 100,000 iterations."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        raw_key.strip().encode("utf-8"),
        KEY_SALT,
        iterations=100000,
    ).hex()


def verify_hash_constant_time(candidate_hash: str, target_hash: str) -> bool:
    """Compare two hashes using constant-time verification to prevent timing attacks."""
    return hmac.compare_digest(candidate_hash.encode("utf-8"), target_hash.encode("utf-8"))


async def authenticate_bearer_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify incoming bearer token against SQLite api_keys and emergency master key.
    Returns the key record if valid and active, else None.
    """
    if not token:
        return None

    clean_token = token.strip()
    candidate_hash = hash_api_key(clean_token)

    # 1. Check emergency master key override if configured
    if settings.FME_MASTER_KEY:
        master_hash = hash_api_key(settings.FME_MASTER_KEY)
        if verify_hash_constant_time(candidate_hash, master_hash):
            return {
                "id": 0,
                "name": "master-admin",
                "key_prefix": "master_",
                "status": "active",
                "is_master": True,
            }

    # 2. Look up key record in database
    key_record = await get_api_key_by_hash(candidate_hash)
    if not key_record:
        return None

    # 3. Check revocation status
    if key_record.get("status") != "active":
        return None

    # Constant-time double check against stored hash
    if not verify_hash_constant_time(candidate_hash, key_record["key_hash"]):
        return None

    # Asynchronously update last_used_at timestamp
    try:
        await touch_api_key(key_record["id"])
    except Exception:
        pass

    return key_record


async def get_current_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security_scheme),
) -> Dict[str, Any]:
    """FastAPI route dependency ensuring a valid, active API key is present."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected Bearer <API_KEY>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_record = await authenticate_bearer_token(credentials.credentials)
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return key_record
