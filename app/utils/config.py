"""Configuration module for Paystack CLI App."""

import os
from typing import List, Dict, cast
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Paystack API Configuration
    paystack_secret_key: str = Field(default="sk_test_placeholder", alias="PAYSTACK_SECRET_KEY")
    paystack_public_key: str = Field(default="pk_test_placeholder", alias="PAYSTACK_PUBLIC_KEY")
    paystack_base_url: str = Field(default="https://api.paystack.co", alias="PAYSTACK_BASE_URL")
    
    # Application Configuration
    app_name: str = Field(default="TizLion AI Banking CLI App", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # FastAPI Configuration
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="API_BASE_URL")
    
    # CLI Configuration
    cli_theme: str = Field(default="dark", alias="CLI_THEME")
    default_currency: str = Field(default="NGN", alias="DEFAULT_CURRENCY")
    default_amount: int = Field(default=5000, alias="DEFAULT_AMOUNT")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./paystack_app.db", alias="DATABASE_URL")
    
    # MongoDB Configuration (for LangGraph agent)
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_database: str = Field(default="paystack_assistant", alias="MONGODB_DATABASE")
    
    # OpenRouter Configuration (AI features)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL")
    openrouter_site_url: str = Field(default="", alias="OPENROUTER_SITE_URL")
    openrouter_site_name: str = Field(default="Paystack WhatsApp Agent", alias="OPENROUTER_SITE_NAME")
    
    # Twilio WhatsApp Configuration
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number: str = Field(default="", alias="TWILIO_WHATSAPP_NUMBER")
    
    # Webhook Configuration
    webhook_url: str = Field(default="", alias="WEBHOOK_URL")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")

    # Telegram Bot (chat interface)
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    telegram_use_polling: bool = Field(default=True, alias="TELEGRAM_USE_POLLING")

    # Security
    jwt_secret_key: str = Field(default="your-secret-key", alias="JWT_SECRET_KEY")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:8000"],
        alias="CORS_ORIGINS"
    )
    
    # Transfer Limits and Safety
    daily_transfer_limit: int = Field(default=500000, alias="DAILY_TRANSFER_LIMIT")  # ₦5,000 in kobo
    single_transfer_limit: int = Field(default=100000, alias="SINGLE_TRANSFER_LIMIT")  # ₦1,000 in kobo
    require_confirmation: bool = Field(default=True, alias="REQUIRE_CONFIRMATION")
    
    # OCR Configuration
    tesseract_path: str = Field(default="", alias="TESSERACT_PATH")
    supported_image_formats: List[str] = Field(
        default=["jpeg", "jpg", "png", "bmp", "gif", "tiff"],
        alias="SUPPORTED_IMAGE_FORMATS"
    )
    
    # Logging
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")
    log_rotation: str = Field(default="10 MB", alias="LOG_ROTATION")
    log_retention: str = Field(default="30 days", alias="LOG_RETENTION")
    
    # Currency configurations
    SUPPORTED_CURRENCIES: dict = {
        "NGN": {"name": "Nigerian Naira", "symbol": "₦", "subunit": "kobo"},
        "USD": {"name": "US Dollar", "symbol": "$", "subunit": "cent"},
        "GHS": {"name": "Ghanaian Cedi", "symbol": "₵", "subunit": "pesewa"},
        "ZAR": {"name": "South African Rand", "symbol": "R", "subunit": "cent"},
        "KES": {"name": "Kenyan Shilling", "symbol": "Ksh", "subunit": "cent"},
    }
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    def get_currency_info(self, currency: str) -> dict[str, str]:
        """Get currency information."""
        default_currency = {"name": "", "symbol": "", "subunit": ""}
        return cast(Dict[str, str], self.SUPPORTED_CURRENCIES.get(currency.upper(), default_currency))

    def format_amount(self, amount: int, currency: str = "") -> str:
        """Format amount for display."""
        if not currency:
            currency = self.default_currency
        currency_info = self.get_currency_info(currency)
        symbol = currency_info.get("symbol", "")
        formatted_amount = amount / 100  # Convert from subunit
        
        return f"{symbol}{formatted_amount:,.2f}"
    
    def to_subunit(self, amount: float) -> int:
        """Convert amount to subunit (kobo/cents)."""
        return int(amount * 100)


# Create global settings instance
try:
    settings = Settings()
except Exception as e:
    # If there are issues loading settings, try with explicit defaults
    print(f"Warning: Could not load all settings from environment: {e}")
    print("Using default settings. Please configure your .env file.")
    
    # Set basic environment variables if not present
    if "PAYSTACK_SECRET_KEY" not in os.environ:
        os.environ["PAYSTACK_SECRET_KEY"] = "sk_test_placeholder"
    if "PAYSTACK_PUBLIC_KEY" not in os.environ:
        os.environ["PAYSTACK_PUBLIC_KEY"] = "pk_test_placeholder"
    
    settings = Settings()

# Ensure logs directory exists
try:
    log_file_path = settings.log_file
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and log_dir != "":
            os.makedirs(log_dir, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create logs directory: {e}")
    # Create default logs directory as fallback
    try:
        os.makedirs("logs", exist_ok=True)
    except Exception:
        pass 