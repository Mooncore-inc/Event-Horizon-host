"""
Logging configuration for Event Horizon Chat
"""
import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """Setup application logging"""
    
    log_level = level or settings.LOG_LEVEL
    log_format = format_string or settings.LOG_FORMAT
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)
