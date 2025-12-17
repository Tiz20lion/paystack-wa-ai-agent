"""Logging configuration for Paystack CLI App."""

import sys
import os
from typing import Optional
from loguru import logger
from .config import settings


def setup_logger():
    """Setup application logging with loguru."""
    
    # Remove default logger
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # File logging (skip on Vercel/serverless - use console only)
    if not os.getenv("VERCEL"):
        # Only log to files if not on Vercel (serverless file system is read-only)
        try:
            logger.add(
                settings.log_file,
                level="DEBUG",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=settings.log_rotation,
                retention=settings.log_retention,
                compression="zip",
            )
            
            # Error file logging
            logger.add(
                "logs/error.log",
                level="ERROR",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation="1 day",
                retention="7 days",
                compression="zip",
            )
        except Exception as e:
            # If file logging fails, continue with console only
            logger.warning(f"File logging not available: {e}")
    
    return logger


# Initialize logger
app_logger = setup_logger()


def get_logger(name: Optional[str] = None):
    """Get a logger instance for a specific module."""
    if name:
        return logger.bind(name=name)
    return logger 