"""Health-check route: reports that the HTTP adapter is up."""

from fastapi import APIRouter

from src.adapters.inbound.api.schemas import HealthResponse


health_router = APIRouter(prefix="/health")


@health_router.get("", response_model=HealthResponse)
def handle_health() -> HealthResponse:
    """Report that the server is up, without touching the index."""
    return HealthResponse(status="ok")
