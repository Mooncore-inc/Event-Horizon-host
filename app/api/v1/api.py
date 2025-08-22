"""
API v1 router configuration
"""
from fastapi import APIRouter

from app.api.v1.endpoints import messages, keys, health, stats

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["messages"]
)

api_router.include_router(
    keys.router,
    prefix="/keys",
    tags=["keys"]
)

api_router.include_router(
    health.router,
    prefix="/system",
    tags=["system"]
)

api_router.include_router(
    stats.router,
    prefix="/stats",
    tags=["statistics"]
)
