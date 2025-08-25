"""
Event Horizon Chat - E2EE Messenger Backend
Main application entry point
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import init_db
from app.api.v1.api import api_router
from app.websocket.endpoints import router as websocket_router
from app.websocket.manager import manager
from app.core.auth import auth_manager
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    await manager.stop()
    await auth_manager.cleanup()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="End-to-End Encrypted Messenger Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )


# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Event Horizon Chat",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running"
    }


# Health check endpoint (legacy)
@app.get("/health")
async def health_check():
    """Legacy health check endpoint"""
    return {
        "status": "healthy",
        "service": "Event Horizon Chat",
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
