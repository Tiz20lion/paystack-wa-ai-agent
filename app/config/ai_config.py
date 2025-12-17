"""AI Configuration module for the financial agent."""

import logging
from typing import Optional
from openai import AsyncOpenAI
from app.utils.config import settings

logger = logging.getLogger(__name__)

_ai_client: Optional[AsyncOpenAI] = None
_ai_enabled = False
_ai_model: Optional[str] = None

def initialize_ai_services():
    """Initialize AI services based on configuration."""
    global _ai_client, _ai_enabled, _ai_model
    
    # Check if OpenRouter is configured
    if not settings.openrouter_api_key or settings.openrouter_api_key == "your_openrouter_api_key_here":
        logger.warning("OpenRouter API key not configured - AI features will be disabled")
        logger.info("Set OPENROUTER_API_KEY in .env file to enable conversational features")
        _ai_enabled = False
        _ai_client = None
        _ai_model = None
    else:
        _ai_enabled = True
        _ai_model = settings.openrouter_model
        
        # Initialize OpenAI client for OpenRouter
        try:
            _ai_client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            logger.info(f"OpenRouter AI enabled with model: {settings.openrouter_model}")
        except ImportError:
            logger.error("OpenAI package not installed - AI features will be disabled")
            _ai_enabled = False
            _ai_client = None
            _ai_model = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter client: {e}")
            _ai_enabled = False
            _ai_client = None
            _ai_model = None

def get_ai_client() -> Optional[AsyncOpenAI]:
    """Get the initialized AI client."""
    if _ai_client is None:
        initialize_ai_services()
    return _ai_client

def get_ai_model() -> Optional[str]:
    """Get the configured AI model."""
    if _ai_model is None:
        initialize_ai_services()
    return _ai_model

def is_ai_enabled() -> bool:
    """Check if AI services are enabled."""
    if _ai_client is None:
        initialize_ai_services()
    return _ai_enabled

# Initialize AI services on module import
initialize_ai_services() 