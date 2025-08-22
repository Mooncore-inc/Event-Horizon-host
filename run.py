#!/usr/bin/env python3
"""
Simple script to run Event Horizon Chat
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📍 Server will be available at: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔍 ReDoc Documentation: http://{settings.HOST}:{settings.PORT}/redoc")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
