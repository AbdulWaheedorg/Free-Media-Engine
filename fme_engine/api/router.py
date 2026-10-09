"""Free Media Engine (FME) — Unified API v1 Router."""
from fastapi import APIRouter

from fme_engine.api.generate import router as generate_router
from fme_engine.api.jobs import router as jobs_router
from fme_engine.api.assets import router as assets_router
from fme_engine.api.characters import router as characters_router
from fme_engine.api.admin import router as admin_router
from fme_engine.api.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(generate_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(assets_router)
api_v1_router.include_router(characters_router)
api_v1_router.include_router(admin_router)
