"""Service validation utilities to ensure all services are properly configured."""

import os
from typing import Dict, List
from app.utils.logger import get_logger
from app.utils.config import settings

logger = get_logger("service_validator")


def validate_paystack_config() -> Dict[str, bool]:
    """Validate Paystack API configuration."""
    issues = []
    warnings = []
    
    # Check secret key
    if not settings.paystack_secret_key or settings.paystack_secret_key in [
        "sk_test_placeholder", 
        "sk_test_your_secret_key_here",
        ""
    ]:
        issues.append("PAYSTACK_SECRET_KEY is not configured or using placeholder value")
    
    # Check public key
    if not settings.paystack_public_key or settings.paystack_public_key in [
        "pk_test_placeholder",
        "pk_test_your_public_key_here",
        ""
    ]:
        warnings.append("PAYSTACK_PUBLIC_KEY is not configured (optional for server-side)")
    
    # Check base URL
    if not settings.paystack_base_url or settings.paystack_base_url == "":
        issues.append("PAYSTACK_BASE_URL is not configured")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


def validate_ai_config() -> Dict[str, bool]:
    """Validate AI/OpenRouter configuration."""
    issues = []
    warnings = []
    
    # Check OpenRouter API key
    if not settings.openrouter_api_key or settings.openrouter_api_key in [
        "sk-or-v1-your_api_key_here",
        "your_openrouter_api_key_here",
        ""
    ]:
        warnings.append("OPENROUTER_API_KEY is not configured - AI features will be disabled")
    
    # Check model
    if not settings.openrouter_model or settings.openrouter_model == "":
        warnings.append("OPENROUTER_MODEL is not configured - using default")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "ai_enabled": bool(settings.openrouter_api_key and settings.openrouter_api_key not in [
            "sk-or-v1-your_api_key_here",
            "your_openrouter_api_key_here",
            ""
        ])
    }


def validate_mongodb_config() -> Dict[str, bool]:
    """Validate MongoDB configuration."""
    issues = []
    warnings = []
    
    # Check MongoDB URL
    if not settings.mongodb_url or settings.mongodb_url in [
        "mongodb://localhost:27017",
        "mongodb+srv://username:password@cluster.mongodb.net/database_name?retryWrites=true&w=majority",
        ""
    ]:
        warnings.append("MONGODB_URL is not configured - using default or fallback")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


def validate_twilio_config() -> Dict[str, bool]:
    """Validate Twilio/WhatsApp configuration."""
    issues = []
    warnings = []
    
    # Check Twilio credentials
    if not settings.twilio_account_sid or settings.twilio_account_sid == "":
        warnings.append("TWILIO_ACCOUNT_SID is not configured - WhatsApp features will not work")
    
    if not settings.twilio_auth_token or settings.twilio_auth_token == "":
        warnings.append("TWILIO_AUTH_TOKEN is not configured - WhatsApp features will not work")
    
    if not settings.twilio_whatsapp_number or settings.twilio_whatsapp_number == "":
        warnings.append("TWILIO_WHATSAPP_NUMBER is not configured - WhatsApp features will not work")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


def validate_all_services() -> Dict[str, any]:
    """Validate all service configurations."""
    results = {
        "paystack": validate_paystack_config(),
        "ai": validate_ai_config(),
        "mongodb": validate_mongodb_config(),
        "twilio": validate_twilio_config(),
        "overall_valid": True
    }
    
    # Check if any critical services have issues
    if not results["paystack"]["valid"]:
        results["overall_valid"] = False
        logger.error("❌ Paystack configuration has critical issues - API calls will fail")
    
    # Log warnings
    for service_name, result in results.items():
        if service_name == "overall_valid":
            continue
        if result.get("warnings"):
            for warning in result["warnings"]:
                logger.warning(f"⚠️  {service_name.upper()}: {warning}")
        if result.get("issues"):
            for issue in result["issues"]:
                logger.error(f"❌ {service_name.upper()}: {issue}")
    
    return results


def log_service_status():
    """Log the status of all services for debugging."""
    logger.info("=" * 60)
    logger.info("Service Configuration Status")
    logger.info("=" * 60)
    
    results = validate_all_services()
    
    logger.info(f"Paystack: {'✅ Valid' if results['paystack']['valid'] else '❌ Invalid'}")
    logger.info(f"AI/OpenRouter: {'✅ Enabled' if results['ai']['ai_enabled'] else '⚠️  Disabled'}")
    logger.info(f"MongoDB: {'✅ Configured' if results['mongodb']['valid'] else '⚠️  Using defaults'}")
    logger.info(f"Twilio: {'✅ Configured' if results['twilio']['valid'] else '⚠️  Not configured'}")
    logger.info(f"Overall: {'✅ All critical services valid' if results['overall_valid'] else '❌ Some services have issues'}")
    logger.info("=" * 60)



