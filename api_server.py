"""FastAPI server for Paystack operations."""

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import asyncio
import os

from app.utils.config import settings
from app.utils.logger import get_logger
from app.services.paystack_service import paystack_service, PaystackAPIError

# Initialize logger first
logger = get_logger("api_server")

# Validate all services on startup
try:
    from app.utils.service_validator import log_service_status
    log_service_status()
except Exception as e:
    logger.warning(f"Could not validate services: {e}")

# Import new AI services
try:
    from app.agents.financial_agent_refactored import FinancialAgent
    from app.utils.memory_manager import memory_manager
    from app.utils.recipient_manager import recipient_manager
    from app.services.whatsapp_service import WhatsAppService
    from app.services.ocr_service import OCRService
    
    # Check for AI services
    ai_client = None
    ai_model = None
    ai_enabled = False
    
    # Try to import AI services
    try:
        from app.config.ai_config import get_ai_client, get_ai_model, is_ai_enabled
        ai_client = get_ai_client()
        ai_model = get_ai_model()
        ai_enabled = is_ai_enabled()
    except ImportError:
        logger.info("AI services not configured, continuing without AI")
    
    # Initialize services with proper parameters
    financial_agent = FinancialAgent(
        paystack_service=paystack_service,
        memory_manager=memory_manager,
        recipient_manager=recipient_manager,
        ai_client=ai_client,
        ai_model=ai_model,
        ai_enabled=ai_enabled
    )
    whatsapp_service = WhatsAppService()
    ocr_service = OCRService()
    telegram_service = None
    try:
        from app.services.telegram_service import TelegramService
        telegram_service = TelegramService()
    except ImportError:
        pass

    AI_SERVICES_AVAILABLE = True
    logger.info("AI services initialized successfully")
except ImportError as e:
    logger.warning(f"AI services not available: {e}")
    AI_SERVICES_AVAILABLE = False
    telegram_service = None
except Exception as e:
    logger.error(f"Error initializing AI services: {e}")
    AI_SERVICES_AVAILABLE = False
    telegram_service = None

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="FastAPI backend for Paystack CLI operations",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None  # Disable redoc in production
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware (restrictive for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only allow necessary methods
    allow_headers=["Content-Type", "X-Twilio-Signature", "X-API-Key", "X-Telegram-Bot-Api-Secret-Token"],
)

# Mount static files for receipt images
receipts_dir = os.path.join(os.path.dirname(__file__), "app", "receipts", "output")
os.makedirs(receipts_dir, exist_ok=True)
app.mount("/receipts", StaticFiles(directory=receipts_dir), name="receipts")


# Pydantic models for request/response

class BankResolveRequest(BaseModel):
    account_number: str = Field(..., description="Account number to resolve")
    bank_code: str = Field(..., description="Bank code")


class BankResolveResponse(BaseModel):
    account_number: str
    account_name: str
    bank_id: Optional[int] = None


class CreateRecipientRequest(BaseModel):
    name: str = Field(..., description="Recipient name")
    account_number: str = Field(..., description="Account number")
    bank_code: str = Field(..., description="Bank code")
    currency: str = Field(default="NGN", description="Currency code")
    description: Optional[str] = Field(None, description="Optional description")


class CreateRecipientResponse(BaseModel):
    recipient_code: str
    name: str
    type: str
    currency: str
    details: Dict[str, Any]


class InitiateTransferRequest(BaseModel):
    amount: float = Field(..., description="Amount in main currency unit (e.g., 100.00 for ₦100)")
    recipient_code: str = Field(..., description="Recipient code")
    reason: str = Field(..., description="Transfer reason")
    currency: str = Field(default="NGN", description="Currency code")
    reference: Optional[str] = Field(None, description="Optional reference")


class FinalizeTransferRequest(BaseModel):
    transfer_code: str = Field(..., description="Transfer code from initiate response")
    otp: str = Field(..., description="OTP received")


class StandardResponse(BaseModel):
    status: bool
    message: str
    data: Optional[Any] = None


# Exception handler for Paystack API errors
@app.exception_handler(PaystackAPIError)
async def paystack_api_exception_handler(request, exc: PaystackAPIError):
    logger.error(f"Paystack API error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code or status.HTTP_400_BAD_REQUEST,
        content={
            "status": False,
            "message": exc.message,
            "data": exc.response_data
        }
    )


# General exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": False,
            "message": "An unexpected error occurred",
            "data": None
        }
    )


@app.on_event("startup")
async def startup_webhook_check():
    """Warn if Twilio is configured but server is bound to localhost or WEBHOOK_URL is unset."""
    if not getattr(settings, "twilio_account_sid", None) or not settings.twilio_account_sid:
        return
    host = getattr(settings, "api_host", "127.0.0.1")
    if host == "127.0.0.1" or host == "localhost":
        logger.warning(
            "Twilio is configured but API_HOST is %s. Twilio cannot reach localhost. "
            "On VPS set API_HOST=0.0.0.0.",
            host,
        )
    webhook_url = (getattr(settings, "webhook_url", "") or "").strip()
    if not webhook_url:
        logger.info(
            "Set WEBHOOK_URL in .env to the exact URL from Twilio Console (e.g. http://YOUR_IP:8000/whatsapp/webhook) so signature validation passes."
        )
    if telegram_service and getattr(telegram_service, "token", None):
        logger.info("Telegram chat interface enabled; set webhook URL in BotFather to https://<your-domain>/telegram/webhook")


# Dependency to check API key for protected endpoints
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for protected endpoints."""
    # For WhatsApp-only deployment, we can disable other endpoints
    # Or require an API key from environment
    api_key = os.getenv("API_KEY", "")
    
    if not api_key:
        # If no API key set, allow access (for development)
        # In production, you should set API_KEY env var
        return True
    
    if x_api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return True


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name, "version": settings.app_version}


# Bank and Account Resolution Endpoints

@app.get("/api/banks")
async def list_banks(currency: str = "NGN", _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Get list of banks for a specific currency."""
    logger.info(f"API: Listing banks for currency {currency}")
    
    try:
        banks = await paystack_service.list_banks(currency)
        return StandardResponse(
            status=True,
            message=f"Banks retrieved for {currency}",
            data=banks
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error listing banks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch banks"
        )


@app.post("/api/bank/resolve")
async def resolve_account(request: BankResolveRequest, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Resolve bank account number."""
    logger.info(f"API: Resolving account {request.account_number}")
    
    try:
        account_info = await paystack_service.resolve_account(
            request.account_number,
            request.bank_code
        )
        
        return StandardResponse(
            status=True,
            message="Account resolved successfully",
            data=account_info
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error resolving account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve account"
        )


# Transfer Recipient Endpoints

@app.post("/api/transfer-recipients")
async def create_transfer_recipient(request: CreateRecipientRequest, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Create a new transfer recipient."""
    logger.info(f"API: Creating recipient {request.name}")
    
    try:
        recipient = await paystack_service.create_transfer_recipient(
            recipient_type="nuban",
            name=request.name,
            account_number=request.account_number,
            bank_code=request.bank_code,
            currency=request.currency,
            description=request.description or ""
        )
        
        return StandardResponse(
            status=True,
            message="Transfer recipient created successfully",
            data=recipient
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error creating recipient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create recipient"
        )


@app.get("/api/transfer-recipients")
async def list_transfer_recipients(
    _: bool = Depends(verify_api_key),
    per_page: int = 50,
    page: int = 1
) -> StandardResponse:
    """Get list of transfer recipients."""
    logger.info(f"API: Listing transfer recipients - page {page}")
    
    try:
        recipients = await paystack_service.list_transfer_recipients(per_page, page)
        return StandardResponse(
            status=True,
            message="Transfer recipients retrieved successfully",
            data=recipients
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error listing recipients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recipients"
        )


@app.get("/api/transfer-recipients/{recipient_code}")
async def fetch_transfer_recipient(recipient_code: str, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Get details of a specific transfer recipient."""
    logger.info(f"API: Fetching recipient {recipient_code}")
    
    try:
        recipient = await paystack_service.fetch_transfer_recipient(recipient_code)
        return StandardResponse(
            status=True,
            message="Transfer recipient retrieved successfully",
            data=recipient
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching recipient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recipient"
        )


# Balance Endpoints

@app.get("/api/balance")
async def get_balance(_: bool = Depends(verify_api_key)) -> StandardResponse:
    """Get account balance."""
    logger.info("API: Getting balance")
    
    try:
        balance = await paystack_service.get_balance()
        return StandardResponse(
            status=True,
            message="Balance retrieved successfully",
            data=balance
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error getting balance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance"
        )


@app.get("/api/balance/ledger")
async def get_balance_ledger(
    _: bool = Depends(verify_api_key),
    per_page: int = 50,
    page: int = 1
) -> StandardResponse:
    """Get balance ledger."""
    logger.info(f"API: Getting balance ledger - page {page}")
    
    try:
        ledger = await paystack_service.get_balance_ledger(per_page, page)
        return StandardResponse(
            status=True,
            message="Balance ledger retrieved successfully",
            data=ledger
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error getting balance ledger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance ledger"
        )


# Transfer Endpoints

@app.post("/api/transfers")
async def initiate_transfer(request: InitiateTransferRequest, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Initiate a transfer."""
    logger.info(f"API: Initiating transfer of {request.amount} to {request.recipient_code}")
    
    try:
        # Convert amount to kobo (multiply by 100)
        amount_kobo = int(request.amount * 100)
        
        # Generate reference if not provided
        reference = request.reference or f"api_{uuid.uuid4().hex[:8]}"
        
        transfer = await paystack_service.initiate_transfer(
            amount=amount_kobo,
            recipient_code=request.recipient_code,
            reason=request.reason,
            currency=request.currency,
            reference=reference
        )
        
        return StandardResponse(
            status=True,
            message="Transfer initiated successfully",
            data=transfer
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error initiating transfer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate transfer"
        )


@app.post("/api/transfers/finalize")
async def finalize_transfer(request: FinalizeTransferRequest, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Finalize a transfer with OTP."""
    logger.info(f"API: Finalizing transfer {request.transfer_code}")
    
    try:
        transfer = await paystack_service.finalize_transfer(
            request.transfer_code,
            request.otp
        )
        
        return StandardResponse(
            status=True,
            message="Transfer finalized successfully",
            data=transfer
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error finalizing transfer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to finalize transfer"
        )


@app.get("/api/transfers")
async def list_transfers(
    _: bool = Depends(verify_api_key),
    per_page: int = 50,
    page: int = 1,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> StandardResponse:
    """Get list of transfers."""
    logger.info(f"API: Listing transfers - page {page}")
    
    try:
        if from_date and to_date:
            transfers = await paystack_service.list_transfers(
                per_page=per_page,
                page=page,
                from_date=from_date,
                to_date=to_date
            )
        elif from_date:
            transfers = await paystack_service.list_transfers(
                per_page=per_page,
                page=page,
                from_date=from_date
            )
        elif to_date:
            transfers = await paystack_service.list_transfers(
                per_page=per_page,
                page=page,
                to_date=to_date
            )
        else:
            transfers = await paystack_service.list_transfers(
                per_page=per_page,
                page=page
            )
        
        return StandardResponse(
            status=True,
            message="Transfers retrieved successfully",
            data=transfers
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list transfers"
        )


@app.get("/api/transfers/{transfer_code}")
async def fetch_transfer(transfer_code: str, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Get details of a specific transfer."""
    logger.info(f"API: Fetching transfer {transfer_code}")
    
    try:
        transfer = await paystack_service.fetch_transfer(transfer_code)
        return StandardResponse(
            status=True,
            message="Transfer retrieved successfully",
            data=transfer
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching transfer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transfer"
        )


@app.get("/api/transfers/verify/{reference}")
async def verify_transfer(reference: str, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Verify a transfer by reference."""
    logger.info(f"API: Verifying transfer {reference}")
    
    try:
        transfer = await paystack_service.verify_transfer(reference)
        return StandardResponse(
            status=True,
            message="Transfer verified successfully",
            data=transfer
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error verifying transfer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify transfer"
        )


# Transaction Endpoints

@app.get("/api/transactions")
async def list_transactions(
    _: bool = Depends(verify_api_key),
    per_page: int = 50,
    page: int = 1,
    status_filter: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> StandardResponse:
    """Get list of transactions."""
    logger.info(f"API: Listing transactions - page {page}")
    
    try:
        if status_filter and from_date and to_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                status=status_filter,
                from_date=from_date,
                to_date=to_date
            )
        elif status_filter and from_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                status=status_filter,
                from_date=from_date
            )
        elif status_filter and to_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                status=status_filter,
                to_date=to_date
            )
        elif from_date and to_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                from_date=from_date,
                to_date=to_date
            )
        elif status_filter:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                status=status_filter
            )
        elif from_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                from_date=from_date
            )
        elif to_date:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page,
                to_date=to_date
            )
        else:
            transactions = await paystack_service.list_transactions(
                per_page=per_page,
                page=page
            )
        
        return StandardResponse(
            status=True,
            message="Transactions retrieved successfully",
            data=transactions
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error listing transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list transactions"
        )


@app.get("/api/transactions/verify/{reference}")
async def verify_transaction(reference: str, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Verify a transaction by reference."""
    logger.info(f"API: Verifying transaction {reference}")
    
    try:
        transaction = await paystack_service.verify_transaction(reference)
        return StandardResponse(
            status=True,
            message="Transaction verified successfully",
            data=transaction
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error verifying transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify transaction"
        )


@app.get("/api/transactions/{transaction_id}")
async def fetch_transaction(transaction_id: int, _: bool = Depends(verify_api_key)) -> StandardResponse:
    """Get details of a specific transaction."""
    logger.info(f"API: Fetching transaction {transaction_id}")
    
    try:
        transaction = await paystack_service.fetch_transaction(transaction_id)
        return StandardResponse(
            status=True,
            message="Transaction retrieved successfully",
            data=transaction
        )
    except PaystackAPIError:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transaction"
        )


@app.get("/api/info")
async def get_app_info(_: bool = Depends(verify_api_key)):
    """Get application information."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "supported_currencies": list(settings.SUPPORTED_CURRENCIES.keys()),
        "default_currency": settings.default_currency
    }


# =============================================================================
# WHATSAPP WEBHOOK ENDPOINTS (NEW)
# =============================================================================

@app.post("/whatsapp/webhook")
@limiter.limit("100/minute")  # Rate limit: 100 requests per minute per IP
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages with signature verification."""
    
    if not AI_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI services not available. Please check configuration."
        )
    
    try:
        twilio_signature = request.headers.get("X-Twilio-Signature", "")
        form_data = await request.form()
        request_data = dict(form_data)

        request_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        if request.url.query:
            request_url += f"?{request.url.query}"
        validation_url = (getattr(settings, "webhook_url", "") or "").strip() or None

        if not whatsapp_service.validate_webhook_request(
            request_data, request_url, twilio_signature, validation_url=validation_url
        ):
            logger.warning(f"Invalid webhook request from {request_data.get('From', 'Unknown')}")
            raise HTTPException(
                status_code=403,
                detail="Invalid webhook signature"
            )

        if 'Body' not in request_data and int(request_data.get('NumMedia', 0)) == 0:
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="application/xml"
            )
        
        logger.info(f"WhatsApp webhook received and verified from {request_data.get('From', 'Unknown')}")
        
        # Extract webhook information with spam filtering
        webhook_info = await whatsapp_service.handle_webhook(request_data)
        
        # Check if message was identified as spam
        if webhook_info.get('is_spam', False) or webhook_info.get('ignored', False):
            logger.info(f"Spam message ignored from {webhook_info.get('user_info', {}).get('user_id', 'Unknown')}")
            # Return empty TwiML response for spam messages
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="application/xml"
            )
        
        user_info = webhook_info['user_info']
        message_content = webhook_info['message_content']
        
        # Handle message based on type
        if message_content.get('num_media', 0) > 0:
            # Handle image message
            response_text = await handle_image_message(user_info, message_content)
        else:
            # Handle text message
            response_text = await handle_text_message(user_info, message_content)
        
        # Return TwiML response
        return Response(
            content=whatsapp_service.create_webhook_response(response_text),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        error_message = "Sorry, I'm having trouble processing your message. Please try again."
        return Response(
            content=whatsapp_service.create_webhook_response(error_message),
            media_type="application/xml"
        )


async def handle_text_message(
    user_info: Dict[str, Any],
    message_content: Dict[str, Any],
    send_follow_up_callback=None,
    send_receipt_callback=None,
) -> str:
    """Handle text message. If callbacks are None, uses WhatsApp."""
    user_id = user_info["user_id"]
    text = message_content.get("text", "").strip()

    if not text:
        return "👋 Hello! I'm your financial assistant. How can I help you today?"

    if text.lower() in ["help", "menu", "commands"]:
        return """
🤖 **Your Financial Assistant**

**Available Commands:**
💰 Check Balance: "balance"
🏦 Resolve Account: "1234567890 access bank"
💸 Send Money: "send 5000 to John"
📊 View History: "history"
❓ Help: "help"

Just chat naturally! I understand Nigerian banking terms.
"""
    if send_follow_up_callback is None:
        async def _whatsapp_follow_up(uid: str, msg: str):
            try:
                await whatsapp_service.send_message(f"whatsapp:{uid}", msg)
                logger.info(f"Follow-up message sent to {uid}")
            except Exception as e:
                logger.error(f"Failed to send follow-up message to {uid}: {e}")
        send_follow_up_callback = _whatsapp_follow_up

    try:
        response = await financial_agent.process_message(
            user_id=user_id,
            message=text,
            send_follow_up_callback=send_follow_up_callback,
            send_receipt_callback=send_receipt_callback,
        )
        return response
    except Exception as e:
        logger.error(f"Error processing with financial agent: {e}")
        return "Sorry, I'm having trouble processing your request. Please try again."


async def handle_image_message(
    user_info: Dict[str, Any],
    message_content: Dict[str, Any],
    send_follow_up_callback=None,
    download_media_func=None,
    send_receipt_callback=None,
) -> str:
    """Handle image message. If download_media_func is None, uses WhatsApp media_url."""
    user_id = user_info["user_id"]

    if download_media_func is not None:
        image_data = await download_media_func(message_content)
    else:
        media_url = message_content.get("media_url", "")
        if not media_url:
            return "I couldn't access the image. Please try sending it again."
        image_data = await whatsapp_service.download_media(media_url)

    if not image_data:
        return "I couldn't download the image. Please try again."

    try:
        ocr_result = await ocr_service.extract_bank_details(image_data)

        if ocr_result.get("has_essential_info", False):
            extracted = ocr_result["extracted_data"]
            account_number = extracted.get("account_number", "")
            bank_name = extracted.get("bank_name", "")

            if account_number and bank_name:
                resolve_message = f"resolve {account_number} {bank_name}"
                response = await financial_agent.process_message(
                    user_id=user_id,
                    message=resolve_message,
                    send_follow_up_callback=send_follow_up_callback,
                    send_receipt_callback=send_receipt_callback,
                )
                return response

        return ocr_service.format_extraction_result(ocr_result)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return "I had trouble processing the image. Please try again with a clearer image."


# =============================================================================
# TELEGRAM WEBHOOK
# =============================================================================

@app.post("/telegram/webhook")
@limiter.limit("100/minute")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram bot updates (messages). Reply with 200 quickly; process then send response."""
    if not AI_SERVICES_AVAILABLE or not telegram_service or not getattr(telegram_service, "token", None):
        return Response(status_code=200)

    try:
        body = await request.json()
    except Exception:
        return Response(status_code=200)

    secret = (getattr(settings, "telegram_webhook_secret", None) or "").strip()
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return Response(status_code=403)

    message = body.get("message")
    if not message:
        return Response(status_code=200)

    chat_id = message.get("chat", {}).get("id")
    if chat_id is None:
        return Response(status_code=200)

    user_info = {"user_id": str(chat_id)}
    text = (message.get("text") or "").strip()
    photo = message.get("photo")

    async def send_follow_up(uid: str, msg: str):
        await telegram_service.send_message(uid, msg)

    async def send_receipt(uid: str, image_bytes: bytes, caption: str):
        await telegram_service.send_photo(uid, image_bytes, caption)

    async def download_media(mc: Dict[str, Any]):
        fid = mc.get("telegram_file_id")
        return await telegram_service.download_media(fid) if fid else None

    try:
        if photo and isinstance(photo, list) and len(photo) > 0:
            file_id = photo[-1].get("file_id")
            if not file_id:
                response_text = "I couldn't get the photo. Please try again."
            else:
                message_content = {"text": "", "num_media": 1, "telegram_file_id": file_id}
                response_text = await handle_image_message(
                    user_info,
                    message_content,
                    send_follow_up_callback=send_follow_up,
                    download_media_func=download_media,
                    send_receipt_callback=send_receipt,
                )
        else:
            message_content = {"text": text, "num_media": 0}
            response_text = await handle_text_message(
                user_info,
                message_content,
                send_follow_up_callback=send_follow_up,
                send_receipt_callback=send_receipt,
            )
        await telegram_service.send_message(str(chat_id), response_text or "Done.")
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        try:
            await telegram_service.send_message(str(chat_id), "Sorry, I had trouble processing that. Please try again.")
        except Exception:
            pass
    return Response(status_code=200)


# Test endpoint for WhatsApp integration
@app.post("/whatsapp/test")
async def test_whatsapp(
    _: bool = Depends(verify_api_key),
    to: str = Form(...),
    message: str = Form(...)
):
    """Test WhatsApp message sending."""
    
    if not AI_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp service not available"
        )
    
    try:
        result = await whatsapp_service.send_message(to, message)
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


# OCR test endpoint
@app.post("/api/ocr/extract")
async def extract_from_image(file: UploadFile = File(...), _: bool = Depends(verify_api_key)):
    """Extract bank details from uploaded image."""
    
    if not AI_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="OCR service not available"
        )
    
    try:
        # Read file content
        image_data = await file.read()
        
        # Process with OCR
        result = await ocr_service.extract_bank_details(image_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing image for OCR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )


# AI Agent test endpoint
@app.post("/api/agent/chat")
async def chat_with_agent(
    _: bool = Depends(verify_api_key),
    user_id: str = Form(...),
    message: str = Form(...),
    thread_id: Optional[str] = Form(None)
):
    """Chat with the financial agent."""
    
    if not AI_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI agent not available"
        )
    
    try:
        response = await financial_agent.process_message(
            user_id=user_id,
            message=message
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error chatting with agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 