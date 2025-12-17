"""
Core Pydantic schemas for the PayStack CLI application.
Provides type safety for WhatsApp, Paystack, and MongoDB data structures.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator

# MongoDB Schemas
class MongoDBUser(BaseModel):
    """MongoDB user document schema."""
    user_id: str = Field(..., description="WhatsApp user ID")
    phone_number: str = Field(..., description="User's phone number")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MongoDBConversation(BaseModel):
    """MongoDB conversation document schema."""
    conversation_id: str = Field(..., description="Unique conversation ID")
    user_id: str = Field(..., description="WhatsApp user ID")
    message: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user/assistant/system)")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MongoDBTransaction(BaseModel):
    """MongoDB transaction document schema."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    user_id: str = Field(..., description="WhatsApp user ID")
    operation_type: str = Field(..., description="Type of operation")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(default="NGN", description="Currency code")
    status: str = Field(..., description="Transaction status")
    timestamp: datetime = Field(default_factory=datetime.now)
    paystack_reference: Optional[str] = Field(None, description="Paystack reference")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# WhatsApp Schemas
class WhatsAppMessage(BaseModel):
    """WhatsApp message schema."""
    from_: str = Field(..., alias="from", description="Sender's phone number")
    to: str = Field(..., description="Recipient's phone number")
    text: str = Field(..., description="Message text")
    timestamp: datetime = Field(default_factory=datetime.now)
    message_id: Optional[str] = Field(None, description="WhatsApp message ID")
    reply_to: Optional[str] = Field(None, description="Reply to message ID")
    
    class Config:
        validate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WhatsAppContact(BaseModel):
    """WhatsApp contact schema."""
    phone_number: str = Field(..., description="Contact's phone number")
    name: Optional[str] = Field(None, description="Contact's name")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+'):
            v = '+' + v
        return v

class WhatsAppWebhook(BaseModel):
    """WhatsApp webhook payload schema."""
    entry: List[Dict[str, Any]] = Field(..., description="Webhook entry data")
    object: str = Field(..., description="Object type")
    
    class Config:
        extra = "allow"

# Paystack Schemas
class PaystackBalance(BaseModel):
    """Paystack balance response schema."""
    currency: str = Field(..., description="Currency code")
    balance: int = Field(..., description="Balance in kobo")
    
    @validator('balance')
    def validate_balance(cls, v):
        if v < 0:
            raise ValueError("Balance cannot be negative")
        return v

class PaystackTransaction(BaseModel):
    """Paystack transaction schema."""
    id: int = Field(..., description="Transaction ID")
    reference: str = Field(..., description="Transaction reference")
    amount: int = Field(..., description="Amount in kobo")
    currency: str = Field(default="NGN", description="Currency code")
    status: str = Field(..., description="Transaction status")
    channel: str = Field(..., description="Payment channel")
    created_at: datetime = Field(..., description="Creation timestamp")
    gateway_response: Optional[str] = Field(None, description="Gateway response message")
    customer: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @validator('created_at', pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

class PaystackTransfer(BaseModel):
    """Paystack transfer schema."""
    amount: int = Field(..., description="Transfer amount in kobo")
    recipient: str = Field(..., description="Recipient code")
    reason: Optional[str] = Field(None, description="Transfer reason")
    currency: str = Field(default="NGN", description="Currency code")
    source: str = Field(default="balance", description="Transfer source")
    reference: Optional[str] = Field(None, description="Transfer reference")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

class PaystackRecipient(BaseModel):
    """Paystack recipient schema."""
    type: str = Field(..., description="Recipient type (nuban)")
    name: str = Field(..., description="Recipient name")
    account_number: str = Field(..., description="Account number")
    bank_code: str = Field(..., description="Bank code")
    currency: str = Field(default="NGN", description="Currency code")
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Account number must be 10 digits")
        return v
    
    @validator('bank_code')
    def validate_bank_code(cls, v):
        if not v.isdigit() or len(v) != 3:
            raise ValueError("Bank code must be 3 digits")
        return v

class PaystackBank(BaseModel):
    """Paystack bank schema."""
    name: str = Field(..., description="Bank name")
    slug: str = Field(..., description="Bank slug")
    code: str = Field(..., description="Bank code")
    longcode: str = Field(..., description="Bank long code")
    gateway: Optional[str] = Field(None, description="Gateway")
    pay_with_bank: bool = Field(default=False, description="Pay with bank enabled")
    active: bool = Field(default=True, description="Bank is active")
    country: str = Field(default="Nigeria", description="Bank country")
    currency: str = Field(default="NGN", description="Bank currency")
    type: str = Field(default="nuban", description="Bank type")

# Business Logic Schemas
class BalanceCheck(BaseModel):
    """Balance check operation schema."""
    user_id: str = Field(..., description="User ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = Field(..., description="Operation success")
    balance: Optional[float] = Field(None, description="Account balance")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TransferRequest(BaseModel):
    """Transfer request schema."""
    user_id: str = Field(..., description="User ID")
    amount: float = Field(..., description="Transfer amount")
    recipient_name: str = Field(..., description="Recipient name")
    account_number: str = Field(..., description="Recipient account number")
    bank_code: str = Field(..., description="Recipient bank code")
    reason: Optional[str] = Field(None, description="Transfer reason")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Account number must be 10 digits")
        return v

class ConversationState(BaseModel):
    """Conversation state schema."""
    user_id: str = Field(..., description="User ID")
    current_state: str = Field(..., description="Current conversation state")
    context: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="State expiration time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BeneficiaryContact(BaseModel):
    """Beneficiary contact schema."""
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Beneficiary name")
    account_number: str = Field(..., description="Account number")
    bank_code: str = Field(..., description="Bank code")
    bank_name: str = Field(..., description="Bank name")
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="Contact is active")
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Account number must be 10 digits")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# OCR Schemas
class OCRExtractionResult(BaseModel):
    """OCR extraction result schema."""
    success: bool = Field(..., description="Extraction success")
    raw_text: str = Field(..., description="Raw extracted text")
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    has_essential_info: bool = Field(default=False, description="Has essential information")
    confidence: str = Field(default="low", description="Extraction confidence")
    error: Optional[str] = Field(None, description="Error message if failed")

class BankDetailsExtraction(BaseModel):
    """Bank details extraction schema."""
    account_number: Optional[str] = Field(None, description="Extracted account number")
    bank_name: Optional[str] = Field(None, description="Extracted bank name")
    account_name: Optional[str] = Field(None, description="Extracted account name")
    amount: Optional[float] = Field(None, description="Extracted amount")
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if v is not None and (not v.isdigit() or len(v) != 10):
            raise ValueError("Account number must be 10 digits")
        return v

# AI/Memory Schemas
class AIContextData(BaseModel):
    """AI context data schema."""
    user_id: str = Field(..., description="User ID")
    context_type: str = Field(..., description="Context type")
    context_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="Context expiration")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MemoryContext(BaseModel):
    """Memory context schema."""
    recent_conversations: List[Dict[str, Any]] = Field(default_factory=list)
    banking_operations: List[Dict[str, Any]] = Field(default_factory=list)
    transaction_context: Optional[Dict[str, Any]] = Field(None)
    query_analysis: Dict[str, Any] = Field(default_factory=dict)
    smart_insights: Dict[str, Any] = Field(default_factory=dict)

# Response Schemas
class LLMRefinedResponse(BaseModel):
    """LLM refined response schema."""
    original_response: str = Field(..., description="Original template response")
    refined_response: str = Field(..., description="LLM-refined response")
    intent: str = Field(..., description="Response intent")
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TransactionSummary(BaseModel):
    """Transaction summary schema."""
    total_transactions: int = Field(..., description="Total number of transactions")
    total_amount: str = Field(..., description="Total amount formatted")
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    period: Optional[str] = Field(None, description="Time period")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TransferConfirmation(BaseModel):
    """Transfer confirmation schema."""
    transfer_id: str = Field(..., description="Transfer ID")
    user_id: str = Field(..., description="User ID")
    amount: float = Field(..., description="Transfer amount")
    recipient_name: str = Field(..., description="Recipient name")
    account_number: str = Field(..., description="Recipient account number")
    bank_name: str = Field(..., description="Recipient bank name")
    status: str = Field(default="pending", description="Confirmation status")
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="Confirmation expiration")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ParsedUserIntent(BaseModel):
    """Parsed user intent schema."""
    intent: str = Field(..., description="Detected intent")
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, description="Intent confidence score")
    original_message: str = Field(..., description="Original user message")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class HistoryItem(BaseModel):
    """History item schema."""
    transaction_id: str = Field(..., description="Transaction ID")
    amount: str = Field(..., description="Formatted amount")
    status: str = Field(..., description="Transaction status")
    date: str = Field(..., description="Transaction date")
    channel: str = Field(..., description="Payment channel")
    reference: str = Field(..., description="Transaction reference")
    description: Optional[str] = Field(None, description="Transaction description")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 