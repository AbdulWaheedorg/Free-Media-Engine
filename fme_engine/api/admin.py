"""Free Media Engine (FME) — Key Administration Routes."""
from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from fme_engine.core.auth import generate_api_key, get_current_api_key
from fme_engine.db import crud
from fme_engine.models.schemas import ApiKeyCreateRequest, ApiKeyResponse

router = APIRouter(prefix="/admin/keys", tags=["Administration"])


@router.post(
    "",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API Key",
    description="Generates a high-entropy bearer token, stores its SHA-256 hash in SQLite, and returns the raw key once.",
)
async def create_key_endpoint(
    request: ApiKeyCreateRequest,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> ApiKeyResponse:
    raw_key, key_hash, key_prefix = generate_api_key()
    record = await crud.create_api_key(name=request.name, key_hash=key_hash, key_prefix=key_prefix)
    record["raw_key"] = raw_key
    return ApiKeyResponse(**record)


@router.get(
    "",
    response_model=List[ApiKeyResponse],
    summary="List all API keys",
)
async def list_keys_endpoint(
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> List[ApiKeyResponse]:
    keys = await crud.list_api_keys()
    return [ApiKeyResponse(**k) for k in keys]


@router.delete(
    "/{identifier}",
    summary="Instantly revoke an API Key",
    description="Flipping the key status to 'revoked' immediately rejects all subsequent requests using this key in <50ms without restarting the service.",
)
async def revoke_key_endpoint(
    identifier: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> Dict[str, str]:
    success = await crud.revoke_api_key(identifier)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Key '{identifier}' not found")
    return {"message": f"API key '{identifier}' revoked successfully"}
