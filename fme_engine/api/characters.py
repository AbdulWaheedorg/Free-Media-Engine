"""Free Media Engine (FME) — Character & Consistency Routes."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from fme_engine.core.auth import get_current_api_key
from fme_engine.db import crud
from fme_engine.models.schemas import CharacterCreateRequest, CharacterResponse

router = APIRouter(prefix="/characters", tags=["Characters"])


@router.post(
    "",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a character for visual consistency",
)
async def create_character(
    request: CharacterCreateRequest,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> CharacterResponse:
    char_id = str(uuid.uuid4())
    record = await crud.create_character({
        "id": char_id,
        "name": request.name,
        "description": request.description,
        "image_prompt": request.image_prompt,
        "voice_description": request.voice_description,
        "reference_image_url": request.reference_image_url,
    })
    return CharacterResponse(**record)


@router.get(
    "",
    response_model=List[CharacterResponse],
    summary="List all registered characters",
)
async def list_characters(
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> List[CharacterResponse]:
    chars = await crud.list_characters()
    return [CharacterResponse(**c) for c in chars]


@router.get(
    "/{char_id}",
    response_model=CharacterResponse,
    summary="Get character details",
)
async def get_character(
    char_id: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> CharacterResponse:
    char = await crud.get_character(char_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return CharacterResponse(**char)


@router.delete(
    "/{char_id}",
    summary="Delete character",
)
async def delete_character(
    char_id: str,
    current_key: Dict[str, Any] = Depends(get_current_api_key),
) -> Dict[str, str]:
    success = await crud.delete_character(char_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return {"message": "Character deleted"}
