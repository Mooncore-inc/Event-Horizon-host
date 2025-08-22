"""
Configuration settings for Event Horizon Chat
"""
import os
import secrets
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Event Horizon Chat"
    APP_VERSION: str = "1.0.0"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"
    
    # Security - Auto-generated, not configurable
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    
    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    
    # Key Rotation Settings
    KEY_ROTATION_INTERVAL_HOURS: int = 24
    MAX_PREVIOUS_KEYS: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
