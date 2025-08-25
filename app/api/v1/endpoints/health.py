"""
Health check API endpoints
"""
from fastapi import APIRouter
from datetime import datetime

from app.models.schemas import HealthCheckResponse
from app.core.config import settings
from app.core.logging import get_logger
from app.database.database import engine

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    try:
        logger.debug("Health check requested")
        
        # Check database connection
        database_status = "connected"
        try:
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
        except Exception as db_error:
            logger.warning(f"Database health check failed: {db_error}")
            database_status = "disconnected"
        
        response = HealthCheckResponse(
            status="healthy" if database_status == "connected" else "unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.APP_VERSION,
            database=database_status
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.APP_VERSION,
            database="disconnected"
        )


@router.get("/info")
async def get_info():
    """Get application information"""
    try:
        logger.debug("Info requested")
        
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": "Event Horizon Chat - E2EE Messenger Backend",
            "features": [
                "End-to-end encryption",
                "WebSocket real-time messaging",
                "Public key exchange",
                "Private messaging",
                "DID-based identity"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in get_info: {str(e)}")
        raise
