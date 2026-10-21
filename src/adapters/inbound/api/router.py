"""Root API router: groups every feature router under ``/api/v1``."""

from fastapi import APIRouter

from src.adapters.inbound.api.routers.answer import answer_router
from src.adapters.inbound.api.routers.health import health_router
from src.adapters.inbound.api.routers.search import search_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(answer_router)
